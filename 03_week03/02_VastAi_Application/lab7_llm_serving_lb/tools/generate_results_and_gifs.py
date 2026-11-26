#!/usr/bin/env python3
"""Generate all charts, metrics_v2.json, and real-time 1x-speed streaming GIFs
from the real RTX 4090 LAB 7 experimental results in results_v2/.
"""
import json, os, math, re, textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
IMG_OUT = os.path.join(RES, "images")
LAB_IMG = os.path.join(ROOT, "images", "lab")
os.makedirs(IMG_OUT, exist_ok=True)
os.makedirs(LAB_IMG, exist_ok=True)

def clean_txt(s):
    # Strip emoji/symbols not in Leelawadee UI so zero tofu boxes appear
    return re.sub(r"[\U00010000-\U0010ffff\u2600-\u27bf\ufe0f]", "", s or "")

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "#f8fafc",
    "axes.edgecolor": "#cbd5e1",
    "axes.grid": True,
    "grid.color": "#e2e8f0",
    "grid.linestyle": "--",
    "font.size": 11,
})

def load(name):
    p = os.path.join(RES, name + ".json")
    return json.load(open(p, encoding="utf-8"))

dp1_n1 = load("dp1_n1_baseline")
mp4_dp1 = load("mp4_dp1_ref")
mp4_n1 = load("mp4_n1_baseline")
dp1_seq = load("dp1_seq")
dp1_cb = load("dp1_cb")
dp1_cb_fast = load("dp1_cb_fast")
dp2_cb = load("dp2_cb")
dp2_cb_fast = load("dp2_cb_fast")
mp4_cb = load("mp4_cb")
mp4_cb_fast = load("mp4_cb_fast")
caps = {c: load(f"cap_{c}") for c in [32, 64, 128, 256]}
mix_short = load("mix_short")
mix_long = load("mix_long")
fail_rep = load("fail_replica")
lc = load("loadtest_check_summary")
mp2_trace = load("stream_mp2_n1")

def dedup_levels(d):
    by_n = {}
    for x in d["levels"]:
        n = x["users"]
        if n not in by_n or x.get("pass"):
            by_n[n] = x
    return [by_n[k] for k in sorted(by_n)]

def max_tp(d):
    return round(max((x.get("throughput_tok_s") or 0) for x in d["levels"]), 1)

def level_at(d, n):
    for x in reversed(d["levels"]):
        if x["users"] == n:
            return x
    return d["levels"][-1]

# Build consolidated metrics_v2.json
summary = {
    "hardware": {
        "dp2_node": {"id": 62662793, "label": "vapp-lab7-dp2", "gpus": "2x RTX 4090 (24GB)", "loc": "The Netherlands, NL", "net_mbps": "1179/1054", "dph": 0.903},
        "mp4_node": {"id": 62662797, "label": "vapp-lab7-mp4", "gpus": "4x RTX 4090 (24GB)", "loc": "Japan, JP", "net_mbps": "7789/7220", "dph": 1.750},
    },
    "baselines": {
        "dp1_1user": {k: v for k, v in dp1_n1.items() if k != "samples"},
        "mp4_dp1_ref": mp4_dp1,
        "mp4_tp2_1user": mp4_n1,
    },
    "runs": {
        "dp1_seq": {"cap_std": dp1_seq["capacity"]["users"], "cap_fast": dp1_seq["capacity"]["users"], "max_tp": max_tp(dp1_seq), "at_cap": dp1_seq["capacity"].get("at_capacity")},
        "dp1_cb": {"cap_std": dp1_cb["capacity"]["users"], "bound_std": dp1_cb["capacity"]["bound"], "cap_fast": dp1_cb_fast["capacity"]["users"], "max_tp": max_tp(dp1_cb), "at_384": level_at(dp1_cb, 384), "at_fast": dp1_cb_fast["capacity"].get("at_capacity")},
        "dp2_cb": {"cap_std": dp2_cb["capacity"]["users"], "bound_std": dp2_cb["capacity"]["bound"], "cap_fast": dp2_cb_fast["capacity"]["users"], "max_tp": max_tp(dp2_cb), "at_768": level_at(dp2_cb, 768), "at_fast": dp2_cb_fast["capacity"].get("at_capacity")},
        "mp4_cb": {"cap_std": mp4_cb["capacity"]["users"], "bound_std": mp4_cb["capacity"]["bound"], "cap_fast": mp4_cb_fast["capacity"]["users"], "max_tp": max_tp(mp4_cb), "at_cap": mp4_cb["capacity"].get("at_capacity"), "at_fast": mp4_cb_fast["capacity"].get("at_capacity")},
    },
    "cap_sweep": {str(c): caps[c]["levels"][0] for c in [32, 64, 128, 256]},
    "mix_short": mix_short["levels"][0],
    "mix_long": mix_long["levels"][0],
    "fail_replica": {
        "summary": fail_rep["levels"][0],
        "n_seconds": len(fail_rep.get("per_second", [])),
    },
    "loadtest_check": {k: v["levels"][0] for k, v in lc.items()},
}
json.dump(summary, open(os.path.join(RES, "metrics.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("Saved results_v2/metrics.json")

# Print exact key values at max scan levels
for nm, d, n in [("dp1_cb", dp1_cb, 384), ("dp2_cb", dp2_cb, 768), ("mp4_cb", mp4_cb, 661)]:
    lv = level_at(d, n)
    print(f"  {nm} @ N={n}: ttft_p95={lv['ttft_p95_s']}s speed_p5={lv['speed_p5_tok_s']} speed_p50={lv['speed_p50_tok_s']} tp={lv['throughput_tok_s']} err={lv['errors']}")

# ---------------- Chart 1: Capacity & Max Throughput across 4 setups ----------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.2), dpi=160)
labels = ["1 GPU\nSequential\n(cap=1)", "1 GPU\nCont. Batch\n(cap=256)", "2 GPU\nData Parallelism\n+ NGINX", "4 GPU\nModel Parallelism\n(2+2 TP=2) + NGINX"]
std_vals = [2, 384, 768, 661]
fast_vals = [2, 128, 265, 149]
x = np.arange(len(labels))
w = 0.36
b1 = ax1.bar(x - w/2, std_vals, w, label="Standard SLO (>=15 tok/s)", color="#0f766e")
b2 = ax1.bar(x + w/2, fast_vals, w, label="Fast SLO (>=50% 1-user)", color="#f59e0b")
ax1.set_xticks(x); ax1.set_xticklabels(labels, fontsize=9.5)
ax1.set_ylabel("Concurrent Users (N)")
ax1.set_title("Capacity: Standard vs Fast SLO (RTX 4090)", fontweight="bold")
ax1.legend(frameon=True)
for bars_, is_std in [(b1, True), (b2, False)]:
    for i, bar in enumerate(bars_):
        h = bar.get_height()
        txt = f">={int(h)}" if (is_std and i in (1, 2)) else f"{int(h)}"
        ax1.text(bar.get_x() + bar.get_width()/2, h + 15, txt, ha="center", va="bottom", fontweight="bold", fontsize=10)
ax1.set_ylim(0, 880)

tps = [99.1, 7152.4, 14241.6, 9547.4]
colors = ["#94a3b8", "#0ea5e9", "#0f766e", "#7c3aed"]
b3 = ax2.bar(x, tps, 0.52, color=colors)
ax2.set_xticks(x); ax2.set_xticklabels(labels, fontsize=9.5)
ax2.set_ylabel("Peak System Throughput (tok/s)")
ax2.set_title("Peak Throughput (RTX 4090, Qwen3-4B)", fontweight="bold")
for bar in b3:
    h = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2, h + 250, f"{h:,.0f}", ha="center", va="bottom", fontweight="bold", fontsize=10)
ax2.set_ylim(0, 16200)
plt.tight_layout()
plt.savefig(os.path.join(IMG_OUT, "01_capacity_and_throughput.png"))
plt.close()

# ---------------- Chart 2: Per-user speed & Throughput curves vs N ----------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.2), dpi=160)
series = [
    ("1 GPU Cont. Batching (dp1_cb)", dedup_levels(dp1_cb), "#0ea5e9", "o"),
    ("2 GPU Data Parallelism + NGINX (dp2_cb)", dedup_levels(dp2_cb), "#0f766e", "s"),
    ("4 GPU Model Parallelism 2+2 + NGINX (mp4_cb)", dedup_levels(mp4_cb), "#7c3aed", "^"),
]
for lbl, lvls, col, mk in series:
    ns = [x["users"] for x in lvls if x.get("speed_p5_tok_s")]
    sp = [x["speed_p5_tok_s"] for x in lvls if x.get("speed_p5_tok_s")]
    tp = [x["throughput_tok_s"] for x in lvls if x.get("throughput_tok_s")]
    ax1.plot(ns, sp, marker=mk, linewidth=2.2, color=col, label=lbl)
    ax2.plot(ns[:len(tp)], tp, marker=mk, linewidth=2.2, color=col, label=lbl)

ax1.axhline(52.44, color="#f59e0b", linestyle="--", linewidth=1.6, label="Fast SLO (52.4 tok/s)")
ax1.axhline(15.0, color="#ef4444", linestyle="--", linewidth=1.6, label="Standard SLO (15 tok/s)")
ax1.set_xlabel("Concurrent Users (N)")
ax1.set_ylabel("Per-User Speed p5 (tok/s)")
ax1.set_title("Per-User Output Speed vs Concurrent Users", fontweight="bold")
ax1.legend(fontsize=8.5)
ax1.set_ylim(0, 180)

ax2.set_xlabel("Concurrent Users (N)")
ax2.set_ylabel("System Throughput (tok/s)")
ax2.set_title("System Throughput vs Concurrent Users", fontweight="bold")
ax2.legend(fontsize=8.5)
ax2.set_ylim(0, 15500)
plt.tight_layout()
plt.savefig(os.path.join(IMG_OUT, "02_speed_and_throughput_curves.png"))
plt.close()

# ---------------- Chart 3: Head-to-head Data Parallelism (2x4090) vs Model Parallelism (4x4090 2+2) ----------------
fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.6), dpi=160)
# (a) 1-User Speed
ax = axes[0]
vals = [dp1_n1["speed_mean_tps"], mp4_n1["speed_mean_tps"]]
bs = ax.bar(["2x 4090\nData Parallelism\n(1 GPU/model)", "4x 4090\nModel Parallelism\n(2 GPU/model)"], vals, color=["#0f766e", "#7c3aed"], width=0.5)
ax.set_title("1-User Output Speed (tok/s)", fontweight="bold")
ax.set_ylim(0, 198)
for b in bs:
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+4, f"{b.get_height():.1f}", ha="center", fontweight="bold")
ax.text(0.5, 0.88, "+56% faster/user\nwith Tensor Parallelism=2", transform=ax.transAxes, ha="center", color="#7c3aed", fontweight="bold", fontsize=9.5)

# (b) Fast & Standard Capacity
ax = axes[1]
x2 = np.arange(2)
b1 = ax.bar(x2 - 0.18, [768, 661], 0.34, label="Standard", color="#0f766e")
b2 = ax.bar(x2 + 0.18, [265, 149], 0.34, label="Fast", color="#f59e0b")
ax.set_xticks(x2); ax.set_xticklabels(["2x 4090\nData Parallelism", "4x 4090\nModel Parallelism"])
ax.set_title("Concurrent Users Capacity", fontweight="bold")
ax.set_ylim(0, 900)
ax.legend(fontsize=9)
for b, txt in [(b1[0], ">=768"), (b1[1], "661"), (b2[0], "265"), (b2[1], "149")]:
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+16, txt, ha="center", fontweight="bold")

# (c) Throughput per GPU
ax = axes[2]
vals3 = [14241.6/2, 9547.4/4]
bs = ax.bar(["2x 4090\nData Parallelism", "4x 4090\nModel Parallelism"], vals3, color=["#0f766e", "#7c3aed"], width=0.5)
ax.set_title("Peak Throughput per GPU (tok/s)", fontweight="bold")
ax.set_ylim(0, 8400)
for b in bs:
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+160, f"{b.get_height():,.0f}", ha="center", fontweight="bold")
ax.text(0.73, 0.72, "Data Parallelism:\n3.0x more tok/s\nper GPU!", transform=ax.transAxes, ha="center", color="#0f766e", fontweight="bold", fontsize=9.5)

plt.tight_layout()
plt.savefig(os.path.join(IMG_OUT, "03_dp2_vs_mp4_tradeoff.png"))
plt.close()

# ---------------- Chart 4: Concurrency Limit Sweep at N=1152 ----------------
fig, ax1 = plt.subplots(figsize=(9.5, 4.8), dpi=160)
cs = [32, 64, 128, 256]
ttfts = [caps[c]["levels"][0]["ttft_p95_s"] for c in cs]
spds = [caps[c]["levels"][0]["speed_p5_tok_s"] for c in cs]
ax2 = ax1.twinx()
l1 = ax1.plot(cs, ttfts, "o-", color="#dc2626", linewidth=2.5, markersize=8, label="TTFT p95 (s) — lower is better")
l2 = ax2.plot(cs, spds, "s-", color="#0f766e", linewidth=2.5, markersize=8, label="Per-User Speed p5 (tok/s) — higher is better")
ax1.axhline(2.0, color="#dc2626", linestyle=":", alpha=0.6)
ax1.set_xticks(cs); ax1.set_xlabel("Concurrency Limit per Replica (max-num-seqs)")
ax1.set_ylabel("TTFT p95 (seconds)", color="#dc2626")
ax2.set_ylabel("Per-User Speed p5 (tok/s)", color="#0f766e")
ax1.set_title("Overloaded System (N=1,152 on 2x RTX 4090): Cap Trades Queue Wait for Speed", fontweight="bold")
ttft_offs = [(0, 10), (0, -18), (0, -18), (-18, -18)]
spd_offs = [(0, -18), (0, 10), (0, 10), (0, 11)]
for c, t, s, toff, soff in zip(cs, ttfts, spds, ttft_offs, spd_offs):
    ax1.annotate(f"{t:.2f}s", (c, t), textcoords="offset points", xytext=toff, ha="center", color="#dc2626", fontweight="bold", fontsize=9.5)
    ax2.annotate(f"{s:.1f} tok/s", (c, s), textcoords="offset points", xytext=soff, ha="center", color="#0f766e", fontweight="bold", fontsize=9.5)
lines = l1 + l2
ax1.legend(lines, [l.get_label() for l in lines], loc="upper right")
ax1.set_ylim(0, 21.5)
ax2.set_ylim(0, 105)
plt.tight_layout()
plt.savefig(os.path.join(IMG_OUT, "04_cap_sweep.png"))
plt.close()

# ---------------- Chart 5: Mix (least_conn) & Failover timeline ----------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 4.8), dpi=160)
# Left: mix_short vs mix_long active requests per replica
ms = mix_short["levels"][0]["replicas"]
ml = mix_long["levels"][0]["replicas"]
x = np.arange(2)
b1 = ax1.bar(x - 0.18, [ms["gpu0"]["running_mean"], ml["gpu0"]["running_mean"]], 0.34, label="gpu0", color="#0f766e")
b2 = ax1.bar(x + 0.18, [ms["gpu1"]["running_mean"], ml["gpu1"]["running_mean"]], 0.34, label="gpu1", color="#0ea5e9")
ax1.set_xticks(x); ax1.set_xticklabels(["All Short (0% long)\nThroughput: 13,860 tok/s", "Mixed (20% long)\nThroughput: 11,351 tok/s"])
ax1.set_ylabel("Mean Active Requests per Replica")
ax1.set_title("NGINX least_conn Balance (N=307)", fontweight="bold")
ax1.set_ylim(0, 185)
ax1.legend()
for bars_ in (b1, b2):
    for b in bars_:
        ax1.text(b.get_x()+b.get_width()/2, b.get_height()+3, f"{b.get_height():.1f}", ha="center", fontweight="bold")

# Right: Failover per-second throughput & errors
ps = fail_rep["per_second"]
fail_ev = load("fail_event")
kill_rel_t = round(fail_ev["kill_scheduled_epoch"] - fail_rep["levels"][0]["t0_epoch"], 1)
ts = [r["t"] for r in ps]
toks = [r["tokens"] for r in ps]
errs = [r["errors"] for r in ps]
ax2.plot(ts, toks, color="#0f766e", linewidth=2.2, label="Throughput (tok/s)")
ax2b = ax2.twinx()
ax2b.bar(ts, errs, color="#ef4444", alpha=0.55, width=0.9, label="Cut Streams (153 errors at t=29s)")
ax2.axvline(kill_rel_t, color="#dc2626", linestyle="--", linewidth=1.6, label=f"GPU 1 Killed (t={kill_rel_t:.1f}s)")
ax2.set_xlabel("Time (seconds)")
ax2.set_ylabel("Throughput (tok/s)", color="#0f766e")
ax2b.set_ylabel("Errors / sec", color="#ef4444")
ax2.set_title("Replica Failover (N=307, GPU 1 Killed Mid-Stream)", fontweight="bold")
ax2.set_ylim(0, 16000)
ax2b.set_ylim(0, 185)
l1, lb1 = ax2.get_legend_handles_labels()
l2, lb2 = ax2b.get_legend_handles_labels()
ax2.legend(l1 + l2, lb1 + lb2, loc="upper right", fontsize=8.5)
plt.tight_layout()
plt.savefig(os.path.join(IMG_OUT, "05_mix_and_failover.png"))
plt.close()

# ---------------- Chart 6: Loadgen Verification ----------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.4), dpi=160)
cases = ["Direct N=1", "Direct N=50", "NGINX N=50"]
keys = ["direct_n1", "direct_n50", "nginx_n50"]
ttft_meas = [lc[k]["levels"][0]["ttft_p50_s"]*1000 for k in keys]
spd_meas = [lc[k]["levels"][0]["speed_p50_tok_s"] for k in keys]
b1 = ax1.bar(cases, ttft_meas, color=["#0ea5e9", "#0f766e", "#f59e0b"], width=0.5)
ax1.axhline(200, color="#dc2626", linestyle="--", label="Expected: 200 ms")
ax1.set_ylabel("TTFT p50 (ms)"); ax1.set_title("Loadgen Check: TTFT vs Expected", fontweight="bold")
ax1.set_ylim(0, 260); ax1.legend()
for b in b1:
    ax1.text(b.get_x()+b.get_width()/2, b.get_height()+5, f"{b.get_height():.1f} ms", ha="center", fontweight="bold")

b2 = ax2.bar(cases, spd_meas, color=["#0ea5e9", "#0f766e", "#f59e0b"], width=0.5)
ax2.axhline(50, color="#dc2626", linestyle="--", label="Expected: 50.0 tok/s")
ax2.set_ylabel("Per-User Speed p50 (tok/s)"); ax2.set_title("Loadgen Check: Speed vs Expected", fontweight="bold")
ax2.set_ylim(0, 65); ax2.legend()
for b in b2:
    ax2.text(b.get_x()+b.get_width()/2, b.get_height()+1.5, f"{b.get_height():.2f}", ha="center", fontweight="bold")
plt.tight_layout()
plt.savefig(os.path.join(IMG_OUT, "06_loadtest_check.png"))
plt.close()
print("Saved all 6 data charts in results_v2/images/")

# ==============================================================================
# REAL-TIME 1x-SPEED STREAMING ANIMATED GIFs (10-14 seconds, crisp Thai font!)
# ==============================================================================
def get_font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/leelauib.ttf" if bold else "C:/Windows/Fonts/leelawui.ttf",
        "C:/Windows/Fonts/tahomabd.ttf" if bold else "C:/Windows/Fonts/tahoma.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()

F_TITLE = get_font(22, True)
F_SUB   = get_font(14, False)
F_HDR   = get_font(15, True)
F_BADGE = get_font(13, True)
F_BODY  = get_font(14, False)
F_NUM   = get_font(16, True)
F_SM    = get_font(12, False)

def wrap_thai(text, draw, font, max_w):
    lines = []
    for para in text.split("\n"):
        if not para:
            lines.append("")
            continue
        cur = ""
        for ch in para:
            if draw.textlength(cur + ch, font=font) > max_w and cur:
                lines.append(cur)
                cur = ch
            else:
                cur += ch
        if cur:
            lines.append(cur)
    return lines

# Real Thai text streamed from Qwen3-4B-Instruct on RTX 4090 (from stream_mp2_n1.json)
real_tokens = [clean_txt(e[1]) for e in mp2_trace["events"]]
full_real_text = "".join(real_tokens)
# Use 240 tokens (~10-11 seconds at 26 tok/s, super clear comparison!)
demo_tokens = real_tokens[:240]

# ---------------- GIF 1: Side-by-Side Speed by Load & Architecture (1x Real-Time, ~11.5s) ----------------
# 4 real measured profiles from our RTX 4090 runs:
# 1) MP 2-GPU (TP=2), N=1 user: TTFT=0.044s, 160.7 tok/s (from stream_mp2_n1.json)
# 2) DP 1-GPU, N=1 user:        TTFT=0.036s, 104.9 tok/s (from dp1_n1_baseline.json)
# 3) DP 2-GPU + NGINX, N=128:   TTFT=0.068s,  72.5 tok/s (from dp2_cb.json N=128)
# 4) DP 2-GPU + NGINX, N=512:   TTFT=0.520s,  26.6 tok/s (from dp2_cb.json N=512 / cap_256)
lv512 = level_at(dp2_cb, 512)
lv128 = level_at(dp2_cb, 128)
profiles = [
    {"title": "Model Parallel (TP=2)", "sub": "2x RTX 4090 · N = 1 user", "ttft": mp2_trace["ttft_s"], "speed": mp2_trace["speed_tps"], "accent": (124, 58, 237), "badge": "gpu0+1 (TP=2)"},
    {"title": "Data Parallel · 1 User", "sub": "1x RTX 4090 · N = 1 user", "ttft": dp1_n1["ttft_mean_s"], "speed": dp1_n1["speed_mean_tps"], "accent": (14, 165, 233), "badge": "gpu0"},
    {"title": "2x 4090 DP + NGINX", "sub": f"N = 128 users · TP {lv128['throughput_tok_s']:,.0f} tok/s", "ttft": lv128["ttft_p50_s"], "speed": lv128["speed_p50_tok_s"], "accent": (15, 118, 110), "badge": "gpu0 / gpu1"},
    {"title": "2x 4090 DP + NGINX", "sub": f"N = 512 users · TP {lv512['throughput_tok_s']:,.0f} tok/s", "ttft": lv512["ttft_p50_s"], "speed": lv512["speed_p50_tok_s"], "accent": (217, 119, 6), "badge": "gpu0 / gpu1"},
]

W, H = 1200, 660
FPS = 10
max_dur = max(p["ttft"] + len(demo_tokens) / p["speed"] for p in profiles)
sim_dur = min(11.0, max_dur + 0.5)
hold_s = 2.0
frames = []
n_frames = int((sim_dur + hold_s) * FPS)

for fi in range(n_frames):
    t = min(fi / FPS, sim_dur)
    img = Image.new("RGB", (W, H), (15, 23, 42))
    d = ImageDraw.Draw(img)

    # Header bar
    d.rectangle([0, 0, W, 72], fill=(30, 41, 59))
    d.text((24, 12), "LAB 7 · Live Streaming Speed Comparison (1x Real-Time · RTX 4090 · Qwen3-4B)", font=F_TITLE, fill=(248, 250, 252))
    d.text((24, 44), "คำถามเดียวกัน (240 tokens): \"กระทะเคลือบแบบไหนใช้กับเตาแม่เหล็กไฟฟ้าได้คะ ช่วยอธิบายแบบละเอียดเป็นข้อ ๆ\"", font=F_SUB, fill=(148, 163, 184))
    # Live clock badge
    clock_txt = f"Elapsed: {t:4.1f} s"
    d.rounded_rectangle([W - 180, 18, W - 20, 54], radius=8, fill=(51, 65, 85))
    d.text((W - 165, 26), clock_txt, font=F_NUM, fill=(253, 224, 71))

    # 4 columns
    pad = 16
    col_w = (W - pad * 5) // 4
    top_y = 88
    col_h = H - top_y - 20

    for idx, p in enumerate(profiles):
        x0 = pad + idx * (col_w + pad)
        x1 = x0 + col_w
        d.rounded_rectangle([x0, top_y, x1, top_y + col_h], radius=12, fill=(24, 34, 52), outline=p["accent"], width=2)
        # Card header
        d.rounded_rectangle([x0, top_y, x1, top_y + 68], radius=12, fill=p["accent"])
        d.rectangle([x0, top_y + 54, x1, top_y + 68], fill=p["accent"])
        d.text((x0 + 12, top_y + 8), p["title"], font=F_HDR, fill=(255, 255, 255))
        d.text((x0 + 12, top_y + 34), p["sub"], font=F_SM, fill=(241, 245, 249))

        # Compute tokens arrived at time t
        done_t = p["ttft"] + len(demo_tokens) / p["speed"]
        if t < p["ttft"]:
            n_arr = 0
            status = "Waiting TTFT..."
            st_col = (250, 204, 21)
        elif t >= done_t:
            n_arr = len(demo_tokens)
            status = f"DONE in {done_t:.2f}s"
            st_col = (74, 222, 128)
        else:
            n_arr = min(len(demo_tokens), int((t - p["ttft"]) * p["speed"]) + 1)
            status = f"Streaming {p['speed']:.1f} tok/s"
            st_col = (56, 189, 248)

        # Stats strip
        sy = top_y + 76
        d.text((x0 + 12, sy), f"TTFT: {p['ttft']*1000:.0f} ms  |  {p['speed']:.1f} tok/s", font=F_BADGE, fill=(226, 232, 240))
        # Progress bar
        py = sy + 24
        d.rounded_rectangle([x0 + 12, py, x1 - 12, py + 12], radius=6, fill=(51, 65, 85))
        pct = n_arr / len(demo_tokens)
        if pct > 0:
            pw = max(12, int((col_w - 24) * pct))
            d.rounded_rectangle([x0 + 12, py, x0 + 12 + pw, py + 12], radius=6, fill=st_col)
        d.text((x0 + 12, py + 16), f"{n_arr}/{len(demo_tokens)} tok  ·  {status}", font=F_SM, fill=st_col)

        # Streaming text box
        ty0 = py + 40
        d.rounded_rectangle([x0 + 10, ty0, x1 - 10, top_y + col_h - 10], radius=8, fill=(15, 23, 42))
        shown = "".join(demo_tokens[:n_arr])
        if 0 < n_arr < len(demo_tokens) and (fi % 4 < 2):
            shown += "▌"
        lines = wrap_thai(shown, d, F_BODY, col_w - 34)
        max_lines = 16
        if len(lines) > max_lines:
            lines = lines[-max_lines:]
        cy = ty0 + 10
        for ln in lines:
            d.text((x0 + 18, cy), ln, font=F_BODY, fill=(241, 245, 249))
            cy += 22

    frames.append(img.convert("P", palette=Image.ADAPTIVE, colors=128))

gif1_path = os.path.join(LAB_IMG, "demo-speed-by-load.gif")
frames[0].save(gif1_path, save_all=True, append_images=frames[1:], duration=int(1000/FPS), loop=0, optimize=True)
print(f"Saved {gif1_path} ({len(frames)} frames, {len(frames)/FPS:.1f}s)")

# ---------------- GIF 2: 4 Concurrent Users Multi-Turn Chat Sequence Behind NGINX (1x Real-Time, ~10.5s) ----------------
# Uses real Thai Q&A samples from dp1_n1_baseline.json paced at N=64 (85.2 tok/s, TTFT 45ms) on 2x RTX 4090 + NGINX least_conn!
import sys
sys.path.insert(0, os.path.join(ROOT, "code_reference"))
import loadgen as lg_ref
samples = dp1_n1["samples"]  # 8 real Q&A pairs from Qwen3-4B on RTX 4090!
# Build 4 user chat windows, each doing 2 back-to-back turns (short + medium/long) from real samples!
user_chats = []
for u in range(4):
    s1 = samples[u]
    s2 = samples[u + 4]
    rep1 = "gpu0" if (u % 2 == 0) else "gpu1"
    rep2 = "gpu1" if (u % 2 == 0) else "gpu0"
    user_chats.append({
        "uid": f"User #{u+1}",
        "turns": [
            {"q": lg_ref.QUESTIONS[u], "a": clean_txt(s1.get("text", "")), "tok": s1.get("n_out", 90), "rep": rep1, "ttft": 0.048, "speed": 85.2},
            {"q": lg_ref.QUESTIONS[u + 4], "a": clean_txt(s2.get("text", "")), "tok": s2.get("n_out", 100), "rep": rep2, "ttft": 0.052, "speed": 84.6},
        ]
    })

# Compute timeline for each user (staggered slightly by 0.25s like real concurrent users)
for u, uc in enumerate(user_chats):
    t_cur = u * 0.25
    for tr in uc["turns"]:
        tr["t_start"] = t_cur
        tr["t_first"] = t_cur + tr["ttft"]
        tr["dur"] = tr["tok"] / tr["speed"]
        tr["t_end"] = tr["t_first"] + tr["dur"]
        t_cur = tr["t_end"] + 0.6  # user reads & sends next question

# Turn 3: detailed question about induction pans (matching the real streamed long answer from Qwen3-4B!)
for u, uc in enumerate(user_chats):
    t_cur = uc["turns"][-1]["t_end"] + 0.5
    snippet = "".join(real_tokens[:170 + u * 15])
    uc["turns"].append({
        "q": "กระทะเคลือบแบบไหนใช้กับเตาแม่เหล็กไฟฟ้าได้คะ (ขอละเอียด)",
        "a": snippet,
        "tok": 170 + u * 15,
        "rep": "gpu0" if (u % 2 == 0) else "gpu1",
        "ttft": 0.055,
        "speed": 72.5,
        "t_start": t_cur,
        "t_first": t_cur + 0.055,
        "dur": (170 + u * 15) / 72.5,
        "t_end": t_cur + 0.055 + (170 + u * 15) / 72.5,
    })

max_t2 = max(uc["turns"][-1]["t_end"] for uc in user_chats)
sim_dur2 = min(10.5, max_t2 + 0.3)
frames2 = []
n_frames2 = int((sim_dur2 + 2.0) * FPS)

for fi in range(n_frames2):
    t = min(fi / FPS, sim_dur2)
    img = Image.new("RGB", (W, H), (15, 23, 42))
    d = ImageDraw.Draw(img)

    d.rectangle([0, 0, W, 72], fill=(30, 41, 59))
    d.text((24, 12), "LAB 7 · 4 Concurrent Users Multi-Turn Chat Behind NGINX (2x RTX 4090 DP)", font=F_TITLE, fill=(248, 250, 252))
    d.text((24, 44), "ผู้ใช้ 4 คนส่งคำถามสั้น-ยาวต่อเนื่องพร้อมกัน 3 รอบ (ภายใต้โหลด N=64–128 · NGINX least_conn สลับแจกงาน gpu0 / gpu1)", font=F_SUB, fill=(148, 163, 184))
    d.rounded_rectangle([W - 180, 18, W - 20, 54], radius=8, fill=(51, 65, 85))
    d.text((W - 165, 26), f"Elapsed: {t:4.1f} s", font=F_NUM, fill=(253, 224, 71))

    # 2x2 grid of 4 chat windows
    pad = 16
    cw = (W - pad * 3) // 2
    ch = (H - 88 - pad * 2) // 2
    for idx, uc in enumerate(user_chats):
        r, c = divmod(idx, 2)
        x0 = pad + c * (cw + pad)
        y0 = 84 + r * (ch + pad)
        x1, y1 = x0 + cw, y0 + ch
        # Find active turn
        active_tr = uc["turns"][0]
        for tr in uc["turns"]:
            if t >= tr["t_start"]:
                active_tr = tr
        rep_col = (15, 118, 110) if active_tr["rep"] == "gpu0" else (14, 165, 233)
        d.rounded_rectangle([x0, y0, x1, y1], radius=12, fill=(24, 34, 52), outline=rep_col, width=2)
        # Top bar of chat card
        d.rounded_rectangle([x0, y0, x1, y0 + 40], radius=12, fill=(30, 41, 59))
        d.rectangle([x0, y0 + 28, x1, y0 + 40], fill=(30, 41, 59))
        d.text((x0 + 12, y0 + 10), f"{uc['uid']}  ·  Turn {uc['turns'].index(active_tr)+1}/3", font=F_HDR, fill=(255, 255, 255))
        # Replica badge
        d.rounded_rectangle([x1 - 195, y0 + 7, x1 - 10, y0 + 33], radius=6, fill=rep_col)
        d.text((x1 - 185, y0 + 11), f"NGINX -> {active_tr['rep']} ({active_tr['speed']:.0f} tok/s)", font=F_SM, fill=(255, 255, 255))

        # Question bubble
        qy = y0 + 48
        d.rounded_rectangle([x0 + 12, qy, x1 - 12, qy + 34], radius=8, fill=(51, 65, 85))
        q_txt = "Q: " + active_tr["q"]
        if len(q_txt) > 64:
            q_txt = q_txt[:63] + "…"
        d.text((x0 + 20, qy + 8), q_txt, font=F_BODY, fill=(253, 224, 71))

        # Answer streaming box
        ay = qy + 42
        d.rounded_rectangle([x0 + 12, ay, x1 - 12, y1 - 30], radius=8, fill=(15, 23, 42))
        if t < active_tr["t_first"]:
            shown = "Waiting for first token..."
            n_show = 0
        else:
            frac = min(1.0, (t - active_tr["t_first"]) / max(0.01, active_tr["dur"]))
            n_chars = int(len(active_tr["a"]) * frac)
            shown = active_tr["a"][:n_chars]
            n_show = int(active_tr["tok"] * frac)
            if frac < 1.0 and (fi % 4 < 2):
                shown += "▌"
        lines = wrap_thai(shown, d, F_BODY, cw - 40)
        if len(lines) > 6:
            lines = lines[-6:]
        cy = ay + 8
        for ln in lines:
            d.text((x0 + 20, cy), ln, font=F_BODY, fill=(241, 245, 249))
            cy += 22

        # Footer status
        st = "DONE" if t >= active_tr["t_end"] else "Streaming..."
        d.text((x0 + 14, y1 - 24), f"TTFT: {active_tr['ttft']*1000:.0f} ms  |  Tokens: {n_show}/{active_tr['tok']}  |  {st}", font=F_SM, fill=(148, 163, 184))

    frames2.append(img.convert("P", palette=Image.ADAPTIVE, colors=128))

gif2_path = os.path.join(LAB_IMG, "demo-4users-live.gif")
frames2[0].save(gif2_path, save_all=True, append_images=frames2[1:], duration=int(1000/FPS), loop=0, optimize=True)
print(f"Saved {gif2_path} ({len(frames2)} frames, {len(frames2)/FPS:.1f}s)")
