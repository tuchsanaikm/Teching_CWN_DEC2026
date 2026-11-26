#!/usr/bin/env python3
"""Draw results/loadtest_check.png from results/loadtest_check.json:
test A - throughput measured by the load generator against the calculated value N / 0.05 s.

usage: python plot_loadtest_check.py [results_dir]
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RES = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
doc = json.load(open(os.path.join(RES, "loadtest_check.json")))
a = doc["tests"]["A"]
rows = a["rows"]
lim = doc["limits"]["A_pct"]
delay_s = doc["method"]["fake_delay_ms"] / 1000.0

INK, MUTED, GRID, SURFACE, BLUE, GRAY = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb", "#2a78d6", "#8a8984"
ns = [r["users"] for r in rows]
exp = [r["expected_throughput_rps"] for r in rows]
got = [r["throughput_rps"] for r in rows]

fig, ax = plt.subplots(figsize=(9, 5.6), dpi=150)
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)
xs = [ns[0] * 0.7, ns[-1] * 1.45]
line = [x / delay_s for x in xs]
ax.fill_between(xs, [v * (1 - lim / 100) for v in line], [v * (1 + lim / 100) for v in line],
                color=GRAY, alpha=0.18, lw=0, label=f"Pass band (calculated ± {lim:g} %)")
ax.plot(xs, line, color=GRAY, lw=2, label=f"Calculated: N / {delay_s:g} s")
ax.plot(ns, got, "o", color=BLUE, ms=9, mec=SURFACE, mew=2, label="Measured by loadgen.py", zorder=3)
for r in rows:
    ax.annotate(f"{r['throughput_rps']:,.1f} req/s\ncalculated {r['expected_throughput_rps']:,.0f}  "
                f"({r['throughput_diff_pct']:+.1f} %)",
                (r["users"], r["throughput_rps"]), xytext=(12, -8), textcoords="offset points",
                ha="left", va="top", fontsize=9, color=INK)
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlim(*xs)
ax.set_xticks(ns)
ax.set_xticklabels([str(n) for n in ns])
ax.minorticks_off()
yt = [10, 20, 50, 100, 200, 500, 1000, 2000, 5000]
ax.set_yticks(yt)
ax.set_yticklabels([f"{v:,}" for v in yt])
ax.set_ylim(line[0] * 0.5, line[1] * 1.3)
ax.grid(True, color=GRID, lw=0.8)
ax.set_axisbelow(True)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
for s in ("left", "bottom"):
    ax.spines[s].set_color(GRID)
ax.tick_params(colors=MUTED, length=0)
ax.set_xlabel("Concurrent users N (log scale)", color=MUTED)
ax.set_ylabel("Throughput, requests/s (log scale)", color=MUTED)
ax.set_title(f"Load generator check, test A: measured vs calculated throughput  [{'PASS' if a['pass'] else 'FAIL'}]",
             color=INK, fontsize=12, loc="left", pad=22)
ax.text(0, 1.02, f"Fake server waits {delay_s * 1000:g} ms per request, shot directly; "
                 f"{doc['method']['level_seconds']:g} s per level, first {doc['method']['warmup_s']:g} s not counted",
        transform=ax.transAxes, fontsize=9, color=MUTED)
ax.legend(loc="upper left", frameon=False, fontsize=9, labelcolor=INK)
fig.tight_layout()
out = os.path.join(RES, "loadtest_check.png")
fig.savefig(out, facecolor=SURFACE)
print("saved", out)
