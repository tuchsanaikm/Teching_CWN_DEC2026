#!/bin/bash
# Control-machine helper: push the check to machine 1, run it there detached (nohup), poll its log,
# fetch results/loadtest_check.json (+ the per-run JSONs and logs).
#   run_loadtest_check.sh [--tests A,C,D,E] [--duration 40] [--note "..."]
set -u
HERE=$(cd "$(dirname "$0")" && pwd); . "$HERE/nodes.env"
SSHO="-i $SSH_KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=20 -o LogLevel=ERROR"
n1() { ssh -n $SSHO -p $N1_SSH_PORT root@$N1_IP "$@"; }
n1 "mkdir -p $REMOTE_DIR/results $REMOTE_DIR/logs"
scp -q $SSHO -P $N1_SSH_PORT "$HERE/fake_llm.py" "$HERE/loadgen.py" "$HERE/loadtest_check.py" "$HERE/nginx.conf" \
    "$HERE"/loadgen_targets*.json root@$N1_IP:$REMOTE_DIR/code/
# NGINX must know the shop_fake group before the check can switch to it (reload = SIGHUP, open questions are not cut)
n1 "pkill -HUP -f 'nginx: [m]aster'; sleep 1; tail -n 3 $REMOTE_DIR/logs/nginx.log | grep -i emerg"
LOG=$REMOTE_DIR/logs/loadtest_check.log
ARGS=$(printf '%q ' "$@")
n1 "cd $REMOTE_DIR && ulimit -n 65536 && setsid nohup $REMOTE_DIR/venv/bin/python -u $REMOTE_DIR/code/loadtest_check.py $ARGS >> $LOG 2>&1 < /dev/null & echo started"
start=$(n1 "wc -l < $LOG"); seen=$(( start > 3 ? start - 3 : 0 ))
while :; do
  sleep 10
  out=$(n1 "tail -n +$((seen+1)) $LOG; pgrep -f 'code/[l]oadtest_check.py' > /dev/null && echo __RUNNING__ || echo __STOPPED__")
  body=$(echo "$out" | grep -v '^__\(RUNNING\|STOPPED\)__$')
  [ -n "$body" ] && { echo "$body"; seen=$((seen + $(echo "$body" | wc -l))); }
  echo "$out" | tail -1 | grep -q __STOPPED__ && break
done
mkdir -p "$HERE/../results/logs" "$HERE/../results/loadtest_check_runs"
scp -q $SSHO -P $N1_SSH_PORT root@$N1_IP:$REMOTE_DIR/results/loadtest_check.json "$HERE/../results/" && echo "fetched results/loadtest_check.json"
scp -q $SSHO -P $N1_SSH_PORT "root@$N1_IP:$REMOTE_DIR/results/ltc_*.json" "$HERE/../results/loadtest_check_runs/"
scp -q $SSHO -P $N1_SSH_PORT "root@$N1_IP:$REMOTE_DIR/logs/loadtest_check.log" "root@$N1_IP:$REMOTE_DIR/logs/fake_llm.log" "$HERE/../results/logs/"
