#!/usr/bin/env python3
"""Lab 4 / model parallelism: merge raw results into results/metrics.json and draw the charts.

Reads only results/raw/ (offline, no API call). Run:  python3 code/report.py
Outputs:  results/metrics.json  and  results/images/*.png
"""
import glob
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "results", "raw")
IMG = os.path.join(ROOT, "results", "images")
GPU_TOTAL_MIB = 24576  # RTX 3090 = 24 GB
GPUS = ["gpu0", "gpu1"]

# colours: categorical slots 1-2 of the validated palette; colour follows the GPU in every chart
C = {"gpu0": "#2a78d6", "gpu1": "#eb6834"}
NAME = {"gpu0": "GPU 0 (embed + layers 0-17)", "gpu1": "GPU 1 (layers 18-35 + lm_head)"}
INK, INK2, GRID, SURFACE, CRIT = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb", "#d03b3b"


def load(name, default=None):
    path = os.path.join(RAW, name)
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)


def usd_per_1k(dph, samples_per_sec):
    """$ for 1,000 training samples at an hourly price and a measured speed."""
    return dph / 3600.0 / samples_per_sec * 1000.0


# ----------------------------------------------------------------------------- metrics
def build_metrics():
    probes = sorted((json.load(open(p)) for p in glob.glob(os.path.join(RAW, "probe_b*.json"))),
                    key=lambda p: p["batch"])
    train = load("train_summary.json")
    evals = {t: load(f"eval_{t}.json") for t in ["base", "epoch1", "epoch2", "epoch3"]}
    inst = load("instance_final.json")
    market = load("market_offers.json")
    billing = load("billing.json")
    hist = train["history"]

    max_batch = max(p["batch"] for p in probes if p["status"] == "ok")
    assert max_batch == train["batch"] == int(open(os.path.join(RAW, "max_batch.txt")).read())

    samples = sum(h["samples"] for h in hist)
    sps = samples / sum(h["epoch_wall_sec"] for h in hist)  # whole-run throughput

    m = {
        "lab": "lab4_multigpu/3_model_parallel",
        "model": "Qwen/Qwen3-8B (bf16) + LoRA, one model split across 2 GPUs",
        "dataset": "b-mc2/sql-create-context (train 4000 / test 200)",
        "machine": {
            "label": inst["label"], "instance_id": inst["id"], "gpu": inst["gpu_name"],
            "num_gpus": inst["num_gpus"], "gpu_ram_mib": inst["gpu_ram"],
            "geolocation": inst["geolocation"], "verification": inst.get("verification"),
            "dph_total": round(inst["dph_total"], 4), "dph_gpu": round(inst["dph_base"], 4),
        },
        "placement": train["placement"],
        "batch_probe": [{
            "batch": p["batch"], "status": p["status"],
            "vram_smi_mib": p["smi_mem_used_mib"],
            "vram_torch_peak_allocated_mib": {g: p["vram_peak"][g]["allocated_mib"] for g in GPUS},
            "sec_per_step": round(sum(p["step_sec"][1:]) / len(p["step_sec"][1:]), 3)
            if len(p["step_sec"]) > 1 else None,
        } for p in probes],
        "max_batch": max_batch,
        "first_oom_batch": next((p["batch"] for p in probes if p["status"] != "ok"), None),
        "train": {
            "batch": train["batch"], "epochs": train["epochs"], "total_samples": samples,
            "train_wall_sec": round(sum(h["epoch_wall_sec"] for h in hist), 1),
            "samples_per_sec": round(sps, 3),
            "sec_per_step": round(sum(h["sec_per_step"] for h in hist) / len(hist), 4),
            "gpu_util_mean_pct": {g: round(sum(h["gpu"][g]["util_mean"] for h in hist) / len(hist), 1)
                                  for g in GPUS},
            "vram_smi_max_mib": {g: max(h["gpu"][g]["smi_mem_max_mib"] for h in hist) for g in GPUS},
            "vram_torch_peak_allocated_mib": {g: max(h["vram_peak"][g]["allocated_mib"] for h in hist)
                                              for g in GPUS},
        },
        "epochs": [{
            "epoch": h["epoch"], "train_loss": h["train_loss"],
            "samples_per_sec": h["samples_per_sec"], "sec_per_step": h["sec_per_step"],
            "epoch_wall_sec": h["epoch_wall_sec"],
            "gpu_util_mean_pct": {g: h["gpu"][g]["util_mean"] for g in GPUS},
            "test_loss": evals[f"epoch{h['epoch']}"]["test_loss"],
            "exact_match": evals[f"epoch{h['epoch']}"]["exact_match"],
            "exact_match_loose": evals[f"epoch{h['epoch']}"]["exact_match_loose"],
        } for h in hist],
        "base": {k: evals["base"][k] for k in ["test_loss", "exact_match", "exact_match_loose"]},
        "exact_match_final": evals[f"epoch{len(hist)}"]["exact_match"],
        "exact_match_best": max(evals[f"epoch{h['epoch']}"]["exact_match"] for h in hist),
        "exact_match_best_epoch": max(hist, key=lambda h: evals[f"epoch{h['epoch']}"]["exact_match"])["epoch"],
        "n_test": evals["epoch1"]["n"],
    }

    # --- price: cheapest 2x RTX 3090 on the market, and money per 1,000 training samples
    v, a = market["verified"]["offers"][0], market["all_incl_unverified"]["offers"][0]
    m["market_price"] = {
        "searched_at": market["searched_at"], "what": "cheapest on-demand offer, RTX 3090 x2, $/hour (dph_total)",
        "cheapest_verified": {"dph_total": round(v["dph_total"], 4), "offer_id": v["id"],
                              "geolocation": v["geolocation"], "n_offers": market["verified"]["n_offers"]},
        "cheapest_any": {"dph_total": round(a["dph_total"], 4), "offer_id": a["id"],
                         "geolocation": a["geolocation"], "verification": a["verification"],
                         "n_offers": market["all_incl_unverified"]["n_offers"]},
    }
    m["usd_per_1000_samples"] = {
        "formula": "price_per_hour / 3600 / samples_per_sec * 1000",
        "at_market_cheapest_verified": round(usd_per_1k(v["dph_total"], sps), 5),
        "at_market_cheapest_any": round(usd_per_1k(a["dph_total"], sps), 5),
        "at_rented_price": round(usd_per_1k(inst["dph_total"], sps), 5),
    }

    # --- what the machine really cost
    destroyed = float(open(os.path.join(RAW, "destroyed_at_unix.txt")).read())
    age = destroyed - inst["start_date"]
    cost = {"age_sec": round(age), "age_min": round(age / 60, 1), "age_hours": round(age / 3600, 3),
            "start_unix": inst["start_date"], "destroyed_unix": destroyed,
            "estimate_age_x_dph_total_usd": round(age / 3600 * inst["dph_total"], 3)}
    if billing:
        items = {}
        for row in billing["charges"]:
            for it in row.get("items", []):
                items[it["type"]] = round(items.get(it["type"], 0) + it["amount"], 4)
        cost.update({"billed_usd": billing["total_charged_usd"], "billed_items_usd": items,
                     "billed_detail": [it["description"] for r in billing["charges"] for it in r.get("items", [])],
                     "billing_fetched_unix": billing["fetched_unix"]})
    m["actual_cost"] = cost
    return m


# ----------------------------------------------------------------------------- charts
def style():
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.family": "DejaVu Sans", "font.size": 10.5, "text.color": INK,
        "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
        "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
        "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.8,
        "axes.axisbelow": True, "xtick.major.size": 0, "ytick.major.size": 0,
        "legend.frameon": False, "lines.linewidth": 2,
    })


def finish(fig, ax, title, subtitle, name):
    fig.text(0.02, 0.965, title, fontsize=13.5, fontweight="bold", va="top", ha="left")
    fig.text(0.02, 0.905, subtitle, fontsize=10, color=INK2, va="top", ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    os.makedirs(IMG, exist_ok=True)
    fig.savefig(os.path.join(IMG, name), dpi=160)
    plt.close(fig)
    print("wrote", os.path.join("results", "images", name))


def chart_vram(m):
    probes = m["batch_probe"]
    xs = list(range(len(probes)))
    fig, ax = plt.subplots(figsize=(8, 5))
    for g in GPUS:
        gb = [p["vram_smi_mib"][g] / 1024 for p in probes]
        ok = [i for i, p in enumerate(probes) if p["status"] == "ok"]
        bad = [i for i, p in enumerate(probes) if p["status"] != "ok"]
        ax.plot([xs[i] for i in ok], [gb[i] for i in ok], color=C[g], marker="o", ms=7,
                mec=SURFACE, mew=1.5, label=NAME[g], zorder=3)
        if bad:  # the failed batch: dashed segment + hollow marker = memory in use when it crashed
            ax.plot([xs[ok[-1]], xs[bad[0]]], [gb[ok[-1]], gb[bad[0]]], color=C[g], ls=(0, (2, 2)),
                    lw=1.6, zorder=2)
            ax.plot([xs[i] for i in bad], [gb[i] for i in bad], ls="none", marker="o", ms=8,
                    mfc=SURFACE, mec=C[g], mew=2, zorder=3)
        for i in xs:
            if i in bad:  # label to the right so it does not sit on the 24 GB line
                off, ha = (11, -3), "left"
            else:
                off, ha = (0, 9 if g == "gpu1" else -15), "center"
            ax.annotate(f"{gb[i]:.1f}", (xs[i], gb[i]), xytext=off,
                        textcoords="offset points", ha=ha, fontsize=9, color=INK2)
    ax.axhline(GPU_TOTAL_MIB / 1024, color=CRIT, lw=1.5, ls="--", zorder=1)
    ax.text(xs[0] - 0.3, 24.35, "24 GB = RTX 3090 limit", color=INK, fontsize=9.5, va="bottom")
    oom = [i for i, p in enumerate(probes) if p["status"] != "ok"]
    if oom:
        ax.axvspan(oom[0] - 0.42, oom[0] + 0.42, color=CRIT, alpha=0.07, lw=0)
        ax.text(oom[0], 2.2, "Out of memory\non GPU 1 at step 1", ha="center", va="bottom",
                fontsize=9.5, color=INK)
    ax.set_xticks(xs)
    ax.set_xticklabels([str(p["batch"]) for p in probes])
    ax.set_xlim(-0.45, len(xs) - 0.45)
    ax.set_ylim(0, 27)
    ax.set_yticks(range(0, 25, 4))
    ax.set_xlabel("Batch size (3 probe steps, every sequence 256 tokens)")
    ax.set_ylabel("VRAM used (GB, nvidia-smi)")
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.88))
    finish(fig, ax, f"VRAM per GPU vs batch size: batch {m['max_batch']} is the largest that fits",
           "Qwen3-8B split across 2x RTX 3090. GPU 1 holds the logits and loss, so it fills up first.",
           "vram_vs_batch.png")


def chart_util(m):
    eps = m["epochs"]
    labels = [f"Epoch {e['epoch']}" for e in eps] + ["Mean"]
    vals = {g: [e["gpu_util_mean_pct"][g] for e in eps] + [m["train"]["gpu_util_mean_pct"][g]] for g in GPUS}
    fig, ax = plt.subplots(figsize=(8, 5))
    w = 0.34
    for k, g in enumerate(GPUS):
        xs = [i + (k - 0.5) * (w + 0.03) for i in range(len(labels))]
        bars = ax.bar(xs, vals[g], w, color=C[g], label=NAME[g], zorder=3)
        for b, v in zip(bars, vals[g]):
            ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.1f}%", ha="center", fontsize=9.5,
                    color=INK2)
    ax.axvline(len(eps) - 0.5, color=GRID, lw=1)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 100)
    ax.set_yticks(range(0, 101, 20))
    ax.set_ylabel("Mean GPU utilisation during training (%)")
    ax.legend(loc="upper left", ncols=2)
    t = m["train"]["gpu_util_mean_pct"]
    finish(fig, ax, f"GPU utilisation: each card is busy only about half the time "
                    f"({t['gpu0']:.0f}% / {t['gpu1']:.0f}%)",
           f"Batch {m['max_batch']}, nvidia-smi sampled about once per second. The two halves of the model "
           "run one after the other,\nnot at the same time.", "gpu_util.png")


def chart_loss(m):
    steps = [json.loads(line) for line in open(os.path.join(RAW, "train_steps.jsonl"))]
    spe = len(steps) // len(m["epochs"])
    loss = [s["loss"] for s in steps]
    k = 25
    smooth = [sum(loss[max(0, i - k + 1):i + 1]) / len(loss[max(0, i - k + 1):i + 1]) for i in range(len(loss))]
    x = [(i + 1) / spe for i in range(len(loss))]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(x, loss, color=C["gpu0"], lw=0.7, alpha=0.28, zorder=2)
    ax.plot(x, smooth, color=C["gpu0"], lw=2, label=f"Train loss ({k}-step moving average; faint = every step)",
            zorder=3)
    ex = [e["epoch"] for e in m["epochs"]]
    ey = [e["test_loss"] for e in m["epochs"]]
    ax.plot(ex, ey, ls="none", marker="D", ms=8, color=C["gpu1"], mec=SURFACE, mew=1.5,
            label=f"Test loss at end of epoch ({m['n_test']} samples)", zorder=4)
    for a, b in zip(ex, ey):
        ax.annotate(f"{b:.3f}", (a, b), xytext=(-6, 9), textcoords="offset points", ha="right",
                    fontsize=9.5, color=INK2)
    for e in m["epochs"]:
        ax.text(e["epoch"] - 0.5, 0.00135, f"epoch {e['epoch']} mean\ntrain loss {e['train_loss']:.4f}",
                ha="center", va="bottom", fontsize=9.5, color=INK2)
        if e["epoch"] < len(m["epochs"]):
            ax.axvline(e["epoch"], color=GRID, lw=1, zorder=1)
    ax.set_yscale("log")
    ax.set_ylim(0.001, 4)
    ax.set_xlim(0, len(m["epochs"]) + 0.03)
    ax.set_xticks(range(0, len(m["epochs"]) + 1))
    ax.set_xlabel(f"Epoch ({spe} steps each, batch {m['max_batch']})")
    ax.set_ylabel("Loss (log scale)")
    ax.legend(loc="upper right")
    e = m["epochs"]
    finish(fig, ax, f"Loss over 3 epochs: train loss keeps falling, test loss is flat after epoch 2",
           f"Train loss per epoch {e[0]['train_loss']:.3f} -> {e[1]['train_loss']:.3f} -> {e[2]['train_loss']:.3f}; "
           f"test loss {e[0]['test_loss']:.3f} -> {e[1]['test_loss']:.3f} -> {e[2]['test_loss']:.3f} "
           f"(base model {m['base']['test_loss']:.2f}).", "loss.png")


def chart_em(m):
    labels = ["Base\n(no LoRA)"] + [f"Epoch {e['epoch']}" for e in m["epochs"]]
    vals = [m["base"]["exact_match"]] + [e["exact_match"] for e in m["epochs"]]
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(range(len(vals)), vals, 0.5, color=C["gpu0"], zorder=3)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.1f}%", ha="center", fontsize=11,
                color=INK, fontweight="bold")
    ax.set_xticks(range(len(vals)))
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 100)
    ax.set_yticks(range(0, 101, 20))
    ax.set_ylabel(f"Exact Match on the test set (%, n = {m['n_test']})")
    finish(fig, ax, f"Exact Match per epoch: {vals[1]:.1f}% -> {vals[2]:.1f}% -> {vals[3]:.1f}%",
           f"Strict string match of the generated SQL (whitespace collapsed only). The base model scores 0%\n"
           f"because it writes other quotes and letter case; ignoring those it gets "
           f"{m['base']['exact_match_loose']:.1f}% (fine-tuned: "
           f"{m['epochs'][-1]['exact_match_loose']:.1f}%).", "exact_match.png")


def main():
    m = build_metrics()
    with open(os.path.join(ROOT, "results", "metrics.json"), "w") as f:
        json.dump(m, f, indent=1, ensure_ascii=False)
    print("wrote results/metrics.json")
    style()
    chart_vram(m)
    chart_util(m)
    chart_loss(m)
    chart_em(m)
    u, c = m["usd_per_1000_samples"], m["actual_cost"]
    print(f"max batch {m['max_batch']} | {m['train']['samples_per_sec']:.2f} samples/s | "
          f"EM final {m['exact_match_final']}% (best {m['exact_match_best']}% @ epoch {m['exact_match_best_epoch']})")
    print(f"$ per 1,000 samples: market verified {u['at_market_cheapest_verified']:.4f} | "
          f"market any {u['at_market_cheapest_any']:.4f} | rented {u['at_rented_price']:.4f}")
    print(f"machine age {c['age_min']} min | billed ${c.get('billed_usd', 'n/a')} | "
          f"estimate ${c['estimate_age_x_dph_total_usd']}")


if __name__ == "__main__":
    main()
