#!/usr/bin/env python3
"""Record REAL token-by-token streaming traces from live vLLM + NGINX on RTX 4090
for rendering 1x real-time animated GIFs:
  1) Speed comparison across concurrent user loads: N=1, N=64, N=256, N=512 (on 2x RTX 4090 DP)
  2) 4 representative concurrent users in a multi-turn chat sequence (short + long questions) under N=64 background load
"""
import asyncio, aiohttp, json, time, sys
sys.path.insert(0, "/workspace/lab7/code")
import loadgen as lg

URL = "http://127.0.0.1:8080/v1/chat/completions"
KEY = open("/workspace/lab7/runtime/api_key").read().strip()
HEADERS = {"Authorization": f"Bearer {KEY}"}

# Representative multi-turn sequence prompts (varying lengths: short & detailed)
DEMO_TURNS = [
    [("ร้านเปิดกี่โมงถึงกี่โมงคะ", False),
     ("กระทะเคลือบแบบไหนใช้กับเตาแม่เหล็กไฟฟ้าได้คะ ช่วยอธิบายแบบละเอียดเป็นข้อ ๆ ด้วยนะคะ", True),
     ("จ่ายเงินปลายทางได้ไหมคะ", False)],
    [("หม้อหุงข้าวสำหรับ 2 คน ควรใช้ขนาดกี่ลิตรครับ", False),
     ("สินค้าชำรุดตอนขนส่ง ต้องทำอย่างไรครับ ช่วยอธิบายแบบละเอียดเป็นข้อ ๆ ด้วยนะคะ", True),
     ("ขอใบกำกับภาษีเต็มรูปได้ไหมคะ", False)],
    [("ไม้ถูพื้นแบบไหนเหมาะกับพื้นไม้ลามิเนตคะ", False),
     ("ที่นอนยางพารากับที่นอนสปริงต่างกันอย่างไรคะ ช่วยอธิบายแบบละเอียดเป็นข้อ ๆ ด้วยนะคะ", True),
     ("สั่งวันนี้ของจะถึงกี่วันคะ", False)],
    [("เครื่องดูดฝุ่นไร้สายใช้งานได้นานกี่นาทีต่อการชาร์จครับ", False),
     ("ปลั๊กพ่วงแบบไหนปลอดภัย มี มอก. ไหมครับ ช่วยอธิบายแบบละเอียดเป็นข้อ ๆ ด้วยนะคะ", True),
     ("มีบริการส่งถึงบ้านไหมครับ ค่าส่งเท่าไร", False)],
]

async def stream_and_record(session, question, is_long):
    body = {
        "model": "shop-bot",
        "messages": [
            {"role": "system", "content": lg.SYSTEM_LONG if is_long else lg.SYSTEM_SHORT},
            {"role": "user", "content": question},
        ],
        "max_tokens": 350 if is_long else 140,
        "temperature": 0.7,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    t0 = time.perf_counter()
    events = []
    replica = "unknown"
    t_first = None
    n_tok = 0
    async with session.post(URL, json=body, headers=HEADERS) as r:
        replica = r.headers.get("X-Replica", "unknown")
        async for raw in r.content:
            line = raw.decode("utf-8", errors="ignore").strip()
            if not line.startswith("data: "):
                continue
            payload = line[6:]
            if payload == "[DONE]":
                break
            try:
                obj = json.loads(payload)
            except Exception:
                continue
            choices = obj.get("choices") or []
            if choices:
                delta = choices[0].get("delta", {}).get("content")
                if delta:
                    dt = time.perf_counter() - t0
                    if t_first is None:
                        t_first = dt
                    n_tok += 1
                    events.append([round(dt, 4), delta])
            usage = obj.get("usage")
            if usage and usage.get("completion_tokens"):
                n_tok = usage["completion_tokens"]
    total = time.perf_counter() - t0
    gen_s = max(0.001, total - (t_first or total))
    speed = round(max(0, n_tok - 1) / gen_s, 2) if n_tok > 1 else 0.0
    return {
        "question": question,
        "is_long": is_long,
        "replica": replica,
        "ttft_s": round(t_first or total, 4),
        "total_s": round(total, 4),
        "n_tokens": n_tok,
        "speed_tps": speed,
        "events": events,
    }

async def bg_worker(session, stop_evt, idx):
    q = idx % len(lg.QUESTIONS)
    while not stop_evt.is_set():
        try:
            body = lg.build_request("shop-bot", q, (q % 5 == 0))
            async with session.post(URL, json=body, headers=HEADERS) as r:
                async for _ in r.content:
                    if stop_evt.is_set():
                        break
        except Exception:
            await asyncio.sleep(0.1)
        q = (q + 1) % len(lg.QUESTIONS)

async def run_load_comparison(session):
    q_same = "กระทะเคลือบแบบไหนใช้กับเตาแม่เหล็กไฟฟ้าได้คะ ช่วยอธิบายแบบละเอียดเป็นข้อ ๆ ด้วยนะคะ"
    out = {}
    for N in [1, 64, 256, 512]:
        print(f"Recording load comparison N={N} ...", flush=True)
        stop_evt = asyncio.Event()
        bg_tasks = [asyncio.create_task(bg_worker(session, stop_evt, i)) for i in range(max(0, N - 1))]
        if bg_tasks:
            await asyncio.sleep(4.0)  # let steady-state queue/batch build up
        rec = await stream_and_record(session, q_same, True)
        stop_evt.set()
        for t in bg_tasks:
            t.cancel()
        await asyncio.gather(*bg_tasks, return_exceptions=True)
        await asyncio.sleep(1.5)
        out[str(N)] = rec
        print(f"  N={N}: ttft={rec['ttft_s']}s speed={rec['speed_tps']} tok/s tokens={rec['n_tokens']} replica={rec['replica']}", flush=True)
    return out

async def run_4users_sequence(session, bg_n=60):
    print(f"Recording 4-user multi-turn sequence under N={bg_n+4} total concurrent users ...", flush=True)
    stop_evt = asyncio.Event()
    bg_tasks = [asyncio.create_task(bg_worker(session, stop_evt, i)) for i in range(bg_n)]
    await asyncio.sleep(3.5)

    t_start = time.perf_counter()
    async def user_seq(uid):
        turns = []
        for q, is_long in DEMO_TURNS[uid]:
            offset = round(time.perf_counter() - t_start, 4)
            rec = await stream_and_record(session, q, is_long)
            rec["start_offset_s"] = offset
            turns.append(rec)
            await asyncio.sleep(0.4)
        return turns

    users = await asyncio.gather(*(user_seq(i) for i in range(4)))
    stop_evt.set()
    for t in bg_tasks:
        t.cancel()
    await asyncio.gather(*bg_tasks, return_exceptions=True)
    return {"total_concurrent_users": bg_n + 4, "users": users}

async def main():
    conn = aiohttp.TCPConnector(limit=1000)
    timeout = aiohttp.ClientTimeout(total=90)
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        # Warmup 2 calls
        await stream_and_record(session, "ร้านเปิดกี่โมงถึงกี่โมงคะ", False)
        comp = await run_load_comparison(session)
        seq4 = await run_4users_sequence(session, bg_n=60)
    res = {"load_comparison": comp, "four_users_sequence": seq4}
    json.dump(res, open("/workspace/lab7/results/stream_demo_traces.json", "w"), ensure_ascii=False, indent=1)
    print("SAVED /workspace/lab7/results/stream_demo_traces.json")

if __name__ == "__main__":
    asyncio.run(main())
