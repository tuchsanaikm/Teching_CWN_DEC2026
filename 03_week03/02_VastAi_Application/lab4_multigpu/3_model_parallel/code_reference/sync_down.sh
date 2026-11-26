#!/bin/bash
# ดึงผล (json/jsonl/log, ไม่รวม checkpoint) กลับมาที่ results/
D=$(cd "$(dirname "$0")" && pwd)
H=$(python3 -c "import json;print(json.load(open('$D/results/instance.json'))['ssh_host'])")
P=$(python3 -c "import json;print(json.load(open('$D/results/instance.json'))['ssh_port'])")
scp -q -i /workspace/vastai_lab/Devtool_SSH/devtoolSSH -P "$P" -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR \
  "root@$H:/workspace/lab4_mp/results/*" "root@$H:/workspace/lab4_mp/logs/*" "$D/results/"
