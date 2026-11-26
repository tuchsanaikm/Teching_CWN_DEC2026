#!/usr/bin/env python3
"""LAB 6.3 report: Round Robin vs Least Connections vs Power of Two Choices (NGINX), 2 cases.

    python3 code/report3.py [--results results]

Reads   results/<method>_<case>.json (+ _nginx.conf, _nginx_running.conf, _nginx_error.log, _status_after.txt)
        method = rr | lc | p2c      case = equal (both GPUs normal) | slow (GPU 1 is 3x slower)
Writes  results/metrics.json
        results/images/1_capacity.png            capacity of the 3 methods in both cases
        results/images/2_gpu_share.png           share of requests each GPU got
        results/images/3_p95_vs_users_equal.png  p95 vs N of the 3 methods, equal GPUs
        results/images/4_p95_vs_users_slow.png   p95 vs N of the 3 methods, GPU 1 is 3x slower
The numbers of one capacity search come from report.py (capacity_metrics), the same code as LAB 6.1 / 6.2.
"""
import argparse
import collections
import json
import os
import re

import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator

from report import (C_ERR, C_GPU0, C_GPU1, C_LC, C_RR, INK, INK2, P95_LIMIT_MS, SURFACE, by_gpu,
                    capacity_metrics, save, users_axis)

C_P2C = "#eb6834"
METHODS = [  # key, name, colour, the balancing line cluster.sh must have written
    ("rr", "Round Robin", C_RR, ""),
    ("lc", "Least Connections", C_LC, "least_conn;"),
    ("p2c", "Power of Two Choices", C_P2C, "random two least_conn;"),
]
CASES = [("equal", "Equal GPUs"), ("slow", "GPU 1 is 3x slower")]
RE_LB = re.compile(r"^\s*(least_conn|random|ip_hash|hash|least_time)(\s[^;]*)?;")


def read_lines(path):
    if not os.path.exists(path):
        return None
    with open(path, errors="replace") as f:
        return f.read().splitlines()


def lb_directives(lines):
    """Balancing directives of a config, comments removed. [] = Round Robin."""
    out = []
    for ln in lines:
        m = RE_LB.match(ln.split("#", 1)[0])
        if m:
            out.append(" ".join(m.group(0).split()))
    return out


def lb_block(lines):
    """The lines between '# BEGIN LB' and '# END LB' (what cluster.sh wrote)."""
    a = next(i for i, ln in enumerate(lines) if ln.strip().startswith("# BEGIN LB"))
    b = next(i for i, ln in enumerate(lines) if ln.strip().startswith("# END LB"))
    return [ln.strip() for ln in lines[a + 1:b]]


def config_check(results, name, want):
    conf = read_lines(os.path.join(results, name + "_nginx.conf"))
    running = read_lines(os.path.join(results, name + "_nginx_running.conf"))
    got = lb_directives(running if running is not None else conf)
    return {
        "file": name + "_nginx.conf", "running_file": name + "_nginx_running.conf" if running is not None else None,
        "lb_line": lb_block(conf), "lb_directives_in_running_config": got,
        "expected_directive": want or "(none)", "matches_request": got == ([want] if want else []),
        "running_config_equals_file": None if running is None else running == conf,
    }


def differing_lines(results, names):
    """Line numbers at which the config files of the given runs are not all the same."""
    files = [read_lines(os.path.join(results, n + "_nginx.conf")) for n in names]
    same_length = len({len(f) for f in files}) == 1
    diff = []
    for i in range(min(len(f) for f in files)):
        if len({f[i] for f in files}) > 1:
            diff.append({"line": i + 1, **{n: f[i].strip() for n, f in zip(names, files)}})
    return {"same_number_of_lines": same_length, "differing_lines": diff, "only_lb_line_differs":
            same_length and len(diff) == 1 and all(RE_LB.match(v.split("#", 1)[0]) or v.startswith("#")
                                                   for k, v in diff[0].items() if k != "line")}


def anomalies(results, name, doc, m):
    err_lines = read_lines(os.path.join(results, name + "_nginx_error.log")) or []
    after = read_lines(os.path.join(results, name + "_status_after.txt")) or []
    kinds = collections.Counter()
    for lv in doc["levels"]:
        for k, v in (lv.get("error_kinds") or {}).items():
            kinds[k] += v
    retested = [{"users": d["users"], "final_pass": d["pass"], "p95_ms_runs": [
        lv["latency_ms"]["p95"] for lv in doc["levels"] if lv["users"] == d["users"]]}
        for d in doc["decisions"] if d["runs"] > 1]
    return {
        "levels_measured_twice": retested,
        "levels_passed_on_second_run": [r["users"] for r in retested if r["final_pass"]],
        "errors_total": m["errors"], "error_kinds": dict(kinds),
        "levels_with_errors": [{"users": lv["users"], "attempt": lv.get("attempt", 1), "errors": lv["errors"],
                                "error_pct": lv["error_pct"]} for lv in doc["levels"] if lv["errors"]],
        "nginx_error_log_lines": len(err_lines),
        "nginx_server_disabled_lines": sum(1 for ln in err_lines if "temporarily disabled" in ln or "no live upstreams" in ln),
        "nginx_error_log_sample": err_lines[:5],
        "cluster_status_after": next((ln.strip() for ln in after if "status:" in ln), None),
        "loadgen_busy_levels": [lv["users"] for lv in doc["levels"] if lv.get("loadgen_busy")],
    }


def build_metrics(results):
    runs = collections.OrderedDict()
    for case, case_name in CASES:
        for key, method, _c, want in METHODS:
            name = "%s_%s" % (key, case)
            with open(os.path.join(results, name + ".json")) as f:
                doc = json.load(f)
            m = capacity_metrics(results, name)
            total = by_gpu({k: {"requests": sum(lv["servers"].get(k, {}).get("requests", 0) for lv in doc["levels"])}
                            for k in doc["system"]["servers"]})
            tsum = sum(total.values()) or 1
            first_fail = m["first_fail_users"]
            ff = next((r for r in m["curve"] if r["users"] == first_fail), None)
            m.update(
                case=case, case_name=case_name, method=key, method_name=method,
                slowdown_by_server={k: v.get("slowdown") for k, v in doc["system"]["servers"].items()},
                p95_ms_at_capacity=m["at_capacity"]["p95_ms"],
                p95_ms_at_first_fail=ff["p95_ms"] if ff else None,
                share_pct_by_gpu_at_capacity=m["at_capacity"]["share_pct_by_gpu"],
                share_pct_by_gpu_all_levels={g: round(100.0 * n / tsum, 1) for g, n in total.items()},
                gpu_util_pct_at_capacity=m["at_capacity"]["gpu_util_pct"],
                nginx_config=config_check(results, name, want),
                anomalies=anomalies(results, name, doc, m),
            )
            runs[name] = m
    config = {case: differing_lines(results, ["%s_%s" % (k, case) for k, *_ in METHODS]) for case, _n in CASES}
    config["all_six_files"] = differing_lines(results, list(runs))
    table = [{
        "case": m["case_name"], "method": m["method_name"], "name": n, "capacity_users": m["capacity_users"],
        "first_fail_users": m["first_fail_users"], "max_throughput_rps": m["max_throughput_rps"],
        "max_throughput_at_users": m["max_throughput_at_users"], "p95_ms_at_capacity": m["p95_ms_at_capacity"],
        "share_pct_gpu0": m["share_pct_by_gpu_at_capacity"].get("gpu0"),
        "share_pct_gpu1": m["share_pct_by_gpu_at_capacity"].get("gpu1"),
        "gpu_util_pct": m["gpu_util_pct_at_capacity"],
    } for n, m in runs.items()]
    return {"pass_rule": {"p95_ms_max": P95_LIMIT_MS, "error_pct_below": 1.0},
            "layout": "2 GPUs x 4 servers, micro-batching (max 32 images, wait max 5 ms)",
            "order_measured": list(runs), "summary_table": table, "nginx_config_diff": config, "runs": runs}


# ----------------------------------------------------------------------------- charts
def chart_capacity(M, images):
    fig, ax = plt.subplots(figsize=(9.5, 5.8))
    top = max(m["capacity_users"] for m in M["runs"].values())
    for ci, (case, _n) in enumerate(CASES):
        for mi, (key, method, col, _w) in enumerate(METHODS):
            cap = M["runs"]["%s_%s" % (key, case)]["capacity_users"]
            x = ci + (mi - 1) * 0.27
            ax.bar(x, cap, width=0.25, color=col, zorder=3, label=method if ci == 0 else None)
            ax.text(x, cap + top * 0.015, "%d" % cap, ha="center", fontsize=13, fontweight="bold")
    ax.set_xticks(range(len(CASES)))
    ax.set_xticklabels([n for _c, n in CASES])
    ax.set_ylim(0, top * 1.22)
    ax.set_ylabel("capacity (concurrent users)")
    ax.set_title("Capacity by NGINX balancing method (2 GPUs x 4 servers, micro-batching)")
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper right", ncol=3)
    ax.text(0.0, -0.13, "capacity = largest N with p95 <= 500 ms and errors < 1 %", transform=ax.transAxes,
            fontsize=10, color=INK2)
    save(fig, images, "1_capacity.png")


def chart_share(M, images):
    fig, ax = plt.subplots(figsize=(10.5, 5.6))
    order = [("%s_%s" % (k, c), "%s\n%s" % (cn, mn)) for c, cn in CASES for k, mn, _c, _w in METHODS]
    for i, (name, _lab) in enumerate(order):
        y = len(order) - 1 - i - (0.35 if i >= len(METHODS) else 0)
        s = M["runs"][name]["share_pct_by_gpu_at_capacity"]
        g0, g1 = s.get("gpu0", 0.0), s.get("gpu1", 0.0)
        ax.barh(y, g0 - 0.3, height=0.6, color=C_GPU0, zorder=3, label="GPU 0" if i == 0 else None)
        ax.barh(y, g1 - 0.3, left=g0 + 0.3, height=0.6, color=C_GPU1, zorder=3, label="GPU 1" if i == 0 else None)
        ax.text(g0 / 2, y, "%.1f %%" % g0, ha="center", va="center", color="white", fontsize=12, fontweight="bold")
        ax.text(g0 + g1 / 2, y, "%.1f %%" % g1, ha="center", va="center", color=INK, fontsize=12, fontweight="bold")
        ax.text(101.5, y, "N=%d" % M["runs"][name]["capacity_users"], va="center", fontsize=10.5, color=INK2)
    ax.set_yticks([len(order) - 1 - i - (0.35 if i >= len(METHODS) else 0) for i in range(len(order))])
    ax.set_yticklabels([lab for _n, lab in order])
    ax.set_xlim(0, 112)
    ax.xaxis.set_major_locator(FixedLocator([0, 25, 50, 75, 100]))
    ax.set_xlabel("share of requests at the capacity level (%)")
    ax.set_title("Share of requests per GPU, by balancing method")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower center", bbox_to_anchor=(0.45, -0.27), ncol=2)
    save(fig, images, "2_gpu_share.png")


def chart_p95(M, images, case, case_name, fname):
    fig, ax = plt.subplots(figsize=(10.5, 6))
    runs = [(M["runs"]["%s_%s" % (k, case)], mn, col) for k, mn, col, _w in METHODS]
    nmax = max(r["users"] for m, _n, _c in runs for r in m["curve"])
    ylim = 1400.0
    for (m, method, col), dy in zip(runs, (34, 0, -34)):
        cur = m["curve"]
        ax.plot([r["users"] for r in cur], [min(r["p95_ms"], ylim) if r["p95_ms"] is not None else ylim for r in cur],
                "-o", color=col, label="%s (capacity N=%d)" % (method, m["capacity_users"]), zorder=3)
        cap = m["at_capacity"]
        ax.plot([cap["users"]], [cap["p95_ms"]], "o", color=col, markersize=13, markeredgecolor=SURFACE,
                markeredgewidth=2, zorder=5)
    ax.axhline(P95_LIMIT_MS, color=C_ERR, linestyle="--", linewidth=1.5, zorder=2)
    ax.text(1.0, P95_LIMIT_MS + 18, "limit: p95 = 500 ms", color=INK, fontsize=10.5)
    ax.plot([], [], "o", color="#8a8984", markersize=13, markeredgecolor=SURFACE, markeredgewidth=2,
            label="capacity = largest N that passes")
    users_axis(ax, max(nmax, 2))
    ax.set_ylim(0, ylim)
    ax.set_ylabel("p95 latency (ms), cut at %d" % ylim)
    ax.set_title("p95 latency vs concurrent users - %s" % case_name)
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.93))
    save(fig, images, fname)


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

    chart_capacity(M, images)
    chart_share(M, images)
    chart_p95(M, images, "equal", "Equal GPUs", "3_p95_vs_users_equal.png")
    chart_p95(M, images, "slow", "GPU 1 is 3x slower", "4_p95_vs_users_slow.png")

    print("\ncase | method | capacity | first fail | max throughput | p95 at capacity | GPU0 / GPU1 share | GPU util")
    for r in M["summary_table"]:
        print("%s | %s | %d | %s | %.1f req/s (N=%d) | %.1f ms | %s / %s %% | %s" % (
            r["case"], r["method"], r["capacity_users"], r["first_fail_users"], r["max_throughput_rps"],
            r["max_throughput_at_users"], r["p95_ms_at_capacity"], r["share_pct_gpu0"], r["share_pct_gpu1"],
            r["gpu_util_pct"]))
    for case, d in M["nginx_config_diff"].items():
        print("config diff %s: only the LB line differs = %s, lines %s" % (
            case, d["only_lb_line_differs"], [x["line"] for x in d["differing_lines"]]))
    for n, m in M["runs"].items():
        a = m["anomalies"]
        print("%s: config ok=%s | twice=%s | errors=%d %s | nginx error lines=%d (disabled: %d) | after: %s" % (
            n, m["nginx_config"]["matches_request"], [x["users"] for x in a["levels_measured_twice"]],
            a["errors_total"], a["error_kinds"], a["nginx_error_log_lines"], a["nginx_server_disabled_lines"],
            a["cluster_status_after"]))


if __name__ == "__main__":
    main()
