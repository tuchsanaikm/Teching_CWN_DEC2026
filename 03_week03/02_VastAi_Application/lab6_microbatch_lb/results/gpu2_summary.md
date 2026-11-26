# LAB 6 - capacity of 4 layouts (RTX 3090, YOLO11s 640, NGINX round robin, pass = p95 <= 500 ms and errors < 1 %)

| # | GPUs | layout | capacity N | max throughput | p95 at capacity | x layout 3 | efficiency (x layout 3 / GPUs) |
|---|---|---|---|---|---|---|---|
| 1 | 1 | base: 1 server, 1 image per call | 29 | 62.6 req/s (N=29) | 494.4 ms | 0.32 | 0.32 |
| 2 | 1 | batch: 1 server, micro-batching 32 / 5 ms | 52 | 142.9 req/s (N=64) | 490.0 ms | 0.58 | 0.58 |
| 3 | 1 | multi: 4 servers on the GPU, micro-batching | 90 | 278.7 req/s (N=128) | 468.4 ms | 1.00 | 1.00 |
| 4 | 2 | gpu2: 4 servers on each GPU, micro-batching | 180 | 566.5 req/s (N=512) | 490.3 ms | 2.00 | 1.00 |

gpu2: N=180 passes (p95 490.3, 0 errors of 8299), N=183 fails twice (520.1, 514.0); N 181-182 not measured.
Requests at N=180: gpu0 4149 / gpu1 4150; each of the 8 servers 1037-1038 (12.5 %).
At N=180: GPU util 85 % / 83 %, 8 server processes 1090 % CPU (of 64 cores), nginx 12 %, loadgen 19 %, 12.1 images per model call.
Throughput is flat at ~550-566 req/s from N=142 to N=512 = 2 x the ~272-279 req/s of layout 3.

One level was not even: N=128 (passed, p95 476.1) - server gpu0-8102 got 277 requests, the other seven 1027 each,
2 x HTTP 502 (0.03 %). Same cause as in layout 3 (gpu2_nginx_error.log): the server reset 2 connections, NGINX default
max_fails=1 / fail_timeout=10s took it out of the rotation for 10 s. NGINX settings were not changed.

Difference to the layout 3 run: the first start of 8 servers died with CUDA out of memory during the parallel warm-up
(GPU 0). cluster.sh now gives every server GPU_MEM_FRACTION = 0.85 / per-gpu (server.py: set_per_process_memory_fraction).
VRAM then 8057-9681 MiB per GPU (201 samples, gpu2_vram.csv) instead of ~14000 MiB. Layout 3 was NOT measured again
with this limit; at the same load per GPU the two runs agree (layout 3 saturates at 267-279 req/s, layout 4 at 275-283 per GPU).
