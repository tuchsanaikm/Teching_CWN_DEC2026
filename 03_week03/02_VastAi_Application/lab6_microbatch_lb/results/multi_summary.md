# LAB 6 - capacity of 3 layouts (1x RTX 3090, YOLO11s 640, NGINX round robin, pass = p95 <= 500 ms and errors < 1 %)

| layout | capacity N | max throughput | p95 at capacity | images / model call at capacity | GPU % | server CPU % | VRAM | x layout 1 |
|---|---|---|---|---|---|---|---|---|
| 1 base: 1 server, 1 image per call | 29 | 62.6 req/s (N=29) | 494.4 ms | 1.0 | 22 | 136 | 522 MiB | 1.00 |
| 2 batch: 1 server, micro-batching 32 / 5 ms | 52 | 142.9 req/s (N=64) | 490.0 ms | 26.0 | 31 | 181 | 13812 MiB | 1.79 |
| 3 multi: 4 servers on the same GPU, micro-batching | 90 | 278.7 req/s (N=128) | 468.4 ms | 11.0 | 82 | 535 (4 processes) | 14001-14017 MiB | 3.10 |

GPU % and CPU % are from the passing run at the capacity level. VRAM: layouts 1-2 = nvidia-smi right after start,
layout 3 = min-max of 212 samples (every 2 s) during the whole search (multi_vram.csv).

multi: N=90 passes (p95 468.4), N=91 fails twice (537.2, 513.3). Requests at N=90: 1007/1007/1008/1008 = 25.0 % each.
Two failing levels far above the capacity were NOT even: N=128 2nd run (8101 got 441 vs ~1158) and N=256 1st run
(8103 got 278 vs ~1215, 3x HTTP 502). Cause (multi_nginx_error.log): the server reset a connection, NGINX default
max_fails=1 / fail_timeout=10s took that server out of the rotation for 10 s. Not changed in this task.
