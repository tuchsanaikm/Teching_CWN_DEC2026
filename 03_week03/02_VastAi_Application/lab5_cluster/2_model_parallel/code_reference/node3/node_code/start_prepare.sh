#!/bin/bash
# start prepare.py in the background unless it already ran or is running
cd /workspace/lab5
[ -f prepare_report.json ] && { echo "already prepared"; exit 0; }
[ -f prepare.pid ] && kill -0 "$(cat prepare.pid)" 2>/dev/null && { echo "running"; exit 0; }
setsid nohup bash -c "/venv/main/bin/pip install -q datasets > pip.log 2>&1 && /venv/main/bin/python code/prepare.py > prepare.log 2>&1; echo EXIT=\$? >> prepare.log" > /dev/null 2>&1 < /dev/null &
echo $! > prepare.pid; echo started
