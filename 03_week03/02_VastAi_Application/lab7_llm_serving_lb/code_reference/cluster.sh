#!/bin/bash
# One command to (re)start the whole 2-machine chatbot. Run on the control machine.
#
#   cluster.sh up [--mode dp|mp] [--cap N]   start everything, return only when every replica is ready
#        --mode dp  Data Parallel  : 4 replicas, 1 GPU each              (default)
#        --mode mp  Model Parallel : 2 replicas, 1 per machine, the model split over that machine's 2 GPUs
#        --cap N    max questions one replica works on at the same time  (default 256; 1 = one at a time)
#   cluster.sh status                        what is running on both machines
#   cluster.sh kill <n1|n2> [--at EPOCH]     sudden failure: SIGKILL both replicas of that machine (NGINX keeps running)
#        --at EPOCH  do it at that clock time; it is scheduled detached on the machine itself, so the
#                    moment does not depend on how long the SSH call takes
#   cluster.sh nginx-reload                  push code/nginx.conf to machine 1 and reload NGINX (replicas keep running)
#   cluster.sh down                          stop NGINX and every replica
#
# The API key is made at random the first time (../.secrets/api_key) and reused on every later start.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/nodes.env"
KEYFILE=$HERE/../.secrets/api_key
SSHO="-i $SSH_KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=20 -o LogLevel=ERROR"
n1() { ssh $SSHO -p $N1_SSH_PORT root@$N1_IP "$@"; }
n2() { ssh $SSHO -p $N2_SSH_PORT root@$N2_IP "$@"; }
both() { n1 "$@" & n2 "$@" & wait; }

ensure_key() {
  if [ ! -s "$KEYFILE" ]; then
    mkdir -p "$(dirname "$KEYFILE")"; chmod 700 "$(dirname "$KEYFILE")"
    ( umask 077; echo "sk-shop-$(openssl rand -hex 24)" > "$KEYFILE" )
    echo "API key: created (first start)"
  else
    echo "API key: reusing the existing one"
  fi
}

push() { # ip ssh_port : code + settings + key (key travels on stdin, never on a command line)
  ssh $SSHO -p $2 root@$1 "mkdir -p $REMOTE_DIR/code $REMOTE_DIR/runtime $REMOTE_DIR/logs; chmod 700 $REMOTE_DIR/runtime;
     echo '$MODEL' > $REMOTE_DIR/runtime/model; echo '$SERVED_NAME' > $REMOTE_DIR/runtime/served_name; echo '$MAX_MODEL_LEN' > $REMOTE_DIR/runtime/max_model_len;
     umask 077; cat > $REMOTE_DIR/runtime/api_key" < "$KEYFILE"
  scp -q $SSHO -P $2 "$HERE/node.sh" "$HERE/nginx.conf" root@$1:$REMOTE_DIR/code/
}

cmd=${1:-}; shift || true
case "$cmd" in
  up)
    MODE=dp; CAP=256
    while [ $# -gt 0 ]; do case "$1" in
      --mode) MODE=$2; shift 2;; --cap) CAP=$2; shift 2;;
      *) echo "unknown option $1"; exit 2;; esac; done
    case "$MODE" in dp) NREP=4;; mp) NREP=2;; *) echo "--mode must be dp or mp"; exit 2;; esac
    [[ "$CAP" =~ ^[1-9][0-9]*$ ]] || { echo "--cap must be a positive integer"; exit 2; }
    T0=$(date +%s)
    echo "== up: mode=$MODE ($NREP replicas)  cap=$CAP questions per replica"
    ensure_key
    push $N1_IP $N1_SSH_PORT & push $N2_IP $N2_SSH_PORT & wait
    both "bash $REMOTE_DIR/code/node.sh stop; rm -f $REMOTE_DIR/runtime/ready_*.t $REMOTE_DIR/runtime/start_*.t $REMOTE_DIR/runtime/replica_*.pid"
    both "bash $REMOTE_DIR/code/node.sh start $MODE $CAP"
    n1 "bash $REMOTE_DIR/code/node.sh nginx-start $MODE" || exit 1
    echo "== waiting for $NREP replicas (checked from machine 1, the same way NGINX reaches them)"
    while :; do
      out=$(n1 "bash $REMOTE_DIR/code/node.sh ready $MODE")
      el=$(( $(date +%s) - T0 ))
      echo "  t=${el}s $(echo "$out" | tail -1)  [$(echo "$out" | grep -v READY | tr -s ' \n' ' ')]"
      echo "$out" | grep -q "READY $NREP/$NREP" && break
      dead=$(both "bash $REMOTE_DIR/code/node.sh alive")
      [ -n "$dead" ] && { echo "$dead"; echo "== FAILED: a replica process died"; exit 1; }
      [ $el -gt 1200 ] && { echo "== FAILED: timeout"; exit 1; }
      sleep 5
    done
    lb=$(n1 "bash $REMOTE_DIR/code/node.sh lbcheck"); echo "  $lb"
    echo "$lb" | grep -q "with_key=200 no_key=401" || { echo "== FAILED: NGINX check"; exit 1; }
    # per-replica start-up time, measured on each machine (process start -> /health 200)
    sleep 1
    mkdir -p "$HERE/../results"
    both "bash $REMOTE_DIR/code/node.sh uptimes" | sort | python3 -c '
import sys, json
per = {a: round(float(b), 1) for a, b in (l.split() for l in sys.stdin if l.strip())}
mode, cap, total, out = sys.argv[1:5]
json.dump({"mode": mode, "cap": int(cap), "up_total_s": int(total), "replica_ready_s": per}, open(out, "w"), indent=1)
print("  replica start-up seconds (machine:port):", per)' "$MODE" "$CAP" "$(( $(date +%s) - T0 ))" "$HERE/../results/startup_$MODE.json"
    echo "== DONE in $(( $(date +%s) - T0 ))s : http://$N1_IP:$N1_LB_PUBLIC_PORT/v1/chat/completions  (model $SERVED_NAME)"
    ;;
  status)
    both "bash $REMOTE_DIR/code/node.sh status" | sort
    m=$(n1 "cut -d' ' -f1 $REMOTE_DIR/runtime/mode 2>/dev/null")
    [ -n "$m" ] && { n1 "bash $REMOTE_DIR/code/node.sh ready $m; bash $REMOTE_DIR/code/node.sh lbcheck"; }
    ;;
  kill)
    NODE=${1:-}; shift || true; AT=
    while [ $# -gt 0 ]; do case "$1" in --at) AT=$2; shift 2;; *) echo "unknown option $1"; exit 2;; esac; done
    case "$NODE" in n1|n2) ;; *) echo "usage: cluster.sh kill <n1|n2> [--at EPOCH]"; exit 2;; esac
    if [ -n "$AT" ]; then
      [[ "$AT" =~ ^[0-9]+(\.[0-9]+)?$ ]] || { echo "--at must be epoch seconds"; exit 2; }
      $NODE "{ setsid nohup bash $REMOTE_DIR/code/node.sh kill $AT > $REMOTE_DIR/logs/kill.log 2>&1 < /dev/null & } ; echo \"$NODE: kill scheduled for $AT (machine clock now \$(date +%s.%N))\""
    else
      $NODE "bash $REMOTE_DIR/code/node.sh kill | tee $REMOTE_DIR/logs/kill.log"
    fi
    ;;
  nginx-reload)
    scp -q $SSHO -P $N1_SSH_PORT "$HERE/node.sh" "$HERE/nginx.conf" root@$N1_IP:$REMOTE_DIR/code/
    scp -q $SSHO -P $N2_SSH_PORT "$HERE/node.sh" root@$N2_IP:$REMOTE_DIR/code/
    n1 "bash $REMOTE_DIR/code/node.sh nginx-reload && bash $REMOTE_DIR/code/node.sh lbcheck"
    ;;
  down)
    both "bash $REMOTE_DIR/code/node.sh stop"
    ;;
  *) sed -n '2,16p' "$0"; exit 2;;
esac
