#!/usr/bin/env bash
# LAB 6.3 - the whole measurement in one background job (run ON the rented machine):
#     nohup setsid bash run_lb3.sh > /workspace/lab6/results/run_lb3.log 2>&1 < /dev/null &
# 2 cases x 3 balancing methods, one capacity search each, always in the order rr -> lc -> p2c:
#     equal : both GPUs at normal speed            slow : GPU 1 is 3x slower (--slow-gpu 1 --slow-factor 3)
# Layout of every run: 2 GPUs x 4 servers, micro-batching (max 32 images, wait max 5 ms).
# Result name = <method>_<case>. Files in results/ for every name:
#   <name>.json                 loadgen result            <name>_log.txt            loadgen output
#   <name>_nginx.conf           the nginx.conf mounted into the running NGINX
#   <name>_nginx_running.conf   what NGINX itself reports as its config (nginx -T), checked by cluster.sh up
#   <name>_cluster_up.txt       output of cluster.sh up   <name>_cluster.state      layout
#   <name>_cluster_status.txt / _status_after.txt   state of every server before / after the search
#   <name>_nginx_error.log      lines NGINX wrote to error.log during the search (empty = nothing)
#   <name>_vram.csv             GPU memory / utilisation every 2 s
# A result that already exists is skipped (so the job can be started again after a break). Ends with ALL DONE.
set -u
BASE=/workspace/lab6; R=$BASE/results; CODE=$BASE/code; NLOG=$BASE/logs/nginx
mkdir -p "$R"; cd "$CODE"
for CASE in equal slow; do
  for LB in rr lc p2c; do
    NAME=${LB}_${CASE}
    if [ -e "$R/$NAME.json" ] && grep -q '"finished": true' "$R/$NAME.json"; then echo "[run_lb3] $NAME exists, skipped"; continue; fi
    rm -f "$R/$NAME.json"
    SLOW=""; [ "$CASE" = slow ] && SLOW="--slow-gpu 1 --slow-factor 3"
    echo "[run_lb3] $(date -u +%FT%TZ) $NAME: cluster up"
    ok=0
    for try in 1 2; do
      bash cluster.sh up --gpus 2 --per-gpu 4 --mode micro --lb "$LB" $SLOW > "$R/${NAME}_cluster_up.txt" 2>&1 && { ok=1; break; }
      echo "[run_lb3] $NAME: cluster up failed (try $try)"; tail -5 "$R/${NAME}_cluster_up.txt"
    done
    [ "$ok" = 1 ] || { echo "[run_lb3] $NAME: GIVING UP"; echo "ALL FAILED"; exit 1; }
    cp "$BASE/logs/cluster.state" "$R/${NAME}_cluster.state"
    cp "$CODE/nginx.conf" "$R/${NAME}_nginx.conf"
    cp "$NLOG/running.conf" "$R/${NAME}_nginx_running.conf"
    bash cluster.sh status > "$R/${NAME}_cluster_status.txt" 2>&1
    E0=$(wc -l < "$NLOG/error.log" 2>/dev/null || echo 0)
    ( while :; do echo "$(date -u +%T),$(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits | tr '\n' ',' )"; sleep 2; done ) > "$R/${NAME}_vram.csv" &
    S=$!
    echo "[run_lb3] $(date -u +%FT%TZ) $NAME: capacity search"
    python loadgen.py capacity --name "$NAME" > "$R/${NAME}_log.txt" 2>&1
    kill $S 2>/dev/null
    tail -n +$((E0 + 1)) "$NLOG/error.log" > "$R/${NAME}_nginx_error.log" 2>/dev/null
    bash cluster.sh status > "$R/${NAME}_status_after.txt" 2>&1
    cmp -s "$CODE/nginx.conf" "$R/${NAME}_nginx.conf" || echo "[run_lb3] WARNING $NAME: nginx.conf changed during the search"
    echo "[run_lb3] $(date -u +%FT%TZ) $NAME: $(grep '^CAPACITY' "$R/${NAME}_log.txt" || echo 'NO CAPACITY LINE')"
  done
done
bash cluster.sh down
echo "ALL DONE"
