"""Exact Match + loss on the Test Set for the Base model and for the adapter saved after each epoch.

Uses the same 4-GPU layer split as train.py. Greedy decoding, thinking off.
  python eval.py                # base, epoch1, epoch2, epoch3 (skips the ones already done)
  python eval.py --tags base    # only some
Exact Match: prediction == reference after collapsing whitespace and dropping a trailing ';'.
"""
import argparse, json, os, time
import torch
from peft import LoraConfig, get_peft_model
from peft.utils import set_peft_model_state_dict
from safetensors.torch import load_file

import common as C

GEN_BATCH, LOSS_BATCH, MAX_NEW = 32, 16, 160


def log(*a):
    print(time.strftime("[%H:%M:%S]"), *a, flush=True)


def norm(s):
    return " ".join(s.split()).rstrip(";").strip()


@torch.no_grad()
def test_loss(model, tok, rows):
    """Mean cross-entropy per answer token (same text format and 256-token cut as training)."""
    enc = [C.encode_example(tok, r) for r in rows]
    tot, n = 0.0, 0
    for s in range(0, len(enc), LOSS_BATCH):
        b = C.collate(tok, enc[s:s + LOSS_BATCH])
        k = int((b["labels"] != -100).sum())
        b = {x: v.to("cuda:0") for x, v in b.items()}
        with torch.autocast("cuda", dtype=torch.bfloat16):
            l = model(**b).loss.item()
        tot += l * k; n += k
    return tot / n


@torch.no_grad()
def generate(model, tok, rows):
    tok.padding_side = "left"
    preds = []
    order = sorted(range(len(rows)), key=lambda i: len(rows[i]["context"]) + len(rows[i]["question"]))
    out = [None] * len(rows)
    for s in range(0, len(order), GEN_BATCH):
        idx = order[s:s + GEN_BATCH]
        enc = tok([C.prompt_text(tok, rows[i]) for i in idx], return_tensors="pt", padding=True,
                  add_special_tokens=False).to("cuda:0")
        with torch.autocast("cuda", dtype=torch.bfloat16):
            g = model.generate(**enc, max_new_tokens=MAX_NEW, do_sample=False, temperature=None,
                               top_p=None, top_k=None, pad_token_id=tok.pad_token_id)
        for i, seq in zip(idx, g[:, enc["input_ids"].shape[1]:]):
            out[i] = tok.decode(seq, skip_special_tokens=True).strip()
    return out


def evaluate(model, tok, rows, tag, out):
    model.eval()
    t0 = time.time()
    loss = test_loss(model, tok, rows)
    preds = generate(model, tok, rows)
    hit = [norm(p) == norm(r["answer"]) for p, r in zip(preds, rows)]
    hit_ci = [norm(p).lower() == norm(r["answer"]).lower() for p, r in zip(preds, rows)]
    res = {"tag": tag, "n": len(rows), "exact_match": round(100 * sum(hit) / len(rows), 2),
           "exact_match_case_insensitive": round(100 * sum(hit_ci) / len(rows), 2),
           "correct": sum(hit), "test_loss": round(loss, 4), "eval_sec": round(time.time() - t0, 1)}
    with open(f"{out}/results/pred_{tag}.jsonl", "w") as f:
        for p, r, h in zip(preds, rows, hit):
            f.write(json.dumps({"question": r["question"], "gold": r["answer"], "pred": p, "em": h},
                               ensure_ascii=False) + "\n")
    json.dump(res, open(f"{out}/results/eval_{tag}.json", "w"), indent=1)
    log("EVAL_DONE", json.dumps(res))
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", nargs="*", default=["base", "epoch1", "epoch2", "epoch3"])
    ap.add_argument("--out", default="/workspace/mp4")
    a = ap.parse_args()
    todo = [t for t in a.tags if not os.path.exists(f"{a.out}/results/eval_{t}.json")]
    log("to evaluate:", todo)
    if todo:
        torch.manual_seed(C.SEED)
        tok = C.load_tokenizer()
        rows = C.read_jsonl(f"{a.out}/data/test.jsonl")
        model = C.load_base()
        if "base" in todo:
            evaluate(model, tok, rows, "base", a.out)      # plain model, no adapter attached
        ep_tags = [t for t in todo if t != "base"]
        if ep_tags:
            model = get_peft_model(model, LoraConfig(**C.LORA))
            for t in ep_tags:
                sd = load_file(f"{a.out}/ckpt/{t}/adapter_model.safetensors")
                res = set_peft_model_state_dict(model, sd)
                assert not res.unexpected_keys, res.unexpected_keys
                evaluate(model, tok, rows, t, a.out)
    allr = [json.load(open(f"{a.out}/results/eval_{t}.json")) for t in a.tags
            if os.path.exists(f"{a.out}/results/eval_{t}.json")]
    json.dump(allr, open(f"{a.out}/results/eval_all.json", "w"), indent=1)
    log("EVAL_ALL_DONE")
