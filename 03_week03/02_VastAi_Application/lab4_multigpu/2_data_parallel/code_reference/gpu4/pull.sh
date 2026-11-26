#!/bin/bash
# copy results (without adapter weights and checkpoints) back from the instance
cd "$(dirname "$0")"
./s.sh 'cd /workspace/lab4_dp4/results && tar czf - --exclude=ckpt --exclude="*.safetensors" --exclude="*.pt" .' | tar xzf - -C results
