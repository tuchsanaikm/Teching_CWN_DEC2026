#!/bin/bash
# Track 1 (vapp-lab7-dp2: 1 Node x 2x RTX 4090) — runs ON the DP2 machine.
set -euo pipefail
D=/workspace/lab7
PY=$D/venv/bin/python
LG="$PY $D/code/loadgen.py"
T=$D/runtime/targets.json
LOG=$D/logs/track_dp2.log
exec > >(tee -a "$LOG") 2>&1

echo "=== [DP2] START $(date -u +%FT%TZ) ==="

# 1. Start dp1 cap=256 to measure 1-user baseline speed (S1) and collect dataset samples
echo "=== [DP2] Step 1: 1-user baseline on 1x RTX 4090 ==="
$D/code/node_single.sh up dp1 256
$PY - <<'P'
import asyncio, aiohttp, json, time, statistics, sys
sys.path.insert(0, "/workspace/lab7/code")
import loadgen as lg

async def main():
    key = open("/workspace/lab7/runtime/api_key").read().strip()
    headers = {"Authorization": f"Bearer {key}"}
    url = "http://127.0.0.1:8080/v1/chat/completions"
    t0 = time.time()
    recs = []
    async with aiohttp.ClientSession() as sess:
        # 2 warmup
        for i in range(2):
            await lg.ask_once(sess, url, headers, lg.build_request("shop-bot", i, False), t0)
        # 10 measured
        for i in range(10):
            r = await lg.ask_once(sess, url, headers, lg.build_request("shop-bot", i, False), t0, keep_text=True)
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
        "samples": recs[:8],
    }
    json.dump(out, open("/workspace/lab7/results/dp1_n1_baseline.json", "w"), indent=2, ensure_ascii=False)
    print(f"1-USER BASELINE: speed_mean={s1} tok/s, fast_slo_min={fast_min} tok/s, ttft_mean={out['ttft_mean_s']} s")

asyncio.run(main())
P

FAST_MIN=$($PY -c "import json; print(json.load(open('/workspace/lab7/results/dp1_n1_baseline.json'))['fast_slo_speed_min_tps'])")
echo "FAST_MIN=$FAST_MIN"

# 2. Loadgen verification with fake_llm (A, B, C, D)
echo "=== [DP2] Step 2: Loadgen verification (fake_llm) ==="
$D/code/node_single.sh set-pool fake
$PY - <<'P'
import subprocess, time, json, urllib.request

# Start fake_llm on 127.0.0.1:9000 (200ms TTFT, 50 tok/s -> 20ms/tok, 100 tokens)
p = subprocess.Popen(["/workspace/lab7/venv/bin/python", "/workspace/lab7/code/fake_llm.py",
                      "--port", "9000", "--ttft-ms", "200", "--interval-ms", "20", "--tokens", "100"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)
fake_direct = {"url": "http://127.0.0.1:9000", "model": "shop-bot", "key_file": "/workspace/lab7/runtime/api_key", "replicas": [], "gpu_sources": []}
fake_nginx = {"url": "http://127.0.0.1:8080", "model": "shop-bot", "key_file": "/workspace/lab7/runtime/api_key", "replicas": [], "gpu_sources": []}
json.dump(fake_direct, open("/workspace/lab7/runtime/targets_fake_direct.json", "w"))
json.dump(fake_nginx, open("/workspace/lab7/runtime/targets_fake_nginx.json", "w"))

res = {}
try:
    for n in [1, 50]:
        name = f"check_direct_n{n}"
        subprocess.run(["/workspace/lab7/venv/bin/python", "/workspace/lab7/code/loadgen.py", "single",
                        "--targets", "/workspace/lab7/runtime/targets_fake_direct.json",
                        "--results-dir", "/workspace/lab7/results", "--name", name,
                        "--users", str(n), "--duration", "20", "--warmup", "5"], check=True)
        res[f"direct_n{n}"] = json.load(open(f"/workspace/lab7/results/{name}.json"))
    subprocess.run(["/workspace/lab7/venv/bin/python", "/workspace/lab7/code/loadgen.py", "single",
                    "--targets", "/workspace/lab7/runtime/targets_fake_nginx.json",
                    "--results-dir", "/workspace/lab7/results", "--name", "check_nginx_n50",
                    "--users", "50", "--duration", "20", "--warmup", "5"], check=True)
    res["nginx_n50"] = json.load(open("/workspace/lab7/results/check_nginx_n50.json"))
finally:
    p.terminate()
    p.wait()
json.dump(res, open("/workspace/lab7/results/loadtest_check_summary.json", "w"), indent=1)
print("FAKE CHECK DONE")
P

# 3. Experiment 1: Single GPU Sequential (cap=1)
echo "=== [DP2] Step 3: dp1_seq (1 GPU, cap=1) ==="
$D/code/node_single.sh up dp1 1
$LG capacity --targets $T --results-dir $D/results --name dp1_seq \
  --levels 1,2,4,8,16 --ttft-p95-max 2.0 --speed-p5-min 15.0

# 4. Experiment 2: Single GPU Continuous Batching (cap=256) — Standard & Fast
echo "=== [DP2] Step 4: dp1_cb (1 GPU, cap=256) ==="
$D/code/node_single.sh up dp1 256
$LG capacity --targets $T --results-dir $D/results --name dp1_cb \
  --levels 1,8,32,64,128,192,256,320,384 --ttft-p95-max 2.0 --speed-p5-min 15.0
$LG capacity --targets $T --results-dir $D/results --name dp1_cb_fast \
  --seed-from $D/results/dp1_cb.json --levels 8,16,32,64,96,128,192 --ttft-p95-max 2.0 --speed-p5-min $FAST_MIN

# 5. Experiment 3: 2 GPUs Data Parallel + Continuous Batching + NGINX (cap=256) — Standard & Fast
echo "=== [DP2] Step 5: dp2_cb (2 GPUs DP, cap=256, NGINX least_conn) ==="
$D/code/node_single.sh up dp2 256
$LG capacity --targets $T --results-dir $D/results --name dp2_cb \
  --levels 1,16,64,128,256,384,512,640,768 --ttft-p95-max 2.0 --speed-p5-min 15.0
$LG capacity --targets $T --results-dir $D/results --name dp2_cb_fast \
  --seed-from $D/results/dp2_cb.json --levels 16,32,64,128,192,256,384 --ttft-p95-max 2.0 --speed-p5-min $FAST_MIN

DP2_CAP=$($PY -c "import json; d=json.load(open('/workspace/lab7/results/dp2_cb.json')); print(d['capacity']['users'])")
OVERLOAD_N=$($PY -c "print(int(round($DP2_CAP * 1.5)))")
MIX_N=$($PY -c "print(max(32, int(round($DP2_CAP * 0.4))))")
echo "DP2_CAP=$DP2_CAP OVERLOAD_N=$OVERLOAD_N MIX_N=$MIX_N"

# 6. Experiment 4: Concurrency Limit Sweep at OVERLOAD_N
echo "=== [DP2] Step 6: cap_sweep at N=$OVERLOAD_N ==="
for CAP in 32 64 128 256; do
  $D/code/node_single.sh up dp2 $CAP
  $LG single --targets $T --results-dir $D/results --name cap_${CAP} \
    --users $OVERLOAD_N --duration 45 --warmup 10
done

# 7. Experiment 5: Mixed Short vs Long answers (least_conn)
echo "=== [DP2] Step 7: mix_short vs mix_long at N=$MIX_N ==="
$LG single --targets $T --results-dir $D/results --name mix_short \
  --users $MIX_N --duration 60 --warmup 10 --long-pct 0
$LG single --targets $T --results-dir $D/results --name mix_long \
  --users $MIX_N --duration 60 --warmup 10 --long-pct 20

# 8. Experiment 6: Replica Failover (kill GPU 1 replica mid-stream at t=35s)
echo "=== [DP2] Step 8: fail_replica at N=$MIX_N ==="
KILL_AT=$($PY -c "import time; print(round(time.time() + 35, 3))")
echo "{\"kill_scheduled_epoch\": $KILL_AT, \"port\": 8002, \"users\": $MIX_N}" > $D/results/fail_event.json
($D/code/node_single.sh kill-port 8002 "$KILL_AT" > $D/logs/kill_port.log 2>&1) &
$LG single --targets $T --results-dir $D/results --name fail_replica \
  --users $MIX_N --duration 75 --warmup 10 --long-pct 0
wait || true
cp $D/runtime/killed.t $D/results/killed.t 2>/dev/null || true

$D/code/node_single.sh stop
touch $D/results/DP2_ALL_DONE
echo "=== [DP2] ALL DONE $(date -u +%FT%TZ) ==="
