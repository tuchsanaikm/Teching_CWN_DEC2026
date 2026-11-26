#!/usr/bin/env python3
"""results/loadtest_check.json -> results/loadtest_check.png : test A, measured vs calculated.
Needs matplotlib (control machine: pip install --target /workspace/l7r/.pydeps matplotlib)."""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", ".pydeps"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

res = json.load(open(os.path.join(HERE, "..", "results", "loadtest_check.json")))
runs = res["tests"]["A"]["runs"]
INK, MUTED, GRID, CALC, MEAS = "#1b1f24", "#5b6470", "#e3e7ec", "#aab3bf", "#2f6fb7"
panels = [("Time to first token (s)", "ttft_s", "ttft_p50_s", "ttft", "%.3f", False),
          ("Speed per user (tokens/s)", "speed_tok_s", "speed_p50_tok_s", "speed", "%.1f", False),
          ("Throughput, all users (tokens/s)", "throughput_tok_s", "throughput_tok_s", "throughput", "%.0f", True)]
plt.rcParams.update({"font.size": 10, "text.color": INK, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": MUTED})
fig, axes = plt.subplots(1, 3, figsize=(13, 4.6))
x = range(len(runs))
w = 0.36
for ax, (title, ek, mk, dk, fmt, logy) in zip(axes, panels):
    exp = [r["expected"][ek] for r in runs]
    mea = [r[mk] for r in runs]
    b1 = ax.bar([i - w / 2 - 0.01 for i in x], exp, w, color=CALC, label="calculated")
    b2 = ax.bar([i + w / 2 + 0.01 for i in x], mea, w, color=MEAS, label="measured")
    if logy:
        ax.set_yscale("log")
        ax.set_ylim(10, max(exp + mea) * 6)
    else:
        ax.set_ylim(0, max(exp + mea) * 1.28)
    for i, (e, m, r) in enumerate(zip(exp, mea, runs)):
        ax.annotate(fmt % e, (i - w / 2 - 0.01, e), xytext=(0, 3), textcoords="offset points", ha="center", color=MUTED, fontsize=9)
        ax.annotate(fmt % m, (i + w / 2 + 0.01, m), xytext=(0, 3), textcoords="offset points", ha="center", color=INK, fontsize=9)
        ax.annotate("%+.1f %%" % r["diff_pct"][dk], (i, max(e, m)), xytext=(0, 17), textcoords="offset points",
                    ha="center", color=INK, fontsize=9, fontweight="bold")
    ax.set_xticks(list(x))
    ax.set_xticklabels(["N = %d" % r["users"] for r in runs])
    ax.set_title(title, loc="left", fontsize=11, fontweight="bold")
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(length=0)
axes[2].set_ylabel("log scale", color=MUTED, fontsize=9)
axes[0].legend(frameon=False, loc="upper left", bbox_to_anchor=(0, -0.08), ncol=2)
cfg = runs[0]["fake_settings"]
verdict = "PASS" if res["tests"]["A"]["pass"] else "FAIL"
fig.suptitle("Load generator check, test A: measured vs calculated against the fake LLM server  (%s, limit 10 %%)" % verdict,
             x=0.01, ha="left", fontsize=13, fontweight="bold")
fig.text(0.01, 0.905, "Fake server: first token after %g ms, then one token every %g ms, %d tokens per answer (2.2 s per answer). "
         "N = users at the same time. Bold = measured minus calculated." % (cfg["ttft_ms"], cfg["interval_ms"], cfg["tokens"]),
         color=MUTED, fontsize=9.5)
fig.tight_layout(rect=(0, 0.02, 1, 0.89))
out = os.path.join(HERE, "..", "results", "loadtest_check.png")
fig.savefig(out, dpi=160, facecolor="white")
print("saved", os.path.normpath(out))
