#!/bin/bash
# copy code/ to both nodes
K=/workspace/vastai_lab/Devtool_SSH/devtoolSSH
O="-i $K -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"
D=$(dirname "$0")
"$D/n1" 'mkdir -p /workspace/mp/code'; "$D/n2" 'mkdir -p /workspace/mp/code'
scp $O -P <N1_SSH_PORT> "$D"/code/*.py "$D"/code/*.sh root@<N1_IP>:/workspace/mp/code/
scp $O -P <N2_SSH_PORT> "$D"/code/*.py "$D"/code/*.sh root@<N2_IP>:/workspace/mp/code/
