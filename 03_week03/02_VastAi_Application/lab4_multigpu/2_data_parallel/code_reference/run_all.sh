#!/bin/bash
# Whole pipeline, safe to start again: each finished stage is skipped, training resumes
# from its checkpoint. Start it inside tmux so it survives a dropped SSH connection:
#   tmux new -d -s dp "bash /workspace/lab4_dp/code/run_all.sh"
ROOT=/workspace/lab4_dp
CODE=$ROOT/code
RES=$ROOT/results
LOG=$ROOT/logs
mkdir -p $RES/probe $LOG
# This image ships a newer "compat" libcuda (570) that hides the host driver's one (550)
# and breaks CUDA start-up (error 804). Put the real driver library first.
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export TOKENIZERS_PARALLELISM=false
cd $CODE
stamp() { echo "[$(date +%H:%M:%S)] $*" | tee -a $LOG/pipeline.log; }

# ---- stage 1: largest batch per GPU (1, 2, 4, 8, ... until out of memory) ----
if [ ! -f $RES/probe/best_bs.txt ]; then
  best=0; bs=1
  while true; do
    if [ -f $RES/probe/bs${bs}.done ]; then
      st=$(cat $RES/probe/bs${bs}.done)
    else
      stamp "PROBE bs/gpu=$bs start"
      rm -f $RES/probe/bs${bs}_rank*.json
      torchrun --nproc_per_node 2 train.py --mode probe --bs $bs > $LOG/probe_bs${bs}.log 2>&1
      rc=$?
      n_ok=$(grep -l '"status": "ok"' $RES/probe/bs${bs}_rank*.json 2>/dev/null | wc -l)
      if [ $rc -eq 0 ] && [ $n_ok -eq 2 ]; then st=ok
      elif grep -qi "out of memory" $LOG/probe_bs${bs}.log; then st=oom
      else st=error; fi
      [ $st != error ] && echo $st > $RES/probe/bs${bs}.done
      stamp "PROBE bs/gpu=$bs -> $st (exit $rc)"
    fi
    if [ $st = ok ]; then best=$bs; bs=$((bs * 2)); else break; fi
  done
  if [ $st = error ] || [ $best -eq 0 ]; then stamp "PROBE FAILED (see $LOG/probe_bs${bs}.log)"; exit 1; fi
  echo $best > $RES/probe/best_bs.txt
fi
BS=$(cat $RES/probe/best_bs.txt)
stamp "largest batch per GPU = $BS"

# ---- stage 2: train 3 epochs (resumes from ckpt/state.pt) ----
if [ ! -f $RES/train_summary.json ]; then
  stamp "TRAIN start/resume bs/gpu=$BS"
  torchrun --nproc_per_node 2 train.py --mode train --bs $BS --epochs 3 >> $LOG/train.log 2>&1 \
    || { stamp "TRAIN FAILED"; exit 1; }
fi
stamp "TRAIN finished"

# ---- stage 3: Exact Match of base + each epoch ----
if [ ! -f $RES/eval_summary.json ]; then
  stamp "EVAL start"
  python eval.py --tags base,epoch1,epoch2,epoch3 >> $LOG/eval.log 2>&1 || { stamp "EVAL FAILED"; exit 1; }
fi
stamp "ALL DONE"
