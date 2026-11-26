#!/bin/bash
# Wait (max ~9.5 min) until the instance is running and SSH answers. Usage: wait_ready.sh <instance_id>
export PATH=/root/.local/bin:$PATH
ID=$1; K=/workspace/vastai_lab/Devtool_SSH/devtoolSSH
cd /workspace/vastapp_lab
for i in $(seq 1 55); do
  read S H P MSG <<<$(vastai show instance $ID --raw 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('actual_status'), d.get('ssh_host'), d.get('ssh_port'), (d.get('status_msg') or '')[:70].replace('\n',' '))")
  if [ "$S" = running ] && ssh -i $K -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=8 -o BatchMode=yes -p $P root@$H 'nvidia-smi -L' 2>/dev/null; then
    echo "READY $H $P"; date; exit 0
  fi
  [ $((i % 6)) = 0 ] && echo "$i $S $MSG"
  sleep 10
done
echo TIMEOUT; date; exit 1
