#!/bin/bash
# usage: start_node.sh <node>  -> upload code, start prepare.py (background) and the probe server on port 9000
cd "$(dirname "$0")"; n=$1
./sshn $n 'mkdir -p /workspace/lab5/code'
./scpn $n node_code/* /workspace/lab5/code/
./sshn $n 'bash /workspace/lab5/code/start_prepare.sh; bash /workspace/lab5/code/start_server.sh'
