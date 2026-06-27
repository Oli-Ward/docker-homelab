# AGENTS.md

This repository manages a homelab Docker Compose setup for a media server and supporting infrastructure. Use the managed skills and project instructions available in this workspace.

## Repo Purpose

This is a simple Docker Compose configuration repository. Stacks are grouped by purpose:

- `apps/` for user-facing apps and media services
- `infra/` for DNS, proxy, networking, and platform plumbing
- `identity/` for authentication services
- `platform/` for deployment and orchestration tooling

The README explains the service catalog and architecture. This file explains how agents should safely modify, validate, and reason about the repo.

## Operating Rules

- Komodo is the source of truth for deploying, restarting, updating, and stopping stacks.
- Do not run `docker compose up`, `docker compose down`, `docker compose pull`, or restart containers directly unless explicitly asked.
- Compose changes should be made in this repo, then reviewed with the expectation that Komodo will deploy them.
- Do not commit `.env` files, secrets, certificates, private keys, runtime state, database files, logs, or session history.
- Keep changes small and per-stack.
- Preserve the simple Docker Compose repository style.

## Source Of Truth

- Treat this repo as the intended source configuration for the homelab.
- Treat Komodo and live Docker state as useful diagnostic evidence, not the first place to make changes.
- When diagnosing issues, compare repo config against live state before proposing fixes.
- If live state differs from the repo, call out the drift clearly instead of silently normalizing it.
- Do not make UI-only or live-only changes unless explicitly asked; prefer durable repo changes.

## Live Docker Access

- Agents may use read-only Docker inspection commands for diagnosis, including:
  - `docker ps`
  - `docker logs <container>`
  - `docker inspect <container>`
  - `docker network inspect <network>`
- Do not mutate live Docker state unless explicitly asked.
- Do not start, stop, restart, recreate, remove, prune, pull, build, or update containers, images, volumes, or networks without permission.
- Prefer Komodo for deployment actions.

## Architecture Assumptions

- External access flows through DNS, Nginx Proxy Manager, then Authentik where required.
- Internal service-to-service traffic should use Docker service names.
- User data lives under `${DATA_ROOT}`.
- Media paths follow `${DATA_ROOT}/media/...`.
- Downloads live under `${DATA_ROOT}/downloads`.
- Mutable container app state lives under `${APPDATA_ROOT}/<service>`.
- Homepage is the deliberate exception: selected safe Homepage config is repo-managed under `apps/utilities/homepage`.
- Do not invent new Docker networks unless there is a clear reason.
- Treat existing external networks as pre-created.

## Adding New Services

- Ask before adding any new service or stack.
- Fit new services into the existing directory structure by purpose.
- New services should be designed end-to-end, including:
  - Komodo management and deployment
  - Nginx Proxy Manager routing if externally exposed
  - Authentik proxy auth or OIDC where appropriate
  - AdGuard DNS entry for `*.home.lab` access
  - Homepage dashboard entry where user-facing
  - Glances or monitoring visibility where relevant
  - correct Docker networks
  - mutable app state under `${APPDATA_ROOT}/<service>`
  - documented variables in an `example.env` or matching example env file
- Do not add a standalone compose stack when the service clearly belongs in an existing stack.
- Do not expose a service directly just because it has a port; route through the established proxy/auth pattern unless explicitly told otherwise.

## Storage And Volumes

- Treat storage, bind mounts, and volume changes as high-risk.
- Mutable app state should normally use `${APPDATA_ROOT}/<service>`.
- Media should normally use `${DATA_ROOT}/media/...`.
- Downloads should normally use `${DATA_ROOT}/downloads`.
- Agents may add new mounts following existing conventions, but must ask before changing existing paths.
- Do not rename, move, delete, or remap existing config, media, or download paths unless explicitly instructed.
- Be especially careful with changes that could make existing app state or media libraries appear missing inside a container.

## Environment And Secrets

- Real `.env` files are gitignored and must not be committed.
- Do not print, copy, normalize, or infer real secret values.
- Do not read secret files unless explicitly needed for diagnosis.
- When adding or changing required environment variables, update the matching `example.env` or `compose.example.env`.
- Example env files should include every required variable with safe placeholder values.
- Prefer clear placeholder names such as `change-me`, `example-token`, or `your-domain-here`.
- Never commit API keys, passwords, tokens, private keys, cookies, session files, database dumps, or runtime state.

## Authentication And TLS

- Apps without strong native auth should not be exposed directly.
- Prefer Authentik proxy auth for apps like Sonarr and Radarr.
- Prefer OIDC where the app supports it.
- Be careful changing callback URLs, issuer URLs, trusted proxy settings, or outpost configuration.
- Internal `*.home.lab` TLS uses the homelab CA.
- Services that call internal HTTPS endpoints may need the CA cert mounted.
- Do not commit private keys or generated certificate material.

## External UI Configuration

Some required homelab configuration may live outside this repo, especially in Komodo, Nginx Proxy Manager, Authentik, AdGuard, and app admin UIs.

- Treat external UI changes as required deployment checklist items.
- Do not claim a service is fully deployed from repo edits alone.
- When adding or changing an exposed service, call out remaining manual or UI work, such as:
  - Komodo stack deployment or redeploy
  - Nginx Proxy Manager proxy host
  - AdGuard DNS rewrite or record
  - Authentik application, provider, group, policy, or outpost config
  - Homepage dashboard entry
  - in-app settings such as webhook URLs, OIDC callback URLs, API keys, or download client links
- Prefer documenting the expected external changes rather than assuming they have been made.

## Image Versioning

- Many services intentionally use floating tags such as `latest`.
- Do not convert tags to pinned versions as unrelated cleanup.
- When changing a service, flag risky floating tags if stability matters.
- Prefer pinning for fragile infrastructure or stateful services such as Authentik, databases, VPN routing, and custom OIDC images.
- Avoid surprise image upgrades as part of unrelated edits.

## Validation

- Validate compose changes before handing work back.
- Prefer non-deploying checks such as:
  - `docker compose config`
  - YAML parsing or linting if available
  - reviewing changed env variable references against example env files
- Do not run commands that deploy, recreate, restart, pull images, remove resources, or mutate live Docker state unless explicitly asked.
- If validation requires real `.env` values that are not available, state that clearly and validate as much as possible with example env files.

## Backups And Risk

- Before stateful or storage-affecting changes, remind the user to confirm backups or checkpoints exist.
- This applies especially to:
  - Authentik and PostgreSQL
  - Komodo and MongoDB
  - app state directories under `${APPDATA_ROOT}`
  - media and download path mappings
  - Nginx Proxy Manager config
  - AdGuard DNS config
- Do not perform backup, restore, migration, or destructive cleanup actions unless explicitly asked.

## Tooling And Complexity

- Do not add Makefiles, CI, pre-commit hooks, Renovate, custom scripts, or schema tooling unless explicitly asked.
- It is okay to suggest tooling when it would solve a recurring problem, but do not introduce it as incidental cleanup.
- Prefer readable compose files and clear example env files over additional abstraction.

## Documentation Boundaries

- `README.md` explains what the homelab contains and how the architecture fits together.
- `AGENTS.md` explains how agents should safely modify, validate, and reason about the repo.
- Avoid duplicating the full service catalog in `AGENTS.md`.
- If a change affects user-facing architecture or service inventory, update `README.md`.
- If a change affects agent workflow, safety rules, or repo conventions, update `AGENTS.md`.

## Unrelated Issues

- If agents notice unrelated issues, flag them clearly instead of silently fixing them.
- Do not bundle unrelated cleanup into service changes.
- Only fix unrelated issues when explicitly asked, or when the issue is directly in scope for the requested change.
- If an unrelated issue looks dangerous, mention the risk and exact file/location.
