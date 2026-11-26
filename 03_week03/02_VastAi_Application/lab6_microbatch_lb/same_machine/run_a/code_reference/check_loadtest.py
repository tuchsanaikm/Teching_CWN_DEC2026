#!/usr/bin/env python3
"""LAB 6 - is the load generator right? Shoot loadgen.py at fake_server.py (known answer) and compare.

Run ON the rented machine:   python check_loadtest.py [--only A,C,D,E]

  A  fake server waits 50 ms, shot directly, N = 1, 10, 50, 100
     expected: p50 = 50 ms, throughput = N / 0.05           pass: both within 10 %
  B  requests the load generator sent (warm-up included) vs requests the fake server counted,
     for every run against the fake server                  pass: every run differs <= 1 %
  C  fake server answers at once, N = 200                   pass: > 2000 requests/s
  D  NGINX :8080 -> fake server (50 ms), N = 50, vs direct  pass: p50 through NGINX <= direct + 10 ms
  E  the real system, layout 1 (1 GPU, 1 server, single), N = 8, three times
                                                            pass: (max - min) / min <= 10 % for throughput and p50

Every run = loadgen.py single, 20 s with 5 s warm-up (its normal settings).
Writes results/loadtest_check.json; the raw loadgen files are in results/loadtest_check_runs/.
With --only, the other tests keep their old result and the replaced result moves to "previous_attempts".
The API key is never printed or saved.
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
RESULTS = os.path.join(BASE, "results")
RUNS = os.path.join(RESULTS, "loadtest_check_runs")
LOGS = os.path.join(BASE, "logs")
NLOG = os.path.join(LOGS, "nginx")
CONF = os.path.join(HERE, "nginx.conf")
OUT = os.path.join(RESULTS, "loadtest_check.json")
FAKE_PORT, LB_PORT = 8101, 8080          # 8101 = the port NGINX forwards to in layout 1
DELAY_MS = 50.0
DURATION, WARMUP = 20.0, 5.0
CLK = os.sysconf("SC_CLK_TCK")
LIMIT = {"A_pct": 10.0, "B_pct": 1.0, "C_rps": 2000.0, "D_ms": 10.0, "E_pct": 10.0}

fake = None                               # Popen of the fake server


def say(*a):
    print(*a, flush=True)


def get(port, path):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as r:
        return json.loads(r.read())


def read_key():
    with open(os.path.join(BASE, "api_key.env")) as fh:
        for line in fh:
            if line.startswith("API_KEY="):
                return line.split("=", 1)[1].strip()
    sys.exit("no API key file")


# ---------------------------------------------------------------- processes
def cluster(*args):
    with open(os.path.join(LOGS, "check_cluster.log"), "a") as log:
        return subprocess.run(["bash", os.path.join(HERE, "cluster.sh"), *args], stdout=log, stderr=log,
                              stdin=subprocess.DEVNULL).returncode


def stop_fake():
    global fake
    if fake is not None:
        try:
            os.killpg(fake.pid, signal.SIGTERM)
        except OSError:
            pass
        fake.wait(10)
        fake = None
        time.sleep(0.5)


def start_fake(delay_ms, workers):
    global fake
    stop_fake()
    env = dict(os.environ, API_KEY=read_key())
    log = open(os.path.join(LOGS, "fake_server.log"), "a")
    fake = subprocess.Popen([sys.executable, os.path.join(HERE, "fake_server.py"), "--port", str(FAKE_PORT),
                             "--delay-ms", str(delay_ms), "--workers", str(workers)],
                            env=env, stdout=log, stderr=log, stdin=subprocess.DEVNULL, start_new_session=True)
    for _ in range(50):
        try:
            h = get(FAKE_PORT, "/health")
            assert h["mode"] == "fake" and h["delay_ms"] == delay_ms
            return
        except Exception:
            if fake.poll() is not None:
                sys.exit("the fake server did not start (see logs/fake_server.log)")
            time.sleep(0.2)
    sys.exit("the fake server does not answer /health")


def fake_cpu_seconds():
    """CPU seconds used so far by all fake server processes (same session as the one we started)."""
    total = 0.0
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        try:
            with open(f"/proc/{name}/stat", "rb") as fh:
                f = fh.read().rsplit(b")", 1)[1].split()
        except OSError:
            continue
        if int(f[3]) == fake.pid:                        # field 6 = session id
            total += (int(f[11]) + int(f[12])) / CLK
    return total


def start_nginx():
    """NGINX alone (same command as cluster.sh), forwarding to 127.0.0.1:8101 = the fake server."""
    servers = [l.split()[1].rstrip(";") for l in open(CONF) if l.strip().startswith("server 127.0.0.1")]
    if servers != [f"127.0.0.1:{FAKE_PORT}"]:
        sys.exit(f"nginx.conf forwards to {servers}, expected only 127.0.0.1:{FAKE_PORT} (run cluster.sh up first)")
    log = open(os.path.join(NLOG, "container.log"), "w")
    subprocess.Popen(["udocker", "--allow-root", "run", "--nobanner", "--entrypoint=",
                      "-v", f"{CONF}:/etc/nginx/nginx.conf", "-v", f"{NLOG}:/var/log/nginx", "lab6-nginx",
                      "/usr/sbin/nginx", "-g", "daemon off;"],
                     stdout=log, stderr=log, stdin=subprocess.DEVNULL, start_new_session=True)
    for _ in range(60):
        try:
            if get(LB_PORT, "/lb/health")["status"] == "ok" and get(LB_PORT, "/health")["mode"] == "fake":
                return
        except Exception:
            time.sleep(0.5)
    sys.exit("NGINX did not open port 8080 in front of the fake server")


# ---------------------------------------------------------------- one run
def shoot(name, users, port, counted=True):
    """One loadgen run. counted=True: the target is the fake server -> also compare the request counts."""
    before = get(FAKE_PORT, "/stats") if counted else None
    cpu0, t0 = (fake_cpu_seconds(), time.monotonic()) if counted else (0.0, 0.0)
    cmd = [sys.executable, os.path.join(HERE, "loadgen.py"), "single", "--name", name, "--users", str(users),
           "--port", str(port), "--duration", str(DURATION), "--warmup", str(WARMUP),
           "--out-dir", RUNS, "--overwrite"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"loadgen failed for {name}:\n{p.stdout[-2000:]}\n{p.stderr[-2000:]}")
    res = json.load(open(os.path.join(RUNS, name + ".json")))["levels"][0]
    row = {
        "run": name, "users": users, "target_port": port,
        "throughput_rps": res["throughput_rps"],
        "p50_ms": res["latency_ms"]["p50"], "p95_ms": res["latency_ms"]["p95"], "p99_ms": res["latency_ms"]["p99"],
        "mean_ms": res["latency_ms"]["mean"], "max_ms": res["latency_ms"]["max"],
        "requests_measured": res["requests"], "errors": res["errors"], "error_kinds": res["error_kinds"],
        "loadgen_procs": res["loadgen_procs"], "loadgen_cpu_pct": res["cpu_pct"]["loadgen"],
        "loadgen_busy": res["loadgen_busy"], "nginx_cpu_pct": res["cpu_pct"]["nginx"],
        "sent": res["sent"],
    }
    if counted:
        wall = time.monotonic() - t0
        time.sleep(0.3)
        after = get(FAKE_PORT, "/stats")
        got = after["received"] - before["received"]
        n_ans = after["answered_200"] - before["answered_200"]
        sent = res["sent"]["total"]
        hold = None
        if n_ans:
            hold = round((after["hold_ms_mean"] * after["answered_200"]
                          - (before["hold_ms_mean"] or 0) * before["answered_200"]) / n_ans, 3)
        row["count"] = {"loadgen_sent": sent, "fake_received": got, "fake_answered_200": n_ans,
                        "diff": sent - got, "diff_pct": round(abs(sent - got) / max(sent, 1) * 100, 4)}
        row["fake_hold_ms_mean"] = hold                  # what the fake server itself held on average
        row["fake_cpu_pct"] = round((fake_cpu_seconds() - cpu0) / wall * 100, 1)   # 100 = one core, whole run
    else:
        row["server_cpu_pct"] = res["cpu_pct"]["server"]
        row["gpu_util_pct"] = res["gpu_util_pct"]
        row["model_ms_mean"] = res["model"].get("model_ms_mean")
        row["queue_ms_mean"] = res["model"].get("queue_ms_mean")
    say(f"  {name:<22} N={users:<4d} thr={row['throughput_rps']:>8.1f}/s  p50={row['p50_ms']} p95={row['p95_ms']} ms  "
        f"err={row['errors']}  " + (f"sent={row['count']['loadgen_sent']} counted={row['count']['fake_received']}  "
                                    f"fake_cpu={row['fake_cpu_pct']}% loadgen_cpu={row['loadgen_cpu_pct']}%"
                                    if counted else f"gpu={row['gpu_util_pct']}"))
    return row


def pct_diff(measured, expected):
    return round((measured - expected) / expected * 100.0, 2)


# ---------------------------------------------------------------- the tests
def test_a(workers):
    say("[A] fake server 50 ms, direct, N = 1, 10, 50, 100")
    start_fake(DELAY_MS, workers)
    rows = []
    for n in (1, 10, 50, 100):
        r = shoot(f"A_direct_n{n}", n, FAKE_PORT)
        r["expected_p50_ms"] = DELAY_MS
        r["expected_throughput_rps"] = round(n / (DELAY_MS / 1000.0), 2)
        r["p50_diff_pct"] = pct_diff(r["p50_ms"], r["expected_p50_ms"])
        r["throughput_diff_pct"] = pct_diff(r["throughput_rps"], r["expected_throughput_rps"])
        r["pass"] = (abs(r["p50_diff_pct"]) <= LIMIT["A_pct"] and abs(r["throughput_diff_pct"]) <= LIMIT["A_pct"]
                     and r["errors"] == 0)
        rows.append(r)
    return {"what": "numbers match the calculation (fake server waits 50 ms, shot directly)",
            "rule": f"p50 and throughput within {LIMIT['A_pct']:g} % of 50 ms and N / 0.05 s",
            "fake_workers": workers, "rows": rows, "pass": all(r["pass"] for r in rows)}


def test_c(workers):
    say("[C] fake server answers at once, direct, N = 200")
    start_fake(0.0, workers)
    r = shoot("C_direct_n200_delay0", 200, FAKE_PORT)
    r["pass"] = r["throughput_rps"] > LIMIT["C_rps"] and r["errors"] == 0
    return {"what": "how many requests per second the load generator can send (fake server answers at once)",
            "rule": f"throughput > {LIMIT['C_rps']:g} requests/s", "fake_workers": workers, "rows": [r],
            "max_throughput_rps": r["throughput_rps"], "pass": r["pass"]}


def test_d(workers):
    say("[D] NGINX :8080 -> fake server 50 ms, N = 50, against direct")
    start_fake(DELAY_MS, workers)
    start_nginx()
    direct = shoot("D_direct_n50", 50, FAKE_PORT)
    time.sleep(1)
    via = shoot("D_nginx_n50", 50, LB_PORT)
    cluster("down")                                      # stops NGINX (the fake server is not touched)
    extra = round(via["p50_ms"] - direct["p50_ms"], 2)
    return {"what": "time added by NGINX (fake server waits 50 ms, N = 50)",
            "rule": f"p50 through NGINX - p50 direct <= {LIMIT['D_ms']:g} ms", "fake_workers": workers,
            "rows": [direct, via], "p50_direct_ms": direct["p50_ms"], "p50_nginx_ms": via["p50_ms"],
            "p50_added_ms": extra, "p95_added_ms": round(via["p95_ms"] - direct["p95_ms"], 2),
            "throughput_direct_rps": direct["throughput_rps"], "throughput_nginx_rps": via["throughput_rps"],
            "pass": extra <= LIMIT["D_ms"] and via["errors"] == 0 and direct["errors"] == 0}


def test_e():
    say("[E] real system, layout 1 (1 GPU x 1 server, single), N = 8, three times")
    stop_fake()
    if cluster("up", "--gpus", "1", "--per-gpu", "1", "--mode", "single") != 0:
        sys.exit("cluster.sh up failed (see logs/check_cluster.log)")
    h = get(LB_PORT, "/health")
    if h.get("mode") != "single":
        sys.exit("port 8080 is not the real system")
    rows = []
    for k in (1, 2, 3):
        rows.append(shoot(f"E_real_n8_run{k}", 8, LB_PORT, counted=False))
        time.sleep(2)

    def spread(key):
        v = [r[key] for r in rows]
        return round((max(v) - min(v)) / min(v) * 100.0, 2)
    s_thr, s_p50, s_p95 = spread("throughput_rps"), spread("p50_ms"), spread("p95_ms")
    return {"what": "same measurement three times on the real API (layout 1, N = 8)",
            "rule": f"(max - min) / min <= {LIMIT['E_pct']:g} % for throughput and for p50",
            "system": {k: h.get(k) for k in ("server", "mode", "max_batch", "device")}, "rows": rows,
            "throughput_rps": [r["throughput_rps"] for r in rows], "p50_ms": [r["p50_ms"] for r in rows],
            "p95_ms": [r["p95_ms"] for r in rows],
            "throughput_spread_pct": s_thr, "p50_spread_pct": s_p50, "p95_spread_pct": s_p95,
            "pass": s_thr <= LIMIT["E_pct"] and s_p50 <= LIMIT["E_pct"] and all(r["errors"] == 0 for r in rows)}


def test_b(tests):
    """No shooting of its own: the counts of every run against the fake server."""
    rows = []
    for t in ("A", "C", "D"):
        for r in tests.get(t, {}).get("rows", []):
            c = r["count"]
            rows.append({"test": t, "run": r["run"], "users": r["users"],
                         "path": "nginx" if r["target_port"] == LB_PORT else "direct",
                         "loadgen_sent": c["loadgen_sent"], "of_which_warmup": r["sent"]["warmup"],
                         "resent_on_closed_keepalive": r["sent"]["resent_on_closed_keepalive"],
                         "fake_received": c["fake_received"], "diff": c["diff"], "diff_pct": c["diff_pct"],
                         "pass": c["diff_pct"] <= LIMIT["B_pct"]})
    return {"what": "requests sent by the load generator (warm-up included) = requests counted by the fake server",
            "rule": f"difference <= {LIMIT['B_pct']:g} % in every run", "rows": rows,
            "total_sent": sum(r["loadgen_sent"] for r in rows), "total_received": sum(r["fake_received"] for r in rows),
            "max_diff_pct": max((r["diff_pct"] for r in rows), default=None),
            "pass": bool(rows) and all(r["pass"] for r in rows)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="A,C,D,E", help="tests to run (B is always rebuilt from A, C, D)")
    ap.add_argument("--fake-workers", type=int, default=4)
    cfg = ap.parse_args()
    only = [x.strip().upper() for x in cfg.only.split(",") if x.strip()]
    for d in (RUNS, LOGS, NLOG):
        os.makedirs(d, exist_ok=True)
    doc = json.load(open(OUT)) if os.path.exists(OUT) else {"tests": {}, "previous_attempts": []}
    tests = doc["tests"]

    def keep(name, new):
        new["measured_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if name in tests:
            doc["previous_attempts"].append({"test": name, **tests[name]})
        tests[name] = new

    try:
        if {"A", "C", "D"} & set(only):
            cluster("down")                              # the fake server takes the place of the real one (port 8101)
        if "A" in only:
            keep("A", test_a(cfg.fake_workers))
        if "C" in only:
            keep("C", test_c(cfg.fake_workers))
        if "D" in only:
            keep("D", test_d(cfg.fake_workers))
        stop_fake()
        if "E" in only:
            keep("E", test_e())
    finally:
        stop_fake()
    tests["B"] = test_b(tests)
    tests["B"]["measured_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    doc.update(
        name="loadtest_check", written_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        method={"load_generator": "loadgen.py single", "level_seconds": DURATION, "warmup_s": WARMUP,
                "fake_server": "fake_server.py on 127.0.0.1:8101", "fake_delay_ms": DELAY_MS,
                "everything_on_the_same_machine": True, "cpu_count": os.cpu_count()},
        limits=LIMIT, tests={k: tests[k] for k in sorted(tests)},
        summary={k: tests[k]["pass"] for k in sorted(tests)},
        all_pass=all(tests.get(k, {}).get("pass") is True for k in "ABCDE"))
    tmp = OUT + ".tmp"
    json.dump(doc, open(tmp, "w"), indent=2, ensure_ascii=False)
    os.replace(tmp, OUT)
    say(f"[check] saved {OUT}")
    for k in sorted(tests):
        say(f"  {k}: {'PASS' if tests[k]['pass'] else 'FAIL'}  {tests[k]['what']}")
    say("ALL PASS" if doc["all_pass"] else "NOT ALL PASS")


if __name__ == "__main__":
    main()
