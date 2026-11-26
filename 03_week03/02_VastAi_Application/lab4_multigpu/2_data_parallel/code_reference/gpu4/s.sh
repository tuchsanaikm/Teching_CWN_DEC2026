#!/bin/bash
# SSH helper for instance vapp-lab4-dp4 (<id>)
exec ssh -i /workspace/vastai_lab/Devtool_SSH/devtoolSSH -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=20 -o ServerAliveInterval=30 -p <port> root@<ssh_host> "$@"
