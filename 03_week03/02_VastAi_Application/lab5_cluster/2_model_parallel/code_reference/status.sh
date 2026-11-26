#!/bin/bash
# one-shot progress report from both nodes
D=$(dirname "$0")
"$D/n1" 'tail -2 /workspace/mp/run/coordinator.log; grep -E "step|epoch|Error|supervisor" /workspace/mp/run/worker_node1.log | tail -2 | cut -c1-220; nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader | tr "\n" ";"; echo'
"$D/n2" 'grep -E "step|epoch|Error|supervisor" /workspace/mp/run/worker_node2.log | tail -1 | cut -c1-220'
