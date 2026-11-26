#!/usr/bin/env python3
"""Tiny TCP network tester (one port is enough for every test).

  server:  nettest.py server PORT
  client:  nettest.py client HOST PORT [--secs 10] [--pings 50]

Each client connection starts with a one-line command:
  ECHO          server echoes 1-byte probes        -> round-trip time (RTT)
  SINK          client sends for N s, server counts -> client->server throughput
  SOURCE N      server sends for N s, client counts -> server->client throughput
"""
import argparse, json, socket, statistics, threading, time

BUF = b"\0" * (1 << 20)


def readline(c):
    b = b""
    while not b.endswith(b"\n"):
        d = c.recv(1)
        if not d:
            break
        b += d
    return b.decode().strip()


def handle(c):
    try:
        c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        cmd = readline(c).split()
        if not cmd:
            return
        if cmd[0] == "ECHO":
            while True:
                d = c.recv(64)
                if not d:
                    break
                c.sendall(d)
        elif cmd[0] == "SINK":
            n, t0 = 0, None
            while True:
                d = c.recv(1 << 20)
                if not d:
                    break
                t0 = t0 or time.perf_counter()
                n += len(d)
        elif cmd[0] == "SOURCE":
            end = time.perf_counter() + float(cmd[1])
            while time.perf_counter() < end:
                c.sendall(BUF)
    except OSError:
        pass
    finally:
        c.close()


def server(port):
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", port))
    s.listen(16)
    print(f"listening on {port}", flush=True)
    while True:
        c, _ = s.accept()
        threading.Thread(target=handle, args=(c,), daemon=True).start()


def connect(host, port):
    t = time.perf_counter()
    c = socket.create_connection((host, port), timeout=10)
    dt = (time.perf_counter() - t) * 1000
    c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    return c, dt


def client(host, port, secs, pings):
    out = {"target": f"{host}:{port}"}
    try:
        c, dt = connect(host, port)
    except OSError as e:
        out.update(connect_ok=False, error=str(e))
        print(json.dumps(out, indent=2))
        return
    out.update(connect_ok=True, tcp_connect_ms=round(dt, 3))
    # RTT: application-level echo of one byte
    c.sendall(b"ECHO\n")
    rtts = []
    for _ in range(pings):
        t = time.perf_counter()
        c.sendall(b"x")
        c.recv(1)
        rtts.append((time.perf_counter() - t) * 1000)
        time.sleep(0.05)
    c.close()
    rtts = rtts[1:]
    out["rtt_ms"] = {"min": round(min(rtts), 3), "avg": round(statistics.mean(rtts), 3),
                     "median": round(statistics.median(rtts), 3), "max": round(max(rtts), 3),
                     "samples": len(rtts)}
    # client -> server
    c, _ = connect(host, port)
    c.sendall(b"SINK\n")
    n, t0 = 0, time.perf_counter()
    while time.perf_counter() - t0 < secs:
        c.sendall(BUF)
        n += len(BUF)
    c.shutdown(socket.SHUT_WR)
    c.settimeout(60)
    while c.recv(1 << 16):      # wait until the server has drained everything
        pass
    dt = time.perf_counter() - t0
    c.close()
    out["client_to_server"] = {"bytes": n, "seconds": round(dt, 2),
                               "mbps": round(n * 8 / dt / 1e6, 1)}
    # server -> client
    c, _ = connect(host, port)
    c.sendall(f"SOURCE {secs}\n".encode())
    n, t0 = 0, None
    while True:
        d = c.recv(1 << 20)
        if not d:
            break
        t0 = t0 or time.perf_counter()
        n += len(d)
    dt = time.perf_counter() - t0
    c.close()
    out["server_to_client"] = {"bytes": n, "seconds": round(dt, 2),
                               "mbps": round(n * 8 / dt / 1e6, 1)}
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)
    s = sub.add_parser("server"); s.add_argument("port", type=int)
    c = sub.add_parser("client"); c.add_argument("host"); c.add_argument("port", type=int)
    c.add_argument("--secs", type=float, default=10); c.add_argument("--pings", type=int, default=50)
    a = ap.parse_args()
    server(a.port) if a.mode == "server" else client(a.host, a.port, a.secs, a.pings)
