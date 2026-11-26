#!/bin/bash
# usage: launch.sh <tag> [worker args...]     e.g.  launch.sh smoke --smoke 3   |   launch.sh train
# Uploads code/, starts the coordinator on Node 1 and one worker on each node.
# Everything runs detached (setsid nohup) on the nodes, so it keeps going if SSH drops.
cd "$(dirname "$0")"; TAG=$1; shift; EXTRA="$*"
read IP P < <(python3 -c "import json;d=json.load(open('state/n1.json'));print(d['ip'],d['port9000'])")
for n in 1 2 3; do ./scpn $n code/* /workspace/lab5/code/ & done; wait
RUN=/workspace/lab5/run/$TAG
./sshn 1 "bash /workspace/lab5/code/start_coord.sh $RUN"
for n in 1 2 3; do
  if [ $n = 1 ]; then H=127.0.0.1; PT=9000; else H=$IP; PT=$P; fi
  ./sshn $n "bash /workspace/lab5/code/start_worker.sh $RUN $((n-1)) $H $PT $EXTRA" &
done; wait
