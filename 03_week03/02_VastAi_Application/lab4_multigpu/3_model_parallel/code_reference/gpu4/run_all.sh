#!/bin/bash
# Whole pipeline on the instance; start it inside tmux so it survives a dropped connection:
#   tmux new -d -s mp4 'bash /workspace/mp4/code/run_all.sh'
# Each stage is skipped when its result already exists, so re-running continues the job.
export HF_HOME=/workspace/hf PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True TOKENIZERS_PARALLELISM=false
OUT=/workspace/mp4; cd $OUT/code; mkdir -p $OUT/logs
stage() { echo "$(date '+[%H:%M:%S]') STAGE $*" | tee -a $OUT/logs/pipeline.log; }

if ! python -c "import json,sys; sys.exit(0 if json.load(open('$OUT/results/probe.json')).get('max_batch') else 1)" 2>/dev/null; then
  stage probe; python train.py probe >> $OUT/logs/probe.log 2>&1 || { stage "probe FAILED"; exit 1; }
fi
B=$(python -c "import json; print(json.load(open('$OUT/results/probe.json'))['max_batch'])")
stage "eval base"; python eval.py --tags base >> $OUT/logs/eval.log 2>&1 || { stage "eval base FAILED"; exit 1; }
stage "train batch $B"; python train.py train --batch $B >> $OUT/logs/train.log 2>&1 || { stage "train FAILED"; exit 1; }
stage "eval epochs"; python eval.py >> $OUT/logs/eval.log 2>&1 || { stage "eval FAILED"; exit 1; }
stage ALL_DONE
