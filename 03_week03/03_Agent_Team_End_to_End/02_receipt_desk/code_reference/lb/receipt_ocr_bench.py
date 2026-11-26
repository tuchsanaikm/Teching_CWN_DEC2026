#!/usr/bin/env python3
"""ReceiptDesk CORD-v2 Receipt OCR Throughput Benchmark (1 GPU vs 2 GPUs Data Parallelism)."""
import argparse, asyncio, base64, json, os, statistics, time
from pathlib import Path
import aiohttp

SYSTEM_PROMPT = (
    "You are a receipt reader for a Thai accounting office. "
    "Read the receipt image and answer with ONE JSON object only, no other text."
)
USER_PROMPT = (
    "Read this receipt and return JSON with exactly these keys:\n"
    '{"merchant": string, "date": "YYYY-MM-DD", '
    '"items": [{"name": string, "price": "0.00"}], "total": "0.00"}\n'
    "- merchant: shop name as printed\n"
    "- date: receipt date in the Gregorian calendar (convert Buddhist Era years: subtract 543)\n"
    "- items: every line item with its printed price as a string with 2 decimals\n"
    "- total: the grand total printed on the receipt (do NOT compute it from the items)\n"
    'If the image is blurred, cut off or not a receipt, return {"unreadable": true} instead. '
    "Never guess a total you cannot read."
)

def load_images(img_dir: Path):
    imgs = []
    for p in sorted(img_dir.glob("*.jpg")):
        if p.name.startswith("un"):
            continue
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        imgs.append((p.name, f"data:image/jpeg;base64,{b64}"))
    return imgs

async def run_one(sess, url, headers, model, name, data_uri):
    body = {
        "model": model,
        "temperature": 0.0,
        "max_tokens": 384,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": data_uri}},
                {"type": "text", "text": USER_PROMPT},
            ]},
        ],
    }
    t0 = time.perf_counter()
    try:
        async with sess.post(url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as r:
            replica = r.headers.get("X-Replica", "unknown")
            txt = await r.text()
            dt = time.perf_counter() - t0
            if r.status != 200:
                return {"ok": False, "status": r.status, "dt": dt, "replica": replica, "name": name}
            data = json.loads(txt)
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage") or {}
            # Check JSON validity
            valid_json = False
            try:
                s = content.strip()
                if "{" in s and "}" in s:
                    obj = json.loads(s[s.find("{"):s.rfind("}")+1])
                    valid_json = isinstance(obj, dict) and ("total" in obj or "unreadable" in obj)
            except Exception:
                pass
            return {
                "ok": True,
                "valid_json": valid_json,
                "dt": dt,
                "replica": replica,
                "name": name,
                "completion_tokens": usage.get("completion_tokens", 0),
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "sample": content[:200],
            }
    except Exception as e:
        return {"ok": False, "err": str(e), "dt": time.perf_counter() - t0, "replica": "unknown", "name": name}

async def bench(url, key, model, img_dir, total_reqs, concurrency):
    imgs = load_images(Path(img_dir))
    assert imgs, f"No images found in {img_dir}"
    headers = {"Authorization": f"Bearer {key}"}
    sem = asyncio.Semaphore(concurrency)

    async def bounded(idx):
        name, uri = imgs[idx % len(imgs)]
        async with sem:
            return await run_one(sess, url + "/v1/chat/completions", headers, model, name, uri)

    conn = aiohttp.TCPConnector(limit=0)
    async with aiohttp.ClientSession(connector=conn) as sess:
        # 2 warmup
        await asyncio.gather(*[run_one(sess, url + "/v1/chat/completions", headers, model, *imgs[i % len(imgs)]) for i in range(2)])
        t_start = time.perf_counter()
        recs = await asyncio.gather(*[bounded(i) for i in range(total_reqs)])
        wall = time.perf_counter() - t_start

    ok_recs = [r for r in recs if r["ok"]]
    dts = [r["dt"] for r in ok_recs]
    valid = sum(1 for r in ok_recs if r.get("valid_json"))
    by_rep = {}
    for r in ok_recs:
        by_rep[r["replica"]] = by_rep.get(r["replica"], 0) + 1
    out = {
        "total_requests": total_reqs,
        "concurrency": concurrency,
        "ok": len(ok_recs),
        "errors": total_reqs - len(ok_recs),
        "valid_json": valid,
        "wall_seconds": round(wall, 3),
        "receipts_per_second": round(len(ok_recs) / wall, 3) if wall > 0 else 0,
        "receipts_per_minute": round(len(ok_recs) / wall * 60.0, 1) if wall > 0 else 0,
        "latency_p50_s": round(statistics.median(dts), 3) if dts else None,
        "latency_p95_s": round(sorted(dts)[int(0.95 * (len(dts) - 1))], 3) if dts else None,
        "latency_mean_s": round(statistics.mean(dts), 3) if dts else None,
        "by_replica": by_rep,
        "sample_outputs": [r["sample"] for r in ok_recs[:3]],
    }
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8080")
    ap.add_argument("--key-file", default="/workspace/receipt_lb/runtime/api_key")
    ap.add_argument("--model", default="receipt-vlm")
    ap.add_argument("--img-dir", default="/workspace/receipt_lb/receipts")
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--concurrency", type=int, default=16)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    key = Path(args.key_file).read_text().strip()
    res = asyncio.run(bench(args.url, key, args.model, args.img_dir, args.n, args.concurrency))
    Path(args.out).write_text(json.dumps(res, indent=2, ensure_ascii=False))
    print(json.dumps({k: v for k, v in res.items() if k != "sample_outputs"}, indent=2, ensure_ascii=False))
