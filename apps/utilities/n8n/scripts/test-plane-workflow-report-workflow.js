#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const workflowPath = path.join(
  __dirname,
  "..",
  "workflows",
  "plane-workflow-report.workflow.json",
);

const workflow = JSON.parse(fs.readFileSync(workflowPath, "utf8"));

assert.equal(workflow.id, "plane-workflow-report");
assert.equal(workflow.name, "plane-workflow-report");
assert.equal(workflow.active, false);
assert.equal(workflow.settings.executionOrder, "v1");

const schedule = workflow.nodes.find((node) => node.type === "n8n-nodes-base.scheduleTrigger");
assert.ok(schedule, "workflow must include a schedule trigger");

const command = workflow.nodes.find((node) => node.name === "Generate Plane Workflow Report");
assert.ok(command, "workflow must include the report command node");
assert.match(command.parameters.command, /\/opt\/n8n-scripts\/plane-workflow-report\.js/);

const parser = workflow.nodes.find((node) => node.name === "Parse Plane Workflow Report");
assert.ok(parser, "workflow must parse the command stdout into JSON");
assert.match(parser.parameters.jsCode, /JSON\.parse/);

console.log("plane-workflow-report workflow tests passed");
