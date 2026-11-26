#!/usr/bin/env python3
"""LAB 6 report: collect the numbers of every run into results/metrics.json and draw the charts.

    python3 code/report.py [--results results]

Input  (written by loadgen.py / cluster.sh):
    base batch multi gpu2            capacity search of the 4 layouts
    lc_equal rr_slow lc_slow         Round Robin vs Least Connections (gpu2 = Round Robin, equal GPUs)
    fail_off fail_on                 one GPU is killed at second 20
    fail_*_nginx_access.log[.gz]     which server answered each request (for the per-GPU chart)
Output:
    results/metrics.json
    results/images/1_p95_vs_users.png ... 7_gpu_failure.png
"""
import argparse
import collections
import datetime as dt
import gzip
import json
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

P95_LIMIT_MS = 500.0
LAYOUTS = [  # key, short label, long label, colour (fixed order, colour follows the layout)
    ("base", "1 base", "1 base: 1 GPU, 1 server, 1 image per call", "#2a78d6"),
    ("batch", "2 batch", "2 batch: 1 GPU, 1 server, micro-batching", "#eb6834"),
    ("multi", "3 multi", "3 multi: 1 GPU, 4 servers, micro-batching", "#1baf7a"),
    ("gpu2", "4 gpu2", "4 gpu2: 2 GPUs x 4 servers, micro-batching", "#eda100"),
]
LB_RUNS = [  # key, case, method
    ("gpu2", "Equal GPUs", "Round Robin"),
    ("lc_equal", "Equal GPUs", "Least Connections"),
    ("rr_slow", "GPU 1 is 3x slower", "Round Robin"),
    ("lc_slow", "GPU 1 is 3x slower", "Least Connections"),
]
FAIL_RUNS = [("fail_off", "failover off"), ("fail_on", "failover on")]
C_GPU0, C_GPU1, C_ERR = "#2a78d6", "#eda100", "#e34948"
C_RR, C_LC = "#6250d6", "#1baf7a"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.size": 11, "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.edgecolor": "#b9b8b2", "axes.labelcolor": INK2, "text.color": INK,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "legend.frameon": False, "lines.linewidth": 2.0, "lines.markersize": 5,
})


# ----------------------------------------------------------------------------- numbers
def load(results, name):
    with open(os.path.join(results, name + ".json")) as f:
        return json.load(f)


def by_gpu(servers, field="requests"):
    """Sum a per-server field into {'gpu0': .., 'gpu1': ..} (server names are 'gpu0-8101')."""
    out = collections.OrderedDict()
    for name in sorted(servers):
        gpu = name.split("-")[0]
        out[gpu] = out.get(gpu, 0) + servers[name].get(field, 0)
    return out


def level_row(lv):
    req = by_gpu(lv["servers"])
    total = sum(req.values()) or 1
    return {
        "users": lv["users"], "attempt": lv.get("attempt", 1), "pass": lv["pass"],
        "p50_ms": lv["latency_ms"]["p50"], "p95_ms": lv["latency_ms"]["p95"], "p99_ms": lv["latency_ms"]["p99"],
        "throughput_rps": lv["throughput_rps"], "requests": lv["requests"], "errors": lv["errors"],
        "error_pct": lv["error_pct"],
        "images_per_model_call": lv["model"]["batch_mean_per_call"],
        "queue_ms_mean": lv["model"]["queue_ms_mean"], "model_ms_mean": lv["model"]["model_ms_mean"],
        "gpu_util_pct": lv["gpu_util_pct"],
        "cpu_server_pct": lv["cpu_pct"]["server"], "cpu_nginx_pct": lv["cpu_pct"]["nginx"],
        "cpu_loadgen_pct": lv["cpu_pct"]["loadgen"], "server_procs": lv.get("server_procs"),
        "requests_by_gpu": req,
        "share_pct_by_gpu": {g: round(100.0 * n / total, 1) for g, n in req.items()},
    }


def capacity_metrics(results, name):
    """One capacity search -> its numbers. The 'curve' has one point per N: the run loadgen decided on."""
    d = load(results, name)
    rows = [level_row(lv) for lv in d["levels"]]
    curve = []
    for dec in sorted(d["decisions"], key=lambda x: x["users"]):
        same = [r for r in rows if r["users"] == dec["users"]]
        hit = [r for r in same if r["p95_ms"] == dec["p95_ms"] and r["throughput_rps"] == dec["throughput_rps"]]
        row = dict((hit or same[-1:])[0])
        row["pass"] = dec["pass"]
        row["runs"] = dec["runs"]
        curve.append(row)
    cap = d["capacity"]
    at_cap = next(r for r in curve if r["users"] == cap)
    used_gpus = [g for g, n in at_cap["requests_by_gpu"].items() if n > 0]
    gpu_idx = [int(g[3:]) for g in used_gpus]
    return {
        "name": name, "started_utc": d["started_utc"], "finished_utc": d["finished_utc"],
        "gpus_used": len(used_gpus), "servers": len(d["system"]["servers"]),
        "server_mode": sorted({s["mode"] for s in d["system"]["servers"].values()}),
        "cpu_count": d["system"]["cpu_count"], "gpu_names": d["system"]["gpus"],
        "level_seconds": d["config"]["level_seconds"], "warmup_s": d["config"]["warmup_s"],
        "pass_rule": d["config"]["pass_rule"],
        "capacity_users": cap, "capacity_closed": d.get("capacity_closed"),
        "first_fail_users": d.get("first_fail_users"),
        "max_throughput_rps": d["max_throughput_rps"], "max_throughput_at_users": d["max_throughput_at_users"],
        "at_capacity": at_cap,
        "gpu_util_pct_used_gpus_at_capacity": [at_cap["gpu_util_pct"][i] for i in gpu_idx],
        "runs": len(rows),
        "measured_requests": sum(r["requests"] for r in rows), "errors": sum(r["errors"] for r in rows),
        "curve": curve, "all_runs": rows,
    }


def open_text(path):
    return gzip.open(path, "rt") if path.endswith(".gz") else open(path)


LOG_RE = re.compile(r'\[([^\]]+)\] "POST /v1/detect[^"]*" (\d+) .*upstream=(.*) upstream_time=')


def access_log_per_second(results, name, t0):
    """Count the /v1/detect answers of each wall-clock second by the GPU of the server that answered.

    NGINX logs the time a request ended, cut to the full second. Bin k = wall second k after the
    second that holds t0 (test start); its centre on the test clock is returned as 't_mid_s'.
    """
    path = next((p for p in (os.path.join(results, name + "_nginx_access.log.gz"),
                             os.path.join(results, name + "_nginx_access.log")) if os.path.exists(p)), None)
    if path is None:
        return None
    base = int(t0.timestamp())            # full second that holds t0
    frac = t0.timestamp() - base
    bins = collections.defaultdict(lambda: collections.Counter())
    retried = 0
    with open_text(path) as f:
        for line in f:
            m = LOG_RE.search(line)
            if not m:
                continue
            sec = int(dt.datetime.fromisoformat(m.group(1)).timestamp()) - base
            ports = re.findall(r":(\d+)", m.group(3))
            retried += len(ports) > 1
            if m.group(2) != "200":
                bins[sec]["error"] += 1
            else:                          # the last upstream in the list is the one that answered
                bins[sec]["gpu%d" % (int(ports[-1]) // 100 - 81)] += 1
    rows = []
    for sec in range(min(bins), max(bins) + 1):
        c = bins[sec]
        rows.append({"t_mid_s": round(sec + 0.5 - frac, 3), "gpu0": c["gpu0"], "gpu1": c["gpu1"], "error": c["error"]})
    total = collections.Counter()
    for r in rows:
        for k in ("gpu0", "gpu1", "error"):
            total[k] += r[k]
    return {"source": os.path.basename(path), "note": "time = end of request, 1 s bins of the NGINX clock; "
            "warm-up included", "totals": dict(total), "sent_to_a_second_server": retried, "per_second": rows}


def fail_metrics(results, name):
    d = load(results, name)
    lv = d["levels"][0]
    ev = lv["event"]
    m = re.search(r"at (\S+Z)", ev["output"])
    kill = dt.datetime.fromisoformat(m.group(1).replace("Z", "+00:00"))
    t0 = kill - dt.timedelta(seconds=ev["started_s"])
    after_err = lv["after"]["error_pct"]
    after_p95 = lv["after"]["latency_ms"]["p95"]
    return {
        "name": name, "users": lv["users"], "level_seconds": d["config"]["level_seconds"],
        "warmup_s": d["config"]["warmup_s"], "failover": "on" if "failover=on" in ev["output"] else "off",
        "event": {"cmd": ev["cmd"], "started_s": ev["started_s"], "ended_s": ev["ended_s"],
                  "kill_utc": m.group(1), "test_start_utc": t0.isoformat()},
        "all_requests": lv["all_requests"], "in_flight_at_event": lv["in_flight_at_event"],
        "before": lv["before"], "during_event": lv["during_event"], "after": lv["after"],
        "after_passes_rule": bool(after_p95 <= P95_LIMIT_MS and after_err < 1.0),
        "loadgen_per_second": [{k: s[k] for k in ("second", "warmup", "ok", "errors", "p95_ms", "gpu_util_pct")}
                               for s in lv["per_second"]],
        "nginx_per_second": access_log_per_second(results, name, t0),
    }


def build_metrics(results):
    layouts = collections.OrderedDict((k, capacity_metrics(results, k)) for k, *_ in LAYOUTS)
    base_cap = layouts["base"]["capacity_users"]
    table = []
    for i, (k, short, long_, _c) in enumerate(LAYOUTS, 1):
        m = layouts[k]
        m["label"] = long_
        m["capacity_x_layout1"] = round(m["capacity_users"] / base_cap, 2)
        m["max_throughput_x_layout1"] = round(m["max_throughput_rps"] / layouts["base"]["max_throughput_rps"], 2)
        table.append({"layout": i, "name": k, "gpus": m["gpus_used"], "description": long_,
                      "capacity_users": m["capacity_users"], "max_throughput_rps": m["max_throughput_rps"],
                      "max_throughput_at_users": m["max_throughput_at_users"],
                      "p95_ms_at_capacity": m["at_capacity"]["p95_ms"],
                      "capacity_x_layout1": m["capacity_x_layout1"],
                      "max_throughput_x_layout1": m["max_throughput_x_layout1"]})
    lb = collections.OrderedDict()
    for k, case, method in LB_RUNS:
        m = layouts[k] if k in layouts else capacity_metrics(results, k)
        lb[k] = {"case": case, "method": method, "capacity_users": m["capacity_users"],
                 "first_fail_users": m["first_fail_users"],
                 "max_throughput_rps": m["max_throughput_rps"], "max_throughput_at_users": m["max_throughput_at_users"],
                 "throughput_at_capacity_rps": m["at_capacity"]["throughput_rps"],
                 "p95_ms_at_capacity": m["at_capacity"]["p95_ms"],
                 "share_pct_by_gpu_at_capacity": m["at_capacity"]["share_pct_by_gpu"],
                 "requests_by_gpu_at_capacity": m["at_capacity"]["requests_by_gpu"],
                 "gpu_util_pct_at_capacity": m["at_capacity"]["gpu_util_pct"],
                 "runs": m["runs"], "measured_requests": m["measured_requests"], "errors": m["errors"],
                 "curve": m["curve"]}
    fails = collections.OrderedDict((k, fail_metrics(results, k)) for k, _ in FAIL_RUNS)
    return {
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "pass_rule": {"p95_ms_max": P95_LIMIT_MS, "error_pct_below": 1.0},
        "note": "capacity = largest number of concurrent users N that passes the rule; one machine, 2x RTX 3090",
        "summary_table": table, "layouts": layouts, "load_balancing": lb, "gpu_failure": fails,
    }


# ----------------------------------------------------------------------------- charts
def users_axis(ax, max_users):
    ax.set_xscale("log", base=2)
    ticks = [t for t in (1, 2, 4, 8, 16, 32, 64, 128, 256, 512) if t <= max_users]
    ax.xaxis.set_major_locator(FixedLocator(ticks))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: "%d" % v))
    ax.set_xlabel("concurrent users N (log scale)")


def save(fig, images, name):
    path = os.path.join(images, name)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("wrote", path)


def chart_p95(M, images):
    fig, ax = plt.subplots(figsize=(10.5, 6))
    offsets = {"base": (-34, 12), "batch": (-14, 30), "multi": (-62, -44), "gpu2": (14, -26)}
    for k, short, long_, c in LAYOUTS:
        m = M["layouts"][k]
        cur = m["curve"]
        ax.plot([r["users"] for r in cur], [r["p95_ms"] for r in cur], "-o", color=c, label=long_, zorder=3)
        cap = m["at_capacity"]
        ax.plot([cap["users"]], [cap["p95_ms"]], "o", color=c, markersize=13, markeredgecolor=SURFACE,
                markeredgewidth=2, zorder=5)
        ax.annotate("N=%d" % cap["users"], (cap["users"], cap["p95_ms"]), textcoords="offset points",
                    xytext=offsets[k], fontsize=11, fontweight="bold", color=INK,
                    bbox={"facecolor": SURFACE, "edgecolor": "none", "pad": 1.5},
                    arrowprops={"arrowstyle": "-", "color": INK2, "lw": 0.8}, zorder=6)
    ax.axhline(P95_LIMIT_MS, color=C_ERR, linestyle="--", linewidth=1.5, zorder=2)
    ax.text(1.0, P95_LIMIT_MS + 18, "limit: p95 = 500 ms", color=INK, fontsize=10.5)
    ax.plot([], [], "o", color="#8a8984", markersize=13, markeredgecolor=SURFACE, markeredgewidth=2,
            label="capacity = largest N that passes")
    users_axis(ax, 512)
    ax.set_ylim(0, 1350)
    ax.set_ylabel("p95 latency (ms)")
    ax.set_title("p95 latency vs concurrent users - 4 layouts")
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.93))
    save(fig, images, "1_p95_vs_users.png")


def chart_throughput(M, images):
    fig, ax = plt.subplots(figsize=(10.5, 6))
    for k, short, long_, c in LAYOUTS:
        m = M["layouts"][k]
        cur = m["curve"]
        ax.plot([r["users"] for r in cur], [r["throughput_rps"] for r in cur], "-o", color=c, label=long_, zorder=3)
        last = cur[-1]
        ax.annotate("max %.0f req/s" % m["max_throughput_rps"], (last["users"], last["throughput_rps"]),
                    textcoords="offset points", xytext=(8, -4), fontsize=10.5, color=INK)
    users_axis(ax, 512)
    ax.set_xlim(0.85, 1500)
    ax.set_ylim(0, 620)
    ax.set_ylabel("throughput (successful requests / s)")
    ax.set_title("Throughput vs concurrent users - 4 layouts")
    ax.legend(loc="upper left")
    save(fig, images, "2_throughput_vs_users.png")


def chart_capacity(M, images):
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for i, (k, short, long_, c) in enumerate(LAYOUTS):
        m = M["layouts"][k]
        ax.bar(i, m["capacity_users"], width=0.6, color=c, zorder=3)
        ax.text(i, m["capacity_users"] + 3, "%d users" % m["capacity_users"], ha="center", fontsize=13,
                fontweight="bold")
        ax.text(i, m["capacity_users"] + 13.5, "x%.2f of layout 1" % m["capacity_x_layout1"], ha="center",
                fontsize=10, color=INK2)
    ax.set_xticks(range(4))
    ax.set_xticklabels(["1 base\n1 GPU, 1 server\n1 image per call", "2 batch\n1 GPU, 1 server\nmicro-batching",
                        "3 multi\n1 GPU, 4 servers\nmicro-batching", "4 gpu2\n2 GPUs x 4 servers\nmicro-batching"])
    ax.set_ylim(0, 215)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("capacity (concurrent users)")
    ax.set_title("Capacity of the 4 layouts (largest N with p95 <= 500 ms and errors < 1 %)")
    save(fig, images, "3_capacity_bar.png")


def chart_batch(M, images):
    fig, ax = plt.subplots(figsize=(10.5, 6))
    for k, short, long_, c in LAYOUTS:
        m = M["layouts"][k]
        cur = m["curve"]
        ax.plot([r["users"] for r in cur], [r["images_per_model_call"] for r in cur], "-o", color=c, label=long_,
                zorder=3)
        cap = m["at_capacity"]
        ax.plot([cap["users"]], [cap["images_per_model_call"]], "o", color=c, markersize=13, markeredgecolor=SURFACE,
                markeredgewidth=2, zorder=5)
        last = cur[-1]
        ax.annotate("%.1f" % last["images_per_model_call"], (last["users"], last["images_per_model_call"]),
                    textcoords="offset points", xytext=(8, -4), fontsize=10.5, color=INK,
                    bbox={"facecolor": SURFACE, "edgecolor": "none", "pad": 1.5})
    ax.plot([], [], "o", color="#8a8984", markersize=13, markeredgecolor=SURFACE, markeredgewidth=2,
            label="at capacity")
    ax.axhline(32, color=INK2, linestyle=":", linewidth=1.2)
    ax.text(1.0, 32.6, "max batch = 32", color=INK2, fontsize=10)
    users_axis(ax, 512)
    ax.set_xlim(0.85, 900)
    ax.set_ylim(0, 35)
    ax.set_ylabel("mean images per model call")
    ax.set_title("Images that enter the model together vs concurrent users (mean per server)")
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.9))
    save(fig, images, "4_images_per_call_vs_users.png")


def chart_gpu_cpu(M, images):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5.5))
    names = ["1 base", "2 batch", "3 multi", "4 gpu2\nGPU 0", "4 gpu2\nGPU 1"]
    vals, cols = [], []
    for k, short, long_, c in LAYOUTS:
        for v in M["layouts"][k]["gpu_util_pct_used_gpus_at_capacity"]:
            vals.append(v)
            cols.append(c)
    a1.bar(range(len(vals)), vals, width=0.62, color=cols, zorder=3)
    for i, v in enumerate(vals):
        a1.text(i, v + 1.5, "%.0f %%" % v, ha="center", fontsize=12, fontweight="bold")
    a1.set_xticks(range(len(vals)))
    a1.set_xticklabels(names)
    a1.set_ylim(0, 100)
    a1.set_ylabel("GPU utilisation (%, nvidia-smi mean)")
    a1.set_title("GPU busy at capacity")
    a1.grid(axis="x", visible=False)

    for i, (k, short, long_, c) in enumerate(LAYOUTS):
        m = M["layouts"][k]
        v = m["at_capacity"]["cpu_server_pct"]
        a2.bar(i, v, width=0.62, color=c, zorder=3)
        a2.text(i, v + 20, "%.0f %%" % v, ha="center", fontsize=12, fontweight="bold")
        a2.text(i, v + 75, "= %.1f cores" % (v / 100.0), ha="center", fontsize=10, color=INK2)
    a2.set_xticks(range(4))
    a2.set_xticklabels(["1 base\n1 process\nN=%d" % M["layouts"]["base"]["capacity_users"],
                        "2 batch\n1 process\nN=%d" % M["layouts"]["batch"]["capacity_users"],
                        "3 multi\n4 processes\nN=%d" % M["layouts"]["multi"]["capacity_users"],
                        "4 gpu2\n8 processes\nN=%d" % M["layouts"]["gpu2"]["capacity_users"]])
    a2.set_ylim(0, 1300)
    a2.set_ylabel("CPU of all server processes (%, 100 % = 1 core)")
    a2.set_title("Server CPU at capacity (machine: %d cores)" % M["layouts"]["base"]["cpu_count"])
    a2.grid(axis="x", visible=False)
    fig.suptitle("GPU and server CPU at the capacity level of each layout", x=0.01, ha="left", fontsize=14,
                 fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    save(fig, images, "5_gpu_cpu_at_capacity.png")


def chart_lb(M, images):
    lb = M["load_balancing"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 5.8), gridspec_kw={"width_ratios": [1, 1.15]})
    cases = ["Equal GPUs", "GPU 1 is 3x slower"]
    for ci, case in enumerate(cases):
        for mi, (method, col) in enumerate((("Round Robin", C_RR), ("Least Connections", C_LC))):
            run = next(v for v in lb.values() if v["case"] == case and v["method"] == method)
            x = ci + (mi - 0.5) * 0.38
            a1.bar(x, run["capacity_users"], width=0.34, color=col, zorder=3,
                   label=method if ci == 0 else None)
            a1.text(x, run["capacity_users"] + 4, "%d" % run["capacity_users"], ha="center", fontsize=13,
                    fontweight="bold")
    a1.set_xticks(range(2))
    a1.set_xticklabels(cases)
    a1.set_ylim(0, 290)
    a1.set_ylabel("capacity (concurrent users)")
    a1.set_title("Capacity")
    a1.grid(axis="x", visible=False)
    a1.legend(loc="upper right")

    order = [("gpu2", "Equal GPUs\nRound Robin"), ("lc_equal", "Equal GPUs\nLeast Connections"),
             ("rr_slow", "GPU 1 3x slower\nRound Robin"), ("lc_slow", "GPU 1 3x slower\nLeast Connections")]
    for i, (k, lab) in enumerate(order):
        y = len(order) - 1 - i
        s = lb[k]["share_pct_by_gpu_at_capacity"]
        g0, g1 = s.get("gpu0", 0.0), s.get("gpu1", 0.0)
        a2.barh(y, g0 - 0.3, height=0.55, color=C_GPU0, zorder=3, label="GPU 0" if i == 0 else None)
        a2.barh(y, g1 - 0.3, left=g0 + 0.3, height=0.55, color=C_GPU1, zorder=3,
                label="GPU 1" if i == 0 else None)
        a2.text(g0 / 2, y, "%.1f %%" % g0, ha="center", va="center", color="white", fontsize=12, fontweight="bold")
        a2.text(g0 + g1 / 2, y, "%.1f %%" % g1, ha="center", va="center", color=INK, fontsize=12, fontweight="bold")
        a2.text(101.5, y, "N=%d" % lb[k]["capacity_users"], va="center", fontsize=10.5, color=INK2)
    a2.set_yticks(range(len(order)))
    a2.set_yticklabels([lab for _k, lab in order][::-1])
    a2.set_xlim(0, 112)
    a2.xaxis.set_major_locator(FixedLocator([0, 25, 50, 75, 100]))
    a2.set_xlabel("share of requests at the capacity level (%)")
    a2.set_title("Share of requests per GPU")
    a2.grid(axis="y", visible=False)
    a2.legend(loc="lower center", bbox_to_anchor=(0.45, -0.3), ncol=2)
    fig.suptitle("NGINX Round Robin vs Least Connections (2 GPUs x 4 servers, micro-batching)", x=0.01, ha="left",
                 fontsize=14, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save(fig, images, "6_round_robin_vs_least_conn.png")


def chart_failure(M, images):
    fig, axes = plt.subplots(2, 1, figsize=(12.5, 8.6), sharex=True, sharey=True)
    for ax, (k, title) in zip(axes, FAIL_RUNS):
        m = M["gpu_failure"][k]
        rows = [r for r in m["nginx_per_second"]["per_second"] if -0.5 <= r["t_mid_s"] <= m["level_seconds"] + 0.5]
        x = [r["t_mid_s"] for r in rows]
        g0 = [r["gpu0"] for r in rows]
        g1 = [r["gpu1"] for r in rows]
        er = [r["error"] for r in rows]
        ax.bar(x, g0, width=0.84, color=C_GPU0, label="answered by GPU 0", zorder=3)
        ax.bar(x, g1, width=0.84, bottom=g0, color=C_GPU1, label="answered by GPU 1", zorder=3)
        ax.bar(x, er, width=0.84, bottom=[a + b for a, b in zip(g0, g1)], color=C_ERR,
               label="error (HTTP 502)", zorder=3)
        t_kill = m["event"]["started_s"]
        ax.axvline(t_kill, color=INK, linestyle="--", linewidth=1.5, zorder=4)
        ax.text(t_kill + 0.5, 690, "GPU 1 killed at %.0f s" % t_kill, fontsize=11, fontweight="bold", va="top")
        ax.axvspan(-0.5, m["warmup_s"], color="#8a8984", alpha=0.13, zorder=1)
        ax.text(m["warmup_s"] / 2 - 0.25, 690, "warm-up", ha="center", va="top", fontsize=9.5, color=INK2)
        a = m["all_requests"]
        ax.set_title("%s (--failover %s): %d errors of %d requests = %.1f %%;  after the kill %.0f req/s OK, "
                     "p95 %.0f ms" % (k, m["failover"], a["errors"], a["requests"], a["error_pct"],
                                      m["after"]["throughput_ok_rps"], m["after"]["latency_ms"]["p95"]),
                     fontsize=12)
        ax.set_ylabel("requests finished per second")
        ax.set_ylim(0, 700)
        ax.set_xlim(-0.6, m["level_seconds"] + 0.6)
        ax.grid(axis="x", visible=False)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", ncol=3, bbox_to_anchor=(0.995, 0.958), fontsize=11.5)
    axes[1].set_xlabel("time since test start (s) - %d users, 1 s bins from the NGINX access log"
                       % M["gpu_failure"]["fail_off"]["users"])
    fig.suptitle("One GPU dies in the middle: requests per second by GPU and errors", x=0.01, ha="left",
                 fontsize=14, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.925))
    save(fig, images, "7_gpu_failure.png")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--results", default=os.path.join(here, "..", "results"))
    args = ap.parse_args()
    results = os.path.abspath(args.results)
    images = os.path.join(results, "images")
    os.makedirs(images, exist_ok=True)

    M = build_metrics(results)
    out = os.path.join(results, "metrics.json")
    with open(out, "w") as f:
        json.dump(M, f, indent=1)
    print("wrote", out)

    for chart in (chart_p95, chart_throughput, chart_capacity, chart_batch, chart_gpu_cpu, chart_lb, chart_failure):
        chart(M, images)

    print("\n# | GPUs | layout | capacity | max throughput | p95 at capacity | x layout 1")
    for r in M["summary_table"]:
        print("%d | %d | %s | %d | %.1f req/s (N=%d) | %.1f ms | %.2f" % (
            r["layout"], r["gpus"], r["name"], r["capacity_users"], r["max_throughput_rps"],
            r["max_throughput_at_users"], r["p95_ms_at_capacity"], r["capacity_x_layout1"]))


if __name__ == "__main__":
    main()
