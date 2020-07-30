#!/bin/sh

until xprop -name "$1"
do
	sleep 1
done
if [ "$2" ]; then
  xprop -name "$1" -f WM_CLASS 8s -set WM_CLASS "$2"
else
  xprop -name "$1" -f WM_CLASS 8s -set WM_CLASS "$1"
fi
