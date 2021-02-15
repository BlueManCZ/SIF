#!/bin/sh

until xdotool search --name "$1"
do
	sleep 1
done

WM_CLASS="$([ "$2" ] && echo "$2" || echo "$1")"
xdotool search --name "$1" set_window --classname "$WM_CLASS" --class "$WM_CLASS"
