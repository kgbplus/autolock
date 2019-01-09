# -*- coding: utf-8 -*-

MAX_RANGE = 3
ALLOWED_MAJOR = ['1']
ALLOWED_MINOR = ['999']
LOG_FILE = './log.txt'
LOCK_SCREEN = 'sudo -H -u mindlin bash -c dbus_address=$(xargs -n 1 -0 < /proc/`pgrep gnome-session`/environ | grep DBUS); sudo -H -u mindlin bash -c "export $dbus_address && gnome-screensaver-command -l"'
