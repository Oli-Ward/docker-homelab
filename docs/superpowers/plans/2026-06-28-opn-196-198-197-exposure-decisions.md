# OPN-196/198/197 Exposure Decisions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce report-only exposure model decisions for Jellyfin, gluetun-published downloader UIs, and n8n using OPN-190 live boundary audit evidence as source of truth.

**Architecture:** Add one short diagnostics/build-lanes decision report that references OPN-190 evidence and records the intended exposure model plus what OPN-175 should enforce later. Do not change Docker, Compose, firewall, reverse proxy, containers, or secret/env material. Post one concise Linear comment per issue with the decision and verification.

**Tech Stack:** Markdown diagnostics, Linear issue comments, read-only repo inspection.

---

### Task 1: Create Report-Only Exposure Decision Document

**Files:**
- Create: `diagnostics/build-lanes/2026-06-28-opn-196-198-197-exposure-decisions.md`

- [ ] **Step 1: Add the decision report**

Create `diagnostics/build-lanes/2026-06-28-opn-196-198-197-exposure-decisions.md` with:

```markdown
# OPN-196/198/197 Exposure Decisions

## Scope

This is a report-only follow-up to OPN-190 for OPN-196, OPN-198, and OPN-197.

No firewall changes, Docker or Compose changes, container restarts, reverse-proxy changes, or secret/env reads were performed.

## Source Of Truth

- OPN-190 live boundary audit: `diagnostics/build-lanes/2026-06-28-opn-190-live-media-boundary-audit.md`.
- Repo Compose evidence for current durable declarations:
  - `apps/media/compose.yml`
  - `apps/downloads/compose.yml`
  - `apps/utilities/compose.yml`
  - `apps/openclaw-gateway/README.md`

## OPN-196: Jellyfin TCP 8096

Current state from OPN-190: Jellyfin is directly host-published on all IPv4 and IPv6 interfaces at TCP `8096`. Repo state also declares `8096:8096` in `apps/media/compose.yml`.

Decision: keep Jellyfin reachable for normal human media use, but do not treat direct TCP `8096` as an OpenClaw integration path. OpenClaw should use only the OpenClaw gateway at TCP `8088`, which exposes selected read-only Jellyfin capabilities without sharing upstream Jellyfin credentials.

Recommended exposure model: LAN-only direct Jellyfin is acceptable if household clients need native Jellyfin discovery or direct playback. If remote or untrusted-client access is needed, prefer Nginx Proxy Manager plus Authentik/native Jellyfin auth rather than broad direct host exposure. Do not expose Jellyfin directly to OpenClaw beyond the gateway.

OPN-175 should later enforce: allow TCP `8096` only from approved LAN and/or trusted admin/VPN client ranges if direct Jellyfin remains approved; deny TCP `8096` from OpenClaw and non-approved sources; keep TCP `8088` restricted to the OpenClaw runtime IP.

## OPN-198: gluetun TCP 8080 and TCP 6789

Current state from OPN-190: gluetun publishes TCP `8080` and TCP `6789` on all IPv4 and IPv6 interfaces. Targeted Docker metadata and repo Compose evidence identify TCP `8080` as qBittorrent web UI and TCP `6789` as NZBGet web UI. qBittorrent and NZBGet share the gluetun network namespace and have no direct host-published ports on their own container rows.

Decision: these are downloader admin UIs and should not be reachable from OpenClaw. They also should not be broadly reachable from the LAN by default.

Recommended exposure model: restrict qBittorrent and NZBGet UI access to trusted admin clients only, ideally through the established reverse proxy/auth path or a narrow admin/VPN source range. Do not expose them through the OpenClaw gateway unless a future capability-specific issue defines tightly scoped non-admin actions.

OPN-175 should later enforce: deny TCP `8080` and TCP `6789` by default; add allow rules only for approved admin source ranges if direct admin UI access remains necessary; ensure OpenClaw runtime IP is not allowed to reach either UI directly.

## OPN-197: n8n TCP 5678 and Runtime Mounts

Current state from OPN-190: n8n is directly host-published on all IPv4 and IPv6 interfaces at TCP `5678`. Targeted metadata found n8n is not privileged, uses private IPC, has only its application data bind mount, and has no observed Docker socket mount or broad host mount.

Decision: n8n has no observed Docker socket or broad host mount risk in the approved evidence, but direct TCP `5678` remains an automation admin surface and should not be broadly exposed. OpenClaw should not call n8n directly unless a future gateway/capability issue explicitly approves a narrow interface.

Recommended exposure model: put n8n behind Nginx Proxy Manager and Authentik or restrict direct access to trusted admin/VPN source ranges only. Prefer closing broad direct TCP `5678` exposure after confirming the intended access path.

OPN-175 should later enforce: deny TCP `5678` by default; add allow rules only for approved admin/proxy source ranges if needed; keep Docker socket and broad host mounts prohibited for n8n unless a separate reviewed issue approves them.

## OPN-175 Enforcement Notes

OPN-175 should treat these report-only decisions as policy inputs, not as evidence that enforcement has happened:

- TCP `8088`: allow only from the OpenClaw runtime IP to the media host gateway listener.
- TCP `8096`: allow only approved LAN/trusted-client Jellyfin access if direct Jellyfin remains approved; deny OpenClaw and unapproved sources.
- TCP `8080`: deny qBittorrent UI by default; allow only approved admin source ranges if direct UI access remains necessary.
- TCP `6789`: deny NZBGet UI by default; allow only approved admin source ranges if direct UI access remains necessary.
- TCP `5678`: deny n8n direct access by default; allow only approved proxy/admin source ranges if needed.

Before enforcement, OPN-175 still needs an approved firewall rules readout and confirmed OpenClaw runtime source IP.
```

- [ ] **Step 2: Verify report content**

Run:

```bash
rg -n "OPN-196|OPN-198|OPN-197|TCP `8096`|TCP `8080`|TCP `6789`|TCP `5678`|OPN-175" diagnostics/build-lanes/2026-06-28-opn-196-198-197-exposure-decisions.md
```

Expected: matches for all three issue identifiers, all four audited ports, and OPN-175 enforcement notes.

### Task 2: Update Linear Comments

**Files:**
- No file changes.

- [ ] **Step 1: Comment on OPN-196**

Post a Linear comment on OPN-196 summarizing:

```markdown
Report-only decision documented in `diagnostics/build-lanes/2026-06-28-opn-196-198-197-exposure-decisions.md`.

Decision: keep Jellyfin usable for human media clients, but direct TCP `8096` is not an OpenClaw integration path. OpenClaw should use only the gateway on TCP `8088`.

OPN-175 should later enforce TCP `8096` as LAN/trusted-client only if direct Jellyfin remains approved, deny it from OpenClaw and unapproved sources, and keep TCP `8088` restricted to the OpenClaw runtime IP.

No live firewall, Docker/Compose, container restart, reverse-proxy, or secret/env action was performed.
```

- [ ] **Step 2: Comment on OPN-198**

Post a Linear comment on OPN-198 summarizing:

```markdown
Report-only decision documented in `diagnostics/build-lanes/2026-06-28-opn-196-198-197-exposure-decisions.md`.

Using OPN-190 evidence: gluetun TCP `8080` is qBittorrent UI, and gluetun TCP `6789` is NZBGet UI. Both are downloader admin surfaces and should not be reachable from OpenClaw.

OPN-175 should later deny TCP `8080` and TCP `6789` by default, with explicit allows only for approved admin source ranges if direct UI access remains necessary.

No live firewall, Docker/Compose, container restart, reverse-proxy, or secret/env action was performed.
```

- [ ] **Step 3: Comment on OPN-197**

Post a Linear comment on OPN-197 summarizing:

```markdown
Report-only decision documented in `diagnostics/build-lanes/2026-06-28-opn-196-198-197-exposure-decisions.md`.

Using OPN-190 evidence: n8n is directly host-published on TCP `5678`; no Docker socket mount, broad host mount, privileged mode, or shared IPC was observed in the approved targeted metadata.

Decision: direct TCP `5678` remains an automation admin surface and should not be broadly exposed. Prefer NPM + Authentik or trusted admin/VPN-only access.

OPN-175 should later deny TCP `5678` by default, with explicit allows only for approved proxy/admin source ranges if needed. Keep Docker socket and broad host mounts prohibited unless separately reviewed.

No live firewall, Docker/Compose, container restart, reverse-proxy, or secret/env action was performed.
```

### Task 3: Verification

**Files:**
- Check: `diagnostics/build-lanes/2026-06-28-opn-196-198-197-exposure-decisions.md`

- [ ] **Step 1: Verify no forbidden live mutation commands were used**

Review shell history for this task in the transcript. Expected: no `docker compose up/down/pull`, no container restart, no firewall mutation, no reverse-proxy mutation, no secret/env reads.

- [ ] **Step 2: Run markdown/file checks**

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; changed files are limited to the new exposure decision doc and this plan, plus pre-existing unrelated worktree changes.

- [ ] **Step 3: Move Linear issues to Done**

After the report exists and comments are posted, move OPN-196, OPN-198, and OPN-197 to Done.
