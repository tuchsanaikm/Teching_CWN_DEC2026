#!/bin/bash
# Runs ON a rented machine (in the background, started by run_install.sh).
# usage: install.sh <vllm_version> <role n1|n2> <model>
# HF_TOKEN (optional) comes only through the environment of this process; it is never written to disk.
set -u
VER=$1; ROLE=$2; MODEL=$3
D=/workspace/lab7
mkdir -p $D/logs $D/runtime
cd $D
rm -f install.done install.failed
fail() { echo "FAILED: $1"; echo "$1" > install.failed; exit 1; }
now() { date +%s.%N; }

echo "$ROLE" > role

# ---- 1) vLLM into its own virtualenv (does not touch the image's torch) ----
T0=$(now)
# vLLM compiles small GPU kernels at start-up (torch.compile/triton) and needs a C compiler
command -v gcc >/dev/null || { apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq gcc g++ > logs/apt.log 2>&1; } || fail "apt install gcc"
pip install -q uv || fail "pip install uv"
uv venv $D/venv --python 3.12 -q || fail "uv venv"
VIRTUAL_ENV=$D/venv uv pip install -q "vllm==$VER" || fail "install vllm"
T1=$(now)
$D/venv/bin/python -c "import vllm,torch;print('vllm',vllm.__version__,'torch',torch.__version__)" || fail "import vllm"

# ---- 2) model download (token only in env, no 'hf auth login', nothing saved) ----
export HF_HOME=$D/hf
HF_BIN=$D/venv/bin/hf; [ -x $HF_BIN ] || HF_BIN=$D/venv/bin/huggingface-cli
$HF_BIN download "$MODEL" > logs/download.log 2>&1 || fail "model download"
T2=$(now)
unset HF_TOKEN
rm -f $HF_HOME/token $HF_HOME/stored_tokens

# ---- 3) machine 1 only: udocker + official nginx:1.27 image ----
T3=$T2
if [ "$ROLE" = n1 ]; then
  pip install -q udocker || fail "pip install udocker"
  export UDOCKER_DIR=$D/udocker
  udocker --allow-root install || fail "udocker install"
  udocker --allow-root pull nginx:1.27 || fail "pull nginx:1.27"
  udocker --allow-root rm lab7nginx 2>/dev/null
  udocker --allow-root create --name=lab7nginx nginx:1.27 || fail "create nginx container"
  T3=$(now)
fi

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
echo "INSTALL OK"
