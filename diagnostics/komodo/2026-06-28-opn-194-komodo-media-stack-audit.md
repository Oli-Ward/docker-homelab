# OPN-194 Komodo Media Stack Inventory And Manual Update Audit

## Scope And Safety

This audit captures read-only evidence for the current media host Docker/Komodo update posture.

No Docker resources, Compose files, Komodo config, backup jobs, containers, images, volumes, networks, or secrets were changed. Real `.env` and `compose.env` files were not opened.

## Evidence Summary

- Running Docker Compose containers point back to tracked compose files under `/home/oli/docker`.
- The live Docker evidence proves the currently running Compose projects and services, but does not by itself prove every project is currently registered as a Komodo Stack resource.
- Komodo itself is running from `platform/komodo/mongo.compose.yaml`; Core and Periphery containers are present, and Periphery has the Docker socket mount required to manage Docker resources.
- Repo-managed Homepage config has a Komodo dashboard entry at `https://komodo.home.lab` and a widget pointed at `http://komodo-core-1:9120` using env-backed API credentials.
- From this shell, `komodo.home.lab` did not resolve and `127.0.0.1:9120` was not published. Komodo Core was reachable only by Docker network IP for static UI assets.
- The local browser automation path could not inspect the UI because Playwright CLI could not find Chrome. No credentials were read or entered.
- The served Komodo static UI bundle contains Stack action labels including `DeployStack`, `PullStack`, `RestartStack`, `StartStack`, `StopStack`, `PauseStack`, `DestroyStack`, `ListStackServices`, `GetStackActionState`, `Procedure`, `ResourceSync`, `Batch`, and `Update`.
- No direct authenticated Komodo inventory, tags, Procedures, or update-indicator state was proven in this audit.

## Observed Compose And Docker Inventory

Tracked Compose files:

```text
apps/arr-stack/compose.yml
apps/docs/compose.yml
apps/downloads/compose.yml
apps/media/compose.yml
apps/openclaw-gateway/compose.yml
apps/utilities/compose.yml
identity/authentik/compose.yml
infra/dns/adguard/compose.yml
infra/proxy/nginx-proxy-manager/compose.yml
platform/komodo/mongo.compose.yaml
```

Live Docker Compose label evidence:

| Compose project | Running services observed | Config file | Env file label |
| --- | --- | --- | --- |
| `media` | `jellyfin`, `jellyseerr` | `/home/oli/docker/apps/media/compose.yml` | `/home/oli/docker/apps/media/.env` |
| `arr-stack` | `radarr`, `sonarr`, `prowlarr`, `bazarr`, `autoscan`, `cleanuparr` | `/home/oli/docker/apps/arr-stack/compose.yml` | `/home/oli/docker/apps/arr-stack/.env` |
| `downloads` | `gluetun`, `qbittorrent`, `nzbget`, `flaresolverr` | `/home/oli/docker/apps/downloads/compose.yml` | `/home/oli/docker/apps/downloads/.env` |
| `docs` | `paperless-webserver`, `paperless-db`, `paperless-broker`, `paperless-gotenberg`, `paperless-tika` | `/home/oli/docker/apps/docs/compose.yml` | `/home/oli/docker/apps/docs/.env` |
| `utilities` | `homepage`, `glances`, `speedtest-tracker`, `n8n` | `/home/oli/docker/apps/utilities/compose.yml` | `/home/oli/docker/apps/utilities/.env` |
| `openclaw-gateway` | `openclaw-gateway` | `/home/oli/docker/apps/openclaw-gateway/compose.yml` | `/home/oli/docker/apps/openclaw-gateway/.env` |
| `authentik` | `authentik-server`, `authentik-worker`, `authentik-postgresql` | `/home/oli/docker/identity/authentik/compose.yml` | `/home/oli/docker/identity/authentik/.env` |
| `adguard` | `adguard` | `/home/oli/docker/infra/dns/adguard/compose.yml` | `/home/oli/docker/infra/dns/adguard/.env` |
| `nginx-proxy-manager` | `nginx-proxy-manager` | `/home/oli/docker/infra/proxy/nginx-proxy-manager/compose.yml` | none shown in Compose labels |
| `komodo` | `komodo-core`, `komodo-periphery`, `komodo-mongo` | `/home/oli/docker/platform/komodo/mongo.compose.yaml` | `/home/oli/docker/platform/komodo/compose.env` |

Drift noted: `apps/utilities/compose.yml` defines `icloudpd`, but no running `icloudpd` container appeared in the current `docker ps` evidence.

Observed Docker networks:

```text
adguard_default
authentik_auth_net
authentik_default
bridge
docs_docs_net
host
internal_net
komodo_default
komodo_net
media_net
none
proxy_net
utilities_net
vpn_net
```

## Komodo-Managed Inventory Evidence

Strong evidence:

- `platform/komodo/mongo.compose.yaml` defines `mongo`, `core`, and `periphery`.
- `komodo-core-1`, `komodo-periphery-1`, and `komodo-mongo-1` are running.
- The Periphery compose service mounts `/var/run/docker.sock:/var/run/docker.sock`, which is the expected live Docker management boundary.
- Homepage includes a Komodo widget configured with type `komodo` and env-backed API credentials.

Evidence gap:

- The audit did not obtain authenticated Komodo Stack API/UI data, so it cannot conclusively say which running Compose projects are registered as Komodo Stack resources today.
- The Docker label evidence shows the live Compose projects and paths that Komodo would manage, but Docker labels are not equivalent to Komodo's resource database.

Best current inventory statement:

The currently running media-host stack candidates are `media`, `arr-stack`, `downloads`, `docs`, `utilities`, `openclaw-gateway`, plus supporting infrastructure stacks `authentik`, `adguard`, `nginx-proxy-manager`, and `komodo`. Direct Komodo resource registration remains an unknown until an authenticated read-only Komodo inventory is captured.

## OPN-173 Policy Bucket Mapping

| Policy bucket | Observed services | Rationale |
| --- | --- | --- |
| manual only | `paperless-webserver`, `paperless-db`, `paperless-broker`, `n8n`, `nginx-proxy-manager`, `authentik-server`, `authentik-worker`, `authentik-postgresql`, `adguard`, `komodo-core`, `komodo-periphery`, `komodo-mongo` | Stateful databases, identity/proxy/DNS/orchestration services, or higher-blast-radius automation. Require backup/checkpoint and deliberate operator review before updates. |
| manual monthly | `jellyfin`, `jellyseerr`, `sonarr`, `radarr`, `bazarr` | User-facing media apps with appdata mounts and integrations; update deliberately after checking release notes and backup posture. |
| cautious/manual | `qbittorrent`, `gluetun`, `prowlarr`, `nzbget`, `flaresolverr` | Download/VPN/indexer path; failures can break acquisition or expose routing assumptions. `qbittorrent` and `nzbget` share Gluetun network mode. |
| safe-ish/manual | `openclaw-gateway`, `autoscan`, `cleanuparr`, `homepage`, `glances`, `speedtest-tracker` | Smaller helper/dashboard/gateway tools, but still update manually because several have appdata mounts, Docker socket reads, or operational dependencies. |
| repo/live drift to confirm | `icloudpd` | Defined in repo, not observed running in Docker during this audit. |

Stateful vs lower-risk helper readout:

- Stateful appdata/database services: Jellyfin, Jellyseerr, Sonarr, Radarr, Prowlarr, Bazarr, Autoscan, Cleanuparr, qBittorrent, NZBGet, FlareSolverr, Gluetun, Paperless web/db/broker, Homepage config, Glances config, iCloudPD config, Speedtest Tracker, n8n, Authentik, AdGuard, NPM, Komodo.
- Lower-risk helpers with no obvious durable appdata in tracked compose: Paperless Gotenberg and Paperless Tika.
- Operationally sensitive helpers even if small: OpenClaw Gateway, Homepage, Glances, Gluetun, FlareSolverr, Cleanuparr.

## Manual Komodo Update Workflow Evidence

Proven from local Komodo UI assets:

- The served Komodo UI bundle includes Stack actions: `DeployStack`, `PullStack`, `RestartStack`, `StartStack`, `StopStack`, `PauseStack`, and `DestroyStack`.
- Stack pages include tabs or panels for `Config`, `Info`, `Services`, `Log`, and `Terminals`.
- The UI bundle has service-level Stack actions and group/batch execution support.
- The UI bundle has `Procedure` and `ResourceSync` concepts.

Not proven:

- The exact operator click-path currently used by Oli for updates.
- Whether Oli updates by opening a Stack, using `Pull Images`, then `Deploy`, or by another Procedure/ResourceSync/batch path.
- Whether update indicators are visible for the observed stacks today.
- Whether any current Stack has `poll_for_updates`, `auto_update`, tags, Procedures, or batch rollout groups configured.

Safe inferred manual path to verify later:

```text
Komodo UI -> Stack resource -> review Stack/Services state -> Pull Images if intended -> Deploy only after backup/checkpoint and release-note review
```

This is an inference from UI action labels and repo policy, not an observed authenticated operator session.

## Update Indicators, Tags, Procedures, And Batch Rollout Evidence

Evidence found:

- The static UI bundle contains labels and code paths for `Procedure`, `ResourceSync`, batch execution, Stack service lists, action state, and update-related UI.
- The Docker label check did not show a `com.centurylinklabs.watchtower.enable` value on observed containers, so no Watchtower opt-in label was proven from running container metadata.

Evidence not found:

- No authenticated Komodo data proving current tags on Stack resources.
- No authenticated Komodo data proving current Procedures.
- No authenticated Komodo data proving batch rollout patterns.
- No authenticated Komodo data proving current update indicators for any specific service.

## Unknowns

- Which of the observed Compose projects are registered as Komodo Stack resources in Komodo's database today.
- Whether any repo-defined but non-running service, especially `icloudpd`, is intentionally stopped, missing, or unmanaged.
- The exact manual update click-path currently used by Oli.
- Whether `poll_for_updates`, `auto_update`, tags, Procedures, or batch execution groups are configured for any Stack.
- Whether Komodo has stale Stack resources for removed/renamed projects.
- Whether Komodo stack definitions exactly match the current repo paths or include UI-side overrides not visible in Docker labels.

## Safety Notes

- Docker commands used were read-only: `docker ps`, `docker inspect`, and `docker network ls`.
- HTTP checks were GET/HEAD requests against Komodo Core static UI routes only.
- Playwright browser automation was attempted but did not run because Chrome was not installed.
- No Komodo credentials, Homepage widget secrets, `.env` values, API keys, cookies, or tokens were read or printed.
- No update, pull, redeploy, restart, stop, start, prune, exec, backup, restore, or config mutation command was run.

## Verification Commands

Commands run for this audit:

```bash
git status --short --branch
git ls-files '*compose*.yml' '*compose*.yaml'
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Labels}}'
docker ps --format '{{.Names}}' | while IFS= read -r c; do docker inspect "$c" --format '{{.Name}}|{{index .Config.Labels "com.docker.compose.project"}}|{{index .Config.Labels "com.docker.compose.service"}}|{{index .Config.Labels "com.docker.compose.project.config_files"}}|{{index .Config.Labels "com.docker.compose.project.environment_file"}}|{{index .Config.Labels "com.docker.compose.project.working_dir"}}|{{index .Config.Labels "com.centurylinklabs.watchtower.enable"}}'; done
docker network ls --format '{{.Name}}'
sed -n '1,260p' apps/media/compose.yml
sed -n '1,320p' apps/arr-stack/compose.yml
sed -n '1,320p' apps/downloads/compose.yml
sed -n '1,260p' apps/docs/compose.yml
sed -n '1,240p' apps/utilities/compose.yml
sed -n '1,220p' apps/openclaw-gateway/compose.yml
sed -n '1,260p' identity/authentik/compose.yml
sed -n '1,220p' infra/proxy/nginx-proxy-manager/compose.yml
sed -n '1,220p' infra/dns/adguard/compose.yml
sed -n '1,240p' platform/komodo/mongo.compose.yaml
rg -n --hidden -g '!*.env' -g '!**/.env' -g '!platform/komodo/compose.env' -g '!**/.git/**' 'Komodo|update|redeploy|procedure|Procedure|stack|manual' README.md AGENTS.md apps docs diagnostics platform infra identity
sed -n '130,190p' apps/utilities/homepage/services.yaml
rg -n "komodo|Komodo|home\.lab|9120|core" apps/utilities/homepage README.md platform/komodo/mongo.compose.yaml infra/proxy/nginx-proxy-manager/compose.yml
curl -k -I --max-time 5 https://komodo.home.lab
curl -sS -k --max-time 5 https://komodo.home.lab
curl -sS --max-time 5 http://127.0.0.1:9120
docker inspect komodo-core-1 --format '{{range $name, $net := .NetworkSettings.Networks}}{{$name}}={{$net.IPAddress}} {{end}}'
docker inspect komodo-core-1 --format '{{json .NetworkSettings.Ports}}'
curl -sS --max-time 5 -I http://172.20.0.5:9120
curl -sS --max-time 5 http://172.20.0.5:9120
curl -sS --max-time 5 http://172.20.0.5:9120/assets/index-uLyEr4OC.js | rg -o 'DeployStack|Deploy Stack|Update|Update Available|Procedure|Procedures|ResourceSync|Stack|Stacks|redeploy|Redeploy|Pull|Refresh|Prune|Batch|Batch Deploy' | sort | uniq -c | sort -nr
for p in /api /api/swagger-ui /api/openapi.json /openapi.json /api/user /api/read /auth/me; do printf '\n## %s\n' "$p"; curl -sS --max-time 5 -i "http://172.20.0.5:9120$p" | sed -n '1,24p'; done
```
