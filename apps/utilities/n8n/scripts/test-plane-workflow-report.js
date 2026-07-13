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
            { id: "state-needs-input", name: "Needs Input" },
            { id: "state-review", name: "In Review" },
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
              updated_at: "2026-07-13T11:30:00.000Z",
              labels: [{ id: "label-agent", name: "agent:ready" }],
              raw: { should: "not-forward" },
            },
            {
              id: "work-2",
              name: "Fix migration discrepancy",
              sequence_id: 269,
              state_id: "state-blocked",
              priority: "urgent",
              updated_at: "2026-07-11T10:00:00.000Z",
              labels: [{ id: "label-blocked", name: "blocked:external" }],
            },
            {
              id: "work-3",
              name: "Write report",
              sequence_id: 274,
              state_id: "state-progress",
              priority: null,
              updated_at: "2026-07-13T10:00:00.000Z",
              labels: [],
            },
            {
              id: "work-4",
              name: "Needs a decision",
              sequence_id: 278,
              state_id: "state-needs-input",
              priority: "medium",
              updated_at: "2026-07-12T06:00:00.000Z",
              labels: [{ id: "label-oli", name: "blocked:oli" }],
            },
            {
              id: "work-5",
              name: "Review the migration",
              sequence_id: 279,
              state_id: "state-review",
              priority: "low",
              created_at: "2026-07-09T12:00:00.000Z",
              updated_at: "2026-07-09T12:00:00.000Z",
              labels: [],
            },
            {
              id: "work-6",
              name: "Fresh review item",
              sequence_id: 280,
              state_id: "state-review",
              priority: "low",
              updated_at: "not-a-date",
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
    now: () => "2026-07-13T12:00:00.000Z",
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
    generated_at: "2026-07-13T12:00:00.000Z",
    project_id: "project-1",
    total_items: 6,
    thresholds_hours: {
      needs_input: 24,
      blocked: 48,
      in_review: 72,
    },
    counts_by_state: {
      "Ready for Agent": 1,
      Blocked: 1,
      "In Progress": 1,
      "Needs Input": 1,
      "In Review": 2,
    },
    counts_by_priority: {
      high: 1,
      urgent: 1,
      none: 1,
      medium: 1,
      low: 2,
    },
    ready_for_agent_count: 1,
    blocked_count: 1,
    needs_input_count: 1,
    in_review_count: 2,
    stale_in_review_count: 1,
    actionable_count: 3,
    items: [
      {
        id: "work-1",
        sequence_id: 273,
        name: "Build Plane pickup",
        state: "Ready for Agent",
        priority: "high",
        created_at: null,
        updated_at: "2026-07-13T11:30:00.000Z",
        labels: ["agent:ready"],
      },
      {
        id: "work-2",
        sequence_id: 269,
        name: "Fix migration discrepancy",
        state: "Blocked",
        priority: "urgent",
        created_at: null,
        updated_at: "2026-07-11T10:00:00.000Z",
        labels: ["blocked:external"],
      },
      {
        id: "work-3",
        sequence_id: 274,
        name: "Write report",
        state: "In Progress",
        priority: "none",
        created_at: null,
        updated_at: "2026-07-13T10:00:00.000Z",
        labels: [],
      },
      {
        id: "work-4",
        sequence_id: 278,
        name: "Needs a decision",
        state: "Needs Input",
        priority: "medium",
        created_at: null,
        updated_at: "2026-07-12T06:00:00.000Z",
        labels: ["blocked:oli"],
      },
      {
        id: "work-5",
        sequence_id: 279,
        name: "Review the migration",
        state: "In Review",
        priority: "low",
        created_at: "2026-07-09T12:00:00.000Z",
        updated_at: "2026-07-09T12:00:00.000Z",
        labels: [],
      },
      {
        id: "work-6",
        sequence_id: 280,
        name: "Fresh review item",
        state: "In Review",
        priority: "low",
        created_at: null,
        updated_at: "not-a-date",
        labels: [],
      },
    ],
    actionable_items: [
      {
        id: "work-2",
        sequence_id: 269,
        name: "Fix migration discrepancy",
        state: "Blocked",
        priority: "urgent",
        created_at: null,
        updated_at: "2026-07-11T10:00:00.000Z",
        labels: ["blocked:external"],
        reason: "blocked_over_threshold",
        age_hours: 50,
        threshold_hours: 48,
      },
      {
        id: "work-4",
        sequence_id: 278,
        name: "Needs a decision",
        state: "Needs Input",
        priority: "medium",
        created_at: null,
        updated_at: "2026-07-12T06:00:00.000Z",
        labels: ["blocked:oli"],
        reason: "needs_input_over_threshold",
        age_hours: 30,
        threshold_hours: 24,
      },
      {
        id: "work-5",
        sequence_id: 279,
        name: "Review the migration",
        state: "In Review",
        priority: "low",
        created_at: "2026-07-09T12:00:00.000Z",
        updated_at: "2026-07-09T12:00:00.000Z",
        labels: [],
        reason: "stale_in_review",
        age_hours: 96,
        threshold_hours: 72,
      },
    ],
  });

  assert.equal(JSON.stringify(report).includes("should"), false);
  assert.equal(JSON.stringify(report).includes("not-forward"), false);
  console.log("plane-workflow-report tests passed");
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
