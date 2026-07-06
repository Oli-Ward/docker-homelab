#!/usr/bin/env node
"use strict";

const crypto = require("node:crypto");

function readStdin() {
  return new Promise((resolve, reject) => {
    let input = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => {
      input += chunk;
    });
    process.stdin.on("end", () => resolve(input));
    process.stdin.on("error", reject);
  });
}

function writeResult(result) {
  process.stdout.write(`${JSON.stringify(result)}\n`);
}

function headerValue(headers, name) {
  const target = name.toLowerCase();
  for (const [key, value] of Object.entries(headers || {})) {
    if (key.toLowerCase() === target) {
      return Array.isArray(value) ? value[0] : value;
    }
  }
  return "";
}

function hmacHex(secret, rawBody) {
  return crypto.createHmac("sha256", secret).update(rawBody).digest("hex");
}

function timingSafeEqualHex(left, right) {
  if (typeof left !== "string" || typeof right !== "string") {
    return false;
  }

  if (!/^[0-9a-f]+$/i.test(left) || !/^[0-9a-f]+$/i.test(right)) {
    return false;
  }

  const leftBuffer = Buffer.from(left, "hex");
  const rightBuffer = Buffer.from(right, "hex");
  if (leftBuffer.length !== rightBuffer.length) {
    return false;
  }

  return crypto.timingSafeEqual(leftBuffer, rightBuffer);
}

function labelNames(labels) {
  if (Array.isArray(labels)) {
    return labels
      .map((label) => (typeof label === "string" ? label : label && label.name))
      .filter(Boolean);
  }

  if (labels && Array.isArray(labels.nodes)) {
    return labels.nodes
      .map((label) => (typeof label === "string" ? label : label && label.name))
      .filter(Boolean);
  }

  return [];
}

function normalizeIssue(payload, headers) {
  const eventType = payload.type || headerValue(headers, "linear-event");
  if (eventType !== "Issue") {
    return { status: "suppressed", reason: "not-issue-event" };
  }

  if (payload.action !== "create" && payload.action !== "update") {
    return { status: "suppressed", reason: "unsupported-action" };
  }

  const issue = payload.data || {};
  const team = issue.team || {};
  const teamKey = team.key || issue.teamKey || "";
  const teamName = team.name || issue.teamName || "";
  if (teamKey !== "OPN" && teamName.toLowerCase() !== "openclaw") {
    return { status: "suppressed", reason: "not-openclaw-team" };
  }

  const labels = labelNames(issue.labels);
  if (!labels.includes("agent:ready")) {
    return { status: "suppressed", reason: "missing-agent-ready" };
  }

  const identifier = issue.identifier || "";
  const delivery = headerValue(headers, "linear-delivery");
  const eventId = delivery || [identifier, payload.action].filter(Boolean).join(":");
  if (!eventId || !identifier || !issue.title || !issue.url) {
    return { status: "rejected", reason: "missing-required-fields" };
  }

  return {
    status: "accepted",
    payload: {
      event_id: eventId,
      event_type: "Issue",
      action: payload.action,
      received_at: new Date().toISOString(),
      issue: {
        id: issue.id || "",
        identifier,
        title: issue.title,
        url: issue.url,
        team_key: teamKey,
        team_name: teamName,
        state: issue.state && issue.state.name ? issue.state.name : "",
        labels,
        priority: issue.priorityLabel || issue.priority || "",
      },
    },
  };
}

async function main() {
  const secret = process.env.LINEAR_OPENCLAW_WEBHOOK_SECRET || "";
  if (!secret) {
    writeResult({ status: "rejected", reason: "missing-webhook-secret" });
    return;
  }

  let envelope;
  try {
    envelope = JSON.parse(await readStdin());
  } catch {
    writeResult({ status: "rejected", reason: "invalid-envelope" });
    return;
  }

  let rawBody = typeof envelope.rawBody === "string" ? envelope.rawBody : "";
  if (!rawBody && typeof envelope.rawBodyBase64 === "string" && envelope.rawBodyBase64) {
    try {
      rawBody = Buffer.from(envelope.rawBodyBase64, "base64").toString("utf8");
    } catch {
      rawBody = "";
    }
  }
  if (!rawBody) {
    writeResult({ status: "rejected", reason: "missing-raw-body" });
    return;
  }

  const signature = String(headerValue(envelope.headers, "linear-signature") || "");
  const expectedSignature = hmacHex(secret, rawBody);
  if (!timingSafeEqualHex(signature, expectedSignature)) {
    writeResult({ status: "rejected", reason: "invalid-signature" });
    return;
  }

  let payload;
  try {
    payload = JSON.parse(rawBody);
  } catch {
    writeResult({ status: "rejected", reason: "invalid-json" });
    return;
  }

  writeResult(normalizeIssue(payload, envelope.headers || {}));
}

main().catch(() => {
  writeResult({ status: "rejected", reason: "verifier-error" });
});
