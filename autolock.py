# -*- coding: utf-8 -*-

"""
Event server simple client
Waits for I-Beacons and sends messages
Temporary stores messages in file


MIT License

Copyright (c) 2017 Roman Mindlin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import blescan
import sys
import math
import const

import bluetooth._bluetooth as bluez
from subprocess import call

import processors
import logger

from time import sleep

import gobject
import dbus
from dbus.mainloop.glib import DBusGMainLoop
import threading

logger = logger.get_logger(__name__)


def getrange(txPower, rssi):
    """https://stackoverflow.com/questions/20416218/understanding-ibeacon-distancing"""
    if txPower == 0:
        txPower = 1
    ratio = float(rssi) / txPower
    if (ratio < 1.0):
        return round(math.pow(ratio, 10))
    else:
        distance = (0.89976) * math.pow(ratio, 7.7095) + 0.111
    return round(distance)


def filter_cb(bus, message):
    """https://unix.stackexchange.com/questions/212347/how-to-monitor-the-screen-lock-unlock-in-the-ubuntu-14-04"""
    global locked
    if message.get_member() != "EventEmitted":
        return
    args = message.get_args_list()
    if args[0] == "desktop-lock":
        locked = True
    elif args[0] == "desktop-unlock":
        locked = False


locked = False
DBusGMainLoop(set_as_default=True)
bus = dbus.SessionBus()
bus.add_match_string("type='signal',interface='com.ubuntu.Upstart0_6'")
bus.add_message_filter(filter_cb)
mainloop = gobject.MainLoop()


def start(*args, **kwargs):
    """Main loop"""
    processor = processors.Kalman()

    gobject_thread = threading.Thread(target=mainloop.run)
    gobject_thread.daemon = True
    gobject_thread.start()

    dev_id = 0
    try:
        sock = bluez.hci_open_dev(dev_id)
        blescan.hci_le_set_scan_parameters(sock)
        blescan.hci_enable_le_scan(sock)
        logger.info("ble thread started")
    except Exception as e:
        logger.error('Error accessing bluetooth device', exc_info=True)
        sys.exit(1)

    try:
        global locked
        counter = 0
        while True:
            returnedList = blescan.parse_events(sock, 10)
            for beacon in returnedList:
                uuid, major, minor = beacon.split(',')[1:4]
                if major in const.ALLOWED_MAJOR and minor in const.ALLOWED_MINOR:
                    beacon_id = beacon[:-8]
                    if beacon_id[-2:] == ',,':  # double comma at end of string
                        beacon_id = beacon_id[:-1]
                    txpower = int(beacon.split(',')[4])
                    rssi = int(beacon.split(',')[5])

                    rssi = -99 if rssi < -99 else rssi # rssi peak fix

                    rssi_filtered = processor.filter(beacon_id, rssi)

                    if rssi_filtered is None:
                        continue

                    beacon_dist = getrange(txpower, rssi_filtered)

                    if not locked:
                        if beacon_dist >= const.MAX_RANGE:
                            counter += 1
                        else:
                            counter = counter-1 if counter > 1 else 0
                        if counter == 4:
                            logger.info('screen is locked')
                            call(const.LOCK_SCREEN, shell=True)
                            locked = True
                            counter = 0

            sleep(.1)
    except KeyboardInterrupt:
        logger.warning("Ctrl-C pressed")
        sys.exit()


if __name__ == "__main__":
    sys.exit(start(sys.argv))
