#!/usr/bin/env bash
# Start ONE detect server on ONE GPU.  usage: run_server.sh <gpu_index> <port> <mode: single|micro> [server_id]
set -eu
cd "$(dirname "$0")"
GPU=${1:-0}; PORT=${2:-8001}; MODE=${3:-single}; SID=${4:-gpu$GPU-$PORT}
set -a; . /workspace/lab6/api_key.env; set +a      # API_KEY (file is chmod 600, never printed)
export CUDA_VISIBLE_DEVICES=$GPU MODE SERVER_ID=$SID MODEL_PATH=/workspace/lab6/best.pt \
       IMGSZ=640 CONF=0.35 MAX_BATCH=32 MAX_WAIT_MS=5 YOLO_VERBOSE=False
mkdir -p /workspace/lab6/logs
PIDF=/workspace/lab6/logs/server_$PORT.pid
[ -f "$PIDF" ] && kill "$(cat "$PIDF")" 2>/dev/null && sleep 2 || true
nohup python -m uvicorn server:app --host 127.0.0.1 --port "$PORT" --workers 1 --no-access-log \
      > /workspace/lab6/logs/server_$PORT.log 2>&1 &
echo $! > "$PIDF"
for i in $(seq 1 180); do
  if curl -fsS -o /dev/null "http://127.0.0.1:$PORT/health" 2>/dev/null; then echo "ready port=$PORT gpu=$GPU mode=$MODE after ${i}s"; exit 0; fi
  kill -0 "$(cat "$PIDF")" 2>/dev/null || { echo "server died"; tail -20 /workspace/lab6/logs/server_$PORT.log; exit 1; }
  sleep 1
done
echo "timeout waiting for /health"; exit 1
