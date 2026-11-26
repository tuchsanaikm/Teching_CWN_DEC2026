#!/usr/bin/env bash
# Run the capacity search in the background (run ON the rented machine):  run_capacity_bg.sh <name>
# Log -> results/<name>_log.txt (ends with DONE), GPU memory/util every 2 s -> results/<name>_vram.csv
set -u
NAME=${1:?name}
BASE=/workspace/lab6; R=$BASE/results
cd "$BASE/code"
[ -e "$R/$NAME.json" ] && { echo "result $NAME already exists"; exit 1; }
# what exactly was measured: layout (lb method, slow GPU), the nginx.conf in use, state of every server
cp "$BASE/logs/cluster.state" "$R/${NAME}_cluster.state" 2>/dev/null
cp "$BASE/code/nginx.conf" "$R/${NAME}_nginx.conf"
bash "$BASE/code/cluster.sh" status > "$R/${NAME}_cluster_status.txt" 2>&1
wc -l < "$BASE/logs/nginx/error.log" > "$R/${NAME}_nginx_error.start" 2>/dev/null || echo 0 > "$R/${NAME}_nginx_error.start"
nohup setsid bash -c "
  ( while :; do echo \"\$(date -u +%T),\$(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits | tr '\n' ',' )\"; sleep 2; done ) > $R/${NAME}_vram.csv &
  S=\$!
  python loadgen.py capacity --name $NAME > $R/${NAME}_log.txt 2>&1
  kill \$S
" > /dev/null 2>&1 < /dev/null &
echo "started $NAME"
