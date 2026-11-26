#!/bin/bash
# ส่ง code/ ขึ้นเครื่อง GPU
D=$(cd "$(dirname "$0")" && pwd)
H=$(python3 -c "import json;print(json.load(open('$D/results/instance.json'))['ssh_host'])")
P=$(python3 -c "import json;print(json.load(open('$D/results/instance.json'))['ssh_port'])")
scp -q -i /workspace/vastai_lab/Devtool_SSH/devtoolSSH -P "$P" -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR "$D"/code/* "root@$H:/workspace/lab4_mp/code/"
