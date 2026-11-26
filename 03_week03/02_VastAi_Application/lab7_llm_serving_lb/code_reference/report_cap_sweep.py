#!/usr/bin/env python3
"""Table of the cap sweep (results/cap_<cap>.json) -> results/report_cap_sweep.md
Limits: Standard = TTFT p95 <= 2 s, speed p5 >= 15 tok/s, errors < 1 %;
        Fast     = same, but speed p5 >= half of the single-user speed (dp, N=1, p50)."""
import json, os, sys
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
caps = [int(c) for c in sys.argv[1:]] or [32, 64, 190, 256]
dp = json.load(open(os.path.join(R, "dp.json")))
single = next(l["speed_p50_tok_s"] for l in dp["levels"] if l["users"] == 1)
fast_min = single / 2
out = ["## Cap sweep — Data Parallel, 4 replicas, fixed N users, cap = questions one replica works on at once", ""]
rows = []
for c in caps:
    d = json.load(open(os.path.join(R, "cap_%d.json" % c)))
    l = d["levels"][0]
    reps = l["replicas"]
    run = sum(v["running_mean"] for v in reps.values()) / len(reps)
    wait = sum(v["waiting_mean"] for v in reps.values())
    base = l["ttft_p95_s"] is not None and l["ttft_p95_s"] <= 2.0 and l["error_pct"] < 1.0
    std = base and l["speed_p5_tok_s"] >= 15.0
    fast = base and l["speed_p5_tok_s"] >= fast_min
    why = []
    if l["ttft_p95_s"] > 2.0: why.append("TTFT p95")
    if l["speed_p5_tok_s"] < 15.0: why.append("speed p5 < 15")
    elif l["speed_p5_tok_s"] < fast_min: why.append("speed p5 < %.1f (Fast only)" % fast_min)
    if l["error_pct"] >= 1.0: why.append("errors")
    level = "Fast + Standard" if fast else "Standard" if std else "none"
    rows.append((c, l, run, wait, level, why))
N = rows[0][1]["users"]
out += ["N = %d users (1.5 x Standard capacity %d), window %.0f s after %.0f s warm-up; single-user speed %.2f tok/s -> Fast needs speed p5 >= %.2f"
        % (N, dp["capacity"]["users"], rows[0][1]["window_s"][1] - rows[0][1]["window_s"][0], rows[0][1]["warmup_s"], single, fast_min), "",
        "| cap / replica | running / replica (mean) | waiting, all replicas (mean) | TTFT p50 s | TTFT p95 s | speed p50 tok/s | speed p5 tok/s | throughput tok/s | answer total p50 / p95 s | questions done | error % | passes | fails on |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for c, l, run, wait, level, why in rows:
    out.append("| %d | %.1f | %.1f | %.3f | %.3f | %.1f | %.1f | %.0f | %.2f / %.2f | %d | %.2f | %s | %s |" % (
        c, run, wait, l["ttft_p50_s"], l["ttft_p95_s"], l["speed_p50_tok_s"], l["speed_p5_tok_s"], l["throughput_tok_s"],
        l["total_p50_s"], l["total_p95_s"], l["questions_done"], l["error_pct"], level, ", ".join(why) or "-"))
out += ["", "| cap | " + " | ".join(rows[0][1]["replicas"]) + " | busiest loadgen proc / nginx % of a core | still without a first token at the end |", "|---|---|---|---|---|---|---|"]
for c, l, run, wait, level, why in rows:
    out.append("| %d | " % c + " | ".join("run %.1f wait %.1f (%.1f%%)" % (v["running_mean"], v["waiting_mean"], v["share_pct"]) for v in l["replicas"].values())
               + " | %.0f / %.0f | %d |" % (l["cpu"]["loadgen_busiest_proc"]["mean_pct_of_core"], l["cpu"]["nginx"]["mean_pct_of_core"], l["open_at_end_without_first_token"]))
open(os.path.join(R, "report_cap_sweep.md"), "w").write("\n".join(out) + "\n")
print("\n".join(out))
