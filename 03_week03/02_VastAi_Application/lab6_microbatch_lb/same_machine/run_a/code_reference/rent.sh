#!/usr/bin/env bash
# Rent the cheapest 2x RTX 3090 machine for lab6 (nginx load-balancing test).
# If an instance is not SSH-ready within 10 minutes, destroy it and try the next offer.
set -u
export PATH="$PATH:/root/.local/bin"
cd "$(dirname "$0")"

KEY=/workspace/vastai_lab/Devtool_SSH/devtoolSSH
LABEL=vapp-lab6-p2c-a
IMAGE=pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime
DISK=40
TIMEOUT=600
# machines to skip: 20505 (reboots when both GPUs are busy) + every machine that already has an instance in
# the account (another session rents at the same time) + machines whose create failed (added below)
BAD_MACHINES="20505 $(vastai show instances --raw 2>/dev/null | python3 -c "import json,sys; print(' '.join(str(i.get('machine_id')) for i in json.load(sys.stdin)))" 2>/dev/null)"
LOG=rent_log.txt

QUERY="gpu_name=RTX_3090 num_gpus=2 verified=true rentable=true reliability>=0.95 \
cpu_cores_effective>=24 dph_total<=0.60 geolocation notin [CN] direct_port_count>=2 \
disk_space>=$DISK"

log() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOG"; }

field() { # field <instance_id> <python expr on dict i>
  vastai show instance "$1" --raw 2>/dev/null | python3 -c "
import json,sys
try:
    i=json.load(sys.stdin); print($2)
except Exception: print('')"
}

for attempt in 1 2 3 4; do
  vastai search offers "$QUERY" --storage $DISK -o dph_total --raw > offers.json
  OFFER=$(python3 - "$BAD_MACHINES" <<'EOF'
import json,sys
bad=set(sys.argv[1].split())
for o in json.load(open('offers.json')):
    if str(o['machine_id']) in bad: continue
    if o['num_gpus']!=2 or o['dph_total']>0.60 or o['cpu_cores_effective']<24: continue
    if o['reliability2']<0.95 or ', CN' in (o.get('geolocation') or ''): continue
    print(o['id'], o['machine_id'], round(o['dph_total'],4), o['geolocation'].replace(' ','_'), o['cpu_cores_effective'])
    break
EOF
)
  [ -z "$OFFER" ] && { log "no offer matches"; exit 1; }
  read -r OID MID DPH GEO CORES <<<"$OFFER"
  log "attempt $attempt: offer=$OID machine=$MID dph=$DPH geo=$GEO cores_eff=$CORES"

  T0=$(date +%s)
  OUT=$(vastai create instance "$OID" --image "$IMAGE" --disk $DISK --ssh --direct \
        --label "$LABEL" --env '-p 8080:8080' --cancel-unavail --raw 2>&1)
  IID=$(echo "$OUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('new_contract',''))" 2>/dev/null)
  if [ -z "$IID" ]; then
    log "create failed: $(echo "$OUT" | head -c 300)"
    BAD_MACHINES="$BAD_MACHINES $MID"; continue
  fi
  log "created instance $IID"

  READY=0
  while [ $(( $(date +%s) - T0 )) -lt $TIMEOUT ]; do
    ST=$(field "$IID" "i.get('actual_status')")
    if [ "$ST" = "running" ]; then
      HOST=$(field "$IID" "i.get('public_ipaddr','').strip()")
      PORT=$(field "$IID" "i['ports']['22/tcp'][0]['HostPort']")
      if [ -n "$PORT" ] && ssh -i "$KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
           -o ConnectTimeout=8 -o BatchMode=yes -o LogLevel=ERROR -p "$PORT" root@"$HOST" true 2>/dev/null; then
        READY=1; break
      fi
    fi
    case "$ST" in exited|offline|unknown) log "bad status $ST"; break;; esac
    sleep 10
  done
  WAIT=$(( $(date +%s) - T0 ))

  if [ $READY = 1 ]; then
    API=$(field "$IID" "i['ports']['8080/tcp'][0]['HostPort']")
    log "READY instance=$IID wait=${WAIT}s ssh=$HOST:$PORT api_port=$API"
    cat > instance.env <<EOF
INSTANCE_ID=$IID
OFFER_ID=$OID
MACHINE_ID=$MID
SSH_HOST=$HOST
SSH_PORT=$PORT
API_PORT=$API
WAIT_SECONDS=$WAIT
EOF
    exit 0
  fi
  log "instance $IID not ready after ${WAIT}s (status=$ST) -> destroy, try another machine"
  vastai destroy instance "$IID" -y >>"$LOG" 2>&1
  BAD_MACHINES="$BAD_MACHINES $MID"
done
log "gave up"; exit 1
