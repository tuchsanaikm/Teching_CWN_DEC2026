#!/bin/bash
# Runs ON a rented machine; called by cluster.sh over SSH. Never prints the API key.
# usage: node.sh start <dp|mp> <cap> | nginx-start <dp|mp> | nginx-reload | stop | kill [epoch] | status | ready <dp|mp> | lbcheck
D=/workspace/lab7
ROLE=$(cat $D/role)
MODEL=$(cat $D/runtime/model 2>/dev/null)
SERVED=$(cat $D/runtime/served_name 2>/dev/null)
CTX=$(cat $D/runtime/max_model_len 2>/dev/null)
export UDOCKER_DIR=$D/udocker
ulimit -n 65536 2>/dev/null
N2=181.173.127.113

endpoints() { # mode -> the replica addresses as machine 1 reaches them: "name url"
  if [ "$1" = dp ]; then
    echo "n1-gpu0 http://127.0.0.1:8001"; echo "n1-gpu1 http://127.0.0.1:8002"
    echo "n2-gpu0 http://$N2:27860";      echo "n2-gpu1 http://$N2:27596"
  else
    echo "n1-gpu0+1 http://127.0.0.1:8001"; echo "n2-gpu0+1 http://$N2:27860"
  fi
}

start_replica() { # gpus port tensor_parallel cap
  local host=0.0.0.0; [ "$ROLE" = n1 ] && host=127.0.0.1   # machine 1 replicas are reached only by NGINX
  date +%s.%N > $D/runtime/start_$2.t
  # the key goes in through the environment (VLLM_API_KEY), so it is not visible in `ps`
  # NCCL_CUMEM_HOST_ENABLE=0: with 2 GPUs (Model Parallel) both workers must use the same /dev/shm path;
  # on machine 1 one worker fell back to /dev/shm and the other did not, and the start failed.
  NCCL_CUMEM_HOST_ENABLE=0 CUDA_VISIBLE_DEVICES=$1 VLLM_API_KEY=$(cat $D/runtime/api_key) HF_HOME=$D/hf HF_HUB_OFFLINE=1 \
  setsid nohup $D/venv/bin/vllm serve "$MODEL" \
      --served-model-name "$SERVED" --max-model-len "$CTX" \
      --max-num-seqs "$4" --tensor-parallel-size "$3" \
      --gpu-memory-utilization 0.90 --host $host --port "$2" \
      > $D/logs/replica_$2.log 2>&1 < /dev/null &
  local pid=$!; echo $pid > $D/runtime/replica_$2.pid
  # small local watcher: writes how many seconds this replica needed until /health answered 200
  rm -f $D/runtime/up_$2.s
  setsid nohup bash -c "t0=\$(cat $D/runtime/start_$2.t); while kill -0 $pid 2>/dev/null; do
      [ \"\$(curl -s -o /dev/null -m 2 -w '%{http_code}' http://127.0.0.1:$2/health)\" = 200 ] && { python3 -c \"import time;print(round(time.time()-\$t0,1))\" > $D/runtime/up_$2.s; break; }; sleep 0.5; done" > /dev/null 2>&1 < /dev/null &
  echo "started replica port=$2 gpu=$1 tp=$3 max-num-seqs=$4 pid=$pid"
}

case "$1" in
  start)
    echo "$2 $3" > $D/runtime/mode
    if [ "$2" = dp ]; then start_replica 0 8001 1 "$3"; start_replica 1 8002 1 "$3"
    else start_replica 0,1 8001 2 "$3"; fi ;;

  nginx-start)
    [ "$2" = dp ] && P=shop_dp || P=shop_mp
    echo "map \$host \$pool { default $P; }" > $D/runtime/pool.conf
    ( umask 077; echo "\"Bearer $(cat $D/runtime/api_key)\" 1;" > $D/runtime/apikey.map )
    setsid nohup udocker --allow-root run \
        --volume=$D/code/nginx.conf:/etc/nginx/nginx.conf \
        --volume=$D/runtime:/etc/nginx/runtime \
        lab7nginx nginx -g 'daemon off;' > $D/logs/nginx.log 2>&1 < /dev/null &
    sleep 2; pgrep -f 'nginx: master' > /dev/null && echo "nginx started (pool $P)" || { echo "nginx FAILED"; tail -5 $D/logs/nginx.log; exit 1; } ;;

  nginx-reload)   # machine 1: take a changed nginx.conf into use without stopping the replicas (SIGHUP)
    m=$(pgrep -f 'nginx: master' | head -1); [ -z "$m" ] && { echo "nginx is not running"; exit 1; }
    before=$(pgrep -f 'nginx: worker' | sort | tr '\n' ' ')
    n0=$(wc -l < $D/logs/nginx.log); kill -HUP $m; sleep 3
    if tail -n +$((n0+1)) $D/logs/nginx.log | grep -F '[emerg]'; then echo "nginx reload FAILED (old configuration kept)"; exit 1; fi
    after=$(pgrep -f 'nginx: worker' | sort | tr '\n' ' ')
    [ "$before" != "$after" ] && echo "nginx reloaded (new workers)" || { echo "nginx reload: workers did not change"; exit 1; } ;;

  kill)   # sudden failure of this machine's replicas: SIGKILL, no clean shutdown, nothing gets to finish.
          # $2 = optional time (epoch seconds, may have decimals) to do it at; NGINX on machine 1 is left alone.
    if [ -n "${2:-}" ]; then python3 -c "import time,sys; time.sleep(max(0.0, float(sys.argv[1]) - time.time()))" "$2"; fi
    t_a=$(date +%s.%N); n=0
    for f in $D/runtime/replica_*.pid; do [ -f "$f" ] || continue
      kill -KILL -- -$(cat $f) 2>/dev/null && n=$((n+1))        # the whole process group: API server + engine
    done
    pkill -KILL -f "vllm serve" 2>/dev/null
    t_b=$(date +%s.%N)
    echo "$t_a $t_b" > $D/runtime/killed.t
    echo "$ROLE KILLED $n replicas at $t_a (done $t_b)" ;;

  stop)
    pkill -f 'nginx: master' 2>/dev/null; pkill -f 'nginx: worker' 2>/dev/null
    for f in $D/runtime/replica_*.pid; do [ -f "$f" ] && kill -TERM -- -$(cat $f) 2>/dev/null; rm -f "$f"; done
    pkill -f "vllm serve" 2>/dev/null
    for i in $(seq 1 30); do pgrep -f "vllm serve|nginx: master" >/dev/null || break; sleep 1; done
    pkill -9 -f "vllm serve" 2>/dev/null
    # wait until GPU memory is released
    for i in $(seq 1 20); do [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader | wc -l)" = 0 ] && break; sleep 1; done
    rm -f $D/runtime/mode $D/runtime/up_*.s $D/runtime/killed.t
    echo "$ROLE stopped" ;;

  status)
    echo "[$ROLE] mode/cap: $(cat $D/runtime/mode 2>/dev/null || echo '(down)')"
    for f in $D/runtime/replica_*.pid; do [ -f "$f" ] || continue
      p=$(basename $f .pid); p=${p#replica_}
      kill -0 $(cat $f) 2>/dev/null && s=running || s=DEAD
      h=$(curl -s -o /dev/null -m 3 -w '%{http_code}' http://127.0.0.1:$p/health)
      echo "[$ROLE] replica port $p: process $s, /health $h"
    done
    [ "$ROLE" = n1 ] && echo "[$ROLE] nginx: $(pgrep -f 'nginx: master' >/dev/null && echo running || echo not running)"
    nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader | sed "s/^/[$ROLE] gpu /" ;;

  ready)   # machine 1 only: asks every replica of the mode for /v1/models with the key
    K=$(cat $D/runtime/api_key); ok=0; n=0
    while read -r name url; do n=$((n+1))
      c=$(curl -s -o /dev/null -m 4 -w '%{http_code}' -H "Authorization: Bearer $K" $url/v1/models)
      [ "$c" = 200 ] && { ok=$((ok+1)); [ -f $D/runtime/ready_$name.t ] || date +%s.%N > $D/runtime/ready_$name.t; }
      echo "  $name $c"
    done < <(endpoints "$2")
    echo "READY $ok/$n" ;;

  alive)   # are the replica processes still alive? (to fail fast instead of waiting forever)
    for f in $D/runtime/replica_*.pid; do [ -f "$f" ] || continue
      kill -0 $(cat $f) 2>/dev/null || { echo "DEAD $(basename $f)"; tail -n 15 $D/logs/$(basename $f .pid).log; }
    done ;;

  uptimes) # seconds each replica of this machine needed to become ready
    for f in $D/runtime/up_*.s; do [ -f "$f" ] || continue; p=$(basename $f .s); echo "$ROLE:${p#up_} $(cat $f)"; done ;;

  lbcheck) # through NGINX: with key -> 200, without key -> 401
    K=$(cat $D/runtime/api_key)
    echo "LB with_key=$(curl -s -o /dev/null -m 5 -w '%{http_code}' -H "Authorization: Bearer $K" http://127.0.0.1:8080/v1/models) no_key=$(curl -s -o /dev/null -m 5 -w '%{http_code}' http://127.0.0.1:8080/v1/models)" ;;
esac
