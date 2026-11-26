#!/bin/bash
# usage: tailall.sh <tag> [lines]  -> last lines of each worker log + coordinator
cd "$(dirname "$0")"; TAG=$1; L=${2:-3}
for n in 1 2 3; do ./sshn $n "tail -n $L /workspace/lab5/run/$TAG/worker_node$n.log; nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader | tr '\n' ' '; echo" 2>&1 | sed "s/^/n$n| /" & done; wait
