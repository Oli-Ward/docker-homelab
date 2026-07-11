#!/bin/sh
set -eu

NODE_BIN=${NODE_BIN:-/usr/local/bin/node}
SCRIPT_DIR=$(dirname "$0")

quote() {
  printf "'%s'" "$(printf "%s" "$1" | sed "s/'/'\\\\''/g")"
}

input_file=$(mktemp)
payload_file=$(mktemp)
preview_file=$(mktemp)
remote_payload="/tmp/opn-271-plane-dispatch-$(date +%s)-$$.json"

cleanup() {
  rm -f "$input_file" "$payload_file" "$preview_file"
}
trap cleanup EXIT

cat > "$input_file"
"$NODE_BIN" - "$input_file" "$payload_file" <<NODE
const fs = require("fs");
const inputPath = process.argv[2];
const outputPath = process.argv[3];
const event = JSON.parse(fs.readFileSync(inputPath, "utf8"));
const normalized = {
  source: "plane",
  event: event.event || "",
  action: event.action || "",
  correlation_id: event.correlation_id || "",
  delivery_id: event.delivery_id || "",
  resource_id: event.resource_id || "",
  webhook_id: event.webhook_id || "",
  actor_id: event.actor_id || "",
  project_id: event.project_id || "",
  sequence_id: Number.isInteger(event.sequence_id) ? event.sequence_id : null,
  name: event.name || "",
  state_id: event.state_id || "",
  state_name: event.state_name || "",
  priority: event.priority || "",
  label_names: Array.isArray(event.label_names) ? event.label_names.filter((label) => typeof label === "string" && label) : [],
  received_at: event.received_at || new Date().toISOString(),
};
fs.writeFileSync(outputPath, JSON.stringify(normalized));
NODE

"$NODE_BIN" "$SCRIPT_DIR/plane-agent-pickup-preview.js" "$payload_file" > "$preview_file"
decision=$("$NODE_BIN" - "$preview_file" <<'NODE'
const fs = require("fs");
const preview = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
process.stdout.write(preview.decision || "");
NODE
)

if [ "$decision" != "ready" ]; then
  cat "$preview_file"
  exit 0
fi

OPENCLAW_SSH_HOST=${OPENCLAW_SSH_HOST:?Set OPENCLAW_SSH_HOST}
OPENCLAW_SSH_USER=${OPENCLAW_SSH_USER:-openclaw}
OPENCLAW_SSH_PORT=${OPENCLAW_SSH_PORT:-22}
OPENCLAW_SSH_KEY_PATH=${OPENCLAW_SSH_KEY_PATH:-/home/node/.n8n/ssh/openclaw_lab_tunnel}
OPENCLAW_WORKSPACE=${OPENCLAW_WORKSPACE:-/home/openclaw/.openclaw/workspace}
OPENCLAW_PLANE_DISPATCH_COMMAND=${OPENCLAW_PLANE_DISPATCH_COMMAND:-tools/bin/openclaw-plane-n8n-dispatch}

ssh_opts="-i $OPENCLAW_SSH_KEY_PATH -p $OPENCLAW_SSH_PORT -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10"
remote="${OPENCLAW_SSH_USER}@${OPENCLAW_SSH_HOST}"
remote_payload_q=$(quote "$remote_payload")
workspace_q=$(quote "$OPENCLAW_WORKSPACE")
dispatch_command_q=$(quote "$OPENCLAW_PLANE_DISPATCH_COMMAND")

ssh $ssh_opts "$remote" "cat > $remote_payload_q" < "$payload_file"

remote_command="
set -eu
export PATH=\"\$HOME/.local/bin:\$HOME/bin:\$PATH\"
cleanup() { rm -f $remote_payload_q; }
trap cleanup EXIT
cd $workspace_q
$dispatch_command_q --event-file $remote_payload_q
"

ssh $ssh_opts "$remote" "$remote_command"
