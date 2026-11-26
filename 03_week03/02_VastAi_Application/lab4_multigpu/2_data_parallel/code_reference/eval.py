"""Lab4 / 2_data_parallel - Exact Match + loss on the test set.

Evaluates the model before training (base) and the LoRA adapter saved after
each epoch. The test set is split over the GPUs (one worker process per GPU).

    python eval.py --tags base,epoch1,epoch2,epoch3
"""
import argparse
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MODEL_NAME, build_prompt, collate, encode_example, read_jsonl, write_json  # noqa: E402


def clean_sql(text):
    """Take the SQL out of the model reply (drop a markdown fence if there is one)."""
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, flags=re.S | re.I)
    if m:
        text = m.group(1)
    return " ".join(text.split())


def relaxed(sql):
    return " ".join(sql.replace("'", '"').rstrip("; ").lower().split())


def worker(args):
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = torch.device("cuda", 0)  # CUDA_VISIBLE_DEVICES picks the real GPU
    model_dir = os.path.join(args.root, "models", MODEL_NAME)
    out_dir = os.path.join(args.root, "results", "eval")
    tok = AutoTokenizer.from_pretrained(model_dir)
    rows = read_jsonl(os.path.join(args.root, "data", "test.jsonl"))
    idx = list(range(len(rows)))[args.shard::args.n_shards]
    base = AutoModelForCausalLM.from_pretrained(model_dir, dtype=torch.bfloat16).to(device).eval()

    def say(msg):
        print(time.strftime("[%H:%M:%S] ") + f"[gpu{args.shard}] {msg}", flush=True)

    for tag in args.tags.split(","):
        out = os.path.join(out_dir, f"{tag}_shard{args.shard}.json")
        if os.path.exists(out):
            say(f"{tag}: already done, skip")
            continue
        model = base if tag == "base" else PeftModel.from_pretrained(
            base, os.path.join(args.root, "ckpt", tag)).eval()
        t0 = time.time()
        # ---- loss on the SQL answer tokens (same format as training) ----
        loss_sum, n_tok = 0.0, 0
        tok.padding_side = "right"
        for b in range(0, len(idx), args.bs):
            ex = [encode_example(tok, rows[i], args.max_len)[:2] for i in idx[b:b + args.bs]]
            ids, att, lab = collate(ex, tok.pad_token_id, device)
            with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
                logits = model(input_ids=ids, attention_mask=att).logits
            ce = torch.nn.functional.cross_entropy(
                logits[:, :-1].float().reshape(-1, logits.shape[-1]), lab[:, 1:].reshape(-1),
                ignore_index=-100, reduction="sum")
            loss_sum += ce.item()
            n_tok += int((lab[:, 1:] != -100).sum())
        # ---- greedy generation ----
        tok.padding_side = "left"
        items = []
        for b in range(0, len(idx), args.bs):
            chunk = idx[b:b + args.bs]
            enc = tok([build_prompt(tok, rows[i]) for i in chunk], return_tensors="pt",
                      padding=True, add_special_tokens=False).to(device)
            with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
                gen = model.generate(**enc, max_new_tokens=args.max_new_tokens, do_sample=False,
                                     temperature=None, top_p=None, top_k=None,
                                     pad_token_id=tok.pad_token_id)
            texts = tok.batch_decode(gen[:, enc.input_ids.shape[1]:], skip_special_tokens=True)
            for i, t in zip(chunk, texts):
                pred, gold = clean_sql(t), " ".join(rows[i]["answer"].split())
                items.append({"i": i, "question": rows[i]["question"], "gold": gold, "pred": pred,
                              "raw": t, "em": pred == gold, "em_relaxed": relaxed(pred) == relaxed(gold)})
            say(f"{tag}: generated {min(b + args.bs, len(idx))}/{len(idx)} "
                f"EM so far {sum(x['em'] for x in items)}/{len(items)}")
        write_json(out, {"tag": tag, "shard": args.shard, "loss_sum": loss_sum, "n_tok": n_tok,
                         "sec": round(time.time() - t0, 1), "items": items})
        say(f"{tag}: shard done in {time.time() - t0:.0f}s")
        if tag != "base":
            base = model.unload()  # take the LoRA layers out again


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/workspace/lab4_dp")
    ap.add_argument("--tags", default="base,epoch1,epoch2,epoch3")
    ap.add_argument("--n-shards", type=int, default=2, help="number of GPUs to use")
    ap.add_argument("--shard", type=int, default=-1, help="internal: worker id")
    ap.add_argument("--bs", type=int, default=10)
    ap.add_argument("--max-len", type=int, default=256)
    ap.add_argument("--max-new-tokens", type=int, default=160)
    args = ap.parse_args()

    if args.shard >= 0:
        return worker(args)

    out_dir = os.path.join(args.root, "results", "eval")
    os.makedirs(out_dir, exist_ok=True)
    procs = []
    for s in range(args.n_shards):
        env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(s))
        procs.append(subprocess.Popen([sys.executable, os.path.abspath(__file__)] + sys.argv[1:]
                                      + ["--shard", str(s)], env=env))
    if any(p.wait() != 0 for p in procs):
        sys.exit("an eval worker failed")

    import json
    summary = []
    for tag in args.tags.split(","):
        parts = [json.load(open(os.path.join(out_dir, f"{tag}_shard{s}.json"))) for s in range(args.n_shards)]
        items = sorted((x for p in parts for x in p["items"]), key=lambda x: x["i"])
        n = len(items)
        row = {"tag": tag, "n_test": n,
               "test_loss": round(sum(p["loss_sum"] for p in parts) / sum(p["n_tok"] for p in parts), 4),
               "em_count": sum(x["em"] for x in items), "exact_match_pct": round(100 * sum(x["em"] for x in items) / n, 2),
               "em_relaxed_pct": round(100 * sum(x["em_relaxed"] for x in items) / n, 2)}
        summary.append(row)
        write_json(os.path.join(out_dir, f"{tag}_predictions.json"), items)
        print(row, flush=True)
    write_json(os.path.join(args.root, "results", "eval_summary.json"), summary)
    print("EVAL DONE", flush=True)


if __name__ == "__main__":
    main()
