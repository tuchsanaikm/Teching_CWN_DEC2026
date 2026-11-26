#!/bin/bash
# Node 2 and Node 3 connect to Node 1's public port (mapped from container port 9000).
# Output: results/net_probe.json
cd "$(dirname "$0")"
read IP P < <(python3 -c "import json;d=json.load(open('state/n1.json'));print(d['ip'],d['port9000'])")
echo "[" > results/net_probe.json
for n in 2 3; do
  R=$(./sshn $n "/venv/main/bin/python /workspace/lab5/code/netprobe.py client $IP $P 10")
  echo "$R" | python3 -c "import json,sys; d=json.load(sys.stdin); d['from']='node$n'; d['to']='node1'; print(json.dumps(d))" | tee -a results/net_probe.json
  [ $n = 2 ] && echo "," >> results/net_probe.json
done
echo "]" >> results/net_probe.json
