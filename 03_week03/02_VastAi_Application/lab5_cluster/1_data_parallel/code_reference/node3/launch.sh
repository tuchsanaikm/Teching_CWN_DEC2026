#!/bin/bash
# usage: launch.sh <outdir on nodes> [worker args]   e.g. launch.sh /workspace/run_smoke --smoke 3
D=$(dirname "$0"); source $D/nodes.env; OUT=$1; shift
$D/sshn 1 "bash /workspace/code/run_node.sh 1 127.0.0.1:$N1_PORT_IN $OUT $*"
for n in 2 3; do $D/sshn $n "bash /workspace/code/run_node.sh $n $N1_IP:$N1_PORT_EXT $OUT $*"; done
