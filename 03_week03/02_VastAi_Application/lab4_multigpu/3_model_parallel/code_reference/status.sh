#!/bin/bash
# รายงานสถานะสั้น ๆ ของงานบนเครื่อง GPU
D=$(cd "$(dirname "$0")" && pwd)
"$D/ssh.sh" 'R=/workspace/lab4_mp/results; echo "stage: $(cat $R/stage.txt 2>/dev/null)  tmux: $(tmux ls 2>/dev/null | wc -l)  $(date +%T)";
tail -n ${N:-4} /workspace/lab4_mp/logs/pipeline.log | cut -c1-400;
nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader'
