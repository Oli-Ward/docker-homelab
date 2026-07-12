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
  schema_version: event.schema_version || "plane.webhook.v1",
  event_id: event.event_id || event.delivery_id || "",
  event_type: event.event_type || "",
  idempotency_key: event.idempotency_key || event.event_id || event.delivery_id || "",
  correlation_id: event.correlation_id || "",
  causation_id: event.causation_id || null,
  origin: event.origin || "plane",
  retry_attempt: Number.isInteger(event.retry_attempt) ? event.retry_attempt : 0,
  raw_payload_hash: event.raw_payload_hash || "",
  source: "plane",
  event: event.event || "",
  action: event.action || "",
  delivery_id: event.delivery_id || "",
  resource_id: event.resource_id || "",
  source_identifier: event.source_identifier || event.sourceIdentifier || "",
  webhook_id: event.webhook_id || "",
  actor_id: event.actor_id || "",
  team: event.team || event.team_name || event.teamName || "",
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
correlation_id=$("$NODE_BIN" - "$payload_file" <<'NODE'
const fs = require("fs");
const payload = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
process.stdout.write(payload.correlation_id || "");
NODE
)

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

if dispatch_output=$(ssh $ssh_opts "$remote" "$remote_command"); then
  "$NODE_BIN" - "$correlation_id" "$dispatch_output" <<'NODE'
const correlationId = process.argv[2] || null;
const output = process.argv[3] || "";
try {
  const parsed = JSON.parse(output);
  if (parsed && typeof parsed === "object" && Object.prototype.hasOwnProperty.call(parsed, "ok")) {
    process.stdout.write(JSON.stringify(parsed));
    process.stdout.write("\n");
    process.exit(0);
  }
} catch (_err) {
}
process.stdout.write(JSON.stringify({ ok: true, correlation_id: correlationId }));
process.stdout.write("\n");
NODE
else
  "$NODE_BIN" - "$correlation_id" <<'NODE'
const correlationId = process.argv[2] || null;
process.stdout.write(JSON.stringify({
  ok: false,
  failure_type: "retryable",
  error_code: "openclaw_dispatch_failed",
  correlation_id: correlationId,
}));
process.stdout.write("\n");
NODE
fi
