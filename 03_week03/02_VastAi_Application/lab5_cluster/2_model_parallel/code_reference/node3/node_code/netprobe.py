#!/usr/bin/env python3
"""TCP probe between nodes (no extra packages).

server:  netprobe.py server <listen_port>
client:  netprobe.py client <host> <port> [seconds]
Protocol per connection (first byte): P=ping echo (RTT), U=client uploads, D=server sends to client.
Client prints one JSON line: reachability, RTT stats (ms), throughput both directions (Mbit/s).
"""
import json, socket, statistics, struct, sys, threading, time

CHUNK = b"\0" * (1 << 20)

def recvn(s, n):
    b = b""
    while len(b) < n:
        c = s.recv(n - len(b))
        if not c: raise EOFError
        b += c
    return b

def handle(c):
    try:
        c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        mode = recvn(c, 1)
        if mode == b"P":
            while True:
                c.sendall(recvn(c, 8))
        elif mode == b"U":          # client -> server; reply with byte count + elapsed
            n = 0; t0 = time.time()
            while True:
                d = c.recv(1 << 20)
                if not d: break
                n += len(d)
            c.sendall(struct.pack("!Qd", n, time.time() - t0))
        elif mode == b"D":          # server -> client for <secs>
            secs = struct.unpack("!d", recvn(c, 8))[0]
            end = time.time() + secs
            while time.time() < end:
                c.sendall(CHUNK)
    except (EOFError, OSError):
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

def conn(host, port):
    s = socket.create_connection((host, port), timeout=15)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    return s

def client(host, port, secs):
    out = {"target": f"{host}:{port}", "connect_ok": False}
    try:
        t0 = time.perf_counter(); s = conn(host, port)
        out["connect_ms"] = round((time.perf_counter() - t0) * 1000, 2); out["connect_ok"] = True
    except OSError as e:
        out["error"] = str(e); print(json.dumps(out)); return
    s.sendall(b"P"); rtts = []
    for i in range(30):
        t0 = time.perf_counter(); s.sendall(struct.pack("!Q", i)); recvn(s, 8)
        rtts.append((time.perf_counter() - t0) * 1000); time.sleep(0.05)
    s.close()
    rtts = rtts[1:]
    out.update(rtt_min_ms=round(min(rtts), 2), rtt_avg_ms=round(statistics.mean(rtts), 2),
               rtt_med_ms=round(statistics.median(rtts), 2), rtt_max_ms=round(max(rtts), 2), rtt_n=len(rtts))
    # upload: this node -> server
    s = conn(host, port); s.settimeout(60); s.sendall(b"U"); end = time.time() + secs
    while time.time() < end: s.sendall(CHUNK)
    s.shutdown(socket.SHUT_WR); n, el = struct.unpack("!Qd", recvn(s, 16)); s.close()
    out.update(up_mbps=round(n * 8 / el / 1e6, 1), up_mb=round(n / 1e6, 1))
    # download: server -> this node
    s = conn(host, port); s.settimeout(60); s.sendall(b"D" + struct.pack("!d", secs)); n = 0; t0 = time.time()
    while True:
        d = s.recv(1 << 20)
        if not d: break
        n += len(d)
    el = time.time() - t0; s.close()
    out.update(down_mbps=round(n * 8 / el / 1e6, 1), down_mb=round(n / 1e6, 1), seconds=secs)
    print(json.dumps(out))

if __name__ == "__main__":
    if sys.argv[1] == "server": server(int(sys.argv[2]))
    else: client(sys.argv[2], int(sys.argv[3]), float(sys.argv[4]) if len(sys.argv) > 4 else 10)
