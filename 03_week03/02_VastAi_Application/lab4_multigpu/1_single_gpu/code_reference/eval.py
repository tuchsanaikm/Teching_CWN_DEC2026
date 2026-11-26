"""Lab 4 / 1_single_gpu: Exact Match (and loss) on the Test Set.

  python eval.py --tag base                              # model before training
  python eval.py --tag epoch1 --adapter <adapter_dir>    # after an epoch

train.py also calls evaluate() in-process at the end of every epoch.

Exact Match (EM): generated SQL == reference SQL after collapsing whitespace and
dropping a trailing ';' (case- and quote-sensitive).
EM relaxed (extra, for reference): also strips ``` fences, lower-cases, and treats ' and " alike.
Loss: token-level cross-entropy on the reference SQL (teacher forcing, <=256 tokens).
"""
import argparse
import os
import re
import time

import torch

import common as C


def norm_strict(s):
    s = " ".join(s.split())
    return s.rstrip(";").strip()


def norm_relaxed(s):
    s = re.sub(r"```(?:sql)?", "", s, flags=re.I)
    s = norm_strict(s).lower().replace('"', "'")
    return s


@torch.no_grad()
def evaluate(model, tok, rows, batch_size=16, max_new_tokens=128, log=print):
    was_training = model.training
    model.eval()
    pad_id = tok.pad_token_id
    t0 = time.time()

    # 1) loss on the reference answer (same encoding as training)
    enc = [C.encode_example(tok, r) for r in rows]
    loss_sum, n_tok = 0.0, 0
    for i in range(0, len(enc), batch_size):
        ids, _, labels = C.collate(enc[i:i + batch_size], pad_id)  # right padded: no mask needed
        with torch.autocast("cuda", dtype=torch.bfloat16):
            logits = model(input_ids=ids).logits
        lp = torch.nn.functional.cross_entropy(
            logits[:, :-1].float().reshape(-1, logits.size(-1)),
            labels[:, 1:].reshape(-1), ignore_index=-100, reduction="sum",
        )
        loss_sum += lp.item()
        n_tok += int((labels[:, 1:] != -100).sum())
        del logits

    # 2) greedy generation from the full prompt (left padded)
    prompts = [tok(C.build_prompt(tok, r), add_special_tokens=False)["input_ids"] for r in rows]
    order = sorted(range(len(rows)), key=lambda i: len(prompts[i]))
    preds = [None] * len(rows)
    eos_ids = [tok.convert_tokens_to_ids("<|im_end|>"), tok.eos_token_id]
    for b in range(0, len(order), batch_size):
        idx = order[b:b + batch_size]
        n = max(len(prompts[i]) for i in idx)
        ids = torch.full((len(idx), n), pad_id, dtype=torch.long)
        mask = torch.zeros((len(idx), n), dtype=torch.long)
        for j, i in enumerate(idx):
            k = len(prompts[i])
            ids[j, n - k:] = torch.tensor(prompts[i])
            mask[j, n - k:] = 1
        with torch.autocast("cuda", dtype=torch.bfloat16):
            out = model.generate(
                input_ids=ids.cuda(), attention_mask=mask.cuda(),
                max_new_tokens=max_new_tokens, do_sample=False,
                temperature=None, top_p=None, top_k=None,
                eos_token_id=eos_ids, pad_token_id=pad_id,
            )
        for j, i in enumerate(idx):
            preds[i] = tok.decode(out[j, n:], skip_special_tokens=True).strip()
        log(f"[eval] generated {min(b + batch_size, len(order))}/{len(order)}")

    em = [norm_strict(p) == norm_strict(r["answer"]) for p, r in zip(preds, rows)]
    emr = [norm_relaxed(p) == norm_relaxed(r["answer"]) for p, r in zip(preds, rows)]
    result = {
        "n": len(rows),
        "loss": loss_sum / max(n_tok, 1),
        "exact_match": sum(em) / len(rows),
        "exact_match_relaxed": sum(emr) / len(rows),
        "n_correct": sum(em),
        "eval_seconds": round(time.time() - t0, 1),
        "predictions": [
            {"question": r["question"], "gold": r["answer"], "pred": p, "em": bool(e)}
            for r, p, e in zip(rows, preds, em)
        ],
    }
    if was_training:
        model.train()
    torch.cuda.empty_cache()
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True, help="base | epoch1 | epoch2 | ...")
    ap.add_argument("--adapter", default=None, help="LoRA adapter dir (omit for base model)")
    ap.add_argument("--batch-size", type=int, default=16)
    args = ap.parse_args()

    os.makedirs(C.RESULTS_DIR, exist_ok=True)
    tok = C.load_tokenizer()
    rows = C.read_jsonl(os.path.join(C.DATA_DIR, "test.jsonl"))
    print(f"[{C.now()}] eval tag={args.tag} adapter={args.adapter} test={len(rows)}", flush=True)
    model = C.load_base_model()
    if args.adapter:
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, args.adapter)
    res = evaluate(model, tok, rows, batch_size=args.batch_size,
                   log=lambda s: print(s, flush=True))
    res["tag"] = args.tag
    res["adapter"] = args.adapter
    C.write_json(os.path.join(C.RESULTS_DIR, f"eval_{args.tag}.json"), res)
    print(f"[{C.now()}] RESULT tag={args.tag} loss={res['loss']:.4f} "
          f"EM={res['exact_match']:.4f} ({res['n_correct']}/{res['n']}) "
          f"EM_relaxed={res['exact_match_relaxed']:.4f} time={res['eval_seconds']}s", flush=True)
    for p in res["predictions"][:3]:
        print("  gold:", p["gold"], "\n  pred:", p["pred"], flush=True)


if __name__ == "__main__":
    main()
