#!/bin/bash
# Single-node cluster manager for ReceiptDesk LAB 7 (runs ON the rented 2x RTX 4090 machine).
# usage:
#   node_receipt.sh up <dp1|dp2> <cap>
#   node_receipt.sh kill-port <port> [epoch]
#   node_receipt.sh stop
#   node_receipt.sh status
set -u
D=/workspace/receipt_lb
MODEL=$D/model_merged
SERVED=receipt-vlm
CTX=4096
export UDOCKER_DIR=$D/udocker
ulimit -n 65536 2>/dev/null || true

start_replica() { # gpu port cap
  date +%s.%N > $D/runtime/start_$2.t
  NCCL_CUMEM_HOST_ENABLE=0 CUDA_VISIBLE_DEVICES=$1 VLLM_API_KEY=$(cat $D/runtime/api_key) HF_HOME=$D/hf \
  setsid nohup $D/venv/bin/vllm serve "$MODEL" \
      --served-model-name "$SERVED" \
      --max-model-len "$CTX" \
      --max-num-seqs "$3" \
      --gpu-memory-utilization 0.90 \
      --limit-mm-per-prompt '{"image": 1}' \
      --host 127.0.0.1 --port "$2" \
      > $D/logs/replica_$2.log 2>&1 < /dev/null &
  local pid=$!; echo $pid > $D/runtime/replica_$2.pid
  rm -f $D/runtime/up_$2.s
  setsid nohup bash -c "t0=\$(cat $D/runtime/start_$2.t); while kill -0 $pid 2>/dev/null; do
      [ \"\$(curl -s -o /dev/null -m 2 -w '%{http_code}' http://127.0.0.1:$2/health)\" = 200 ] && { python3 -c \"import time;print(round(time.time()-\$t0,1))\" > $D/runtime/up_$2.s; break; }; sleep 0.5; done" > /dev/null 2>&1 < /dev/null &
  echo "started replica port=$2 gpu=$1 cap=$3 pid=$pid"
}

start_nginx() { # dp1|dp2
  local P="receipt_$1"
  echo "map \$host \$pool { default $P; }" > $D/runtime/pool.conf
  ( umask 077; echo "\"Bearer $(cat $D/runtime/api_key)\" 1;" > $D/runtime/apikey.map )
  pkill -f 'nginx: master' 2>/dev/null || true
  pkill -f 'nginx: worker' 2>/dev/null || true
  sleep 1
  setsid nohup $D/venv/bin/udocker --allow-root run \
      --volume=$D/code/nginx.conf:/etc/nginx/nginx.conf \
      --volume=$D/runtime:/etc/nginx/runtime \
      receiptnginx nginx -g 'daemon off;' > $D/logs/nginx.log 2>&1 < /dev/null &
  sleep 2
  pgrep -f 'nginx: master' > /dev/null && echo "nginx started (pool $P)" || { echo "nginx FAILED"; tail -15 $D/logs/nginx.log; exit 1; }
}

stop_all() {
  pkill -f 'nginx: master' 2>/dev/null || true
  pkill -f 'nginx: worker' 2>/dev/null || true
  for f in $D/runtime/replica_*.pid; do
    [ -f "$f" ] && kill -TERM -- -$(cat $f) 2>/dev/null || true
    rm -f "$f"
  done
  pkill -f "vllm serve" 2>/dev/null || true
  for i in $(seq 1 25); do pgrep -f "vllm serve|nginx: master" >/dev/null || break; sleep 1; done
  pkill -9 -f "vllm serve" 2>/dev/null || true
  for i in $(seq 1 20); do [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader | wc -l)" = 0 ] && break; sleep 1; done
  rm -f $D/runtime/mode $D/runtime/up_*.s $D/runtime/killed.t
  echo "stopped all"
}

wait_ready() { # ports...
  local K=$(cat $D/runtime/api_key)
  local ports=("$@")
  for i in $(seq 1 180); do
    local ok=0
    for p in "${ports[@]}"; do
      local c=$(curl -s -o /dev/null -m 3 -w '%{http_code}' -H "Authorization: Bearer $K" http://127.0.0.1:$p/v1/models)
      [ "$c" = 200 ] && ok=$((ok+1))
    done
    if [ "$ok" = "${#ports[@]}" ]; then
      echo "ALL READY ($ok/${#ports[@]})"
      for p in "${ports[@]}"; do
        echo "  port $p ready in $(cat $D/runtime/up_$p.s 2>/dev/null || echo '?') s"
      done
      return 0
    fi
    for p in "${ports[@]}"; do
      local pid=$(cat $D/runtime/replica_$p.pid 2>/dev/null || true)
      if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then
        echo "DEAD replica port $p:"
        tail -n 30 $D/logs/replica_$p.log
        return 1
      fi
    done
    sleep 2
  done
  echo "TIMEOUT waiting for replicas"
  return 1
}

write_targets() { # dp1|dp2
  python3 - "$1" <<'P'
import json, sys
m = sys.argv[1]
reps = {
  "dp1": [{"name": "gpu0", "metrics": "http://127.0.0.1:8001/metrics"}],
  "dp2": [{"name": "gpu0", "metrics": "http://127.0.0.1:8001/metrics"},
          {"name": "gpu1", "metrics": "http://127.0.0.1:8002/metrics"}],
}[m]
t = {
  "url": "http://127.0.0.1:8080",
  "model": "receipt-vlm",
  "key_file": "/workspace/receipt_lb/runtime/api_key",
  "replicas": reps,
  "gpu_sources": [{"machine": "local"}],
}
json.dump(t, open("/workspace/receipt_lb/runtime/targets.json", "w"), indent=1)
P
}

case "$1" in
  up)
    MODE=$2; CAP=$3
    stop_all
    echo "$MODE $CAP" > $D/runtime/mode
    case "$MODE" in
      dp1) start_replica 0 8001 "$CAP"; PORTS=(8001) ;;
      dp2) start_replica 0 8001 "$CAP"; start_replica 1 8002 "$CAP"; PORTS=(8001 8002) ;;
      *) echo "unknown mode $MODE"; exit 1 ;;
    esac
    start_nginx "$MODE"
    write_targets "$MODE"
    wait_ready "${PORTS[@]}"
    K=$(cat $D/runtime/api_key)
    echo "LB check: with_key=$(curl -s -o /dev/null -m 5 -w '%{http_code}' -H "Authorization: Bearer $K" http://127.0.0.1:8080/v1/models) no_key=$(curl -s -o /dev/null -m 5 -w '%{http_code}' http://127.0.0.1:8080/v1/models)"
    ;;
  kill-port)
    PORT=$2; EPOCH=${3:-}
    if [ -n "$EPOCH" ]; then
      python3 -c "import time,sys; time.sleep(max(0.0, float(sys.argv[1]) - time.time()))" "$EPOCH"
    fi
    t_a=$(date +%s.%N)
    if [ -f "$D/runtime/replica_${PORT}.pid" ]; then
      kill -KILL -- -$(cat "$D/runtime/replica_${PORT}.pid") 2>/dev/null || true
    fi
    pkill -KILL -f -- "--port ${PORT}" 2>/dev/null || true
    t_b=$(date +%s.%N)
    echo "$t_a $t_b" > $D/runtime/killed.t
    echo "KILLED port $PORT at $t_a (done $t_b)"
    ;;
  stop)
    stop_all
    ;;
  status)
    echo "mode/cap: $(cat $D/runtime/mode 2>/dev/null || echo '(down)')"
    for f in $D/runtime/replica_*.pid; do [ -f "$f" ] || continue
      p=$(basename $f .pid); p=${p#replica_}
      kill -0 $(cat $f) 2>/dev/null && s=running || s=DEAD
      h=$(curl -s -o /dev/null -m 3 -w '%{http_code}' http://127.0.0.1:$p/health)
      echo "replica port $p: $s, /health=$h"
    done
    echo "nginx: $(pgrep -f 'nginx: master' >/dev/null && echo running || echo down)"
    nvidia-smi --query-gpu=index,name,temperature.gpu,memory.used,utilization.gpu --format=csv,noheader
    ;;
esac
