# OPN-237 Ryot Service-Add Runbook

Date: 2026-07-05

## Approval Log

- Pre-change inventory approval: APPROVED by Oli in chat at 2026-07-05 11:23:04 NZST.
- Approved scope: read-only Docker/Komodo/media appdata/proxy/Auth/DNS/Homepage/Jellyfin/gateway/n8n inventory sufficient to confirm current stack names, networks, routes, auth pattern, storage paths, backup coverage, and integration prerequisites.
- Exclusions: no deploy/redeploy/restart/pull/build/remove, no appdata creation, no Compose/env edits, no NPM/Auth/DNS/Homepage mutation, no Jellyfin plugin changes, no n8n/gateway runtime changes, no secret reads, no destructive cleanup.
- Deployment preparation approval: APPROVED by Oli in chat at 2026-07-05 19:57:18 NZST.
- Approved scope: confirm backups/checkpoints, create/check Ryot appdata path as needed, place real Ryot secret values only in the approved untracked env/secret store, and prepare Komodo media stack deployment inputs.
- Exclusions: no actual deploy/redeploy/restart/pull/build/remove actions, no proxy/Auth/DNS/Homepage mutations, no Jellyfin plugin changes, no n8n/gateway runtime changes, and no printing/copying secret values.
- Live resume approval: APPROVED by Oli in chat at 2026-07-06.
- Approved scope: read-only live verification of Ryot/media/Auth/NPM/Homepage state, and if needed appdata path confirmation/prep plus Komodo-managed deployment/route verification.
- Exclusions: no printing or storing secret values, no direct `docker compose up/down/pull/restart`, no destructive cleanup or deletion of Ryot database/appdata state, and no broad unrelated proxy/Auth/DNS/Homepage/n8n/OpenClaw/Jellyfin changes.

## Pre-Change Inventory Commands

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
docker network inspect media_net
docker network inspect proxy_net
docker inspect jellyfin jellyseerr nginx-proxy-manager authentik-server
docker logs --tail 120 nginx-proxy-manager
docker logs --tail 120 authentik-server
```

Additional repo-only and redacted live read-only checks may be used if needed:

```bash
rg -n "Ryot|ryot|Jellyfin|jellyfin|Jellyseerr|jellyseerr|Authentik|authentik|request.home.lab|home.lab|n8n|openclaw|backup|APPDATA_ROOT|DATA_ROOT" README.md apps diagnostics docs infra identity platform
docker exec nginx-proxy-manager sh -lc "find /data/nginx/proxy_host -maxdepth 1 -type f -name '*.conf' -print 2>/dev/null"
docker exec nginx-proxy-manager sh -lc "grep -R \"server_name .*home.lab\\|auth_request\\|outpost.goauthentik\\|jellyfin\\|jellyseerr\\|n8n\\|openclaw\\|ryot\" -n /data/nginx/proxy_host 2>/dev/null"
```

## Findings

Inventory run at 2026-07-05 11:23-11:25 NZST. Commands were read-only. No secret values, raw env files, database contents, or runtime state files were read or recorded.

### Live Container State

`docker ps` showed only these relevant services running:

- `nginx-proxy-manager`
- `n8n`
- `openclaw-gateway`
- `openclaw-tunnel`
- `komodo-core-1`
- `komodo-periphery-1`
- `adguard`
- `homepage`
- `komodo-mongo-1`

`docker ps -a` showed the media and Authentik services exist but are currently stopped:

- `jellyfin`: `Exited (0) About an hour ago`
- `jellyseerr`: `Exited (143) About an hour ago`
- `sonarr`, `radarr`, `prowlarr`, `bazarr`: `Exited (0) About an hour ago`
- `qbittorrent`, `nzbget`, `gluetun`, `cleanuparr`, `autoscan`, `flaresolverr`: stopped
- `authentik-server`: `Exited (0) About an hour ago`
- `authentik-worker-1`: `Exited (1) About an hour ago`
- `authentik-postgresql-1`: `Exited (0) About an hour ago`

This is important drift from normal expected service availability: the repo contains `apps/media/compose.yml` entries for `jellyfin` and `jellyseerr`, and live containers exist, but they are not running.

### Networks

`media_net` exists as a bridge network on `172.21.0.0/16`.

Current attached services:

- `openclaw-gateway`

`proxy_net` exists as a bridge network on `172.20.0.0/16`.

Current attached services:

- `nginx-proxy-manager`
- `n8n`
- `openclaw-tunnel`
- `komodo-core-1`
- `adguard`
- `homepage`
- `glances`
- `speedtest-tracker`

Because the stopped media/Auth containers are not attached to runtime DNS, NPM cannot currently resolve `jellyfin`, `jellyseerr`, or `authentik-server`.

### Targeted Container Metadata

Targeted `docker inspect --format` avoided environment dumps.

- `jellyfin`
  - Image: `lscr.io/linuxserver/jellyfin:latest`
  - Status: exited
  - Networks in config: `media_net`, `proxy_net`
  - Mounts: `/srv/appdata/jellyfin`, `/data/media/movies`, `/data/media/tv`, homelab CA cert
- `jellyseerr`
  - Image: `fallenbagel/jellyseerr:preview-OIDC`
  - Status: exited
  - Networks in config: `media_net`, `proxy_net`
  - Mounts: `/srv/appdata/jellyseerr`, homelab CA cert
- `nginx-proxy-manager`
  - Image: `jc21/nginx-proxy-manager:latest`
  - Status: running
  - Networks: `internal_net`, `proxy_net`
  - Host ports: `80`, `81`, `443`
  - Mounts: `/srv/appdata/nginx-proxy-manager/data`, `/srv/appdata/nginx-proxy-manager/letsencrypt`
- `authentik-server`
  - Image: `ghcr.io/goauthentik/server:2026.2.2`
  - Status: exited
  - Networks in config: `authentik_auth_net`, `proxy_net`
  - Mounts: repo-managed Authentik data/templates paths under `identity/authentik`
- `n8n`
  - Image: `docker.n8n.io/n8nio/n8n:latest`
  - Status: running
  - Networks: `proxy_net`, `utilities_net`
  - Mounts: `/srv/appdata/n8n`, read-only scripts, read-only OpenClaw SSH tunnel key path
- `openclaw-gateway`
  - Image: `openclaw-gateway-openclaw-gateway`
  - Status: running
  - Networks: `media_net`, `utilities_net`
  - Host bind: `192.168.1.103:8088->8080/tcp`
- `komodo-core-1`
  - Image: `ghcr.io/moghtech/komodo-core:2`
  - Status: running
  - Networks: `internal_net`, `komodo_net`, `proxy_net`
  - Host port: `9120`
  - Mounts: Komodo keys volume and `/etc/komodo/backups`
- `komodo-periphery-1`
  - Image: `ghcr.io/moghtech/komodo-periphery:2`
  - Status: running
  - Networks: `komodo_net`
  - Mounts include Docker socket, `/proc`, and `/home/oli/docker`
- `adguard`
  - Image: `adguard/adguardhome:latest`
  - Status: running
  - Networks: `proxy_net`
  - Host ports include DNS `53` and admin/UI ports
  - Mounts: `/srv/appdata/adguard/conf`, `/srv/appdata/adguard/work`
- `homepage`
  - Image: `ghcr.io/gethomepage/homepage:latest`
  - Status: running and healthy
  - Networks: `proxy_net`, `utilities_net`
  - Mounts repo-managed Homepage config from `apps/utilities/homepage`, read-only `/data`, read-only Docker socket, homelab CA cert

### Proxy/Auth/DNS State

NPM has generated proxy host files for existing `*.home.lab` routes. Relevant generated config evidence:

- `jellyfin.home.lab` exists and proxies to upstream `jellyfin`.
- `jellyseerr.home.lab` exists and proxies to upstream `jellyseerr`.
- `jellyseerr.home.lab` has Authentik `auth_request /_auth` and `outpost.goauthentik` blocks.
- `n8n.home.lab` exists and has Authentik `auth_request /_auth`.
- `openclaw.home.lab` exists and proxies to upstream `openclaw-tunnel`.
- No `ryot.home.lab` NPM proxy host was found.

NPM container DNS lookup currently resolves:

- `n8n`
- `openclaw-tunnel`

NPM container DNS lookup did not resolve these because their containers are stopped or absent from the shared runtime network:

- `authentik-server`
- `jellyfin`
- `jellyseerr`
- `openclaw-gateway`

NPM logs show repeated normal certificate renewal checks followed by an nginx configuration test failure at `2026-07-05 10:33:44`:

```text
nginx: [emerg] host not found in upstream "authentik-server" in /data/nginx/proxy_host/10.conf:70
nginx: configuration file /etc/nginx/nginx.conf test failed
```

Authentik logs show the outpost previously loaded protected applications including:

- `jellyseerr.home.lab`
- `n8n.home.lab`
- `sonarr.home.lab`
- `radarr.home.lab`
- `prowlarr.home.lab`
- `bazarr.home.lab`
- `paperless.home.lab`
- `dash.home.lab`

The Authentik server then shut down at `2026-07-04T22:09:41Z`.

AdGuard config grep shows `*.home.lab` wildcard DNS plus specific records for existing hosts. No `ryot.home.lab` record was found, but the wildcard may cover it depending on AdGuard rewrite behavior.

### Route Probes

Read-only unauthenticated `curl -I` probes returned:

- `https://jellyfin.home.lab`: `HTTP/2 502`
- `https://jellyseerr.home.lab`: `HTTP/2 500`
- `https://n8n.home.lab`: `HTTP/2 500`
- `https://openclaw.home.lab`: `HTTP/1.1 200 OK`
- `https://ryot.home.lab`: TLS SNI error, `tlsv1 unrecognized name`

Interpretation:

- Jellyfin route exists but upstream is stopped.
- Jellyseerr and n8n protected routes exist, but Authentik is stopped, so forward-auth cannot complete.
- OpenClaw route is currently reachable through `openclaw-tunnel`.
- Ryot route does not exist in NPM/TLS yet.

### Homepage

Repo-managed Homepage currently has:

- Jellyfin href: `https://jellyfin.home.lab`
- Jellyfin widget URL: `http://jellyfin:8096`
- Jellyseerr href: `https://request.home.lab`
- Jellyseerr widget URL: `http://jellyseerr:5055`
- n8n href: `https://n8n.home.lab`

This shows repo/live drift for Jellyseerr:

- Live NPM has `jellyseerr.home.lab`.
- Homepage still links to `request.home.lab`.
- Prior `OPN-224` diagnostics recorded that `request.home.lab` should not remain as a direct unauthenticated Jellyseerr path.

### Appdata And Backup

`/srv/appdata` exists but is not listable by this user:

```text
drwxr-x--- root root /srv/appdata
ls: cannot open directory '/srv/appdata': Permission denied
```

Appdata paths were confirmed indirectly from Docker mount metadata:

- `/srv/appdata/jellyfin`
- `/srv/appdata/jellyseerr`
- `/srv/appdata/n8n`
- `/srv/appdata/nginx-proxy-manager/data`
- `/srv/appdata/nginx-proxy-manager/letsencrypt`
- `/srv/appdata/adguard/conf`
- `/srv/appdata/adguard/work`

`docs/backup/media-appdata.md` covers selected existing appdata paths and stack env files. It does not yet include any future Ryot path. If Ryot is added, the backup docs/script coverage should add the selected Ryot database/app state path, expected as `${APPDATA_ROOT}/ryot-postgres` unless the implementation decision changes.

### Integration Prerequisites

- OpenClaw gateway is running and attached to `media_net`, but current media service upstreams are stopped.
- `apps/openclaw-gateway/compose.yml` defaults to internal service names:
  - `JELLYFIN_URL=http://jellyfin:8096`
  - `JELLYSEERR_URL=http://jellyseerr:5055`
  - `N8N_WEBHOOK_BASE_URL=http://n8n:5678`
- n8n is running on `proxy_net` and `utilities_net`.
- No Ryot container, appdata path, NPM route, Authentik application, DNS record, or Homepage entry currently exists.

## Decisions

- Do not proceed to Ryot repo edits or deployment until the stopped media/Auth stack state is acknowledged. A Ryot deployment can still be planned, but any route/auth verification will be unreliable while Authentik and the media stack are stopped.
- Keep the proposed Ryot placement in `apps/media`, with `ryot` on `media_net` and `proxy_net`, and `ryot-db` on `media_net` only.
- Keep the proposed route as `ryot.home.lab`; this requires a new NPM proxy host and likely no explicit AdGuard record if the wildcard is confirmed to cover it.
- Keep Authentik OIDC as the preferred auth model for Ryot after Authentik is running. Proxy auth is a fallback if OIDC setup is deferred.
- Add future Ryot backup coverage for `${APPDATA_ROOT}/ryot-postgres` before considering the service operational.
- Fix or intentionally update the existing Homepage Jellyseerr link drift separately or as a small included cleanup only if Oli approves it in the repo-edit step.

## Implementation Log

- Created this runbook and recorded the explicit pre-change inventory approval.
- Ran read-only Docker inventory: `docker ps`, `docker ps -a`, `docker network inspect media_net`, `docker network inspect proxy_net`.
- Ran targeted read-only `docker inspect --format` for relevant containers, avoiding raw env output.
- Read NPM generated proxy host config using `docker exec nginx-proxy-manager` with `find`/`grep`.
- Read NPM and Authentik log tails.
- Read AdGuard host rewrite evidence with targeted hostname grep only.
- Read route headers with unauthenticated `curl -I`.
- Read repo-managed Homepage, backup, media compose/example env, and OpenClaw gateway compose files.
- Did not run deploy/redeploy/restart/pull/build/remove commands.
- Did not create appdata directories.
- Did not edit Compose/env files.
- Did not mutate NPM/Auth/DNS/Homepage/Jellyfin/n8n/gateway/Komodo state.
- Did not read or record real secret values.

### Repo Configuration Edit Checkpoint

Approved by Oli in chat after the inventory checkpoint.

Repo-only changes made:

- Added `ryot` and `ryot-db` services to `apps/media/compose.yml`.
- Added safe Ryot placeholders to `apps/media/example.env`.
- Added Ryot to README service/domain inventory.
- Added `ryot-postgres` to the manual media appdata backup script and docs.
- Updated repo-managed Homepage Jellyseerr href from `https://request.home.lab` to `https://jellyseerr.home.lab` to match the verified live NPM host from `OPN-224`.
- Added a focused backup-script regression test for `ryot-postgres` dry-run inventory coverage.

Still not performed:

- No live deployment, redeploy, restart, pull, build, remove, or appdata creation.
- No real `.env` or secret-store edits.
- No NPM/Auth/DNS/Homepage live UI changes.
- No Jellyfin Sink, n8n, or OpenClaw runtime changes.

### Deployment Preparation Checkpoint

Approved by Oli in chat at 2026-07-05 19:57:18 NZST.

Prep-only checks completed:

- Confirmed `apps/media/.env` exists and is ignored by Git via `.gitignore`.
- Inspected only env variable names and placeholder status; no real secret values were printed or copied.
- Confirmed all variables referenced by `apps/media/compose.yml` are present in `apps/media/.env`.
- Confirmed required Ryot secret keys are present in `apps/media/.env` and do not match the known placeholder values from `apps/media/example.env`:
  - `RYOT_POSTGRES_PASSWORD`
  - `RYOT_SERVER_ADMIN_ACCESS_TOKEN`
  - `RYOT_TMDB_ACCESS_TOKEN`
  - `RYOT_OIDC_CLIENT_SECRET`
- Confirmed Ryot non-secret deployment inputs in `apps/media/.env` match the current repo decision:
  - `RYOT_FRONTEND_URL=https://ryot.home.lab`
  - `RYOT_POSTGRES_DB=ryot`
  - `RYOT_POSTGRES_USER=ryot`
  - `RYOT_DISABLE_TELEMETRY=true`
  - `RYOT_USERS_ALLOW_REGISTRATION=true`
  - `RYOT_OIDC_CLIENT_ID=ryot`
  - `RYOT_OIDC_ISSUER_URL=https://auth.home.lab/application/o/ryot/`
  - `RYOT_OIDC_BUTTON_LABEL=Continue with Authentik`
- Confirmed backup coverage documentation and script now include `${APPDATA_ROOT}/ryot-postgres`.

Blocked prep item:

- `/srv/appdata` is owned by `root:root` with `750` permissions. Checking or creating `/srv/appdata/ryot-postgres` requires interactive sudo credentials in this session:

```text
sudo: a terminal is required to read the password; either use the -S option to read from standard input or configure an askpass helper
sudo: a password is required
```

No appdata directory was created by this checkpoint.

Still not performed:

- No live deployment, redeploy, restart, pull, build, remove, or appdata creation.
- No backup artifact was created.
- No real `.env` values were printed, copied, or recorded.
- No NPM/Auth/DNS/Homepage live UI changes.
- No Jellyfin Sink, n8n, or OpenClaw runtime changes.

## Verification

- Read-only inventory completed within approved scope.
- New finding: most media/Auth containers are stopped; NPM protected routes depending on `authentik-server` are currently degraded.
- New finding: no Ryot service or route exists yet.
- New finding: Homepage still links Jellyseerr to `request.home.lab`, while live NPM has `jellyseerr.home.lab`.
- Backup regression red step: `python3 -m pytest tests/test_backup_media_appdata_script.py::test_backup_script_dry_run_lists_inventory_without_writing -q` failed before the script change because `APPDATA_ROOT/ryot-postgres` was absent from dry-run output.
- Compose validation: `docker compose --env-file apps/media/example.env -f apps/media/compose.yml config` exited 0 and rendered `ryot` plus `ryot-db`.
- Example env coverage: local Python variable check exited 0 with `All compose variables are present in apps/media/example.env`.
- Backup regression green step: `python3 -m pytest tests/test_backup_media_appdata_script.py -q` reported 3 passed, 1 warning from existing pytest-asyncio deprecation config.
- Fresh Compose validation at 2026-07-05 19:57 NZST: `docker compose --env-file apps/media/example.env -f apps/media/compose.yml config` exited 0 and rendered `ryot` plus `ryot-db`.
- Fresh backup regression at 2026-07-05 19:57 NZST: `python3 -m pytest tests/test_backup_media_appdata_script.py -q` reported 3 passed, 1 existing pytest-asyncio warning.
- Fresh whitespace validation at 2026-07-05 19:57 NZST: `git diff --check` exited 0.
- Fresh untracked env coverage check at 2026-07-05 19:57 NZST: all `apps/media/compose.yml` variables are present in `apps/media/.env`.
- Fresh secret placeholder check at 2026-07-05 19:57 NZST: required Ryot secret keys are present in `apps/media/.env` and do not match known placeholder values; real values were not printed.
- Fresh non-secret deployment input check at 2026-07-05 19:57 NZST: current Ryot non-secret env values match the repo decision.

### Live Resume Verification Checkpoint

Approved by Oli in chat on 2026-07-06.

Scope performed:

- Moved `OPN-237` back to `In Progress`.
- Refreshed live container state with `docker ps -a`.
- Checked `media_net` and `proxy_net` attachments.
- Checked targeted Docker metadata for `ryot`, `ryot-db`, `jellyfin`, `jellyseerr`, `authentik-server`, `nginx-proxy-manager`, and `homepage` without dumping environment variables.
- Checked the `ryot-db` bind mount metadata and in-container database directory ownership.
- Checked Ryot internal health from the existing `n8n` container on `proxy_net`.
- Checked Postgres readiness from inside `ryot-db`.
- Checked NPM generated proxy config and `nginx -t`.
- Checked external protected route headers for `https://ryot.home.lab/` and `https://ryot.home.lab/health`.
- Checked running Homepage config for the Ryot entry.
- Checked required Ryot secret keys in `apps/media/.env` are present, nonblank, and not equal to the safe placeholders from `apps/media/example.env`; real values were not printed.

Live state:

- `ryot` is running from `ignisda/ryot:v10`.
- `ryot-db` is running from `postgres:18-alpine`.
- `jellyfin`, `jellyseerr`, media automation services, Authentik, NPM, Homepage, AdGuard, Komodo, n8n, and OpenClaw gateway are running.
- `ryot` is attached to `media_net` and `proxy_net`.
- `ryot-db` is attached to `media_net`.
- `ryot-db` has `/srv/appdata/ryot-postgres` mounted at `/var/lib/postgresql` as a read-write bind mount.
- Inside the container, PostgreSQL data lives under `/var/lib/postgresql/18/docker`, owned by `postgres:root` with `700` permissions.
- Host-level `sudo -n stat /srv/appdata /srv/appdata/ryot-postgres` still cannot report ownership without an interactive sudo password, but the running database and bind mount confirm the path exists and is writable by the container.

Verification:

- `docker exec n8n node ... http://ryot:8000/health` returned `status=200`.
- `docker exec ryot-db ... pg_isready ...` reported `/var/run/postgresql:5432 - accepting connections`.
- `docker exec nginx-proxy-manager nginx -t` reported syntax OK and test successful.
- `curl -k -I https://ryot.home.lab/` returned `HTTP/2 302` to the Authentik outpost start URL.
- `curl -k -I https://ryot.home.lab/health` returned `HTTP/2 302` to the Authentik outpost start URL, confirming the health route is also protected externally.
- NPM generated config contains proxy host `19` for `server_name ryot.home.lab` with Authentik `auth_request` and `outpost.goauthentik` locations.
- Running Homepage config contains the Ryot entry with `href: https://ryot.home.lab` and `siteMonitor: http://ryot:8000/health`.
- `docker logs --tail 80 ryot` showed Ryot `v10.3.16`, timezone `Pacific/Auckland`, no pending migrations, frontend serving on `:8000`, backend listening on `0.0.0.0:5000`, and no secret values recorded.
- `docker logs --tail 80 ryot-db` showed initial database creation on 2026-07-05, reuse of the existing database on 2026-07-06, automatic recovery after an unclean shutdown, and readiness to accept connections.
- Required Ryot secret keys in `apps/media/.env` are present, nonblank, and not equal to example placeholders; values were not printed.

Decisions confirmed:

- Ryot is exposed through `https://ryot.home.lab` via NPM and Authentik proxy auth.
- No direct Ryot host port is required.
- Ryot stateful database storage is `${APPDATA_ROOT}/ryot-postgres`.
- Jellyfin Sink is deferred until after Ryot account/bootstrap/API decisions are made.
- n8n and OpenClaw runtime integration remains out of scope for this ticket and continues in `OPN-228`.

### Post-Completion Authentik Redirect Fix

Reported by Oli on 2026-07-06 after initial completion:

- Browser reached `https://ryot.home.lab/auth`.
- Ryot showed a minified React hydration error.
- Browser blocked a mixed-content request because the Authentik authorize redirect used `http://auth.home.lab/application/o/authorize/...` from an HTTPS Ryot page.

Root cause:

- The embedded Authentik outpost config had `authentik_host='http://auth.home.lab'`.
- Ryot's Authentik proxy provider was not the source of the bad scheme; `external_host` was already `https://ryot.home.lab`.
- NPM's `auth.home.lab` proxy route itself served HTTPS correctly, but the outpost generated browser authorization URLs from its own `authentik_host` value.

Live change:

- Updated the embedded Authentik outpost backing `_config.authentik_host` from `http://auth.home.lab` to `https://auth.home.lab` using Authentik's Django shell inside `authentik-server`.
- No secret values were printed or changed.
- No Docker Compose lifecycle commands were run.
- Authentik queued outpost update tasks after the model update.

Verification:

- Before fix: `curl -k -sS -D - -o /dev/null 'https://ryot.home.lab/outpost.goauthentik.io/start?rd=https://ryot.home.lab/manifest.json'` returned `Location: http://auth.home.lab/application/o/authorize/...`.
- After fix: the same command returned `Location: https://auth.home.lab/application/o/authorize/...`.
- Readback from Authentik Django shell confirmed `authentik_host` is `https://auth.home.lab`.

### Post-Completion Ryot OIDC CA Trust Fix

Reported by Oli on 2026-07-06 after the Authentik redirect scheme fix:

- Browser still showed a minified React hydration error on `https://ryot.home.lab/auth`.
- Browser also showed `GET https://ryot.home.lab/favicon.ico 404`.
- Ryot still did not present or complete login through Authentik.

Findings:

- The mixed-content authorize redirect was no longer present after the Authentik outpost fix.
- Ryot's `/auth` HTML rendered only the local username/password form and signup link.
- The embedded route loader data and a direct backend GraphQL query both reported `oidcEnabled=false`.
- Ryot's redacted `/backend/config` endpoint confirmed the OIDC client id, client secret, issuer URL, and button label were loaded from environment.
- From inside the running Ryot container, `https://auth.home.lab/application/o/ryot/.well-known/openid-configuration` failed normal TLS verification but succeeded with `curl -k`.
- The `favicon.ico` 404 is a benign missing route from the Ryot app and is not the OIDC blocker.

Root cause:

- The Ryot service did not trust the homelab CA used by `auth.home.lab`.
- Ryot loaded the OIDC config, but the backend could not validate the Authentik issuer over HTTPS, so `coreDetails.oidcEnabled` stayed `false`.

Repo change:

- Mounted `/home/oli/docker/ssl/home-lab-root.crt` into the Ryot service at `/usr/local/share/ca-certificates/home-lab-root.crt`.
- Set `SSL_CERT_FILE=/usr/local/share/ca-certificates/home-lab-root.crt` for the Rust backend HTTP client path.
- Set `NODE_EXTRA_CA_CERTS=/usr/local/share/ca-certificates/home-lab-root.crt` for the Node/React Router process path.
- No live Docker Compose lifecycle commands were run; deploy/recreate remains a Komodo action.

Verification:

- `docker compose --env-file apps/media/example.env -f apps/media/compose.yml config` rendered the Ryot CA mount plus `SSL_CERT_FILE` and `NODE_EXTRA_CA_CERTS`.
- `git diff --check` passed.
- The local CA file exists and parses as an X.509 certificate valid from 2026-04-22 to 2036-04-22.

## Rollback/Disable Path

No live state was changed by this 2026-07-06 verification checkpoint, so no rollback is required for the checkpoint itself.

Ryot rollback/disable path:

- Roll back through Komodo to the previous media stack revision.
- Disable or remove NPM `ryot.home.lab` host.
- Disable or remove Authentik Ryot application/provider/outpost entry.
- Remove AdGuard `ryot.home.lab` record if one is added.
- Remove Homepage Ryot entry if one is added.
- Preserve `${APPDATA_ROOT}/ryot-postgres` until Oli confirms backup/export and deletion intent.
- Do not delete Ryot database state as part of routine rollback.

## Follow-Ups

- Commit the repo-managed OPN-237 changes separately from unrelated local n8n changes.
- Host-level ownership of `/srv/appdata/ryot-postgres` could not be read with non-interactive sudo, but Docker mount metadata and in-container checks confirm the path is present and usable by Postgres.
- Backup coverage now includes `${APPDATA_ROOT}/ryot-postgres`; perform a real backup/readback exercise under the backup workflow when ready.
- After Ryot is deployed and healthy, decide separately whether to configure Jellyfin Sink in this pass.
- `OPN-228` can now proceed with live Ryot/OpenClaw connector work using the verified internal health and protected external route.
