#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const scriptPath = path.join(__dirname, "send-plane-openclaw-dispatch.sh");
const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "opn271-plane-send-test-"));
const fakeSshPath = path.join(tmpDir, "ssh");
const inputPath = path.join(tmpDir, "input.json");
const capturedPayloadPath = path.join(tmpDir, "payload.json");
const capturedCommandPath = path.join(tmpDir, "remote-command.txt");
const opencInputPath = path.join(tmpDir, "openc-input.json");
const capturedOpencPayloadPath = path.join(tmpDir, "openc-payload.json");
const ignoredInputPath = path.join(tmpDir, "ignored-input.json");
const needsInputPath = path.join(tmpDir, "needs-input.json");
const unexpectedPayloadPath = path.join(tmpDir, "unexpected-payload.json");

fs.writeFileSync(
  fakeSshPath,
  `#!/bin/sh
set -eu
last=""
for arg do
  last="$arg"
done
case "$last" in
  cat\\ \\>\\ *)
    cat > "$FAKE_SSH_PAYLOAD"
    ;;
  *)
    printf '%s\\n' "$last" > "$FAKE_SSH_COMMAND"
    printf '%s\\n' '{"ok":true,"correlation_id":"plane:delivery-1"}'
    ;;
esac
`,
  { mode: 0o755 },
);

const input = {
  schema_version: "plane.webhook.v1",
  event_id: "delivery-1",
  event_type: "work_item.updated",
  idempotency_key: "delivery-1",
  source: "plane",
  event: "issue",
  action: "update",
  correlation_id: "plane:delivery-1",
  causation_id: null,
  delivery_id: "delivery-1",
  resource_id: "work-item-1",
  webhook_id: "webhook-1",
  actor_id: "human-user-1",
  team: "Openclaw",
  project_id: "project-1",
  source_identifier: "OPN-273",
  sequence_id: 273,
  name: "Ready for agent",
  state_id: "state-ready",
  state_name: "Ready for Agent",
  priority: "high",
  label_names: ["agent:ready", "repo:docker"],
  agent_ready: { context: true, acceptance_criteria: true, safety_notes: true },
  agent_ready_checks: ["context", "acceptance_criteria", "safety_notes"],
  origin: "plane",
  retry_attempt: 0,
  raw_payload_hash: "a".repeat(64),
  received_at: "2026-07-11T08:45:00.000Z",
  description_html: "<p>must not forward</p>",
  raw_payload: { should: "not-forward" },
};

fs.writeFileSync(inputPath, JSON.stringify(input));

const result = spawnSync("sh", ["-c", "exec sh \"$1\" < \"$2\"", "sh", scriptPath, inputPath], {
  encoding: "utf8",
  timeout: 10000,
  env: {
    ...process.env,
    PATH: `${tmpDir}:${process.env.PATH}`,
    FAKE_SSH_PAYLOAD: capturedPayloadPath,
    FAKE_SSH_COMMAND: capturedCommandPath,
    OPENCLAW_SSH_HOST: "openclaw.internal",
    OPENCLAW_SSH_USER: "openclaw",
    OPENCLAW_SSH_PORT: "22",
    OPENCLAW_SSH_KEY_PATH: "/tmp/fake-key",
    OPENCLAW_WORKSPACE: "/srv/openclaw/workspace",
    OPENCLAW_PLANE_DISPATCH_COMMAND: "tools/bin/openclaw-plane-n8n-dispatch",
    NODE_BIN: process.execPath,
  },
});

assert.equal(
  result.status,
  0,
  `sender exited ${result.status} signal ${result.signal}: ${result.stderr || result.error || ""} tmp ${tmpDir}`,
);
assert.equal(result.stderr, "");
assert.match(result.stdout, /"ok":true/);
assert.match(result.stdout, /"correlation_id":"plane:delivery-1"/);

const uploaded = JSON.parse(fs.readFileSync(capturedPayloadPath, "utf8"));
assert.deepEqual(uploaded, {
  schema_version: "plane.webhook.v1",
  event_id: "delivery-1",
  event_type: "work_item.updated",
  idempotency_key: "delivery-1",
  correlation_id: "plane:delivery-1",
  causation_id: null,
  origin: "plane",
  retry_attempt: 0,
  raw_payload_hash: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  source: "plane",
  event: "issue",
  action: "update",
  delivery_id: "delivery-1",
  resource_id: "work-item-1",
  webhook_id: "webhook-1",
  actor_id: "human-user-1",
  team: "Openclaw",
  project_id: "project-1",
  source_identifier: "OPN-273",
  sequence_id: 273,
  name: "Ready for agent",
  state_id: "state-ready",
  state_name: "Ready for Agent",
  priority: "high",
  label_names: ["agent:ready", "repo:docker"],
  agent_ready: { context: true, acceptance_criteria: true, safety_notes: true },
  agent_ready_checks: ["context", "acceptance_criteria", "safety_notes"],
  received_at: "2026-07-11T08:45:00.000Z",
});

const remoteCommand = fs.readFileSync(capturedCommandPath, "utf8");
assert.equal(remoteCommand.includes("cd '/srv/openclaw/workspace'"), true);
assert.equal(remoteCommand.includes("'tools/bin/openclaw-plane-n8n-dispatch' --event-file"), true);

fs.writeFileSync(
  opencInputPath,
  JSON.stringify({
    ...input,
    event_id: "delivery-openc-261",
    idempotency_key: "delivery-openc-261",
    correlation_id: "plane:delivery-openc-261",
    delivery_id: "delivery-openc-261",
    resource_id: "work-item-openc-261",
    team: undefined,
    source_identifier: undefined,
    identifier: "OPENC-261",
    sequence_id: 261,
    name: "Make workout state sync resilient",
    label_names: ["agent:ready", "repo:openclaw"],
    agent_ready: undefined,
    agent_ready_checks: undefined,
  }),
);

const opencResult = spawnSync("sh", ["-c", "exec sh \"$1\" < \"$2\"", "sh", scriptPath, opencInputPath], {
  encoding: "utf8",
  timeout: 10000,
  env: {
    ...process.env,
    PATH: `${tmpDir}:${process.env.PATH}`,
    FAKE_SSH_PAYLOAD: capturedOpencPayloadPath,
    FAKE_SSH_COMMAND: capturedCommandPath,
    OPENCLAW_SSH_HOST: "openclaw.internal",
    OPENCLAW_SSH_USER: "openclaw",
    OPENCLAW_SSH_PORT: "22",
    OPENCLAW_SSH_KEY_PATH: "/tmp/fake-key",
    OPENCLAW_WORKSPACE: "/srv/openclaw/workspace",
    OPENCLAW_PLANE_DISPATCH_COMMAND: "tools/bin/openclaw-plane-n8n-dispatch",
    NODE_BIN: process.execPath,
  },
});

assert.equal(
  opencResult.status,
  0,
  `OPENC sender exited ${opencResult.status} signal ${opencResult.signal}: ${opencResult.stderr || opencResult.error || ""}`,
);
assert.equal(opencResult.stderr, "");
const uploadedOpenc = JSON.parse(fs.readFileSync(capturedOpencPayloadPath, "utf8"));
assert.equal(uploadedOpenc.team, "openclaw");
assert.equal(uploadedOpenc.source_identifier, "OPENC-261");
assert.deepEqual(uploadedOpenc.agent_ready_checks, ["context", "acceptance_criteria", "safety_notes"]);

fs.writeFileSync(
  ignoredInputPath,
  JSON.stringify({
    ...input,
    state_name: "Todo",
  }),
);

const ignoredResult = spawnSync("sh", ["-c", "exec sh \"$1\" < \"$2\"", "sh", scriptPath, ignoredInputPath], {
  encoding: "utf8",
  timeout: 10000,
  env: {
    ...process.env,
    PATH: `${tmpDir}:${process.env.PATH}`,
    FAKE_SSH_PAYLOAD: unexpectedPayloadPath,
    NODE_BIN: process.execPath,
  },
});

assert.equal(
  ignoredResult.status,
  0,
  `ignored sender exited ${ignoredResult.status} signal ${ignoredResult.signal}: ${ignoredResult.stderr || ignoredResult.error || ""}`,
);
assert.equal(ignoredResult.stderr, "");
const ignoredPreview = JSON.parse(ignoredResult.stdout);
assert.equal(ignoredPreview.decision, "ignored");
assert.equal(ignoredPreview.reason, "not_ready_for_agent");
assert.equal(fs.existsSync(unexpectedPayloadPath), false);

fs.writeFileSync(
  needsInputPath,
  JSON.stringify({
    ...input,
    label_names: ["agent:ready"],
  }),
);

const needsInputResult = spawnSync("sh", ["-c", "exec sh \"$1\" < \"$2\"", "sh", scriptPath, needsInputPath], {
  encoding: "utf8",
  timeout: 10000,
  env: {
    ...process.env,
    PATH: `${tmpDir}:${process.env.PATH}`,
    FAKE_SSH_PAYLOAD: unexpectedPayloadPath,
    NODE_BIN: process.execPath,
  },
});

assert.equal(
  needsInputResult.status,
  0,
  `needs-input sender exited ${needsInputResult.status} signal ${needsInputResult.signal}: ${needsInputResult.stderr || needsInputResult.error || ""}`,
);
assert.equal(needsInputResult.stderr, "");
const needsInputPreview = JSON.parse(needsInputResult.stdout);
assert.equal(needsInputPreview.decision, "needs_input");
assert.equal(needsInputPreview.reason, "missing_repo_label");
assert.equal(fs.existsSync(unexpectedPayloadPath), false);

fs.rmSync(tmpDir, { recursive: true, force: true });
console.log("send-plane-openclaw-dispatch tests passed");
