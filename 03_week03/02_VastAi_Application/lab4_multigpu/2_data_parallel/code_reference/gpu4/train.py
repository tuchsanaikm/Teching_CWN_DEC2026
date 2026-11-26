"""LoRA fine-tuning of Qwen3-8B (text -> SQL) with Data Parallelism on N GPUs (PyTorch DDP).

Every GPU holds its own full copy of the model, gets 1/N of the data (DistributedSampler),
and DDP averages the gradients of all copies so every copy takes the same optimizer step.

Launch:  torchrun --nproc_per_node 4 train.py --mode train --batch-size B
         torchrun --nproc_per_node 4 train.py --mode probe --batch-size B   (3 steps, longest sample)
"""
import argparse
import json
import os
import sys
import time

# less fragmentation when the batch shape changes from step to step
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import torch
import torch.distributed as dist
from peft import LoraConfig, get_peft_model
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader
from torch.utils.data.distributed import DistributedSampler
from transformers import AutoModelForCausalLM, AutoTokenizer

from common import MAX_LEN, MODEL_DIR, ROOT, TRAIN_FILE, GpuMonitor, collate, encode, load_jsonl

p = argparse.ArgumentParser()
p.add_argument("--mode", choices=["train", "probe"], required=True)
p.add_argument("--batch-size", type=int, required=True, help="batch per GPU")
p.add_argument("--epochs", type=int, default=3)
p.add_argument("--lr", type=float, default=2e-4)
p.add_argument("--seed", type=int, default=0)
p.add_argument("--max-len", type=int, default=MAX_LEN)
p.add_argument("--probe-steps", type=int, default=3)
p.add_argument("--report-every", type=float, default=120, help="seconds between [REPORT] lines")
p.add_argument("--out", default=f"{ROOT}/results")
args = p.parse_args()

rank = int(os.environ["RANK"])
world = int(os.environ["WORLD_SIZE"])
os.environ.setdefault("NCCL_SHM_DISABLE", "1")  # NCCL cannot attach its /dev/shm segment in this container
dev = torch.device("cuda", int(os.environ["LOCAL_RANK"]))
torch.cuda.set_device(dev)
dist.init_process_group("nccl")
torch.manual_seed(args.seed)  # same seed on every rank -> identical LoRA init
B = args.batch_size


def log(*a):
    if rank == 0:
        print(time.strftime("%H:%M:%S"), *a, flush=True)


def gather(x):
    """One float of every rank, as a list indexed by rank."""
    t = torch.zeros(world, dtype=torch.float64, device=dev)
    t[rank] = float(x)
    dist.all_reduce(t)
    return t.tolist()


def die_oom(e):
    """Leave a marker for find_batch.py and kill the whole DDP job."""
    path = f"{args.out}/probe/oom_bs{B}_rank{rank}.json"
    if args.mode == "probe":
        json.dump({"batch_per_gpu": B, "rank": rank, "error": str(e)[:300],
                   "allocated_mib": torch.cuda.max_memory_allocated(dev) / 2**20}, open(path, "w"))
    print(f"[OOM] rank {rank} batch_per_gpu={B}: {str(e)[:700]}", flush=True)
    os._exit(42)


# ---------------- data ----------------
tok = AutoTokenizer.from_pretrained(MODEL_DIR)
data = [encode(tok, ex, args.max_len) for ex in load_jsonl(TRAIN_FILE)]
n_trunc = sum(d["full_len"] > args.max_len for d in data)
longest = max(data, key=lambda d: len(d["input_ids"]))
log(f"mode={args.mode} world={world} batch_per_gpu={B} global_batch={B * world} "
    f"train={len(data)} truncated_to_{args.max_len}={n_trunc} longest={len(longest['input_ids'])} tokens")

# ---------------- model: one full copy per GPU ----------------
model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, dtype=torch.bfloat16, device_map={"": dev.index})
model.config.use_cache = False
assert not model.is_gradient_checkpointing
model = get_peft_model(model, LoraConfig(r=8, lora_alpha=16, target_modules=["q_proj", "v_proj"],
                                         lora_dropout=0.0, bias="none", task_type="CAUSAL_LM"))
params = [q for q in model.parameters() if q.requires_grad]
log(f"base dtype={next(model.base_model.model.model.layers[0].mlp.parameters()).dtype} "
    f"trainable={sum(q.numel() for q in params):,} ({params[0].dtype}) "
    f"total={sum(q.numel() for q in model.parameters()):,} "
    f"weights_on_gpu={torch.cuda.memory_allocated(dev) / 2**20:.0f} MiB")


class AnswerLoss(torch.nn.Module):
    """Cross entropy on the answer tokens only. The vocabulary projection (151,936 wide) is applied to the
    answer positions instead of all positions: same loss value as model(labels=...), about 1.5 GB less
    VRAM at batch 4 x 256 tokens (attempts 1-2 ran out of memory at step ~25 of real training without it)."""

    def __init__(self, peft_model):
        super().__init__()
        self.peft = peft_model
        self.lm = peft_model.get_base_model()  # Qwen3ForCausalLM with the LoRA layers inside

    def forward(self, input_ids, attention_mask, labels):
        h = self.lm.model(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
        tgt = labels[:, 1:]  # position t predicts token t+1
        keep = tgt != -100
        logits = self.lm.lm_head(h[:, :-1][keep]).float()
        return torch.nn.functional.cross_entropy(logits, tgt[keep])


ddp = DDP(AnswerLoss(model), device_ids=[dev.index])
opt = torch.optim.AdamW(params, lr=args.lr, weight_decay=0.0)  # constant learning rate
mon = GpuMonitor() if rank == 0 else None
torch.cuda.reset_peak_memory_stats(dev)


def train_step(batch, check=False):
    """Forward + backward + optimizer step. Returns mean loss over ranks (and gradient check)."""
    try:
        batch = {k: v.to(dev, non_blocking=True) for k, v in batch.items()}
        with torch.autocast("cuda", dtype=torch.bfloat16):
            loss = ddp(**batch)
        opt.zero_grad(set_to_none=True)
        loss.backward()  # DDP all-reduces (averages) the gradients of all ranks in here
        info = None
        if check:  # same gradient on every GPU although every GPU saw different data?
            info = {"local_loss": gather(loss.item()),
                    "grad_abs_sum": gather(sum(q.grad.double().abs().sum() for q in params).item())}
        opt.step()
        torch.cuda.synchronize(dev)
    except torch.OutOfMemoryError as e:
        die_oom(e)
    return sum(gather(loss.item())) / world, info


def peaks():
    return {"torch_allocated_mib": [round(x) for x in gather(torch.cuda.max_memory_allocated(dev) / 2**20)],
            "torch_reserved_mib": [round(x) for x in gather(torch.cuda.max_memory_reserved(dev) / 2**20)]}


# ---------------- probe: 3 steps with the longest sample ----------------
if args.mode == "probe":
    os.makedirs(f"{args.out}/probe", exist_ok=True)
    batch = collate([longest] * B, tok.pad_token_id)
    t_start, times = time.time(), []
    for s in range(args.probe_steps):
        t0 = time.time()
        loss, info = train_step(batch, check=True)
        times.append(time.time() - t0)
        log(f"probe step {s + 1}/{args.probe_steps} loss={loss:.4f} {times[-1]:.2f}s grad_abs_sum={info['grad_abs_sum']}")
    pk = peaks()
    if rank == 0:
        time.sleep(2.5)  # let nvidia-smi see the peak
        w = mon.window(t_start)
        res = {"batch_per_gpu": B, "global_batch": B * world, "status": "ok", "steps": args.probe_steps,
               "seq_len": len(longest["input_ids"]), "sec_per_step": [round(t, 3) for t in times],
               **pk, "nvidia_smi_peak_mib": w["mem_peak_mib"]}
        json.dump(res, open(f"{args.out}/probe/bs{B}.json", "w"), indent=1)
        log("PROBE_OK", json.dumps(res))
        mon.stop()
    dist.barrier()
    dist.destroy_process_group()
    sys.exit(0)

# ---------------- train ----------------
sampler = DistributedSampler(data, shuffle=True, seed=args.seed, drop_last=False)  # 1/N of the data per GPU
loader = DataLoader(data, batch_size=B, sampler=sampler, collate_fn=lambda b: collate(b, tok.pad_token_id))
steps_per_epoch = len(loader)
ckpt_path = f"{args.out}/ckpt/last.pt"
os.makedirs(f"{args.out}/ckpt", exist_ok=True)
history, start_epoch = [], 0
if os.path.exists(ckpt_path):  # resume after an interruption, from the last finished epoch
    ck = torch.load(ckpt_path, map_location=dev)
    assert ck["batch_per_gpu"] == B and ck["world"] == world
    with torch.no_grad():
        for q, v in zip(params, ck["params"]):
            q.copy_(v)
    opt.load_state_dict(ck["opt"])
    history, start_epoch = ck["history"], ck["epoch"]
    log(f"resumed from {ckpt_path}: {start_epoch} epoch(s) already done")
log(f"samples_per_gpu_per_epoch={len(sampler)} steps_per_epoch={steps_per_epoch} epochs={args.epochs} lr={args.lr}")

last_report = time.time()
for epoch in range(start_epoch, args.epochs):
    sampler.set_epoch(epoch)
    ddp.train()
    torch.cuda.reset_peak_memory_stats(dev)
    t_epoch, losses, times, n_seen = time.time(), [], [], 0
    t_prev = time.time()
    for step, batch in enumerate(loader, 1):
        check = epoch == 0 and step <= 3
        loss, info = train_step(batch, check)
        now = time.time()
        times.append(now - t_prev)  # full step incl. data loading
        t_prev = now
        losses.append(loss)
        n_seen += batch["input_ids"].shape[0] * world
        if check:
            g = info["grad_abs_sum"]
            log(f"[GRADCHECK] step {step} local_loss/rank={[round(x, 4) for x in info['local_loss']]} "
                f"grad_abs_sum/rank={g} identical={max(g) - min(g) == 0}")
        if step % 10 == 0 or step == steps_per_epoch:
            log(f"epoch {epoch + 1}/{args.epochs} step {step}/{steps_per_epoch} loss={loss:.4f} "
                f"avg10={sum(losses[-10:]) / len(losses[-10:]):.4f} {times[-1]:.2f}s/step")
        if rank == 0 and now - last_report >= args.report_every:
            w = mon.window(last_report)
            done = (epoch - start_epoch) * steps_per_epoch + step
            left = (args.epochs - start_epoch) * steps_per_epoch - done
            sps = sum(times[-50:]) / len(times[-50:])
            log(f"[REPORT] epoch {epoch + 1}/{args.epochs} step {step}/{steps_per_epoch} "
                f"loss_epoch_avg={sum(losses) / len(losses):.4f} sec/step={sps:.2f} "
                f"samples/s={B * world / sps:.1f} eta={left * sps / 60:.1f}min "
                f"gpu_util%={w['util_mean']} vram_mib={w['mem_peak_mib']}")
            last_report = now
    pk = peaks()
    if rank == 0:
        w = mon.window(t_epoch)
        tt = sum(times)
        ep = {"epoch": epoch + 1, "steps": len(times), "samples": n_seen,
              "train_loss_mean": sum(losses) / len(losses), "train_loss_last10": sum(losses[-10:]) / len(losses[-10:]),
              "epoch_sec": round(tt, 1), "sec_per_step": round(tt / len(times), 4),
              "sec_per_step_median": round(sorted(times)[len(times) // 2], 4),
              "samples_per_sec": round(n_seen / tt, 2),
              "gpu_util_mean": w["util_mean"], "nvidia_smi_peak_mib": w["mem_peak_mib"], **pk, "losses": losses}
        history.append(ep)
        model.save_pretrained(f"{args.out}/adapters/epoch{epoch + 1}")
        tmp = ckpt_path + ".tmp"
        torch.save({"epoch": epoch + 1, "batch_per_gpu": B, "world": world, "history": history,
                    "params": [q.detach().cpu() for q in params], "opt": opt.state_dict()}, tmp)
        os.replace(tmp, ckpt_path)
        json.dump({"batch_per_gpu": B, "world": world, "global_batch": B * world, "lr": args.lr,
                   "seed": args.seed, "max_len": args.max_len, "truncated": n_trunc,
                   "steps_per_epoch": steps_per_epoch, "epochs_done": epoch + 1, "epochs": history},
                  open(f"{args.out}/train_metrics.json", "w"), indent=1)
        log(f"[EPOCH] {epoch + 1} done loss={ep['train_loss_mean']:.4f} sec/step={ep['sec_per_step']} "
            f"samples/s={ep['samples_per_sec']} gpu_util%={ep['gpu_util_mean']} "
            f"vram_mib={ep['nvidia_smi_peak_mib']} time={tt:.0f}s")
    dist.barrier()

if rank == 0:
    mon.stop()
log("TRAIN_DONE")
dist.destroy_process_group()
