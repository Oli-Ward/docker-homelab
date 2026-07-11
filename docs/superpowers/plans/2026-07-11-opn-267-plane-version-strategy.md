# OPN-267 Plane Version Strategy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Plane Commercial app image updates controlled through the existing `APP_RELEASE_VERSION` env variable and document the safe update flow without changing the current default version.

**Architecture:** Keep the default Plane release at `v2.6.3`, but replace hardcoded Plane Commercial image tags and `APP_VERSION` with `${APP_RELEASE_VERSION:-v2.6.3}`. Leave non-Plane dependency images pinned or floating exactly as they are.

**Tech Stack:** Docker Compose, example env, Plane stack README, non-deploying compose validation.

---

### Task 1: Version Variable Wiring

**Files:**
- Modify: `apps/plane/compose.yml`

- [x] **Step 1: Verify current hardcoded Plane release drift**

Run:

```bash
rg -n "makeplane/.+:v2\.6\.3|APP_VERSION: v2\.6\.3" apps/plane/compose.yml
```

Expected: reports hardcoded Plane image tags and `APP_VERSION`.

- [x] **Step 2: Replace hardcoded Plane release references**

Replace Plane Commercial `v2.6.3` tags and `APP_VERSION` with `${APP_RELEASE_VERSION:-v2.6.3}`. Do not change `makeplane/iframely`, PostgreSQL, Valkey, RabbitMQ, or MinIO images.

### Task 2: Documentation And Verification

**Files:**
- Modify: `apps/plane/README.md`

- [x] **Step 1: Document update strategy**

Document that Plane app images are controlled by `APP_RELEASE_VERSION`, and that updates require backup/checkpoint confirmation, `docker compose config`, Komodo deployment, and desktop/mobile smoke checks.

- [x] **Step 2: Verify**

Run:

```bash
rg -n "makeplane/.+:v2\.6\.3|APP_VERSION: v2\.6\.3" apps/plane/compose.yml
docker compose -p plane -f apps/plane/compose.yml --env-file apps/plane/example.env config --quiet
docker compose -p plane -f apps/plane/compose.yml --env-file apps/plane/example.env config --services
git diff --check
```

Expected: `rg` exits 1 because hardcoded Plane release references are gone; compose config and diff checks exit 0.

- [x] **Step 3: Commit and update Linear**

Commit with:

```bash
git commit -m "OPN-267: wire Plane image version env"
```

Update OPN-267 and OPN-264 with commit hash, verification, and the remaining live validation gaps.
