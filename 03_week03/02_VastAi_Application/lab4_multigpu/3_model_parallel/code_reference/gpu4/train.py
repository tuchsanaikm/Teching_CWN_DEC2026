"""LoRA fine-tuning of Qwen3-8B (text -> SQL) with Model Parallelism on 4 GPUs.

One copy of the model; its 36 decoder layers are split into 4 equal parts (9 each),
part k on GPU k. Activations flow GPU0 -> GPU1 -> GPU2 -> GPU3, gradients flow back.

  python train.py probe                 # find the largest batch (1,2,4,8,... 3 steps each, longest example)
  python train.py train --batch N       # 3 epochs; resumes from the last finished epoch
Fixed: bf16, thinking off, no gradient checkpointing, LoRA r8/alpha16 on q_proj+v_proj,
lr 2e-4, seed 0, max 256 tokens.
"""
import argparse, gc, json, os, subprocess, time
import torch
from peft import LoraConfig, get_peft_model
from peft.utils import set_peft_model_state_dict
from safetensors.torch import load_file

import common as C

LR, EPOCHS, PROBE_STEPS = 2e-4, 3, 3


def log(*a):
    print(time.strftime("[%H:%M:%S]"), *a, flush=True)


def build(out):
    torch.manual_seed(C.SEED)
    tok = C.load_tokenizer()
    model = C.load_base()
    assert not model.is_gradient_checkpointing
    model = get_peft_model(model, LoraConfig(**C.LORA))
    place = C.placement(model)
    n_train = sum(p.numel() for p in model.parameters() if p.requires_grad)
    n_all = sum(p.numel() for p in model.parameters())
    place["trainable_params"], place["total_params"] = n_train, n_all
    json.dump(place, open(f"{out}/results/placement.json", "w"), indent=1)
    log("placement", json.dumps({k: v for k, v in place.items() if k != "layer_to_gpu"}))
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=LR, weight_decay=0.0)
    return tok, model, opt


def step(model, opt, batch):
    """One optimisation step. Inputs enter on GPU 0; HF moves labels to the logits' GPU."""
    batch = {k: v.to("cuda:0") for k, v in batch.items()}
    with torch.autocast("cuda", dtype=torch.bfloat16):
        loss = model(**batch).loss
    loss.backward()
    opt.step()
    opt.zero_grad(set_to_none=True)
    return loss


def smi_used():
    r = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                       capture_output=True, text=True).stdout.split()
    return [int(x) for x in r]


def probe(args):
    out = args.out
    tok, model, opt = build(out)
    rows = C.read_jsonl(f"{out}/data/train.jsonl")
    enc = [C.encode_example(tok, r) for r in rows]
    lens = [len(i) for i, _ in enc]
    k = max(range(len(enc)), key=lambda j: lens[j])
    raw_long = sum(1 for r in rows if len(tok(C.prompt_text(tok, r) + r["answer"] + "<|im_end|>",
                                              add_special_tokens=False)["input_ids"]) > C.MAX_LEN)
    info = {"longest_tokens": lens[k], "longest_index": k, "mean_tokens": round(sum(lens) / len(lens), 1),
            "n_over_max_len_truncated": raw_long, "max_len": C.MAX_LEN, "steps_per_batch": PROBE_STEPS,
            "runs": []}
    log(f"longest example: {lens[k]} tokens (index {k}); mean {info['mean_tokens']}; truncated {raw_long}")
    model.train()
    bs, best = 1, None
    while bs <= 4096:
        gc.collect()
        for d in range(torch.cuda.device_count()):
            torch.cuda.empty_cache(); torch.cuda.reset_peak_memory_stats(d)
        run = {"batch": bs, "ok": False}
        oom = None
        try:
            batch = C.collate(tok, [enc[k]] * bs)
            C.sync_all(); t0 = time.time()
            losses = []
            for _ in range(PROBE_STEPS):
                losses.append(step(model, opt, batch).item())
            C.sync_all()
            run.update(ok=True, sec_per_step=round((time.time() - t0) / PROBE_STEPS, 3), losses=[round(x, 4) for x in losses])
        except torch.OutOfMemoryError as e:
            oom = str(e).split("\n")[0][:200]
        run["mem"] = C.gpu_mem_gb()
        run["smi_used_mib"] = smi_used()
        if oom:
            run["error"] = oom
            opt.zero_grad(set_to_none=True)
        info["runs"].append(run)
        log(f"probe batch {bs}: {'OK' if run['ok'] else 'OOM'}",
            "peak_reserved_gb", [m["peak_reserved_gb"] for m in run["mem"]],
            "sec/step", run.get("sec_per_step"), run.get("error", ""))
        json.dump(info, open(f"{out}/results/probe.json", "w"), indent=1)
        if not run["ok"]:
            break
        best = bs
        bs *= 2
    info["max_batch"] = best
    json.dump(info, open(f"{out}/results/probe.json", "w"), indent=1)
    log("PROBE_DONE max_batch", best)


def train(args):
    out, bs = args.out, args.batch
    ck = f"{out}/ckpt"
    os.makedirs(ck, exist_ok=True)
    tok, model, opt = build(out)
    rows = C.read_jsonl(f"{out}/data/train.jsonl")
    enc = [C.encode_example(tok, r) for r in rows]
    steps_per_epoch = (len(enc) + bs - 1) // bs
    state_f = f"{ck}/state.json"
    state = {"batch": bs, "epochs_done": 0, "epochs": []}
    if os.path.exists(state_f):
        old = json.load(open(state_f))
        if old["batch"] == bs and old["epochs_done"] > 0:
            state = old
            e = state["epochs_done"]
            sd = load_file(f"{ck}/epoch{e}/adapter_model.safetensors")
            set_peft_model_state_dict(model, sd)
            opt.load_state_dict(torch.load(f"{ck}/optimizer.pt"))
            log(f"RESUME after epoch {e}")
    model.train()
    for ep in range(state["epochs_done"] + 1, EPOCHS + 1):
        g = torch.Generator().manual_seed(C.SEED * 1000 + ep)   # same order even after a resume
        perm = torch.randperm(len(enc), generator=g).tolist()
        for d in range(torch.cuda.device_count()):
            torch.cuda.reset_peak_memory_stats(d)
        util_f = f"{out}/results/gpu_util_epoch{ep}.csv"
        mon = subprocess.Popen(["nvidia-smi", "--query-gpu=index,utilization.gpu,memory.used",
                                "--format=csv,noheader,nounits", "-l", "1", "-f", util_f])
        C.sync_all(); t0 = time.time(); tl = t0
        tot, win, n_tok = 0.0, 0.0, 0
        for s in range(steps_per_epoch):
            batch = C.collate(tok, [enc[j] for j in perm[s * bs:(s + 1) * bs]])
            n_tok += int(batch["attention_mask"].sum())
            l = step(model, opt, batch).item()
            tot += l; win += l
            if (s + 1) % 10 == 0 or s + 1 == steps_per_epoch:
                C.sync_all(); now = time.time()
                k = 10 if (s + 1) % 10 == 0 else (s + 1) % 10
                el = now - t0
                log(f"epoch {ep}/{EPOCHS} step {s+1}/{steps_per_epoch} loss {win/k:.4f} "
                    f"{(now-tl)/k:.3f}s/step elapsed {el:.0f}s eta_epoch {el/(s+1)*(steps_per_epoch-s-1):.0f}s")
                win, tl = 0.0, now
        C.sync_all(); dt = time.time() - t0
        mon.terminate(); mon.wait()
        util = {}
        for line in open(util_f):
            p = [x.strip() for x in line.split(",")]
            if len(p) == 3 and p[1].isdigit():
                util.setdefault(int(p[0]), []).append((int(p[1]), int(p[2])))
        rec = {"epoch": ep, "steps": steps_per_epoch, "train_loss_mean": round(tot / steps_per_epoch, 4),
               "train_sec": round(dt, 1), "sec_per_step": round(dt / steps_per_epoch, 4),
               "samples_per_sec": round(len(enc) / dt, 2), "tokens_per_sec": round(n_tok / dt, 1),
               "gpu_util_mean_pct": {f"gpu{d}": round(sum(u for u, _ in v) / len(v), 1) for d, v in sorted(util.items())},
               "gpu_util_samples": len(util.get(0, [])),
               "smi_mem_used_max_mib": {f"gpu{d}": max(m for _, m in v) for d, v in sorted(util.items())},
               "mem": C.gpu_mem_gb()}
        model.save_pretrained(f"{ck}/epoch{ep}")
        torch.save(opt.state_dict(), f"{ck}/optimizer.pt")
        state["epochs"].append(rec); state["epochs_done"] = ep
        json.dump(state, open(state_f + ".tmp", "w"), indent=1); os.replace(state_f + ".tmp", state_f)
        json.dump(state, open(f"{out}/results/train.json", "w"), indent=1)
        log("EPOCH_DONE", json.dumps(rec))
    log("TRAIN_DONE")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["probe", "train"])
    ap.add_argument("--batch", type=int)
    ap.add_argument("--out", default="/workspace/mp4")
    a = ap.parse_args()
    os.makedirs(f"{a.out}/results", exist_ok=True)
    assert torch.cuda.device_count() == 4, "this script expects 4 GPUs"
    probe(a) if a.mode == "probe" else train(a)
