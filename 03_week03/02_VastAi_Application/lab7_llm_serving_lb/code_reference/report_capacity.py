#!/usr/bin/env python3
"""Tables for the Data Parallel capacity measurement: results/seq.json, dp.json, dp_fast.json -> results/report_capacity.md

  seq     : 4 replicas, 1 question at a time each (cap 1)        limits "Standard"
  dp      : 4 replicas, Continuous Batching (cap 256 each)       limits "Standard"
  dp_fast : the same system as dp                                 limits "Fast" (speed p5 >= half of one user alone)
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")


def load(name):
    p = os.path.join(RES, name + ".json")
    return json.load(open(p)) if os.path.exists(p) else None


def f(v, p="%.2f"):
    return "-" if v is None else p % v


def counted(d):
    """Measurements that count (not the ones thrown away because the load generator's CPU was full)."""
    return [l for l in d["levels"] if not l.get("discarded")]


def final_per_n(d):
    last = {}
    for l in counted(d):
        last[l["users"]] = l
    return [last[n] for n in sorted(last)]


def waiting(l):
    return sum((r.get("waiting_mean") or 0.0) for r in l["replicas"].values())


def gpu_util(l):
    g = [v["util_mean_pct"] for v in l["gpus"].values()]
    return sum(g) / len(g) if g else None


def cpu_txt(l):
    c = l.get("cpu") or {}
    g = lambda k, m="mean_pct_of_core": (c.get(k) or {}).get(m)
    return "%s / %s" % (f(g("loadgen_busiest_proc"), "%.0f"), f(g("nginx_busiest_proc"), "%.0f"))


def cap_txt(d):
    c = d["capacity"]
    if c["bound"] == "=":
        return "%d" % c["users"]
    return (">= %s" % c["users"]) if c["bound"] == ">=" else ("< %s" % c["below"])


def main():
    seq, dp, fast = load("seq"), load("dp"), load("dp_fast")
    out = []
    single = None
    if dp:
        n1 = [l for l in final_per_n(dp) if l["users"] == 1]
        single = n1[0]["speed_p50_tok_s"] if n1 else None
    fast_min = fast["limits"]["speed_p5_min_tok_s"] if fast else (single / 2 if single else None)

    if seq:
        out += ["## seq — 4 replicas, one question at a time (cap 1 per replica), Standard", "",
                "| N | phase | TTFT p50 s | TTFT p95 s | speed p5 tok/s | throughput tok/s | waiting in queue (mean, all replicas) | Standard | CPU busiest loadgen proc / nginx worker % |",
                "|---|---|---|---|---|---|---|---|---|"]
        for l in final_per_n(seq):
            out.append("| %d | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                l["users"], l["phase"], f(l["ttft_p50_s"], "%.3f"), f(l["ttft_p95_s"], "%.3f"), f(l["speed_p5_tok_s"], "%.1f"),
                f(l["throughput_tok_s"], "%.0f"), f(waiting(l), "%.1f"), "pass" if l["pass"] else "FAIL", cpu_txt(l)))
        out += ["", "capacity Standard (seq): **%s**" % cap_txt(seq), ""]

    if dp:
        allv = {l["users"]: l for l in final_per_n(dp)}
        fv = {l["users"]: l for l in final_per_n(fast)} if fast else {}
        for n, l in fv.items():
            allv.setdefault(n, l)
        out += ["## dp — 4 replicas, Continuous Batching (cap 256 per replica)", "",
                "single-user speed (dp, N=1, p50): %s tok/s -> Fast limit: speed p5 >= %s tok/s" % (f(single), f(fast_min)), "",
                "| N | measured in | TTFT p95 s | speed p50 tok/s | speed p5 tok/s | p5 as %% of single user | throughput tok/s | GPU util %% (mean of 4) | waiting (mean) | Standard | Fast | CPU busiest loadgen proc / nginx worker %% | loadgen procs |".replace("%%", "%"),
                "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        dpn = {l["users"] for l in final_per_n(dp)}
        for n in sorted(allv):
            l = allv[n]
            std = ("pass" if l["pass"] else "FAIL") if n in dpn else (
                "pass" if (l["ttft_p95_s"] <= 2.0 and l["speed_p5_tok_s"] >= 15 and l["error_pct"] < 1) else "FAIL")
            fl = fv.get(n)
            if fl is not None:
                fst = "pass" if fl["pass"] else "FAIL"
            elif fast_min and l["speed_p5_tok_s"] is not None:
                fst = "pass" if (l["ttft_p95_s"] <= 2.0 and l["speed_p5_tok_s"] >= fast_min and l["error_pct"] < 1) else "FAIL"
            else:
                fst = "-"
            out.append("| %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %d |" % (
                n, ("dp " + l["phase"]) if n in dpn else ("dp_fast " + l["phase"]), f(l["ttft_p95_s"], "%.3f"),
                f(l["speed_p50_tok_s"], "%.1f"), f(l["speed_p5_tok_s"], "%.1f"),
                f(100.0 * l["speed_p5_tok_s"] / single if single and l["speed_p5_tok_s"] else None, "%.0f"),
                f(l["throughput_tok_s"], "%.0f"), f(gpu_util(l), "%.0f"), f(waiting(l), "%.1f"), std, fst, cpu_txt(l), l["processes"]))
        out += ["", "capacity Standard (dp): **%s**" % cap_txt(dp)]
        if fast:
            out += ["capacity Fast (dp_fast): **%s**" % cap_txt(fast)]
        out += [""]

    if seq and dp:
        tmax = lambda d: max(l["throughput_tok_s"] for l in counted(d))
        ts, td = tmax(seq), max(tmax(dp), tmax(fast) if fast else 0)
        cs, cd = seq["capacity"].get("users"), dp["capacity"].get("users")
        # Fast for seq: judged from seq's own levels with the Fast limit
        seq_fast = max([l["users"] for l in final_per_n(seq) if l["ttft_p95_s"] is not None and l["ttft_p95_s"] <= 2.0
                        and l["speed_p5_tok_s"] >= fast_min and l["error_pct"] < 1] or [0]) if fast_min else None
        cf = fast["capacity"].get("users") if fast else None
        x = lambda a, b: "-" if not a or not b else "%.1fx" % (float(b) / a)
        out += ["## Comparison", "",
                "| | one at a time (seq) | Continuous Batching (dp) | times |", "|---|---|---|---|",
                "| capacity Standard (users) | %s | %s | %s |" % (cap_txt(seq), cap_txt(dp), x(cs, cd)),
                "| capacity Fast (users) | %s | %s | %s |" % (seq_fast, cap_txt(fast) if fast else "-", x(seq_fast, cf)),
                "| highest throughput (tok/s) | %.0f | %.0f | %s |" % (ts, td, x(ts, td)), ""]

    out += ["## Estimates: predicted (straight line between last pass and first fail) vs measured", "",
            "| run | round | between N | line: N at TTFT limit | line: N at speed limit | method | measured N | predicted TTFT p95 / speed p5 | measured TTFT p95 / speed p5 | result | gap after (allowed) |",
            "|---|---|---|---|---|---|---|---|---|---|---|"]
    def inside(e, k):                       # a crossing outside the two measured points is not an estimate
        v = e[k]
        return f(v, "%.1f") if v is not None and e["between"][0] <= v <= e["between"][1] else "not between"
    for d in (seq, dp, fast):
        if not d:
            continue
        for e in d.get("estimates", []):
            if e["round"] == "final":
                out.append("| %s | final | %d-%d | %s | %s | line | - | - | - | capacity %s (line says %s) | - |" % (
                    d["name"], e["between"][0], e["between"][1], inside(e, "n_at_ttft_limit"), inside(e, "n_at_speed_limit"),
                    cap_txt(d), f(e["estimate_n"], "%.1f")))
                continue
            out.append("| %s | %s | %d-%d | %s | %s | %s | %d | %s s / %s | %s s / %s | %s | %d (%d) |" % (
                d["name"], e["round"], e["between"][0], e["between"][1], inside(e, "n_at_ttft_limit"),
                inside(e, "n_at_speed_limit"), e["method"], e["measure_n"], f(e.get("predicted_ttft_p95_s"), "%.3f"),
                f(e.get("predicted_speed_p5_tok_s"), "%.1f"), f(e["measured_ttft_p95_s"], "%.3f"),
                f(e["measured_speed_p5_tok_s"], "%.1f"), "pass" if e["measured_pass"] else "FAIL", e["gap_after"], e["gap_allowed"]))
    out += ["", "## Spread over the 4 replicas at the capacity level", "",
            "| run | N | n1-gpu0 | n1-gpu1 | n2-gpu0 | n2-gpu1 | questions (window) |", "|---|---|---|---|---|---|---|"]
    for d in (seq, dp, fast):
        if not d or d["capacity"].get("bound") != "=":
            continue
        l = [x for x in final_per_n(d) if x["users"] == d["capacity"]["users"]][0]
        r = l["replicas"]
        out.append("| %s | %d | %s | %d |" % (d["name"], l["users"], " | ".join(
            "%s%% (%d q, run %s)" % (f(v["share_pct"], "%.1f"), v["questions_done"], f(v.get("running_mean"), "%.1f"))
            for v in r.values()), l["questions_done"]))
    disc = [(d["name"], l) for d in (seq, dp, fast) if d for l in d["levels"] if l.get("discarded") or l.get("cpu_full")]
    out += ["", "## CPU of the load generator and NGINX", ""]
    if disc:
        for name, l in disc:
            out.append("- %s N=%d (%d procs): %s" % (name, l["users"], l["processes"], l.get("discarded") or l.get("cpu_full")))
    else:
        out.append("- no level had a load-generator process or an NGINX worker above the 'full' mark (80 % of a core, mean)")
    txt = "\n".join(out) + "\n"
    open(os.path.join(RES, "report_capacity.md"), "w").write(txt)
    sys.stdout.write(txt)


if __name__ == "__main__":
    main()
