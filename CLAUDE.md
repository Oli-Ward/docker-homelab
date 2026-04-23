# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A homelab Docker Compose configuration repository. Each subdirectory is an independent stack deployed with `docker compose`. There is no build step, no tests, and no CI — changes are applied by redeploying the relevant stack.

## Deployments

Stacks are deployed and managed via **Komodo** (the `platform/komodo/` stack). Use the Komodo UI to deploy, update, or restart stacks rather than running `docker compose` manually. Each stack has its own `.env` file (gitignored) that Komodo uses when bringing up the stack.

For quick log inspection outside Komodo:

```bash
docker logs -f <container-name>
```

## Repository structure

```
apps/          Application stacks
  media/       Jellyfin + Jellyseerr
  arr-stack/   Radarr, Sonarr, Prowlarr, Bazarr, Autoscan, Cleanuparr
  downloads/   qBittorrent, NZBGet, FlareSolverr
  utilities/   Homepage dashboard

identity/
  authentik/   SSO/OIDC provider (Authentik server + worker + PostgreSQL)

infra/
  dns/adguard/              AdGuard Home DNS (port 53)
  network/gluetun/          VPN gateway
  proxy/nginx-proxy-manager/ Reverse proxy (ports 80/443, admin on 81)

platform/
  komodo/      Container management UI (Komodo Core + Periphery + MongoDB)

ssl/           TLS certificates (gitignored — not committed)
.generic.env   Shared vars: PUID=1000, PGID=1000, TZ=Pacific/Auckland
```

## Network architecture

Docker networks are all pre-created externally (`external: true`) except `auth_net` (created by Authentik's compose) and `komodo_net`.

| Network | Purpose |
|---|---|
| `proxy_net` | Services exposed via nginx-proxy-manager (Jellyfin, Jellyseerr, Authentik server, AdGuard) |
| `media_net` | Internal communication between arr-stack and media services |
| `vpn_net` | Download clients (qBittorrent, NZBGet) routed through Gluetun VPN |
| `auth_net` | Authentik internal (server, worker, PostgreSQL) |
| `utilities_net` | Homepage |
| `internal_net` | Komodo Core + nginx-proxy-manager |
| `komodo_net` | Komodo Core, Periphery, MongoDB |

## Key architectural patterns

**VPN routing:** qBittorrent and NZBGet use `network_mode: "service:gluetun"` — they share Gluetun's network namespace, so all their traffic exits through the VPN. Gluetun must be running before these containers start.

**Authentication:** Authentik is the OIDC provider. Jellyfin and Jellyseerr use a custom `preview-OIDC` image. Authentik `server` sits on both `auth_net` and `proxy_net`; the `worker` only needs `auth_net` plus Docker socket access.

**SSL:** The homelab root CA cert at `ssl/home-lab-root.crt` is bind-mounted read-only into services that need to trust internal TLS (Jellyfin, Jellyseerr, Homepage). Services use `NODE_EXTRA_CA_CERTS` or `update-ca-certificates` to load it.

**Data root:** Persistent app data lives under `DATA_ROOT` (default `/data`). Config dirs follow the pattern `${DATA_ROOT}/configs/<service-name>`. Media dirs are `${DATA_ROOT}/media/{tv,movies,books}` and downloads go to `${DATA_ROOT}/downloads`.

**Komodo:** Manages container deployments on this host. Periphery must have access to `/var/run/docker.sock` and the `PERIPHERY_ROOT_DIRECTORY` (default `/etc/komodo`). Compose files managed by Komodo must live under that root.

## Environment files

- `.generic.env` — documents the standard base vars (PUID, PGID, TZ) for reference, but is not automatically sourced by stacks
- Each stack has its own `.env` (gitignored) alongside an `example.env` or `compose.example.env` to document required variables
- `platform/komodo/compose.env` is gitignored; `compose.example.env` documents all available Komodo variables
