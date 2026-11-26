"""Lab 4 · Data Parallelism · 4x RTX 3090 — merge the raw results into results/metrics.json and draw the charts.

Reads   results/raw/            raw outputs pulled from the instance (probe, train metrics, eval)
        results/machine.json    the machine that was rented
        results/billing/        market search results, instance snapshot, billed charges
Writes  results/metrics.json, results/report.md, results/images/*.png

Run:  python3 code/report.py
"""
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
RAW, BILL, IMG = f"{ROOT}/raw", f"{ROOT}/billing", f"{ROOT}/images"
os.makedirs(IMG, exist_ok=True)


def load(path, default=None):
    return json.load(open(path)) if os.path.exists(path) else default


# ----------------------------------------------------------------------------- inputs
probe = load(f"{RAW}/batch_probe.json")
train = load(f"{RAW}/train_metrics.json")
evals = {t: load(f"{RAW}/eval/eval_{t}.json") for t in ["base", "epoch1", "epoch2", "epoch3"]}
machine = load(f"{ROOT}/machine.json")
NGPU = probe["ngpu"]
GPUS = list(range(NGPU))
GPU_TOTAL_MIB = 24576  # nvidia-smi memory.total of an RTX 3090 = 24 GB (GiB)
epochs = train["epochs"]

# ----------------------------------------------------------------------------- speed
tot_sec = sum(e["epoch_sec"] for e in epochs)
tot_samples = sum(e["samples"] for e in epochs)
tot_steps = sum(e["steps"] for e in epochs)
sps = tot_samples / tot_sec  # training samples per second, all 3 epochs, all 4 GPUs together
util_mean = [sum(e["gpu_util_mean"][g] * e["epoch_sec"] for e in epochs) / tot_sec for g in GPUS]
train_peak = [max(e["nvidia_smi_peak_mib"][g] for e in epochs) for g in GPUS]


# ----------------------------------------------------------------------------- market price
def cheapest(name, price_key="dph_total"):
    offers = load(f"{BILL}/market_{name}.json", [])
    if not offers:
        return None
    o = min(offers, key=lambda x: x[price_key])
    return {"usd_per_hour": round(o[price_key], 4), "offer_id": o["id"], "machine_id": o["machine_id"],
            "verification": o.get("verification"), "reliability": round(o.get("reliability2") or 0, 4),
            "geolocation": o.get("geolocation"), "inet_down_mbps": o.get("inet_down"), "offers_found": len(offers)}


market = {
    "searched_at_utc": open(f"{BILL}/market_time.txt").read().strip() if os.path.exists(f"{BILL}/market_time.txt") else None,
    "query": "gpu_name=RTX_3090 num_gpus=4 rentable=true, 60 GB disk included in the price, sorted by dph_total",
    "cheapest_on_demand_any": cheapest("all_ondemand"),            # verified or not
    "cheapest_on_demand_verified": cheapest("verified_ondemand"),
    "cheapest_interruptible_verified_min_bid": cheapest("verified_bid", "min_bid"),
}


def usd_per_1000(usd_per_hour, samples_per_sec=None):
    """Money to push 1,000 training samples through the 4 GPUs at a given hourly price."""
    return usd_per_hour / 3600.0 / (samples_per_sec or sps) * 1000.0


prices = {"rented_machine": machine["dph_total"]}
for k in ["cheapest_on_demand_any", "cheapest_on_demand_verified", "cheapest_interruptible_verified_min_bid"]:
    if market[k]:
        prices["market_" + k] = market[k]["usd_per_hour"]
cost = {k: {"usd_per_hour": round(p, 4), "usd_per_1000_samples": round(usd_per_1000(p), 6),
            "usd_for_3_epochs_12000_samples": round(p / 3600 * tot_sec, 4)} for k, p in prices.items()}

# ----------------------------------------------------------------------------- real bill
snap = load(f"{BILL}/instance_before_destroy.json")
charges = load(f"{BILL}/charges.json")
after = load(f"{BILL}/after_destroy.json")
bill = None
if snap:
    destroy_t = float(open(f"{BILL}/destroy_time.txt").read()) if os.path.exists(f"{BILL}/destroy_time.txt") else snap["snapshot_time"]
    age = destroy_t - snap["start_date"]
    bill = {"instance_id": snap["id"], "label": snap["label"], "usd_per_hour": snap["dph_total"],
            "start_utc": snap["start_date"], "destroy_utc": destroy_t,
            "age_sec": round(age, 1), "age_min": round(age / 60, 2), "age_hours": round(age / 3600, 4),
            "estimate_usd_age_x_price": round(age / 3600 * snap["dph_total"], 4),
            "destroyed_and_verified_gone": bool(after) and all(i["label"] != snap["label"] for i in after["remaining_instances"])}
    if charges:
        rows = charges["charges"]
        by_type = {}
        for r in rows:
            for it in r.get("items", []):
                by_type[it["type"]] = round(by_type.get(it["type"], 0) + it["amount"], 4)
        this = [r for r in rows if r.get("source") == f"instance-{snap['id']}"]
        bill.update({
            "charged_usd_this_instance": round(sum(r["amount"] for r in this), 4),
            "charged_usd_all_instances_with_label": round(sum(r["amount"] for r in rows), 4),
            "charged_by_type_usd_all_with_label": by_type,  # gpu / disk / bwd (download) / bwu (upload)
            "charge_rows": [{"source": r.get("source"), "amount": r["amount"],
                             "items": {it["type"]: [it["amount"], it["description"]] for it in r.get("items", [])}} for r in rows],
            "charges_fetched_at_utc": charges["fetched_at"]})

# ----------------------------------------------------------------------------- metrics.json
ok = [p for p in probe["probes"] if p["status"] == "ok"]
metrics = {
    "lab": "Lab 4 - Data Parallelism (DDP), 4x RTX 3090",
    "model": "Qwen/Qwen3-8B + LoRA (bf16 base, gradient checkpointing)", "dataset": "b-mc2/sql-create-context",
    "train_samples": 4000, "test_samples": evals["base"]["n"], "max_len_tokens": train["max_len"],
    "machine": {k: machine.get(k) for k in ["id", "label", "gpu_name", "num_gpus", "dph_total", "geolocation", "cpu_name",
                                              "cpu_cores", "cpu_ram", "pci_gen", "gpu_lanes", "image_uuid"]},
    "batch_probe": {
        "max_batch_per_gpu": probe["max_batch_per_gpu"], "max_global_batch": probe["max_batch_per_gpu"] * NGPU,
        "gpu_total_mib": GPU_TOTAL_MIB,
        "rows": [{"batch_per_gpu": p["batch_per_gpu"], "global_batch": p.get("global_batch"), "status": p["status"],
                  "vram_peak_mib_per_gpu": p.get("nvidia_smi_peak_mib"),
                  "torch_allocated_mib_per_gpu": p.get("torch_allocated_mib"),
                  "sec_per_step": round(sum(p["sec_per_step"][1:]) / len(p["sec_per_step"][1:]), 4) if p["status"] == "ok" else None}
                 for p in probe["probes"]]},
    "training": {
        "batch_per_gpu": train["batch_per_gpu"], "global_batch": train["global_batch"], "lr": train["lr"],
        "steps_per_epoch": train["steps_per_epoch"], "epochs": len(epochs), "total_steps": tot_steps,
        "total_samples": tot_samples, "total_sec": round(tot_sec, 1),
        "samples_per_sec": round(sps, 2), "samples_per_sec_per_gpu": round(sps / NGPU, 2),
        "sec_per_step": round(tot_sec / tot_steps, 4),
        "gpu_util_mean_pct_per_gpu": [round(u, 1) for u in util_mean],
        "vram_peak_mib_per_gpu": train_peak,
        "per_epoch": [{"epoch": e["epoch"], "train_loss_mean": round(e["train_loss_mean"], 4),
                       "train_loss_last10": round(e["train_loss_last10"], 4), "epoch_sec": e["epoch_sec"],
                       "samples_per_sec": e["samples_per_sec"], "gpu_util_mean_pct_per_gpu": e["gpu_util_mean"],
                       "vram_peak_mib_per_gpu": e["nvidia_smi_peak_mib"],
                       "test_loss": evals[f"epoch{e['epoch']}"]["test_loss"],
                       "exact_match": evals[f"epoch{e['epoch']}"]["exact_match"],
                       "exact_match_loose": evals[f"epoch{e['epoch']}"]["exact_match_loose"]} for e in epochs]},
    "eval": {t: {k: ev[k] for k in ["n", "test_loss", "exact_match", "em_correct", "exact_match_loose"]} for t, ev in evals.items()},
    "market": market,
    "cost": cost,
    "headline": {
        "max_batch_per_gpu": probe["max_batch_per_gpu"], "samples_per_sec": round(sps, 2),
        "exact_match_final": evals["epoch3"]["exact_match"],
        "usd_per_1000_samples_rented": cost["rented_machine"]["usd_per_1000_samples"],
        "usd_per_1000_samples_market_cheapest": cost.get("market_cheapest_on_demand_any", {}).get("usd_per_1000_samples")},
    "actual_bill": bill,
}
json.dump(metrics, open(f"{ROOT}/metrics.json", "w"), indent=1, ensure_ascii=False)

# ----------------------------------------------------------------------------- chart style
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]  # one fixed colour per GPU (GPU0..GPU3), same in every chart
RED = "#e34948"
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE, "font.size": 11,
    "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "axes.edgecolor": GRID,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left", "legend.frameon": False})
SUB = "Qwen3-8B + LoRA · DDP on 4x RTX 3090 · sequences padded/truncated to 256 tokens"


def finish(fig, ax, name, subtitle=SUB):
    ax.tick_params(length=0)
    fig.text(0.012, 0.012, subtitle, fontsize=8.5, color=INK2, ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(f"{IMG}/{name}", dpi=160)
    plt.close(fig)


def grouped(ax, groups, values_per_gpu, width=0.19, fmt="{:.1f}", label_size=8, rotation=0):
    """values_per_gpu[group][gpu]; bars of one GPU share one colour and are separated by a thin surface gap."""
    for g in GPUS:
        xs = [i + (g - (NGPU - 1) / 2) * width for i in range(len(groups))]
        ys = [v[g] if v else 0 for v in values_per_gpu]
        bars = ax.bar(xs, ys, width=width, color=C[g], edgecolor=SURFACE, linewidth=1.5, label=f"GPU {g}")
        for b, v in zip(bars, values_per_gpu):
            if v:
                ax.annotate(fmt.format(v[g]), (b.get_x() + b.get_width() / 2, b.get_height()), xytext=(0, 3),
                            textcoords="offset points", ha="center", va="bottom", fontsize=label_size, color=INK2,
                            rotation=rotation)
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels(groups)


# ----------------------------------------------------------------------------- 1) VRAM vs batch
GIB = 1024.0
groups, vals = [], []
for p in probe["probes"]:
    groups.append(f"{p['batch_per_gpu']}\n(global {p['global_batch']})")
    vals.append([m / GIB for m in p["nvidia_smi_peak_mib"]] if p["status"] == "ok" else None)
    if p["status"] == "ok" and p["batch_per_gpu"] == train["batch_per_gpu"]:  # the real 3-epoch run at this batch
        groups.append(f"{p['batch_per_gpu']}\n(full 3-epoch run)")
        vals.append([m / GIB for m in train_peak])
fig, ax = plt.subplots(figsize=(11, 6))
grouped(ax, groups, vals)
limit = GPU_TOTAL_MIB / GIB
ax.axhline(limit, color=RED, linewidth=2, linestyle=(0, (6, 3)), zorder=3)
ax.annotate("24 GB — RTX 3090 memory limit", (-0.45, limit), xytext=(0, 5), textcoords="offset points",
            color=INK, fontsize=10, fontweight="bold", va="bottom")
for i, p in zip([i for i, g in enumerate(groups) if "run" not in g], probe["probes"]):
    if p["status"] != "ok":
        ax.bar(i, limit, width=0.19 * NGPU, color="none", edgecolor=RED, hatch="////", linewidth=1.2, zorder=2)
        ax.text(i, limit / 2, "Out of Memory\non all 4 GPUs\n(needs > 24 GB)", ha="center", va="center", fontsize=10,
                fontweight="bold", color=INK, bbox=dict(facecolor=SURFACE, edgecolor="none", pad=4))
ax.set_ylim(0, 27.5)
ax.set_ylabel("Peak VRAM per GPU (GB, nvidia-smi)")
ax.set_xlabel("Batch size per GPU")
ax.set_title(f"Peak VRAM of each GPU vs batch size — largest batch that fits: {probe['max_batch_per_gpu']} per GPU")
ax.legend(ncol=NGPU, loc="upper center", bbox_to_anchor=(0.5, -0.17), fontsize=9.5)
finish(fig, ax, "vram_vs_batch.png", SUB + " · 3 probe steps per batch size")

# ----------------------------------------------------------------------------- 2) GPU utilisation
fig, ax = plt.subplots(figsize=(10, 5.2))
grouped(ax, [f"Epoch {e['epoch']}" for e in epochs] + ["All 3 epochs"], [e["gpu_util_mean"] for e in epochs] + [util_mean],
        fmt="{:.0f}%", label_size=8.5)
ax.set_ylim(0, 112)
ax.set_yticks(range(0, 101, 20))
ax.set_ylabel("Mean GPU utilization (%)")
ax.set_title(f"GPU utilization of each GPU during training — all four average {min(util_mean):.1f}–{max(util_mean):.1f}%")
ax.legend(ncol=NGPU, loc="upper center", bbox_to_anchor=(0.5, -0.08), fontsize=9.5)
finish(fig, ax, "gpu_util.png", SUB + f" · batch {train['batch_per_gpu']} per GPU")

# ----------------------------------------------------------------------------- 3) loss over 3 epochs
losses = [l for e in epochs for l in e["losses"]]
steps = list(range(1, len(losses) + 1))
W = 20
smooth = [sum(losses[max(0, i - W + 1):i + 1]) / len(losses[max(0, i - W + 1):i + 1]) for i in range(len(losses))]
spe = train["steps_per_epoch"]
fig, ax = plt.subplots(figsize=(10, 5.4))
ax.plot(steps, losses, color="#b9b8b2", linewidth=0.8, label="Train loss (each step)")
ax.plot(steps, smooth, color=C[0], linewidth=2, label=f"Train loss (mean of last {W} steps)")
tx = [spe * e["epoch"] for e in epochs]
ty = [evals[f"epoch{e['epoch']}"]["test_loss"] for e in epochs]
ax.plot(tx, ty, color=C[1], linewidth=2, marker="o", markersize=8, markeredgecolor=SURFACE, markeredgewidth=2,
        label="Test loss (200 test samples, end of epoch)", zorder=4)
for x, y in zip(tx, ty):
    ax.annotate(f"{y:.4f}", (x, y), xytext=(-6, 9), textcoords="offset points", ha="right", fontsize=9, color=INK)
ax.set_yscale("log")
ax.set_ylim(min(losses) * 0.7, max(losses) * 1.3)
for e in epochs:
    x0 = spe * (e["epoch"] - 1)
    if x0:
        ax.axvline(x0 + 0.5, color=GRID, linewidth=1.2)
    ax.text(x0 + spe / 2, max(losses) * 1.12, f"Epoch {e['epoch']} · mean train loss {e['train_loss_mean']:.4f}",
            ha="center", va="top", fontsize=9.5, color=INK2)
ax.set_xlim(0, len(losses) + 5)
ax.set_xticks(range(0, len(losses) + 1, 50))
ax.set_xlabel(f"Training step (global batch {train['global_batch']} = {train['batch_per_gpu']} per GPU x {NGPU} GPUs)")
ax.set_ylabel("Loss (log scale)")
ax.set_title("Loss over 3 epochs")
ax.legend(loc="lower left", fontsize=9.5)
finish(fig, ax, "loss.png")

# ----------------------------------------------------------------------------- 4) Exact Match per epoch
tags = ["base", "epoch1", "epoch2", "epoch3"]
names = ["Base model\n(no LoRA)", "After epoch 1", "After epoch 2", "After epoch 3"]
em = [evals[t]["exact_match"] * 100 for t in tags]
fig, ax = plt.subplots(figsize=(10, 5.2))
bars = ax.bar(range(len(tags)), em, width=0.5, color=C[0])
for b, t in zip(bars, tags):
    ax.annotate(f"{evals[t]['exact_match'] * 100:.1f}%\n({evals[t]['em_correct']}/{evals[t]['n']})",
                (b.get_x() + b.get_width() / 2, b.get_height()), xytext=(0, 4), textcoords="offset points",
                ha="center", va="bottom", fontsize=11, color=INK, fontweight="bold")
ax.set_xticks(range(len(tags)))
ax.set_xticklabels(names)
ax.set_ylim(0, 100)
ax.set_ylabel("Exact Match on the test set (%)")
ax.set_title(f"Exact Match after each epoch — {em[0]:.1f}% before training, {em[-1]:.1f}% after 3 epochs")
finish(fig, ax, "exact_match.png", SUB + " · text-to-SQL, 200 test samples, strict string match")

# ----------------------------------------------------------------------------- report.md
h = metrics["headline"]
L = ["# Lab 4 · Data Parallelism · RTX 3090 x 4", "",
     "| batch ต่อ GPU ใหญ่สุด | ตัวอย่างต่อวินาที | Exact Match (หลัง Epoch 3) | เงินต่อ 1,000 ตัวอย่าง (ราคาเครื่องที่เช่า) | เงินต่อ 1,000 ตัวอย่าง (ราคาตลาดถูกสุด) |",
     "|---|---|---|---|---|",
     f"| {h['max_batch_per_gpu']} (รวม {h['max_batch_per_gpu'] * NGPU}) | {sps:.1f} | {h['exact_match_final'] * 100:.1f}% | "
     f"${h['usd_per_1000_samples_rented']:.5f} (${prices['rented_machine']:.3f}/ชม.) | "
     + (f"${h['usd_per_1000_samples_market_cheapest']:.5f} (${prices['market_cheapest_on_demand_any']:.3f}/ชม.) |"
        if h["usd_per_1000_samples_market_cheapest"] else "– |"), "",
     "## ราคา", "", "| ราคา | $/ชม. | $ ต่อ 1,000 ตัวอย่าง | $ ต่อการเทรน 3 Epoch |", "|---|---|---|---|"]
L += [f"| {k} | {v['usd_per_hour']:.4f} | {v['usd_per_1000_samples']:.5f} | {v['usd_for_3_epochs_12000_samples']:.4f} |" for k, v in cost.items()]
if bill:
    L += ["", "## ค่าใช้จ่ายจริง", "",
          f"- อายุเครื่อง: {bill['age_min']:.1f} นาที ({bill['age_hours']:.3f} ชม.) ที่ ${bill['usd_per_hour']:.3f}/ชม.",
          f"- ยอดที่ถูกคิด (เครื่อง {bill['instance_id']}): ${bill.get('charged_usd_this_instance', float('nan')):.3f}",
          f"- ยอดรวมทุกเครื่องที่ใช้ป้าย {bill['label']}: ${bill.get('charged_usd_all_instances_with_label', float('nan')):.3f}",
          f"- ลบเครื่องแล้วและตรวจว่าไม่เหลือ: {bill['destroyed_and_verified_gone']}"]
L += ["", "## กราฟ", ""] + [f"![{n}](images/{n})" for n in ["vram_vs_batch.png", "gpu_util.png", "loss.png", "exact_match.png"]]
open(f"{ROOT}/report.md", "w").write("\n".join(L) + "\n")

print(json.dumps({"headline": h, "cost": cost, "actual_bill": bill and {k: v for k, v in bill.items() if k != "charge_rows"}},
                 indent=1, ensure_ascii=False))
