# OPN-197 n8n Exposure And Runtime Mount Audit

## Scope

This is a report-only n8n exposure and runtime mount audit.

No Docker, firewall, proxy, Komodo, or compose changes were applied. Docker inspection was targeted to non-secret metadata and did not include environment values, logs, or raw inspect dumps.

Related evidence:

- `diagnostics/build-lanes/2026-06-28-opn-190-live-media-boundary-audit.md`
- `diagnostics/build-lanes/2026-06-28-opn-175-firewall-policy.md`

## Approved Read-Only Inspection Packet

Commands used for this pass:

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | rg '^(NAMES|jellyfin|n8n|gluetun|qbittorrent|nzbget)\b'
docker inspect n8n --format 'Name={{.Name}} Privileged={{.HostConfig.Privileged}} IpcMode={{.HostConfig.IpcMode}} NetworkMode={{.HostConfig.NetworkMode}} Ports={{json .NetworkSettings.Ports}} Mounts={{range .Mounts}}{{.Type}}:{{.Source}}->{{.Destination}}:rw={{.RW}};{{end}}'
```

These commands are read-only and avoid secrets.

## Current Evidence

Repo-managed compose in `apps/utilities/compose.yml` publishes n8n directly:

```yaml
ports:
  - "${N8N_PORT:-5678}:5678"
volumes:
  - ${APPDATA_ROOT}/n8n:/home/node/.n8n
networks:
  - utilities_net
  - proxy_net
```

Current live Docker inventory:

```text
n8n Up 15 hours 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp
```

Targeted non-secret Docker metadata:

```text
container /n8n; privileged false; ipc private; network proxy_net; ports {"5678/tcp":[{"HostIp":"0.0.0.0","HostPort":"5678"},{"HostIp":"::","HostPort":"5678"}]}; mounts bind:/data/configs/n8n->/home/node/.n8n:rw=true;
```

## Mount And Socket Findings

Docker socket access: disproven by the targeted mount output. No `/var/run/docker.sock` mount was observed.

Broad host mounts: disproven by the targeted mount output. The only observed mount is the n8n app-data bind mount to `/home/node/.n8n`.

Privilege posture:

- `Privileged=false`
- `IpcMode=private`

## Exposure Decision

Direct wildcard TCP `5678` exposure is not justified by current repo documentation. n8n is on `proxy_net`, so a reverse-proxy/auth path is available without direct host publishing.

n8n can trigger workflows and may contain credentials in app state. Even without Docker socket access or broad host mounts, its UI/API should not remain broadly host-published unless a specific LAN-only requirement is approved.

## Remediation Recommendation

Created follow-up enforcement issue: OPN-199, `SEC: Restrict direct n8n host exposure`.

Recommended enforcement plan:

1. Confirm intended n8n access path: Authentik/OIDC or reverse-proxy auth through Nginx Proxy Manager.
2. Remove or bind-restrict the direct host port in `apps/utilities/compose.yml`.
3. Prefer no host port when NPM can reach `n8n:5678` over `proxy_net`.
4. If a direct LAN exception is required, restrict it in OPN-175 to approved admin source ranges only.
5. Redeploy through Komodo.
6. Re-run read-only `docker ps` and targeted inspect checks.

## OPN-175 Firewall Policy Impact

OPN-175 already classifies media host n8n `5678/tcp` as:

```text
should-not-be-exposed directly | route through proxy/auth or close direct host exposure
```

That classification is supported by this audit.
