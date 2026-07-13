#!/usr/bin/env node
"use strict";

function normalizeGatewayUrl(gatewayUrl) {
  return String(gatewayUrl || "").replace(/\/+$/, "");
}

function required(value, name) {
  if (!value) {
    throw new Error(`Set ${name}`);
  }
  return value;
}

async function fetchGatewayJson({ gatewayUrl, gatewayToken, path, fetchImpl }) {
  const response = await fetchImpl(`${normalizeGatewayUrl(gatewayUrl)}${path}`, {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${gatewayToken}`,
    },
  });
  if (!response.ok) {
    throw new Error(`gateway returned ${response.status} for ${path}`);
  }
  return response.json();
}

function countBy(values) {
  return values.reduce((counts, value) => {
    counts[value] = (counts[value] || 0) + 1;
    return counts;
  }, {});
}

function stateNameFor(workItem, statesById) {
  return statesById.get(workItem.state_id) || workItem.state_id || "unknown";
}

function priorityFor(workItem) {
  return workItem.priority === null || workItem.priority === undefined || workItem.priority === ""
    ? "none"
    : String(workItem.priority);
}

function optionalTimestamp(workItem, fieldName) {
  const value = workItem[fieldName];
  return typeof value === "string" && value ? value : null;
}

function labelNames(workItem) {
  const labels = Array.isArray(workItem.labels) ? workItem.labels : [];
  return labels
    .map((label) => {
      if (typeof label === "string") {
        return label;
      }
      if (label && typeof label === "object" && label.name) {
        return String(label.name);
      }
      return "";
    })
    .filter(Boolean);
}

function thresholdHours(value, fallback) {
  const numeric = Number(value);
  return Number.isFinite(numeric) && numeric > 0 ? numeric : fallback;
}

function ageHoursSince(timestamp, generatedAt) {
  if (!timestamp) {
    return null;
  }
  const timestampMs = Date.parse(timestamp);
  const generatedMs = Date.parse(generatedAt);
  if (!Number.isFinite(timestampMs) || !Number.isFinite(generatedMs) || timestampMs > generatedMs) {
    return null;
  }
  return Math.round(((generatedMs - timestampMs) / 36e5) * 10) / 10;
}

function summarizeWorkItems(workItems, statesById) {
  return workItems.map((workItem) => ({
    id: String(workItem.id || ""),
    sequence_id: workItem.sequence_id ?? null,
    name: String(workItem.name || ""),
    state: stateNameFor(workItem, statesById),
    priority: priorityFor(workItem),
    created_at: optionalTimestamp(workItem, "created_at"),
    updated_at: optionalTimestamp(workItem, "updated_at"),
    labels: labelNames(workItem),
  }));
}

function actionableReason(item, thresholdsHours, generatedAt) {
  const ageHours = ageHoursSince(item.updated_at || item.created_at, generatedAt);
  if (ageHours === null) {
    return null;
  }

  if (item.state === "Blocked" && ageHours >= thresholdsHours.blocked) {
    return {
      reason: "blocked_over_threshold",
      age_hours: ageHours,
      threshold_hours: thresholdsHours.blocked,
    };
  }
  if (item.state === "Needs Input" && ageHours >= thresholdsHours.needs_input) {
    return {
      reason: "needs_input_over_threshold",
      age_hours: ageHours,
      threshold_hours: thresholdsHours.needs_input,
    };
  }
  if (item.state === "In Review" && ageHours >= thresholdsHours.in_review) {
    return {
      reason: "stale_in_review",
      age_hours: ageHours,
      threshold_hours: thresholdsHours.in_review,
    };
  }
  return null;
}

function actionableItems(items, thresholdsHours, generatedAt) {
  return items.flatMap((item) => {
    const action = actionableReason(item, thresholdsHours, generatedAt);
    return action ? [{ ...item, ...action }] : [];
  });
}

async function buildPlaneWorkflowReport({
  gatewayUrl,
  gatewayToken,
  projectId,
  limit = 100,
  needsInputHours = 24,
  blockedHours = 48,
  inReviewHours = 72,
  now = () => new Date().toISOString(),
  fetchImpl = globalThis.fetch,
}) {
  required(gatewayUrl, "MEDIA_GATEWAY_URL");
  required(gatewayToken, "MEDIA_GATEWAY_TOKEN");
  required(projectId, "PLANE_REPORT_PROJECT_ID");
  if (typeof fetchImpl !== "function") {
    throw new Error("fetch is unavailable");
  }

  const encodedProjectId = encodeURIComponent(projectId);
  const [statesPayload, workItemsPayload] = await Promise.all([
    fetchGatewayJson({
      gatewayUrl,
      gatewayToken,
      path: `/v1/workflow/plane/projects/${encodedProjectId}/states`,
      fetchImpl,
    }),
    fetchGatewayJson({
      gatewayUrl,
      gatewayToken,
      path: `/v1/workflow/plane/projects/${encodedProjectId}/work-items?limit=${Number(limit)}`,
      fetchImpl,
    }),
  ]);

  const states = Array.isArray(statesPayload.items) ? statesPayload.items : [];
  const statesById = new Map(
    states
      .filter((state) => state && state.id)
      .map((state) => [String(state.id), String(state.name || state.id)]),
  );
  const workItems = Array.isArray(workItemsPayload.items) ? workItemsPayload.items : [];
  const items = summarizeWorkItems(workItems, statesById);
  const generatedAt = now();
  const thresholds = {
    needs_input: thresholdHours(needsInputHours, 24),
    blocked: thresholdHours(blockedHours, 48),
    in_review: thresholdHours(inReviewHours, 72),
  };
  const actions = actionableItems(items, thresholds, generatedAt);
  const stateValues = items.map((item) => item.state);
  const priorityValues = items.map((item) => item.priority);

  return {
    source: "plane",
    report: "workflow-summary",
    generated_at: generatedAt,
    project_id: projectId,
    total_items: items.length,
    thresholds_hours: thresholds,
    counts_by_state: countBy(stateValues),
    counts_by_priority: countBy(priorityValues),
    ready_for_agent_count: items.filter((item) => item.state === "Ready for Agent").length,
    blocked_count: items.filter((item) => item.state === "Blocked").length,
    needs_input_count: items.filter((item) => item.state === "Needs Input").length,
    in_review_count: items.filter((item) => item.state === "In Review").length,
    stale_in_review_count: actions.filter((item) => item.reason === "stale_in_review").length,
    actionable_count: actions.length,
    items,
    actionable_items: actions,
  };
}

async function main() {
  const report = await buildPlaneWorkflowReport({
    gatewayUrl: process.env.MEDIA_GATEWAY_URL,
    gatewayToken: process.env.MEDIA_GATEWAY_TOKEN,
    projectId: process.env.PLANE_REPORT_PROJECT_ID,
    limit: process.env.PLANE_REPORT_LIMIT || 100,
    needsInputHours: process.env.PLANE_REPORT_NEEDS_INPUT_HOURS || 24,
    blockedHours: process.env.PLANE_REPORT_BLOCKED_HOURS || 48,
    inReviewHours: process.env.PLANE_REPORT_IN_REVIEW_HOURS || 72,
  });
  process.stdout.write(`${JSON.stringify(report)}\n`);
}

if (require.main === module) {
  main().catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exit(1);
  });
}

module.exports = {
  actionableItems,
  buildPlaneWorkflowReport,
  summarizeWorkItems,
};
