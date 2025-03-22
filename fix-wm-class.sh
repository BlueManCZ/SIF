#!/bin/sh
WM_CLASS="$([ "$2" ] && echo "$2" || echo "$1")"
reaper_pid=$(pidof reaper)
while kill -0 $reaper_pid 2> /dev/null; do
    xdotool search --sync --name "$1" set_window --classname "$WM_CLASS" --class "$WM_CLASS" %@
    sleep 1
done