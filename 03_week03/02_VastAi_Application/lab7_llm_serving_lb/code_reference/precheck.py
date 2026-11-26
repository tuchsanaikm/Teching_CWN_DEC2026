#!/usr/bin/env python3
"""Step 6: runs ON machine 1. One user asks each replica DIRECTLY (not through NGINX), 5 questions,
one after another. Records TTFT and tokens/sec per replica.
usage: precheck.py <key_file> <out.json> [dp|mp]
"""
import sys, json, statistics
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from llm_client import ask

REPLICAS = [  # name, machine, GPU, address as seen from machine 1
    ("n1-gpu0", "machine 1", "GPU 0", "http://127.0.0.1:8001"),
    ("n1-gpu1", "machine 1", "GPU 1", "http://127.0.0.1:8002"),
    ("n2-gpu0", "machine 2", "GPU 0", "http://181.173.127.113:27860"),
    ("n2-gpu1", "machine 2", "GPU 1", "http://181.173.127.113:27596"),
]
if len(sys.argv) > 3 and sys.argv[3] == "mp":   # Model Parallel: 1 replica per machine, the model split over its 2 GPUs
    REPLICAS = [("n1-gpu0+1", "machine 1", "GPU 0+1", "http://127.0.0.1:8001"),
                ("n2-gpu0+1", "machine 2", "GPU 0+1", "http://181.173.127.113:27860")]
QUESTIONS = [
    "อธิบายวิธีเลือกหม้อหุงข้าวสำหรับครอบครัว 4 คน พร้อมข้อดีข้อเสียของแต่ละแบบ",
    "ขอขั้นตอนการทำความสะอาดเครื่องซักผ้าฝาหน้าแบบละเอียด",
    "เปรียบเทียบไม้ถูพื้นแบบสเปรย์กับแบบถังปั่นให้หน่อย ควรเลือกแบบไหน",
    "อธิบายนโยบายการคืนสินค้าทั่วไปของร้านขายของใช้ในบ้านว่าควรมีเงื่อนไขอะไรบ้าง",
    "แนะนำวิธีจัดเก็บของในห้องครัวขนาดเล็กให้เป็นระเบียบ พร้อมอุปกรณ์ที่ควรซื้อ",
]
MAX_TOKENS = 256

key = open(sys.argv[1]).read().strip()
out = {"what": "1 user, sequential, direct to each replica from machine 1, streaming",
       "questions": len(QUESTIONS), "max_tokens": MAX_TOKENS,
       "ttft": "request sent -> first content token (includes network RTT machine1->machine2 for n2 replicas)",
       "tokens_per_s": "(completion_tokens-1)/(last token time - first token time)", "replicas": []}
for name, machine, gpu, url in REPLICAS:
    ask(url, key, "สวัสดี", max_tokens=8)          # one warm-up request, not counted
    runs = []
    for q in QUESTIONS:
        r = ask(url, key, q, max_tokens=MAX_TOKENS)
        assert r["status"] == 200, r
        runs.append({k: r[k] for k in ("ttft_s", "tokens_per_s", "completion_tokens", "prompt_tokens", "total_s")})
    rec = {"replica": name, "machine": machine, "gpu": gpu, "url": url, "runs": runs,
           "ttft_s_mean": round(statistics.mean(x["ttft_s"] for x in runs), 4),
           "ttft_s_median": round(statistics.median(x["ttft_s"] for x in runs), 4),
           "tokens_per_s_mean": round(statistics.mean(x["tokens_per_s"] for x in runs), 2),
           "tokens_per_s_min": min(x["tokens_per_s"] for x in runs),
           "tokens_per_s_max": max(x["tokens_per_s"] for x in runs)}
    out["replicas"].append(rec)
    print(name, rec["ttft_s_mean"], rec["tokens_per_s_mean"], flush=True)
best = max(r["tokens_per_s_mean"] for r in out["replicas"])
for r in out["replicas"]:
    r["slower_than_fastest_pct"] = round(100 * (best - r["tokens_per_s_mean"]) / best, 2)
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
print("PRECHECK DONE")
