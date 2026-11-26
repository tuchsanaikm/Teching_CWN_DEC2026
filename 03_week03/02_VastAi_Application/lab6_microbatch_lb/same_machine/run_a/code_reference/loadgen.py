#!/usr/bin/env python3
"""LAB 6 - load generator: how many concurrent users can the system take?

Run ON the same machine as the servers; it shoots at NGINX (127.0.0.1:8080).

  python loadgen.py capacity --name s1_single            # search for the capacity
  python loadgen.py single   --name try_n4 --users 4 --duration 10    # one level, per-second results
  python loadgen.py single   --name fail_on --users 60 --duration 60 --event-at 20 \
                             --event-cmd "bash cluster.sh kill-gpu 1"   # something happens in the middle of the level:
                             # the command is run 20 s after the level started; the result gets "before" / "after"

One simulated user = a loop: send 1 image -> wait for the answer -> send the next image at once
(closed loop, no think time), walking over the 6 test images. An answer that takes more than
10 s (or is not HTTP 200) is an error.

One level = 20 s of shooting; the first 5 s are warm-up and are not counted.
  latency p50/p95/p99, errors : requests that START inside the measured window (they are followed
                                to their end, so slow requests are not lost when the level stops)
  throughput                  : successful answers that ARRIVE inside the measured window / its length
PASS = p95 <= 500 ms and errors < 1 %.   Capacity = the largest number of users N that passes.

Capacity search (3 steps):
  1. range    : N = 1, 2, 4 ... 512 until 2 levels in a row fail
  2. estimate : straight line through (N, p95) of the last passing and the first failing level
                -> the N where p95 would be 500 ms -> measure there
  3. refine   : repeat step 2 with the new point until pass and fail are <= 2 users apart (4 above N = 100)
  A level that fails is always measured one more time; it fails only if both runs fail.
Results go to <out-dir>/<name>.json (one file per name). The API key is never printed or saved.

Needs only the Python standard library (uvloop and nvidia-ml-py are used when installed).
"""
import argparse
import asyncio
import json
import math
import multiprocessing as mp
import os
import re
import resource
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone

LADDER = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512]
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)                         # /workspace/lab6
BOUNDARY = "----lab6loadgen7MA4YWxkTrZu0gW"
RE_CLEN = re.compile(rb"\r\ncontent-length:\s*(\d+)")
CLK_TCK = os.sysconf("SC_CLK_TCK")
now = time.monotonic                                 # CLOCK_MONOTONIC: the same clock in every process
RESENT = [0]                                         # per worker process: requests sent a second time (see user())


def say(*a):
    print(*a, flush=True)


# =====================================================================================
# 1. the simulated users (run inside worker processes)
# =====================================================================================
def build_requests(image_paths, host, port, key):
    """One ready-to-send HTTP request (bytes) per test image."""
    reqs = []
    for path in image_paths:
        with open(path, "rb") as fh:
            data = fh.read()
        body = (f'--{BOUNDARY}\r\nContent-Disposition: form-data; name="file"; '
                f'filename="{os.path.basename(path)}"\r\nContent-Type: image/jpeg\r\n\r\n').encode() \
            + data + f"\r\n--{BOUNDARY}--\r\n".encode()
        head = (f"POST /v1/detect HTTP/1.1\r\nHost: {host}:{port}\r\nAuthorization: Bearer {key}\r\n"
                f"Content-Type: multipart/form-data; boundary={BOUNDARY}\r\n"
                f"Content-Length: {len(body)}\r\n\r\n").encode()
        reqs.append(head + body)
    return reqs


async def exchange(reader, writer, req):
    """Send one request on an open connection, read the whole answer. -> (status, body, server_closes)"""
    writer.write(req)
    await writer.drain()
    head = await reader.readuntil(b"\r\n\r\n")
    status = int(head[9:12])
    low = head.lower()
    m = RE_CLEN.search(low)
    if m:
        body = await reader.readexactly(int(m.group(1)))
    elif b"transfer-encoding: chunked" in low:
        parts = []
        while True:
            size = int((await reader.readline()).split(b";")[0].strip() or b"0", 16)
            if size == 0:
                await reader.readuntil(b"\r\n")
                break
            parts.append(await reader.readexactly(size))
            await reader.readexactly(2)
        body = b"".join(parts)
    else:
        return status, b"", True
    return status, body, b"connection: close" in low


def hangup(writer):
    if writer is not None:
        try:
            writer.transport.abort()
        except Exception:
            pass


async def user(uid, host, port, reqs, timeout, t0, duration, start_delay, recs):
    """One simulated user. Appends one record per request:
    (start_s, latency_ms, error or None, server, queue_ms, model_ms, batch_size)"""
    await asyncio.sleep(max(0.0, t0 + start_delay - now()))
    t_end = t0 + duration
    reader = writer = None
    i = uid % len(reqs)
    while True:
        ts = now()
        if ts >= t_end:
            break
        req = reqs[i]
        i = (i + 1) % len(reqs)
        err = None
        status, body = 0, b""
        try:
            async with asyncio.timeout(timeout):
                while True:
                    reused = writer is not None
                    if not reused:
                        reader, writer = await asyncio.open_connection(host, port)
                    try:
                        status, body, closes = await exchange(reader, writer, req)
                        break
                    except (ConnectionError, asyncio.IncompleteReadError) as exc:
                        hangup(writer)
                        writer = None
                        got = getattr(exc, "partial", b"")
                        if reused and not got:       # idle keep-alive connection was closed by NGINX:
                            RESENT[0] += 1
                            continue                 # same request again on a new connection (not an error)
                        raise
            if closes:
                hangup(writer)
                writer = None
            if status != 200:
                err = f"http_{status}"
        except TimeoutError:
            err = "timeout"
        except (OSError, asyncio.IncompleteReadError, asyncio.LimitOverrunError, ValueError) as exc:
            err = type(exc).__name__
        lat = (now() - ts) * 1000.0
        if err is None:
            try:
                d = json.loads(body)
                recs.append((ts - t0, lat, None, d["server"], d["queue_ms"], d["model_ms"], d["batch_size"]))
            except (ValueError, KeyError, TypeError):
                recs.append((ts - t0, lat, "bad_body", None, None, None, None))
        else:
            hangup(writer)
            writer = None
            recs.append((ts - t0, lat, err, None, None, None, None))
            if lat < 50.0:                           # fast failure (door closed): do not spin
                await asyncio.sleep(0.05)
    hangup(writer)


def worker_main(conn, uids, host, port, reqs, timeout, t0, duration):
    """One worker process = one event loop that runs some of the users."""
    recs = []
    try:
        async def main():
            ramp = min(1.0, duration / 4)            # users do not all start in the same millisecond
            await asyncio.gather(*(
                user(u, host, port, reqs, timeout, t0, duration, ramp * ((u * 0.618034) % 1.0), recs)
                for u in uids))
        try:
            import uvloop
            factory = uvloop.new_event_loop
        except ImportError:
            factory = None
        with asyncio.Runner(loop_factory=factory) as runner:
            runner.run(main())
        conn.send((recs, RESENT[0]))
    except BaseException as exc:                     # the parent must never wait forever
        conn.send(RuntimeError(f"worker failed: {type(exc).__name__}: {exc}"))
    finally:
        conn.close()


# =====================================================================================
# 2. what the machine is doing meanwhile: GPU % and CPU of server / NGINX / load generator
# =====================================================================================
class Gpu:
    def __init__(self):
        self.nv = None
        self.handles = []
        try:
            import pynvml
            pynvml.nvmlInit()
            self.nv = pynvml
            self.handles = [pynvml.nvmlDeviceGetHandleByIndex(i) for i in range(pynvml.nvmlDeviceGetCount())]
            self.names = [str(getattr(n, "decode", lambda: n)()) for n in
                          (pynvml.nvmlDeviceGetName(h) for h in self.handles)]
        except Exception:
            self.nv = None
            try:
                out = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                                     capture_output=True, text=True, timeout=10).stdout
                self.names = [x.strip() for x in out.splitlines() if x.strip()]
            except Exception:
                self.names = []

    def util(self):
        """GPU busy % of every card (the driver's own average over its last sample period)."""
        try:
            if self.nv:
                return [float(self.nv.nvmlDeviceGetUtilizationRates(h).gpu) for h in self.handles]
            if not self.names:
                return []
            out = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                                 capture_output=True, text=True, timeout=5).stdout
            return [float(x) for x in out.split()]
        except Exception:
            return []


def find_pids():
    """pids of the detect servers and of NGINX (read from /proc)."""
    servers, nginx = [], []
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        try:
            with open(f"/proc/{name}/cmdline", "rb") as fh:
                cmd = fh.read().replace(b"\0", b" ")
        except OSError:
            continue
        if b"uvicorn" in cmd and b"server:app" in cmd:
            servers.append(int(name))
        elif cmd.startswith(b"nginx:"):
            nginx.append(int(name))
    return servers, nginx


def cpu_seconds(pid):
    """CPU time (user + system, all threads) a process has used so far."""
    with open(f"/proc/{pid}/stat", "rb") as fh:
        f = fh.read().rsplit(b")", 1)[1].split()
    return (int(f[11]) + int(f[12])) / CLK_TCK


class Sampler(threading.Thread):
    """Every 0.5 s: GPU % of each card and the CPU seconds used by each process group."""

    def __init__(self, gpu, groups, t0, duration, interval=0.5):
        super().__init__(daemon=True)
        self.gpu, self.groups, self.t0, self.duration, self.interval = gpu, groups, t0, duration, interval
        self.samples = []                            # (t_s, [gpu %], {group: cpu seconds})
        self.last = {}

    def read_cpu(self):
        out = {}
        for group, pids in self.groups.items():
            total = 0.0
            for pid in pids:
                try:
                    self.last[pid] = cpu_seconds(pid)
                except (OSError, IndexError, ValueError):
                    pass                             # process ended: keep its last value
                total += self.last.get(pid, 0.0)
            out[group] = total
        return out

    def run(self):
        k = 0
        while True:
            target = self.t0 + k * self.interval
            delay = target - now()
            if delay > 0:
                time.sleep(delay)
            self.samples.append((now() - self.t0, self.gpu.util(), self.read_cpu()))
            if target >= self.t0 + self.duration - 1e-9:
                return
            k += 1


def cpu_pct(samples, a, b):
    """CPU % of each group between time a and b (100 % = one core busy all the time)."""
    sa = min(samples, key=lambda s: abs(s[0] - a))
    sb = min(samples, key=lambda s: abs(s[0] - b))
    dt = sb[0] - sa[0]
    if dt <= 0:
        return {}
    return {g: round((sb[2][g] - sa[2][g]) / dt * 100.0, 1) for g in sb[2]}


def gpu_mean(samples, a, b):
    rows = [s[1] for s in samples if a < s[0] <= b + 1e-6 and s[1]]
    if not rows:
        return []
    return [round(sum(r[i] for r in rows) / len(rows), 1) for i in range(len(rows[0]))]


# =====================================================================================
# 3. one level: shoot, then turn the records into numbers
# =====================================================================================
def pct(sorted_vals, p):
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * p / 100.0
    lo, hi = math.floor(k), math.ceil(k)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def r1(x, nd=1):
    return None if x is None else round(x, nd)


def model_stats(rows):
    """rows = successful records. Queue time, model time, images per model call."""
    n = len(rows)
    if n == 0:
        return {"requests": 0}
    q = sorted(r[4] for r in rows)
    m = sorted(r[5] for r in rows)
    calls = sum(1.0 / r[6] for r in rows)            # every image of a batch of b counts 1/b call
    return {
        "requests": n,
        "queue_ms_mean": r1(sum(q) / n, 2), "queue_ms_p95": r1(pct(q, 95), 2),
        "model_ms_mean": r1(sum(m) / n, 2), "model_ms_p95": r1(pct(m, 95), 2),
        "batch_mean_per_call": r1(n / calls, 2),     # average images in one model call
        "batch_mean_per_request": r1(sum(r[6] for r in rows) / n, 2),   # batch size an average image saw
        "batch_max": max(r[6] for r in rows),
    }


def summarize(recs, samples, n_users, warmup, duration, cfg, per_second=False):
    span = duration - warmup
    win = [r for r in recs if r[0] >= warmup]                    # started inside the measured window
    ok = [r for r in win if r[2] is None]
    lats = sorted(r[1] for r in ok)
    errors = {}
    for r in win:
        if r[2] is not None:
            errors[r[2]] = errors.get(r[2], 0) + 1
    n_err = len(win) - len(ok)
    err_pct = 100.0 * n_err / len(win) if win else 100.0
    arrived = sum(1 for r in recs if r[2] is None and warmup <= r[0] + r[1] / 1000.0 < duration)
    p95 = pct(lats, 95)
    passed = bool(ok) and p95 <= cfg.target_p95 and err_pct < cfg.max_error_pct
    servers = {}
    for name in sorted({r[3] for r in ok}):
        rows = [r for r in ok if r[3] == name]
        servers[name] = {**model_stats(rows), "share_pct": r1(100.0 * len(rows) / len(ok))}
    cpu = cpu_pct(samples, warmup, duration)
    res = {
        "users": n_users,
        "pass": passed,
        "throughput_rps": round(arrived / span, 2),
        "latency_ms": {"p50": r1(pct(lats, 50)), "p95": r1(p95), "p99": r1(pct(lats, 99)),
                       "mean": r1(sum(lats) / len(lats)) if lats else None, "max": r1(lats[-1]) if lats else None},
        "requests": len(win), "ok": len(ok), "errors": n_err, "error_pct": round(err_pct, 3),
        "error_kinds": errors,
        "gpu_util_pct": gpu_mean(samples, warmup, duration),
        "cpu_pct": {"server": cpu.get("server"), "nginx": cpu.get("nginx"), "loadgen": cpu.get("loadgen")},
        "model": model_stats(ok),
        "servers": servers,
        "window_s": [warmup, duration],
    }
    if per_second:
        rows = []
        for s in range(int(math.ceil(duration))):
            done = [r for r in recs if s <= r[0] + r[1] / 1000.0 < s + 1]
            good = sorted(r[1] for r in done if r[2] is None)
            c = cpu_pct(samples, s, s + 1)
            rows.append({"second": s + 1, "warmup": s < warmup, "ok": len(good), "errors": len(done) - len(good),
                         "p50_ms": r1(pct(good, 50)), "p95_ms": r1(pct(good, 95)), "max_ms": r1(good[-1]) if good else None,
                         "gpu_util_pct": gpu_mean(samples, s, s + 1),
                         "cpu_pct": {k: c.get(k) for k in ("server", "nginx", "loadgen")}})
        res["per_second"] = rows
    return res


def phase_stats(recs, a, b):
    """Part of a level, seconds [a, b) after its start. Requests are counted by their START time;
    throughput = successful answers that ARRIVE in [a, b) / (b - a)."""
    win = [r for r in recs if a <= r[0] < b]
    ok = [r for r in win if r[2] is None]
    lats = sorted(r[1] for r in ok)
    kinds = {}
    for r in win:
        if r[2] is not None:
            kinds[r[2]] = kinds.get(r[2], 0) + 1
    arrived = sum(1 for r in recs if r[2] is None and a <= r[0] + r[1] / 1000.0 < b)
    by_gpu = {}
    for r in ok:
        g = str(r[3]).split("-")[0]
        by_gpu[g] = by_gpu.get(g, 0) + 1
    return {
        "window_s": [round(a, 3), round(b, 3)],
        "requests": len(win), "ok": len(ok), "errors": len(win) - len(ok),
        "error_pct": round(100.0 * (len(win) - len(ok)) / len(win), 3) if win else None,
        "error_kinds": kinds,
        "throughput_ok_rps": round(arrived / (b - a), 2) if b > a else None,
        "latency_ms": {"p50": r1(pct(lats, 50)), "p95": r1(pct(lats, 95)), "p99": r1(pct(lats, 99)),
                       "max": r1(lats[-1]) if lats else None},
        "ok_by_gpu": dict(sorted(by_gpu.items())),
    }


class EventThread(threading.Thread):
    """Runs one shell command at second `at` of the level and notes when it started and ended."""

    def __init__(self, t0, at, cmd):
        super().__init__(daemon=True)
        self.t0, self.at, self.cmd = t0, at, cmd
        self.result = {"cmd": cmd, "planned_s": at, "done": False}

    def run(self):
        time.sleep(max(0.0, self.t0 + self.at - now()))
        a = now()
        try:
            p = subprocess.run(self.cmd, shell=True, cwd=HERE, capture_output=True, text=True, timeout=30)
            rc, out = p.returncode, (p.stdout + p.stderr).strip()
        except Exception as exc:
            rc, out = -1, f"{type(exc).__name__}: {exc}"
        b = now()
        self.result.update(done=True, started_s=round(a - self.t0, 3), ended_s=round(b - self.t0, 3),
                           returncode=rc, output=out[-2000:])


class Runner:
    def __init__(self, cfg, reqs):
        self.cfg, self.reqs = cfg, reqs
        self.gpu = Gpu()
        self.n_servers = 1
        self.ctx = mp.get_context("fork")

    # ---- the system behind the door ----
    def health(self):
        with urllib.request.urlopen(f"http://{self.cfg.host}:{self.cfg.port}/health", timeout=5) as r:
            return json.loads(r.read())

    def discover(self):
        """Ask /health many times: round robin shows every server behind NGINX. With a random method
        (p2c) a server can be missed for a while, so stop only after a long row of answers with nothing new."""
        seen, quiet = {}, 0
        for _ in range(4000):
            h = self.health()
            if h.get("server") in seen:
                quiet += 1
            else:
                seen[h.get("server")] = {k: h.get(k) for k in ("mode", "max_batch", "max_wait_ms", "device", "imgsz", "slowdown")}
                quiet = 0
            if quiet >= 12 * len(seen) + 2:
                break
        self.n_servers = max(1, len(seen))
        return dict(sorted(seen.items()))

    def wait_idle(self, limit=90.0):
        """Between levels: wait until no server has images left in its queue (after time-outs the
        servers still work on requests nobody waits for)."""
        time.sleep(self.cfg.pause)
        t_stop = now() + limit
        while now() < t_stop:
            try:
                if all(self.health().get("queue_len", 0) == 0 for _ in range(2 * self.n_servers + 1)):
                    return
            except Exception:
                pass
            time.sleep(0.5)

    # ---- one level ----
    def level(self, n_users, duration, warmup, per_second=False, event=None):
        cfg = self.cfg
        procs = cfg.procs or min(8, math.ceil(n_users / 64))
        procs = max(1, min(procs, n_users))
        server_pids, nginx_pids = find_pids()
        t0 = now() + 0.4 + 0.02 * procs
        workers = []
        for k in range(procs):
            parent, child = self.ctx.Pipe(duplex=False)
            p = self.ctx.Process(target=worker_main, daemon=True,
                                 args=(child, list(range(k, n_users, procs)), cfg.host, cfg.port, self.reqs,
                                       cfg.timeout, t0, duration))
            p.start()
            child.close()
            workers.append((p, parent))
        groups = {"server": server_pids, "nginx": nginx_pids, "loadgen": [os.getpid()] + [p.pid for p, _ in workers]}
        sampler = Sampler(self.gpu, groups, t0, duration)        # thread starts only after the forks
        sampler.start()
        ev = None
        if event:                                    # (second, shell command): thread, started after the forks
            ev = EventThread(t0, event[0], event[1])
            ev.start()
        recs, resent = [], 0
        for p, parent in workers:
            if not parent.poll(max(1.0, t0 + duration + cfg.timeout + 30 - now())):
                p.kill()
                raise RuntimeError("a load worker did not finish")
            got = parent.recv()
            if isinstance(got, Exception):
                raise got
            recs.extend(got[0])
            resent += got[1]
            p.join(10)
        sampler.join(duration + 30)
        res = summarize(recs, sampler.samples, n_users, warmup, duration, cfg, per_second)
        if ev:
            ev.join(40)
            e = dict(ev.result)
            res["event"] = e
            if e["done"]:
                # before = started in [warm-up, event start); after = started in [event end, end of level)
                a, b = e["started_s"], e["ended_s"]
                res["before"] = phase_stats(recs, warmup, a)
                res["during_event"] = phase_stats(recs, a, b)
                res["after"] = phase_stats(recs, b, duration)
                # requests already on their way when the event started (sent before it, answered after it)
                fly = [r for r in recs if r[0] < a <= r[0] + r[1] / 1000.0]
                kinds = {}
                for r in fly:
                    if r[2] is not None:
                        kinds[r[2]] = kinds.get(r[2], 0) + 1
                res["in_flight_at_event"] = {"requests": len(fly), "errors": sum(kinds.values()), "error_kinds": kinds}
                # the whole level, warm-up included: every request the users sent
                kinds = {}
                for r in recs:
                    if r[2] is not None:
                        kinds[r[2]] = kinds.get(r[2], 0) + 1
                n_bad = sum(kinds.values())
                res["all_requests"] = {"requests": len(recs), "ok": len(recs) - n_bad, "errors": n_bad,
                                       "error_pct": round(100.0 * n_bad / len(recs), 3) if recs else None,
                                       "error_kinds": kinds}
        # every request this level has sent, warm-up included (to compare with what the server counted)
        res["sent"] = {"total": len(recs), "warmup": sum(1 for r in recs if r[0] < warmup),
                       "measured": res["requests"], "ok_total": sum(1 for r in recs if r[2] is None),
                       "resent_on_closed_keepalive": resent}
        res["loadgen_procs"] = procs
        # a load generator that is itself out of CPU would make the system look slow
        res["loadgen_busy"] = bool((res["cpu_pct"]["loadgen"] or 0) > 85.0 * procs)
        res["server_procs"], res["nginx_procs"] = len(server_pids), len(nginx_pids)
        return res


def fmt(res):
    lat, c, m = res["latency_ms"], res["cpu_pct"], res["model"]
    gpus = " ".join(f"gpu{i}={u:.0f}%" for i, u in enumerate(res["gpu_util_pct"])) or "gpu=n/a"
    line = (f"N={res['users']:<4d} {'PASS' if res['pass'] else 'FAIL'}  thr={res['throughput_rps']:.1f}/s  "
            f"p50={lat['p50']} p95={lat['p95']} p99={lat['p99']} ms  err={res['errors']}/{res['requests']} "
            f"({res['error_pct']:.2f}%)  {gpus}  cpu% server={c['server']} nginx={c['nginx']} loadgen={c['loadgen']}")
    if m.get("requests"):
        line += (f"\n       queue={m['queue_ms_mean']} ms  model={m['model_ms_mean']} ms  "
                 f"images/call={m['batch_mean_per_call']}  answered by: "
                 + "  ".join(f"{k}={v['requests']}" for k, v in res["servers"].items()))
    if res["error_kinds"]:
        line += f"\n       errors: {res['error_kinds']}"
    if res.get("loadgen_busy"):
        line += "\n       WARNING: the load generator itself was short of CPU (use more --procs)"
    return line


# =====================================================================================
# 4. capacity search (measure = any function N -> verdict, so the search can be tested alone)
# =====================================================================================
def gap_allowed(n):
    return 4 if n > 100 else 2


def find_capacity(measure, ladder, target_ms, fail_ms, max_rounds=30):
    """measure(n, phase) -> {"users", "pass", "p95_ms", ...}.  Returns (capacity, closed, lo, hi, estimates)."""
    points, estimates = {}, []
    # ---- 1. range ----
    first_fail, streak = None, 0
    for n in ladder:
        points[n] = measure(n, "range")
        if points[n]["pass"]:
            first_fail, streak = None, 0
        else:
            first_fail = n if streak == 0 else first_fail
            streak += 1
            if streak >= 2:
                break
    if first_fail is None:                           # everything passed: the top of the ladder is not the limit
        return ladder[-1], False, ladder[-1], None, estimates
    hi = first_fail
    lo = max((n for n, d in points.items() if n < hi and d["pass"]), default=0)
    # ---- 2. estimate + 3. refine ----
    rnd, last_side, same = 0, None, 0
    while lo > 0 and hi - lo > gap_allowed(lo) and rnd < max_rounds:
        rnd += 1
        p_lo = points[lo]["p95_ms"]
        p_hi = points[hi]["p95_ms"] if points[hi]["p95_ms"] is not None else fail_ms
        if same >= 2:                                # the line moved the same end twice: cut the range in half
            method, raw = "midpoint (same side moved twice)", (lo + hi) / 2
        elif p_lo is None or not (p_lo < target_ms < p_hi):   # failed because of errors, not because of p95
            method, raw = "midpoint (p95 does not cross the target)", (lo + hi) / 2
        else:
            method, raw = "line", lo + (target_ms - p_lo) * (hi - lo) / (p_hi - p_lo)
        n = min(hi - 1, max(lo + 1, int(round(raw))))
        d = points[n] = measure(n, "estimate" if rnd == 1 else "refine")
        estimates.append({"round": rnd, "pass_point": {"users": lo, "p95_ms": p_lo},
                          "fail_point": {"users": hi, "p95_ms": points[hi]["p95_ms"]},
                          "method": method, "estimated_users": round(raw, 2), "measured_users": n,
                          "measured_p95_ms": d["p95_ms"], "measured_pass": d["pass"]})
        side = "pass" if d["pass"] else "fail"
        same = same + 1 if side == last_side else 1
        last_side = side
        if d["pass"]:
            lo = n
        else:
            hi = n
    return lo, True, lo, hi, estimates


# =====================================================================================
# 5. command line
# =====================================================================================
def read_key(path):
    key = os.environ.get("API_KEY", "")
    if not key and os.path.isfile(path):
        with open(path) as fh:
            for line in fh:
                if line.startswith("API_KEY="):
                    key = line.split("=", 1)[1].strip()
    if not key:
        sys.exit(f"no API key: set API_KEY or give --key-file (looked at {path})")
    return key


def save(path, doc):
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser(description="LAB 6 load generator (see the top of this file)")
    ap.add_argument("mode", choices=["capacity", "single"])
    ap.add_argument("--name", required=True, help="name of this result -> <out-dir>/<name>.json")
    ap.add_argument("--out-dir", default=os.path.join(BASE, "results"))
    ap.add_argument("--overwrite", action="store_true", help="replace an existing result of the same name")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--images", default=os.path.join(BASE, "samples"), help="folder with the test images")
    ap.add_argument("--key-file", default=os.path.join(BASE, "api_key.env"))
    ap.add_argument("--timeout", type=float, default=10.0, help="seconds; waiting longer = error")
    ap.add_argument("--warmup", type=float, default=5.0, help="first seconds of a level that are not counted")
    ap.add_argument("--target-p95", type=float, default=500.0, help="ms")
    ap.add_argument("--max-error-pct", type=float, default=1.0)
    ap.add_argument("--procs", type=int, default=0, help="load processes (0 = 1 per 64 users, max 8)")
    ap.add_argument("--pause", type=float, default=1.0, help="seconds of rest between levels")
    ap.add_argument("--level-seconds", type=float, default=20.0, help="capacity: length of one level")
    ap.add_argument("--ladder", default=",".join(map(str, LADDER)), help="capacity: N of the range step")
    ap.add_argument("--users", type=int, help="single: N")
    ap.add_argument("--duration", type=float, default=20.0, help="single: seconds (warm-up included)")
    ap.add_argument("--event-at", type=float, help="single: second of the level at which --event-cmd is run")
    ap.add_argument("--event-cmd", help="single: shell command run once in the middle of the level (cwd = code/)")
    cfg = ap.parse_args()

    if not re.fullmatch(r"[A-Za-z0-9._-]+", cfg.name):
        sys.exit("--name: use letters, digits, . _ - only")
    seconds = cfg.duration if cfg.mode == "single" else cfg.level_seconds
    if seconds <= cfg.warmup:
        sys.exit("the level must be longer than the warm-up")
    if cfg.mode == "single" and (not cfg.users or cfg.users < 1):
        sys.exit("single mode needs --users N")
    if (cfg.event_at is None) != (cfg.event_cmd is None):
        sys.exit("--event-at and --event-cmd go together")
    if cfg.event_cmd and (cfg.mode != "single" or not cfg.warmup < cfg.event_at < cfg.duration):
        sys.exit("an event needs single mode and warm-up < --event-at < --duration")
    ladder = sorted({int(x) for x in cfg.ladder.split(",") if x.strip()})
    os.makedirs(cfg.out_dir, exist_ok=True)
    out = os.path.join(cfg.out_dir, cfg.name + ".json")
    if os.path.exists(out) and not cfg.overwrite:
        sys.exit(f"{out} already exists: choose another --name or add --overwrite")
    images = sorted(os.path.join(cfg.images, f) for f in os.listdir(cfg.images)
                    if f.lower().endswith((".jpg", ".jpeg", ".png")))[:6]
    if not images:
        sys.exit(f"no test images in {cfg.images}")
    try:                                             # 1 connection per user
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        resource.setrlimit(resource.RLIMIT_NOFILE, (hard if hard != resource.RLIM_INFINITY else 65536, hard))
    except (ValueError, OSError):
        pass

    run = Runner(cfg, build_requests(images, cfg.host, cfg.port, read_key(cfg.key_file)))
    try:
        system = run.discover()
    except Exception as exc:
        sys.exit(f"the system does not answer on http://{cfg.host}:{cfg.port}/health ({type(exc).__name__})")
    doc = {
        "name": cfg.name, "mode": cfg.mode, "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "finished": False,
        "config": {"url": f"http://{cfg.host}:{cfg.port}/v1/detect", "images": [os.path.basename(p) for p in images],
                   "timeout_s": cfg.timeout, "level_seconds": seconds, "warmup_s": cfg.warmup,
                   "pass_rule": {"p95_ms_max": cfg.target_p95, "error_pct_below": cfg.max_error_pct},
                   "ladder": ladder if cfg.mode == "capacity" else None},
        "system": {"servers": system, "gpus": run.gpu.names, "cpu_count": os.cpu_count()},
        "levels": [],
    }
    say(f"[loadgen] name={cfg.name} mode={cfg.mode} target=http://{cfg.host}:{cfg.port}  "
        f"servers={len(system)} ({', '.join(system)})  mode={'/'.join(sorted({str(v['mode']) for v in system.values()}))}")
    say(f"[loadgen] level={seconds:g}s (warm-up {cfg.warmup:g}s)  images={len(images)}  timeout={cfg.timeout:g}s  "
        f"pass: p95<={cfg.target_p95:g}ms and errors<{cfg.max_error_pct:g}%")

    if cfg.mode == "single":
        res = run.level(cfg.users, seconds, cfg.warmup, per_second=True,
                        event=(cfg.event_at, cfg.event_cmd) if cfg.event_cmd else None)
        res.update(phase="single", attempt=1)
        doc["levels"].append(res)
        say(" sec     ok  err   p50ms   p95ms   gpu%          cpu% server/nginx/loadgen")
        for s in res["per_second"]:
            c = s["cpu_pct"]
            say(f"{s['second']:4d}{'w' if s['warmup'] else ' '} {s['ok']:5d} {s['errors']:4d} "
                f"{str(s['p50_ms']):>7} {str(s['p95_ms']):>7}   {str(s['gpu_util_pct']):<13} "
                f"{c['server']}/{c['nginx']}/{c['loadgen']}")
        say(fmt(res))
        if "event" in res:
            e = res["event"]
            say(f"EVENT: '{e['cmd']}' planned at {e['planned_s']:g}s -> ran {e.get('started_s')}s..{e.get('ended_s')}s "
                f"rc={e.get('returncode')}  {e.get('output', '')}")
            for k in ("before", "during_event", "after"):
                if k in res:
                    ph = res[k]
                    say(f"  {k:<12} {ph['window_s'][0]:6.2f}-{ph['window_s'][1]:6.2f}s  requests={ph['requests']} "
                        f"errors={ph['errors']} ({ph['error_pct']}%) {ph['error_kinds']}  ok-throughput={ph['throughput_ok_rps']} req/s  "
                        f"p50={ph['latency_ms']['p50']} p95={ph['latency_ms']['p95']} max={ph['latency_ms']['max']} ms  ok_by_gpu={ph['ok_by_gpu']}")
            if "all_requests" in res:
                al, fl = res["all_requests"], res["in_flight_at_event"]
                say(f"  all requests (warm-up included): {al['errors']} errors of {al['requests']} ({al['error_pct']}%) {al['error_kinds']}; "
                    f"in flight at the event: {fl['requests']}, of them errors {fl['errors']}")
        doc.update(finished=True, capacity=None,
                   max_throughput_rps=res["throughput_rps"],
                   finished_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        save(out, doc)
        say(f"[loadgen] saved {out}")
        say(f"CAPACITY: not searched in single mode (N={cfg.users} {'PASS' if res['pass'] else 'FAIL'}, "
            f"{res['throughput_rps']:.1f} req/s, p95 {res['latency_ms']['p95']} ms)")
        say("DONE")
        return

    doc.update(decisions=[], estimates=[])

    def measure(n, phase):
        """Measure N; a failing level is measured once more and fails only if both runs fail."""
        runs = []
        for attempt in (1, 2):
            if doc["levels"]:
                run.wait_idle()
            res = run.level(n, seconds, cfg.warmup)
            res.update(phase=phase, attempt=attempt)
            doc["levels"].append(res)
            runs.append(res)
            say(f"[{phase}{' again' if attempt == 2 else ''}] " + fmt(res))
            save(out, doc)
            if res["pass"]:
                break
        # the run that decides: the passing one, else the better of the two failing ones
        best = runs[-1] if runs[-1]["pass"] else min(
            runs, key=lambda r: r["latency_ms"]["p95"] if r["latency_ms"]["p95"] is not None else float("inf"))
        d = {"users": n, "phase": phase, "pass": best["pass"], "runs": len(runs),
             "p95_ms": best["latency_ms"]["p95"], "throughput_rps": best["throughput_rps"],
             "error_pct": best["error_pct"]}
        doc["decisions"].append(d)
        return d

    def measure_logged(n, phase):
        if phase != "range":
            say(f"[{phase}] next N = {n}")
        return measure(n, phase)

    capacity, closed, lo, hi, estimates = find_capacity(measure_logged, ladder, cfg.target_p95, cfg.timeout * 1000.0)
    best = max(doc["levels"], key=lambda r: r["throughput_rps"])
    alt = best["throughput_rps"] * cfg.target_p95 / 1000.0
    doc.update(
        finished=True, estimates=estimates, capacity=capacity, capacity_closed=closed,
        last_pass_users=lo if lo else None, first_fail_users=hi,
        max_throughput_rps=best["throughput_rps"], max_throughput_at_users=best["users"],
        estimate_from_throughput={"formula": "max throughput x target p95 (s)", "users": round(alt, 1)},
        finished_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    save(out, doc)
    say(f"[loadgen] saved {out}  ({len(doc['levels'])} runs)")
    for e in estimates:
        say(f"  estimate {e['round']}: pass N={e['pass_point']['users']} (p95 {e['pass_point']['p95_ms']}) / "
            f"fail N={e['fail_point']['users']} (p95 {e['fail_point']['p95_ms']}) -> {e['method']} -> "
            f"N~{e['estimated_users']} -> measured N={e['measured_users']}: p95 {e['measured_p95_ms']} "
            f"{'PASS' if e['measured_pass'] else 'FAIL'}")
    say(f"OTHER ESTIMATE: max throughput {best['throughput_rps']:.1f} req/s (at N={best['users']}) x "
        f"{cfg.target_p95 / 1000:g} s = N ~ {alt:.1f}")
    if not closed:
        say(f"CAPACITY: >= {capacity} users (every level up to N={capacity} passed; the limit was not reached)")
    elif capacity == 0:
        say(f"CAPACITY: 0 users (even N={hi} does not pass)")
    else:
        say(f"CAPACITY: {capacity} users  (N={lo} passes, N={hi} fails)")
    say("DONE")


if __name__ == "__main__":
    main()
