#!/bin/sh
LAST=${@:$#}
WM_CLASS="$LAST"
"$@" &
PID=$!
while kill -0 $PID 2> /dev/null; do
    xdotool search --sync --name "$LAST" set_window --classname "$WM_CLASS" --class "$WM_CLASS" %@
    sleep 1
done