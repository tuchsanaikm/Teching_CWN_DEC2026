#!/usr/bin/env python3
"""mix_short vs mix_long: does Least Connections still spread the work evenly over the 4 replicas
when 20 % of the questions ask for a long answer?   -> results/report_mix.md
usage: python3 code/report_mix.py"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
TTFT_MAX, STD_SPEED = 2.0, 15.0


def load(name):
    with open(os.path.join(RES, name + ".json")) as f:
        return json.load(f)


def pct(xs, p):
    if not xs:
        return None
    s = sorted(xs)
    k = (len(s) - 1) * p / 100.0
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def f(v, p="%.3f"):
    return "-" if v is None else p % v


dp = load("dp")
single = next(l for l in dp["levels"] if l["users"] == 1 and not l.get("discarded"))["speed_p50_tok_s"]
fast_speed = single / 2.0
cap_std = dp["capacity"]["users"]
runs = {n: load(n) for n in ("mix_short", "mix_long")}
out = []
w = out.append

w("# Answers of different length: does Least Connections still share the work evenly? (Data Parallel, cap 256)\n")
w("N = %d users = 80 %% of the Standard capacity of dp (%d). One level, 90 s, the first 15 s not counted."
  % (runs["mix_short"]["levels"][0]["users"], cap_std))
w("Standard: TTFT p95 <= %.0f s, speed p5 >= %.0f tok/s, errors < 1 %%.  Fast: speed p5 >= %.2f tok/s "
  "(half of one user alone, dp N=1: %.2f tok/s).\n" % (TTFT_MAX, STD_SPEED, fast_speed, single))


def level_of(run):
    s = run["levels"][0]
    ok_base = s["ttft_p95_s"] <= TTFT_MAX and s["error_pct"] < 1.0
    std = ok_base and s["speed_p5_tok_s"] >= STD_SPEED
    fast = ok_base and s["speed_p5_tok_s"] >= fast_speed
    return s, std, fast


w("## The two rounds\n")
w("| round | long-answer questions | TTFT p95 s | speed p50 / p5 tok/s | throughput tok/s | questions/s | tokens per answer (mean) | errors | Standard | Fast | passes |")
w("|---|---|---|---|---|---|---|---|---|---|---|")
for name, run in runs.items():
    s, std, fast = level_of(run)
    w("| %s | %.0f %% asked (%d of %d finished) | %.3f | %.1f / %.1f | %.0f | %.1f | %.0f | %d (%.2f %%) | %s | %s | %s |" % (
        name, run["settings"]["long_pct"], s["long_answer_questions"], s["questions_done"], s["ttft_p95_s"],
        s["speed_p50_tok_s"], s["speed_p5_tok_s"], s["throughput_tok_s"], s["questions_per_s"], s["tokens_out_mean"],
        s["errors"], s["error_pct"], "pass" if std else "FAIL", "pass" if fast else "FAIL",
        "Fast + Standard" if fast else ("Standard only" if std else "none")))
w("")

summary = {}
for name, run in runs.items():
    s = run["levels"][0]
    w0, w1 = s["window_s"]
    reqs = [r for r in run.get("requests", []) if r["err"] is None and w0 <= r["t_end"] < w1]
    firsts = [r for r in run.get("requests", []) if r.get("t_first") is not None and w0 <= r["t_first"] < w1]
    w("## %s — per replica\n" % name)
    w("| replica | machine | questions received | share % | of them long | working on: mean / max | waiting mean | speed p50 tok/s | TTFT p50 s | TTFT p95 s | tokens/s |")
    w("|---|---|---|---|---|---|---|---|---|---|---|")
    for rep, b in s["replicas"].items():
        nlong = sum(1 for r in reqs if r["replica"] == rep and r.get("long"))
        w("| %s | %s | %d | %.1f | %d | %.1f / %d | %.1f | %.1f | %.3f | %.3f | %.0f |" % (
            rep, "1" if rep.startswith("n1") else "2", b["questions_done"], b["share_pct"], nlong, b["running_mean"], b["running_max"],
            b["waiting_mean"], b["speed_p50_tok_s"], b["ttft_p50_s"], b["ttft_p95_s"], b["throughput_tok_s"]))
    w("")
    # spread of the work in progress
    means = {rep: b["running_mean"] for rep, b in s["replicas"].items()}
    hi, lo = max(means, key=means.get), min(means, key=means.get)
    series = {rep: dict(zip(b["per_second"]["t"], b["per_second"]["running"])) for rep, b in s["replicas"].items()}
    common = sorted(set.intersection(*[set(v) for v in series.values()]))
    gaps = [max(series[r][t] for r in series) - min(series[r][t] for r in series) for t in common]
    q = {rep: b["questions_done"] for rep, b in s["replicas"].items()}
    qhi, qlo = max(q, key=q.get), min(q, key=q.get)
    w("- work in progress (mean): most %s %.1f, least %s %.1f -> difference **%.1f questions** (%.1f %% of the mean %.1f)" % (
        hi, means[hi], lo, means[lo], means[hi] - means[lo], 100.0 * (means[hi] - means[lo]) / (sum(means.values()) / 4), sum(means.values()) / 4))
    w("- same second, most vs least busy replica (%d seconds): mean gap %.1f, p95 %.1f, max %d questions" % (
        len(gaps), sum(gaps) / len(gaps), pct(gaps, 95), max(gaps)))
    w("- questions received: most %s %d, least %s %d -> difference %d (%.1f %% of the mean)" % (
        qhi, q[qhi], qlo, q[qlo], q[qhi] - q[qlo], 100.0 * (q[qhi] - q[qlo]) / (sum(q.values()) / 4)))
    m = {}
    for mach in ("n1", "n2"):
        tt = [r["ttft"] for r in firsts if (r["replica"] or "").startswith(mach)]
        sp = [r["speed"] for r in reqs if (r["replica"] or "").startswith(mach) and r["speed"] is not None]
        m[mach] = (pct(tt, 50), pct(tt, 95), pct(sp, 50), len(tt))
    w("- TTFT machine 1 (same machine as NGINX): p50 %.3f s, p95 %.3f s (%d questions) | machine 2 (over the internet): p50 %.3f s, p95 %.3f s (%d questions) "
      "-> machine 2 is %+.0f ms at p50, %+.0f ms at p95" % (m["n1"][0], m["n1"][1], m["n1"][3], m["n2"][0], m["n2"][1], m["n2"][3],
                                                       1000 * (m["n2"][0] - m["n1"][0]), 1000 * (m["n2"][1] - m["n1"][1])))
    w("- speed p50: machine 1 %.1f tok/s, machine 2 %.1f tok/s" % (m["n1"][2], m["n2"][2]))
    kinds = {}
    for kind, sel in (("short", 0), ("long", 1)):
        rr = [r for r in reqs if int(r.get("long", 0)) == sel]
        if rr:
            sp = [r["speed"] for r in rr if r["speed"] is not None]
            kinds[kind] = {"n": len(rr), "tok": sum(r["n_out"] for r in rr) / len(rr), "total": pct([r["total"] for r in rr], 50),
                           "sp50": pct(sp, 50), "sp5": pct(sp, 5), "tokens": sum(r["n_out"] for r in rr)}
    if len(kinds) == 2:
        tot_tok = kinds["short"]["tokens"] + kinds["long"]["tokens"]
        tot_time = sum(r["total"] for r in reqs)
        long_time = sum(r["total"] for r in reqs if r.get("long"))
        w("- short answers: %d questions, %.0f tokens each, %.1f s each, speed p50 %.1f / p5 %.1f tok/s" % (
            kinds["short"]["n"], kinds["short"]["tok"], kinds["short"]["total"], kinds["short"]["sp50"], kinds["short"]["sp5"]))
        w("- long answers: %d questions (%.0f %% of the finished ones), %.0f tokens each, %.1f s each, speed p50 %.1f / p5 %.1f tok/s "
          "-> %.0f %% of all answer tokens, %.0f %% of the users' time" % (
              kinds["long"]["n"], 100.0 * kinds["long"]["n"] / len(reqs), kinds["long"]["tok"], kinds["long"]["total"],
              kinds["long"]["sp50"], kinds["long"]["sp5"], 100.0 * kinds["long"]["tokens"] / tot_tok, 100.0 * long_time / tot_time))
    w("")
    summary[name] = {"running_gap": means[hi] - means[lo], "ttft": m}

with open(os.path.join(RES, "report_mix.md"), "w") as fh:
    fh.write("\n".join(out) + "\n")
print("\n".join(out))
