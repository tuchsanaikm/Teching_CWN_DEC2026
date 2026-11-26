#!/bin/bash
# copy code/ to all nodes
D=$(dirname "$0"); for n in 1 2 3; do for f in common.py coordinator.py worker.py eval.py run_node.sh; do $D/sshn cp $n $D/code/$f /workspace/code/$f; done; done; echo deployed
