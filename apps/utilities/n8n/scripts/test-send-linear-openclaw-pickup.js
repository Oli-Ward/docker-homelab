#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const scriptPath = path.join(__dirname, "send-linear-openclaw-pickup.sh");
const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "opn234-send-test-"));
const fakeSshPath = path.join(tmpDir, "ssh");
const capturedPayloadPath = path.join(tmpDir, "payload.json");
const capturedCommandPath = path.join(tmpDir, "remote-command.txt");

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
    printf '%s\\n' '{"status":"accepted","queued":true}'
    ;;
esac
`,
  { mode: 0o755 },
);

const input = {
  event_id: "delivery-123",
  action: "update",
  received_at: "2026-07-05T08:40:00.000Z",
  issue: {
    identifier: "OPN-234",
    title: "Install n8n Linear webhook ingress for OpenClaw pickup",
    team_name: "Openclaw",
    state: "Todo",
    labels: ["agent:ready", "tag:linear"],
    url: "https://linear.app/alex-lawson/issue/OPN-234/install-n8n-linear-webhook-ingress-for-openclaw-pickup",
  },
};

const result = spawnSync("sh", [scriptPath], {
  input: JSON.stringify(input),
  encoding: "utf8",
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
    OPENCLAW_LINEAR_HANDOFF_COMMAND: "tools/bin/openclaw-linear-n8n-handoff",
    NODE_BIN: process.execPath,
  },
});

assert.equal(result.status, 0, `sender exited ${result.status}: ${result.stderr}`);
assert.equal(result.stderr, "");
assert.match(result.stdout, /"status":"accepted"/);

const uploaded = JSON.parse(fs.readFileSync(capturedPayloadPath, "utf8"));
assert.deepEqual(uploaded, {
  event_id: "delivery-123",
  identifier: "OPN-234",
  title: "Install n8n Linear webhook ingress for OpenClaw pickup",
  action: "update",
  team: "Openclaw",
  status: "Todo",
  status_type: "",
  labels: ["agent:ready", "tag:linear"],
  url: "https://linear.app/alex-lawson/issue/OPN-234/install-n8n-linear-webhook-ingress-for-openclaw-pickup",
  received_at: "2026-07-05T08:40:00.000Z",
});

const remoteCommand = fs.readFileSync(capturedCommandPath, "utf8");
assert.equal(remoteCommand.includes("cd '/srv/openclaw/workspace'"), true);
assert.equal(remoteCommand.includes("'tools/bin/openclaw-linear-n8n-handoff' --event-file"), true);

fs.rmSync(tmpDir, { recursive: true, force: true });
console.log("send-linear-openclaw-pickup tests passed");
