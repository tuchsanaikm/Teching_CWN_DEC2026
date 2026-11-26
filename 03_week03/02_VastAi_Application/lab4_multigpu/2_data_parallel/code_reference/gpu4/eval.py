"""Test-set loss and Exact Match of the base model or of base + a LoRA adapter (one GPU).

  CUDA_VISIBLE_DEVICES=0 python eval.py --tag base
  CUDA_VISIBLE_DEVICES=1 python eval.py --tag epoch1 --adapter /workspace/lab4_dp4/results/adapters/epoch1

Exact Match: the generated SQL equals the reference SQL after trimming, collapsing whitespace
and dropping a trailing ';' (case and quotes must match).
"""
import argparse
import json
import os
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from common import MAX_LEN, MODEL_DIR, ROOT, TEST_FILE, collate, encode, load_jsonl, prompt_text

p = argparse.ArgumentParser()
p.add_argument("--tag", required=True)
p.add_argument("--adapter", default=None)
p.add_argument("--batch-size", type=int, default=16)
p.add_argument("--max-new-tokens", type=int, default=128)
p.add_argument("--limit", type=int, default=0)
p.add_argument("--out", default=f"{ROOT}/results/eval")
args = p.parse_args()
os.makedirs(args.out, exist_ok=True)
torch.manual_seed(0)
dev = "cuda"


def norm(s):
    return " ".join(s.strip().rstrip(";").split())


def loose(s):  # extra, more forgiving number: ignore case and quote style
    return norm(s).lower().replace('"', "'")


tok = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, dtype=torch.bfloat16, device_map={"": 0})
if args.adapter:
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, args.adapter)
model.eval()
test = load_jsonl(TEST_FILE)
if args.limit:
    test = test[:args.limit]
t0 = time.time()

# ---- loss on the answer tokens (teacher forcing, same format and 256-token limit as training) ----
enc = [encode(tok, ex, MAX_LEN) for ex in test]
nll, ntok = 0.0, 0
with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
    for i in range(0, len(enc), args.batch_size):
        b = {k: v.to(dev) for k, v in collate(enc[i:i + args.batch_size], tok.pad_token_id).items()}
        logits = model(input_ids=b["input_ids"], attention_mask=b["attention_mask"]).logits[:, :-1].float()
        labels = b["labels"][:, 1:]
        nll += torch.nn.functional.cross_entropy(logits.reshape(-1, logits.shape[-1]), labels.reshape(-1),
                                                 ignore_index=-100, reduction="sum").item()
        ntok += (labels != -100).sum().item()
loss = nll / ntok

# ---- greedy generation ----
tok.padding_side = "left"
order = sorted(range(len(test)), key=lambda i: enc[i]["prompt_len"])
preds = [None] * len(test)
im_end = tok.convert_tokens_to_ids("<|im_end|>")
with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
    for i in range(0, len(order), args.batch_size):
        idx = order[i:i + args.batch_size]
        x = tok([prompt_text(tok, test[j]) for j in idx], return_tensors="pt", padding=True,
                add_special_tokens=False).to(dev)
        out = model.generate(**x, max_new_tokens=args.max_new_tokens, do_sample=False, temperature=None,
                             top_p=None, top_k=None, eos_token_id=im_end, pad_token_id=tok.pad_token_id)
        for j, o in zip(idx, out[:, x["input_ids"].shape[1]:]):
            preds[j] = tok.decode(o, skip_special_tokens=True)

rows = [{"i": i, "question": ex["question"], "context": ex["context"], "ref": ex["answer"], "pred": pr,
         "em": norm(pr) == norm(ex["answer"]), "em_loose": loose(pr) == loose(ex["answer"])}
        for i, (ex, pr) in enumerate(zip(test, preds))]
res = {"tag": args.tag, "adapter": args.adapter, "n": len(rows), "test_loss": round(loss, 4),
       "answer_tokens": ntok, "exact_match": sum(r["em"] for r in rows) / len(rows),
       "em_correct": sum(r["em"] for r in rows),
       "exact_match_loose": sum(r["em_loose"] for r in rows) / len(rows),
       "eval_sec": round(time.time() - t0, 1),
       "vram_peak_mib": round(torch.cuda.max_memory_allocated() / 2**20)}
with open(f"{args.out}/pred_{args.tag}.jsonl", "w") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
json.dump(res, open(f"{args.out}/eval_{args.tag}.json", "w"), indent=1)
print("EVAL_DONE", json.dumps(res), flush=True)
