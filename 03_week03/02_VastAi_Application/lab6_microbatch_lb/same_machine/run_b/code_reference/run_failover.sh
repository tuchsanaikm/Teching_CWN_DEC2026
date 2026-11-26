#!/usr/bin/env bash
# One failure run (run ON the rented machine):  run_failover.sh <name> <on|off> [users] [kill-gpu] [kill-at] [seconds]
#   opens layout 4 (2 GPUs x 4 servers, micro-batching, Round Robin) with NGINX --failover <on|off>,
#   shoots one level and kills every server of the GPU in the middle of it.
# Runs in the background. Log -> results/<name>_log.txt (ends with FINISHED), plus the nginx.conf in use, the state
# before / after, the NGINX error lines and the access-log lines of the run.
set -u
NAME=${1:?name}; FO=${2:?on|off}; USERS=${3:-60}; KGPU=${4:-1}; AT=${5:-20}; SECS=${6:-60}
BASE=/workspace/lab6; R=$BASE/results; C=$BASE/code; NL=$BASE/logs/nginx
[ -e "$R/$NAME.json" ] && { echo "result $NAME already exists"; exit 1; }
nohup setsid bash -c "
  cd $C
  bash cluster.sh up --gpus 2 --per-gpu 4 --mode micro --lb rr --failover $FO || { echo UP_FAILED; echo FINISHED; exit 1; }
  cp $C/nginx.conf $R/${NAME}_nginx.conf
  bash cluster.sh status > $R/${NAME}_cluster_status.txt 2>&1
  E0=\$(wc -l < $NL/error.log 2>/dev/null || echo 0); A0=\$(wc -l < $NL/access.log 2>/dev/null || echo 0)
  ( while :; do echo \"\$(date -u +%T),\$(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits | tr '\n' ',' )\"; sleep 2; done ) > $R/${NAME}_vram.csv &
  S=\$!
  python loadgen.py single --name $NAME --users $USERS --duration $SECS --event-at $AT --event-cmd 'bash cluster.sh kill-gpu $KGPU'
  kill \$S
  sleep 2
  cp $BASE/logs/cluster.state $R/${NAME}_cluster.state
  bash cluster.sh status > $R/${NAME}_cluster_status_after.txt 2>&1
  tail -n +\$((E0 + 1)) $NL/error.log > $R/${NAME}_nginx_error.log
  tail -n +\$((A0 + 1)) $NL/access.log > $R/${NAME}_nginx_access.log
  echo FINISHED
" > "$R/${NAME}_log.txt" 2>&1 < /dev/null &
echo "started $NAME (failover=$FO users=$USERS kill gpu$KGPU at ${AT}s of ${SECS}s)"
