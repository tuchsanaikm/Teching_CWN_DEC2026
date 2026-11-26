#!/bin/bash
# One-time: let machine 1 read the GPU load/temperature of machine 2 once per second.
# Machine 1 gets its own SSH key; on machine 2 that key may run exactly one command (nvidia-smi), nothing else.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd); . "$HERE/nodes.env"
SSHO="-i $SSH_KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=20 -o LogLevel=ERROR"
Q='nvidia-smi --query-gpu=index,utilization.gpu,temperature.gpu,power.draw --format=csv,noheader,nounits -l 1'
PUB=$(ssh $SSHO -p $N1_SSH_PORT root@$N1_IP "K=$REMOTE_DIR/runtime/gpumon_key; [ -f \$K ] || ssh-keygen -q -t ed25519 -N '' -C lab7-gpumon -f \$K; cat \$K.pub")
ssh $SSHO -p $N2_SSH_PORT root@$N2_IP "grep -q lab7-gpumon ~/.ssh/authorized_keys || printf '\n%s\n' 'command=\"$Q\",no-port-forwarding,no-agent-forwarding,no-X11-forwarding,no-pty $PUB' >> ~/.ssh/authorized_keys"
ssh $SSHO -p $N1_SSH_PORT root@$N1_IP "timeout 4 ssh -i $REMOTE_DIR/runtime/gpumon_key -p $N2_SSH_PORT -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o BatchMode=yes root@$N2_IP | head -4" || true
echo "gpu monitor n1 -> n2: ok if GPU lines are shown above"
