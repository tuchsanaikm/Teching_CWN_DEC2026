#!/bin/bash
# VRAM used per GPU on both machines right now -> results/vram_<tag>.json    usage: gpu_mem.sh <tag>
set -u
HERE=$(cd "$(dirname "$0")" && pwd); . "$HERE/nodes.env"
SSHO="-i $SSH_KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=20 -o LogLevel=ERROR"
Q='nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits'
{ ssh -n $SSHO -p $N1_SSH_PORT root@$N1_IP "$Q" | sed 's/^/n1,/'; ssh -n $SSHO -p $N2_SSH_PORT root@$N2_IP "$Q" | sed 's/^/n2,/'; } | python3 -c '
import sys, json, time
g = {}
for l in sys.stdin:
    m, i, used, total, util = [x.strip() for x in l.split(",")]
    g["%s:%s" % (m, i)] = {"memory_used_mib": int(used), "memory_total_mib": int(total), "util_pct": int(util)}
json.dump({"tag": sys.argv[1], "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "gpus": g}, open(sys.argv[2], "w"), indent=1)
print(sys.argv[1], {k: (v["memory_used_mib"], v["util_pct"]) for k, v in g.items()})' "$1" "$HERE/../results/vram_$1.json"
