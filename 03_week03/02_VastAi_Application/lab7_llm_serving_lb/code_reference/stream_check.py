#!/usr/bin/env python3
"""Runs ON machine 1: is NGINX passing tokens on one by one? Same question direct to a replica and through NGINX.
usage: stream_check.py <key_file> <out.json>   (no internet in between, so chunk gaps show only server + NGINX)"""
import sys, json
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from llm_client import ask
key = open(sys.argv[1]).read().strip()
q = "ขอวิธีดูแลเขียงไม้ให้ใช้ได้นานหน่อย"
out = {}
for name, url in (("direct_replica_n1_gpu0", "http://127.0.0.1:8001"), ("through_nginx_8080", "http://127.0.0.1:8080")):
    ask(url, key, "สวัสดี", max_tokens=8)
    r = ask(url, key, q, max_tokens=200)
    out[name] = {k: r[k] for k in ("status", "replica", "completion_tokens", "stream_chunks", "ttft_s", "total_s",
                                   "tokens_per_s", "chunk_gap_ms_median", "chunk_gap_ms_max")}
    print(name, out[name])
json.dump(out, open(sys.argv[2], "w"), indent=1)
