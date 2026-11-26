#!/bin/bash
# Clean resume for MP4 (1 Node x 4x RTX 4090): mp4_cb (2+2 TP=2) then dp4_cb (4x1 DP)
set -euo pipefail
D=/workspace/lab7
PY=$D/venv/bin/python
LG="$PY $D/code/loadgen.py"
T=$D/runtime/targets.json
LOG=$D/logs/track_mp4.log
rm -f "$LOG"
exec > >(tee -a "$LOG") 2>&1

echo "=== [MP4 RESUME] START $(date -u +%FT%TZ) ==="
FAST_MIN=$($PY -c "import json; print(json.load(open('/workspace/lab7/results/mp4_dp1_ref.json'))['fast_slo_speed_min_tps'])")
echo "FAST_MIN=$FAST_MIN"

# 1. Model Parallel 2+2 (GPU 0+1 = 8001, GPU 2+3 = 8002, TP=2, cap=512, NGINX least_conn)
echo "=== [MP4] Step 2: mp4_cb (Model Parallel 2+2, cap=512, NGINX least_conn) ==="
$D/code/node_single.sh up mp2 512
rm -f $D/results/mp4_cb.json $D/results/mp4_cb_fast.json
$LG capacity --targets $T --results-dir $D/results --name mp4_cb \
  --levels 1,16,64,128,256,384,512,640,768 --ttft-p95-max 2.0 --speed-p5-min 15.0
$LG capacity --targets $T --results-dir $D/results --name mp4_cb_fast \
  --seed-from $D/results/mp4_cb.json --levels 16,32,64,128,192,256,384 --ttft-p95-max 2.0 --speed-p5-min $FAST_MIN

# 2. Data Parallel 4x1 on the EXACT SAME 4x RTX 4090 machine
echo "=== [MP4] Step 3: dp4_cb (Data Parallel 4x1, cap=256, NGINX least_conn) ==="
$D/code/node_single.sh up dp4 256
rm -f $D/results/dp4_cb.json $D/results/dp4_cb_fast.json
$LG capacity --targets $T --results-dir $D/results --name dp4_cb \
  --levels 1,32,128,256,512,768,1024,1280 --ttft-p95-max 2.0 --speed-p5-min 15.0
$LG capacity --targets $T --results-dir $D/results --name dp4_cb_fast \
  --seed-from $D/results/dp4_cb.json --levels 32,64,128,256,384,512,640 --ttft-p95-max 2.0 --speed-p5-min $FAST_MIN

$D/code/node_single.sh stop
touch $D/results/MP4_ALL_DONE
echo "=== [MP4] ALL DONE $(date -u +%FT%TZ) ==="
