#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const {
  buildPlaneAgentPickupPreviewOutput,
  classifyPlaneAgentPickup,
} = require("./plane-agent-pickup-preview");

function baseEvent(overrides = {}) {
  return {
    source: "plane",
    event: "issue",
    action: "update",
    correlation_id: "plane:delivery-1",
    delivery_id: "delivery-1",
    resource_id: "work-item-1",
    project_id: "project-1",
    sequence_id: 273,
    name: "Build the pickup loop",
    state_name: "Ready for Agent",
    priority: "high",
    label_names: ["agent:ready", "repo:docker"],
    agent_ready: { context: true, acceptance_criteria: true, safety_notes: true },
    description_html: "<p>must not leak</p>",
    raw_payload: { must: "not leak" },
    ...overrides,
  };
}

assert.deepEqual(classifyPlaneAgentPickup(baseEvent({ event: "comment" })), {
  source: "plane",
  preview: "agent-pickup",
  decision: "ignored",
  reason: "unsupported_event",
  correlation_id: "plane:delivery-1",
  resource_id: "work-item-1",
  project_id: "project-1",
  sequence_id: 273,
  state_name: "Ready for Agent",
  priority: "high",
  labels: ["agent:ready", "repo:docker"],
  repo: "docker",
  ticket_name: "Build the pickup loop",
});

assert.equal(
  classifyPlaneAgentPickup(baseEvent({ state_name: "In Progress" })).decision,
  "ignored",
);
assert.equal(
  classifyPlaneAgentPickup(baseEvent({ state_name: "In Progress" })).reason,
  "not_ready_for_agent",
);

assert.deepEqual(
  classifyPlaneAgentPickup(baseEvent({ label_names: ["agent:ready"] })),
  {
    source: "plane",
    preview: "agent-pickup",
    decision: "needs_input",
    reason: "missing_repo_label",
    correlation_id: "plane:delivery-1",
    resource_id: "work-item-1",
    project_id: "project-1",
    sequence_id: 273,
    state_name: "Ready for Agent",
    priority: "high",
    labels: ["agent:ready"],
    repo: null,
    ticket_name: "Build the pickup loop",
  },
);

assert.deepEqual(
  classifyPlaneAgentPickup(baseEvent({ agent_ready: { context: true, safety_notes: true } })),
  {
    source: "plane",
    preview: "agent-pickup",
    decision: "needs_input",
    reason: "agent_ready_incomplete: acceptance_criteria",
    correlation_id: "plane:delivery-1",
    resource_id: "work-item-1",
    project_id: "project-1",
    sequence_id: 273,
    state_name: "Ready for Agent",
    priority: "high",
    labels: ["agent:ready", "repo:docker"],
    repo: "docker",
    ticket_name: "Build the pickup loop",
  },
);

assert.deepEqual(
  classifyPlaneAgentPickup(
    baseEvent({
      agent_ready: null,
      agent_ready_checks: ["context", "acceptance_criteria", "safety_notes"],
    }),
  ),
  {
    source: "plane",
    preview: "agent-pickup",
    decision: "ready",
    reason: "ready_for_agent",
    correlation_id: "plane:delivery-1",
    resource_id: "work-item-1",
    project_id: "project-1",
    sequence_id: 273,
    state_name: "Ready for Agent",
    priority: "high",
    labels: ["agent:ready", "repo:docker"],
    repo: "docker",
    ticket_name: "Build the pickup loop",
  },
);

assert.deepEqual(classifyPlaneAgentPickup(baseEvent()), {
  source: "plane",
  preview: "agent-pickup",
  decision: "ready",
  reason: "ready_for_agent",
  correlation_id: "plane:delivery-1",
  resource_id: "work-item-1",
  project_id: "project-1",
  sequence_id: 273,
  state_name: "Ready for Agent",
  priority: "high",
  labels: ["agent:ready", "repo:docker"],
  repo: "docker",
  ticket_name: "Build the pickup loop",
});

const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "opn273-plane-preview-test-"));
const eventPath = path.join(tmpDir, "event.json");
fs.writeFileSync(eventPath, JSON.stringify(baseEvent()));

const output = JSON.parse(buildPlaneAgentPickupPreviewOutput(eventPath));
assert.equal(output.decision, "ready");
assert.equal(output.repo, "docker");
assert.equal(JSON.stringify(output).includes("description_html"), false);
assert.equal(JSON.stringify(output).includes("raw_payload"), false);
assert.equal(JSON.stringify(output).includes("must not leak"), false);

fs.rmSync(tmpDir, { recursive: true, force: true });
console.log("plane-agent-pickup-preview tests passed");
