"""ดูความยาว token ของ train/test หลังใส่ prompt (ก่อนตัดที่ 256)"""
import json
from common import *
tok = load_tokenizer()
out = {}
for name, path in (("train", TRAIN_FILE), ("test", TEST_FILE)):
    rows = read_jsonl(path)
    pl, tl, al = [], [], []
    for r in rows:
        p = tok(prompt_text(tok, r), add_special_tokens=False)["input_ids"]
        a = tok(r["answer"] + "<|im_end|>", add_special_tokens=False)["input_ids"]
        pl.append(len(p)); al.append(len(a)); tl.append(len(p) + len(a))
    s = sorted(tl)
    out[name] = {"n": len(rows), "total_min": s[0], "total_mean": round(sum(s) / len(s), 1),
                 "total_p95": s[int(.95 * len(s))], "total_max": s[-1],
                 "over_256": sum(t > MAX_LEN for t in tl),
                 "prompt_ge_256": sum(p >= MAX_LEN for p in pl),
                 "prompt_max": max(pl), "answer_max": max(al)}
out["example_text"] = prompt_text(tok, rows[0]) + rows[0]["answer"] + "<|im_end|>"
json.dump(out, open(f"{RESULT_DIR}/token_stats.json", "w"), indent=2, ensure_ascii=False)
print(json.dumps(out, indent=2, ensure_ascii=False))
