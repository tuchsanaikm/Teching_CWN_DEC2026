#!/usr/bin/env python3
"""Collect the Model Parallelism (4 x RTX 3090) numbers into results/metrics.json and draw the charts.

Reads only files under results/raw (copied back from the instance) and writes
results/metrics.json + results/images/*.png.

Optional steps that talk to Vast.ai (the API key is never read or printed here; the CLI uses its own config):
  --fetch-market      save the current 4 x RTX 3090 on-demand offers to results/raw/market/offers.json
  --fetch-instance    save a snapshot of the instance with label LABEL to results/raw/billing/instance.json
  --fetch-billing     save the charges of the instances with label LABEL to results/raw/billing/charges.json
"""
import argparse
import csv
import json
import os
import re
import subprocess
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "results", "raw")
IMG = os.path.join(ROOT, "results", "images")
LABEL = "vapp-lab4-mp4"
VAST_CWD = "/workspace/vastapp_lab"
VRAM_LIMIT_GB = 24.0

# chart style: one fixed colour per GPU (entity), neutral ink for all text
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
GPU_COLOR = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
CRITICAL = "#d03b3b"
SECRET_KEYS = re.compile(r"key|token|secret|password|jupyter", re.I)


def jload(*parts):
    with open(os.path.join(*parts)) as f:
        return json.load(f)


def jsave(obj, *parts):
    path = os.path.join(*parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
    return path


def scrub(o):
    """Drop every field whose name looks like a credential before anything is written to disk."""
    if isinstance(o, dict):
        return {k: scrub(v) for k, v in o.items() if not SECRET_KEYS.search(k)}
    if isinstance(o, list):
        return [scrub(x) for x in o]
    return o


def vast(*args):
    env = dict(os.environ, PATH="/root/.local/bin:" + os.environ.get("PATH", ""))
    r = subprocess.run(["vastai", *args, "--raw"], capture_output=True, text=True, cwd=VAST_CWD, env=env, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"vastai {args[0]} {args[1]} failed (exit {r.returncode})")
    return json.loads(r.stdout)


# ---------- Vast.ai fetch steps ----------
def fetch_market():
    # -n = no default filters, so the verified filter is applied here and both views are kept
    offers = vast("search", "offers", "-n", "gpu_name=RTX_3090 num_gpus=4 rentable=true rented=false", "-o", "dph_total")
    offers = offers.get("offers", offers) if isinstance(offers, dict) else offers
    keep = ("id", "machine_id", "host_id", "gpu_name", "num_gpus", "gpu_ram", "dph_total", "dph_base", "storage_cost",
            "min_bid", "verification", "reliability2", "geolocation", "cpu_cores_effective", "cpu_ram", "disk_space",
            "inet_down", "inet_up", "cuda_max_good", "dlperf")
    rows = [{k: o.get(k) for k in keep} for o in offers]
    jsave({"fetched_at": time.time(), "fetched_at_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
           "query": "gpu_name=RTX_3090 num_gpus=4 rentable=true rented=false (on-demand, no default filters)",
           "offers": rows}, RAW, "market", "offers.json")
    print(f"market: {len(rows)} offers saved")


def fetch_instance():
    inst = [i for i in vast("show", "instances") if i.get("label") == LABEL]
    jsave({"fetched_at": time.time(), "instances": scrub(inst)}, RAW, "billing", "instance.json")
    print(f"instance: {len(inst)} with label {LABEL} saved")


def fetch_billing():
    r = vast("show", "invoices-v1", "--charges", "--latest-first", "--limit", "100")
    rows = r.get("results", r) if isinstance(r, dict) else r
    mine = [x for x in rows if (x.get("metadata") or {}).get("label") == LABEL]
    jsave({"fetched_at": time.time(), "charges": scrub(mine)}, RAW, "billing", "charges.json")
    print(f"billing: {len(mine)} charge rows with label {LABEL} saved")


# ---------- metrics ----------
def read_util(epoch):
    """nvidia-smi rows 'gpu, util %, mem MiB' sampled every second -> {gpu: [util...]}"""
    out = {}
    with open(os.path.join(RAW, "results", f"gpu_util_epoch{epoch}.csv")) as f:
        for row in csv.reader(f):
            if len(row) == 3:
                out.setdefault(int(row[0]), []).append(float(row[1]))
    return out


def read_loss_log():
    pat = re.compile(r"epoch (\d+)/\d+ step (\d+)/(\d+) loss ([\d.]+)")
    pts = []
    with open(os.path.join(RAW, "logs", "train.log")) as f:
        for line in f:
            m = pat.search(line)
            if m:
                ep, s, n, loss = int(m[1]), int(m[2]), int(m[3]), float(m[4])
                pts.append({"epoch": ep, "step": s, "global_step": (ep - 1) * n + s, "loss": loss})
    return pts


def build_metrics():
    probe = jload(RAW, "results", "probe.json")
    train = jload(RAW, "results", "train.json")
    evals = jload(RAW, "results", "eval_all.json")
    prep = jload(RAW, "results", "prepare_info.json")
    place = jload(RAW, "results", "placement.json")

    m = {"label": LABEL, "method": "model parallelism (layers split across 4 GPUs)", "gpu": "RTX 3090 24 GB x 4",
         "model": prep["model"], "dataset": prep["dataset"], "train_samples": prep["train"], "test_samples": prep["test"],
         "placement": place["layers_per_gpu"], "vram_limit_gb": VRAM_LIMIT_GB}

    m["batch_probe"] = [{
        "batch": r["batch"], "ok": r["ok"], "sec_per_step": r.get("sec_per_step"),
        "peak_reserved_gb": [g["peak_reserved_gb"] for g in r["mem"]],
        "peak_alloc_gb": [g["peak_alloc_gb"] for g in r["mem"]],
        "smi_used_gb": [round(x / 1024, 2) for x in r["smi_used_mib"]],
        "oom_gpu": (int(re.search(r"GPU (\d)", r["error"])[1]) if not r["ok"] and re.search(r"GPU (\d)", r.get("error", "")) else None),
    } for r in probe["runs"]]
    m["max_batch"] = probe["max_batch"]
    m["first_failed_batch"] = next((r["batch"] for r in m["batch_probe"] if not r["ok"]), None)

    eps = train["epochs"]
    total_sec = sum(e["train_sec"] for e in eps)
    total_samples = sum(e["steps"] for e in eps) * train["batch"]
    m["train"] = {
        "batch": train["batch"], "epochs": len(eps), "steps": sum(e["steps"] for e in eps),
        "train_sec_total": round(total_sec, 1), "samples_total": total_samples,
        "samples_per_sec": round(total_samples / total_sec, 2),
        "sec_per_step": round(total_sec / sum(e["steps"] for e in eps), 4),
        "per_epoch": [{"epoch": e["epoch"], "train_loss_mean": e["train_loss_mean"], "train_sec": e["train_sec"],
                       "samples_per_sec": e["samples_per_sec"], "tokens_per_sec": e["tokens_per_sec"],
                       "gpu_util_mean_pct": [e["gpu_util_mean_pct"][f"gpu{g}"] for g in range(4)],
                       "smi_mem_used_max_gb": [round(e["smi_mem_used_max_mib"][f"gpu{g}"] / 1024, 2) for g in range(4)]}
                      for e in eps],
    }
    util = {g: [] for g in range(4)}
    for e in eps:
        for g, v in read_util(e["epoch"]).items():
            util[g] += v
    m["train"]["gpu_util_mean_pct"] = [round(sum(util[g]) / len(util[g]), 1) for g in range(4)]
    m["train"]["gpu_util_mean_all_pct"] = round(sum(m["train"]["gpu_util_mean_pct"]) / 4, 1)
    m["loss_curve"] = read_loss_log()

    m["eval"] = [{"tag": e["tag"], "exact_match_pct": e["exact_match"], "correct": e["correct"], "n": e["n"],
                  "test_loss": e["test_loss"]} for e in evals]
    trained = [e for e in m["eval"] if e["tag"] != "base"]
    m["exact_match_final_pct"] = trained[-1]["exact_match_pct"]
    best = max(trained, key=lambda e: e["exact_match_pct"])
    m["exact_match_best"] = {"tag": best["tag"], "exact_match_pct": best["exact_match_pct"]}

    # ---- money ----
    sps = m["train"]["samples_per_sec"]

    def usd_per_1000(dph):
        return round(dph / (sps * 3600) * 1000, 4)

    cost = {"formula": "price per hour / (samples per second * 3600) * 1000", "samples_per_sec": sps}
    mp = os.path.join(RAW, "market", "offers.json")
    if os.path.exists(mp):
        mk = jload(mp)
        offers = sorted(mk["offers"], key=lambda o: o["dph_total"])
        ver = [o for o in offers if o["verification"] == "verified"]
        slim = lambda o: {k: o[k] for k in ("id", "machine_id", "dph_total", "verification", "reliability2", "geolocation")}  # noqa: E731
        cost["market"] = {"fetched_at_utc": mk["fetched_at_utc"], "query": mk["query"], "offers_found": len(offers),
                          "verified_offers_found": len(ver),
                          "cheapest_verified": slim(ver[0]) if ver else None, "cheapest_any": slim(offers[0]),
                          "median_verified_dph": round(sorted(o["dph_total"] for o in ver)[len(ver) // 2], 4) if ver else None}
        ref = ver[0] if ver else offers[0]
        cost["market_dph_usd"] = round(ref["dph_total"], 4)
        cost["usd_per_1000_samples_market"] = usd_per_1000(ref["dph_total"])
        cost["usd_per_1000_samples_cheapest_any"] = usd_per_1000(offers[0]["dph_total"])
    ip = os.path.join(RAW, "billing", "instance.json")
    if os.path.exists(ip):
        snap = jload(ip)
        if snap["instances"]:
            i = snap["instances"][0]
            age = snap["fetched_at"] - i["start_date"]
            cost["instance"] = {"id": i["id"], "label": i["label"], "geolocation": i.get("geolocation"),
                                "dph_total_usd": round(i["dph_total"], 4), "start_date": i["start_date"],
                                "snapshot_at": snap["fetched_at"], "age_sec_at_snapshot": round(age),
                                "age_min_at_snapshot": round(age / 60, 1),
                                "estimated_cost_at_snapshot_usd": round(i["dph_total"] * age / 3600, 3)}
            cost["rented_dph_usd"] = round(i["dph_total"], 4)
            cost["usd_per_1000_samples_rented"] = usd_per_1000(i["dph_total"])
    dp = os.path.join(RAW, "billing", "destroy.json")
    if os.path.exists(dp) and "instance" in cost:
        d = jload(dp)
        age = d["destroyed_at"] - cost["instance"]["start_date"]
        cost["instance"].update(destroyed_at=d["destroyed_at"], age_sec=round(age), age_min=round(age / 60, 1),
                                estimated_cost_usd=round(cost["instance"]["dph_total_usd"] * age / 3600, 3),
                                remaining_with_label_after_destroy=d.get("remaining_with_label"))
    bp = os.path.join(RAW, "billing", "charges.json")
    if os.path.exists(bp):
        ch = jload(bp)["charges"]
        rows = [{"source": c["source"], "amount_usd": c["amount"],
                 "items": {it["type"]: {"amount_usd": it["amount"], "detail": it["description"]} for it in c.get("items", [])}}
                for c in ch]
        cur = cost.get("instance", {}).get("id")
        cost["billed"] = {"rows": rows,
                          "this_instance_usd": round(sum(r["amount_usd"] for r in rows if r["source"] == f"instance-{cur}"), 3),
                          "all_instances_with_label_usd": round(sum(r["amount_usd"] for r in rows), 3)}
    m["cost"] = cost
    return m


# ---------- charts ----------
def style(ax, xlabel, ylabel):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=INK2, labelsize=9, length=0)
    ax.set_xlabel(xlabel, color=INK2, fontsize=10)
    ax.set_ylabel(ylabel, color=INK2, fontsize=10)


def save(fig, name):
    os.makedirs(IMG, exist_ok=True)
    path = os.path.join(IMG, name)
    fig.savefig(path, dpi=160, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    print("chart:", path)


def title(ax, main, sub):
    ax.set_title(main, loc="left", color=INK, fontsize=13, fontweight="bold", pad=24)
    ax.text(0, 1.03, sub, transform=ax.transAxes, color=INK2, fontsize=9.5, va="bottom")


def chart_vram(m):
    runs = m["batch_probe"]
    x = list(range(len(runs)))
    fig, ax = plt.subplots(figsize=(8.6, 5.0), facecolor=SURFACE)
    style(ax, "Batch size (longest example, 256 tokens)", "Peak VRAM reserved by PyTorch (GB)")
    fail = [i for i, r in enumerate(runs) if not r["ok"]]
    if fail:
        ax.axvspan(fail[0] - 0.4, len(runs) - 0.6, color=CRITICAL, alpha=0.07, lw=0)
        ax.text(fail[0], 1.2, "Out of Memory", color=INK, fontsize=9.5, ha="center", fontweight="bold")
    ax.axhline(VRAM_LIMIT_GB, color=CRITICAL, lw=1.6, ls=(0, (5, 3)))
    ax.text(-0.3, VRAM_LIMIT_GB + 0.35, "24 GB per card (RTX 3090)", color=INK, fontsize=9.5, va="bottom")
    lines = {0: "-", 1: "-", 2: (0, (2, 2)), 3: "-"}  # GPU 1 and GPU 2 sit on the same values -> GPU 2 dotted on top
    role = {0: "Embedding + layers 0-8", 1: "layers 9-17", 2: "layers 18-26", 3: "layers 27-35 + LM Head"}
    for g in range(4):
        y = [r["peak_reserved_gb"][g] for r in runs]
        ax.plot(x, y, color=GPU_COLOR[g], lw=2, ls=lines[g], marker="o", ms=7, mec=SURFACE, mew=1.5,
                label=f"GPU {g}  ({role[g]})", zorder=3 + g)
    for g, dy in ((3, 0.7), (0, 0.7), (1, -1.5)):  # direct labels at the largest batch that fits
        i = max(i for i, r in enumerate(runs) if r["ok"])
        v = runs[i]["peak_reserved_gb"][g]
        ax.text(i, v + dy, f"{v:.1f}", color=INK, fontsize=9, ha="center")
    if fail:
        i = fail[0]
        v = max(runs[i]["peak_reserved_gb"])
        ax.annotate(f"GPU {runs[i]['oom_gpu']} is full\n({v:.1f} GB reserved when it failed)", (i, v), (i - 1.3, 25.2),
                    color=INK, fontsize=9, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
    ax.set_xticks(x)
    ax.set_xticklabels([str(r["batch"]) for r in runs])
    ax.set_xlim(-0.4, len(runs) - 0.6)
    ax.set_ylim(0, 27)
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.86), frameon=False, fontsize=9, labelcolor=INK)
    title(ax, "VRAM per GPU vs batch size", f"Model Parallelism on 4 x RTX 3090 - largest batch that fits: {m['max_batch']}"
          f" (batch {m['first_failed_batch']} runs out of memory); GPU 1 and GPU 2 use the same amount")
    save(fig, "vram_vs_batch.png")


def chart_util(m):
    series = {g: [] for g in range(4)}
    bounds = []
    for e in m["train"]["per_epoch"]:
        u = read_util(e["epoch"])
        for g in range(4):
            series[g] += u[g]
        bounds.append(len(series[0]))
    win = 15

    def roll(v):
        out, s = [], 0.0
        for i, x in enumerate(v):
            s += x
            if i >= win:
                s -= v[i - win]
            out.append(s / min(i + 1, win))
        return out

    fig, axes = plt.subplots(4, 1, figsize=(9.2, 7.4), facecolor=SURFACE, sharex=True, sharey=True)
    for g, ax in enumerate(axes):
        style(ax, "", "")
        t = [i / 60 for i in range(len(series[g]))]
        ax.fill_between(t, roll(series[g]), color=GPU_COLOR[g], alpha=0.18, lw=0)
        ax.plot(t, roll(series[g]), color=GPU_COLOR[g], lw=1.6)
        mean = m["train"]["gpu_util_mean_pct"][g]
        ax.axhline(mean, color=INK2, lw=0.9, ls=(0, (4, 3)))
        ax.text(1.005, mean / 100, f"mean {mean:.1f}%", transform=ax.transAxes, color=INK, fontsize=9.5, va="center")
        ax.text(0.005, 0.86, f"GPU {g}", transform=ax.transAxes, color=INK, fontsize=10.5, fontweight="bold")
        for b in bounds[:-1]:
            ax.axvline(b / 60, color=GRID, lw=1.2)
        ax.set_ylim(0, 100)
        ax.set_yticks([0, 25, 50, 75, 100])
    lo = 0
    for k, b in enumerate(bounds):
        axes[0].text((lo + b) / 120, 104, f"Epoch {k + 1}", color=INK2, fontsize=9, ha="center")
        lo = b
    axes[-1].set_xlabel("Training time (minutes)", color=INK2, fontsize=10)
    axes[-1].set_xlim(0, bounds[-1] / 60)
    fig.supylabel("GPU utilization (%), 15 s rolling mean", color=INK2, fontsize=10, x=0.03)
    fig.suptitle("GPU utilization of each card during training", x=0.075, y=0.985, ha="left", color=INK, fontsize=13,
                 fontweight="bold")
    fig.text(0.075, 0.935, f"Model Parallelism, batch {m['train']['batch']}: the cards take turns, so each one works about a "
             f"quarter of the time (average of 4 cards {m['train']['gpu_util_mean_all_pct']:.1f}%)", color=INK2, fontsize=9.5)
    fig.subplots_adjust(top=0.885, hspace=0.16, right=0.88)
    save(fig, "gpu_util.png")


def chart_loss(m):
    pts = m["loss_curve"]
    n = m["train"]["steps"] // m["train"]["epochs"]
    fig, ax = plt.subplots(figsize=(8.6, 4.8), facecolor=SURFACE)
    style(ax, "Training step", "Loss (log scale)")
    ax.set_yscale("log")
    ax.plot([p["global_step"] for p in pts], [p["loss"] for p in pts], color=GPU_COLOR[0], lw=2,
            label="Train loss (mean of each 10 steps)")
    tx = [e for e in m["eval"] if e["tag"] != "base"]
    ex = [n * (i + 1) for i in range(len(tx))]
    ax.plot(ex, [e["test_loss"] for e in tx], color=GPU_COLOR[1], lw=0, marker="D", ms=9, mec=SURFACE, mew=1.5,
            label="Test loss after each Epoch (200 examples)", zorder=5)
    for xx, e in zip(ex, tx):
        ax.text(xx - 8, e["test_loss"] * 1.18, f"{e['test_loss']:.4f}", color=INK, fontsize=9, ha="right")
    for k in range(m["train"]["epochs"]):
        if k:
            ax.axvline(n * k, color=GRID, lw=1.2)
        ep = m["train"]["per_epoch"][k]
        ax.text(n * k + n / 2, 0.92, f"Epoch {k + 1}\nmean train loss {ep['train_loss_mean']:.4f}", color=INK2, fontsize=9,
                ha="center", va="top", transform=ax.get_xaxis_transform())
    ax.set_xlim(0, n * m["train"]["epochs"] + 6)
    ax.set_ylim(0.012, 2.2)
    ax.set_yticks([0.02, 0.05, 0.1, 0.2, 0.5, 1, 2])
    ax.set_yticklabels(["0.02", "0.05", "0.1", "0.2", "0.5", "1", "2"])
    ax.minorticks_off()
    ax.legend(loc="upper right", bbox_to_anchor=(1.0, 0.8), frameon=False, fontsize=9, labelcolor=INK)
    base = next(e for e in m["eval"] if e["tag"] == "base")
    title(ax, "Loss over 3 Epochs", f"{m['model']} + LoRA, text to SQL, batch {m['train']['batch']}, {m['train']['steps']} steps"
          f" - test loss before training {base['test_loss']:.2f}")
    save(fig, "loss.png")


def chart_em(m):
    ev = m["eval"]
    names = ["Base (no training)" if e["tag"] == "base" else e["tag"].replace("epoch", "Epoch ") for e in ev]
    fig, ax = plt.subplots(figsize=(7.4, 4.6), facecolor=SURFACE)
    style(ax, "", "Exact Match on the Test Set (%)")
    bars = ax.bar(range(len(ev)), [e["exact_match_pct"] for e in ev], width=0.5, color=GPU_COLOR[0])
    for b, e in zip(bars, ev):
        ax.text(b.get_x() + b.get_width() / 2, e["exact_match_pct"] + 1.5, f"{e['exact_match_pct']:.1f}%\n{e['correct']}/{e['n']}",
                color=INK, fontsize=9.5, ha="center", va="bottom")
    ax.set_xticks(range(len(ev)))
    ax.set_xticklabels(names, color=INK)
    ax.set_ylim(0, 100)
    title(ax, "Exact Match after each Epoch", f"{m['test_samples']} test examples, generated SQL must equal the reference exactly"
          f" - best: {m['exact_match_best']['tag'].replace('epoch', 'Epoch ')}")
    save(fig, "exact_match.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch-market", action="store_true")
    ap.add_argument("--fetch-instance", action="store_true")
    ap.add_argument("--fetch-billing", action="store_true")
    a = ap.parse_args()
    if a.fetch_market:
        fetch_market()
    if a.fetch_instance:
        fetch_instance()
    if a.fetch_billing:
        fetch_billing()
    m = build_metrics()
    jsave(m, ROOT, "results", "metrics.json")
    chart_vram(m)
    chart_util(m)
    chart_loss(m)
    chart_em(m)
    c = m["cost"]
    print(f"max_batch={m['max_batch']} samples_per_sec={m['train']['samples_per_sec']} "
          f"exact_match_final={m['exact_match_final_pct']} best={m['exact_match_best']}")
    print({k: v for k, v in c.items() if k.startswith(("usd_", "market_dph", "rented_dph"))})
    print("instance:", c.get("instance"))
    print("billed:", {k: v for k, v in c.get("billed", {}).items() if k != "rows"})


if __name__ == "__main__":
    main()
