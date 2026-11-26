#!/bin/bash
# copy code to the instance
cd "$(dirname "$0")"
scp -q -i /workspace/vastai_lab/Devtool_SSH/devtoolSSH -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -P <port> code/*.py code/*.sh root@<ssh_host>:/workspace/lab4_dp4/code/ 2>&1 | grep -v "No such file"
