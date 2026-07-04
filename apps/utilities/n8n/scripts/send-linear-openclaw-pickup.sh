#!/bin/sh
set -eu

OPENCLAW_SSH_HOST=${OPENCLAW_SSH_HOST:?Set OPENCLAW_SSH_HOST}
OPENCLAW_SSH_USER=${OPENCLAW_SSH_USER:-openclaw}
OPENCLAW_SSH_PORT=${OPENCLAW_SSH_PORT:-22}
OPENCLAW_SSH_KEY_PATH=${OPENCLAW_SSH_KEY_PATH:-/home/node/.n8n/ssh/openclaw_lab_tunnel}
OPENCLAW_WORKSPACE=${OPENCLAW_WORKSPACE:-/home/openclaw/.openclaw/workspace}
OPENCLAW_LINEAR_HANDOFF_COMMAND=${OPENCLAW_LINEAR_HANDOFF_COMMAND:-tools/bin/openclaw-linear-n8n-handoff}

quote() {
  printf "'%s'" "$(printf "%s" "$1" | sed "s/'/'\\\\''/g")"
}

payload_file=$(mktemp)
remote_payload="/tmp/opn-234-linear-pickup-$(date +%s)-$$.json"

cleanup() {
  rm -f "$payload_file"
}
trap cleanup EXIT

cat > "$payload_file"

ssh_opts="-i $OPENCLAW_SSH_KEY_PATH -p $OPENCLAW_SSH_PORT -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10"
remote="${OPENCLAW_SSH_USER}@${OPENCLAW_SSH_HOST}"
remote_payload_q=$(quote "$remote_payload")
workspace_q=$(quote "$OPENCLAW_WORKSPACE")
handoff_command_q=$(quote "$OPENCLAW_LINEAR_HANDOFF_COMMAND")

ssh $ssh_opts "$remote" "cat > $remote_payload_q" < "$payload_file"

remote_command="
set -eu
export PATH=\"\$HOME/.local/bin:\$HOME/bin:\$PATH\"
cleanup() { rm -f $remote_payload_q; }
trap cleanup EXIT
cd $workspace_q
$handoff_command_q --event-file $remote_payload_q
"

ssh $ssh_opts "$remote" "$remote_command"
