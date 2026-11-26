#!/bin/bash
# SSH helper for instance labelled vapp-lab4-single
exec ssh -i /workspace/vastai_lab/Devtool_SSH/devtoolSSH -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=20 -o ServerAliveInterval=30 -p <port> root@<host> "$@"
