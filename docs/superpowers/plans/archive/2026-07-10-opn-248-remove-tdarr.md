# OPN-248 Remove Tdarr Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove Tdarr from the homelab's active service catalog and external access because it is too resource-heavy for the server.

**Architecture:** Remove durable repo-managed service/dashboard configuration and remove live NPM/AuthentiK access objects. Keep appdata, test library, and transcode cache directories intact for manual review or later cleanup.

**Tech Stack:** Docker Compose, Homepage YAML, Nginx Proxy Manager API, AuthentiK API, Markdown docs, Linear.

---

## Constraints

- Do not delete `/srv/appdata/tdarr`, `/data/tdarr-test-library`, or `/data/tdarr-transcode-cache`.
- Do not run `docker compose up`, `docker compose down`, `docker compose pull`, or direct container removal.
- Prefer Komodo for undeploying/stopping the running Tdarr container.
- Remove live NPM/AuthentiK objects because the user explicitly approved external UI cleanup.

## Task 1: Remove Repo-Managed Tdarr Config

**Files:**
- Modify: `apps/media/compose.yml`
- Modify: `apps/media/example.env`
- Modify: `apps/utilities/homepage/services.yaml`
- Modify: `README.md`
- Modify: `docs/media/tdarr.md`

- [x] **Step 1: Remove Tdarr service from media Compose**

Delete the `tdarr` service block from `apps/media/compose.yml`.

- [x] **Step 2: Remove Tdarr example env variables**

Delete the `TDARR_*` block from `apps/media/example.env`.

- [x] **Step 3: Remove Tdarr Homepage card**

Delete the `Tdarr` entry from `apps/utilities/homepage/services.yaml`.

- [x] **Step 4: Update README service catalog**

Remove Tdarr from the Media service list and remove the Tdarr safety note.

- [x] **Step 5: Record removal decision**

Update `docs/media/tdarr.md` to state Tdarr was removed because it was too resource-heavy for this server and that data directories were intentionally left intact.

## Task 2: Remove Live External Access

**Systems:**
- Nginx Proxy Manager
- AuthentiK

- [x] **Step 1: Remove NPM proxy host**

Delete NPM proxy host `tdarr.home.lab` if present.

- [x] **Step 2: Remove AuthentiK outpost attachment, app, and provider**

Detach provider `tdarr` from the embedded outpost, then delete the `Tdarr` application and `tdarr` proxy provider if present.

## Task 3: Verify and Commit

- [x] **Step 1: Validate media Compose**

Run `docker compose config` from `apps/media` with safe placeholder env values. Expected: config renders without any `tdarr` service or `TDARR_*` references.

- [x] **Step 2: Verify live removal**

Check that NPM has no `tdarr.home.lab` proxy host and AuthentiK has no `Tdarr` app/provider. `https://tdarr.home.lab` should no longer route to Tdarr through NPM.

- [x] **Step 3: Commit**

Commit repo updates with `OPN-248: remove Tdarr`.
