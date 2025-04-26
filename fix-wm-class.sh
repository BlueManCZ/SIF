#!/bin/sh
LOG_FILE="/tmp/wmfix.log"
LAST=${@:$#}
WM_CLASS="$LAST"
echo "Starting process: $@" > $LOG_FILE
echo "Window Class: $WM_CLASS" >> $LOG_FILE
"$@" &
PID=$!
echo "Process ID: $PID" >> $LOG_FILE
while kill -0 $PID 2> /dev/null; do
    echo "Process still running: $(date)" >> $LOG_FILE
    xdotool search --sync --name "$LAST" set_window --classname "$WM_CLASS" --class "$WM_CLASS" %@
    sleep 1
done
echo "Process ended: $(date)" >> $LOG_FILE