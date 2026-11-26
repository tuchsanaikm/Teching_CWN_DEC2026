#!/usr/bin/env python3
"""LAB 6 - fake detect server: no model, a known answer time. Used to check the load generator.

  API_KEY=... python fake_server.py --port 8101 --delay-ms 50 [--workers 4]

Same door as the real server (server.py):
  POST /v1/detect   multipart/form-data with a part named "file" + "Authorization: Bearer <key>"
                    -> waits --delay-ms (counted from the moment the whole request has arrived),
                       then answers 200 with the same JSON fields as the real server (0 detections)
                    -> 401 without / with a wrong key, 422 when the body is not such an upload, 413 above 20 MB
  GET  /health      same fields as the real server (mode = "fake")
  GET  /stats       what this server has counted since it started (all workers together)

No limit on requests at the same time: every request only sets a timer, nothing waits in a queue.
--workers N = N processes on the same port (so that the fake server itself is not the slow part);
the counters live in shared memory, /stats of any worker shows the total.
Standard library only (uvloop is used when installed).
"""
import argparse
import asyncio
import hmac
import json
import multiprocessing as mp
import os
import re
import resource
import signal
import socket
import sys
import time

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_HEAD_BYTES = 64 * 1024
RE_FILENAME = re.compile(rb'filename="([^"]*)"')
REASON = {200: "OK", 400: "Bad Request", 401: "Unauthorized", 404: "Not Found", 405: "Method Not Allowed",
          411: "Length Required", 413: "Payload Too Large", 422: "Unprocessable Entity", 431: "Headers Too Large"}

# one row of counters per worker process (each worker writes only its own row -> no lock needed)
RECEIVED, ANSWERED, REJECTED, HOLD_SUM_MS, HOLD_MAX_MS, HEALTH, NSLOTS = 0, 1, 2, 3, 4, 5, 6

CFG = None          # argparse result
STATS = None        # shared array, NSLOTS numbers per worker
ME = 0              # index of this worker
KEY = b""
T_START = time.time()
perf = time.perf_counter


def total(slot):
    return sum(STATS[w * NSLOTS + slot] for w in range(CFG.workers))


def stats_doc():
    answered = total(ANSWERED)
    return {
        "server": CFG.server_id, "delay_ms": CFG.delay_ms, "workers": CFG.workers,
        "uptime_s": round(time.time() - T_START, 1),
        "received": int(total(RECEIVED)),            # complete POST /v1/detect requests that arrived
        "answered_200": int(answered),               # ... answered 200 after the delay
        "rejected": int(total(REJECTED)),            # ... refused (401 / 413 / 422)
        "waiting_now": int(total(RECEIVED) - answered - total(REJECTED)),
        # time really held = whole request arrived -> answer written
        "hold_ms_mean": round(total(HOLD_SUM_MS) / answered, 3) if answered else None,
        "hold_ms_max": round(max(STATS[w * NSLOTS + HOLD_MAX_MS] for w in range(CFG.workers)), 3),
        "health_calls": int(total(HEALTH)),
        "received_per_worker": [int(STATS[w * NSLOTS + RECEIVED]) for w in range(CFG.workers)],
    }


class Conn(asyncio.Protocol):
    """One client connection (keep-alive). One request at a time, answers go out in order."""

    def connection_made(self, transport):
        self.tr = transport
        self.buf = bytearray()
        self.head = None            # (method, path, headers) once the header block is complete
        self.clen = 0
        self.busy = False           # an answer is still owed on this connection
        self.loop = asyncio.get_running_loop()

    def connection_lost(self, exc):
        self.tr = None

    def data_received(self, data):
        self.buf += data
        self.process()

    # ---- read ----
    def process(self):
        while not self.busy and self.tr is not None:
            if self.head is None:
                end = self.buf.find(b"\r\n\r\n")
                if end < 0:
                    if len(self.buf) > MAX_HEAD_BYTES:
                        self.reply(431, {"detail": "headers too large"}, close=True)
                    return
                lines = bytes(self.buf[:end]).split(b"\r\n")
                del self.buf[:end + 4]
                try:
                    method, target, _ = lines[0].split(b" ", 2)
                except ValueError:
                    self.reply(400, {"detail": "bad request line"}, close=True)
                    return
                headers = {}
                for line in lines[1:]:
                    k, _, v = line.partition(b":")
                    headers[k.strip().lower()] = v.strip()
                self.head = (method, target.split(b"?", 1)[0], headers)
                if b"transfer-encoding" in headers:
                    self.reply(411, {"detail": "send Content-Length"}, close=True)
                    return
                try:
                    self.clen = int(headers.get(b"content-length", b"0"))
                except ValueError:
                    self.reply(400, {"detail": "bad Content-Length"}, close=True)
                    return
                if self.clen > MAX_UPLOAD_BYTES + 65536:      # do not read it at all
                    if method == b"POST" and self.head[1] == b"/v1/detect":
                        STATS[ME * NSLOTS + RECEIVED] += 1
                        STATS[ME * NSLOTS + REJECTED] += 1
                    self.reply(413, {"detail": "file too large"}, close=True)
                    return
                if headers.get(b"expect", b"").lower() == b"100-continue":
                    self.tr.write(b"HTTP/1.1 100 Continue\r\n\r\n")
            if len(self.buf) < self.clen:
                return                                   # body not complete yet
            t_recv = perf()                              # the whole request is here
            method, path, headers = self.head
            body_start = bytes(self.buf[:1024])
            del self.buf[:self.clen]
            self.head = None
            self.route(method, path, headers, body_start, t_recv)

    # ---- answer ----
    def route(self, method, path, headers, body_start, t_recv):
        base = ME * NSLOTS
        if path == b"/v1/detect":
            if method != b"POST":
                return self.reply(405, {"detail": "Method Not Allowed"})
            STATS[base + RECEIVED] += 1
            scheme, _, token = headers.get(b"authorization", b"").partition(b" ")
            if scheme.lower() != b"bearer" or not hmac.compare_digest(token.strip(), KEY):
                STATS[base + REJECTED] += 1
                return self.reply(401, {"detail": "missing or invalid API key"}, extra=b"WWW-Authenticate: Bearer\r\n")
            if self.clen > MAX_UPLOAD_BYTES:
                STATS[base + REJECTED] += 1
                return self.reply(413, {"detail": "file too large"})
            if not headers.get(b"content-type", b"").lower().startswith(b"multipart/form-data") \
                    or b'name="file"' not in body_start:
                STATS[base + REJECTED] += 1
                return self.reply(422, {"detail": "multipart/form-data with a part named 'file' is required"})
            m = RE_FILENAME.search(body_start)
            fname = m.group(1).decode("utf-8", "replace") if m else None
            self.busy = True
            if CFG.delay_ms <= 0:
                self.detect_done(t_recv, fname)
            else:
                self.loop.call_later(CFG.delay_ms / 1000.0, self.detect_due, t_recv, fname)
        elif path == b"/health" and method == b"GET":
            STATS[base + HEALTH] += 1
            self.reply(200, {"status": "ready", "server": CFG.server_id, "mode": "fake", "max_batch": 1,
                             "max_wait_ms": 0, "imgsz": 640, "conf": 0.35, "device": "none",
                             "classes": [], "warmed_batch_sizes": 0, "queue_len": 0,
                             "delay_ms": CFG.delay_ms})
        elif path == b"/stats" and method == b"GET":
            self.reply(200, stats_doc())
        else:
            self.reply(404, {"detail": "Not Found"})

    def detect_due(self, t_recv, fname):
        left = CFG.delay_ms / 1000.0 - (perf() - t_recv)
        if left > 0.0002:                                # the timer fired early: never answer before the delay
            self.loop.call_later(left, self.detect_due, t_recv, fname)
        else:
            self.detect_done(t_recv, fname)

    def detect_done(self, t_recv, fname):
        self.busy = False
        if self.tr is None:                              # client went away while waiting
            STATS[ME * NSLOTS + REJECTED] += 1
            return
        hold = (perf() - t_recv) * 1000.0
        base = ME * NSLOTS
        STATS[base + ANSWERED] += 1
        STATS[base + HOLD_SUM_MS] += hold
        if hold > STATS[base + HOLD_MAX_MS]:
            STATS[base + HOLD_MAX_MS] = hold
        self.reply(200, {"filename": fname, "server": CFG.server_id, "mode": "fake", "batch_size": 1,
                         "queue_ms": 0.0, "model_ms": round(hold, 2), "image": {"width": 0, "height": 0},
                         "count": 0, "detections": []})
        if self.buf:
            self.process()

    def reply(self, status, doc, extra=b"", close=False):
        if self.tr is None:
            return
        body = json.dumps(doc).encode()
        self.tr.write(b"HTTP/1.1 %d %s\r\nContent-Type: application/json\r\nContent-Length: %d\r\n%s%s\r\n"
                      % (status, REASON[status].encode(), len(body), extra,
                         b"Connection: close\r\n" if close else b"") + body)
        if close:
            self.tr.close()
            self.tr = None


def serve(sock):
    async def main():
        loop = asyncio.get_running_loop()
        server = await loop.create_server(Conn, sock=sock, backlog=4096)
        async with server:
            await server.serve_forever()
    try:
        import uvloop
        factory = uvloop.new_event_loop
    except ImportError:
        factory = None
    with asyncio.Runner(loop_factory=factory) as runner:
        runner.run(main())


def main():
    global CFG, STATS, ME, KEY
    ap = argparse.ArgumentParser(description="LAB 6 fake detect server (see the top of this file)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8101)
    ap.add_argument("--delay-ms", type=float, default=50.0, help="time to wait before the answer (0 = answer at once)")
    ap.add_argument("--workers", type=int, default=1, help="processes on the same port")
    ap.add_argument("--server-id", default="fake")
    CFG = ap.parse_args()
    KEY = os.environ.get("API_KEY", "").encode()
    if not KEY:
        sys.exit("API_KEY is not set")
    if CFG.workers < 1 or CFG.delay_ms < 0:
        sys.exit("--workers must be >= 1 and --delay-ms >= 0")
    try:                                                 # one open file per connection
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        resource.setrlimit(resource.RLIMIT_NOFILE, (hard if hard != resource.RLIM_INFINITY else 65536, hard))
    except (ValueError, OSError):
        pass
    STATS = mp.RawArray("d", CFG.workers * NSLOTS)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((CFG.host, CFG.port))
    sock.listen(4096)
    sock.setblocking(False)

    children = []
    for w in range(1, CFG.workers):                      # the parent is worker 0
        pid = os.fork()
        if pid == 0:
            ME = w
            try:
                serve(sock)
            finally:
                os._exit(0)
        children.append(pid)

    def stop(*_):
        for pid in children:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
        os._exit(0)
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print(f"[fake] http://{CFG.host}:{CFG.port}  delay={CFG.delay_ms:g} ms  workers={CFG.workers}  "
          f"pids={[os.getpid()] + children}", flush=True)
    serve(sock)


if __name__ == "__main__":
    main()
