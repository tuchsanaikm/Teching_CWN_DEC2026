#!/bin/bash
# usage: rent.sh <node-number> <offer-id>   -> creates instance, writes state/n<N>.id
# Node 1 additionally exposes TCP port 9000 for the other nodes.
set -euo pipefail
export PATH=$PATH:$HOME/.local/bin
cd "$(dirname "$0")"
N=$1; OFFER=$2
IMAGE=vastai/pytorch:2.8.0-cuda-12.8.1-py312-24.04
ENVS=""
[ "$N" = 1 ] && ENVS="-p 9000:9000"
ARGS=(create instance "$OFFER" --image "$IMAGE" --disk 60 --ssh --direct --label "vapp-lab5-3mp-$N" --cancel-unavail --raw)
[ -n "$ENVS" ] && ARGS+=(--env "$ENVS")
OUT=$(vastai "${ARGS[@]}")
echo "$OUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print({k:d[k] for k in ('success','new_contract') if k in d}); open('state/n$N.id','w').write(str(d['new_contract']))"
date +%s > state/n$N.created
echo "$OFFER" > state/n$N.offer
