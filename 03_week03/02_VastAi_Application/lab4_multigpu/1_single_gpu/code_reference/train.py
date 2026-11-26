"""Lab 4 / 1_single_gpu: LoRA fine-tuning of Qwen3-8B (question -> SQL) on ONE GPU.

The whole model and the whole batch live on cuda:0.

  python train.py --probe                 # batch 1,2,4,8,... x 3 steps on the longest example, until OOM
  python train.py --batch-size N          # train 3 epochs, eval on Test Set after every epoch
                                          # (re-running the same command resumes from the last checkpoint)

Fixed: bf16, thinking off, no gradient checkpointing, LoRA r=8 alpha=16 on q_proj+v_proj,
lr 2e-4 (constant, AdamW), seed 0, max 256 tokens.
"""
import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import time

import numpy as np
import torch

import common as C

LR = 2e-4
EPOCHS = 3
PROBE_STEPS = 3


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def log(msg):
    print(f"[{C.now()}] {msg}", flush=True)


def train_step(model, opt, batch):
    # No attention_mask on purpose: batches are RIGHT padded and attention is causal, so real
    # tokens never see the padding and padded positions have label -100 -> same loss/gradients.
    # Passing a mask with padding makes attention take a path that needs more VRAM than the
    # all-real-tokens batch used by the probe (that caused an OOM at batch 4 in the first run).
    ids, _, labels = batch
    with torch.autocast("cuda", dtype=torch.bfloat16):
        logits = model(input_ids=ids).logits
    loss = torch.nn.functional.cross_entropy(
        logits[:, :-1].float().reshape(-1, logits.size(-1)),
        labels[:, 1:].reshape(-1), ignore_index=-100,
    )
    loss.backward()
    opt.step()
    opt.zero_grad(set_to_none=True)
    return loss.item()


def build_model():
    model = C.add_lora(C.load_base_model())
    model.config.use_cache = False
    model.train()
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=LR)
    return model, opt, params


# ----------------------------------------------------------------------------- probe
def probe_one(bs):
    """3 training steps with `bs` copies of the longest training example. Prints one JSON line."""
    set_seed(C.SEED)
    tok = C.load_tokenizer()
    rows = C.read_jsonl(os.path.join(C.DATA_DIR, "train.jsonl"))
    enc = [C.encode_example(tok, r) for r in rows]
    longest = max(enc, key=lambda e: e["full_len"])
    res = {"batch": bs, "tokens": len(longest["input_ids"]), "full_len": longest["full_len"],
           "steps": PROBE_STEPS}
    mon = C.GpuMonitor(0.25).start()
    try:
        model, opt, _ = build_model()
        res["model_vram_gb"] = round(torch.cuda.memory_allocated() / 2**30, 2)
        torch.cuda.reset_peak_memory_stats()
        times, losses = [], []
        for _ in range(PROBE_STEPS):
            t = time.time()
            batch = C.collate([longest] * bs, tok.pad_token_id)
            losses.append(train_step(model, opt, batch))
            torch.cuda.synchronize()
            times.append(time.time() - t)
        res.update(status="ok", sec_per_step=round(sum(times[1:]) / len(times[1:]), 3),
                   losses=[round(x, 4) for x in losses])
    except torch.OutOfMemoryError as e:
        res.update(status="oom", error=str(e).split("\n")[0][:200])
    res["peak_allocated_gb"] = round(torch.cuda.max_memory_allocated() / 2**30, 2)
    res["peak_reserved_gb"] = round(torch.cuda.max_memory_reserved() / 2**30, 2)
    mon.stop()
    _, mem, _ = mon.take()
    res["nvidia_smi_peak_gb"] = round(mem / 1024, 2) if mem else None
    print("PROBE_RESULT " + json.dumps(res), flush=True)


def probe():
    """Double the batch size until Out of Memory. Each size runs in a fresh process."""
    out_path = os.path.join(C.RESULTS_DIR, "probe.json")
    results = []
    if os.path.exists(out_path):
        results = json.load(open(out_path)).get("results", [])
    done = {r["batch"] for r in results}
    total = float(subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits", "-i", "0"],
        capture_output=True, text=True).stdout.strip()) / 1024
    bs = 1
    while bs <= 1024:
        if bs not in done:
            log(f"probe batch={bs} ...")
            p = subprocess.run([sys.executable, os.path.abspath(__file__), "--probe-one", str(bs)],
                               capture_output=True, text=True)
            line = [l for l in p.stdout.splitlines() if l.startswith("PROBE_RESULT ")]
            if line:
                r = json.loads(line[-1][len("PROBE_RESULT "):])
            else:  # killed or crashed in a way other than a python OOM exception
                r = {"batch": bs, "status": "oom" if "out of memory" in p.stderr.lower() else "error",
                     "error": p.stderr.strip().splitlines()[-1][:200] if p.stderr.strip() else "no output"}
            results.append(r)
            log("probe result " + json.dumps(r))
        last = [r for r in results if r["batch"] == bs][0]
        ok = [r["batch"] for r in results if r["status"] == "ok"]
        C.write_json(out_path, {"gpu_total_gb": round(total, 2), "results": results,
                                "max_batch": max(ok) if ok else None,
                                "finished": last["status"] != "ok"})
        if last["status"] != "ok":
            break
        bs *= 2
    log(f"probe finished: max batch = {max(ok) if ok else None}")


# ----------------------------------------------------------------------------- train
def save_checkpoint(model, opt, state, run_dir):
    """Atomic: write to a temp dir, then swap."""
    tmp, dst = os.path.join(run_dir, "ckpt_tmp"), os.path.join(run_dir, "ckpt_last")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    lora = {n: p.detach().cpu() for n, p in model.named_parameters() if p.requires_grad}
    torch.save({"lora": lora, "opt": opt.state_dict(), "state": state}, os.path.join(tmp, "ckpt.pt"))
    old = dst + "_old"
    shutil.rmtree(old, ignore_errors=True)
    if os.path.exists(dst):
        os.rename(dst, old)
    os.rename(tmp, dst)
    shutil.rmtree(old, ignore_errors=True)


def load_checkpoint(model, opt, run_dir):
    for name in ("ckpt_last", "ckpt_last_old"):
        path = os.path.join(run_dir, name, "ckpt.pt")
        if os.path.exists(path):
            ck = torch.load(path, map_location="cpu")
            named = dict(model.named_parameters())
            with torch.no_grad():
                for n, v in ck["lora"].items():
                    named[n].copy_(v)
            opt.load_state_dict(ck["opt"])
            return ck["state"]
    return None


def train(args):
    from eval import evaluate

    bs = args.batch_size
    os.makedirs(C.RESULTS_DIR, exist_ok=True)
    os.makedirs(C.RUN_DIR, exist_ok=True)
    set_seed(C.SEED)
    tok = C.load_tokenizer()
    train_rows = C.read_jsonl(os.path.join(C.DATA_DIR, "train.jsonl"))
    test_rows = C.read_jsonl(os.path.join(C.DATA_DIR, "test.jsonl"))
    enc = [C.encode_example(tok, r) for r in train_rows]
    n_trunc = sum(e["full_len"] > C.MAX_LEN for e in enc)
    lens = [len(e["input_ids"]) for e in enc]
    steps_per_epoch = (len(enc) + bs - 1) // bs
    log(f"train={len(enc)} test={len(test_rows)} batch={bs} steps/epoch={steps_per_epoch} "
        f"epochs={EPOCHS} tokens mean={sum(lens)/len(lens):.1f} max={max(lens)} truncated={n_trunc}")

    model, opt, params = build_model()
    n_train = sum(p.numel() for p in params)
    log(f"model loaded: {torch.cuda.memory_allocated()/2**30:.2f} GB on cuda:0, "
        f"trainable LoRA params={n_train:,}")

    state = load_checkpoint(model, opt, C.RUN_DIR)
    if state is None or state["batch_size"] != bs:
        state = {"batch_size": bs, "epoch": 0, "step": 0, "global_step": 0,
                 "loss_sum": 0.0, "train_seconds": 0.0, "samples": 0,
                 "util_sum": 0.0, "util_n": 0, "peak_gb": 0.0, "history": []}
    else:
        log(f"RESUMED from checkpoint: epoch={state['epoch']+1} step={state['step']} "
            f"global_step={state['global_step']}")

    metrics_path = os.path.join(C.RESULTS_DIR, "train_metrics.json")
    step_log = open(os.path.join(C.RESULTS_DIR, "train_log.jsonl"), "a")
    mon = C.GpuMonitor(1.0).start()
    torch.cuda.reset_peak_memory_stats()

    def write_metrics(finished=False):
        C.write_json(metrics_path, {
            "batch_size": bs, "lr": LR, "epochs": EPOCHS, "seed": C.SEED, "max_len": C.MAX_LEN,
            "lora": {"r": C.LORA_R, "alpha": C.LORA_ALPHA, "targets": C.LORA_TARGETS,
                     "trainable_params": n_train},
            "train_examples": len(enc), "steps_per_epoch": steps_per_epoch,
            "truncated_examples": n_trunc, "history": state["history"], "finished": finished,
        })

    while state["epoch"] < EPOCHS:
        ep = state["epoch"]
        perm = np.random.RandomState(C.SEED + ep).permutation(len(enc))
        win_loss, win_t, win_n = 0.0, time.time(), 0
        while state["step"] < steps_per_epoch:
            s = state["step"]
            idx = perm[s * bs:(s + 1) * bs]
            t = time.time()
            loss = train_step(model, opt, C.collate([enc[i] for i in idx], tok.pad_token_id))
            torch.cuda.synchronize()
            dt = time.time() - t
            state["step"] += 1
            state["global_step"] += 1
            state["loss_sum"] += loss
            state["train_seconds"] += dt
            state["samples"] += len(idx)
            win_loss += loss
            win_n += 1
            if state["step"] % args.log_every == 0 or state["step"] == steps_per_epoch:
                util, mem, n = mon.take()
                if n:
                    state["util_sum"] += util * n
                    state["util_n"] += n
                state["peak_gb"] = max(state["peak_gb"], torch.cuda.max_memory_allocated() / 2**30)
                sps = (time.time() - win_t) / win_n
                left = (steps_per_epoch - state["step"]) + (EPOCHS - ep - 1) * steps_per_epoch
                rec = {"epoch": ep + 1, "step": state["step"], "global_step": state["global_step"],
                       "loss": round(win_loss / win_n, 4), "sec_per_step": round(sps, 3),
                       "samples_per_sec": round(bs / sps, 2),
                       "gpu_util": round(util, 1) if util is not None else None,
                       "vram_gb": round(mem / 1024, 2) if mem else None}
                step_log.write(json.dumps(rec) + "\n")
                step_log.flush()
                log(f"epoch {ep+1}/{EPOCHS} step {state['step']}/{steps_per_epoch} "
                    f"loss={rec['loss']:.4f} {rec['sec_per_step']:.2f}s/step "
                    f"{rec['samples_per_sec']:.1f} samples/s util={rec['gpu_util']}% "
                    f"vram={rec['vram_gb']}GB train-ETA={left*sps/60:.1f}min")
                win_loss, win_t, win_n = 0.0, time.time(), 0
            if state["step"] % args.save_every == 0 or state["step"] == steps_per_epoch:
                save_checkpoint(model, opt, state, C.RUN_DIR)

        # ---- end of epoch: save adapter, evaluate on the Test Set
        adapter_dir = os.path.join(C.RUN_DIR, f"adapter_epoch{ep+1}")
        model.save_pretrained(adapter_dir)
        log(f"epoch {ep+1} training done, evaluating on Test Set ...")
        mon.take()
        res = evaluate(model, tok, test_rows, log=log)
        mon.take()
        res["tag"] = f"epoch{ep+1}"
        res["adapter"] = adapter_dir
        C.write_json(os.path.join(C.RESULTS_DIR, f"eval_epoch{ep+1}.json"), res)
        h = {
            "epoch": ep + 1,
            "train_loss": state["loss_sum"] / steps_per_epoch,
            "test_loss": res["loss"],
            "exact_match": res["exact_match"],
            "exact_match_relaxed": res["exact_match_relaxed"],
            "n_correct": res["n_correct"], "n_test": res["n"],
            "steps": steps_per_epoch,
            "train_seconds": round(state["train_seconds"], 1),
            "sec_per_step": round(state["train_seconds"] / steps_per_epoch, 4),
            "samples_per_sec": round(state["samples"] / state["train_seconds"], 3),
            "gpu_util_mean": round(state["util_sum"] / max(state["util_n"], 1), 1),
            "peak_allocated_gb": round(state["peak_gb"], 2),
            "eval_seconds": res["eval_seconds"],
        }
        state["history"].append(h)
        log(f"EPOCH {ep+1} DONE train_loss={h['train_loss']:.4f} test_loss={h['test_loss']:.4f} "
            f"EM={h['exact_match']:.4f} ({h['n_correct']}/{h['n_test']}) "
            f"{h['sec_per_step']:.3f}s/step {h['samples_per_sec']:.2f} samples/s "
            f"util={h['gpu_util_mean']}%")
        state.update(epoch=ep + 1, step=0, loss_sum=0.0, train_seconds=0.0, samples=0,
                     util_sum=0.0, util_n=0, peak_gb=0.0)
        torch.cuda.reset_peak_memory_stats()
        save_checkpoint(model, opt, state, C.RUN_DIR)
        write_metrics()

    mon.stop()
    write_metrics(finished=True)
    log("TRAINING FINISHED")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true", help="find the largest batch size")
    ap.add_argument("--probe-one", type=int, default=None, help=argparse.SUPPRESS)
    ap.add_argument("--batch-size", type=int, default=None)
    ap.add_argument("--log-every", type=int, default=10)
    ap.add_argument("--save-every", type=int, default=100)
    args = ap.parse_args()
    os.makedirs(C.RESULTS_DIR, exist_ok=True)
    if args.probe_one is not None:
        probe_one(args.probe_one)
    elif args.probe:
        probe()
    else:
        if args.batch_size is None:
            args.batch_size = json.load(open(os.path.join(C.RESULTS_DIR, "probe.json")))["max_batch"]
        train(args)


if __name__ == "__main__":
    main()
