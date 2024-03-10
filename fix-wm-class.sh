#!/bin/sh
WM_CLASS="$([ "$2" ] && echo "$2" || echo "$1")"
xdotool search --sync --name "$1" set_window --classname "$WM_CLASS" --class "$WM_CLASS" %@
