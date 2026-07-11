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

function summarizeWorkItems(workItems, statesById) {
  return workItems.map((workItem) => ({
    id: String(workItem.id || ""),
    sequence_id: workItem.sequence_id ?? null,
    name: String(workItem.name || ""),
    state: stateNameFor(workItem, statesById),
    priority: priorityFor(workItem),
    labels: labelNames(workItem),
  }));
}

async function buildPlaneWorkflowReport({
  gatewayUrl,
  gatewayToken,
  projectId,
  limit = 100,
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
  const stateValues = items.map((item) => item.state);
  const priorityValues = items.map((item) => item.priority);

  return {
    source: "plane",
    report: "workflow-summary",
    generated_at: now(),
    project_id: projectId,
    total_items: items.length,
    counts_by_state: countBy(stateValues),
    counts_by_priority: countBy(priorityValues),
    ready_for_agent_count: items.filter((item) => item.state === "Ready for Agent").length,
    blocked_count: items.filter((item) => item.state === "Blocked").length,
    items,
  };
}

async function main() {
  const report = await buildPlaneWorkflowReport({
    gatewayUrl: process.env.MEDIA_GATEWAY_URL,
    gatewayToken: process.env.MEDIA_GATEWAY_TOKEN,
    projectId: process.env.PLANE_REPORT_PROJECT_ID,
    limit: process.env.PLANE_REPORT_LIMIT || 100,
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
  buildPlaneWorkflowReport,
  summarizeWorkItems,
};
