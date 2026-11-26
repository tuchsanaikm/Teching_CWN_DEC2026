#!/usr/bin/env python3
"""LAB 6 - compare the two NGINX balancing methods (Round Robin / Least Connections) on layout 4.

  python make_lb_summary.py <results-dir>      -> prints the tables and writes <results-dir>/lb_summary.md

Reads gpu2.json (Round Robin, equal GPUs), lc_equal.json, rr_slow.json, lc_slow.json (written by loadgen.py).
"At capacity" = the passing run at N = capacity. Every number comes from the result files.
"""
import json
import os
import sys

CASES = [
    ("Equal GPUs", [("Round Robin", "gpu2"), ("Least Connections", "lc_equal")]),
    ("GPU 1 is 3x slower", [("Round Robin", "rr_slow"), ("Least Connections", "lc_slow")]),
]


def gpu_share(level):
    """{gpu name: (requests, share %)} from the per-server counts of one level."""
    per = {}
    for name, s in level["servers"].items():
        g = name.split("-")[0]
        per[g] = per.get(g, 0) + s["requests"]
    total = sum(per.values()) or 1
    return {g: (n, 100.0 * n / total) for g, n in sorted(per.items())}


def row(label, name, rdir):
    path = os.path.join(rdir, name + ".json")
    if not os.path.isfile(path):
        return f"| {label} | {name} | (no result file) | | | | | | |", None
    d = json.load(open(path))
    cap = d["capacity"]
    at = [l for l in d["levels"] if l["users"] == cap and l["pass"]]
    if not at:
        return f"| {label} | {name} | {cap} | (no passing run at capacity) | | | | | |", d
    lv = at[-1]
    sh = gpu_share(lv)
    share = " / ".join(f"{p:.1f} %" for _, p in sh.values())
    util = " / ".join(f"{u:.0f} %" for u in lv["gpu_util_pct"])
    top = max(d["levels"], key=lambda l: l["throughput_rps"])
    tsh = " / ".join(f"{p:.1f} %" for _, p in gpu_share(top).values())
    tutil = " / ".join(f"{u:.0f} %" for u in top["gpu_util_pct"])
    sign = "" if d.get("capacity_closed", True) else ">= "
    return (f"| {label} | {name} | {sign}{cap} | {d['max_throughput_rps']:.1f} req/s (N={d['max_throughput_at_users']}) | "
            f"{lv['throughput_rps']:.1f} req/s | {lv['latency_ms']['p95']} ms | {share} | {util} | {tsh} ; {tutil} |"), d


def main():
    rdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
    out = ["# LAB 6 - NGINX Round Robin vs Least Connections (layout 4: 2 GPUs x 4 servers, micro-batching)",
           "", "Pass = p95 <= 500 ms and errors < 1 %. Capacity = largest N (concurrent users) that passes.",
           "Share and GPU % are gpu0 / gpu1."]
    for title, rows in CASES:
        out += ["", f"## {title}", "",
                "| method | result | capacity N | max throughput | throughput at capacity | p95 at capacity | "
                "requests share at capacity | GPU busy at capacity | share ; GPU busy at max throughput |",
                "|---|---|---|---|---|---|---|---|---|"]
        notes = []
        for label, name in rows:
            line, d = row(label, name, rdir)
            out.append(line)
            if d:
                fails = sorted({l["users"] for l in d["levels"] if not l["pass"] and l["users"] > d["capacity"]})
                errs = sum(l["errors"] for l in d["levels"])
                reqs = sum(l["requests"] for l in d["levels"])
                slow = sorted({str(v.get("slowdown")) for k, v in d["system"]["servers"].items() if k.startswith("gpu1")})
                notes.append(f"- {name}: capacity {d['capacity']} (first failing N above it: {fails[0] if fails else '-'}), "
                             f"{len(d['levels'])} runs, errors {errs} of {reqs} measured requests, "
                             f"gpu1 slowdown in /health: {'/'.join(slow)}")
        out += [""] + notes
    text = "\n".join(out) + "\n"
    print(text)
    with open(os.path.join(rdir, "lb_summary.md"), "w") as fh:
        fh.write(text)


if __name__ == "__main__":
    main()
