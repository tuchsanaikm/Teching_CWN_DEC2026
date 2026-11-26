#!/usr/bin/env python3
"""LAB 6.3 report: NGINX Round Robin vs Least Connections vs Power of Two Choices.

    python3 code/report3.py [--results results]

Input (written by run_lb3.sh / loadgen.py / cluster.sh), <name> = <method>_<case>:
    rr_equal lc_equal p2c_equal        both GPUs at the same speed
    rr_slow  lc_slow  p2c_slow         GPU 1 is 3x slower
    <name>.json                        capacity search
    <name>_nginx_running.conf          the config NGINX loaded (nginx -T);  <name>_nginx.conf = the file on disk
    <name>_nginx_error.log             NGINX warnings / errors written during the run
    <name>_upstream_counts.txt         requests per server and status from the NGINX access log
Output:
    results/metrics.json
    results/images/1_capacity.png  2_gpu_share.png  3_p95_vs_users.png
"""
import argparse
import collections
import datetime as dt
import json
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator

# numbers of one level and the chart style are the same as in report.py (LAB 6.1 / 6.2)
from report import (C_GPU0, C_GPU1, INK, INK2, P95_LIMIT_MS, by_gpu, level_row, load, save, users_axis)

METHODS = [  # key, name, nginx directive, colour (colour follows the method in every chart)
    ("rr", "Round Robin", "(no directive)", "#6250d6"),
    ("lc", "Least Connections", "least_conn;", "#1baf7a"),
    ("p2c", "Power of Two Choices", "random two least_conn;", "#eb6834"),
]
CASES = [("equal", "Equal GPUs"), ("slow", "GPU 1 is 3x slower")]
RUN_ORDER = ["p2c", "lc", "rr"]          # the order the methods were measured in, in each case


# ----------------------------------------------------------------------------- numbers
def read(path):
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return None


def conf_lines(text):
    """Config lines without the 'nginx -T' header line."""
    return [ln for ln in text.splitlines() if not ln.startswith("# configuration file ")]


def lb_directive(text):
    """The balancing directive of the upstream block ('' = none = Round Robin), comments removed."""
    found = []
    inside = False
    for ln in conf_lines(text):
        code = ln.split("#", 1)[0].strip()
        if code.startswith("upstream "):
            inside = True
        elif inside and code == "}":
            inside = False
        elif inside and re.match(r"(least_conn|random|ip_hash|hash|least_time)\b", code):
            found.append(code)
    return found


def run_metrics(results, method, case):
    name = "%s_%s" % (method, case)
    d = load(results, name)
    rows = [level_row(lv) for lv in d["levels"]]
    curve = []
    for dec in sorted(d["decisions"], key=lambda x: x["users"]):
        same = [r for r in rows if r["users"] == dec["users"]]
        hit = [r for r in same if r["p95_ms"] == dec["p95_ms"] and r["throughput_rps"] == dec["throughput_rps"]]
        row = dict((hit or same[-1:])[0])
        row["pass"], row["runs"] = dec["pass"], dec["runs"]
        curve.append(row)
    cap = d["capacity"]
    at_cap = next((r for r in curve if r["users"] == cap), None)
    # all measured requests of the whole search, per GPU
    tot = collections.OrderedDict()
    for lv in d["levels"]:
        for g, n in by_gpu(lv["servers"]).items():
            tot[g] = tot.get(g, 0) + n
    tsum = sum(tot.values()) or 1
    # the config NGINX really loaded
    running = read(os.path.join(results, name + "_nginx_running.conf"))
    ondisk = read(os.path.join(results, name + "_nginx.conf"))
    directive = lb_directive(running) if running else None
    want = {"rr": [], "lc": ["least_conn;"], "p2c": ["random two least_conn;"]}[method]
    state = read(os.path.join(results, name + "_cluster.state")) or ""
    slow = dict(re.findall(r"^(SLOW_GPU|SLOW_FACTOR|LB|MODE|GPUS|PER_GPU)=(.*)$", state, re.M))
    err_log = read(os.path.join(results, name + "_nginx_error.log")) or ""
    err_lines = [ln for ln in err_log.splitlines() if ln.strip()]
    counts = read(os.path.join(results, name + "_upstream_counts.txt")) or ""
    non200 = [ln for ln in counts.splitlines() if ln.strip() and not ln.rstrip().endswith("status=200")]
    again = [{"users": r["users"], "p95_ms": r["p95_ms"], "pass": r["pass"], "error_pct": r["error_pct"]}
             for r in rows if r["attempt"] == 2]
    return {
        "name": name, "method": method, "case": case,
        "started_utc": d["started_utc"], "finished_utc": d.get("finished_utc"), "finished": d["finished"],
        "servers": len(d["system"]["servers"]),
        "server_slowdown": {k: v.get("slowdown") for k, v in d["system"]["servers"].items()},
        "server_mode": sorted({str(s["mode"]) for s in d["system"]["servers"].values()}),
        "max_batch": sorted({s["max_batch"] for s in d["system"]["servers"].values()}),
        "max_wait_ms": sorted({s["max_wait_ms"] for s in d["system"]["servers"].values()}),
        "cluster_state": slow,
        "capacity_users": cap, "capacity_closed": d.get("capacity_closed"),
        "first_fail_users": d.get("first_fail_users"),
        "max_throughput_rps": d["max_throughput_rps"], "max_throughput_at_users": d["max_throughput_at_users"],
        "throughput_at_capacity_rps": at_cap and at_cap["throughput_rps"],
        "p95_ms_at_capacity": at_cap and at_cap["p95_ms"],
        "share_pct_by_gpu_at_capacity": at_cap and at_cap["share_pct_by_gpu"],
        "requests_by_gpu_at_capacity": at_cap and at_cap["requests_by_gpu"],
        "gpu_util_pct_at_capacity": at_cap and at_cap["gpu_util_pct"],
        "requests_by_gpu_all_levels": tot,
        "share_pct_by_gpu_all_levels": {g: round(100.0 * n / tsum, 1) for g, n in tot.items()},
        "runs": len(rows), "levels_measured_again": again,
        "measured_requests": sum(r["requests"] for r in rows), "errors": sum(r["errors"] for r in rows),
        "error_kinds": {k: sum(lv["error_kinds"].get(k, 0) for lv in d["levels"])
                        for k in sorted({k for lv in d["levels"] for k in lv["error_kinds"]})},
        "loadgen_busy_levels": [lv["users"] for lv in d["levels"] if lv.get("loadgen_busy")],
        "nginx": {
            "lb_directive_in_loaded_config": directive, "lb_directive_expected": want,
            "method_confirmed": directive == want,
            "loaded_config_equals_file_on_disk": bool(running and ondisk) and conf_lines(running) == ondisk.splitlines(),
            "error_log_lines": len(err_lines),
            "servers_temporarily_disabled": sum("temporarily disabled" in ln for ln in err_lines),
            "error_log_sample": err_lines[:5],
            "access_log_non_200": non200,
        },
        "curve": curve, "all_runs": rows,
    }


def config_diff(results):
    """Lines that are not the same in the 6 loaded configs (must be only the LB line)."""
    texts = {}
    for case, _ in CASES:
        for m, *_ in METHODS:
            t = read(os.path.join(results, "%s_%s_nginx_running.conf" % (m, case)))
            if t is not None:
                texts["%s_%s" % (m, case)] = conf_lines(t)
    if not texts:
        return {"compared": []}
    n = {len(v) for v in texts.values()}
    out = {"compared": sorted(texts), "same_number_of_lines": len(n) == 1, "different_lines": []}
    if len(n) == 1:
        for i in range(n.pop()):
            vals = {k: v[i] for k, v in texts.items()}
            if len(set(vals.values())) > 1:
                out["different_lines"].append({"line_number": i + 1, "by_run": {k: v.strip() for k, v in vals.items()}})
    out["only_the_lb_line_differs"] = bool(out.get("same_number_of_lines")) and len(out["different_lines"]) == 1
    return out


def build_metrics(results):
    runs = collections.OrderedDict()
    for case, _ in CASES:
        for m in RUN_ORDER:
            runs["%s_%s" % (m, case)] = run_metrics(results, m, case)
    tables = collections.OrderedDict()
    for case, clabel in CASES:
        rows = []
        for m, mname, directive, _c in METHODS:
            r = runs["%s_%s" % (m, case)]
            rows.append({"method": mname, "name": r["name"], "nginx_line": directive,
                         "capacity_users": r["capacity_users"], "first_fail_users": r["first_fail_users"],
                         "max_throughput_rps": r["max_throughput_rps"],
                         "max_throughput_at_users": r["max_throughput_at_users"],
                         "p95_ms_at_capacity": r["p95_ms_at_capacity"],
                         "share_pct_by_gpu_at_capacity": r["share_pct_by_gpu_at_capacity"],
                         "gpu_util_pct_at_capacity": r["gpu_util_pct_at_capacity"]})
        tables[case] = {"label": clabel, "rows": rows}
    return {
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "pass_rule": {"p95_ms_max": P95_LIMIT_MS, "error_pct_below": 1.0},
        "note": "capacity = largest number of concurrent users N that passes the rule; one machine, 2x RTX 3090, "
                "2 GPUs x 4 servers, micro-batching (max 32 images, wait <= 5 ms); 1 capacity search per method, "
                "measured in the order p2c, lc, rr in each case",
        "methods": {m: {"name": n, "nginx_line": d} for m, n, d, _c in METHODS},
        "tables": tables, "nginx_config_diff": config_diff(results), "runs": runs,
    }


# ----------------------------------------------------------------------------- charts
def chart_capacity(M, images):
    fig, ax = plt.subplots(figsize=(9.5, 5.6))
    top = max(r["capacity_users"] for r in M["runs"].values()) or 1
    w = 0.26
    for ci, (case, _cl) in enumerate(CASES):
        for mi, (m, mname, _d, col) in enumerate(METHODS):
            r = M["runs"]["%s_%s" % (m, case)]
            x = ci + (mi - 1) * (w + 0.02)
            ax.bar(x, r["capacity_users"], width=w, color=col, zorder=3, label=mname if ci == 0 else None)
            ax.text(x, r["capacity_users"] + top * 0.015, "%d" % r["capacity_users"], ha="center", fontsize=13,
                    fontweight="bold")
    ax.set_xticks(range(len(CASES)))
    ax.set_xticklabels([cl for _c, cl in CASES], fontsize=12)
    ax.set_ylim(0, top * 1.22)
    ax.set_ylabel("capacity (concurrent users N)")
    ax.set_title("Capacity of the 3 NGINX balancing methods\n2 GPUs x 4 servers, micro-batching; pass = p95 <= 500 ms and errors < 1 %",
                 fontsize=12.5)
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper right", ncol=3, fontsize=10)
    fig.tight_layout()
    save(fig, images, "1_capacity.png")


def chart_share(M, images):
    fig, ax = plt.subplots(figsize=(10.5, 5.8))
    order = [(case, cl, m, mname) for case, cl in CASES for m, mname, _d, _c in METHODS]
    for i, (case, cl, m, mname) in enumerate(order):
        y = len(order) - 1 - i + (0.35 if case == CASES[0][0] else 0.0)      # gap between the 2 cases
        r = M["runs"]["%s_%s" % (m, case)]
        s = r["share_pct_by_gpu_at_capacity"] or r["share_pct_by_gpu_all_levels"]
        g0, g1 = s.get("gpu0", 0.0), s.get("gpu1", 0.0)
        ax.barh(y, g0 - 0.3, height=0.6, color=C_GPU0, zorder=3, label="GPU 0" if i == 0 else None)
        ax.barh(y, g1 - 0.3, left=g0 + 0.3, height=0.6, color=C_GPU1, zorder=3, label="GPU 1" if i == 0 else None)
        if g0 >= 8:
            ax.text(g0 / 2, y, "%.1f %%" % g0, ha="center", va="center", color="white", fontsize=12, fontweight="bold")
        if g1 >= 8:
            ax.text(g0 + g1 / 2, y, "%.1f %%" % g1, ha="center", va="center", color=INK, fontsize=12, fontweight="bold")
        ax.text(101.5, y, "N=%d" % r["capacity_users"], va="center", fontsize=10.5, color=INK2)
        ax.text(-1.5, y, "%s\n%s" % (cl, mname), va="center", ha="right", fontsize=10.5, color=INK2)
    ax.axvline(50, color=INK2, linewidth=0.8, linestyle=":", zorder=4)
    ax.set_yticks([])
    ax.set_xlim(0, 112)
    ax.xaxis.set_major_locator(FixedLocator([0, 25, 50, 75, 100]))
    ax.set_xlabel("share of the requests answered at the capacity level (%)")
    ax.set_title("Share of requests each GPU got")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower center", bbox_to_anchor=(0.45, -0.25), ncol=2)
    fig.tight_layout()
    save(fig, images, "2_gpu_share.png")


def chart_p95(M, images):
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.8), sharey=True)
    for ax, (case, cl) in zip(axes, CASES):
        nmax = 1
        for m, mname, _d, col in METHODS:
            r = M["runs"]["%s_%s" % (m, case)]
            pts = [(c["users"], c["p95_ms"], c["pass"]) for c in r["curve"] if c["p95_ms"] is not None]
            nmax = max([nmax] + [p[0] for p in pts])
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=col, zorder=3,
                    label="%s (capacity N=%d)" % (mname, r["capacity_users"]))
            ax.scatter([p[0] for p in pts if p[2]], [p[1] for p in pts if p[2]], color=col, s=28, zorder=4)
            ax.scatter([p[0] for p in pts if not p[2]], [p[1] for p in pts if not p[2]], facecolor="white",
                       edgecolor=col, s=34, linewidth=1.6, zorder=4)
        ax.axhline(P95_LIMIT_MS, color="#e34948", linestyle="--", linewidth=1.2, zorder=2)
        ax.text(1, P95_LIMIT_MS * 1.08, "limit 500 ms", color="#e34948", fontsize=10)
        ax.set_yscale("log")
        users_axis(ax, nmax)
        ax.set_title(cl)
        ax.legend(loc="upper left", fontsize=10, bbox_to_anchor=(0.0, 0.9))
    axes[0].set_ylabel("p95 latency (ms, log scale)")
    fig.suptitle("p95 latency vs concurrent users N  (filled = pass, hollow = fail)", x=0.01, ha="left",
                 fontsize=14, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save(fig, images, "3_p95_vs_users.png")


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
    for chart in (chart_capacity, chart_share, chart_p95):
        chart(M, images)

    for case, t in M["tables"].items():
        print("\n%s\nmethod | capacity | first fail | max throughput | p95 at capacity | share gpu0/gpu1 | gpu util %%" % t["label"])
        for r in t["rows"]:
            s, u = r["share_pct_by_gpu_at_capacity"] or {}, r["gpu_util_pct_at_capacity"] or []
            print("%s | %s | %s | %.1f req/s (N=%d) | %s ms | %s / %s | %s" % (
                r["method"], r["capacity_users"], r["first_fail_users"], r["max_throughput_rps"],
                r["max_throughput_at_users"], r["p95_ms_at_capacity"], s.get("gpu0"), s.get("gpu1"),
                " / ".join("%.0f" % x for x in u)))
    cd = M["nginx_config_diff"]
    print("\nloaded NGINX configs compared: %d, only the LB line differs: %s" % (len(cd["compared"]), cd.get("only_the_lb_line_differs")))
    for dl in cd.get("different_lines", []):
        print("  line %d:" % dl["line_number"])
        for k, v in dl["by_run"].items():
            print("    %-10s %s" % (k, v))
    for k, r in M["runs"].items():
        n = r["nginx"]
        print("%-10s method_confirmed=%s runs=%d again=%s errors=%d %s nginx_error_lines=%d disabled=%d non200=%s" % (
            k, n["method_confirmed"], r["runs"], [a["users"] for a in r["levels_measured_again"]], r["errors"],
            r["error_kinds"], n["error_log_lines"], n["servers_temporarily_disabled"], n["access_log_non_200"]))


if __name__ == "__main__":
    main()
