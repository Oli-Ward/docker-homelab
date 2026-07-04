# OPN-227 Trakt Replacement Investigation

Date: 2026-07-04

## Recommendation

Use Ryot as the Trakt replacement.

Ryot is the best fit because it is self-hosted, supports movies and TV, uses TMDb-centered media metadata, supports IMDb watchlist import, can receive Jellyfin play tracking events, and exposes an API surface through its GraphQL backend. OpenClaw should treat Ryot as the canonical media tracking service for watched/watchlist/rating-style state, while continuing to use the existing OpenClaw media gateway for safe Jellyfin/Jellyseerr/Radarr/Sonarr access.

Simkl remains the fallback if the operator later decides not to host another stateful app.

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
