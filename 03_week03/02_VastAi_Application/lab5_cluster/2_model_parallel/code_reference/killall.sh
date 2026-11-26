#!/bin/bash
# stop everything of this lab on both nodes
D=$(dirname "$0")
for n in n1 n2; do "$D/$n" 'pkill -f "[s]upervise_node"; pkill -f "[w]orker.py"; pkill -f "[c]oordinator.py"; pkill -f "[n]et_server.py"; sleep 2; ps aux | grep -E "[p]ython" | wc -l; nvidia-smi --query-gpu=memory.used --format=csv,noheader | tr "\n" " "'; echo; done
