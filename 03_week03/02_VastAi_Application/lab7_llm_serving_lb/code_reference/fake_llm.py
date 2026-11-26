#!/usr/bin/env python3
"""Fake LLM server: no model, no GPU, answers with a timing that is known in advance.

It accepts the same request as the real chatbot (POST /v1/chat/completions, OpenAI format,
streaming SSE with usage in every chunk) so the load generator can be checked against it.

  fake_llm.py --port 9000 --ttft-ms 200 --interval-ms 20 --tokens 100 [--workers 8]

  --ttft-ms      wait this long before the first token
  --interval-ms  then one token every this many ms   (0 = as fast as possible)
  --tokens       tokens per answer
  Timeline of one answer: token k (k = 1..tokens) leaves at  ttft + (k-1) * interval,
  the answer ends ([DONE]) at ttft + tokens * interval.  -> 200/20/100 = 2.2 s per answer.

Any number of requests at the same time (one coroutine each, several worker processes on one port).
Every chat request is counted in memory shared by all workers.

  GET  /stats    {"requests": .., "finished": .., "aborted": .., "running": .., "tokens_sent": .., settings}
  POST /reset    counters back to 0
  POST /config   {"ttft_ms": .., "interval_ms": .., "tokens": ..}  change the 3 settings while running
  GET  /metrics  vllm:num_requests_running / _waiting (so the load generator's replica monitor works)
  GET  /health, /v1/models
"""
import argparse, asyncio, json, multiprocessing as mp, os, signal, socket, sys, time

YIELD_EVERY = 32          # fastest mode: let other answers run after this many tokens

# counters shared by all worker processes: requests, finished, aborted, running, tokens_sent
C_REQ, C_FIN, C_ABORT, C_RUN, C_TOK = range(5)
# settings shared by all workers: ttft_ms, interval_ms, tokens, version (bumped on every change)
S_TTFT, S_INT, S_TOK, S_VER = range(4)


def http_chunk(payload: bytes) -> bytes:
    """One HTTP/1.1 chunk (Transfer-Encoding: chunked)."""
    return b"%x\r\n%s\r\n" % (len(payload), payload)


def sse(obj) -> bytes:
    return http_chunk(b"data: " + json.dumps(obj, separators=(",", ":")).encode() + b"\n\n")


def build_stream(n_tokens, model="shop-bot", prompt_tokens=40):
    """All chunks of one answer, encoded once. Returns (head, [token chunks], tail)."""
    base = {"id": "chatcmpl-fake", "object": "chat.completion.chunk", "created": int(time.time()), "model": model}

    def usage(k):
        return {"prompt_tokens": prompt_tokens, "total_tokens": prompt_tokens + k, "completion_tokens": k}

    head = sse(dict(base, choices=[{"index": 0, "delta": {"role": "assistant", "content": ""},
                                    "logprobs": None, "finish_reason": None}], usage=usage(0)))
    toks = [sse(dict(base, choices=[{"index": 0, "delta": {"content": "t%d " % k}, "logprobs": None,
                                     "finish_reason": None}], usage=usage(k))) for k in range(1, n_tokens + 1)]
    tail = (sse(dict(base, choices=[{"index": 0, "delta": {"content": ""}, "logprobs": None,
                                     "finish_reason": "length"}], usage=usage(n_tokens)))
            + sse(dict(base, choices=[], usage=usage(n_tokens)))
            + http_chunk(b"data: [DONE]\n\n") + b"0\r\n\r\n")
    return head, toks, tail


SSE_HEAD = (b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream; charset=utf-8\r\n"
            b"Cache-Control: no-cache\r\nTransfer-Encoding: chunked\r\n\r\n")


def plain(status, obj, ctype=b"application/json"):
    body = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
    return b"HTTP/1.1 %s\r\nContent-Type: %s\r\nContent-Length: %d\r\n\r\n%s" % (status, ctype, len(body), body)


class Worker:
    def __init__(self, counters, settings, lock):
        self.c, self.s, self.lock = counters, settings, lock
        self.ver, self.stream = -1, None

    def add(self, i, n=1):
        with self.lock:
            self.c[i] += n

    def current(self):
        """(ttft_s, interval_s, head, tokens, tail) for the settings valid right now."""
        if self.ver != self.s[S_VER]:
            with self.lock:
                self.ver, self.cfg = self.s[S_VER], (self.s[S_TTFT] / 1000.0, self.s[S_INT] / 1000.0, int(self.s[S_TOK]))
            self.stream = build_stream(self.cfg[2])
        return self.cfg[0], self.cfg[1], self.stream

    async def chat(self, writer, body):
        """One answer. Tokens leave on an absolute timetable, so a late wake-up does not add up."""
        ttft, interval, (head, toks, tail) = self.current()
        loop = asyncio.get_running_loop()
        t0 = loop.time()
        self.add(C_REQ)
        self.add(C_RUN)
        sent, ok = 0, False
        try:
            stream = True
            try:
                stream = bool(json.loads(body).get("stream", False))
            except Exception:
                pass
            if not stream:                                    # whole answer at the end, like a non-streaming call
                await asyncio.sleep(ttft + interval * len(toks))
                sent = len(toks)
                writer.write(plain(b"200 OK", {
                    "id": "chatcmpl-fake", "object": "chat.completion", "model": "shop-bot",
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": "".join("t%d " % k for k in range(1, sent + 1))},
                                 "finish_reason": "length"}],
                    "usage": {"prompt_tokens": 40, "completion_tokens": sent, "total_tokens": 40 + sent}}))
                await writer.drain()
                ok = True
                return
            if ttft > 0:
                await asyncio.sleep(ttft)
            writer.write(SSE_HEAD + head)
            for k, chunk in enumerate(toks):
                if interval > 0:
                    d = t0 + ttft + k * interval - loop.time()
                    if d > 0:
                        await asyncio.sleep(d)
                elif k % YIELD_EVERY == YIELD_EVERY - 1:
                    await asyncio.sleep(0)
                writer.write(chunk)
                sent += 1
                await writer.drain()                          # waits only when the client reads too slowly
            if interval > 0:
                d = t0 + ttft + len(toks) * interval - loop.time()
                if d > 0:
                    await asyncio.sleep(d)
            writer.write(tail)
            await writer.drain()
            ok = True
        finally:
            with self.lock:
                self.c[C_RUN] -= 1
                self.c[C_TOK] += sent
                self.c[C_FIN if ok else C_ABORT] += 1

    def stats(self):
        with self.lock:
            return {"requests": self.c[C_REQ], "finished": self.c[C_FIN], "aborted": self.c[C_ABORT],
                    "running": self.c[C_RUN], "tokens_sent": self.c[C_TOK],
                    "ttft_ms": self.s[S_TTFT], "interval_ms": self.s[S_INT], "tokens": int(self.s[S_TOK])}

    async def handle(self, reader, writer):
        """One TCP connection (keep-alive: several requests one after the other)."""
        sock = writer.get_extra_info("socket")
        if sock is not None:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)   # every token leaves at once
        try:
            while True:
                try:
                    raw = await reader.readuntil(b"\r\n\r\n")
                except (asyncio.IncompleteReadError, asyncio.LimitOverrunError):
                    return
                lines = raw.split(b"\r\n")
                parts = lines[0].split()
                if len(parts) < 2:
                    return
                method, path = parts[0], parts[1].split(b"?")[0]
                clen, close = 0, False
                for h in lines[1:]:
                    k, _, v = h.partition(b":")
                    k = k.strip().lower()
                    if k == b"content-length":
                        clen = int(v)
                    elif k == b"connection" and v.strip().lower() == b"close":
                        close = True
                body = await reader.readexactly(clen) if clen else b""
                if method == b"POST" and path == b"/v1/chat/completions":
                    await self.chat(writer, body)
                elif path == b"/stats":
                    writer.write(plain(b"200 OK", self.stats()))
                elif method == b"POST" and path == b"/reset":
                    with self.lock:
                        for i in (C_REQ, C_FIN, C_ABORT, C_TOK):
                            self.c[i] = 0
                    writer.write(plain(b"200 OK", self.stats()))
                elif method == b"POST" and path == b"/config":
                    try:
                        new = json.loads(body or b"{}")
                        with self.lock:
                            for name, i in (("ttft_ms", S_TTFT), ("interval_ms", S_INT), ("tokens", S_TOK)):
                                if name in new:
                                    if float(new[name]) < 0 or (name == "tokens" and int(new[name]) < 1):
                                        raise ValueError(name)
                                    self.s[i] = float(new[name])
                            self.s[S_VER] += 1
                        writer.write(plain(b"200 OK", self.stats()))
                    except Exception as e:
                        writer.write(plain(b"400 Bad Request", {"error": {"message": "bad config: %s" % e}}))
                elif path == b"/metrics":
                    run = self.stats()["running"]
                    writer.write(plain(b"200 OK", (
                        'vllm:num_requests_running{model_name="shop-bot"} %d.0\n'
                        'vllm:num_requests_waiting{model_name="shop-bot"} 0.0\n' % run).encode(), b"text/plain"))
                elif path == b"/health":
                    writer.write(plain(b"200 OK", b"{}"))
                elif path == b"/v1/models":
                    writer.write(plain(b"200 OK", {"object": "list", "data": [{"id": "shop-bot", "object": "model", "owned_by": "fake"}]}))
                else:
                    writer.write(plain(b"404 Not Found", {"error": {"message": "not found"}}))
                await writer.drain()
                if close:
                    return
        except (ConnectionError, asyncio.CancelledError, OSError):
            pass
        finally:
            try:
                writer.close()
            except Exception:
                pass


def worker_entry(host, port, counters, settings, lock):
    try:
        import uvloop
        uvloop.install()
    except Exception:
        pass
    w = Worker(counters, settings, lock)

    async def main():
        srv = await asyncio.start_server(w.handle, host, port, reuse_port=True, backlog=4096, limit=1 << 20)
        async with srv:
            await srv.serve_forever()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--ttft-ms", type=float, default=200.0, help="wait before the first token")
    ap.add_argument("--interval-ms", type=float, default=20.0, help="time between tokens (0 = as fast as possible)")
    ap.add_argument("--tokens", type=int, default=100, help="tokens per answer")
    ap.add_argument("--workers", type=int, default=8, help="server processes sharing the port")
    a = ap.parse_args()
    ctx = mp.get_context("fork")
    lock = ctx.Lock()
    counters = ctx.Array("q", 5, lock=False)
    settings = ctx.Array("d", [a.ttft_ms, a.interval_ms, a.tokens, 0.0], lock=False)
    ws = [ctx.Process(target=worker_entry, args=(a.host, a.port, counters, settings, lock), daemon=True)
          for _ in range(a.workers)]
    for w in ws:
        w.start()
    print("fake_llm on %s:%d  workers=%d  ttft=%gms interval=%gms tokens=%d  pid=%d" % (
        a.host, a.port, a.workers, a.ttft_ms, a.interval_ms, a.tokens, os.getpid()), flush=True)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        while all(w.is_alive() for w in ws):
            time.sleep(1.0)
    finally:
        for w in ws:
            w.terminate()


if __name__ == "__main__":
    main()
