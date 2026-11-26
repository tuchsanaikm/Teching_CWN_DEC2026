#!/usr/bin/env bash
# ssh.sh <remote command>   |  ssh.sh --push <local> <remote>  |  ssh.sh --pull <remote> <local>
cd "$(dirname "$0")"; . ./instance.env
KEY=/workspace/vastai_lab/Devtool_SSH/devtoolSSH
O="-i $KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=15"
case "${1:-}" in
  --push) scp $O -P "$SSH_PORT" -r "$2" root@"$SSH_HOST":"$3";;
  --pull) scp $O -P "$SSH_PORT" -r root@"$SSH_HOST":"$2" "$3";;
  *) ssh $O -p "$SSH_PORT" root@"$SSH_HOST" "$@";;
esac
