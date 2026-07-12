# OPN-227 Trakt Replacement Investigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decide the free Trakt replacement path for OpenClaw media import, tracking, and recommendation workflows, favoring an option with an API or self-hosting.

**Architecture:** This is a report-only investigation. The output is a durable diagnostic note under `diagnostics/build-lanes/`, plus Linear updates to `OPN-227` and the dependent hookup ticket `OPN-228`.

**Tech Stack:** Linear, Markdown, OpenClaw Gateway repo docs, TMDb API, IMDb CSV export, Simkl API, Ryot, Letterboxd, Jellyfin/Jellyseerr.

---

### Task 1: Gather Current Evidence

**Files:**
- Read: `apps/openclaw-gateway/README.md`
- Read: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/media.py`
- Read: Linear `OPN-227`
- Read: Linear `OPN-228`

- [ ] **Step 1: Confirm issue scope**

Use Linear to read `OPN-227` and confirm the investigation must cover:

```text
Free IMDb import support
Free API access
Movies and TV coverage
IMDb, TMDb, and TVDb ID mapping
Watched, watchlist, ratings, and recommendations
Export/data portability
Rate limits and auth model
Self-hosted option if practical
Fit with Jellyfin/Jellyseerr/Radarr/Sonarr/TMDb
```

- [ ] **Step 2: Confirm current gateway shape**

Run:

```bash
sed -n '1,260p' apps/openclaw-gateway/README.md
sed -n '1,220p' apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/media.py
```

Expected: the gateway already uses TMDb IDs for Jellyseerr requests, reads Jellyfin inventory, forwards completed movie events, and keeps upstream media-service API keys off OpenClaw.

### Task 2: Compare Candidate Paths

**Files:**
- Create: `diagnostics/build-lanes/2026-07-04-opn-227-trakt-replacement.md`

- [ ] **Step 1: Write the investigation report**

Create `diagnostics/build-lanes/2026-07-04-opn-227-trakt-replacement.md` with:

```markdown
# OPN-227 Trakt Replacement Investigation

Date: 2026-07-04

## Recommendation

Use Ryot as the Trakt replacement.

Ryot is the best fit because it is self-hosted, supports movies and TV, uses TMDb-centered media metadata, supports IMDb watchlist import, can receive Jellyfin play tracking events, and exposes an API surface through its GraphQL backend.

## Why

OpenClaw needs something with a real API or self-hosted control, not just a local import table. Ryot gives the homelab a dedicated self-hosted tracker that can own media state and still fit the existing OpenClaw boundary.

The selected path avoids recurring Trakt import/API costs:

```text
IMDb watchlist export -> Ryot IMDb import
Jellyfin play tracking -> Ryot integration/webhook
OpenClaw -> Ryot API for tracked media state
OpenClaw -> existing media gateway for Jellyfin/Jellyseerr/Radarr/Sonarr actions
TMDb IDs -> shared media identity with Jellyseerr/Radarr and OpenClaw workflows
```

## Compared Options

| Option | IMDb import | Free API/write fit | Movies + TV | ID mapping | Portability | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| Ryot self-hosted | IMDb watchlist import exists; Jellyfin tracking exists | Self-hosted GraphQL/API surface exists, no third-party recurring API cost | Yes | TMDb-centered media model | Good, but requires Ryot backup/export discipline | Recommended |
| Simkl | Yes, documented IMDb CSV import for TV and movies | Likely viable for personal/non-commercial use, with OAuth and rate limits | Yes | Strong external IDs, including IMDb/TMDb/TVDb | SaaS export/import dependency remains | Good fallback, not canonical |
| OpenClaw local state + TMDb | Yes, via IMDb CSV export parsed locally | Yes for metadata lookup; local writes cost nothing | Yes | IMDb -> TMDb via TMDb `/find`; TVDb available where TMDb exposes it | Best raw portability, but no dedicated tracker UI/API product | Reject per operator preference for an API/self-hosted tracker |
| Letterboxd | IMDb CSV import exists | API access is request-only and not granted for private/personal/LLM/recommendation style use cases | Films first; TV is not a reliable current fit | IMDb/TMDb import matching for films | Good user export/import, poor automation fit | Reject for OpenClaw automation |
| Movary | Imports/exports and Jellyfin scrobbling exist | Self-hosted, but movie-only focus is too narrow | Movies only | TMDb/IMDb metadata | Good for movie diary | Reject as Trakt replacement |
| IMDb API directly | User CSV export is useful | Official API requires AWS Data Exchange subscription flow and is metadata-oriented, not user list/write automation | Metadata product covers movies/TV | IMDb native | Not a free tracker API | Reject |

## Selected Import Path

Use Ryot's IMDb import path rather than IMDb's commercial API:

1. Export IMDb watchlist CSV.
2. Import the file into Ryot using its IMDb import support.
3. Configure Ryot's Jellyfin integration so future watched state can be captured from Jellyfin playback.
4. Use Ryot's API for OpenClaw read/write media tracking workflows.
5. Keep unmatched/import-problem records visible in the Ryot/OpenClaw hookup work rather than silently dropping them.

## API/Auth Model

OpenClaw should use:

- Ryot API access for tracked media state.
- TMDb API key/read token where OpenClaw still needs metadata lookup, ID resolution, details, and recommendation enrichment outside Ryot.
- Existing media gateway token for Jellyfin inventory, Jellyfin watch-completed events, and Jellyseerr requests.

OpenClaw should not receive:

- Raw Jellyfin, Jellyseerr, Sonarr, or Radarr API keys.
- IMDb AWS/Data Exchange credentials.
- Simkl OAuth tokens unless a later ticket explicitly selects Simkl sync as an optional external mirror.

## Data Model Implications

Ryot becomes the canonical tracker for media watched/watchlist/rating-style state. OpenClaw can still cache or mirror selected state locally for recommendation queries, but the integration should be built around Ryot rather than inventing a parallel tracker first.

Minimum OpenClaw-side concepts or cached records:

```text
tracked_media_items
- id
- media_type
- title
- year
- imdb_id
- tmdb_id
- tvdb_id
- ryot_id

tracked_media_state
- tracked_media_item_id
- state
- rating_10
- watched_at
- source = "ryot"
- updated_at

media_sync_runs
- id
- source = "ryot"
- synced_at
- row_count
- error_count
```

The important behavior is idempotent sync: repeated Ryot reads should update existing OpenClaw cache rows without overwriting separate OpenClaw-only recommendation annotations such as notes, rejected flags, and do-not-recommend state.

## Risks And Limits

- Ryot adds another stateful service. It needs a Compose stack, Komodo deployment, backup coverage, restore verification, and Homepage/monitoring entries if adopted.
- Ryot API details need to be verified during OPN-228 against the deployed version before building broad OpenClaw automation on top of it.
- IMDb CSV export is manual unless a separate browser/session automation is approved. Do not scrape IMDb credentials or session cookies.
- IMDb ratings/watchlist CSV coverage may not perfectly represent episode-level TV history. Store unknown/unmatched rows explicitly.
- Simkl has a strong API and import story, but it introduces another SaaS dependency, attribution requirements, OAuth tokens, and rate limits.
- Letterboxd is unsuitable for OpenClaw automation because API access is not generally available for private/personal/recommendation projects.

## OPN-228 Hookup Direction

Implement OPN-228 as:

1. Add Ryot to the homelab as a new self-hosted stateful service, after explicit service-add approval.
2. Include Komodo deployment, appdata path, example env, backup/restore notes, Homepage entry, and proxy/auth decision.
3. Import IMDb watchlist data into Ryot.
4. Configure Ryot's Jellyfin integration for watched-state capture.
5. Add an OpenClaw Ryot connector that can read tracked media state and perform the minimum approved writes.
6. Keep the existing OpenClaw media gateway as the boundary for Jellyfin/Jellyseerr/Radarr/Sonarr actions.
7. Keep Simkl as the fallback if Ryot's API or operational footprint is not acceptable after a deployment spike.

Do not implement Simkl, Letterboxd, or Movary as the first canonical replacement.

## Sources Checked

- TMDb API getting started: https://developer.themoviedb.org/reference/intro/getting-started
- TMDb finding data guide: https://developer.themoviedb.org/docs/finding-data
- TMDb `/find` endpoint: https://developer.themoviedb.org/reference/find-by-id
- TMDb account watchlist endpoint: https://developer.themoviedb.org/reference/account-add-to-watchlist
- Simkl API docs: https://api.simkl.com/
- Simkl API rules: https://api.simkl.org/api-rules
- Simkl IMDb import: https://simkl.com/apps/import/imdb/
- Ryot README: https://github.com/ignisda/ryot
- Ryot IMDb import docs: https://docs.ryot.io/importing/imdb
- Ryot Jellyfin sink docs: https://docs.ryot.io/integrations/jellyfin-sink
- Letterboxd API access: https://letterboxd.com/api-beta/
- Letterboxd importing data: https://letterboxd.com/about/importing-data/
- Movary README: https://github.com/leepeuker/movary
- IMDb API access docs: https://developer.imdb.com/documentation/api-documentation/getting-access/

## Verification

This was a research-only ticket. No Docker, Komodo, NPM, Authentik, or live container state was changed.
```

- [ ] **Step 2: Check for accidental secrets**

Run:

```bash
rg -n "token|secret|password|api[_-]?key|cookie|authorization|privkey|BEGIN " diagnostics/build-lanes/2026-07-04-opn-227-trakt-replacement.md docs/superpowers/plans/2026-07-04-opn-227-trakt-replacement-investigation.md
```

Expected: no secret values. Generic words like `API key` or `OAuth tokens` are acceptable if they do not include values.

### Task 3: Update Linear

**Files:**
- Update: Linear `OPN-227`
- Update: Linear `OPN-228`

- [ ] **Step 1: Update OPN-228 with implementation direction**

Add a comment to `OPN-228`:

```markdown
OPN-227 recommendation: implement the Trakt replacement with Ryot as the self-hosted canonical media tracker.

Implementation shape:

- Add Ryot to the homelab as a new stateful service after explicit service-add approval.
- Include Komodo deployment, appdata path, example env, backup/restore notes, Homepage entry, and proxy/auth decision.
- Import IMDb watchlist data into Ryot.
- Configure Ryot's Jellyfin integration for watched-state capture.
- Add an OpenClaw Ryot connector for tracked media state and minimum approved writes.
- Existing media gateway remains the path for Jellyfin/Jellyseerr/Radarr/Sonarr actions.
- Simkl is the fallback if Ryot's API or operational footprint is not acceptable after a deployment spike.

See `diagnostics/build-lanes/2026-07-04-opn-227-trakt-replacement.md`.
```

- [ ] **Step 2: Close OPN-227**

Add a final comment to `OPN-227` with outcome, verification, and follow-ups, then move it to `Done`.
