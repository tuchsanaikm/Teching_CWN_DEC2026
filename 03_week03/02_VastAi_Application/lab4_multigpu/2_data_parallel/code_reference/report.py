#!/usr/bin/env python3
"""Lab4 / 2_data_parallel: turn the raw results into results/metrics.json and four charts.

Reads only files under results/raw (copied back from the machine, plus the market search
and the instance / billing snapshots taken on teardown). Nothing here talks to the network.

  python code/report.py
"""
import glob
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
RAW = os.path.join(RES, "raw")
RAW_RES = os.path.join(RAW, "results")
IMG = os.path.join(RES, "images")

CARD_MIB = 24576  # RTX 3090: 24 GB (nvidia-smi reports 24576 MiB)
GPU_COLOR = ["#2a78d6", "#eb6834"]  # GPU 0, GPU 1 (fixed order everywhere)
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
LIMIT_COLOR = "#d03b3b"


def load(path, default=None):
    if not os.path.exists(path):
        if default is None:
            sys.exit(f"missing file: {path}")
        return default
    with open(path) as f:
        return json.load(f)


def gib(mib):
    return mib / 1024.0


# ----------------------------------------------------------------------------- numbers
def read_probe():
    """One row per batch size: status and peak memory of both GPUs."""
    rows = []
    for done in glob.glob(os.path.join(RAW_RES, "probe", "bs*.done")):
        bs = int(os.path.basename(done)[2:-5])
        ranks = [load(os.path.join(RAW_RES, "probe", f"bs{bs}_rank{r}.json")) for r in (0, 1)]
        status = open(done).read().strip()
        row = {"bs_per_gpu": bs, "status": status, "seq_len": ranks[0]["seq_len"],
               "torch_peak_alloc_mib": [r["peak_alloc_mib"] for r in ranks],
               "torch_peak_reserved_mib": [r["peak_reserved_mib"] for r in ranks]}
        smi = ranks[0].get("nvidia_smi") or {}
        if status == "ok":
            # nvidia-smi peak is what the card really holds (PyTorch + CUDA context)
            row["nvidia_smi_peak_mib"] = smi.get("mem_max_mib")
            row["gpu_util_mean_pct"] = smi.get("util_mean")
            steps = [r["step_sec"][1:] for r in ranks]
            row["sec_per_step"] = round(sum(map(sum, steps)) / sum(map(len, steps)), 3)
        else:
            # the run died before the sampler saw the peak, so there is no usable reading
            row["nvidia_smi_peak_mib"] = None
            row["error"] = ranks[0].get("error", "")[:160]
        rows.append(row)
    return sorted(rows, key=lambda r: r["bs_per_gpu"])


def read_train_log():
    rows = []
    with open(os.path.join(RAW_RES, "train_log.jsonl")) as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def cheapest(offers):
    if not offers:
        return None
    o = min(offers, key=lambda x: x["dph_total"])
    keys = ["id", "machine_id", "dph_total", "dph_base", "storage_total_cost", "verification",
            "reliability2", "geolocation"]
    out = {k: o.get(k) for k in keys}
    out["n_offers"] = len(offers)
    return out


def usd_per_1000(usd_per_hour, samples_per_sec):
    return usd_per_hour / (samples_per_sec * 3600.0) * 1000.0


def build_metrics():
    summary = load(os.path.join(RAW_RES, "train_summary.json"))
    evals = load(os.path.join(RAW_RES, "eval_summary.json"))
    prep = load(os.path.join(RAW_RES, "prepare_info.json"))
    probe = read_probe()
    ok = [p for p in probe if p["status"] == "ok"]
    largest = max(p["bs_per_gpu"] for p in ok)
    sps = summary["samples_per_sec"]

    m = {
        "lab": "lab4_multigpu/2_data_parallel",
        "method": "LoRA fine-tuning with DistributedDataParallel on 2 GPUs (one model copy per GPU)",
        "model": prep["model_id"], "dataset": prep["dataset_id"],
        "n_train": prep["n_train"], "n_test": prep["n_test"],
        "config": {k: summary[k] for k in ("dtype", "gradient_checkpointing", "thinking", "lora", "lr",
                                           "lr_schedule", "optimizer", "seed", "max_len", "world_size")},
        "gpu": {"name": "RTX 3090", "count": 2, "vram_mib_per_gpu": CARD_MIB},
        "probe": probe,
        "largest_bs_per_gpu": largest,
        "largest_bs_total": largest * summary["world_size"],
        "train": {
            "bs_per_gpu": summary["bs_per_gpu"], "bs_total": summary["bs_total"],
            "steps_per_epoch": summary["steps_per_epoch"], "epochs": summary["epochs"],
            "sec_per_step": summary["sec_per_step"], "samples_per_sec": sps,
            "epochs_detail": summary["epochs_detail"],
        },
        "eval": evals,
    }
    final = evals[-1]
    m["final"] = {"tag": final["tag"], "exact_match_pct": final["exact_match_pct"],
                  "em_count": final["em_count"], "n_test": final["n_test"]}
    best = max((e for e in evals if e["tag"] != "base"), key=lambda e: e["exact_match_pct"])
    m["best_epoch"] = {"tag": best["tag"], "exact_match_pct": best["exact_match_pct"]}

    # ---- price: market search + the machine that was really rented ----
    market = load(os.path.join(RAW, "market", "offers_2x3090.json"), default={})
    cost = {"formula": "usd_per_hour / (samples_per_sec * 3600) * 1000", "samples_per_sec": sps,
            "note": "samples = training examples; price includes 60 GB of disk"}
    if market:
        s = market["searches"]
        mk = {"searched_at_utc": market["searched_at_utc"], "query": market["query"],
              "cheapest_on_demand_verified": cheapest(s.get("on_demand_verified")),
              "cheapest_on_demand_any_verification": cheapest(s.get("on_demand_any_verification")),
              "cheapest_interruptible_verified": cheapest(s.get("interruptible_verified"))}
        m["market_price"] = mk
        for key, short in (("cheapest_on_demand_verified", "market_on_demand_verified"),
                           ("cheapest_on_demand_any_verification", "market_on_demand_any_verification"),
                           ("cheapest_interruptible_verified", "market_interruptible_verified")):
            if mk[key]:
                cost[short] = {"usd_per_hour": round(mk[key]["dph_total"], 4),
                               "usd_per_1000_samples": round(usd_per_1000(mk[key]["dph_total"], sps), 6)}
        if mk["cheapest_on_demand_verified"]:
            # headline number: cheapest machine anyone can rent right now without being interrupted
            cost["headline"] = dict(cost["market_on_demand_verified"], basis="market_on_demand_verified")

    inst = load(os.path.join(RAW, "instance", "instance_before_destroy.json"), default={})
    if inst:
        cost["rented_instance"] = {"usd_per_hour": round(inst["dph_total"], 4),
                                   "usd_per_1000_samples": round(usd_per_1000(inst["dph_total"], sps), 6)}
        real = {"instance_id": inst["id"], "label": inst["label"], "usd_per_hour": round(inst["dph_total"], 4),
                "created_utc": inst.get("created_utc"), "snapshot_utc": inst.get("snapshot_utc"),
                "destroyed_utc": inst.get("destroyed_utc"),
                "age_sec_at_destroy": inst.get("age_sec_at_destroy")}
        if real["age_sec_at_destroy"]:
            real["age_min_at_destroy"] = round(real["age_sec_at_destroy"] / 60.0, 1)
            real["estimated_cost_usd"] = round(real["age_sec_at_destroy"] / 3600.0 * inst["dph_total"], 4)
        bill = load(os.path.join(RAW, "instance", "charges.json"), default={})
        if bill:
            real["billed"] = bill
        m["instance_cost"] = real
    m["cost_per_1000_samples"] = cost
    return m


# ------------------------------------------------------------------------------ charts
def style(ax, ygrid=True):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK2, length=0, labelsize=10)
    if ygrid:
        ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def new_fig(title, subtitle, size=(8.4, 5.0)):
    fig, ax = plt.subplots(figsize=size, dpi=160)
    fig.patch.set_facecolor(SURFACE)
    fig.subplots_adjust(top=0.82, left=0.1, right=0.97, bottom=0.13)
    fig.text(0.1, 0.945, title, fontsize=13.5, fontweight="bold", color=INK, ha="left", va="center")
    fig.text(0.1, 0.885, subtitle, fontsize=9.5, color=INK2, ha="left", va="center")
    style(ax)
    return fig, ax


def save(fig, name):
    os.makedirs(IMG, exist_ok=True)
    path = os.path.join(IMG, name)
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)
    print("wrote", os.path.relpath(path, ROOT))


def grouped_bars(ax, groups, values, fmt, width=0.34):
    """values[i] = [gpu0, gpu1] or None (nothing to draw for that group)."""
    for i, pair in enumerate(values):
        if pair is None:
            continue
        for g in (0, 1):
            x = i + (g - 0.5) * (width + 0.03)
            ax.bar(x, pair[g], width=width, color=GPU_COLOR[g], label=f"GPU {g}" if i == 0 else None,
                   linewidth=0)
            ax.annotate(fmt.format(pair[g]), (x, pair[g]), textcoords="offset points", xytext=(0, 3),
                        ha="center", va="bottom", fontsize=9, color=INK, zorder=5,
                        bbox=dict(boxstyle="round,pad=0.15", facecolor=SURFACE, edgecolor="none"))
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels(groups)


def chart_vram(m):
    probe = m["probe"]
    fig, ax = new_fig("Peak VRAM per GPU vs batch size per GPU",
                      f"{m['model'].split('/')[-1]} LoRA, DDP on 2 x RTX 3090, bf16, {probe[0]['seq_len']}-token "
                      "samples, 3 steps per batch size - peak from nvidia-smi")
    vals = [[gib(v) for v in p["nvidia_smi_peak_mib"]] if p["status"] == "ok" else None for p in probe]
    grouped_bars(ax, [str(p["bs_per_gpu"]) for p in probe], vals, "{:.1f}")
    limit = gib(CARD_MIB)
    ax.axhline(limit, color=LIMIT_COLOR, linewidth=1.6, linestyle=(0, (5, 3)), zorder=3)
    ax.text(len(probe) - 0.48, limit + 0.25, "24 GB card limit", color=INK, fontsize=9.5, ha="right",
            va="bottom")
    for i, p in enumerate(probe):
        if p["status"] != "ok":
            ax.text(i, limit / 2, "Out of memory\non both GPUs", ha="center", va="center", fontsize=10.5,
                    color=INK, fontweight="bold")
            ax.text(i, limit / 2 - 2.6, "(does not fit in 24 GB)", ha="center", va="center", fontsize=9,
                    color=INK2)
    ax.set_ylim(0, 28)
    ax.set_yticks(range(0, 29, 4))
    ax.set_xlim(-0.6, len(probe) - 0.4)
    ax.set_xlabel("Batch size per GPU", color=INK2, fontsize=10.5)
    ax.set_ylabel("Peak VRAM (GB)", color=INK2, fontsize=10.5)
    ax.legend(loc="upper left", frameon=False, ncol=2, fontsize=10, labelcolor=INK2,
              bbox_to_anchor=(0.0, 1.0))
    save(fig, "vram_vs_batch.png")


def chart_util(m):
    ep = m["train"]["epochs_detail"]
    fig, ax = new_fig("GPU utilization per GPU during training",
                      f"Mean of nvidia-smi samples in each epoch, batch {m['train']['bs_per_gpu']} per GPU "
                      "(epoch 1 covers steps 101-500, after the resume)")
    grouped_bars(ax, [f"Epoch {e['epoch']}" for e in ep], [e["gpu_util_mean"] for e in ep], "{:.1f}%")
    ax.set_ylim(0, 112)
    ax.set_yticks(range(0, 101, 20))
    ax.set_xlim(-0.6, len(ep) - 0.4)
    ax.set_ylabel("GPU utilization (%)", color=INK2, fontsize=10.5)
    ax.legend(loc="upper left", frameon=False, ncol=2, fontsize=10, labelcolor=INK2,
              bbox_to_anchor=(0.0, 1.0))
    save(fig, "gpu_util.png")


def chart_loss(m, log):
    steps = [r["gstep"] for r in log]
    loss = [r["loss"] for r in log]
    win = 25
    smooth = [sum(loss[max(0, i - win + 1): i + 1]) / len(loss[max(0, i - win + 1): i + 1])
              for i in range(len(loss))]
    spe = m["train"]["steps_per_epoch"]
    n_ep = m["train"]["epochs"]
    fig, ax = new_fig(f"Training loss over {n_ep} epochs",
                      f"{len(steps):,} steps, total batch {m['train']['bs_total']} "
                      f"({m['train']['bs_per_gpu']} per GPU x 2 GPUs), log scale", size=(9.2, 5.0))
    ax.plot(steps, loss, color="#9ec5f4", linewidth=0.7, label="Train loss (each step)", zorder=2)
    ax.plot(steps, smooth, color=GPU_COLOR[0], linewidth=2, label=f"Train loss ({win}-step mean)", zorder=3)
    ev = {e["tag"]: e for e in m["eval"]}
    tx = [0] + [spe * k for k in range(1, n_ep + 1)]
    ty = [ev["base"]["test_loss"]] + [ev[f"epoch{k}"]["test_loss"] for k in range(1, n_ep + 1)]
    ax.plot(tx, ty, linestyle="none", marker="D", markersize=8, color=GPU_COLOR[1], markeredgecolor=SURFACE,
            markeredgewidth=1.5, label="Test loss (200 examples)", zorder=4, clip_on=False)
    for x, y in zip(tx, ty):
        ax.annotate(f"{y:.3f}", (x, y), textcoords="offset points", xytext=(10, -3) if x == 0 else (-9, 8),
                    ha="left" if x == 0 else "right", va="center" if x == 0 else "baseline", fontsize=9,
                    color=INK)
    ax.set_yscale("log")
    lo = min(loss)
    ax.set_ylim(max(lo * 0.7, 1e-4), 9)
    for k in range(1, n_ep + 1):
        if k < n_ep:
            ax.axvline(spe * k, color=INK2, linewidth=0.8, linestyle=(0, (2, 3)), zorder=1)
        mean = m["train"]["epochs_detail"][k - 1]["train_loss_mean"]
        ax.text(spe * (k - 0.5), 5.2, f"Epoch {k}  -  mean train loss {mean:.4f}", ha="center", va="center",
                fontsize=9.5, color=INK2)
    ax.set_xlim(0, spe * n_ep)
    ax.set_xticks(range(0, spe * n_ep + 1, 250))
    ax.set_xlabel("Training step", color=INK2, fontsize=10.5)
    ax.set_ylabel("Loss (cross-entropy)", color=INK2, fontsize=10.5)
    ax.grid(axis="y", which="minor", color=GRID, linewidth=0.4)
    ax.legend(loc="lower left", frameon=False, fontsize=9.5, labelcolor=INK2)
    save(fig, "loss_3_epochs.png")


def chart_em(m):
    ev = m["eval"]
    names = {"base": "Base\n(before training)"}
    labels = [names.get(e["tag"], e["tag"].replace("epoch", "Epoch ")) for e in ev]
    vals = [e["exact_match_pct"] for e in ev]
    fig, ax = new_fig("Exact Match on the test set after each epoch",
                      f"{ev[0]['n_test']} test examples, greedy decoding; a prediction counts only if the SQL "
                      "text equals the reference", size=(7.6, 5.0))
    ax.bar(range(len(ev)), vals, width=0.5, color=GPU_COLOR[0], linewidth=0)
    for i, e in enumerate(ev):
        ax.text(i, vals[i] + 1.2, f"{vals[i]:.1f}%", ha="center", va="bottom", fontsize=11, color=INK,
                fontweight="bold")
        ax.text(i, vals[i] + 7.2, f"{e['em_count']}/{e['n_test']}", ha="center", va="bottom", fontsize=9,
                color=INK2)
    ax.set_xticks(range(len(ev)))
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 100)
    ax.set_yticks(range(0, 101, 20))
    ax.set_ylabel("Exact Match (%)", color=INK2, fontsize=10.5)
    save(fig, "exact_match.png")


def main():
    plt.rcParams["font.family"] = "DejaVu Sans"
    m = build_metrics()
    with open(os.path.join(RES, "metrics.json"), "w") as f:
        json.dump(m, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("wrote results/metrics.json")
    chart_vram(m)
    chart_util(m)
    chart_loss(m, read_train_log())
    chart_em(m)

    c = m["cost_per_1000_samples"]
    print(f"largest batch per GPU : {m['largest_bs_per_gpu']} (total {m['largest_bs_total']})")
    print(f"samples per second    : {m['train']['samples_per_sec']:.2f}")
    print(f"Exact Match (final)   : {m['final']['exact_match_pct']:.1f}% "
          f"({m['final']['em_count']}/{m['final']['n_test']})")
    for k in ("market_on_demand_verified", "market_on_demand_any_verification",
              "market_interruptible_verified", "rented_instance"):
        if k in c:
            print(f"USD per 1,000 samples : {c[k]['usd_per_1000_samples']:.6f}  "
                  f"({k}, ${c[k]['usd_per_hour']:.4f}/h)")


if __name__ == "__main__":
    main()
