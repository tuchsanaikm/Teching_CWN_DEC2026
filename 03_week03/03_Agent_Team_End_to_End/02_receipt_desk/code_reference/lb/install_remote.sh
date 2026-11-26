#!/bin/bash
# Install vLLM + udocker + merge LoRA on rented 2x RTX 4090 machine
set -euo pipefail
D=/workspace/receipt_lb
mkdir -p $D/{code,runtime,logs,results,hf,udocker,receipts}

echo "=== [1] Install uv & create venv ==="
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
export PATH="$HOME/.local/bin:$PATH"
export HF_HOME=$D/hf
export UDOCKER_DIR=$D/udocker

if [ ! -x "$D/venv/bin/vllm" ]; then
  uv venv --python 3.12 "$D/venv" --seed
  uv pip install --python "$D/venv/bin/python" vllm aiohttp uvloop pillow peft transformers accelerate udocker qwen-vl-utils
fi

echo "=== [2] Setup udocker nginx:1.27 ==="
if ! $D/venv/bin/udocker --allow-root ps | grep -q receiptnginx; then
  $D/venv/bin/udocker --allow-root pull nginx:1.27
  $D/venv/bin/udocker --allow-root create --name=receiptnginx nginx:1.27
fi

echo "=== [3] Generate API key ==="
if [ ! -f "$D/runtime/api_key" ]; then
  (umask 077; python3 -c "import secrets; print('rd_' + secrets.token_hex(24))" > $D/runtime/api_key)
fi

echo "=== [4] Download Qwen3-VL-2B-Instruct & Merge LoRA ==="
$D/venv/bin/python $D/code/merge_lora.py

chmod +x $D/code/node_receipt.sh
echo "=== INSTALL & MERGE DONE ==="
