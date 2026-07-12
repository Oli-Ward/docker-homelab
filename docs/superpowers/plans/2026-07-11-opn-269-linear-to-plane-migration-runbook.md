# OPN-269 Linear to Plane Migration Runbook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a repo-managed Linear-to-Plane migration runbook that defines safe dry-run, verification, discrepancy, cutover, and rollback gates before Linear stops being the source of truth.

**Architecture:** This is an operator/documentation slice for OPN-269, not an import script. The runbook should sit under `docs/migrations/`, link back to the shared Plane workflow contract, and explicitly separate read-only Linear export, test Plane import, verification evidence, production cutover, and rollback. It must not require reading or committing secrets.

**Tech Stack:** Markdown documentation, existing Plane workflow contract, non-deploying repository validation.

---

### Task 1: Migration Runbook

**Files:**
- Add: `docs/migrations/2026-07-11-opn-269-linear-to-plane-migration.md`

- [x] **Step 1: Add the runbook**

Create the migration runbook with these sections:

- Scope freeze.
- Preconditions and backups.
- Read-only Linear export evidence.
- Plane dry-run target.
- Field mapping gates.
- Verification matrix for counts, statuses, labels, priorities, parent/child relationships, links, comments, and attachments.
- Discrepancy report format.
- Cutover checklist.
- Rollback checklist.
- Post-cutover validation.

### Task 2: Cross-References

**Files:**
- Modify: `docs/workflow/plane.md`
- Modify: `README.md`

- [x] **Step 1: Link the runbook from workflow docs**

Add the migration runbook as the OPN-269 execution checklist from `docs/workflow/plane.md`.

- [x] **Step 2: Link the runbook from the root README**

Add the runbook next to the existing Plane workflow contract reference in `README.md`.

### Task 3: Verification and Linear

**Files:**
- Modify: this plan file as checkboxes complete.

- [x] **Step 1: Verify docs**

Run:

```bash
git diff --check
rg -n "(password|secret|token|api[_-]?key|BEGIN (RSA|OPENSSH|PRIVATE))" docs/migrations/2026-07-11-opn-269-linear-to-plane-migration.md docs/workflow/plane.md README.md
```

Expected: whitespace check exits 0; secret scan returns only policy wording or placeholder references.

- [x] **Step 2: Commit and update Linear**

Commit with:

```bash
git commit -m "OPN-269: document Linear to Plane migration runbook"
```

Update OPN-269 and OPN-264 with commit hash, verification, and remaining live dry-run/import gaps.
