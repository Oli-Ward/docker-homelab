# Homepage Config And Appdata Refactor

## Context

The Docker Compose repo currently treats `${DATA_ROOT}` as both user data storage and container app-state storage. Most stacks mount mutable state from `${DATA_ROOT}/configs/<service>`, while media and downloads also live under `${DATA_ROOT}`.

That made sense when `/data` was the broad shared storage root. The intended domain is now narrower: `/data` should describe media, downloads, photos, and similar user data. Mutable internal container state should move elsewhere.

Homepage is the immediate pain point because its config is edited by hand and benefits from Git diffs. Most other service config directories are poor candidates for Git because they contain databases, generated state, sessions, caches, cookies, API keys, logs, or cert material.

## Decisions

- Stage the work instead of doing one large migration.
- Move only selected Homepage configuration under repo control first.
- Replace literal Homepage widget API keys with `HOMEPAGE_VAR_*` environment references before committing Homepage YAML.
- Keep real secrets in the untracked utilities `.env` file.
- Track Homepage config by whitelist, not by committing the whole config directory.
- Later introduce a dedicated mutable app-state root, recommended as `APPDATA_ROOT`.
- Keep media, downloads, and photos under `DATA_ROOT`.
- Do not move live data, redeploy stacks, or restart containers directly as part of repo-only planning.

## Ticket 1: Move Homepage Config Under Repo Control With Env-Based Secrets

### What To Build

Move the safe, human-authored Homepage configuration into the Docker config repo and make it the source of truth for the Homepage container. Replace literal Homepage widget API keys with environment-variable references so only placeholders are committed.

The live Homepage config should be bind-mounted from the repo into the Homepage container. Only selected safe files should be tracked in Git; generated files, secrets, caches, logs, and unknown files should remain ignored.

### Acceptance Criteria

- [ ] Homepage YAML/config files needed for the dashboard live in the repo under the utilities stack.
- [ ] Literal API keys are removed from committed Homepage config and replaced with `HOMEPAGE_VAR_*` references.
- [ ] `apps/utilities/example.env` documents every required Homepage secret variable with safe placeholder values.
- [ ] The real `apps/utilities/.env` remains untracked.
- [ ] `.gitignore` tracks only approved Homepage config files and ignores everything else in that config folder.
- [ ] `apps/utilities/compose.yml` mounts the repo-managed Homepage config into `/app/config`.
- [ ] `docker compose config` validation succeeds for the utilities stack using safe placeholder env values.
- [ ] Any required Komodo redeploy/manual checklist is documented in the handoff.

### Blocked By

None - can start immediately.

## Ticket 2: Move Mutable Container App State Out Of `/data/configs`

### What To Build

Introduce a dedicated mutable app-state root, recommended as `APPDATA_ROOT`, and migrate non-Homepage container state mounts away from `${DATA_ROOT}/configs/<service>` to `${APPDATA_ROOT}/<service>`.

This is a repo/config migration only. Do not move live data, restart containers, or redeploy stacks directly unless explicitly approved. The output should include exact migration commands/checklist for the operator or Komodo-managed deployment process.

### Acceptance Criteria

- [ ] Compose files use `${APPDATA_ROOT}/<service>` for mutable app state instead of `${DATA_ROOT}/configs/<service>`, except where a deliberate exception is documented.
- [ ] Media, downloads, and photo mounts continue to use `${DATA_ROOT}`.
- [ ] Example env files document `APPDATA_ROOT` with a safe example value.
- [ ] README and agent/project docs are updated so `/data` and `APPDATA_ROOT` have distinct meanings.
- [ ] High-risk services are called out before migration, especially Authentik, Nginx Proxy Manager, AdGuard, Jellyfin, Arr apps, download clients, n8n, and Speedtest Tracker.
- [ ] A stack-by-stack migration checklist is provided, including backup/checkpoint reminder, copy/sync command shape, ownership/permission checks, compose validation, Komodo redeploy, and rollback path.
- [ ] Non-deploying compose validation succeeds as far as possible with placeholder env values.
- [ ] No secrets, runtime databases, cert private keys, logs, or `.env` files are committed.

### Blocked By

Recommended: Ticket 1, so the Homepage repo-control exception pattern is established first.

## Implementation Notes

Recommended root naming:

```env
DATA_ROOT=/data
APPDATA_ROOT=/srv/appdata
```

Recommended Homepage policy:

- Commit structure, labels, URLs, icons, layouts, and environment-variable references.
- Do not commit literal API keys, tokens, usernames/passwords, cookies, generated assets, logs, or caches.
- Prefer `HOMEPAGE_VAR_*` variables for Homepage widget secrets.

Recommended Homepage ignore posture:

```gitignore
apps/utilities/homepage/*
!apps/utilities/homepage/*.yaml
!apps/utilities/homepage/custom.css
!apps/utilities/homepage/custom.js
```

Only include `custom.css` or `custom.js` if they are actually used and contain no secrets.
