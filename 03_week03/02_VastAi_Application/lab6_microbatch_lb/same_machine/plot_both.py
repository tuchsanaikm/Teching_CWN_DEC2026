#!/usr/bin/env python3
"""Combine the two machines of step 10.2 (LAB 6.1) into one summary file and two charts.

  python plot_both.py          (run inside 1_nginx/same_machine)

Reads run_a/results/<name>.json and run_b/results/<name>.json (written by loadgen.py) and writes
  summary.json                  capacity, p95, request share per machine, method and case
  ../image/result-3methods.png     capacity of the 3 methods, both cases, both machines
  ../image/result-p95-n64.png     p95 at N = 64 when GPU 1 is 3x slower
"""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
METHODS = [("rr", "Round Robin"), ("lc", "Least Connections"), ("p2c", "Power of Two Choices")]
CASES = [("equal", "Equal GPUs"), ("slow", "GPU 1 made 3x slower")]
RUNS = [("a", "Machine A"), ("b", "Machine B")]
COL = {"a": "#2f6fb7", "b": "#e08a1e"}


def load(run, name):
    d = json.load(open(os.path.join(HERE, "run_" + run, "results", name + ".json"), encoding="utf-8"))
    cap = d["capacity"]
    at = [x for x in d["levels"] if x["users"] == cap and x["pass"]][-1]
    per_gpu = {}
    for s in at.get("servers") or []:
        if isinstance(s, dict):
            g = str(s.get("gpu", s.get("name", "")))
            per_gpu[g] = per_gpu.get(g, 0) + (s.get("requests") or s.get("count") or 0)
    n64 = [x["latency_ms"]["p95"] for x in d["levels"] if x["users"] == 64]
    return {"capacity": cap, "first_fail": d.get("first_fail_users"), "p95_at_capacity": round(at["latency_ms"]["p95"], 1),
            "throughput_at_capacity": round(at["throughput_rps"], 1), "max_throughput": round(d["max_throughput_rps"], 1),
            "p95_at_n64_first_try": round(n64[0], 1) if n64 else None, "levels_measured": len(d["levels"])}


S = {r: {c: {m: load(r, m + "_" + c) for m, _ in METHODS} for c, _ in CASES} for r, _ in RUNS}
json.dump(S, open(os.path.join(HERE, "summary.json"), "w", encoding="utf-8"), indent=1)
IMG = os.path.join(HERE, "..", "image")
os.makedirs(IMG, exist_ok=True)

fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
for ax, (c, ctitle) in zip(axes, CASES):
    for k, (r, rname) in enumerate(RUNS):
        xs = [i + (k - 0.5) * 0.36 for i in range(len(METHODS))]
        ys = [S[r][c][m]["capacity"] for m, _ in METHODS]
        bars = ax.bar(xs, ys, 0.34, color=COL[r], label=rname)
        for x, y in zip(xs, ys):
            ax.text(x, y + max(ys) * 0.015, "N = %d" % y, ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.set_xticks(range(len(METHODS)))
    ax.set_xticklabels([n for _, n in METHODS], fontsize=10)
    ax.set_title(ctitle, fontsize=13, fontweight="bold")
    ax.set_ylabel("capacity N (concurrent users, p95 <= 500 ms)")
    ax.set_ylim(0, max(S[r][c][m]["capacity"] for r, _ in RUNS for m, _ in METHODS) * 1.14)
    ax.grid(axis="y", alpha=0.3)
    ax.legend(loc="upper left")
fig.suptitle("NGINX on the same machine: Round Robin vs Least Connections vs Power of Two Choices\n"
             "2 GPUs x 4 servers, micro-batching, one capacity search per bar", fontsize=12)
fig.tight_layout()
fig.savefig(os.path.join(IMG, "result-3methods.png"), dpi=140)

fig, ax = plt.subplots(figsize=(7.6, 4.8))
for k, (r, rname) in enumerate(RUNS):
    xs = [i + (k - 0.5) * 0.36 for i in range(len(METHODS))]
    ys = [S[r]["slow"][m]["p95_at_n64_first_try"] for m, _ in METHODS]
    ax.bar(xs, ys, 0.34, color=COL[r], label=rname)
    for x, y in zip(xs, ys):
        ax.text(x, y + 8, "%.0f ms" % y, ha="center", va="bottom", fontsize=10, fontweight="bold")
ax.axhline(500, color="#c62828", ls="--", lw=1.5)
ax.text(2.45, 508, "limit 500 ms", color="#c62828", ha="right", fontsize=10)
ax.set_xticks(range(len(METHODS)))
ax.set_xticklabels([n for _, n in METHODS], fontsize=10)
ax.set_ylabel("p95 latency at N = 64 (ms)")
ax.set_title("Same load (N = 64), GPU 1 made 3x slower", fontsize=12, fontweight="bold")
ax.grid(axis="y", alpha=0.3)
ax.set_ylim(0, 760)
ax.legend(loc="upper center", ncol=2)
fig.tight_layout()
fig.savefig(os.path.join(IMG, "result-p95-n64.png"), dpi=140)
print(json.dumps({r: {c: {m: S[r][c][m]["capacity"] for m, _ in METHODS} for c, _ in CASES} for r, _ in RUNS}))
