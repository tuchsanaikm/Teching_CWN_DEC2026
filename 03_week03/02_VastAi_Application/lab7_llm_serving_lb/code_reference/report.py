#!/usr/bin/env python3
"""Final report of lab7: every result -> one metrics file, 7 charts and the design table.

  reads   results/{seq,dp,dp_fast,mp,mp_fast,mp_n1,cap_*,mix_short,mix_long,fail_node,fail_node_event}.json
  writes  results/metrics.json
          results/images/01..07_*.png          (English text)
          results/design_table.md

usage: python3 code/report.py          (needs matplotlib; ../../.pydeps is used when it is there)
"""
import glob, json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
IMG = os.path.join(RES, "images")
_deps = os.path.abspath(os.path.join(HERE, "..", "..", ".pydeps"))
if os.path.isdir(_deps) and _deps not in sys.path:
    sys.path.insert(0, _deps)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TTFT_MAX, STD_SPEED, ERR_MAX = 2.0, 15.0, 1.0
GPUS = 4                                   # every measurement used the same 4 GPUs (2 machines x 2)
TARGET_USERS = (500, 1000, 2000)

# colours: one per entity, the same in every chart
C_DP, C_MP, C_SEQ = "#2a78d6", "#eb6834", "#1baf7a"
C_REP = {"n1-gpu0": "#2a78d6", "n1-gpu1": "#eb6834", "n2-gpu0": "#1baf7a", "n2-gpu1": "#eda100"}
C_M1, C_M2 = "#2a78d6", "#eb6834"          # machine 1 / machine 2
C_ERR = "#d03b3b"
INK, INK2, MUTED, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "font.size": 11, "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "text.color": INK, "xtick.color": INK2, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True, "lines.linewidth": 2.0, "lines.markersize": 6, "legend.frameon": False,
})


# ------------------------------------------------------------------ reading
def load(name):
    p = os.path.join(RES, name + ".json")
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def pct(xs, p):
    if not xs:
        return None
    s = sorted(xs)
    k = (len(s) - 1) * p / 100.0
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def rnd(v, n=3):
    return None if v is None else round(v, n)


def gpu_util(l):
    return mean([v.get("util_mean_pct") for v in (l.get("gpus") or {}).values()])


def level_row(l, source, fast_min):
    """the numbers of one measured level, the same fields for every run"""
    base = l["ttft_p95_s"] is not None and l["ttft_p95_s"] <= TTFT_MAX and l["error_pct"] < ERR_MAX and l["speed_p5_tok_s"] is not None
    reps = l.get("replicas") or {}
    return {
        "users": l["users"], "source": source, "phase": l.get("phase", "single"),
        "ttft_p50_s": l["ttft_p50_s"], "ttft_p95_s": l["ttft_p95_s"],
        "speed_p50_tok_s": l["speed_p50_tok_s"], "speed_p5_tok_s": l["speed_p5_tok_s"],
        "throughput_tok_s": l["throughput_tok_s"], "questions_per_s": l.get("questions_per_s"),
        "questions_done": l["questions_done"], "errors": l["errors"], "error_pct": l["error_pct"],
        "gpu_util_mean_pct": rnd(gpu_util(l), 1),
        "running_mean_per_replica": {k: v.get("running_mean") for k, v in reps.items()},
        "waiting_mean_all_replicas": rnd(sum((v.get("waiting_mean") or 0.0) for v in reps.values()), 2),
        "replica_share_pct": {k: v.get("share_pct") for k, v in reps.items()},
        "pass_standard": bool(base and l["speed_p5_tok_s"] >= STD_SPEED),
        "pass_fast": bool(base and fast_min is not None and l["speed_p5_tok_s"] >= fast_min),
    }


def curve(runs, fast_min):
    """runs = [(name, json)] in priority order (later wins); one row per N, the last measurement that counts.
    Levels another run only re-judged ('reused') are not measured again, so they do not replace the original."""
    rows = {}
    for name, d in runs:
        if not d:
            continue
        for l in d["levels"]:
            if l.get("discarded") or l.get("phase") == "reused":
                continue
            rows[l["users"]] = level_row(l, name, fast_min)
    return [rows[n] for n in sorted(rows)]


def cap_of(d):
    if not d:
        return None
    c = d["capacity"]
    return {"users": c.get("users"), "bound": c["bound"], "last_pass": c.get("last_pass"), "first_fail": c.get("first_fail"),
            "converged": c.get("converged"), "at_capacity": c.get("at_capacity"), "limits": d["limits"]}


# ------------------------------------------------------------------ metrics
def build_metrics():
    seq, dp, dpf, mp, mpf, mp1 = (load(n) for n in ("seq", "dp", "dp_fast", "mp", "mp_fast", "mp_n1"))
    single_dp = next(l for l in dp["levels"] if l["users"] == 1 and not l.get("discarded"))["speed_p50_tok_s"]
    fast_min = dpf["limits"]["speed_p5_min_tok_s"] if dpf else single_dp / 2.0
    M = {"what": "lab7 - shop-bot on 4 GPUs (2 machines x 2 RTX 3090), vLLM replicas behind NGINX Least Connections",
         "model": "Qwen/Qwen3-4B-Instruct-2507", "gpus": GPUS,
         "limits": {"standard": {"ttft_p95_max_s": TTFT_MAX, "speed_p5_min_tok_s": STD_SPEED, "max_error_pct": ERR_MAX},
                    "fast": {"ttft_p95_max_s": TTFT_MAX, "speed_p5_min_tok_s": fast_min, "max_error_pct": ERR_MAX,
                             "rule": "speed p5 >= half of the speed of one user alone on Data Parallel (dp N=1 p50 = %.2f tok/s)" % single_dp}},
         "single_user_speed_tok_s": {"dp": single_dp, "mp": mp1["levels"][0]["speed_p50_tok_s"] if mp1 else None},
         "runs": {}}
    R = M["runs"]
    R["seq"] = {"system": "Data Parallel, 4 replicas, one question at a time (cap 1)", "capacity": cap_of(seq),
                "levels": curve([("seq", seq)], fast_min)}
    R["dp"] = {"system": "Data Parallel, 4 replicas x 1 GPU, Continuous Batching (cap 256)", "capacity": cap_of(dp),
               "levels": curve([("dp", dp)], fast_min)}
    R["dp_fast"] = {"system": "same system as dp, judged with the Fast limit (dp levels reused + extra levels)",
                    "capacity": cap_of(dpf), "levels": curve([("dp", dp), ("dp_fast", dpf)], fast_min),
                    "levels_measured_here": sorted({l["users"] for l in dpf["levels"] if l.get("phase") != "reused"})}
    R["mp"] = {"system": "Model Parallel, 2 replicas x 2 GPUs, Tensor Parallelism (cap 512)", "capacity": cap_of(mp),
               "levels": curve([("mp", mp)], fast_min)}
    R["mp_fast"] = {"system": "same system as mp, judged with the Fast limit (mp levels reused + extra levels)",
                    "capacity": cap_of(mpf), "levels": curve([("mp_n1", mp1), ("mp", mp), ("mp_fast", mpf)], fast_min),
                    "levels_measured_here": sorted({l["users"] for l in mpf["levels"] if l.get("phase") != "reused"})}

    # cap sweep
    for p in sorted(glob.glob(os.path.join(RES, "cap_*.json")), key=lambda p: (not re.search(r"cap_\d+\.json$", p), int(re.sub(r"\D", "", os.path.basename(p)) or 0))):
        name = os.path.basename(p)[:-5]
        m = re.match(r"cap_(\d+)$", name)
        if not m:
            continue                         # cap_test = a try-out, not part of the sweep
        d = load(name)
        l = d["levels"][0]
        row = level_row(l, name, fast_min)
        row.update({"cap_per_replica": int(m.group(1)), "total_p50_s": l["total_p50_s"], "total_p95_s": l["total_p95_s"],
                    "running_mean_all_replicas": rnd(sum(v["running_mean"] for v in l["replicas"].values()), 1),
                    "open_at_end_without_first_token": l.get("open_at_end_without_first_token")})
        R[name] = row

    # mixed answer lengths
    for name in ("mix_short", "mix_long"):
        d = load(name)
        if not d:
            continue
        l = d["levels"][0]
        row = level_row(l, name, fast_min)
        reps = l["replicas"]
        run_mean = {k: v["running_mean"] for k, v in reps.items()}
        series = {k: dict(zip(v["per_second"]["t"], v["per_second"]["running"])) for k, v in reps.items()}
        common = sorted(set.intersection(*[set(s) for s in series.values()]))
        gaps = [max(series[k][t] for k in series) - min(series[k][t] for k in series) for t in common]
        row.update({"long_pct_asked": d["settings"]["long_pct"], "long_answer_questions": l["long_answer_questions"],
                    "tokens_out_mean": l["tokens_out_mean"],
                    "per_replica": {k: {"questions_done": v["questions_done"], "share_pct": v["share_pct"], "running_mean": v["running_mean"],
                                        "running_max": v["running_max"], "waiting_mean": v["waiting_mean"], "ttft_p95_s": v["ttft_p95_s"],
                                        "speed_p50_tok_s": v["speed_p50_tok_s"], "throughput_tok_s": v["throughput_tok_s"]}
                                    for k, v in reps.items()},
                    "running_mean_gap_most_vs_least": rnd(max(run_mean.values()) - min(run_mean.values()), 2),
                    "same_second_gap_mean": rnd(mean(gaps), 2), "same_second_gap_p95": rnd(pct(gaps, 95), 2), "same_second_gap_max": max(gaps),
                    "running_per_second": {"t": common, **{k: [series[k][t] for t in common] for k in series}}})
        R[name] = row

    # machine failure
    fn, ev = load("fail_node"), load("fail_node_event")
    if fn and ev:
        lv, rows, reqs = fn["levels"][0], fn["per_second"], fn["requests"]
        names = fn["target"]["replicas"]
        kill, dur, warm, dead = ev["kill_start_s"], lv["duration_s"], lv["warmup_s"], ev["node"]

        def phase(a, b):
            first = [r for r in reqs if r["t_first"] is not None and a <= r["t_first"] < b]
            done = [r for r in reqs if r["err"] is None and a <= r["t_end"] < b]
            errs = [r for r in reqs if r["err"] is not None and a <= r["t_end"] < b]
            sec = [r for r in rows if a <= r["t"] + 0.5 < b]
            sp = [r["speed"] for r in done if r["speed"] is not None]
            o = {"from_s": a, "to_s": b, "questions_done": len(done), "errors": len(errs),
                 "error_pct": rnd(100.0 * len(errs) / max(1, len(errs) + len(done)), 2),
                 "throughput_tok_s": rnd(sum(r["tokens"] for r in sec) / max(1, len(sec)), 1),
                 "speed_p50_tok_s": rnd(pct(sp, 50), 2), "speed_p5_tok_s": rnd(pct(sp, 5), 2),
                 "ttft_p50_s": rnd(pct([r["ttft"] for r in first], 50)), "ttft_p95_s": rnd(pct([r["ttft"] for r in first], 95)),
                 "ttft_max_s": rnd(max([r["ttft"] for r in first], default=None)),
                 "replicas_answering": sum(1 for n in names if any(r["replica"] == n for r in done))}
            ok = o["ttft_p95_s"] is not None and o["ttft_p95_s"] <= TTFT_MAX and o["error_pct"] < ERR_MAX
            o["pass_standard"] = bool(ok and o["speed_p5_tok_s"] >= STD_SPEED)
            o["pass_fast"] = bool(ok and o["speed_p5_tok_s"] >= fast_min)
            return o
        errs = [r for r in reqs if r["err"]]
        cut = [r for r in errs if r["t_send"] < kill and (r["replica"] or "").startswith(dead)]
        machines = sorted({n.split("-")[0] for n in names})
        R["fail_node"] = {
            "users": lv["users"], "duration_s": dur, "warmup_s": warm, "killed_machine": dead, "kill_at_s": kill,
            "before": phase(warm, kill), "after_all": phase(kill, dur), "after_settled": phase(int(kill) + 5.0, dur),
            "errors_total": len(errs), "errors_answer_cut_on_dead_machine": len(cut),
            "errors_sent_after_the_failure": sum(1 for r in errs if r["t_send"] >= kill),
            "users_hit": len({r["user"] for r in cut}),
            "passed_on_by_nginx": sum(1 for r in reqs if (r.get("tries") or 1) > 1),
            "per_second": {"t": [r["t"] for r in rows], "errors": [r["errors"] for r in rows],
                           "tokens_total": [r["tokens"] for r in rows],
                           **{"tokens_" + m: [sum(r["replicas"][n]["tokens"] for n in names if n.startswith(m)) for r in rows] for m in machines}}}

    # summary + design
    def tmax(*names):
        """highest throughput of any measurement that counts (also a repeated measurement of the same N)"""
        return max(l["throughput_tok_s"] for n in names for l in load(n)["levels"]
                   if not l.get("discarded") and l.get("phase") != "reused")
    seq_fast = max([l["users"] for l in R["seq"]["levels"] if l["pass_fast"]] or [0])
    S = {
        "seq": {"system": "Data Parallel, one question at a time", "replicas": 4, "capacity_standard": R["seq"]["capacity"]["users"],
                "capacity_fast": seq_fast, "capacity_fast_note": "judged from the seq levels with the Fast limit (no separate run)",
                "max_throughput_tok_s": tmax("seq")},
        "dp": {"system": "Data Parallel, Continuous Batching", "replicas": 4, "capacity_standard": R["dp"]["capacity"]["users"],
               "capacity_fast": R["dp_fast"]["capacity"]["users"], "max_throughput_tok_s": tmax("dp", "dp_fast")},
        "mp": {"system": "Model Parallel (Tensor Parallelism over 2 GPUs)", "replicas": 2, "capacity_standard": R["mp"]["capacity"]["users"],
               "capacity_fast": R["mp_fast"]["capacity"]["users"], "max_throughput_tok_s": tmax("mp", "mp_fast")},
    }
    M["summary"] = S
    D = {"gpus_measured": GPUS, "targets_users": list(TARGET_USERS), "systems": {},
         "note": "users per GPU = measured capacity of the 4-GPU system / 4; GPUs needed = ceil(users / users per GPU), "
                 "then rounded up to whole replicas (Model Parallel: 2 GPUs per replica). Only the 4-GPU capacities are measured."}
    for key, unit in (("seq", 1), ("dp", 1), ("mp", 2)):
        e = {"gpus_per_replica": unit}
        for lvl in ("standard", "fast"):
            cap = S[key]["capacity_" + lvl]
            per = cap / float(GPUS)
            need = {}
            for u in TARGET_USERS:
                g = int(math.ceil(u / per - 1e-9))
                need[str(u)] = {"gpus_exact": rnd(u / per, 2), "gpus": int(math.ceil(g / float(unit)) * unit)}
            e[lvl] = {"capacity_4gpu_measured": cap, "users_per_gpu": rnd(per, 2), "gpus_needed_calculated": need}
        D["systems"][key] = e
    M["design"] = D
    return M


# ------------------------------------------------------------------ charts
def hline(ax, y, text, x=0.995, va="bottom", outside=False):
    """limit line with its label: inside at the right end, or outside to the right of the plot"""
    ax.axhline(y, color=INK2, lw=1.2, ls=(0, (5, 3)), zorder=4 if outside else 1)
    if outside:
        ax.text(1.01, y, text, transform=ax.get_yaxis_transform(), ha="left", va="center", color=INK2, fontsize=9.5)
    else:
        ax.text(x, y, text + " ", transform=ax.get_yaxis_transform(), ha="right", va=va, color=INK2, fontsize=9.5)


def save(fig, name):
    os.makedirs(IMG, exist_ok=True)
    p = os.path.join(IMG, name)
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return p


def xy(rows, key):
    pts = [(r["users"], r[key]) for r in rows if r[key] is not None]
    return [p[0] for p in pts], [p[1] for p in pts]


def chart_speed(M):
    R, fast_min = M["runs"], M["limits"]["fast"]["speed_p5_min_tok_s"]
    fig, ax = plt.subplots(figsize=(10, 5.6))
    for key, col, lab in (("dp_fast", C_DP, "Data Parallel (4 replicas x 1 GPU)"), ("mp_fast", C_MP, "Model Parallel (2 replicas x 2 GPUs)")):
        x, y = xy(R[key]["levels"], "speed_p5_tok_s")
        ax.plot(x, y, "-o", color=col, label=lab, markeredgecolor=SURF, markeredgewidth=1.2, zorder=3)
    hline(ax, fast_min, "Fast limit: p5 >= %.1f tok/s" % fast_min)
    ax.axhline(STD_SPEED, color=INK2, lw=1.2, ls=(0, (5, 3)), zorder=1)      # label at the left end: the right end is under the curves
    ax.text(0.012, STD_SPEED, "Standard limit: p5 >= %.0f tok/s" % STD_SPEED, transform=ax.get_yaxis_transform(), ha="left",
            va="bottom", color=INK2, fontsize=9.5)
    for run, col, tag, dx, dy, ha in (("dp_fast", C_DP, "Fast", 8, 16, "left"), ("dp", C_DP, "Standard", 0, 20, "center"),
                                      ("mp_fast", C_MP, "Fast", -10, -20, "right"), ("mp", C_MP, "Standard", -6, -22, "right")):
        c = R[run]["capacity"]
        n, s = c["users"], c["at_capacity"]["speed_p5_tok_s"]
        ax.plot([n], [s], marker="D", ms=11, color=col, markeredgecolor=INK, markeredgewidth=1.3, ls="none", zorder=5)
        ax.annotate("%s capacity %d" % (tag, n), (n, s), xytext=(dx, dy), textcoords="offset points", fontsize=10, color=INK,
                    fontweight="bold", va="center", ha=ha)
    ax.plot([], [], marker="D", ms=9, color="none", markeredgecolor=INK, markeredgewidth=1.3, ls="none", label="capacity = largest N that passes")
    ax.set_xlabel("users at the same time (N)")
    ax.set_ylabel("speed per user, p5 (tokens/s)")
    ax.set_title("Speed per user (p5) vs number of users - Data Parallel vs Model Parallel")
    ax.set_xlim(0, 1060); ax.set_ylim(0, 125)
    ax.legend(loc="upper center")
    return save(fig, "01_speed_p5_vs_users.png")


def chart_throughput(M):
    R = M["runs"]
    fig, ax = plt.subplots(figsize=(10, 5.6))
    for key, col, lab, sk in (("dp_fast", C_DP, "Data Parallel, Continuous Batching", "dp"), ("mp_fast", C_MP, "Model Parallel", "mp"),
                              ("seq", C_SEQ, "Data Parallel, one question at a time", "seq")):
        x, y = xy(R[key]["levels"], "throughput_tok_s")
        top = M["summary"][sk]["max_throughput_tok_s"]       # highest of all measurements (a repeated N can be above the plotted one)
        ax.plot(x, y, "-o", color=col, label=lab, markeredgecolor=SURF, markeredgewidth=1.2, zorder=3)
        i = max(range(len(y)), key=lambda i: y[i])
        ax.annotate("highest %s tok/s" % format(int(round(top)), ","), (x[i], max(y[i], top)), xytext=(0, 9), textcoords="offset points",
                    ha="center", fontsize=10, fontweight="bold", color=INK)
    ax.set_xscale("log")
    ax.set_xticks([1, 4, 8, 16, 32, 64, 128, 256, 512, 1024]); ax.set_xticklabels(["1", "4", "8", "16", "32", "64", "128", "256", "512", "1024"])
    ax.minorticks_off()
    ax.set_xlabel("users at the same time (N, log scale)")
    ax.set_ylabel("throughput of the whole system (tokens/s)")
    ax.set_ylim(0, 13200)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: format(int(v), ",")))
    ax.set_title("Throughput vs number of users (same 4 GPUs)")
    ax.legend(loc="upper left")
    return save(fig, "02_throughput_vs_users.png")


def chart_ttft(M):
    R = M["runs"]
    fig, ax = plt.subplots(figsize=(10, 5.6))
    for key, col, lab in (("seq", C_SEQ, "one question at a time (cap 1 per replica)"), ("dp_fast", C_DP, "Continuous Batching (cap 256 per replica)")):
        x, y = xy(R[key]["levels"], "ttft_p95_s")
        ax.plot(x, y, "-o", color=col, label=lab, markeredgecolor=SURF, markeredgewidth=1.2, zorder=3)
    hline(ax, TTFT_MAX, "limit: TTFT p95 <= 2 s")
    s = R["seq"]["levels"]
    last = s[-1]
    ax.annotate("N=%d: %.1f s" % (last["users"], last["ttft_p95_s"]), (last["users"], last["ttft_p95_s"]), xytext=(8, 0),
                textcoords="offset points", va="center", fontsize=10, color=INK)
    d = R["dp_fast"]["levels"][-1]
    ax.annotate("N=%d: %.2f s" % (d["users"], d["ttft_p95_s"]), (d["users"], d["ttft_p95_s"]), xytext=(0, 9),
                textcoords="offset points", ha="center", fontsize=10, color=INK)
    c = R["seq"]["capacity"]["users"]
    ax.annotate("seq capacity N=%d" % c, (c, next(l["ttft_p95_s"] for l in s if l["users"] == c)), xytext=(-12, -4),
                textcoords="offset points", ha="right", va="center", fontsize=10, color=INK)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xticks([1, 4, 8, 16, 32, 64, 128, 256, 512, 1024]); ax.set_xticklabels(["1", "4", "8", "16", "32", "64", "128", "256", "512", "1024"])
    ax.set_yticks([0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10]); ax.set_yticklabels(["0.05", "0.1", "0.2", "0.5", "1", "2", "5", "10"])
    ax.minorticks_off()
    ax.set_xlim(0.8, 1500); ax.set_ylim(0.04, 12)
    ax.set_xlabel("users at the same time (N, log scale)")
    ax.set_ylabel("TTFT p95 (seconds, log scale)")
    ax.set_title("Time to first token (p95) vs number of users - Data Parallel, 4 replicas")
    ax.legend(loc="lower right")
    return save(fig, "03_ttft_p95_vs_users.png")


def chart_caps(M):
    R, fast_min = M["runs"], M["limits"]["fast"]["speed_p5_min_tok_s"]
    caps = sorted((v for k, v in R.items() if re.match(r"cap_\d+$", k)), key=lambda v: v["cap_per_replica"])
    labels = ["cap %d" % c["cap_per_replica"] for c in caps]
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 5.4))
    xs = range(len(caps))
    for ax, key, fmt in ((a, "ttft_p95_s", "%.2f s"), (b, "speed_p5_tok_s", "%.1f")):
        bars = ax.bar(xs, [c[key] for c in caps], width=0.56, color=C_DP, zorder=3)
        for r, c in zip(bars, caps):
            ax.text(r.get_x() + r.get_width() / 2, r.get_height(), fmt % c[key], ha="center", va="bottom", fontsize=10.5, fontweight="bold", zorder=6,
                    bbox=dict(facecolor=SURF, edgecolor="none", pad=1.0))
        ax.set_xticks(list(xs)); ax.set_xticklabels(labels)
        ax.grid(axis="x", visible=False)
        ax.set_xlabel("questions one replica works on at once (the rest wait in its queue)")
    hline(a, TTFT_MAX, "limit\n<= 2 s", outside=True)
    a.set_ylabel("TTFT p95 (seconds)"); a.set_title("TTFT p95  (lower is better)")
    a.set_ylim(0, max(c["ttft_p95_s"] for c in caps) * 1.15)
    hline(b, fast_min, "Fast\n>= %.1f" % fast_min, outside=True)
    hline(b, STD_SPEED, "Standard\n>= %.0f" % STD_SPEED, outside=True)
    b.set_ylabel("speed per user, p5 (tokens/s)"); b.set_title("Speed per user p5  (higher is better)")
    b.set_ylim(0, max(c["speed_p5_tok_s"] for c in caps) * 1.15)
    fig.suptitle("Four caps at N = %d users (1.5 x Standard capacity), Data Parallel\n"
                 "low cap: the speed stays high but users wait long for the first token; high cap: the answer starts soon but is slow"
                 % caps[0]["users"], x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.92), w_pad=5.0)
    return save(fig, "04_cap_sweep_ttft_and_speed.png")


def chart_capacity(M):
    S = M["summary"]
    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    w = 0.36
    groups = (("Standard", "capacity_standard"), ("Fast", "capacity_fast"))
    for i, (key, col, lab) in enumerate((("dp", C_DP, "Data Parallel (4 replicas x 1 GPU)"), ("mp", C_MP, "Model Parallel (2 replicas x 2 GPUs)"))):
        xs = [g + (i - 0.5) * (w + 0.03) for g in range(len(groups))]
        vals = [S[key][k] for _, k in groups]
        bars = ax.bar(xs, vals, width=w, color=col, label=lab, zorder=3)
        for r, v in zip(bars, vals):
            ax.text(r.get_x() + r.get_width() / 2, v, "%d" % v, ha="center", va="bottom", fontsize=12, fontweight="bold")
            ax.text(r.get_x() + r.get_width() / 2, v / 2.0, "%.1f\nper GPU" % (v / float(GPUS)), ha="center", va="center", fontsize=9.5, color="#ffffff")
    lim = M["limits"]
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels(["Standard\n(speed p5 >= %.0f tok/s, TTFT p95 <= 2 s)" % lim["standard"]["speed_p5_min_tok_s"],
                        "Fast\n(speed p5 >= %.1f tok/s, TTFT p95 <= 2 s)" % lim["fast"]["speed_p5_min_tok_s"]])
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("capacity: users at the same time")
    ax.set_ylim(0, S["dp"]["capacity_standard"] * 1.14)
    ax.set_title("Measured capacity on the same 4 GPUs")
    ax.legend(loc="upper right")
    return save(fig, "05_capacity_standard_fast.png")


def chart_mix(M):
    R = M["runs"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), sharey=True)
    lo = min(min(R[n]["running_per_second"][k]) for n in ("mix_short", "mix_long") for k in C_REP)
    hi = max(max(R[n]["running_per_second"][k]) for n in ("mix_short", "mix_long") for k in C_REP)
    for ax, name, ttl in zip(axes, ("mix_short", "mix_long"), ("mix_short: every answer short", "mix_long: 20 % of the questions ask for a long answer")):
        ps = R[name]["running_per_second"]
        for k, col in C_REP.items():
            ax.plot(ps["t"], ps[k], color=col, lw=1.6, label=k, zorder=3)
        ax.set_title(ttl)
        ax.set_xlabel("second of the run (first 15 s = warm-up, not shown)")
        ax.set_ylim(lo - 4, hi + 6)
        ax.text(0.01, 0.03, "mean per replica: %s\nsame-second gap most vs least busy: mean %.1f, max %d questions"
                % (" / ".join("%.1f" % R[name]["per_replica"][k]["running_mean"] for k in C_REP),
                   R[name]["same_second_gap_mean"], R[name]["same_second_gap_max"]),
                transform=ax.transAxes, fontsize=9.5, color=INK2, va="bottom")
    axes[0].set_ylabel("questions the replica is working on")
    axes[1].legend(loc="upper right", ncol=4, fontsize=9.5)
    fig.suptitle("Work in progress per replica, second by second (N = %d users, NGINX Least Connections) - y axis zoomed, does not start at 0"
                 % R["mix_short"]["users"], x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return save(fig, "06_mix_running_per_replica.png")


def chart_fail(M):
    F = M["runs"]["fail_node"]
    ps, kill = F["per_second"], F["kill_at_s"]
    t = [x + 0.5 for x in ps["t"]]
    fig, (a, b) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1.25]})
    a.stackplot(t, ps["tokens_n1"], ps["tokens_n2"], colors=[C_M1, C_M2], labels=["machine 1 (2 replicas, also runs NGINX)", "machine 2 (2 replicas) - killed"],
                edgecolor=SURF, linewidth=1.0, zorder=3)
    a.axvline(kill, color=INK, lw=1.4, ls=(0, (4, 3)), zorder=4)
    a.text(kill + 0.8, 0.97, "second %.0f: machine 2 fails (SIGKILL)" % kill, transform=a.get_xaxis_transform(), va="top", fontsize=10, color=INK)
    bf, af = F["before"], F["after_settled"]
    a.text(kill / 2.0, max(ps["tokens_total"]) + 250, "before: %s tok/s" % format(int(round(bf["throughput_tok_s"])), ","),
           ha="center", fontsize=10.5, fontweight="bold")
    a.text((kill + F["duration_s"]) / 2.0 + 4, max(ps["tokens_n1"]) + 350, "after: %s tok/s (%.0f %%), 2 replicas left"
           % (format(int(round(af["throughput_tok_s"])), ","), 100.0 * af["throughput_tok_s"] / bf["throughput_tok_s"]),
           ha="center", fontsize=10.5, fontweight="bold")
    a.set_ylabel("throughput (tokens/s)")
    a.set_ylim(0, max(ps["tokens_total"]) * 1.22)
    a.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: format(int(v), ",")))
    a.set_title("fail_node: throughput per second by machine (N = %d users, Data Parallel)" % F["users"])
    a.legend(loc="upper right", fontsize=9.5)
    b.bar(t, ps["errors"], width=0.8, color=C_ERR, zorder=3)
    b.axvline(kill, color=INK, lw=1.4, ls=(0, (4, 3)), zorder=4)
    imax = max(range(len(ps["errors"])), key=lambda i: ps["errors"][i])
    b.annotate("%d answers cut in the middle (all were streaming from machine 2);\n%d errors in every other second, %d errors among questions sent after the failure"
               % (ps["errors"][imax], sum(ps["errors"]) - ps["errors"][imax], F["errors_sent_after_the_failure"]),
               (t[imax], ps["errors"][imax]), xytext=(10, -4), textcoords="offset points", va="top", fontsize=10, color=INK)
    b.set_ylabel("errors per second")
    b.set_ylim(0, max(ps["errors"]) * 1.15 + 1)
    b.set_xlabel("second of the run")
    b.set_xlim(0, F["duration_s"])
    b.set_title("Errors per second (total %d)" % F["errors_total"], fontsize=11.5)
    fig.tight_layout()
    return save(fig, "07_fail_node_throughput_errors.png")


# ------------------------------------------------------------------ design table
def design_table(M):
    S, D, lim = M["summary"], M["design"], M["limits"]
    names = {"seq": "Data Parallel, one question at a time (cap 1)", "dp": "Data Parallel, Continuous Batching (cap 256)",
             "mp": "Model Parallel, Tensor Parallelism over 2 GPUs (cap 512)"}
    o = ["# Design table - how many GPUs for how many users", "",
         "Model %s on RTX 3090 24 GB, vLLM replicas behind NGINX Least Connections, short shop answers (about 86 tokens)." % M["model"],
         "",
         "- **Standard**: TTFT p95 <= %.0f s, speed per user p5 >= %.0f tok/s, errors < %.0f %%" % (TTFT_MAX, STD_SPEED, ERR_MAX),
         "- **Fast**: TTFT p95 <= %.0f s, speed per user p5 >= %.2f tok/s (half of one user alone: %.2f tok/s), errors < %.0f %%"
         % (TTFT_MAX, lim["fast"]["speed_p5_min_tok_s"], M["single_user_speed_tok_s"]["dp"], ERR_MAX),
         "- **[M] = measured** on the real 4-GPU system (2 machines x 2 GPUs).  **[C] = calculated** from the measured value.",
         "",
         "## 1. Summary of the three systems (4 GPUs) - all measured [M]", "",
         "| system | replicas | capacity Standard (users) | capacity Fast (users) | highest throughput (tok/s) |",
         "|---|---|---|---|---|"]
    for k in ("seq", "dp", "mp"):
        s = S[k]
        o.append("| %s | %d | %d | %d%s | %s |" % (names[k], s["replicas"], s["capacity_standard"], s["capacity_fast"],
                                                 " (a)" if k == "seq" else "", format(int(round(s["max_throughput_tok_s"])), ",")))
    o += ["", "(a) no separate Fast run for this system: its measured levels were judged with the Fast limit. Its limit is the wait "
              "for a free replica (TTFT), not the speed, so Standard and Fast give the same number.", "",
          "## 2. Users per GPU", "",
          "| system | level | capacity on 4 GPUs [M] | users per GPU [C] = capacity / 4 |", "|---|---|---|---|"]
    for k in ("dp", "mp", "seq"):
        for lvl in ("standard", "fast"):
            e = D["systems"][k][lvl]
            o.append("| %s | %s | %d | %s |" % (names[k], lvl.capitalize(), e["capacity_4gpu_measured"], ("%.2f" % e["users_per_gpu"]).rstrip("0").rstrip(".")))
    o += ["", "## 3. GPUs needed for 500, 1,000 and 2,000 users at the same time - all calculated [C]", "",
          "GPUs = users / (users per GPU), rounded up to a whole GPU; Model Parallel is rounded up to an even number "
          "(one replica = 2 GPUs). The exact quotient is in brackets.", "",
          "| system | level | users per GPU [C] | " + " | ".join("%s users [C]" % format(u, ",") for u in TARGET_USERS) + " |",
          "|---|---|---|" + "---|" * len(TARGET_USERS)]
    for k in ("dp", "mp", "seq"):
        for lvl in ("standard", "fast"):
            e = D["systems"][k][lvl]
            o.append("| %s | %s | %s | %s |" % (names[k], lvl.capitalize(), ("%.2f" % e["users_per_gpu"]).rstrip("0").rstrip("."),
                     " | ".join("**%d** (%.2f)" % (e["gpus_needed_calculated"][str(u)]["gpus"], e["gpus_needed_calculated"][str(u)]["gpus_exact"])
                                for u in TARGET_USERS)))
    dps, dpf = D["systems"]["dp"]["standard"], D["systems"]["dp"]["fast"]
    shares = list(next(l for l in M["runs"]["dp"]["levels"] if l["users"] == S["dp"]["capacity_standard"])["replica_share_pct"].values())
    o += ["", "## 4. Which cells are measured, which are calculated", "",
          "| cell | kind |", "|---|---|",
          "| capacity Standard / Fast of each system on 4 GPUs, highest throughput | measured [M] |",
          "| users per GPU | calculated [C]: measured capacity / 4 |",
          "| GPUs for 500 / 1,000 / 2,000 users | calculated [C]: users / users per GPU, rounded up |",
          "",
          "## 5. How far the calculated cells can be trusted", "",
          "- The calculation assumes that capacity grows in a straight line with the number of GPUs (each replica is independent, "
          "NGINX shares the work evenly). Measured support: on 4 replicas the shares were %.1f-%.1f %% each at the Standard capacity; "
          "with 2 of the 4 replicas (fail_node, N = %d) throughput fell to %.0f %% of the 4-replica value." % (
              min(shares), max(shares), M["runs"]["fail_node"]["users"], 100.0 * M["runs"]["fail_node"]["after_settled"]["throughput_tok_s"] / M["runs"]["fail_node"]["before"]["throughput_tok_s"]),
          "- Not measured beyond 4 GPUs: one NGINX and one load generator were enough for the levels measured here (up to N = %d), "
          "but 2,000 users on %d or more replicas were never run." % (
              max(l["users"] for l in M["runs"]["dp"]["levels"]), D["systems"]["dp"]["standard"]["gpus_needed_calculated"]["2000"]["gpus"]),
          "- 500 users is below the measured Standard capacity of the 4-GPU Data Parallel system (%d), so 4 GPUs are known to carry it; "
          "the table's %d GPUs for it is a calculated value." % (dps["capacity_4gpu_measured"], dps["gpus_needed_calculated"]["500"]["gpus"]),
          "- The numbers have no spare room: at exactly the capacity the speed p5 sits on the limit, and one failed machine out of two "
          "halves the capacity. A design that must survive one failed GPU/machine needs that many GPUs more.",
          "- Valid for this model, this GPU and these answer lengths. With %.0f %% long answers (mix_long) the same %d users got "
          "speed p5 %.1f instead of %.1f tok/s, so longer answers need more GPUs." % (
              M["runs"]["mix_long"]["long_pct_asked"], M["runs"]["mix_long"]["users"], M["runs"]["mix_long"]["speed_p5_tok_s"],
              M["runs"]["mix_short"]["speed_p5_tok_s"]),
          "- Data Parallel is the choice for capacity: on the same 4 GPUs it carries %.2fx the users of Model Parallel at Standard "
          "and %.2fx at Fast. Model Parallel only makes a single user faster (%.1f vs %.1f tok/s)." % (
              S["dp"]["capacity_standard"] / float(S["mp"]["capacity_standard"]), S["dp"]["capacity_fast"] / float(S["mp"]["capacity_fast"]),
              M["single_user_speed_tok_s"]["mp"], M["single_user_speed_tok_s"]["dp"]),
          ""]
    txt = "\n".join(o)
    with open(os.path.join(RES, "design_table.md"), "w") as fh:
        fh.write(txt)
    return txt


def main():
    import matplotlib.ticker  # noqa: F401  (used through matplotlib.ticker in the charts)
    M = build_metrics()
    imgs = [f(M) for f in (chart_speed, chart_throughput, chart_ttft, chart_caps, chart_capacity, chart_mix, chart_fail)]
    M["images"] = [os.path.relpath(p, RES) for p in imgs]
    with open(os.path.join(RES, "metrics.json"), "w") as fh:
        json.dump(M, fh, indent=1, ensure_ascii=False)
    txt = design_table(M)
    need = ["seq", "dp", "dp_fast", "mp", "mp_fast", "mix_short", "mix_long", "fail_node"]
    missing = [n for n in need if n not in M["runs"]] + ([] if any(k.startswith("cap_") for k in M["runs"]) else ["cap_*"])
    print("runs in metrics.json: %s" % ", ".join(M["runs"]))
    print("missing: %s" % (", ".join(missing) or "none"))
    for p in imgs:
        print("image: %s (%d bytes)" % (os.path.relpath(p, RES), os.path.getsize(p)))
    print()
    print(txt)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
