#!/usr/bin/env sh

LOG_FILE="/tmp/steam_watcher.log"

WM_NAME=$1
echo "WM_NAME: $WM_NAME" > $LOG_FILE
shift
WM_NAME_ALT=$1
echo "WM_NAME_ALT: $WM_NAME_ALT" >> $LOG_FILE
shift

WM_CLASS=$WM_NAME_ALT

echo "Starting process: $@" >> $LOG_FILE
"$@" &

PID=$!
echo "Process ID: $PID" >> $LOG_FILE

while kill -0 $PID 2> /dev/null; do
        xdotool search --sync --name "$WM_NAME" set_window --classname "$WM_CLASS" --class "$WM_CLASS" %@
        echo "Process still running: $(date)" >> $LOG_FILE
        sleep 1
done
exit 0