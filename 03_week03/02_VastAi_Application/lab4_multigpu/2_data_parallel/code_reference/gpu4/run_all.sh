#!/bin/bash
# Whole experiment on the instance. Start inside tmux so it survives a lost connection:
#   tmux new -d -s dp4 'bash /workspace/lab4_dp4/code/run_all.sh'
# Safe to start again: finished stages are skipped and training resumes from the last finished epoch.
ROOT=/workspace/lab4_dp4
R=$ROOT/results
cd $ROOT/code
mkdir -p $R/eval $R/logs
export PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false NCCL_SHM_DISABLE=1
exec >>$R/logs/pipeline.log 2>&1
stage() { echo "$1" >$R/stage; echo "$(date +%T) STAGE $1"; }

# progress line every 150 s
( while true; do
    echo "$(date '+%F %T') stage=$(cat $R/stage 2>/dev/null) | gpu util/mem: $(nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader,nounits | tr '\n' ';') | $(cat $R/logs/probe.log $R/logs/train.log 2>/dev/null | tr '\r' '\n' | grep -E '^[0-9]{2}:|^batch_per_gpu' | tail -n 1 | cut -c1-200)" >>$R/status.log
    sleep 150
  done ) &
REPORTER=$!
trap "kill $REPORTER" EXIT

set -e
if [ ! -f $R/eval/eval_base.json ]; then
  stage "1/5 eval base"
  CUDA_VISIBLE_DEVICES=0 python eval.py --tag base >$R/logs/eval_base.log 2>&1
fi
if [ ! -f $R/batch_probe.json ]; then
  stage "2/5 batch probe"
  python find_batch.py 4 >$R/logs/probe.log 2>&1
fi
BS=$(python -c "import json;print(json.load(open('$R/batch_probe.json'))['max_batch_per_gpu'])")
if [ ! -f $R/train_done ]; then
  stage "3/5 train batch_per_gpu=$BS"
  torchrun --nproc_per_node 4 train.py --mode train --batch-size $BS --epochs 3 >>$R/logs/train.log 2>&1
  touch $R/train_done
fi
stage "4/5 eval epochs"
pids=""
for e in 1 2 3; do
  if [ ! -f $R/eval/eval_epoch$e.json ]; then
    CUDA_VISIBLE_DEVICES=$((e - 1)) python eval.py --tag epoch$e --adapter $R/adapters/epoch$e >$R/logs/eval_epoch$e.log 2>&1 &
    pids="$pids $!"
  fi
done
for p in $pids; do wait $p; done
stage "5/5 summary"
python summarize.py >$R/logs/summarize.log 2>&1
stage "done"
echo "$(date +%T) ALL_DONE"
