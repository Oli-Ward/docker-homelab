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
"$NODE_BIN" - "$input_file" "$payload_file" <<'NODE'
const fs = require("fs");
const inputPath = process.argv[2];
const outputPath = process.argv[3];
const event = JSON.parse(fs.readFileSync(inputPath, "utf8"));
function normalizeAgentReady(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return undefined;
  }
  const checks = {};
  for (const [key, enabled] of Object.entries(value)) {
    const name = String(key).trim();
    if (name) {
      checks[name] = Boolean(enabled);
    }
  }
  return Object.keys(checks).length > 0 ? checks : undefined;
}
function normalizeStringList(value) {
  if (!Array.isArray(value)) {
    return undefined;
  }
  const values = value.map((item) => String(item).trim()).filter(Boolean);
  return values.length > 0 ? values : undefined;
}
const REQUIRED_AGENT_READY_CHECKS = ["context", "acceptance_criteria", "safety_notes"];
function normalizeInteger(value) {
  if (Number.isInteger(value)) {
    return value;
  }
  if (typeof value === "string" && /^\d+$/.test(value.trim())) {
    return Number(value.trim());
  }
  return null;
}
function firstString(...values) {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return "";
}
function canonicalIdentifier(event, sequenceId) {
  return firstString(
    event.source_identifier,
    event.sourceIdentifier,
    event.identifier,
    event.work_item_identifier,
    event.workItemIdentifier,
  ) || (sequenceId !== null ? `OPENC-${sequenceId}` : "");
}
function normalizeLabels(value) {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((label) => String(label).trim()).filter(Boolean);
}
function isReadyForAgent(event) {
  return firstString(event.state_name, event.stateName).toLowerCase() === "ready for agent";
}
function normalizeAgentReadyChecks(event) {
  const checks = normalizeStringList(event.agent_ready_checks || event.agentReadyChecks);
  if (checks) {
    return checks;
  }
  return isReadyForAgent(event) ? REQUIRED_AGENT_READY_CHECKS : undefined;
}
const sequenceId = normalizeInteger(event.sequence_id || event.sequenceId);
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
  source_identifier: canonicalIdentifier(event, sequenceId),
  webhook_id: event.webhook_id || "",
  actor_id: event.actor_id || "",
  team: firstString(event.team, event.team_name, event.teamName) || "openclaw",
  project_id: event.project_id || "",
  sequence_id: sequenceId,
  name: event.name || "",
  state_id: event.state_id || "",
  state_name: firstString(event.state_name, event.stateName),
  priority: event.priority || "",
  label_names: normalizeLabels(event.label_names || event.labelNames),
  agent_ready: normalizeAgentReady(event.agent_ready || event.agentReady),
  agent_ready_checks: normalizeAgentReadyChecks(event),
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
