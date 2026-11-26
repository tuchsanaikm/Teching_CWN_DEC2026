#!/usr/bin/env python3
"""Step 5: test from OUTSIDE the machines through NGINX (public port of 8080).
usage: chat_test.py <base_url> <key_file> <out.json>
Asks 4 household-goods customer questions with streaming + key (all 4 in flight at the same time, so
Least Connections has to spread them), then one question without a key and one with a wrong key.
"""
import sys, json, threading, time
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from llm_client import ask

QUESTIONS = [
    "กระทะเคลือบเทฟล่อนใช้กับเตาแม่เหล็กไฟฟ้าได้ไหม และควรดูแลอย่างไรไม่ให้ผิวเคลือบลอก",
    "ซื้อเครื่องดูดฝุ่นไปแล้ว 5 วัน แรงดูดอ่อนมาก ขอเปลี่ยนสินค้าได้ไหม ต้องเตรียมอะไรบ้าง",
    "ช่วยแนะนำน้ำยาทำความสะอาดพื้นกระเบื้องห้องน้ำที่มีคราบหินปูนหน่อย",
    "ผ้าปูที่นอนขนาด 6 ฟุต ควรซักด้วยน้ำอุณหภูมิเท่าไร และตากอย่างไรไม่ให้สีซีด",
]

base, keyfile, outpath = sys.argv[1:4]
key = open(keyfile).read().strip()
res = [None] * len(QUESTIONS)


def worker(i):
    r = ask(base, key, QUESTIONS[i], max_tokens=220)
    r["question"] = QUESTIONS[i]
    res[i] = r


th = [threading.Thread(target=worker, args=(i,)) for i in range(len(QUESTIONS))]
for t in th:
    t.start()
    time.sleep(0.05)   # keep the order 1..4 while all four overlap
for t in th:
    t.join()

no_key = ask(base, None, QUESTIONS[0])
bad_key = ask(base, "sk-wrong-key", QUESTIONS[0])
out = {"endpoint": base + "/v1/chat/completions", "streaming": True, "with_key": res,
       "without_key": no_key, "wrong_key": bad_key}
json.dump(out, open(outpath, "w"), ensure_ascii=False, indent=1)
for i, r in enumerate(res, 1):
    print(f"Q{i} status={r['status']} replica={r['replica']} tokens={r.get('completion_tokens')} "
          f"ttft={r.get('ttft_s')}s tok/s={r.get('tokens_per_s')} chunks={r.get('stream_chunks')} "
          f"gap_med={r.get('chunk_gap_ms_median')}ms gap_max={r.get('chunk_gap_ms_max')}ms")
print("no key   ->", no_key["status"], no_key.get("error"))
print("wrong key->", bad_key["status"], bad_key.get("error"))
