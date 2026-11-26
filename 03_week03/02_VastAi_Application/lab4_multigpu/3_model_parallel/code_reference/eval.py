#!/usr/bin/env python3
"""วัด loss และ Exact Match บน Test Set ของ Base และ adapter หลังจบแต่ละ Epoch

  python eval.py --tags base
  python eval.py --tags epoch1 epoch2 epoch3     (อ่าน adapter จาก ckpt/<tag>)
โมเดลแบ่งลง GPU 2 ใบแบบเดียวกับตอนเทรน · ปิด thinking · greedy decoding
"""
import argparse
import json
import os
import re
import time

import torch

from common import (CKPT_DIR, RESULT_DIR, TEST_FILE, add_lora, collate, encode_example,
                    load_base_model, load_tokenizer, prompt_text, read_jsonl)

MAX_NEW_TOKENS = 160
BATCH = 32


def norm_strict(s):
    """Exact Match หลัก: ตัดช่องว่างหัวท้ายและยุบช่องว่างซ้ำเท่านั้น"""
    return " ".join(s.split())


def norm_loose(s):
    """แบบผ่อนปรน (รายงานประกอบ): ตัด code fence, ; ท้าย, ไม่สนตัวพิมพ์และชนิดเครื่องหมายคำพูด"""
    s = re.sub(r"```(?:sql)?", "", s, flags=re.I)
    s = " ".join(s.split()).rstrip(";").strip()
    return s.replace("'", '"').lower()


@torch.no_grad()
def test_loss(model, tok, rows):
    enc = [encode_example(tok, r) for r in rows]
    tot = n = 0.0
    for i in range(0, len(enc), BATCH):
        ids, att, lab = collate(tok, enc[i:i + BATCH], "cuda:0")
        with torch.autocast("cuda", dtype=torch.bfloat16):
            loss = model(input_ids=ids, attention_mask=att, labels=lab).loss
        k = int((lab != -100).sum())
        tot += loss.item() * k
        n += k
    return tot / n


@torch.no_grad()
def generate(model, tok, rows):
    tok.padding_side = "left"
    prompts = [prompt_text(tok, r) for r in rows]
    order = sorted(range(len(rows)), key=lambda i: len(prompts[i]))
    preds = [None] * len(rows)
    eos = tok.convert_tokens_to_ids("<|im_end|>")
    for i in range(0, len(order), BATCH):
        idx = order[i:i + BATCH]
        x = tok([prompts[j] for j in idx], return_tensors="pt", padding=True,
                add_special_tokens=False).to("cuda:0")
        with torch.autocast("cuda", dtype=torch.bfloat16):
            out = model.generate(**x, max_new_tokens=MAX_NEW_TOKENS, do_sample=False,
                                 temperature=None, top_p=None, top_k=None,
                                 use_cache=True, eos_token_id=eos,
                                 pad_token_id=tok.pad_token_id)
        new = out[:, x["input_ids"].shape[1]:]
        for j, t in zip(idx, tok.batch_decode(new, skip_special_tokens=True)):
            preds[j] = t.strip()
    return preds


def evaluate(model, tok, rows, tag):
    model.eval()
    t0 = time.time()
    loss = test_loss(model, tok, rows)
    preds = generate(model, tok, rows)
    em = [norm_strict(p) == norm_strict(r["answer"]) for p, r in zip(preds, rows)]
    eml = [norm_loose(p) == norm_loose(r["answer"]) for p, r in zip(preds, rows)]
    res = {"tag": tag, "n": len(rows), "test_loss": round(loss, 5),
           "exact_match": round(100 * sum(em) / len(rows), 2), "em_count": sum(em),
           "exact_match_loose": round(100 * sum(eml) / len(rows), 2),
           "eval_sec": round(time.time() - t0, 1)}
    with open(f"{RESULT_DIR}/pred_{tag}.jsonl", "w", encoding="utf-8") as f:
        for p, r, a, b in zip(preds, rows, em, eml):
            f.write(json.dumps({"question": r["question"], "gold": r["answer"], "pred": p,
                                "em": a, "em_loose": b}, ensure_ascii=False) + "\n")
    with open(f"{RESULT_DIR}/eval_{tag}.json", "w") as f:
        json.dump(res, f, indent=2)
    print("[eval]", json.dumps(res), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", nargs="+", required=True)
    a = ap.parse_args()
    todo = [t for t in a.tags if not os.path.exists(f"{RESULT_DIR}/eval_{t}.json")]
    if not todo:
        print("[eval] nothing to do", flush=True)
        return
    tok = load_tokenizer()
    rows = read_jsonl(TEST_FILE)
    model = load_base_model()
    if "base" in todo:                       # โมเดลก่อนเทรน: ยังไม่มี LoRA
        evaluate(model, tok, rows, "base")
    adapters = [t for t in todo if t != "base"]
    if adapters:
        from peft import set_peft_model_state_dict
        from safetensors.torch import load_file
        model = add_lora(model)
        for t in adapters:
            sd = load_file(f"{CKPT_DIR}/{t}/adapter_model.safetensors")
            r = set_peft_model_state_dict(model, sd)
            assert not r.unexpected_keys, r.unexpected_keys
            evaluate(model, tok, rows, t)


if __name__ == "__main__":
    main()
