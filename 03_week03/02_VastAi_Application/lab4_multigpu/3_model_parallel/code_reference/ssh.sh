#!/bin/bash
# ใช้: ./ssh.sh <คำสั่ง>   (อ่าน host/port จาก results/instance.json)
D=$(cd "$(dirname "$0")" && pwd)
H=$(python3 -c "import json;print(json.load(open('$D/results/instance.json'))['ssh_host'])")
P=$(python3 -c "import json;print(json.load(open('$D/results/instance.json'))['ssh_port'])")
exec ssh -i /workspace/vastai_lab/Devtool_SSH/devtoolSSH -p "$P" -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ServerAliveInterval=30 "root@$H" "$@"
