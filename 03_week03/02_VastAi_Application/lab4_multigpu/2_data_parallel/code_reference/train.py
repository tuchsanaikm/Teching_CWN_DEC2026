"""Lab4 / 2_data_parallel - LoRA fine-tuning of Qwen3-8B with PyTorch DDP (data parallelism).

Every GPU holds its own full copy of the model. Each step, every GPU takes a
different slice of the data, runs forward + backward, then DDP averages the
gradients over all GPUs so every copy takes the same optimizer step.

Launch (2 GPUs):
    torchrun --nproc_per_node 2 train.py --mode probe --bs 4     # 3 steps, longest example
    torchrun --nproc_per_node 2 train.py --mode train --bs 4     # 3 epochs, resumable
"""
import argparse
import json
import os
import sys
import time

import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MODEL_NAME, GpuMonitor, collate, encode_example, read_jsonl, write_json  # noqa: E402


def parse():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/workspace/lab4_dp")
    ap.add_argument("--mode", choices=["probe", "train"], required=True)
    ap.add_argument("--bs", type=int, required=True, help="batch size per GPU")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-len", type=int, default=256)
    ap.add_argument("--probe-steps", type=int, default=3)
    ap.add_argument("--save-every", type=int, default=50)
    ap.add_argument("--log-every", type=int, default=10)
    return ap.parse_args()


def build_model(model_dir, device, seed):
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM

    model = AutoModelForCausalLM.from_pretrained(model_dir, dtype=torch.bfloat16)
    model.to(device)
    model.config.use_cache = False
    # Same seed on every rank -> identical LoRA init on every GPU (DDP does not sync it).
    torch.manual_seed(seed)
    cfg = LoraConfig(
        r=8, lora_alpha=16, lora_dropout=0.0, bias="none",
        target_modules=["q_proj", "v_proj"], task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, cfg)  # LoRA weights are fp32, base stays bf16
    assert not model.base_model.model.is_activation_checkpointing
    return model


def lora_state(model):
    return {k: v.detach().cpu() for k, v in model.named_parameters() if v.requires_grad}


def train_step(ddp, opt, batch):
    # No attention_mask on purpose. Batches are padded on the RIGHT and attention is causal,
    # so a real token never looks at a pad token, and pad positions have label -100: the loss
    # and gradients are the same as with a mask. But passing a mask that contains zeros makes
    # the attention keep a (batch x heads x len x len) tensor per layer for backward
    # (about 0.5 GB more at 4 x 256 tokens), which the no-padding probe batch never needs.
    ids, _att, lab = batch
    with torch.autocast("cuda", dtype=torch.bfloat16):
        loss = ddp(input_ids=ids, labels=lab).loss
    opt.zero_grad(set_to_none=True)
    loss.backward()  # DDP all-reduces (averages) the gradients here
    opt.step()
    return loss.detach()


def mean_over_ranks(x):
    t = x.detach().float().clone()
    dist.all_reduce(t, op=dist.ReduceOp.SUM)
    return (t / dist.get_world_size()).item()


def main():
    args = parse()
    rank = int(os.environ["RANK"])
    world = int(os.environ["WORLD_SIZE"])
    local = int(os.environ["LOCAL_RANK"])
    torch.cuda.set_device(local)
    device = torch.device("cuda", local)
    dist.init_process_group("nccl")

    model_dir = os.path.join(args.root, "models", MODEL_NAME)
    res_dir = os.path.join(args.root, "results")
    ckpt_dir = os.path.join(args.root, "ckpt")
    os.makedirs(os.path.join(res_dir, "probe"), exist_ok=True)
    os.makedirs(ckpt_dir, exist_ok=True)

    def say(msg):
        if rank == 0:
            print(time.strftime("[%H:%M:%S] ") + msg, flush=True)

    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_dir)
    pad_id = tok.pad_token_id
    rows = read_jsonl(os.path.join(args.root, "data", "train.jsonl"))
    data = [encode_example(tok, r, args.max_len) for r in rows]
    n_cut = sum(d[2] > args.max_len for d in data)
    say(f"train examples {len(data)} | longer than {args.max_len} tokens (cut): {n_cut} | "
        f"longest kept {max(len(d[0]) for d in data)} tokens")

    # ------------------------------------------------------------ probe
    if args.mode == "probe":
        out = os.path.join(res_dir, "probe", f"bs{args.bs}_rank{rank}.json")
        info = {"bs_per_gpu": args.bs, "rank": rank, "gpu": local, "status": "started", "steps_done": 0}
        write_json(out, info)
        mon = GpuMonitor(0.5).start() if rank == 0 else None
        try:
            model = build_model(model_dir, device, args.seed)
            ddp = DDP(model, device_ids=[local])
            opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=args.lr)
            longest = max(data, key=lambda d: len(d[0]))
            info["seq_len"] = len(longest[0])
            info["model_only_alloc_mib"] = round(torch.cuda.memory_allocated(device) / 2**20)
            batch = collate([longest] * args.bs, pad_id, device)
            torch.cuda.reset_peak_memory_stats(device)
            times = []
            for s in range(args.probe_steps):
                t0 = time.time()
                loss = train_step(ddp, opt, batch)
                torch.cuda.synchronize(device)
                times.append(round(time.time() - t0, 3))
                info["steps_done"] = s + 1
                say(f"probe bs/gpu={args.bs} step {s + 1}/{args.probe_steps} loss {loss.item():.4f} "
                    f"{times[-1]:.2f}s peak_alloc {torch.cuda.max_memory_allocated(device) / 2**20:.0f} MiB")
            info["status"] = "ok"
            info["step_sec"] = times
        except torch.OutOfMemoryError as e:
            info["status"] = "oom"
            info["error"] = str(e).splitlines()[0][:300]
            print(f"[rank {rank}] OOM at bs/gpu={args.bs}: {info['error']}", flush=True)
        info["peak_alloc_mib"] = round(torch.cuda.max_memory_allocated(device) / 2**20)
        info["peak_reserved_mib"] = round(torch.cuda.max_memory_reserved(device) / 2**20)
        if mon:
            mon.stop()
            info["nvidia_smi"] = mon.summary()
        write_json(out, info)
        # A rank that hit OOM leaves at once; torchrun then stops the other rank.
        os._exit(0 if info["status"] == "ok" else 17)

    # ------------------------------------------------------------ train
    model = build_model(model_dir, device, args.seed)
    params = [p for p in model.parameters() if p.requires_grad]
    say(f"trainable LoRA params {sum(p.numel() for p in params):,} | world {world} | "
        f"bs/gpu {args.bs} | total bs {args.bs * world}")
    opt = torch.optim.AdamW(params, lr=args.lr)  # constant learning rate

    state_path = os.path.join(ckpt_dir, "state.pt")
    log_path = os.path.join(res_dir, "train_log.jsonl")
    start_epoch, start_step, gstep = 0, 0, 0
    epoch_stats, cur = [], {"loss_sum": 0.0, "n": 0, "time": 0.0}
    if os.path.exists(state_path):
        st = torch.load(state_path, map_location="cpu")
        assert st["bs"] == args.bs and st["world"] == world, "checkpoint was made with another batch setup"
        model.load_state_dict(st["lora"], strict=False)
        opt.load_state_dict(st["opt"])
        start_epoch, start_step, gstep = st["epoch"], st["step_in_epoch"], st["gstep"]
        epoch_stats, cur = st["epoch_stats"], st["cur"]
        say(f"RESUME from epoch {start_epoch + 1} step {start_step} (global step {gstep})")
        if rank == 0 and os.path.exists(log_path):  # drop log lines newer than the checkpoint
            keep = [l for l in open(log_path) if json.loads(l)["gstep"] <= gstep]
            with open(log_path, "w") as f:
                f.writelines(keep)
    elif rank == 0 and os.path.exists(log_path):
        os.remove(log_path)

    ddp = DDP(model, device_ids=[local])
    n = len(data)
    per_rank = n // world
    steps_per_epoch = (per_rank + args.bs - 1) // args.bs
    total_steps = steps_per_epoch * args.epochs
    mon = GpuMonitor(1.0).start() if rank == 0 else None
    logf = open(log_path, "a") if rank == 0 else None
    torch.cuda.reset_peak_memory_stats(device)
    t_run = time.time()
    biggest = 0

    def save_state(epoch, step_in_epoch):
        if rank != 0:
            return
        tmp = state_path + ".tmp"
        torch.save({"lora": lora_state(model), "opt": opt.state_dict(), "epoch": epoch,
                    "step_in_epoch": step_in_epoch, "gstep": gstep, "bs": args.bs, "world": world,
                    "epoch_stats": epoch_stats, "cur": cur}, tmp)
        os.replace(tmp, state_path)

    for epoch in range(start_epoch, args.epochs):
        # Same shuffle on every rank; rank r takes every world-th item -> half of the data each.
        g = torch.Generator().manual_seed(args.seed + epoch)
        perm = torch.randperm(n, generator=g).tolist()
        mine = perm[rank::world][:per_rank]
        first = start_step if epoch == start_epoch else 0
        if first == 0:
            cur = {"loss_sum": 0.0, "n": 0, "time": 0.0}
        t_epoch = time.time()
        for s in range(first, steps_per_epoch):
            batch = collate([data[i][:2] for i in mine[s * args.bs:(s + 1) * args.bs]], pad_id, device)
            if batch[0].numel() > biggest:  # new largest batch: hand cached blocks back first
                biggest = batch[0].numel()
                torch.cuda.empty_cache()
            torch.cuda.synchronize(device)
            t0 = time.time()
            loss = train_step(ddp, opt, batch)
            torch.cuda.synchronize(device)
            dt = time.time() - t0
            loss = mean_over_ranks(loss)
            gstep += 1
            cur["loss_sum"] += loss
            cur["n"] += 1
            cur["time"] += dt
            if rank == 0:
                logf.write(json.dumps({"gstep": gstep, "epoch": epoch + 1, "step": s + 1,
                                       "loss": round(loss, 5), "sec": round(dt, 4),
                                       "seq_len": batch[0].shape[1]}) + "\n")
                logf.flush()
                if (s + 1) % args.log_every == 0 or s + 1 == steps_per_epoch:
                    m = mon.summary(since=time.time() - 60)
                    sps = cur["time"] / cur["n"]
                    eta = (total_steps - gstep) * sps / 60
                    say(f"epoch {epoch + 1}/{args.epochs} step {s + 1}/{steps_per_epoch} "
                        f"(global {gstep}/{total_steps}) loss {loss:.4f} avg {cur['loss_sum'] / cur['n']:.4f} "
                        f"{sps:.3f}s/step {args.bs * world / sps:.2f} samples/s "
                        f"util {m.get('util_mean')} mem {m.get('mem_max_mib')} ETA {eta:.1f} min")
            if (s + 1) % args.save_every == 0 and s + 1 < steps_per_epoch:
                save_state(epoch, s + 1)

        # ---- end of epoch: check all copies are still identical, save adapter ----
        chk = torch.stack([p.detach().double().sum() for p in params]).sum()
        lo, hi = chk.clone(), chk.clone()
        dist.all_reduce(lo, op=dist.ReduceOp.MIN)
        dist.all_reduce(hi, op=dist.ReduceOp.MAX)
        peak = torch.tensor([torch.cuda.max_memory_allocated(device) / 2**20 if r == rank else 0.0
                             for r in range(world)], device=device)
        peak_res = torch.tensor([torch.cuda.max_memory_reserved(device) / 2**20 if r == rank else 0.0
                                 for r in range(world)], device=device)
        dist.all_reduce(peak)
        dist.all_reduce(peak_res)
        if rank == 0:
            m = mon.summary(since=t_epoch)
            sps = cur["time"] / cur["n"]
            epoch_stats.append({
                "epoch": epoch + 1, "steps": cur["n"], "train_loss_mean": round(cur["loss_sum"] / cur["n"], 5),
                "sec_per_step": round(sps, 4), "samples_per_sec": round(args.bs * world / sps, 3),
                "epoch_wall_sec_this_run": round(time.time() - t_epoch, 1),
                "gpu_util_mean": m.get("util_mean"), "nvidia_smi_mem_max_mib": m.get("mem_max_mib"),
                "torch_peak_alloc_mib": [round(x) for x in peak.tolist()],
                "torch_peak_reserved_mib": [round(x) for x in peak_res.tolist()],
                "replicas_identical": bool(lo.item() == hi.item()),
            })
            model.save_pretrained(os.path.join(ckpt_dir, f"epoch{epoch + 1}"))
            say(f"== epoch {epoch + 1} done: {json.dumps(epoch_stats[-1])}")
        cur_done = cur
        cur = {"loss_sum": 0.0, "n": 0, "time": 0.0}
        save_state(epoch + 1, 0)
        cur = cur_done

    if rank == 0:
        mon.stop()
        tot_t = sum(e["sec_per_step"] * e["steps"] for e in epoch_stats)
        tot_n = sum(e["steps"] for e in epoch_stats)
        write_json(os.path.join(res_dir, "train_summary.json"), {
            "model": MODEL_NAME, "dtype": "bfloat16", "gradient_checkpointing": False, "thinking": False,
            "lora": {"r": 8, "alpha": 16, "target_modules": ["q_proj", "v_proj"]},
            "lr": args.lr, "lr_schedule": "constant", "optimizer": "AdamW", "seed": args.seed,
            "max_len": args.max_len, "n_train": n, "n_cut_to_max_len": n_cut,
            "world_size": world, "bs_per_gpu": args.bs, "bs_total": args.bs * world,
            "steps_per_epoch": steps_per_epoch, "epochs": args.epochs,
            "sec_per_step": round(tot_t / tot_n, 4),
            "samples_per_sec": round(args.bs * world * tot_n / tot_t, 3),
            "wall_sec_this_run": round(time.time() - t_run, 1),
            "epochs_detail": epoch_stats,
        })
        say("TRAIN DONE")
    dist.destroy_process_group()


if __name__ == "__main__":
    main()
