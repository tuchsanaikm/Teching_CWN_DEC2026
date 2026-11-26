#!/bin/bash
# usage: progress.sh <tag> [wait seconds]  -> waits, then prints one status line per node (also appended to logs/progress.log)
cd "$(dirname "$0")"; TAG=$1; W=${2:-0}
python3 -c "import time; time.sleep($W)"
{ echo "== $(date '+%F %T') $TAG"
for n in 1 2 3; do ./sshn $n "grep -E 'step [0-9]+/|EPOCH|DONE|Error|error|Traceback' /workspace/lab5/run/$TAG/worker_node$n.log | tail -n 1 | cut -c1-260; nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader | tr '\n' ' '; echo" 2>&1 | sed "s/^/n$n| /"; done; } | tee -a logs/progress.log
