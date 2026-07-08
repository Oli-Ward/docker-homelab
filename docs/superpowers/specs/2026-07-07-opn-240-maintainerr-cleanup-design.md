# OPN-240 Maintainerr Cleanup Design

## Goal

Use Maintainerr as the watched-media cleanup system for Jellyfin, Sonarr, Radarr, and Jellyseerr instead of building custom deletion logic in OpenClaw or the gateway.

## Chosen Approach

Maintainerr is the source of truth for cleanup rules, candidate collections, grace periods, deletion handling, and deletion history. The Docker repository only deploys Maintainerr and documents the required UI configuration. Live deletion policy remains in Maintainerr app state because it includes service tokens, rule definitions, candidate review state, and destructive action settings that should not be committed.

Maintainerr is added to `apps/arr-stack` because it operates directly alongside Radarr, Sonarr, Bazarr, Prowlarr, and the media-management plane. It uses `ghcr.io/maintainerr/maintainerr:latest`, persists state at `${APPDATA_ROOT}/maintainerr:/opt/data`, runs as `${PUID}:${PGID}`, and joins both `media_net` and `proxy_net`.

## Exposure And Authentication

Maintainerr has a web UI, so it must follow the homelab external UI pattern:

- Komodo deploys the updated arr stack.
- Nginx Proxy Manager exposes `https://maintainerr.home.lab` to upstream `http://maintainerr:6246`.
- Authentik protects the app with proxy auth, unless Maintainerr later gains a stronger native OIDC setup suitable for this stack.
- AdGuard provides the `maintainerr.home.lab` DNS entry or rewrite.
- Homepage links to `https://maintainerr.home.lab`.

Repo edits alone do not fully deploy Maintainerr. The external UI configuration is a required deployment checklist.

## Cleanup Policy

Initial cleanup is conservative:

- Movies: Maintainerr should collect watched movies, hold them for a configurable grace period, then delete through Maintainerr's Radarr/Jellyfin-aware handling. Radarr handling must prevent the deleted movie from being automatically downloaded again.
- TV: cleanup is season-level for the first version. Maintainerr should collect seasons only when the relevant watched-state rule qualifies the season, hold the season for a grace period, then handle Sonarr monitoring so deleted episodes are not immediately re-grabbed.
- Candidate review: destructive handling stays disabled until the generated collections prove that the rules select the expected media.
- Exclusions: favorites, pinned/manual keep items, protected collections, and protected paths must be excluded in Maintainerr before destructive handling is enabled.
- Observability: Maintainerr's collections, history, and logs are the first place to review why a title qualified and what action was performed.

## Manual Recovery

Recovery is manual and service-specific:

- Remove or adjust the matching Maintainerr rule or exclusion if it selected the wrong item.
- Re-monitor the movie or show in Radarr/Sonarr only when it should become eligible for download again.
- Re-request the title in Jellyseerr when appropriate.
- Restore deleted media from backup if the original file is needed and no re-download should occur.

## Out Of Scope

- No custom OpenClaw deletion workflow.
- No new gateway write endpoints for Radarr, Sonarr, or Jellyfin.
- No direct filesystem deletion scripts.
- No live Docker, Komodo, NPM, Authentik, AdGuard, or Maintainerr UI mutations from this repo change.

