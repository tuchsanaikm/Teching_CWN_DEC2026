"""Lab 4 / 1_single_gpu: merge the raw results into results/metrics.json and draw the charts.

Runs on the local machine (needs only matplotlib, no torch):
    python code/report.py

Reads   results/raw/   probe.json, train_metrics.json, train_log.jsonl, eval_base.json,
                       market_rtx3090.json, instance_before_destroy.json, billing.json
Writes  results/metrics.json
        results/images/vram_vs_batch.png, loss_3_epochs.png, exact_match_per_epoch.png
"""
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(os.path.dirname(HERE), "results")
RAW = os.path.join(RESULTS, "raw")
IMAGES = os.path.join(RESULTS, "images")

GPU_LIMIT_GB = 24.0

# colours: one categorical blue + orange, neutral grey for "failed", red only for the limit line
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e4e3df"
BLUE = "#2a78d6"
BLUE_LIGHT = "#9ec5f4"
ORANGE = "#eb6834"
GREY = "#b9b8b2"
CRITICAL = "#d03b3b"


def load(name, required=True):
    path = os.path.join(RAW, name)
    if not os.path.exists(path):
        if required:
            raise SystemExit(f"missing raw result: {path}")
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(name):
    with open(os.path.join(RAW, name), encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def usd_per_1000(price_per_hour, samples_per_sec):
    """Dollars to push 1,000 training examples through the GPU at this hourly price."""
    return price_per_hour / (samples_per_sec * 3600.0) * 1000.0


# ----------------------------------------------------------------------------- metrics
def build_metrics():
    probe = load("probe.json")
    tm = load("train_metrics.json")
    base = load("eval_base.json")
    market = load("market_rtx3090.json")
    inst = load("instance_before_destroy.json", required=False)
    bill = load("billing.json", required=False)

    hist = tm["history"]
    train_seconds = sum(h["train_seconds"] for h in hist)
    samples = tm["train_examples"] * len(hist)
    sps = samples / train_seconds  # whole-run average, training steps only
    best = max(hist, key=lambda h: h["exact_match"])
    last = hist[-1]

    prices = {
        "market_cheapest_verified": market["verified"]["cheapest"]["dph_total"],
        "market_cheapest_any": market["all_including_unverified"]["cheapest"]["dph_total"],
    }
    if inst:
        prices["rented_instance"] = inst["dph_total"]

    m = {
        "lab": "lab4_multigpu/1_single_gpu",
        "model": "Qwen/Qwen3-8B",
        "method": "LoRA r=%d alpha=%d on %s, bf16, max_len %d" % (
            tm["lora"]["r"], tm["lora"]["alpha"], "+".join(tm["lora"]["targets"]), tm["max_len"]),
        "gpu": {"name": "RTX 3090", "count": 1, "vram_gb": probe["gpu_total_gb"]},
        "batch_probe": [
            {k: r.get(k) for k in ("batch", "status", "peak_allocated_gb", "peak_reserved_gb",
                                   "nvidia_smi_peak_gb", "sec_per_step")}
            for r in probe["results"]
        ],
        "max_batch": probe["max_batch"],
        "train": {
            "batch_size": tm["batch_size"],
            "epochs": tm["epochs"],
            "train_examples": tm["train_examples"],
            "steps_per_epoch": tm["steps_per_epoch"],
            "train_seconds_total": round(train_seconds, 1),
            "samples_per_sec": round(sps, 3),
            "sec_per_step": round(train_seconds / (tm["steps_per_epoch"] * len(hist)), 4),
            "gpu_util_mean": round(sum(h["gpu_util_mean"] for h in hist) / len(hist), 1),
            "peak_vram_gb": max(h["peak_allocated_gb"] for h in hist),
        },
        "base": {"test_loss": base["loss"], "exact_match": base["exact_match"],
                 "exact_match_relaxed": base["exact_match_relaxed"],
                 "n_correct": base["n_correct"], "n_test": base["n"]},
        "epochs": [
            {k: h[k] for k in ("epoch", "train_loss", "test_loss", "exact_match", "exact_match_relaxed",
                               "n_correct", "n_test", "samples_per_sec", "sec_per_step",
                               "train_seconds", "eval_seconds", "gpu_util_mean", "peak_allocated_gb")}
            for h in hist
        ],
        "exact_match_final": last["exact_match"],
        "exact_match_best": {"epoch": best["epoch"], "value": best["exact_match"]},
        "market": {
            "searched_at_utc": market["searched_at_utc"],
            "query": market["query"],
            "cheapest_verified": market["verified"]["cheapest"],
            "cheapest_any": market["all_including_unverified"]["cheapest"],
            "n_offers_verified": market["verified"]["n_offers"],
            "n_offers_any": market["all_including_unverified"]["n_offers"],
        },
        "price_usd_per_hour": prices,
        "usd_per_1000_samples": {k: round(usd_per_1000(v, sps), 6) for k, v in prices.items()},
        "usd_per_1000_samples_basis": "price_per_hour / (samples_per_sec * 3600) * 1000, "
                                      "training steps only (no model load / eval time)",
    }
    if inst and bill:
        m["actual_cost"] = {
            "instance_id": inst["id"],
            "label": inst["label"],
            "price_usd_per_hour": inst["dph_total"],
            "lifetime_seconds": bill["lifetime_seconds"],
            "lifetime_minutes": round(bill["lifetime_seconds"] / 60, 1),
            "charged_usd": bill["total_charged_usd"],
            "charged_items": [{"type": i["type"], "amount": i["amount"], "description": i["description"]}
                              for c in bill["charges"] for i in c["items"]],
            "expected_usd_from_rate": round(inst["dph_total"] * bill["lifetime_seconds"] / 3600, 4),
        }
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(m, f, indent=2, ensure_ascii=False)
    return m


# ----------------------------------------------------------------------------- charts
def style(ax, title, xlabel, ylabel):
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", fontsize=13, fontweight="bold", color=INK, pad=14)
    ax.set_xlabel(xlabel, color=INK2, fontsize=10)
    ax.set_ylabel(ylabel, color=INK2, fontsize=10)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9, length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def save(fig, name):
    os.makedirs(IMAGES, exist_ok=True)
    path = os.path.join(IMAGES, name)
    fig.savefig(path, dpi=160, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    print("wrote", path)


def chart_vram(m):
    rows = m["batch_probe"]
    fig, ax = plt.subplots(figsize=(7.2, 4.4), facecolor=SURFACE)
    style(ax, "Peak VRAM vs batch size — Qwen3-8B + LoRA on one RTX 3090",
          "Batch size (256 tokens per example, 3 training steps each)", "Peak VRAM allocated (GB)")
    xs = range(len(rows))
    for x, r in zip(xs, rows):
        ok = r["status"] == "ok"
        ax.bar(x, r["peak_allocated_gb"], width=0.56, color=BLUE if ok else GREY,
               hatch=None if ok else "///", edgecolor=SURFACE, linewidth=1.5)
        label = f"{r['peak_allocated_gb']:.2f} GB" if ok else f"Out of memory\n(stopped at {r['peak_allocated_gb']:.1f} GB)"
        ax.text(x, r["peak_allocated_gb"] - 0.5 if ok else 12, label, ha="center",
                va="top" if ok else "center", fontsize=10, color="white" if ok else INK,
                fontweight="bold" if ok else "normal",
                bbox=None if ok else dict(facecolor=SURFACE, edgecolor="none", pad=3))
    ax.axhline(GPU_LIMIT_GB, color=CRITICAL, linewidth=1.6, linestyle="--")
    ax.text(len(rows) - 0.5, GPU_LIMIT_GB + 0.3, "24 GB card limit", ha="right", va="bottom",
            fontsize=9.5, color=INK)
    ax.set_xticks(list(xs))
    ax.set_xticklabels([str(r["batch"]) for r in rows])
    ax.set_xlim(-0.6, len(rows) - 0.4)
    ax.set_ylim(0, 27.5)
    ax.set_yticks(range(0, 25, 4))
    fig.text(0.125, -0.02, f"Largest batch that fits: {m['max_batch']}. Grey hatched bar = run failed with CUDA out of memory.",
             fontsize=9, color=INK2)
    save(fig, "vram_vs_batch.png")


def chart_loss(m):
    log = load_jsonl("train_log.jsonl")
    spe = m["train"]["steps_per_epoch"]
    n_ep = m["train"]["epochs"]
    fig, ax = plt.subplots(figsize=(8.4, 4.6), facecolor=SURFACE)
    style(ax, f"Loss over {n_ep} epochs — batch {m['train']['batch_size']}, {spe} steps per epoch",
          "Training step", "Cross-entropy loss (log scale)")
    ax.plot([r["global_step"] for r in log], [r["loss"] for r in log], color=BLUE, linewidth=1.3,
            label="Train loss (mean of each 10 steps)")
    ex = [e["epoch"] * spe for e in m["epochs"]]
    ey = [e["test_loss"] for e in m["epochs"]]
    ax.plot(ex, ey, color=ORANGE, linewidth=2, marker="o", markersize=8, markeredgecolor=SURFACE,
            markeredgewidth=2, label="Test loss (200 examples, end of epoch)")
    for x, y in zip(ex, ey):
        ax.annotate(f"{y:.4f}", (x, y), textcoords="offset points", xytext=(-6, 12), ha="right",
                    fontsize=9.5, color=INK, bbox=dict(facecolor=SURFACE, edgecolor="none", pad=1.5))
    ax.set_yscale("log")
    ax.set_ylim(0.004, 2)
    for e in range(1, n_ep):
        ax.axvline(e * spe, color=GRID, linewidth=1)
    top = ax.get_ylim()[1]
    for e in range(n_ep):
        ax.text((e + 0.5) * spe, top * 0.8, f"Epoch {e + 1}", ha="center", va="top", fontsize=9.5, color=INK2)
    ax.set_xlim(0, n_ep * spe * 1.01)
    ax.set_yticks([0.01, 0.03, 0.1, 0.3, 1])
    ax.set_yticklabels(["0.01", "0.03", "0.1", "0.3", "1"])
    ax.minorticks_off()
    ax.legend(loc="upper right", bbox_to_anchor=(1.0, 0.86), frameon=False, fontsize=9.5, labelcolor=INK)
    save(fig, "loss_3_epochs.png")


def chart_em(m):
    rows = [("Base model\n(no training)", m["base"])] + [(f"Epoch {e['epoch']}", e) for e in m["epochs"]]
    fig, ax = plt.subplots(figsize=(7.2, 4.4), facecolor=SURFACE)
    style(ax, "Exact Match on 200 test questions (text-to-SQL)", "", "Exact Match (%)")
    for x, (_, r) in enumerate(rows):
        v = r["exact_match"] * 100
        ax.bar(x, v, width=0.56, color=BLUE_LIGHT if x == 0 else BLUE, edgecolor=SURFACE, linewidth=1.5)
        ax.text(x, v + 1.5, f"{v:.1f}%", ha="center", va="bottom", fontsize=11, fontweight="bold", color=INK)
        ax.text(x, v + 7.5, f"{r['n_correct']}/{r['n_test']}", ha="center", va="bottom", fontsize=9, color=INK2)
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels([n for n, _ in rows], fontsize=10, color=INK)
    ax.set_ylim(0, 100)
    ax.set_xlim(-0.6, len(rows) - 0.4)
    save(fig, "exact_match_per_epoch.png")


def main():
    m = build_metrics()
    chart_vram(m)
    chart_loss(m)
    chart_em(m)
    t = m["train"]
    print(f"max batch {m['max_batch']} | {t['samples_per_sec']:.2f} samples/s | "
          f"EM final {m['exact_match_final'] * 100:.1f}% (best {m['exact_match_best']['value'] * 100:.1f}% "
          f"@ epoch {m['exact_match_best']['epoch']})")
    for k, v in m["usd_per_1000_samples"].items():
        print(f"  ${v:.5f} per 1,000 samples at ${m['price_usd_per_hour'][k]:.4f}/h ({k})")
    if "actual_cost" in m:
        a = m["actual_cost"]
        print(f"  instance lived {a['lifetime_minutes']} min, charged ${a['charged_usd']:.3f}")


if __name__ == "__main__":
    main()
