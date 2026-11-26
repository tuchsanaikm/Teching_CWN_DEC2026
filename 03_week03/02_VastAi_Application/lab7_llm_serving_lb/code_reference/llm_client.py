"""Tiny streaming client for an OpenAI-compatible /v1/chat/completions (standard library only).

TTFT        = time from sending the request to the first content token arriving.
tokens/sec  = (completion_tokens - 1) / (time of last token - time of first token)
              i.e. generation speed after the first token; completion_tokens comes from the server's usage.
"""
import json, time, http.client, urllib.parse

SYSTEM = ("You are shop-bot, the customer-service assistant of a household-goods store. "
          "Answer briefly and practically in the language of the customer.")


def ask(base_url, key, question, model="shop-bot", max_tokens=200, timeout=300):
    u = urllib.parse.urlparse(base_url)
    body = json.dumps({
        "model": model, "stream": True, "max_tokens": max_tokens, "temperature": 0.2,
        "stream_options": {"include_usage": True},
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}],
    })
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    conn = http.client.HTTPConnection(u.hostname, u.port, timeout=timeout)
    t0 = time.perf_counter()
    conn.request("POST", "/v1/chat/completions", body, headers)
    r = conn.getresponse()
    out = {"status": r.status, "replica": r.getheader("X-Replica"), "replica_addr": r.getheader("X-Replica-Addr")}
    if r.status != 200:
        out["error"] = r.read().decode("utf-8", "replace").strip()[:300]
        conn.close()
        return out
    text, t_first, t_last, usage, arrivals = [], None, None, None, []
    while True:
        line = r.readline()
        if not line:
            break
        line = line.strip()
        if not line.startswith(b"data:"):
            continue
        data = line[5:].strip()
        if data == b"[DONE]":
            break
        ev = json.loads(data)
        if ev.get("usage"):
            usage = ev["usage"]
        for ch in ev.get("choices") or []:
            piece = (ch.get("delta") or {}).get("content")
            if piece:
                now = time.perf_counter()
                if t_first is None:
                    t_first = now
                t_last = now
                arrivals.append(now - t0)
                text.append(piece)
    t_end = time.perf_counter()
    conn.close()
    n = (usage or {}).get("completion_tokens") or len(text)
    gen = (t_last - t_first) if t_first is not None else 0
    out.update({
        "answer": "".join(text),
        "prompt_tokens": (usage or {}).get("prompt_tokens"),
        "completion_tokens": n,
        "ttft_s": round(t_first - t0, 4) if t_first else None,
        "total_s": round(t_end - t0, 4),
        "tokens_per_s": round((n - 1) / gen, 2) if gen > 0 and n > 1 else None,
        "stream_chunks": len(text),
        # proof of token-by-token delivery: chunks arrive spread over the whole generation time
        "chunk_gap_ms_median": round(1000 * sorted(b - a for a, b in zip(arrivals, arrivals[1:]))[len(arrivals) // 2 - 1], 1) if len(arrivals) > 2 else None,
        "chunk_gap_ms_max": round(1000 * max(b - a for a, b in zip(arrivals, arrivals[1:])), 1) if len(arrivals) > 2 else None,
    })
    return out
