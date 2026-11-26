#!/bin/bash
# one progress line per call (used for the 2-3 minute reports); appends to results/progress.log
D=$(dirname "$0"); OUT=${1:-/workspace/run}
L=$($D/sshn 1 "python3 - <<'PY'
import json,glob
r=[json.loads(l) for l in open('$OUT/worker0_steps.jsonl')]
if r:
    x=r[-1]; k=r[-20:]
    c=sum(i['t_compute'] for i in k)/len(k); m=sum(i['t_comm'] for i in k)/len(k)
    print(f\"step {x['step']+1}/334 epoch {x['epoch']} loss(last20)={sum(i['loss_global'] for i in k)/len(k):.4f} compute={c:.2f}s comm={m:.2f}s/step elapsed={x['t']/60:.1f}min eta={(334-x['step']-1)*(c+m)/60:.1f}min vram={x['vram_reserved_peak_mb']}MB reconnects={x['reconnects']}\")
PY
tail -n 2 $OUT/weight_check.jsonl 2>/dev/null | cut -c1-40; nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader | tr '\n' ' '" 2>&1)
echo "[$(date +%H:%M:%S)] $L" | tee -a $D/results/progress.log
