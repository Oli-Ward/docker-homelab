#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const { buildPlaneWorkflowReport } = require("./plane-workflow-report");

const calls = [];

async function fakeFetch(url, options) {
  calls.push({ url, options });
  assert.equal(options.headers.Authorization, "Bearer gateway-token");
  assert.equal(options.headers.Accept, "application/json");

  if (url === "http://gateway.example/v1/workflow/plane/projects/project-1/states") {
    return {
      ok: true,
      status: 200,
      async json() {
        return {
          items: [
            { id: "state-ready", name: "Ready for Agent" },
            { id: "state-progress", name: "In Progress" },
            { id: "state-blocked", name: "Blocked" },
          ],
        };
      },
    };
  }

  if (
    url ===
    "http://gateway.example/v1/workflow/plane/projects/project-1/work-items?limit=3"
  ) {
    return {
      ok: true,
      status: 200,
      async json() {
        return {
          items: [
            {
              id: "work-1",
              name: "Build Plane pickup",
              sequence_id: 273,
              state_id: "state-ready",
              priority: "high",
              labels: [{ id: "label-agent", name: "agent:ready" }],
              raw: { should: "not-forward" },
            },
            {
              id: "work-2",
              name: "Fix migration discrepancy",
              sequence_id: 269,
              state_id: "state-blocked",
              priority: "urgent",
              labels: [{ id: "label-blocked", name: "blocked:external" }],
            },
            {
              id: "work-3",
              name: "Write report",
              sequence_id: 274,
              state_id: "state-progress",
              priority: null,
              labels: [],
            },
          ],
        };
      },
    };
  }

  throw new Error(`unexpected fetch ${url}`);
}

(async () => {
  const report = await buildPlaneWorkflowReport({
    gatewayUrl: "http://gateway.example/",
    gatewayToken: "gateway-token",
    projectId: "project-1",
    limit: 3,
    now: () => "2026-07-11T09:15:00.000Z",
    fetchImpl: fakeFetch,
  });

  assert.deepEqual(
    calls.map((call) => call.url),
    [
      "http://gateway.example/v1/workflow/plane/projects/project-1/states",
      "http://gateway.example/v1/workflow/plane/projects/project-1/work-items?limit=3",
    ],
  );
  assert.deepEqual(report, {
    source: "plane",
    report: "workflow-summary",
    generated_at: "2026-07-11T09:15:00.000Z",
    project_id: "project-1",
    total_items: 3,
    counts_by_state: {
      "Ready for Agent": 1,
      Blocked: 1,
      "In Progress": 1,
    },
    counts_by_priority: {
      high: 1,
      urgent: 1,
      none: 1,
    },
    ready_for_agent_count: 1,
    blocked_count: 1,
    items: [
      {
        id: "work-1",
        sequence_id: 273,
        name: "Build Plane pickup",
        state: "Ready for Agent",
        priority: "high",
        labels: ["agent:ready"],
      },
      {
        id: "work-2",
        sequence_id: 269,
        name: "Fix migration discrepancy",
        state: "Blocked",
        priority: "urgent",
        labels: ["blocked:external"],
      },
      {
        id: "work-3",
        sequence_id: 274,
        name: "Write report",
        state: "In Progress",
        priority: "none",
        labels: [],
      },
    ],
  });

  console.log("plane-workflow-report tests passed");
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
