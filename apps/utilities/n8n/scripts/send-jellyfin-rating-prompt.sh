#!/bin/sh
set -eu

OPENCLAW_SSH_HOST=${OPENCLAW_SSH_HOST:?Set OPENCLAW_SSH_HOST}
OPENCLAW_SSH_USER=${OPENCLAW_SSH_USER:-oli}
OPENCLAW_SSH_PORT=${OPENCLAW_SSH_PORT:-22}
OPENCLAW_SSH_KEY_PATH=${OPENCLAW_SSH_KEY_PATH:-/home/node/.n8n/ssh/openclaw_lab_tunnel}
OPENCLAW_WORKSPACE=${OPENCLAW_WORKSPACE:-/home/openclaw/.openclaw/workspace}
OPENCLAW_RATING_PROMPT_DB=${OPENCLAW_RATING_PROMPT_DB:-tracking/jellyfin-rating-prompts/rating-prompts.sqlite}

quote() {
  printf "'%s'" "$(printf "%s" "$1" | sed "s/'/'\\\\''/g")"
}

payload_file=$(mktemp)
remote_payload="/tmp/opn-212-jellyfin-rating-$(date +%s)-$$.json"

cleanup() {
  rm -f "$payload_file"
}
trap cleanup EXIT

cat > "$payload_file"

ssh_base="ssh -i $(quote "$OPENCLAW_SSH_KEY_PATH") -p $(quote "$OPENCLAW_SSH_PORT") -o BatchMode=yes -o StrictHostKeyChecking=accept-new"
remote="${OPENCLAW_SSH_USER}@${OPENCLAW_SSH_HOST}"
remote_payload_q=$(quote "$remote_payload")
workspace_q=$(quote "$OPENCLAW_WORKSPACE")
db_q=$(quote "$OPENCLAW_RATING_PROMPT_DB")

# shellcheck disable=SC2086
$ssh_base "$remote" "cat > $remote_payload_q" < "$payload_file"

remote_command="
set -eu
cleanup() { rm -f $remote_payload_q; }
trap cleanup EXIT
cd $workspace_q
tools/bin/openclaw-with-secrets -- sh -c 'OPENCLAW_GATEWAY_TOKEN=\"\$OPENCLAW_GATEWAY_AUTH_TOKEN\" python3 execution/jellyfin-rating-prompt.py --event-file \"\$1\" --db \"\$2\" --send' sh $remote_payload_q $db_q
"

# shellcheck disable=SC2086
$ssh_base "$remote" "$remote_command"
