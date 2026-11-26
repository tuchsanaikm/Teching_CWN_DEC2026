#!/bin/bash
# What does a streaming-chat user see when one machine fails in the middle of a run?
#   run_fail_node.sh [name] [users] [kill_at_s] [node] [duration_s] [warmup_s]
#   run_fail_node.sh fail_node 305 30 n2 90 15
# 1 starts the load generator on machine 1 (detached there, run_loadgen.sh polls it)
# 2 reads the clock time of second 0 from its log and schedules "cluster.sh kill <node>" for second <kill_at_s>
#   (the kill waits detached on the machine itself; the clock difference between the machines is measured and added)
# 3 fetches the result, the kill log and the NGINX log lines of the run
# The cluster is left as it is after the failure (2 replicas dead): bring it back with  cluster.sh up --mode dp --cap 256
set -u
HERE=$(cd "$(dirname "$0")" && pwd); . "$HERE/nodes.env"
NAME=${1:-fail_node}; USERS=${2:-305}; KILL_AT=${3:-30}; NODE=${4:-n2}; DUR=${5:-90}; WARM=${6:-15}
RES=$HERE/../results; mkdir -p "$RES/logs"
SSHO="-i $SSH_KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=20 -o LogLevel=ERROR"
n1() { ssh -n $SSHO -p $N1_SSH_PORT root@$N1_IP "$@"; }
n2() { ssh -n $SSHO -p $N2_SSH_PORT root@$N2_IP "$@"; }
LOG=$REMOTE_DIR/logs/loadgen_$NAME.log

# clock of each machine minus the clock of this control machine (best of 5 samples over one open SSH connection)
offset() { # ip port
  python3 - "$SSH_KEY" "$1" "$2" <<'PY'
import subprocess, sys, time
key, ip, port = sys.argv[1:4]
p = subprocess.Popen(["ssh", "-i", key, "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR",
                      "-p", port, "root@" + ip, "python3 -u -c \"import sys,time\nfor l in sys.stdin: print(repr(time.time()), flush=True)\""],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
best = None
for _ in range(6):
    a = time.time(); p.stdin.write("x\n"); p.stdin.flush(); r = float(p.stdout.readline()); b = time.time()
    if best is None or b - a < best[0]:
        best = (b - a, r - (a + b) / 2)
    time.sleep(0.1)
p.stdin.close(); p.wait()
print("%.4f %.4f" % (best[1], best[0]))
PY
}
read O1 RTT1 < <(offset $N1_IP $N1_SSH_PORT)
read O2 RTT2 < <(offset $N2_IP $N2_SSH_PORT)
DCLK=$(python3 -c "print('%.3f' % ($O2 - $O1))")
[ "$NODE" = n1 ] && DNODE=0.000 || DNODE=$DCLK
echo "== clocks: machine 2 - machine 1 = ${DCLK}s (round trips ${RTT1}s / ${RTT2}s)"

n1 "rm -f $LOG $REMOTE_DIR/results/$NAME.json"
NGX0=$(n1 "wc -l < $REMOTE_DIR/logs/nginx.log")
"$HERE/run_loadgen.sh" "$NAME" single --users "$USERS" --duration "$DUR" --warmup "$WARM" --long-pct 0 --keep-requests \
    > "$RES/logs/run_$NAME.log" 2>&1 &
RL=$!
T0=
for i in $(seq 1 60); do
  T0=$(n1 "grep -m1 '^T0 ' $LOG 2>/dev/null | cut -d' ' -f2"); [ -n "$T0" ] && break; sleep 1
done
[ -z "$T0" ] && { echo "== FAILED: the load generator did not start"; kill $RL 2>/dev/null; exit 1; }
AT=$(python3 -c "print('%.3f' % ($T0 + $KILL_AT + $DNODE))")
left=$(python3 -c "import time; print('%.1f' % ($T0 + $KILL_AT - time.time() - $O1))")
echo "== second 0 = $T0 (machine 1 clock); kill of $NODE at second $KILL_AT = $AT on its own clock, ${left}s from now"
python3 -c "import sys; sys.exit(0 if $left > 8 else 1)" || { echo "== FAILED: too late to schedule the kill"; kill $RL 2>/dev/null; exit 1; }
"$HERE/cluster.sh" kill "$NODE" --at "$AT"
wait $RL
tail -n 12 "$RES/logs/run_$NAME.log"
KL=$($NODE "cat $REMOTE_DIR/logs/kill.log; cat $REMOTE_DIR/runtime/killed.t")
echo "$KL" | head -1
# NGINX lines written during the run (access log: which replica, how many tries; error log: why)
ssh -n $SSHO -p $N1_SSH_PORT root@$N1_IP "tail -n +$((NGX0+1)) $REMOTE_DIR/logs/nginx.log | gzip -c" > "$RES/logs/nginx_$NAME.log.gz"
python3 - "$RES/${NAME}_event.json" "$NODE" "$T0" "$KILL_AT" "$AT" "$DCLK" "$DNODE" "$(echo "$KL" | tail -1)" <<'PY'
import json, sys
out, node, t0, at_s, at, dclk, dnode, killed = sys.argv[1:9]
ka, kb = (float(x) for x in killed.split())
json.dump({"node": node, "t0_epoch_machine1": float(t0), "kill_planned_s": float(at_s), "kill_planned_epoch_node_clock": float(at),
           "clock_machine2_minus_machine1_s": float(dclk),
           "kill_start_s": round(ka - float(dnode) - float(t0), 3), "kill_done_s": round(kb - float(dnode) - float(t0), 3),
           "how": "SIGKILL to the process group of every replica of the machine (cluster.sh kill)"}, open(out, "w"), indent=1)
print("== kill happened at second %.3f .. %.3f of the run" % (ka - float(dnode) - float(t0), kb - float(dnode) - float(t0)))
PY
"$HERE/cluster.sh" status > "$RES/logs/status_after_$NAME.log" 2>&1; cat "$RES/logs/status_after_$NAME.log"
