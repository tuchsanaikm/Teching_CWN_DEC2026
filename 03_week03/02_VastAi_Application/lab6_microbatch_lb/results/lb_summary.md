# LAB 6 - NGINX Round Robin vs Least Connections (layout 4: 2 GPUs x 4 servers, micro-batching)

Pass = p95 <= 500 ms and errors < 1 %. Capacity = largest N (concurrent users) that passes.
Share and GPU % are gpu0 / gpu1.

## Equal GPUs

| method | result | capacity N | max throughput | throughput at capacity | p95 at capacity | requests share at capacity | GPU busy at capacity | share ; GPU busy at max throughput |
|---|---|---|---|---|---|---|---|---|
| Round Robin | gpu2 | 180 | 566.5 req/s (N=512) | 553.4 req/s | 490.3 ms | 50.0 % / 50.0 % | 85 % / 83 % | 50.0 % / 50.0 % ; 85 % / 84 % |
| Least Connections | lc_equal | 250 | 561.1 req/s (N=512) | 560.7 req/s | 493.3 ms | 49.8 % / 50.2 % | 82 % / 83 % | 49.8 % / 50.2 % ; 76 % / 81 % |

- gpu2: capacity 180 (first failing N above it: 183), 19 runs, errors 2 of 125249 measured requests, gpu1 slowdown in /health: None
- lc_equal: capacity 250 (first failing N above it: 253), 18 runs, errors 1 of 117905 measured requests, gpu1 slowdown in /health: 1.0

## GPU 1 is 3x slower

| method | result | capacity N | max throughput | throughput at capacity | p95 at capacity | requests share at capacity | GPU busy at capacity | share ; GPU busy at max throughput |
|---|---|---|---|---|---|---|---|---|
| Round Robin | rr_slow | 52 | 223.4 req/s (N=128) | 219.9 req/s | 495.9 ms | 50.0 % / 50.0 % | 55 % / 95 % | 50.0 % / 50.0 % ; 47 % / 93 % |
| Least Connections | lc_slow | 103 | 389.3 req/s (N=256) | 370.0 req/s | 493.5 ms | 70.8 % / 29.2 % | 82 % / 93 % | 70.4 % / 29.6 % ; 80 % / 93 % |

- rr_slow: capacity 52 (first failing N above it: 53), 13 runs, errors 0 of 33290 measured requests, gpu1 slowdown in /health: 3.0
- lc_slow: capacity 103 (first failing N above it: 107), 14 runs, errors 0 of 59232 measured requests, gpu1 slowdown in /health: 3.0

## Notes (measured 2026-11-23, same machine and same server/loadgen code for all runs)

- NGINX config: the saved copies `rr_slow_nginx.conf` and `lc_slow_nginx.conf` differ in exactly one line
  (`least_conn;` vs a comment); `lc_equal_nginx.conf` = `lc_slow_nginx.conf`. gpu2 (Round Robin, equal GPUs) is the
  earlier run and was not measured again as a full search.
- Slow GPU: `cluster.sh up --slow-gpu 1 --slow-factor 3` -> the 4 servers of GPU 1 run with MODEL_SLOWDOWN=3
  (server.py does every model call 3 times, so the card is really busy). Direct check on one server each, N=8:
  fast 109.7 req/s, 33.3 ms per model call at 6.1 images per call (slow_check_8101); slowed 52.6 req/s, 69.7 ms per
  call at 4.0 images per call (slow_check_8201). The batch sizes differ, so this check does not show an exact 3x.
- At capacity, slow case: Round Robin gives each server 412-413 requests; GPU-1 servers wait 160-176 ms in queue and
  212-234 ms in the model, GPU-0 servers 12-13 ms and 23 ms (1.2 images per call, GPU 0 only 55 % busy).
  Least Connections gives GPU-0 servers 974-995 requests and GPU-1 servers 403-410 (70.8 % / 29.2 %).
- Round Robin control after the restore (single levels, equal GPUs, not part of the capacity numbers):
  N=180 p95 392.2 / 468.7 ms (pass) and 640.6 ms (fail: server gpu0-8102 got 559 instead of ~1048 requests - NGINX
  took it out for 10 s after a connection reset, the max_fails behaviour already seen in gpu2); N=250 p95 705.3 / 696.6 ms
  (fail twice). Least Connections at N=250: 493.3 ms (pass). So the Round Robin capacity of 180 moves by run
  (p95 at N=180 was 392-490 ms in 4 clean runs), but it stays clearly below 250.
- lc_equal had 1 HTTP 502 (N=237, first run, 0.01 %); rr_slow and lc_slow had 0 errors.
- Search gap: lc_equal N 251-252 and lc_slow N 104-106 were not measured (search stops at a gap of 4 above N=100).
- After the runs: `cluster.sh up --gpus 2 --per-gpu 4 --mode micro --lb rr` (no slow GPU), status OK
  (lb_final_cluster_status.txt).
