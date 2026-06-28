# OPN-198 Gluetun-Published Admin Ports Review

## Scope

This is a report-only identification and exposure review for gluetun-published TCP `6789` and TCP `8080`.

No Docker, firewall, proxy, Komodo, or compose changes were applied. Docker inspection was targeted to non-secret metadata and did not include environment values, logs, or raw inspect dumps.

Related evidence:

- `diagnostics/build-lanes/2026-06-28-opn-190-live-media-boundary-audit.md`
- `diagnostics/build-lanes/2026-06-28-opn-175-firewall-policy.md`

## Approved Read-Only Evidence

Commands used for this pass:

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | rg '^(NAMES|jellyfin|n8n|gluetun|qbittorrent|nzbget)\b'
docker inspect gluetun qbittorrent nzbget --format 'Name={{.Name}} Privileged={{.HostConfig.Privileged}} NetworkMode={{.HostConfig.NetworkMode}} Ports={{json .NetworkSettings.Ports}} Mounts={{range .Mounts}}{{.Type}}:{{.Source}}->{{.Destination}}:rw={{.RW}};{{end}}'
```

Repo-managed compose evidence from `apps/downloads/compose.yml`:

```yaml
gluetun:
  ports:
    - 8080:8080 # qBittorrent web UI
    - 6789:6789 # NZBGet web UI

qbittorrent:
  network_mode: "service:gluetun"

nzbget:
  network_mode: "service:gluetun"
```

## Current Live Evidence

Published ports:

```text
gluetun Up 15 hours (healthy) 1080/tcp, 0.0.0.0:6789->6789/tcp, [::]:6789->6789/tcp, 8000/tcp, 1080/udp, 8388/tcp, 8888/tcp, 8388/udp, 0.0.0.0:8080->8080/tcp, [::]:8080->8080/tcp
qbittorrent Up 15 hours
nzbget Up 15 hours
```

Targeted non-secret Docker metadata:

```text
container /gluetun; privileged false; network media_net; ports {"1080/tcp":null,"1080/udp":null,"6789/tcp":[{"HostIp":"0.0.0.0","HostPort":"6789"},{"HostIp":"::","HostPort":"6789"}],"8000/tcp":null,"8080/tcp":[{"HostIp":"0.0.0.0","HostPort":"8080"},{"HostIp":"::","HostPort":"8080"}],"8388/tcp":null,"8388/udp":null,"8888/tcp":null}; mounts bind:/data/configs/gluetun->/gluetun:rw=true;
container /qbittorrent; privileged false; network shares gluetun container namespace; ports {}; mounts bind:/data/configs/qbittorrent->/config:rw=true;bind:/data/downloads->/downloads:rw=true;
container /nzbget; privileged false; network shares gluetun container namespace; ports {}; mounts bind:/data/configs/nzbget->/config:rw=true;bind:/data/downloads->/downloads:rw=true;
```

## Port Identification

TCP `8080`: qBittorrent web UI, published by gluetun because qBittorrent shares gluetun's network namespace.

TCP `6789`: NZBGet web UI, published by gluetun because NZBGet shares gluetun's network namespace.

qBittorrent and NZBGet do not publish their own host ports; the admin surfaces are exposed through gluetun's host port mappings.

## Exposure Decision

Both `8080/tcp` and `6789/tcp` are downloader admin surfaces. They should not be reachable from OpenClaw and should not be broadly reachable from the LAN unless a specific admin-only exception is approved.

The current wildcard IPv4 and IPv6 mappings are broader than the intended OpenClaw/media gateway boundary.

## OPN-175 Firewall Policy Impact

OPN-175 already classifies these surfaces as:

```text
Media host qBittorrent UI via gluetun 8080/tcp | should-not-be-exposed directly | downloader admin UI
Media host NZBGet UI via gluetun 6789/tcp | should-not-be-exposed directly | downloader admin UI
```

This review supports denying direct `8080/tcp` and `6789/tcp` except for any explicitly approved admin source range.

## Recommendation

Prefer removing direct host publication and routing any required UI access through the established proxy/auth/admin path. If direct admin access is retained, restrict it to approved admin LAN or Tailscale sources in OPN-175 before enforcement.
