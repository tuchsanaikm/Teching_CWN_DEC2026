#!/bin/bash
# Runs ON each rented single-node machine (dp2 or mp4).
# usage: install_single.sh <role dp2|mp4> <model>
set -u
ROLE=$1; MODEL=$2
D=/workspace/lab7
mkdir -p $D/logs $D/runtime $D/code $D/results
cd $D
rm -f install.done install.failed
fail() { echo "FAILED: $1"; echo "$1" > install.failed; exit 1; }
now() { date +%s.%N; }

echo "$ROLE" > role
echo "$MODEL" > runtime/model
echo "shop-bot" > runtime/served_name
echo "4096" > runtime/max_model_len

# Generate API key once
if [ ! -f $D/runtime/api_key ]; then
  ( umask 077; python3 -c "import secrets; print('sk-lab7-' + secrets.token_hex(24))" > $D/runtime/api_key )
fi

T0=$(now)
command -v gcc >/dev/null || { apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq gcc g++ > logs/apt.log 2>&1; } || fail "apt install gcc"
pip install -q uv aiohttp matplotlib || fail "pip install uv aiohttp matplotlib"
uv venv $D/venv --python 3.12 -q || fail "uv venv"
VIRTUAL_ENV=$D/venv uv pip install -q vllm aiohttp || fail "install vllm"
T1=$(now)
$D/venv/bin/python -c "import vllm,torch;print('vllm',vllm.__version__,'torch',torch.__version__)" || fail "import vllm"

# Download model (HF_TOKEN only in env, never saved)
export HF_HOME=$D/hf
HF_BIN=$D/venv/bin/hf; [ -x $HF_BIN ] || HF_BIN=$D/venv/bin/huggingface-cli
$HF_BIN download "$MODEL" > logs/download.log 2>&1 || fail "model download"
T2=$(now)
unset HF_TOKEN
rm -f $HF_HOME/token $HF_HOME/stored_tokens

# udocker + official nginx:1.27 on BOTH machines (each is a self-contained single-node setup)
pip install -q udocker || fail "pip install udocker"
export UDOCKER_DIR=$D/udocker
udocker --allow-root install || fail "udocker install"
udocker --allow-root pull nginx:1.27 || fail "pull nginx:1.27"
udocker --allow-root rm lab7nginx 2>/dev/null || true
udocker --allow-root create --name=lab7nginx nginx:1.27 || fail "create nginx container"
T3=$(now)

python3 - "$T0" "$T1" "$T2" "$T3" "$ROLE" <<'P'
import sys, json, subprocess
t0, t1, t2, t3 = map(float, sys.argv[1:5])
v = subprocess.check_output(["/workspace/lab7/venv/bin/python", "-c",
     "import vllm,torch;print(vllm.__version__, torch.__version__)"], text=True).split()
size = subprocess.check_output("du -sb /workspace/lab7/hf | cut -f1", shell=True, text=True).strip()
json.dump({"role": sys.argv[5], "vllm": v[0], "torch": v[1],
           "install_vllm_s": round(t1 - t0, 1), "download_model_s": round(t2 - t1, 1),
           "install_nginx_udocker_s": round(t3 - t2, 1), "model_bytes": int(size)},
          open("/workspace/lab7/timings.json", "w"), indent=1)
P
touch install.done
echo "INSTALL OK ($ROLE)"
