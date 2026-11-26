#!/bin/bash
# Runs on the control machine. Starts install.sh on BOTH machines at the same time (background, nohup).
# usage: run_install.sh start <vllm_version> | run_install.sh poll
# HF_TOKEN is read from the .env of the folder Claude Code is open in and sent over SSH stdin:
# it lives only in the environment of the install process and is never stored on the rented machine.
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/nodes.env"
ENVFILE=${ENVFILE:-$HERE/../../.env}
SSH="ssh -i $SSH_KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=20 -o LogLevel=ERROR"

start_one() { # role ip port version
  $SSH -p "$3" root@"$2" "mkdir -p $REMOTE_DIR/code $REMOTE_DIR/logs"
  scp -q -i $SSH_KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -P "$3" \
      "$HERE/install.sh" root@"$2":$REMOTE_DIR/code/
  # first stdin line = token (may be empty)
  grep -m1 '^HF_TOKEN=' "$ENVFILE" 2>/dev/null | cut -d= -f2- | tr -d '"'"'" | { cat; echo; } | \
  $SSH -p "$3" root@"$2" "IFS= read -r HF_TOKEN; [ -n \"\$HF_TOKEN\" ] && export HF_TOKEN; \
     echo token_present=\$([ -n \"\$HF_TOKEN\" ] && echo yes || echo no); \
     setsid nohup bash $REMOTE_DIR/code/install.sh $4 $1 $MODEL > $REMOTE_DIR/logs/install.log 2>&1 < /dev/null & echo started $1"
}

case "$1" in
  start)
    start_one n1 $N1_IP $N1_SSH_PORT "$2" &
    start_one n2 $N2_IP $N2_SSH_PORT "$2" &
    wait ;;
  poll)
    for n in "n1 $N1_IP $N1_SSH_PORT" "n2 $N2_IP $N2_SSH_PORT"; do set -- $n
      echo "== $1"; $SSH -p $3 root@$2 "cd $REMOTE_DIR; ls install.done install.failed 2>/dev/null; tail -n 3 logs/install.log; du -sh hf venv 2>/dev/null | tr '\n' ' '; echo; cat timings.json 2>/dev/null"
    done ;;
esac
