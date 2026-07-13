#!/usr/bin/env node
"use strict";

const fs = require("node:fs");

function stringValue(value) {
  return typeof value === "string" && value ? value : null;
}

function integerValue(value) {
  return Number.isInteger(value) ? value : null;
}

function labelNames(value) {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((label) => typeof label === "string" && label);
}

const REQUIRED_AGENT_READY_CHECKS = ["context", "acceptance_criteria", "safety_notes"];

function agentReadyChecks(event) {
  if (event.agent_ready && typeof event.agent_ready === "object" && !Array.isArray(event.agent_ready)) {
    return {
      present: true,
      checks: Object.entries(event.agent_ready)
        .filter(([, enabled]) => Boolean(enabled))
        .map(([name]) => String(name).trim().toLowerCase())
        .filter(Boolean),
    };
  }
  if (Array.isArray(event.agent_ready_checks)) {
    return {
      present: true,
      checks: event.agent_ready_checks.map((check) => String(check).trim().toLowerCase()).filter(Boolean),
    };
  }
  return { present: false, checks: [] };
}

function missingAgentReadyChecks(event) {
  const readiness = agentReadyChecks(event);
  const complete = new Set(readiness.checks);
  return {
    present: readiness.present,
    missing: REQUIRED_AGENT_READY_CHECKS.filter((check) => !complete.has(check)),
  };
}

function repoFromLabels(labels) {
  const repoLabel = labels.find((label) => label.startsWith("repo:"));
  if (!repoLabel) {
    return null;
  }
  const repo = repoLabel.slice("repo:".length).trim();
  return repo || null;
}

function classifyPlaneAgentPickup(event) {
  const labels = labelNames(event.label_names);
  const repo = repoFromLabels(labels);
  let decision = "ready";
  let reason = "ready_for_agent";

  if (event.event !== "issue") {
    decision = "ignored";
    reason = "unsupported_event";
  } else if (event.state_name !== "Ready for Agent") {
    decision = "ignored";
    reason = "not_ready_for_agent";
  } else if (!repo) {
    decision = "needs_input";
    reason = "missing_repo_label";
  } else {
    const readiness = missingAgentReadyChecks(event);
    if (readiness.missing.length > 0) {
      decision = "needs_input";
      reason = readiness.present
        ? `agent_ready_incomplete: ${readiness.missing.join(", ")}`
        : `agent_ready_missing: ${readiness.missing.join(", ")}`;
    }
  }

  return {
    source: "plane",
    preview: "agent-pickup",
    decision,
    reason,
    correlation_id: stringValue(event.correlation_id),
    resource_id: stringValue(event.resource_id),
    project_id: stringValue(event.project_id),
    sequence_id: integerValue(event.sequence_id),
    state_name: stringValue(event.state_name),
    priority: stringValue(event.priority),
    labels,
    repo,
    ticket_name: stringValue(event.name),
  };
}

function readInput(inputPath) {
  if (inputPath) {
    return fs.readFileSync(inputPath, "utf8");
  }
  return fs.readFileSync(0, "utf8");
}

function buildPlaneAgentPickupPreviewOutput(inputPath) {
  const input = readInput(inputPath);
  const event = JSON.parse(input);
  return `${JSON.stringify(classifyPlaneAgentPickup(event))}\n`;
}

function main() {
  process.stdout.write(buildPlaneAgentPickupPreviewOutput(process.argv[2]));
}

if (require.main === module) {
  try {
    main();
  } catch (error) {
    process.stderr.write(`${error.message}\n`);
    process.exit(1);
  }
}

module.exports = {
  buildPlaneAgentPickupPreviewOutput,
  classifyPlaneAgentPickup,
};
