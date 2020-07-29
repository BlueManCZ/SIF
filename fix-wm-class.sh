#!/bin/sh

until xprop -name "$*"
do
	sleep 1
done
xprop -name "$*" -f WM_CLASS 8s -set WM_CLASS "$*"
