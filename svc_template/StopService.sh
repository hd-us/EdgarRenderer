#!/bin/bash
cd $(dirname $(readlink -f "$0"))
SCRIPT_PID=`cat pid.pid`
for SCRIPT_CHILD_PID in $(ps -o pid --no-headers --ppid $SCRIPT_PID); do
    echo Stopping Rendering Daemon process $SCRIPT_CHILD_PID
    kill -9 $SCRIPT_CHILD_PID
done
echo Stopping Rendering Daemon script process $SCRIPT_PID
kill -9 $SCRIPT_PID
