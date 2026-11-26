#!/bin/bash
# Cap sweep: fixed N users, 4 values of "questions one replica works on at the same time" (vLLM --max-num-seqs).
# For each cap: restart the Data Parallel cluster with that cap, run the load generator in single mode
# (15 s warm-up + 60 s measured), result -> results/cap_<cap>.json. At the end the cluster is put back to cap 256.
#   usage: run_cap_sweep.sh <N users> <cap> [<cap> ...]
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
N=$1; shift
mkdir -p "$HERE/../results/logs"
for CAP in "$@"; do
  echo "#### cap $CAP: cluster up  ($(date -u +%H:%M:%S))"
  "$HERE/cluster.sh" up --mode dp --cap "$CAP" 2>&1 | tee "$HERE/../results/logs/up_dp_cap_$CAP.log" | tail -4
  grep -q "== DONE" "$HERE/../results/logs/up_dp_cap_$CAP.log" || { echo "#### cap $CAP: cluster FAILED, skipping"; continue; }
  cp "$HERE/../results/startup_dp.json" "$HERE/../results/startup_dp_cap_$CAP.json"
  echo "#### cap $CAP: load N=$N"
  "$HERE/run_loadgen.sh" "cap_$CAP" single --users "$N" --duration 75 --warmup 15 2>&1 | tee "$HERE/../results/logs/run_cap_$CAP.log" | grep -v "^ *t=" | tail -15
done
echo "#### back to Data Parallel cap 256"
"$HERE/cluster.sh" up --mode dp --cap 256 2>&1 | tee "$HERE/../results/logs/up_dp_256_after_cap_sweep.log" | tail -4
"$HERE/cluster.sh" status 2>&1 | tee "$HERE/../results/logs/status_after_cap_sweep.log"
echo "#### SWEEP DONE"
