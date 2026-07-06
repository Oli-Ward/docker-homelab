#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const { spawnSync } = require("node:child_process");
const path = require("node:path");

const verifierPath = path.join(__dirname, "verify-linear-openclaw-pickup.js");
const secret = "test-linear-secret";

function sign(rawBody) {
  return crypto.createHmac("sha256", secret).update(rawBody).digest("hex");
}

function runVerifier(envelope, env = {}) {
  const result = spawnSync(process.execPath, [verifierPath], {
    input: JSON.stringify(envelope),
    encoding: "utf8",
    env: {
      ...process.env,
      LINEAR_OPENCLAW_WEBHOOK_SECRET: secret,
      ...env,
    },
  });

  assert.equal(result.stderr, "", "verifier must not write to stderr");
  assert.equal(result.status, 0, `verifier exited ${result.status}: ${result.stdout}`);
  return JSON.parse(result.stdout);
}

function issuePayload(overrides = {}) {
  const { data: dataOverrides = {}, ...payloadOverrides } = overrides;
  return {
    type: "Issue",
    action: "create",
    data: {
      id: "issue-uuid-1",
      identifier: "OPN-234",
      title: "Install n8n Linear webhook ingress for OpenClaw pickup",
      url: "https://linear.app/alex-lawson/issue/OPN-234/install-n8n-linear-webhook-ingress-for-openclaw-pickup",
      team: {
        key: "OPN",
        name: "Openclaw",
      },
      state: {
        name: "Todo",
      },
      labels: {
        nodes: [{ name: "agent:ready" }, { name: "tag:linear" }],
      },
      priorityLabel: "Medium",
      ...dataOverrides,
    },
    ...payloadOverrides,
  };
}

function envelopeFor(payload, headers = {}) {
  const rawBody = JSON.stringify(payload);
  return {
    rawBody,
    headers: {
      "linear-signature": sign(rawBody),
      "linear-delivery": "delivery-123",
      "linear-event": "Issue",
      ...headers,
    },
  };
}

function testAcceptedCreateEvent() {
  const result = runVerifier(envelopeFor(issuePayload()));

  assert.equal(result.status, "accepted");
  assert.equal(result.payload.event_id, "delivery-123");
  assert.equal(result.payload.event_type, "Issue");
  assert.equal(result.payload.action, "create");
  assert.equal(result.payload.issue.identifier, "OPN-234");
  assert.equal(result.payload.issue.team_key, "OPN");
  assert.deepEqual(result.payload.issue.labels, ["agent:ready", "tag:linear"]);
}

function testAcceptedCreateEventFromBase64RawBody() {
  const payload = issuePayload();
  const rawBody = JSON.stringify(payload);
  const result = runVerifier({
    rawBodyBase64: Buffer.from(rawBody, "utf8").toString("base64"),
    headers: {
      "linear-signature": sign(rawBody),
      "linear-delivery": "delivery-base64",
      "linear-event": "Issue",
    },
  });

  assert.equal(result.status, "accepted");
  assert.equal(result.payload.event_id, "delivery-base64");
  assert.equal(result.payload.issue.identifier, "OPN-234");
}

function testAcceptedUpdateEvent() {
  const result = runVerifier(envelopeFor(issuePayload({ action: "update" })));

  assert.equal(result.status, "accepted");
  assert.equal(result.payload.action, "update");
}

function testInvalidSignatureRejected() {
  const result = runVerifier(envelopeFor(issuePayload(), { "linear-signature": "bad" }));

  assert.equal(result.status, "rejected");
  assert.equal(result.reason, "invalid-signature");
  assert.equal(result.payload, undefined);
}

function testMalformedJsonRejected() {
  const rawBody = "{not-json";
  const result = runVerifier({
    rawBody,
    headers: {
      "linear-signature": sign(rawBody),
      "linear-delivery": "delivery-malformed",
      "linear-event": "Issue",
    },
  });

  assert.equal(result.status, "rejected");
  assert.equal(result.reason, "invalid-json");
}

function testNonIssueSuppressed() {
  const result = runVerifier(envelopeFor({ type: "Comment", action: "create", data: {} }));

  assert.equal(result.status, "suppressed");
  assert.equal(result.reason, "not-issue-event");
}

function testMissingGateSuppressed() {
  const result = runVerifier(
    envelopeFor(
      issuePayload({
        data: {
          labels: {
            nodes: [{ name: "tag:linear" }],
          },
        },
      }),
    ),
  );

  assert.equal(result.status, "suppressed");
  assert.equal(result.reason, "missing-agent-ready");
}

function testNonOpenclawTeamSuppressed() {
  const result = runVerifier(
    envelopeFor(
      issuePayload({
        data: {
          team: {
            key: "ABC",
            name: "Other",
          },
        },
      }),
    ),
  );

  assert.equal(result.status, "suppressed");
  assert.equal(result.reason, "not-openclaw-team");
}

for (const test of [
  testAcceptedCreateEvent,
  testAcceptedCreateEventFromBase64RawBody,
  testAcceptedUpdateEvent,
  testInvalidSignatureRejected,
  testMalformedJsonRejected,
  testNonIssueSuppressed,
  testMissingGateSuppressed,
  testNonOpenclawTeamSuppressed,
]) {
  test();
}

console.log("verify-linear-openclaw-pickup tests passed");
