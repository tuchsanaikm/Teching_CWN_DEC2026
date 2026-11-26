#!/usr/bin/env python3
"""Tiny TCP probe (own code, stdlib only).
  server: net_probe.py server PORT
  client: net_probe.py client HOST PORT [seconds]
Protocol (first byte): P = echo ping, U = client uploads (server counts), D = server sends.
Client prints one JSON line: reachability, RTT stats, throughput both directions."""
import json, socket, statistics, struct, sys, threading, time
CHUNK = b"\0" * (1 << 18)

def recvn(s, n):
    buf = b""
    while len(buf) < n:
        d = s.recv(n - len(buf))
        if not d: raise ConnectionError("closed")
        buf += d
    return buf

def handle(c):
    try:
        c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        mode = recvn(c, 1)
        if mode == b"P":
            while True:
                d = c.recv(64)
                if not d: break
                c.sendall(d)
        elif mode == b"U":
            n = 0; t0 = time.time()
            while True:
                d = c.recv(1 << 20)
                if not d: break
                n += len(d)
            # peer half-closed; report what we really received
            c.sendall(struct.pack("!Qd", n, time.time() - t0))
        elif mode == b"D":
            secs = struct.unpack("!d", recvn(c, 8))[0]
            end = time.time() + secs
            while time.time() < end:
                c.sendall(CHUNK)
    except Exception:
        pass
    finally:
        c.close()

def server(port):
    s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", port)); s.listen(16)
    print("listening", port, flush=True)
    while True:
        c, _ = s.accept()
        threading.Thread(target=handle, args=(c,), daemon=True).start()

def client(host, port, secs):
    res = {"target": f"{host}:{port}"}
    try:
        t0 = time.perf_counter()
        s = socket.create_connection((host, port), timeout=10)
        res["connect_ms"] = round((time.perf_counter() - t0) * 1e3, 2)
        res["reachable"] = True
    except Exception as e:
        res.update(reachable=False, error=repr(e)); print(json.dumps(res)); return
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    s.sendall(b"P"); rt = []
    for i in range(55):
        t0 = time.perf_counter(); s.sendall(b"x" * 16); recvn(s, 16)
        rt.append((time.perf_counter() - t0) * 1e3)
    s.close(); rt = rt[5:]
    res["rtt_ms"] = {"n": len(rt), "min": round(min(rt), 2), "avg": round(statistics.mean(rt), 2),
                     "median": round(statistics.median(rt), 2), "max": round(max(rt), 2)}
    # upload: this node -> server
    s = socket.create_connection((host, port), timeout=10); s.sendall(b"U")
    end = time.time() + secs
    while time.time() < end: s.sendall(CHUNK)
    s.shutdown(socket.SHUT_WR); s.settimeout(60)
    n, dt = struct.unpack("!Qd", recvn(s, 16)); s.close()
    res["send_to_server_mbps"] = round(n * 8 / dt / 1e6, 1); res["send_bytes"] = n
    # download: server -> this node
    s = socket.create_connection((host, port), timeout=10); s.sendall(b"D" + struct.pack("!d", secs))
    n = 0; t0 = time.time()
    while True:
        d = s.recv(1 << 20)
        if not d: break
        n += len(d)
    dt = time.time() - t0; s.close()
    res["recv_from_server_mbps"] = round(n * 8 / dt / 1e6, 1); res["recv_bytes"] = n
    print(json.dumps(res))

if __name__ == "__main__":
    if sys.argv[1] == "server": server(int(sys.argv[2]))
    else: client(sys.argv[2], int(sys.argv[3]), float(sys.argv[4]) if len(sys.argv) > 4 else 10)
