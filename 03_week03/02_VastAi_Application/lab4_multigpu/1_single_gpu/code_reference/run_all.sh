#!/bin/bash
# Lab 4 / 1_single_gpu pipeline. Start inside tmux so it survives a dropped SSH connection:
#   tmux new -d -s lab4 'bash /workspace/lab4/code/run_all.sh'
# Every stage skips itself when its result already exists, so re-running continues the job.
set -u
export LAB_ROOT=${LAB_ROOT:-/workspace/lab4}
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export TOKENIZERS_PARALLELISM=false
cd "$LAB_ROOT/code"
R="$LAB_ROOT/results"
mkdir -p "$R"
LOG="$R/run.log"
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

done_flag() { python - "$1" "$2" <<'EOF'
import json, sys
try:
    sys.exit(0 if json.load(open(sys.argv[1])).get(sys.argv[2]) else 1)
except Exception:
    sys.exit(1)
EOF
}

say "STAGE 1/3 probe max batch"
if ! done_flag "$R/probe.json" finished; then
  python train.py --probe 2>&1 | tee -a "$LOG"
fi

say "STAGE 2/3 eval base model"
if [ ! -f "$R/eval_base.json" ]; then
  python eval.py --tag base 2>&1 | grep -v Warning | tee -a "$LOG"
fi

say "STAGE 3/3 train 3 epochs (+ eval after each epoch)"
if ! done_flag "$R/train_metrics.json" finished; then
  python train.py 2>&1 | tee -a "$LOG"
fi

if done_flag "$R/train_metrics.json" finished; then
  say "training finished; run code/report.py locally on results/raw for metrics.json + charts"
  say "ALL DONE"
else
  say "PIPELINE STOPPED BEFORE FINISHING (re-run run_all.sh to resume)"
fi
