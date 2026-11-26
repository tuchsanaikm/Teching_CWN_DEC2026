#!/usr/bin/env python3
"""Data Parallel vs Model Parallel on the same 4 GPUs -> results/report_mp.md

  dp / dp_fast : 4 replicas, 1 GPU each (cap 256 each)                    results/dp.json, dp_fast.json
  mp / mp_fast : 2 replicas, 1 per machine, Tensor Parallelism over 2 GPUs (cap 512 each)   results/mp.json, mp_fast.json
  mp_n1        : Model Parallel, 1 user through NGINX                     results/mp_n1.json
  precheck_replicas(.json / _mp.json) : 1 user straight to every replica
  vram_<tag>.json : nvidia-smi memory.used per GPU (code/gpu_mem.sh)
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")


def load(name):
    p = os.path.join(RES, name + ".json")
    return json.load(open(p)) if os.path.exists(p) else None


def f(v, p="%.1f"):
    return "-" if v is None else p % v


def counted(d):
    return [l for l in d["levels"] if not l.get("discarded")]


def final_per_n(d):
    last = {}
    for l in counted(d):
        last[l["users"]] = l
    return last


def gpu_util(l):
    g = [v["util_mean_pct"] for v in l["gpus"].values()]
    return sum(g) / len(g) if g else None


def waiting(l):
    return sum((r.get("waiting_mean") or 0.0) for r in l["replicas"].values())


def cap(d):
    c = d["capacity"]
    if c["bound"] == "=":
        return c["users"], "%d" % c["users"]
    if c["bound"] == ">=":
        return c["users"], ">= %s" % c["users"]
    return None, "< %s" % c["below"]


def vram(tag):
    v = load("vram_" + tag)
    if not v:
        return None, "-"
    m = [g["memory_used_mib"] for g in v["gpus"].values()]
    return sum(m) / len(m), "%.1f GB (%d-%d MiB)" % (sum(m) / len(m) / 1024.0, min(m), max(m))


def times(a, b):
    return "-" if not a or not b else "%.2fx" % (float(b) / a)


def main():
    dp, dpf, mp, mpf, mp1 = load("dp"), load("dp_fast"), load("mp"), load("mp_fast"), load("mp_n1")
    pre_dp, pre_mp = load("precheck_replicas"), load("precheck_replicas_mp")
    out = ["# Data Parallel vs Model Parallel (same 4 GPUs, same load generator, NGINX Least Connections)", ""]

    # ---- 1 user straight to each replica
    out += ["## 1 user straight to each replica (5 questions, not through NGINX)", "",
            "| system | replica | TTFT mean s | TTFT median s | tokens/s mean | tokens/s min-max |", "|---|---|---|---|---|---|"]
    means = {}
    for tag, d in (("Data Parallel", pre_dp), ("Model Parallel", pre_mp)):
        if not d:
            continue
        for r in d["replicas"]:
            out.append("| %s | %s | %.4f | %.4f | %.2f | %.2f-%.2f |" % (tag, r["replica"], r["ttft_s_mean"], r["ttft_s_median"],
                       r["tokens_per_s_mean"], r["tokens_per_s_min"], r["tokens_per_s_max"]))
        n = len(d["replicas"])
        means[tag] = (sum(r["ttft_s_mean"] for r in d["replicas"]) / n, sum(r["tokens_per_s_mean"] for r in d["replicas"]) / n)
    if len(means) == 2:
        a, b = means["Data Parallel"], means["Model Parallel"]
        out += ["", "mean of the replicas: Data Parallel TTFT %.4f s, %.2f tok/s; Model Parallel TTFT %.4f s, %.2f tok/s "
                "-> Model Parallel TTFT %s, tokens/s %s of Data Parallel" % (a[0], a[1], b[0], b[1], times(a[0], b[0]), times(a[1], b[1]))]
        for m in ("machine 1", "machine 2"):          # the same machine: no network difference in the TTFT
            x = [r for r in pre_dp["replicas"] if r["machine"] == m]
            y = [r for r in pre_mp["replicas"] if r["machine"] == m]
            if x and y:
                xt, xs = sum(r["ttft_s_mean"] for r in x) / len(x), sum(r["tokens_per_s_mean"] for r in x) / len(x)
                out.append("- %s: TTFT %.4f -> %.4f s (%s), tokens/s %.2f -> %.2f (%s)" % (
                    m, xt, y[0]["ttft_s_mean"], times(xt, y[0]["ttft_s_mean"]), xs, y[0]["tokens_per_s_mean"], times(xs, y[0]["tokens_per_s_mean"])))
    out.append("")

    # ---- levels of mp
    single_dp = final_per_n(dp)[1]["speed_p50_tok_s"]
    single_mp = mp1["levels"][0]["speed_p50_tok_s"] if mp1 else None
    fast_min = (mpf or dpf)["limits"]["speed_p5_min_tok_s"]
    for title, a, b, names in (("dp — 4 replicas x 1 GPU (cap 256 each)", dp, dpf, ("dp", "dp_fast")),
                               ("mp — 2 replicas x 2 GPUs, Tensor Parallelism (cap 512 each)", mp, mpf, ("mp", "mp_fast"))):
        if not a:
            continue
        allv = dict(final_per_n(a))
        src = {n: names[0] for n in allv}
        if b:
            for n, l in final_per_n(b).items():
                if l.get("phase") != "reused":
                    allv[n] = l
                    src[n] = names[1]
        if a is mp and mp1:
            allv.setdefault(1, mp1["levels"][0])
            src.setdefault(1, "mp_n1")
        out += ["## " + title, "",
                "| N | measured in | TTFT p95 s | speed p50 tok/s | speed p5 tok/s | throughput tok/s | error %% | GPU util %% (mean of 4) | running per replica (mean) | waiting (mean, all) | Standard | Fast (p5 >= %.2f) |" % fast_min,
                "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for n in sorted(allv):
            l = allv[n]
            ok = lambda lim: "pass" if (l["ttft_p95_s"] is not None and l["ttft_p95_s"] <= 2.0 and l["speed_p5_tok_s"] is not None
                                        and l["speed_p5_tok_s"] >= lim and l["error_pct"] < 1) else "FAIL"
            run = "/".join(f(r.get("running_mean"), "%.0f") for r in l["replicas"].values())
            out.append("| %d | %s %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                n, src[n], l.get("phase", "single"), f(l["ttft_p95_s"], "%.3f"), f(l["speed_p50_tok_s"]), f(l["speed_p5_tok_s"]),
                f(l["throughput_tok_s"], "%.0f"), f(l["error_pct"], "%.2f"), f(gpu_util(l), "%.0f"), run, f(waiting(l)), ok(15.0), ok(fast_min)))
        out += ["", "capacity Standard (%s): **%s**" % (names[0], cap(a)[1])]
        if b:
            out += ["capacity Fast (%s): **%s**" % (names[1], cap(b)[1])]
        out.append("")

    # ---- summary table
    def row(a, b, single, tag):
        tmax = max([l["throughput_tok_s"] for l in counted(a)] + ([l["throughput_tok_s"] for l in counted(b)] if b else []))
        la = final_per_n(a).get(cap(a)[0])
        lb = final_per_n(b).get(cap(b)[0]) if b else None
        vm, vt = vram(tag)
        busy = [gpu_util(l) for l in counted(a) if l["users"] >= 32 and gpu_util(l) is not None]
        return {"replicas": len(a["target"]["replicas"]), "single": single, "std": cap(a), "fast": cap(b) if b else (None, "-"),
                "tmax": tmax, "vram": vm, "vram_txt": vt, "util_std": gpu_util(la) if la else None,
                "util_fast": gpu_util(lb) if lb else None, "util_1": None,
                "util_min_loaded": min(busy) if busy else None, "util_max_loaded": max(busy) if busy else None}
    D = row(dp, dpf, single_dp, "dp_load")
    M = row(mp, mpf, single_mp, "mp_load")
    D["util_1"] = gpu_util(final_per_n(dp)[1])
    M["util_1"] = gpu_util(mp1["levels"][0]) if mp1 else None
    util = lambda r: "%s %% at Standard capacity, %s %% at Fast capacity (1 user: %s %%)" % (f(r["util_std"], "%.0f"), f(r["util_fast"], "%.0f"), f(r["util_1"], "%.0f"))
    out += ["## Summary", "",
            "| | replicas | 1 user speed tok/s (p50, through NGINX) | capacity Standard | capacity Fast | highest throughput tok/s | VRAM used per GPU (under load) | GPU busy |",
            "|---|---|---|---|---|---|---|---|"]
    for name, r in (("Data Parallel", D), ("Model Parallel", M)):
        out.append("| %s | %d | %s | %s | %s | %.0f | %s | %s |" % (name, r["replicas"], f(r["single"], "%.2f"), r["std"][1], r["fast"][1],
                                                              r["tmax"], r["vram_txt"], util(r)))
    out.append("| Model Parallel / Data Parallel | %s | %s | %s | %s | %s | %s | %s (at Standard capacity) |" % (
        times(D["replicas"], M["replicas"]), times(D["single"], M["single"]), times(D["std"][0], M["std"][0]),
        times(D["fast"][0], M["fast"][0]), times(D["tmax"], M["tmax"]), times(D["vram"], M["vram"]), times(D["util_std"], M["util_std"])))
    out.append("")

    # ---- spread over the 2 replicas
    out += ["## Model Parallel: spread of the questions over the 2 replicas", "",
            "| run | N | " + " | ".join(mp["target"]["replicas"]) + " | questions (window) |", "|---|---|" + "---|" * (len(mp["target"]["replicas"]) + 1)]
    rows = [("mp_n1", mp1["levels"][0])] if mp1 else []
    rows += [("mp", l) for n, l in sorted(final_per_n(mp).items())]
    if mpf:
        rows += [("mp_fast", l) for n, l in sorted(final_per_n(mpf).items()) if l.get("phase") != "reused"]
    worst = 0.0
    for name, l in rows:
        sh = [v["share_pct"] for v in l["replicas"].values()]
        if l["users"] > 1:
            worst = max(worst, max(sh) - min(sh))
        out.append("| %s | %d | %s | %d |" % (name, l["users"], " | ".join(
            "%s%% (%d q, run %s, wait %s)" % (f(v["share_pct"]), v["questions_done"], f(v.get("running_mean")), f(v.get("waiting_mean")))
            for v in l["replicas"].values()), l["questions_done"]))
    out += ["", "largest difference between the two replicas' shares (N > 1): %.1f percentage points" % worst, ""]

    disc = [(d["name"], l) for d in (mp, mpf) if d for l in d["levels"] if l.get("discarded") or l.get("cpu_full")]
    out += ["## CPU of the load generator and NGINX (Model Parallel runs)", ""]
    out += ["- %s N=%d (%d procs): %s" % (n, l["users"], l["processes"], l.get("discarded") or l.get("cpu_full")) for n, l in disc] or \
           ["- no level had a load-generator process or an NGINX worker above the 'full' mark (80 % of a core, mean)"]
    txt = "\n".join(out) + "\n"
    open(os.path.join(RES, "report_mp.md"), "w").write(txt)
    sys.stdout.write(txt)


if __name__ == "__main__":
    main()
