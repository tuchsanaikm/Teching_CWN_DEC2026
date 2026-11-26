#!/bin/bash
# Rent the cheapest 4x RTX 3090 offer meeting the lab conditions; retry with next offer if not ready in 10 min.
export PATH=$PATH:~/.local/bin
KEY=/workspace/vastai_lab/Devtool_SSH/devtoolSSH
IMG=pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime
Q='gpu_name=RTX_3090 num_gpus=4 verified=true reliability>=0.95 inet_down>=700 inet_down_cost<=0.01 cpu_cores>=16 geolocation notin [CN] dph_total<=1.40 cuda_max_good>=12.8 rentable=true'
OUT=$(dirname "$0")/../results
vastai search offers "$Q" --storage 60 -o dph_total --raw > $OUT/offers.json
SKIP_MACHINES="${SKIP_MACHINES:-}"  # machine ids that already failed to start within 10 min
for OID in $(python3 -c "import json;[print(o['id']) for o in json.load(open('$OUT/offers.json')) if str(o['machine_id']) not in '$SKIP_MACHINES'.split()]"); do
  echo "== try offer $OID"
  IID=$(vastai create instance $OID --image $IMG --disk 60 --ssh --direct --label vapp-lab4-dp4 --cancel-unavail --raw | python3 -c "import sys,json;print(json.load(sys.stdin).get('new_contract',''))")
  [ -z "$IID" ] && { echo "create failed"; continue; }
  echo "instance $IID"; vastai attach ssh $IID "$(cat $KEY.pub)" >/dev/null
  T0=$(date +%s)
  while [ $(( $(date +%s)-T0 )) -lt 600 ]; do
    vastai show instance $IID --raw > $OUT/instance.json 2>/dev/null
    read ST HOST PORT <<<$(python3 -c "import json;d=json.load(open('$OUT/instance.json'));print(d.get('actual_status'),d.get('public_ipaddr'),(d.get('ports') or {}).get('22/tcp',[{}])[0].get('HostPort'))")
    echo "$(( $(date +%s)-T0 ))s status=$ST"
    case $ST in exited|unknown|offline) break;; esac
    if [ "$ST" = running ] && [ "$PORT" != None ] && ssh -i $KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=8 -p $PORT root@$HOST nvidia-smi -L 2>/dev/null | grep -c 3090 | grep -q 4; then
      echo "READY $IID $HOST $PORT offer=$OID after $(( $(date +%s)-T0 ))s"; echo "$IID $HOST $PORT $OID" > $OUT/instance.txt; exit 0
    fi
    sleep 15
  done
  echo "not ready in 10 min -> destroy $IID"; vastai destroy instance $IID -y
done
exit 1
