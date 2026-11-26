# LAB 6 - one GPU dies in the middle (layout 4: 2 GPUs x 4 servers, micro-batching, NGINX Round Robin)

Load: 60 users (= 1/3 of the layout 4 capacity of 180, gpu2.json), single level 60 s (first 5 s warm-up).
At second 20.0 `cluster.sh kill-gpu 1` kills the 4 servers of the 2nd GPU (gpu1, ports 8201-8204) with SIGKILL
(done after 0.31-0.35 s). One run per setting, RTX 3090 x 2, 2026-11-23.

| | fail_off (`--failover off`) | fail_on (`--failover on`) |
|---|---|---|
| errors / all requests (warm-up included) | 11206 / 32769 = 34.2 % (all HTTP 502) | 0 / 20413 = 0 % |
| - of the 60 requests in flight at the kill | 21 failed | 0 failed |
| - requests started after the kill | 11087 / 22175 = 50.0 % | 0 / 10218 |
| successful throughput before (5-20 s) | 522.1 req/s | 506.3 req/s |
| successful throughput after (kill end-60 s) | 279.6 req/s | 257.4 req/s |
| p95 after (successful requests only) | 197.4 ms | 346.3 ms |
| p95 before | 153.4 ms | 168.7 ms |
| after the kill: p95 <= 500 ms? | yes for p95, but 50 % errors -> level FAILS (errors must be < 1 %) | yes, and 0 errors -> PASS |

Notes
- fail_off: NGINX keeps giving every 2nd request to a dead server -> 502 at once. Its p95 is lower than in fail_on
  only because half of the requests fail fast (and loadgen waits 50 ms after a fast failure), so the 4 living
  servers get less work per second than 60 users would normally give them.
- fail_on: all 60 users are served by gpu0 alone (layout 3 capacity = 90 users). Single seconds reached p95 > 500 ms
  (seconds 33 and 37: 506.7 / 532.9 ms); such short peaks also exist before the kill and in fail_off (max 441.6 ms);
  their cause was not looked for.
- NGINX error log: fail_off 11206 lines; fail_on 140 lines (116 in the second of the kill, then 8 every ~11 s =
  one test request per dead server after fail_timeout, sent on to a living server).
- After the two runs the system was started again as layout 4 with the default settings
  (fail_final_cluster_status.txt: status OK; fail_restore_check.json: N=60, 12 s, 0 errors, p95 139.4 ms).

Files: fail_off.json / fail_on.json (keys event, before, during_event, after, in_flight_at_event, all_requests,
per_second), *_log.txt, *_nginx.conf (config in use), *_nginx_error.log, *_nginx_access.log.gz, *_cluster_status*.txt.
Code: code/cluster.sh (up --failover, kill-gpu), code/nginx.conf (FAILOVER markers), code/loadgen.py (--event-at /
--event-cmd), code/run_failover.sh.
