#!/bin/bash
# start the probe server on port 9000 if nothing listens there yet
cd /workspace/lab5
if ! ss -ltn | grep -q ':9000 '; then
  setsid nohup /venv/main/bin/python code/netprobe.py server 9000 > netprobe_server.log 2>&1 < /dev/null &
  sleep 1
fi
ss -ltn | grep ':9000 '
