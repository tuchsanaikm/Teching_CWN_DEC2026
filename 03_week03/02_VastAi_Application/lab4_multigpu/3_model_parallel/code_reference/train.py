#!/usr/bin/env python3
"""เทรน Qwen3-8B + LoRA แบบ Model Parallelism (โมเดลชุดเดียว แบ่งครึ่งลง GPU 2 ใบ)

  python train.py --probe 8            ลอง batch 8 จำนวน 3 step ด้วยตัวอย่างที่ยาวที่สุด
  python train.py --batch 8 --epochs 3 เทรนจริง (รันซ้ำได้ จะทำต่อจาก Epoch ล่าสุดที่บันทึกไว้)
"""
import argparse
import json
import os
import subprocess
import time

import torch

from common import (CKPT_DIR, MAX_LEN, RESULT_DIR, SEED, TRAIN_FILE, GpuMonitor, add_lora,
                    collate, encode_example, layer_placement, load_base_model,
                    load_tokenizer, read_jsonl, vram_peaks)

LR = 2e-4
MAX_GRAD_NORM = 1.0
ADAPTER_FILE = "adapter_model.safetensors"


def sync():
    for i in range(torch.cuda.device_count()):
        torch.cuda.synchronize(i)


def smi_mem():
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
        capture_output=True, text=True).stdout.split()
    return {f"gpu{i}": int(v) for i, v in enumerate(out)}


def train_step(model, opt, batch, params):
    """1 step: forward ไหลจาก GPU 0 -> GPU 1, backward ไหลย้อนกลับ"""
    ids, att, lab = batch
    with torch.autocast("cuda", dtype=torch.bfloat16):
        loss = model(input_ids=ids, attention_mask=att, labels=lab).loss
    loss.backward()
    torch.nn.utils.clip_grad_norm_(params, MAX_GRAD_NORM)
    opt.step()
    opt.zero_grad(set_to_none=True)
    return loss


def build(seed=SEED):
    torch.manual_seed(seed)
    tok = load_tokenizer()
    model = add_lora(load_base_model())
    model.train()
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=LR, weight_decay=0.0)
    return tok, model, params, opt


def write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


# ---------------------------------------------------------------- probe
def probe(bs, steps=3):
    out_path = f"{RESULT_DIR}/probe_b{bs}.json"
    tok, model, params, opt = build()
    rows = read_jsonl(TRAIN_FILE)
    enc = [encode_example(tok, r) for r in rows]
    longest = max(enc, key=lambda e: len(e[0]))   # ตัวอย่างที่ยาวที่สุด (ตัดที่ 256 แล้ว)
    res = {"batch": bs, "steps": steps, "seq_len": len(longest[0]), "max_len": MAX_LEN}
    for i in range(torch.cuda.device_count()):
        torch.cuda.reset_peak_memory_stats(i)
    res["vram_model_only"] = vram_peaks()
    times, losses = [], []
    try:
        batch = collate(tok, [longest] * bs, "cuda:0")
        for s in range(steps):
            sync()
            t0 = time.time()
            loss = train_step(model, opt, batch, params)
            sync()
            times.append(round(time.time() - t0, 3))
            losses.append(round(loss.item(), 4))
            print(f"[probe] batch={bs} step={s + 1}/{steps} loss={losses[-1]} "
                  f"t={times[-1]}s", flush=True)
        res["status"] = "ok"
    except torch.OutOfMemoryError as e:
        res["status"] = "oom"
        res["error"] = str(e)[:300]
        res["steps_done"] = len(times)
        print(f"[probe] batch={bs} OUT OF MEMORY at step {len(times) + 1}: "
              f"{str(e)[:120]}", flush=True)
    res["step_sec"] = times
    res["loss"] = losses
    res["vram_peak"] = vram_peaks()
    res["smi_mem_used_mib"] = smi_mem()
    write_json(out_path, res)
    print("[probe]", json.dumps(res), flush=True)


# ---------------------------------------------------------------- train
def epoch_order(n, epoch):
    g = torch.Generator().manual_seed(SEED * 1000 + epoch)
    return torch.randperm(n, generator=g).tolist()


def train(bs, epochs):
    from peft import get_peft_model_state_dict, set_peft_model_state_dict
    from safetensors.torch import load_file
    tok, model, params, opt = build()
    rows = read_jsonl(TRAIN_FILE)
    enc = [encode_example(tok, r) for r in rows]
    steps_per_epoch = (len(enc) + bs - 1) // bs
    total_steps = steps_per_epoch * epochs
    sched = torch.optim.lr_scheduler.LambdaLR(     # linear decay แบบค่าเริ่มต้นของ HF Trainer
        opt, lambda s: max(0.0, 1.0 - s / total_steps))

    placement = layer_placement(model)
    n_train = sum(p.numel() for p in params)
    info = {"batch": bs, "epochs": epochs, "lr": LR, "seed": SEED, "max_len": MAX_LEN,
            "n_train": len(enc), "steps_per_epoch": steps_per_epoch,
            "trainable_params": n_train,
            "total_params": sum(p.numel() for p in model.parameters()),
            "gradient_checkpointing": bool(model.base_model.model.is_gradient_checkpointing),
            "dtype": "bfloat16", "placement": placement,
            "hf_device_map": {k: str(v) for k, v in model.base_model.model.hf_device_map.items()}}
    write_json(f"{RESULT_DIR}/layer_map.json", placement)
    print("[train] placement", json.dumps(placement), flush=True)
    print(f"[train] trainable={n_train:,} batch={bs} steps/epoch={steps_per_epoch}", flush=True)

    # ---- ทำต่อจาก Epoch ล่าสุดที่บันทึกครบ
    history, start_epoch = [], 0
    for e in range(epochs, 0, -1):
        d = f"{CKPT_DIR}/epoch{e}"
        if os.path.exists(f"{d}/state.pt"):
            st = torch.load(f"{d}/state.pt", weights_only=False)
            if st["batch"] != bs:
                continue
            set_peft_model_state_dict(model, load_file(f"{d}/{ADAPTER_FILE}"))
            opt.load_state_dict(st["opt"])
            sched.load_state_dict(st["sched"])
            history, start_epoch = st["history"], e
            print(f"[train] resume after epoch {e}", flush=True)
            break

    mon = GpuMonitor()
    step_log = open(f"{RESULT_DIR}/train_steps.jsonl", "a")
    t_run = time.time()
    for epoch in range(start_epoch + 1, epochs + 1):
        order = epoch_order(len(enc), epoch)
        for i in range(torch.cuda.device_count()):
            torch.cuda.reset_peak_memory_stats(i)
        mon.reset()
        mon.active = True
        sum_loss = sum_tok_loss = n_tok = 0.0
        step_times, n_samples = [], 0
        sync()
        t_epoch = time.time()
        for s in range(steps_per_epoch):
            idx = order[s * bs:(s + 1) * bs]
            sync()
            t0 = time.time()
            batch = collate(tok, [enc[j] for j in idx], "cuda:0")
            loss = train_step(model, opt, batch, params)
            sched.step()
            lv = loss.item()
            sync()
            dt = time.time() - t0
            step_times.append(dt)
            n_samples += len(idx)
            nt = int((batch[2] != -100).sum())
            sum_loss += lv
            sum_tok_loss += lv * nt
            n_tok += nt
            gstep = (epoch - 1) * steps_per_epoch + s + 1
            step_log.write(json.dumps({"epoch": epoch, "step": gstep, "loss": round(lv, 5),
                                       "sec": round(dt, 4), "bs": len(idx),
                                       "seq": batch[0].shape[1]}) + "\n")
            if (s + 1) % 10 == 0 or s + 1 == steps_per_epoch:
                step_log.flush()
                avg = sum(step_times) / len(step_times)
                prog = {"stage": "train", "epoch": epoch, "step_in_epoch": s + 1,
                        "steps_per_epoch": steps_per_epoch, "global_step": gstep,
                        "total_steps": total_steps, "loss_last": round(lv, 4),
                        "loss_epoch_avg": round(sum_loss / (s + 1), 4),
                        "sec_per_step": round(avg, 3),
                        "samples_per_sec": round(n_samples / sum(step_times), 2),
                        "eta_min": round((total_steps - gstep) * avg / 60, 1),
                        "gpu": mon.summary(), "time": time.strftime("%H:%M:%S")}
                write_json(f"{RESULT_DIR}/progress.json", prog)
                print(f"[train] ep {epoch} step {s + 1}/{steps_per_epoch} "
                      f"loss {lv:.4f} avg {prog['loss_epoch_avg']:.4f} "
                      f"{avg:.3f}s/step {prog['samples_per_sec']} smp/s "
                      f"eta {prog['eta_min']}m", flush=True)
        sync()
        mon.active = False
        wall = time.time() - t_epoch
        ep = {"epoch": epoch, "steps": steps_per_epoch, "samples": n_samples,
              "train_loss": round(sum_loss / steps_per_epoch, 5),
              "train_loss_token_avg": round(sum_tok_loss / n_tok, 5),
              "sec_per_step": round(sum(step_times) / len(step_times), 4),
              "samples_per_sec": round(n_samples / sum(step_times), 3),
              "epoch_wall_sec": round(wall, 1),
              "gpu": mon.summary(), "vram_peak": vram_peaks(),
              "lr_end": sched.get_last_lr()[0]}
        history.append(ep)
        d = f"{CKPT_DIR}/epoch{epoch}"
        model.save_pretrained(d)
        torch.save({"opt": opt.state_dict(), "sched": sched.state_dict(),
                    "history": history, "batch": bs}, f"{d}/state.pt.tmp")
        os.replace(f"{d}/state.pt.tmp", f"{d}/state.pt")
        write_json(f"{RESULT_DIR}/train_summary.json", info | {"history": history})
        print("[train] EPOCH DONE", json.dumps(ep), flush=True)
    mon.stop()
    info["train_wall_sec_this_run"] = round(time.time() - t_run, 1)
    write_json(f"{RESULT_DIR}/train_summary.json", info | {"history": history, "done": True})
    print("[train] DONE", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", type=int, default=0)
    ap.add_argument("--batch", type=int, default=0)
    ap.add_argument("--epochs", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(RESULT_DIR, exist_ok=True)
    os.makedirs(CKPT_DIR, exist_ok=True)
    if a.probe:
        probe(a.probe)
    else:
        assert a.batch > 0
        train(a.batch, a.epochs)
