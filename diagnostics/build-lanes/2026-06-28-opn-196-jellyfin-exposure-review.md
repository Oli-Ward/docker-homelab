# OPN-196 Jellyfin Exposure Review

## Scope

This is a report-only review of Jellyfin direct host exposure.

No Docker, firewall, proxy, Komodo, or compose changes were applied.

Related evidence:

- `diagnostics/build-lanes/2026-06-28-opn-190-live-media-boundary-audit.md`
- `diagnostics/build-lanes/2026-06-28-opn-175-firewall-policy.md`

## Current Evidence

Repo-managed compose in `apps/media/compose.yml` publishes Jellyfin directly:

```yaml
ports:
  - 8096:8096
```

The same compose service also joins `media_net` and `proxy_net`, so Jellyfin is available internally by Docker service name and to the reverse-proxy network.

Current live Docker inventory:

```text
jellyfin Up 15 hours 0.0.0.0:8096->8096/tcp, [::]:8096->8096/tcp, 8920/tcp
```

Targeted non-secret Docker metadata:

```text
container /jellyfin; privileged false; network media_net; ports {"8096/tcp":[{"HostIp":"0.0.0.0","HostPort":"8096"},{"HostIp":"::","HostPort":"8096"}],"8920/tcp":null}; mounts bind:/data/media/tv->/data/tv:rw=true;bind:/data/media/movies->/data/movies:rw=true;bind:/home/oli/docker/ssl/home-lab-root.crt->/usr/local/share/ca-certificates/home-lab-root.crt:rw=false;bind:/data/configs/jellyfin->/config:rw=true;
```

Repo-managed Homepage points the user-facing URL at `https://jellyfin.home.lab`, while widgets use internal Docker networking at `http://jellyfin:8096`.

The OpenClaw gateway documentation says OpenClaw should use selected read-only gateway endpoints and should not receive upstream media credentials.

## Exposure Model Decision

Intended model for OpenClaw: gateway-only. OpenClaw should not directly reach Jellyfin TCP `8096`; it should use the OpenClaw media gateway.

Intended model for user access: reverse proxy first via `https://jellyfin.home.lab`. If direct LAN Jellyfin access remains desired for clients, it should be an explicit LAN-only exception rather than wildcard host exposure.

Current wildcard host exposure on `0.0.0.0:8096` and `[::]:8096` is broader than the documented OpenClaw/media gateway boundary.

## Safe Remediation Plan

Do not enforce this directly from this report. Use Komodo for deployment and apply firewall/proxy changes only after approval.

Recommended sequence:

1. Confirm whether direct LAN Jellyfin clients need `http://media-host:8096`.
2. If no direct clients are required, remove the Jellyfin host port mapping in `apps/media/compose.yml` and keep access through Nginx Proxy Manager plus Docker-internal service access.
3. If direct LAN clients are required, change `8096` from wildcard exposure to an explicit LAN-only firewall allowance in OPN-175 and deny non-approved sources.
4. Confirm Nginx Proxy Manager `jellyfin.home.lab` still reaches Jellyfin over `proxy_net`.
5. Redeploy through Komodo, not direct `docker compose up/down`.
6. Re-run read-only published-port and gateway health checks after deployment.

## OPN-175 Firewall Policy Impact

OPN-175 already accounts for Jellyfin as:

```text
Media host Jellyfin 8096/tcp | reverse-proxy-only or LAN-only | do not expose directly to OpenClaw in gateway-only model
```

Update OPN-175 enforcement only after the direct-LAN decision is made:

- `proxy-only`: deny direct `8096/tcp` and rely on Nginx Proxy Manager.
- `LAN-only exception`: allow `8096/tcp` only from approved LAN client ranges; deny OpenClaw except through gateway.

## Recommendation

Treat direct wildcard Jellyfin host exposure as not intended for OpenClaw. Prefer proxy-only unless a concrete LAN client requirement is confirmed.
