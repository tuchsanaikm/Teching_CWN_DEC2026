#!/usr/bin/env python3
"""fail_node: machine 2 fails in the middle of a streaming-chat run (Data Parallel, 4 replicas, Least Connections).
Reads results/fail_node.json (+ fail_node_event.json, logs/nginx_fail_node.log.gz, dp.json) -> results/report_fail_node.md
usage: python3 code/report_fail_node.py [name]"""
import collections, gzip, json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
NAME = sys.argv[1] if len(sys.argv) > 1 else "fail_node"
TTFT_MAX, STD_SPEED, ERR_MAX = 2.0, 15.0, 1.0
SETTLE = 5.0                                    # seconds after the failure that the "settled" column leaves out


def load(n):
    with open(os.path.join(RES, n + ".json")) as f:
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


run, ev, dp = load(NAME), load(NAME + "_event"), load("dp")
lv, rows, reqs = run["levels"][0], run["per_second"], run["requests"]
N, dur, warm = lv["users"], lv["duration_s"], lv["warmup_s"]
kill = ev["kill_start_s"]
dead = ev["node"]
single = next(l for l in dp["levels"] if l["users"] == 1 and not l.get("discarded"))["speed_p50_tok_s"]
cap_std = dp["capacity"]["users"]
names = run["target"]["replicas"]
dead_reps = [n for n in names if n.startswith(dead)]
live_reps = [n for n in names if not n.startswith(dead)]


def phase(a, b):
    """statistics of the seconds [a, b): same definitions as loadgen.py's summary"""
    first = [r for r in reqs if r["t_first"] is not None and a <= r["t_first"] < b]
    done = [r for r in reqs if r["err"] is None and a <= r["t_end"] < b]
    errs = [r for r in reqs if r["err"] is not None and a <= r["t_end"] < b]
    sec = [r for r in rows if a <= r["t"] + 0.5 < b]         # whole seconds inside the phase
    sp = [r["speed"] for r in done if r["speed"] is not None]
    o = {"a": a, "b": b, "done": len(done), "errors": len(errs),
         "error_pct": 100.0 * len(errs) / max(1, len(errs) + len(done)),
         "throughput": sum(r["tokens"] for r in sec) / max(1, len(sec)),
         "qps": len(done) / (b - a),
         "speed_p50": pct(sp, 50), "speed_p5": pct(sp, 5),
         "ttft_p50": pct([r["ttft"] for r in first], 50), "ttft_p95": pct([r["ttft"] for r in first], 95),
         "ttft_max": max([r["ttft"] for r in first], default=None), "running": {}, "tok": {}, "share": {}}
    for n in names:
        v = [r["replicas"][n]["running"] for r in sec if r["replicas"][n]["running"] is not None]
        o["running"][n] = (sum(v) / len(v), max(v)) if v else None
        o["tok"][n] = sum(r["replicas"][n]["tokens"] for r in sec) / max(1, len(sec))
        o["share"][n] = sum(1 for r in done if r["replica"] == n)
    o["ok_ttft"] = o["ttft_p95"] is not None and o["ttft_p95"] <= TTFT_MAX
    o["ok_speed"] = o["speed_p5"] is not None and o["speed_p5"] >= STD_SPEED
    o["ok_err"] = o["error_pct"] < ERR_MAX
    o["std"] = o["ok_ttft"] and o["ok_speed"] and o["ok_err"]
    o["fast"] = o["ok_ttft"] and o["ok_err"] and o["speed_p5"] is not None and o["speed_p5"] >= single / 2
    return o


P = [("before the failure", phase(warm, kill)), ("after the failure, all of it", phase(kill, dur)),
     ("after, settled", phase(int(kill) + SETTLE, dur))]
out = []
w = out.append
w("# fail_node — machine 2 fails in the middle of a streaming chat (Data Parallel, 4 replicas, Least Connections, cap 256)\n")
w("N = %d users = 40 %% of the Standard capacity of dp (%d). One level, %.0f s, the first %.0f s not counted. "
  "Second %.3f: both replicas of machine 2 are killed with SIGKILL (`cluster.sh kill %s`); the machine itself and NGINX stay up."
  % (N, cap_std, dur, warm, kill, dead))
w("Standard: TTFT p95 <= %.0f s, speed p5 >= %.0f tok/s, errors < 1 %%.  Fast: speed p5 >= %.2f tok/s (half of one user alone, dp N=1: %.2f).\n"
  % (TTFT_MAX, STD_SPEED, single / 2, single))

w("## Before and after\n")
w("| | " + " | ".join("%s (s %.0f-%.0f)" % (n, p["a"], p["b"]) for n, p in P) + " |")
w("|---|" + "---|" * len(P))
rowf = lambda label, fn: w("| %s | %s |" % (label, " | ".join(fn(p) for _, p in P)))
rowf("replicas answering", lambda p: str(sum(1 for n in names if p["share"][n] > 0)))
rowf("throughput tok/s", lambda p: f(p["throughput"], "%.0f"))
rowf("finished questions/s", lambda p: f(p["qps"], "%.1f"))
rowf("speed per user p50 tok/s", lambda p: f(p["speed_p50"], "%.1f"))
rowf("speed per user p5 tok/s", lambda p: f(p["speed_p5"], "%.1f"))
rowf("TTFT p50 s", lambda p: f(p["ttft_p50"]))
rowf("TTFT p95 s", lambda p: f(p["ttft_p95"]))
rowf("TTFT max s", lambda p: f(p["ttft_max"]))
for n in names:
    rowf("questions being worked on, %s (mean / max)" % n,
         lambda p, n=n: "down" if p["running"][n] is None else "%.0f / %d" % p["running"][n])
rowf("questions being worked on per live replica (mean)",
     lambda p: f(sum(v[0] for v in p["running"].values() if v) / max(1, sum(1 for v in p["running"].values() if v)), "%.0f"))
rowf("finished / errors", lambda p: "%d / %d" % (p["done"], p["errors"]))
rowf("errors %", lambda p: f(p["error_pct"], "%.2f"))
rowf("Standard: TTFT / speed / errors", lambda p: " / ".join("ok" if x else "FAIL" for x in (p["ok_ttft"], p["ok_speed"], p["ok_err"])))
rowf("**Standard**", lambda p: "**pass**" if p["std"] else "**FAIL**")
rowf("Fast", lambda p: "pass" if p["fast"] else "FAIL")
w("")
b, a, s = P[0][1], P[1][1], P[2][1]
w("- settled vs before: throughput %.0f -> %.0f tok/s (%.0f %%), speed p5 %.1f -> %.1f tok/s (%.0f %%), TTFT p95 %.3f -> %.3f s, "
  "work per live replica %.0f -> %.0f questions."
  % (b["throughput"], s["throughput"], 100 * s["throughput"] / b["throughput"], b["speed_p5"], s["speed_p5"],
     100 * s["speed_p5"] / b["speed_p5"], b["ttft_p95"], s["ttft_p95"],
     sum(v[0] for v in b["running"].values() if v) / sum(1 for v in b["running"].values() if v),
     sum(v[0] for v in s["running"].values() if v) / sum(1 for v in s["running"].values() if v)))
w("- 'after, settled' leaves out the first %.0f s after the failure, i.e. the cut answers themselves and the moment when all "
  "their users ask again at once. 'all of it' counts them, and that is why its error limit fails.\n" % SETTLE)

# ---------------------------------------------------------------- errors
errs = [r for r in reqs if r["err"]]
on_dead = lambda r: (r["replica"] or "").startswith(dead)
inflight = [r for r in errs if r["t_send"] < kill and on_dead(r)]
later = [r for r in errs if r["t_send"] >= kill]
other = [r for r in errs if r not in inflight and r not in later]
w("## Errors\n")
w("| | questions | what the user saw |")
w("|---|---|---|")
cut_tok = [r for r in inflight if r["ttft"] is not None]
cut_none = [r for r in inflight if r["ttft"] is None]
w("| all errors of the run | **%d** | %s |" % (len(errs), ", ".join("%s x%d" % kv for kv in collections.Counter(r["err"] for r in errs).items()) or "-"))
w("| being answered on machine %s when it failed (sent before second %.3f) | **%d** | answer stops in the middle: %d had received %s tokens "
  "(median %s) of an answer, %d had the HTTP 200 header but no token yet |"
  % (dead[1:], kill, len(inflight), len(cut_tok),
     ("%d-%d" % (min(r["n_out"] for r in cut_tok), max(r["n_out"] for r in cut_tok))) if cut_tok else "-",
     f(pct([r["n_out"] for r in cut_tok], 50), "%.0f"), len(cut_none)))
w("| sent after the failure | **%d** | %s |" % (len(later), "nothing: every question got a full answer" if not later else
                                                ", ".join("%s x%d" % kv for kv in collections.Counter(r["err"] for r in later).items())))
w("| other (sent before, not on machine %s) | %d | - |" % (dead[1:], len(other)))
w("")
if inflight:
    per = collections.Counter(r["replica"] for r in inflight)
    w("- the %d cut answers: %s; they ended between second %.3f and %.3f (%.0f ms after the kill); users hit: %d of %d (%.0f %%)."
      % (len(inflight), ", ".join("%s %d" % kv for kv in sorted(per.items())), min(r["t_end"] for r in inflight),
         max(r["t_end"] for r in inflight), 1000 * (max(r["t_end"] for r in inflight) - kill),
         len({r["user"] for r in inflight}), N, 100.0 * len({r["user"] for r in inflight}) / N))
    w("- on machine %s at the last sample before the failure: %s questions being worked on (sampled once a second); %d were lost."
      % (dead[1:], " + ".join(str(next(r["replicas"][n]["running"] for r in reversed(rows) if r["t"] < kill and r["replicas"][n]["running"] is not None))
                               for n in dead_reps), len(inflight)))
    again = []
    for r in inflight:                            # the same user's next question = the "ask again"
        nxt = min((x for x in reqs if x["user"] == r["user"] and x["t_send"] > r["t_end"]), key=lambda x: x["t_send"], default=None)
        if nxt:
            again.append(nxt)
    w("- their users asked again 0.2 s later (the load generator's rule): %d of %d of those next questions were answered in full, by %s; "
      "TTFT p50 / p95 / max of them %.3f / %.3f / %.3f s."
      % (sum(1 for x in again if x["err"] is None), len(again),
         ", ".join("%s %d" % kv for kv in sorted(collections.Counter(x["replica"] for x in again).items())),
         pct([x["ttft"] for x in again if x["ttft"]], 50), pct([x["ttft"] for x in again if x["ttft"]], 95),
         max(x["ttft"] for x in again if x["ttft"])))
after_dead = [r for r in reqs if r["t_send"] >= kill and on_dead(r)]
passed = [r for r in reqs if (r.get("tries") or 1) > 1]
w("- questions sent after the failure: %d, answered by a replica of machine %s: %d."
  % (sum(1 for r in reqs if r["t_send"] >= kill), dead[1:], len(after_dead)))
w("- questions NGINX passed on to another replica (the user noticed nothing): %d -> %s."
  % (len(passed), "; ".join("second %.2f, %d tries, answered by %s, TTFT %.3f s%s" % (
      r["t_send"], r["tries"], r["replica"], r["ttft"] or float("nan"), "" if r["err"] is None else " ERROR " + r["err"])
      for r in sorted(passed, key=lambda r: r["t_send"])) or "-"))
w("")

# ---------------------------------------------------------------- NGINX log
p = os.path.join(RES, "logs", "nginx_%s.log.gz" % NAME)
if os.path.exists(p):
    with gzip.open(p, "rt", errors="replace") as fh:
        L = fh.read().splitlines()
    post = [l for l in L if re.match(r"^\d{4}-\d\d-\d\dT", l) and '"POST /v1/chat/completions' in l]
    multi = [l for l in post if re.search(r"upstream=[^ ]+, ", l)]
    st = collections.Counter(m.group(1) for m in (re.search(r'HTTP/1\.1" (\d+) ', l) for l in post) if m)
    el = [l for l in L if re.match(r"^\d{4}/\d\d/\d\d ", l) and "prctl(" not in l]
    kinds = collections.Counter()
    for l in el:
        m = re.search(r"\*\d+ (.*?)(, client:| while )", l)
        k = (m.group(1) if m else l[:60]) + (" while " + l.split(" while ", 1)[1].split(",")[0] if " while " in l else "")
        kinds[re.sub(r"\(\d+: ", "(", k)] += 1
    w("## What NGINX wrote down (results/logs/nginx_%s.log.gz)\n" % NAME)
    w("- chat questions in the access log: %d, status %s; with more than one replica address (passed on): %d (499 = still open when the run ended)"
      % (len(post), ", ".join("%s x%d" % kv for kv in sorted(st.items())), len(multi)))
    for l in multi:
        m = re.search(r"^(\S+) .*replica=(\S+) upstream=(.*?) upstream_status=(.*?) first_byte", l)
        w("  - %s: tried %s -> status %s, answered by %s" % (m.group(1), m.group(3), m.group(4), m.group(2)))
    w("- error log:")
    for k, n in kinds.most_common():
        w("  - %d x %s" % (n, k))
    w("")

# ---------------------------------------------------------------- second by second
w("## Second by second around the failure\n")
w("| second | questions sent | finished | errors | tokens | TTFT p95 s | speed p5 tok/s | being worked on: %s |" % " / ".join(names))
w("|---|---|---|---|---|---|---|---|")
k0 = int(kill)
for r in rows:
    if k0 - 3 <= r["t"] <= k0 + 8 or r["t"] in (k0 + 29, k0 + 30, k0 + 31, k0 + 32) or r["t"] == int(dur) - 1:
        w("| %d%s | %d | %d | %d | %d | %s | %s | %s |" % (
            r["t"], " (kill)" if r["t"] == k0 else "", r["sent"], r["done"], r["errors"], r["tokens"], f(r["ttft_p95_s"]),
            f(r["speed_p5_tok_s"], "%.1f"),
            " / ".join("down" if r["replicas"][n]["running"] is None else str(r["replicas"][n]["running"]) for n in names)))
w("")
w("Kill: planned second %.0f, done second %.3f-%.3f (clock of machine 2 minus machine 1: %+.3f s, taken into account). "
  "CPU of the load generator: busiest process %.0f %% of a core, busiest NGINX worker %.0f %% (max over the run) - neither was the brake."
  % (ev["kill_planned_s"], ev["kill_start_s"], ev["kill_done_s"], ev["clock_machine2_minus_machine1_s"],
     lv["cpu"]["loadgen_busiest_proc"]["max_pct_of_core"], lv["cpu"]["nginx_busiest_proc"]["max_pct_of_core"]))
w("Questions still open when the run ended (not errors, the run just stopped): %d.\n" % lv["open_at_end"])

w("## NGINX settings used (code/nginx.conf, [5] and [8b])\n")
w("    server ... max_fails=1 fail_timeout=30s;      # one failed attempt -> the replica gets no questions for 30 s, then 1 question tests it")
w("    proxy_next_upstream error timeout http_502 http_503 http_504 non_idempotent;   # answer not started -> give the question to another replica")
w("    proxy_next_upstream_tries 3;  proxy_connect_timeout 2s;                        # up to 3 replicas (2 of them may be the dead machine)\n")
w("NGINX can pass a question on only while it has sent nothing of the answer to the user. An answer that is already streaming "
  "cannot be continued on another replica (the half answer exists only in the dead replica), so it is cut.")

with open(os.path.join(RES, "report_%s.md" % NAME), "w") as fh:
    fh.write("\n".join(out) + "\n")
print("\n".join(out))
