#!/bin/sh
WM_CLASS="$([ "$3" ] && echo "$3" || echo "$2")"
WM_NAME=$2
echo $WM_CLASS > "/tmp/wmlog.log"
echo $WM_NAME >> "/tmp/wmlog.log"
echo $1 >> "/tmp/wmlog.log"
COMMAND=$(echo $1 | tr -d "'")
set -- "${COMMAND}"
echo $@ >> "/tmp/wmlog.log"
$@ &
PID=$!
echo $PID >> "/tmp/wmlog.log"
while kill -0 $PID 2> /dev/null; do
    xdotool search --sync --name "$WM_NAME" set_window --classname "$WM_CLASS" --class "$WM_CLASS" %@
    echo "Still running $PID! at $(date)!" >> "/tmp/wmlog.log"
    sleep 1
done
echo "Completed execution at $(date)!" >> "/tmp/wmlog.log"
exit 0