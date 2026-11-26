#!/bin/bash
# ReceiptDesk LAB 7 Benchmark Suite on 2x RTX 4090 (Qwen3-VL-2B-Instruct + LoRA merged)
set -euo pipefail
D=/workspace/receipt_lb
PY=$D/venv/bin/python
LG="$PY $D/code/loadgen_receipt.py"
T=$D/runtime/targets.json
LOG=$D/logs/bench_all.log
exec > >(tee -a "$LOG") 2>&1

echo "=== [RECEIPT-LB] START $(date -u +%FT%TZ) ==="

# 1. 1-user baseline on 1x RTX 4090 (cap=256)
echo "=== [Step 1] 1-user streaming baseline on 1x RTX 4090 ==="
$D/code/node_receipt.sh up dp1 256
$PY - <<'P'
import asyncio, aiohttp, json, time, statistics, sys
sys.path.insert(0, "/workspace/receipt_lb/code")
import loadgen_receipt as lg

async def main():
    key = open("/workspace/receipt_lb/runtime/api_key").read().strip()
    headers = {"Authorization": f"Bearer {key}"}
    url = "http://127.0.0.1:8080/v1/chat/completions"
    t0 = time.time()
    recs = []
    async with aiohttp.ClientSession() as sess:
        for i in range(2):
            await lg.ask_once(sess, url, headers, lg.build_request("receipt-vlm", i, False), t0)
        for i in range(8):
            r = await lg.ask_once(sess, url, headers, lg.build_request("receipt-vlm", i, False), t0, keep_text=True)
            recs.append(r)
    speeds = [r["speed"] for r in recs if r["speed"]]
    ttfts = [r["ttft"] for r in recs if r["ttft"]]
    s1 = round(statistics.mean(speeds), 2)
    fast_min = round(s1 * 0.5, 2)
    out = {
        "n_questions": len(recs),
        "ttft_mean_s": round(statistics.mean(ttfts), 4),
        "ttft_p50_s": round(statistics.median(ttfts), 4),
        "speed_mean_tps": s1,
        "speed_p50_tps": round(statistics.median(speeds), 2),
        "fast_slo_speed_min_tps": fast_min,
        "samples": recs[:4],
    }
    json.dump(out, open("/workspace/receipt_lb/results/dp1_n1_baseline.json", "w"), indent=2, ensure_ascii=False)
    print(f"1-USER BASELINE: speed_mean={s1} tok/s, fast_slo_min={fast_min} tok/s, ttft_mean={out['ttft_mean_s']} s")

asyncio.run(main())
P

FAST_MIN=$($PY -c "import json; print(json.load(open('/workspace/receipt_lb/results/dp1_n1_baseline.json'))['fast_slo_speed_min_tps'])")
echo "FAST_MIN=$FAST_MIN"

# 1b. Receipt OCR batch benchmark on 1 GPU (dp1_cb is already up!)
echo "=== [Step 1b] Real CORD-v2 Receipt OCR batch benchmark on 1 GPU ==="
$PY $D/code/receipt_ocr_bench.py --n 32 --concurrency 16 --out $D/results/receipt_batch_dp1.json

# 2. dp1_cb: 1 GPU Continuous Batching (cap=256) — Standard & Fast SLO (already up!)
echo "=== [Step 2] dp1_cb (1 GPU, Continuous Batching cap=256) ==="
$LG capacity --targets $T --results-dir $D/results --name dp1_cb \
  --duration 20 --warmup 5 --max-rounds 4 \
  --levels 1,8,32,64,128,192,256,320 --ttft-p95-max 2.0 --speed-p5-min 15.0
$LG capacity --targets $T --results-dir $D/results --name dp1_cb_fast \
  --duration 20 --warmup 5 --max-rounds 4 \
  --seed-from $D/results/dp1_cb.json --levels 8,16,32,64,96,128,192 --ttft-p95-max 2.0 --speed-p5-min $FAST_MIN

# 3. dp1_seq: 1 GPU Sequential baseline (cap=1)
echo "=== [Step 3] dp1_seq (1 GPU, Sequential cap=1) ==="
$D/code/node_receipt.sh up dp1 1
$LG capacity --targets $T --results-dir $D/results --name dp1_seq \
  --duration 20 --warmup 5 --max-rounds 3 \
  --levels 1,2,4,8 --ttft-p95-max 2.0 --speed-p5-min 15.0

# 4. dp2_cb: 2 GPUs Data Parallelism + Continuous Batching + NGINX least_conn (cap=256)
echo "=== [Step 4] dp2_cb (2 GPUs DP, cap=256, NGINX least_conn) ==="
$D/code/node_receipt.sh up dp2 256
$PY $D/code/receipt_ocr_bench.py --n 64 --concurrency 32 --out $D/results/receipt_batch_dp2.json
$LG capacity --targets $T --results-dir $D/results --name dp2_cb \
  --duration 20 --warmup 5 --max-rounds 4 \
  --levels 1,16,64,128,256,384,512,640 --ttft-p95-max 2.0 --speed-p5-min 15.0
$LG capacity --targets $T --results-dir $D/results --name dp2_cb_fast \
  --duration 20 --warmup 5 --max-rounds 4 \
  --seed-from $D/results/dp2_cb.json --levels 16,32,64,128,192,256,384 --ttft-p95-max 2.0 --speed-p5-min $FAST_MIN

DP2_CAP=$($PY -c "import json; d=json.load(open('/workspace/receipt_lb/results/dp2_cb.json')); print(d['capacity']['users'] or 256)")
OVERLOAD_N=$($PY -c "print(min(640, max(128, int(round($DP2_CAP * 1.4)))))")
MIX_N=$($PY -c "print(max(32, min(160, int(round($DP2_CAP * 0.4)))))")
echo "DP2_CAP=$DP2_CAP OVERLOAD_N=$OVERLOAD_N MIX_N=$MIX_N"

# 5. Concurrency cap trade-off: cap=256 (already up!) vs cap=32
echo "=== [Step 5] Concurrency cap sweep at N=$OVERLOAD_N (cap=256 vs cap=32) ==="
$LG single --targets $T --results-dir $D/results --name cap_256 \
  --users $OVERLOAD_N --duration 25 --warmup 5
$D/code/node_receipt.sh up dp2 32
$LG single --targets $T --results-dir $D/results --name cap_32 \
  --users $OVERLOAD_N --duration 25 --warmup 5

# 6. Bring back winning dp2 cap=256 for Mix Short/Long & Failover
echo "=== [Step 6] Mixed Short vs Long answers (NGINX least_conn) at N=$MIX_N ==="
$D/code/node_receipt.sh up dp2 256
$LG single --targets $T --results-dir $D/results --name mix_short \
  --users $MIX_N --duration 30 --warmup 5 --long-pct 0
$LG single --targets $T --results-dir $D/results --name mix_long \
  --users $MIX_N --duration 30 --warmup 5 --long-pct 25

# 7. Replica Failover (kill gpu1 :8002 mid-stream at t=20s)
echo "=== [Step 7] Replica Failover at N=$MIX_N ==="
KILL_AT=$($PY -c "import time; print(round(time.time() + 20, 3))")
echo "{\"kill_scheduled_epoch\": $KILL_AT, \"port\": 8002, \"users\": $MIX_N}" > $D/results/fail_event.json
($D/code/node_receipt.sh kill-port 8002 "$KILL_AT" > $D/logs/kill_port.log 2>&1) &
$LG single --targets $T --results-dir $D/results --name fail_replica \
  --users $MIX_N --duration 45 --warmup 5 --long-pct 0
wait || true
cp $D/runtime/killed.t $D/results/killed.t 2>/dev/null || true

# 8. Bring winning dp2 (2x vLLM + NGINX least_conn) BACK UP and leave running for Next.js live tests!
echo "=== [Step 8] Restarting winning dp2 cap=256 cluster for LIVE Next.js app ==="
$D/code/node_receipt.sh up dp2 256
$D/code/node_receipt.sh status

touch $D/results/BENCH_ALL_DONE
echo "=== [RECEIPT-LB] ALL DONE $(date -u +%FT%TZ) ==="
