#!/bin/bash
# Control-machine helper: push the load generator to machine 1, run it there in the background (nohup),
# poll its log, then fetch results/<name>.json.   usage: run_loadgen.sh <name> <loadgen.py arguments...>
#   run_loadgen.sh try_n8 single --users 8 --duration 30
#   run_loadgen.sh cap_dp capacity --levels 8,16,32,64,128,256 --ttft-p95-max 1.0 --speed-p5-min 20
#   TARGETS=loadgen_targets_mp.json run_loadgen.sh mp capacity ...     # Model Parallel: the 2 replicas' counters
set -u
HERE=$(cd "$(dirname "$0")" && pwd); . "$HERE/nodes.env"
NAME=$1; MODE=$2; shift 2
SSHO="-i $SSH_KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=20 -o LogLevel=ERROR"
n1() { ssh -n $SSHO -p $N1_SSH_PORT root@$N1_IP "$@"; }
n1 "mkdir -p $REMOTE_DIR/results $REMOTE_DIR/logs"
scp -q $SSHO -P $N1_SSH_PORT "$HERE/loadgen.py" "$HERE/loadgen_targets.json" "$HERE/loadgen_targets_mp.json" "$HERE/dataset_samples.py" root@$N1_IP:$REMOTE_DIR/code/ 2>/dev/null
LOG=$REMOTE_DIR/logs/loadgen_$NAME.log
if [ "$MODE" = samples ]; then RUN="$REMOTE_DIR/code/dataset_samples.py --out $REMOTE_DIR/results/$NAME.json $*"
else RUN="-u $REMOTE_DIR/code/loadgen.py $MODE --name $NAME --results-dir $REMOTE_DIR/results --targets $REMOTE_DIR/code/${TARGETS:-loadgen_targets.json} $*"; fi
# the braces matter: without them the whole "cd && ulimit && python" list is backgrounded with the SSH channel still open
n1 "cd $REMOTE_DIR && ulimit -n 65536 && { setsid nohup $REMOTE_DIR/venv/bin/python $RUN > $LOG 2>&1 < /dev/null & } ; echo started"
seen=0
while :; do                       # short SSH calls only; the measurement itself runs detached on machine 1
  sleep 5
  out=$(n1 "tail -n +$((seen+1)) $LOG; pgrep -f 'code/(loadgen|dataset_samples).py' > /dev/null && echo __RUNNING__ || echo __STOPPED__")
  body=$(echo "$out" | grep -v '^__\(RUNNING\|STOPPED\)__$')
  [ -n "$body" ] && { echo "$body"; seen=$((seen + $(echo "$body" | wc -l))); }
  echo "$out" | tail -1 | grep -q __STOPPED__ && break
done
mkdir -p "$HERE/../results/logs"
scp -q $SSHO -P $N1_SSH_PORT root@$N1_IP:$REMOTE_DIR/results/$NAME.json "$HERE/../results/" && echo "fetched results/$NAME.json"
scp -q $SSHO -P $N1_SSH_PORT root@$N1_IP:$LOG "$HERE/../results/logs/" 
