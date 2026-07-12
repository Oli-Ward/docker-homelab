#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const workflowPath = path.join(
  __dirname,
  "..",
  "workflows",
  "plane-openclaw-dispatch.workflow.json",
);

const workflow = JSON.parse(fs.readFileSync(workflowPath, "utf8"));

assert.equal(workflow.id, "plane-openclaw-dispatch");
assert.equal(workflow.name, "plane-openclaw-dispatch");
assert.equal(workflow.active, false);
assert.equal(workflow.settings.executionOrder, "v1");

const webhook = workflow.nodes.find((node) => node.type === "n8n-nodes-base.webhook");
assert.ok(webhook, "workflow must include a webhook node");
assert.equal(webhook.parameters.httpMethod, "POST");
assert.equal(webhook.parameters.path, "plane-openclaw-dispatch");
assert.equal(webhook.parameters.responseMode, "responseNode");

const sender = workflow.nodes.find((node) => node.name === "Send OpenClaw Plane Dispatch");
assert.ok(sender, "workflow must include the sender command node");
assert.match(
  sender.parameters.command,
  /\/opt\/n8n-scripts\/send-plane-openclaw-dispatch\.sh/,
);

const payloadBuilder = workflow.nodes.find((node) => node.name === "Build Plane Dispatch Payload");
assert.ok(payloadBuilder, "workflow must include a payload builder node");
const assignmentNames = payloadBuilder.parameters.assignments.assignments.map(
  (assignment) => assignment.name,
);
assert.deepEqual(
  [
    "project_id",
    "team",
    "source_identifier",
    "sequence_id",
    "name",
    "state_id",
    "state_name",
    "priority",
    "label_names",
  ].filter((name) => !assignmentNames.includes(name)),
  [],
);

const response = workflow.nodes.find((node) => node.type === "n8n-nodes-base.respondToWebhook");
assert.ok(response, "workflow must return a webhook response");
assert.equal(response.parameters.respondWith, "json");
assert.match(response.parameters.responseBody, /plane-openclaw-dispatch/);
assert.match(response.parameters.responseBody, /correlation_id/);

console.log("plane-openclaw-dispatch workflow tests passed");
