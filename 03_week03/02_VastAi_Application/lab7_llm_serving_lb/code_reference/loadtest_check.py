#!/usr/bin/env python3
"""Is the load generator measuring correctly?  Runs ON machine 1 (started by run_loadtest_check.sh).

It fires loadgen.py at fake_llm.py, a server whose answer timing is known in advance:

  A  numbers match the calculation?   fake: first token 200 ms, 50 tokens/s, 100 tokens; N = 1, 50, 200
       expected: TTFT 0.2 s, per-user speed 50 tok/s, throughput N * 100 / 2.2 tok/s      (each within 10 %)
  B  nothing lost in the count?       questions sent by the load generator (warm-up included)
       vs. requests counted by the fake server in the same run                            (within 1 %)
  C  load generator fast enough?      fake sends as fast as possible, N = 400             (> 40,000 tok/s)
  D  does NGINX hold tokens back?     NGINX -> fake (settings of A), N = 50 through port 8080 vs. direct
       TTFT at most 20 ms more, per-user speed within 5 %
  E  same result when repeated?       NGINX back on the 4 real replicas, N = 32, 3 runs   (throughput within 10 %)

  loadtest_check.py [--tests A,C,D,E]     (B is judged on the runs of A; a re-run replaces only the tests given)
Result: results/loadtest_check.json
"""
import argparse, json, os, signal, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.dirname(HERE)                               # /workspace/lab7
RES = os.path.join(D, "results")
OUT = os.path.join(RES, "loadtest_check.json")
PY = sys.executable
FAKE = "http://127.0.0.1:9000"
LB = "http://127.0.0.1:8080"
T_FAKE = os.path.join(HERE, "loadgen_targets_fake.json")
T_FAKE_LB = os.path.join(HERE, "loadgen_targets_fake_nginx.json")
T_REAL = os.path.join(HERE, "loadgen_targets.json")
A_CFG = {"ttft_ms": 200, "interval_ms": 20, "tokens": 100}
C_CFG = {"ttft_ms": 0, "interval_ms": 0, "tokens": 1000}


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def http(url, data=None, headers=None, timeout=5):
    req = urllib.request.Request(url, data=None if data is None else json.dumps(data).encode(),
                                 headers=headers or {}, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, dict(r.headers), r.read()


def fake(path, data=None):
    return json.loads(http(FAKE + path, data)[2])


# ----------------------------------------------------------------------------- fake server
def start_fake(workers):
    try:
        fake("/stats")
        log("fake_llm already running")
        return None
    except Exception:
        pass
    lf = open(os.path.join(D, "logs", "fake_llm.log"), "a")
    p = subprocess.Popen([PY, os.path.join(HERE, "fake_llm.py"), "--port", "9000", "--workers", str(workers)],
                         stdout=lf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
    for _ in range(50):
        time.sleep(0.2)
        try:
            fake("/stats")
            log("fake_llm started, pid", p.pid, "workers", workers)
            return p
        except Exception:
            pass
    raise SystemExit("fake_llm did not start")


# ----------------------------------------------------------------------------- NGINX pool switch
def key():
    with open(os.path.join(D, "runtime", "api_key")) as f:
        return f.read().strip()                         # never printed


def nginx_pool(pool, expect_replica=None):
    """Point NGINX at an upstream group (pool.conf is the one line it includes) and reload it (SIGHUP)."""
    with open(os.path.join(D, "runtime", "pool.conf"), "w") as f:
        f.write("map $host $pool { default %s; }\n" % pool)
    pids = subprocess.run(["pgrep", "-f", "nginx: master"], capture_output=True, text=True).stdout.split()
    if not pids:
        raise SystemExit("NGINX is not running")
    for p in pids:
        os.kill(int(p), signal.SIGHUP)
    hdr = {"Authorization": "Bearer " + key(), "Content-Type": "application/json"}
    body = {"model": "shop-bot", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 2, "stream": False}
    seen = None
    for _ in range(40):                                 # old workers finish, new ones take over
        time.sleep(0.5)
        try:
            st, h, _ = http(LB + "/v1/chat/completions", body, hdr, timeout=20)
            seen = h.get("X-Replica")
            if st == 200 and ((seen == "fake") == (pool == "shop_fake")):
                log("NGINX now uses %s (X-Replica: %s)" % (pool, seen))
                time.sleep(1.0)
                return
        except Exception as e:
            seen = "error %s" % type(e).__name__
    raise SystemExit("NGINX did not switch to %s (last answer from: %s)" % (pool, seen))


# ----------------------------------------------------------------------------- one load-generator run
KEEP = ("users", "processes", "duration_s", "warmup_s", "window_s", "started_at", "ttft_p50_s", "ttft_p95_s", "ttft_max_s",
        "speed_p50_tok_s", "speed_p5_tok_s", "throughput_tok_s", "questions_per_s", "questions_done", "questions_sent",
        "questions_sent_total", "tokens_received_total", "tokens_out_mean", "total_p50_s", "errors", "error_kinds",
        "open_at_end", "cpu", "worker_errors")


def loadgen(name, targets, users, duration, extra=()):
    cmd = [PY, "-u", os.path.join(HERE, "loadgen.py"), "single", "--name", name, "--targets", targets,
           "--results-dir", RES, "--users", str(users), "--duration", str(duration)] + list(extra)
    with open(os.path.join(D, "logs", "loadgen_%s.log" % name), "w") as lf:
        rc = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL).returncode
    if rc != 0:
        raise RuntimeError("loadgen %s failed (rc %d), see logs/loadgen_%s.log" % (name, rc, name))
    with open(os.path.join(RES, name + ".json")) as f:
        lv = json.load(f)["levels"][0]
    out = {k: lv.get(k) for k in KEEP}
    out["run"] = name
    return out


def fake_run(name, targets, cfg, users, duration, extra=()):
    """Set the fake server, zero its counters, run one level, read its counters again."""
    fake("/config", cfg)
    for _ in range(100):                                # nothing left over from the run before
        if fake("/stats")["running"] == 0:
            break
        time.sleep(0.1)
    fake("/reset", {})
    r = loadgen(name, targets, users, duration, extra)
    for _ in range(100):                                # dropped questions are closed by the server a moment later
        st = fake("/stats")
        if st["running"] == 0:
            break
        time.sleep(0.1)
    r["fake_settings"] = cfg
    r["server_counted_requests"] = st["requests"]
    r["server_finished"], r["server_aborted"], r["server_tokens_sent"] = st["finished"], st["aborted"], st["tokens_sent"]
    r["count_diff_pct"] = round(100.0 * abs(r["questions_sent_total"] - st["requests"]) / max(1, st["requests"]), 3)
    log("%-14s N=%-3d TTFT p50 %.4fs  speed p50 %.2f tok/s  throughput %.1f tok/s | sent %d, server counted %d" % (
        name, users, r["ttft_p50_s"] or -1, r["speed_p50_tok_s"] or -1, r["throughput_tok_s"], r["questions_sent_total"], st["requests"]))
    return r


def dev(measured, expected):
    return None if measured is None else round(100.0 * (measured - expected) / expected, 2)


# ----------------------------------------------------------------------------- the tests
def test_A(dur):
    rows = []
    for n in (1, 50, 200):
        r = fake_run("ltc_A_n%d" % n, T_FAKE, A_CFG, n, dur)
        exp = {"ttft_s": 0.2, "speed_tok_s": 50.0, "throughput_tok_s": round(n * 100 / 2.2, 1)}
        r["expected"] = exp
        r["diff_pct"] = {"ttft": dev(r["ttft_p50_s"], exp["ttft_s"]), "speed": dev(r["speed_p50_tok_s"], exp["speed_tok_s"]),
                         "throughput": dev(r["throughput_tok_s"], exp["throughput_tok_s"])}
        r["pass"] = all(v is not None and abs(v) <= 10.0 for v in r["diff_pct"].values()) and r["errors"] == 0
        rows.append(r)
    return {"what": "measured vs calculated, direct to the fake server", "limit": "each of the 3 values within 10 %",
            "measured_values": "TTFT p50, per-user speed p50, throughput in the window after warm-up",
            "runs": rows, "pass": all(r["pass"] for r in rows)}


def test_B(a):
    rows = [{"run": r["run"], "users": r["users"], "loadgen_sent_incl_warmup": r["questions_sent_total"],
             "server_counted": r["server_counted_requests"], "diff_pct": r["count_diff_pct"],
             "pass": r["count_diff_pct"] <= 1.0} for r in a["runs"]]
    return {"what": "questions sent by the load generator (warm-up included) vs requests counted by the fake server, same run",
            "limit": "within 1 %", "runs": rows, "pass": all(r["pass"] for r in rows)}


def test_C(dur, procs):
    extra = ["--procs", str(procs)] if procs else []
    r = fake_run("ltc_C_n400", T_FAKE, C_CFG, 400, dur, extra)
    r["pass"] = r["throughput_tok_s"] > 40000 and r["errors"] == 0
    return {"what": "fake server sends as fast as it can, N = 400: tokens/s the load generator takes in",
            "limit": "> 40,000 tok/s", "runs": [r], "max_tok_s": r["throughput_tok_s"], "pass": r["pass"]}


def test_D(dur):
    direct = fake_run("ltc_D_direct", T_FAKE, A_CFG, 50, dur)
    try:
        nginx_pool("shop_fake")
        via = fake_run("ltc_D_nginx", T_FAKE_LB, A_CFG, 50, dur)
    finally:
        nginx_pool("shop_dp")
    ttft_add_ms = round((via["ttft_p50_s"] - direct["ttft_p50_s"]) * 1000, 2)
    ttft95_add_ms = round((via["ttft_p95_s"] - direct["ttft_p95_s"]) * 1000, 2)
    sp = dev(via["speed_p50_tok_s"], direct["speed_p50_tok_s"])
    sp5 = dev(via["speed_p5_tok_s"], direct["speed_p5_tok_s"])
    ok = ttft_add_ms <= 20.0 and abs(sp) <= 5.0 and via["errors"] == 0
    return {"what": "N = 50 through NGINX :8080 -> fake server, compared with direct to the fake server",
            "limit": "TTFT at most 20 ms more, per-user speed within 5 %",
            "direct": direct, "through_nginx": via, "ttft_p50_added_ms": ttft_add_ms, "ttft_p95_added_ms": ttft95_add_ms,
            "speed_p50_diff_pct": sp, "speed_p5_diff_pct": sp5, "pass": ok}


def test_E(dur):
    nginx_pool("shop_dp")                               # make sure the 4 real replicas are behind NGINX
    rows = []
    for i in (1, 2, 3):
        r = loadgen("ltc_E_run%d" % i, T_REAL, 32, dur)
        log("%-14s N=32  TTFT p50 %.3fs  speed p50 %.1f  throughput %.1f tok/s  errors %d" % (
            r["run"], r["ttft_p50_s"], r["speed_p50_tok_s"], r["throughput_tok_s"], r["errors"]))
        rows.append(r)
    th = [r["throughput_tok_s"] for r in rows]
    spread = round(100.0 * (max(th) - min(th)) / min(th), 2)
    return {"what": "4 real replicas behind NGINX, N = 32, three runs", "limit": "throughput of the 3 runs within 10 %",
            "runs": rows, "throughput_tok_s": th, "spread_pct": spread, "spread_definition": "(max - min) / min",
            "pass": spread <= 10.0 and all(r["errors"] == 0 for r in rows)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tests", default="A,C,D,E")
    ap.add_argument("--duration", type=float, default=40.0, help="seconds per run (first 10 s are warm-up)")
    ap.add_argument("--fake-workers", type=int, default=8)
    ap.add_argument("--c-procs", type=int, default=0, help="load-generator processes in test C (0 = loadgen default)")
    ap.add_argument("--note", default="", help="free text stored with the tests of this invocation")
    args = ap.parse_args()
    tests = [t.strip().upper() for t in args.tests.split(",") if t.strip()]
    res = {}
    if os.path.exists(OUT):
        with open(OUT) as f:
            res = json.load(f)
    res.setdefault("tests", {})
    res.setdefault("history", [])
    res["fake_server"] = {"file": "code/fake_llm.py", "address": FAKE, "workers": args.fake_workers}

    def save():
        res["saved"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        res["all_pass"] = all(res["tests"].get(t, {}).get("pass") is True for t in "ABCDE")
        with open(OUT + ".tmp", "w") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
        os.replace(OUT + ".tmp", OUT)

    proc = start_fake(args.fake_workers)
    try:
        for t in tests:
            log("== test", t)
            if t == "A":
                out = {"A": test_A(args.duration)}
                out["B"] = test_B(out["A"])
            elif t == "C":
                out = {"C": test_C(args.duration, args.c_procs)}
            elif t == "D":
                out = {"D": test_D(args.duration)}
            elif t == "E":
                out = {"E": test_E(args.duration)}
            else:
                continue
            for k, v in out.items():
                v["measured_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
                if args.note:
                    v["note"] = args.note
                if k in res["tests"]:                   # keep what an earlier attempt measured
                    old = res["tests"][k]
                    res["history"].append({"test": k, "replaced_at": v["measured_at"], "result": old})
                res["tests"][k] = v
                log("== test %s: %s" % (k, "PASS" if v["pass"] else "FAIL"))
            save()
    finally:
        if proc is not None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except Exception:
                pass
    log("ALL PASS" if res["all_pass"] else "NOT ALL PASS", "->", OUT)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
