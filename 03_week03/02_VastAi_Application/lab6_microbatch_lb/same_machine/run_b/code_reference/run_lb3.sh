#!/usr/bin/env bash
# LAB 6.3 - Round Robin vs Least Connections vs Power of Two Choices (run ON the rented machine):
#     run_lb3.sh [case ...]        cases: equal slow        default: equal slow
# Starts everything in the background (nohup setsid) and returns at once; poll results/lb3_progress.txt
# (last line ALL_FINISHED). For every case, in this order: p2c -> lc -> rr
#   cluster.sh up --gpus 2 --per-gpu 4 --mode micro --lb <method> [--slow-gpu 1 --slow-factor 3]
#   loadgen.py capacity --name <method>_<case>          (1 capacity search per method)
# Saved per result in results/: <name>.json  <name>_log.txt  <name>_up.log  <name>_nginx.conf (file on disk)
#   <name>_nginx_running.conf (nginx -T: what NGINX loaded)  <name>_cluster.state  <name>_cluster_status.txt
#   <name>_cluster_status_after.txt  <name>_vram.csv  <name>_nginx_error.log  <name>_upstream_counts.txt
# A result that already exists is skipped (so the script can be started again after a failure).
set -u
BASE=/workspace/lab6; R=$BASE/results; C=$BASE/code; NL=$BASE/logs/nginx
CASES=${*:-equal slow}
mkdir -p "$R"
nohup setsid bash -c "
  cd $C
  for CASE in $CASES; do
    for LB in p2c lc rr; do
      NAME=\${LB}_\${CASE}
      if [ -e $R/\$NAME.json ] && grep -q '\"finished\": true' $R/\$NAME.json; then echo \"\$(date -u +%T) \$NAME SKIP (exists)\"; continue; fi
      rm -f $R/\$NAME.json
      SLOW=''; [ \$CASE = slow ] && SLOW='--slow-gpu 1 --slow-factor 3'
      echo \"\$(date -u +%T) \$NAME UP\"
      bash cluster.sh up --gpus 2 --per-gpu 4 --mode micro --lb \$LB \$SLOW > $R/\${NAME}_up.log 2>&1 \
        || { echo \"\$(date -u +%T) \$NAME UP_FAILED\"; continue; }
      cp $C/nginx.conf $R/\${NAME}_nginx.conf
      cp $NL/running_config.txt $R/\${NAME}_nginx_running.conf
      cp $BASE/logs/cluster.state $R/\${NAME}_cluster.state
      bash cluster.sh status > $R/\${NAME}_cluster_status.txt 2>&1
      E0=\$(wc -l < $NL/error.log 2>/dev/null || echo 0); A0=\$(wc -l < $NL/access.log 2>/dev/null || echo 0)
      ( while :; do echo \"\$(date -u +%T),\$(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits | tr '\n' ',' )\"; sleep 2; done ) > $R/\${NAME}_vram.csv &
      S=\$!
      echo \"\$(date -u +%T) \$NAME LOADGEN\"
      python loadgen.py capacity --name \$NAME > $R/\${NAME}_log.txt 2>&1
      RC=\$?
      kill \$S
      sleep 2
      bash cluster.sh status > $R/\${NAME}_cluster_status_after.txt 2>&1
      tail -n +\$((E0 + 1)) $NL/error.log > $R/\${NAME}_nginx_error.log
      # every /v1/detect request NGINX handled in this run: how many per server, per status
      tail -n +\$((A0 + 1)) $NL/access.log | awk '/\\/v1\\/detect/ {for(i=1;i<=NF;i++){if(\$i ~ /^upstream=/)u=\$i}; c[u\" status=\"\$6]++} END {for(k in c) print c[k], k}' | sort -k2 > $R/\${NAME}_upstream_counts.txt
      echo \"\$(date -u +%T) \$NAME DONE rc=\$RC \$(grep '^CAPACITY' $R/\${NAME}_log.txt)\"
    done
  done
  bash cluster.sh down > /dev/null 2>&1
  echo \"\$(date -u +%T) ALL_FINISHED\"
" >> "$R/lb3_progress.txt" 2>&1 < /dev/null &
echo "started cases: $CASES"
