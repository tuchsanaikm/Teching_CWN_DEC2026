#!/bin/bash
# ไปป์ไลน์ทั้งหมด รันบนเครื่อง GPU ใน tmux (หลุดการเชื่อมต่อก็ยังรันต่อ; รันซ้ำจะข้ามขั้นที่เสร็จแล้ว)
source /venv/main/bin/activate >/dev/null 2>&1
cd /workspace/lab4_mp/code
R=/workspace/lab4_mp/results
export TQDM_DISABLE=1 PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false
stage() { echo "$1" > $R/stage.txt; echo "===== $(date +%T) $1 ====="; }

stage "1/4 eval base"
python eval.py --tags base || exit 1

stage "2/4 probe batch"
if [ ! -f $R/max_batch.txt ]; then
  best=0
  for b in 1 2 4 8 16 32 64 128 256; do
    [ -f $R/probe_b$b.json ] || python train.py --probe $b
    if [ ! -f $R/probe_b$b.json ]; then   # process ตายโดยไม่ได้เขียนผล (เช่น OOM นอก PyTorch)
      echo "{\"batch\": $b, \"status\": \"oom\", \"error\": \"process died\"}" > $R/probe_b$b.json
    fi
    if grep -q '"status": "ok"' $R/probe_b$b.json; then best=$b; else break; fi
  done
  [ "$best" -gt 0 ] || exit 1
  echo $best > $R/max_batch.txt
fi
B=$(cat $R/max_batch.txt)
echo "max batch = $B"

stage "3/4 train batch $B"
python train.py --batch $B --epochs 3 || exit 1

stage "4/4 eval epochs"
python eval.py --tags epoch1 epoch2 epoch3 || exit 1

stage "DONE"
touch $R/DONE
