#!/bin/bash
# Run a command on the vapp-lab4-mp4 instance. Usage: r.sh '<command>'
exec ssh -i /workspace/vastai_lab/Devtool_SSH/devtoolSSH -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=15 -o ServerAliveInterval=20 -p <port> root@<ssh-host> "$@"
