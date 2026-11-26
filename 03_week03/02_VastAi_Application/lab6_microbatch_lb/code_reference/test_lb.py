"""Run OUTSIDE the rented machine: test the system through NGINX (public port mapped to 8080).

usage: python test_lb.py <public_host> <public_port> <image.jpg> <out.json>     (API_KEY comes from the environment)
The key is never printed and never written to the output file.
"""
import json
import os
import socket
import sys
import time

import requests

HOST, PORT, IMAGE, OUT = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
URL = f"http://{HOST}:{PORT}"
KEY = os.environ["API_KEY"]
rows = []


def post(headers):
    with open(IMAGE, "rb") as fh:
        t0 = time.perf_counter()
        r = requests.post(f"{URL}/v1/detect", headers=headers,
                          files={"file": (os.path.basename(IMAGE), fh, "image/jpeg")}, timeout=60)
    return r, round((time.perf_counter() - t0) * 1000, 1)


def add(name, expect, r, ms, extra=None):
    row = {"test": name, "expect": expect, "status_code": r.status_code, "pass": r.status_code == expect,
           "client_ms": ms, "answered_by": r.headers.get("X-Rejected-By") or r.headers.get("X-Upstream") or "nginx",
           "www_authenticate": r.headers.get("WWW-Authenticate")}
    row.update(extra or {})
    rows.append(row)
    return row


t0 = time.perf_counter(); r = requests.get(f"{URL}/lb/health", timeout=15)
add("GET /lb/health (nginx itself)", 200, r, round((time.perf_counter() - t0) * 1000, 1), {"body": r.json()})

t0 = time.perf_counter(); r = requests.get(f"{URL}/health", timeout=15)
h = r.json()
add("GET /health (forwarded to a server)", 200, r, round((time.perf_counter() - t0) * 1000, 1),
    {"body": {k: h.get(k) for k in ("status", "server", "mode", "max_batch", "device")}})

r, ms = post({"Authorization": f"Bearer {KEY}"})
b = r.json() if r.status_code == 200 else {}
counts = {}
for d in b.get("detections", []):
    counts[d["class_name"]] = counts.get(d["class_name"], 0) + 1
add("POST /v1/detect, 1 image, with key", 200, r, ms,
    {"image_bytes": os.path.getsize(IMAGE), "server": b.get("server"), "mode": b.get("mode"),
     "batch_size": b.get("batch_size"), "queue_ms": b.get("queue_ms"), "model_ms": b.get("model_ms"),
     "objects": b.get("count"), "classes": counts})

r, ms = post({})
add("POST /v1/detect, no key", 401, r, ms, {"body": r.json()})

r, ms = post({"Authorization": "Bearer this-is-not-the-key"})
add("POST /v1/detect, wrong key", 401, r, ms, {"body": r.json()})

t0 = time.perf_counter(); r = requests.get(f"{URL}/anything-else", timeout=15)
add("GET /anything-else (unknown path)", 404, r, round((time.perf_counter() - t0) * 1000, 1))

# the server port itself must not be reachable from outside
s = socket.socket(); s.settimeout(5)
try:
    s.connect((HOST, 8101)); reach = "open"
except Exception as exc:
    reach = type(exc).__name__
finally:
    s.close()
rows.append({"test": f"TCP connect {HOST}:8101 (server port, from outside)", "expect": "not reachable",
             "result": reach, "pass": reach != "open"})

json.dump({"url": URL, "image": os.path.basename(IMAGE), "tests": rows}, open(OUT, "w"), indent=2, ensure_ascii=False)
for row in rows:
    print("PASS" if row["pass"] else "FAIL", "|", row["test"], "|", row.get("status_code", row.get("result")),
          "|", row.get("answered_by", ""), "|", row.get("client_ms", ""), "ms",
          "|", {k: row[k] for k in ("server", "mode", "batch_size", "model_ms", "objects", "classes") if k in row} or "")
sys.exit(0 if all(row["pass"] for row in rows) else 1)
