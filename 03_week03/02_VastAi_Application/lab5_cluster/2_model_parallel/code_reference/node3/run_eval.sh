#!/bin/bash
# After training: Node 1 evaluates the base model, Node 2 its own epoch-1 LoRA, Node 3 its own epoch-2 LoRA.
cd "$(dirname "$0")"
for n in 1 2 3; do ./scpn $n code/eval.py code/common.py code/start_eval.sh /workspace/lab5/code/ & done; wait
./sshn 1 "bash /workspace/lab5/code/start_eval.sh base"
./sshn 2 "bash /workspace/lab5/code/start_eval.sh epoch1 /workspace/lab5/run/train/lora_epoch1_node2.pt"
./sshn 3 "bash /workspace/lab5/code/start_eval.sh epoch2 /workspace/lab5/run/train/lora_epoch2_node3.pt"
