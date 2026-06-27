# OPN-190 Live Media Boundary Audit

## Scope

This report records the OPN-190 live media boundary audit attempt for the OpenClaw to media-host path.

Related issues: OPN-168 for the intended OpenClaw/media boundary model, and OPN-175 for the follow-on firewall policy.

The requested audit scope was:

- OpenClaw Ubuntu to media-host network path.
- Media-host published ports.
- Exact deployed media gateway endpoint and port.
- Whether direct Jellyfin, Jellyseerr, Sonarr, or Radarr admin APIs are reachable from OpenClaw.
- Whether qBittorrent, NZBGet, or Prowlarr have any reachable exposure relevant to OpenClaw.
- Whether n8n exists at runtime and, if present, whether it has Docker socket access or broad host mounts.

This was kept report-only. No firewall, Docker write, restart, compose, reverse-proxy, or deployment action was performed.

## Approval Packet

The named host was confirmed by the operator as the current media server. The live audit was limited to the OPN-190 baseline read-only command set:

- `ss -tulpn`
- `ip addr`
- `sudo ufw status verbose || true`
- `docker ps --format 'table {{.Names}}\t{{.Ports}}'`

After the baseline report, the operator approved continuing. Additional targeted read-only Docker metadata checks were run with explicit `docker inspect --format` fields for n8n, gluetun, OpenClaw gateway, qBittorrent, and NZBGet. These checks intentionally avoided environment values, logs, and raw inspect dumps.

No firewall changes, Docker writes, restarts, compose edits, reverse-proxy changes, or secret capture were performed. Docker inspection was limited to targeted non-secret metadata and did not include environment values, logs, or raw inspect dumps.

## Commands And Categories Run

Linear reads:

- Fetched OPN-190 issue details.
- Listed OPN-190 comments.
- Listed Openclaw issue statuses.

Workspace-only checks:

- `git status --short`
- `rg` searches for OPN-190, approval packet, access packet, live media boundary audit, gateway verification, and the issue-suggested command strings.
- `rg --files` searches for OPN-190, media-boundary, gateway, audit, approval, and packet artifacts.
- `find diagnostics -maxdepth 3 -type f | sort`
- `find docs -maxdepth 4 -type f | sort | rg 'opn-168|opn-175|media-boundary|firewall|gateway'`
- Read repo-managed OpenClaw gateway docs and compose file.

Live host checks:

- Port inventory: run.
- Interface inventory: run.
- Firewall status: attempted, but `sudo` required an interactive password and `ufw` also required root without sudo.
- Docker runtime published-port inventory: run with `docker ps`.
- Targeted Docker metadata inspection: run with explicit `--format` fields for mounts, bind paths, privilege mode, network mode, labels, and port mappings. Environment values were not inspected.

Live host categories not run:

- Environment inspection, log inspection, or raw Docker inspect dumps.
- Reachability probing from OpenClaw.
- Reverse-proxy configuration inspection.

## Non-Secret Findings

- The media host has a LAN interface and a Tailscale interface. Address values are intentionally redacted.
- The workspace contains repo-managed OpenClaw gateway intent: the gateway stack binds a configured media-host LAN address and port to container port `8080`.
- The repo-managed gateway service joins only the external `media_net` Docker network.
- The gateway documentation states the intended OpenClaw boundary is the gateway only, with selected read-only Jellyfin and Jellyseerr endpoints.
- The gateway documentation states OpenClaw should not receive upstream media service credentials.
- Live Docker inventory shows `openclaw-gateway` published on the media-host LAN address at TCP `8088`, forwarding to container TCP `8080`.
- Live socket inventory also shows TCP `8088` listening only on the media-host LAN address, not all interfaces.
- Live Docker inventory shows `jellyfin` published on all IPv4 and IPv6 interfaces at TCP `8096`.
- Live Docker inventory shows `n8n` published on all IPv4 and IPv6 interfaces at TCP `5678`.
- Live Docker inventory shows `nginx-proxy-manager` published on all IPv4 and IPv6 interfaces at TCP `80`, `81`, and `443`.
- Live Docker inventory shows `authentik-server` published on all IPv4 and IPv6 interfaces at TCP `9000` and `9443`.
- Live Docker inventory shows `adguard` published on DNS TCP/UDP `53` and selected admin or service ports.
- Live Docker inventory shows `gluetun` published on all IPv4 and IPv6 interfaces at TCP `6789` and TCP `8080`; the exact upstream app behind those gluetun-published ports was not confirmed without Docker inspection.
- Live Docker inventory shows `sonarr`, `radarr`, `prowlarr`, `jellyseerr`, `qbittorrent`, and `nzbget` containers exist, but their own container rows did not show host-published ports.
- Targeted Docker metadata and repo compose evidence identify gluetun TCP `8080` as the qBittorrent web UI and gluetun TCP `6789` as the NZBGet web UI.
- qBittorrent and NZBGet share the gluetun network namespace and have no direct host-published ports on their own container rows.
- n8n is not privileged and has only its application data bind mount; no Docker socket mount or broad host mount was observed in the targeted metadata.
- OpenClaw gateway is not privileged and has no bind mounts.
- Gluetun is not privileged, has the expected VPN tunnel device and network capability, and has only its application data bind mount.
- Firewall state was not confirmed because UFW status required elevated access.
- The previously referenced OPN-168 and OPN-175 dated diagnostics reports were not present in this checkout under `diagnostics/build-lanes`.

## OpenClaw Gateway Path

Status: partially verified from media-host live evidence.

Repo intent indicates OpenClaw should call only the media gateway path on the configured gateway port, and the gateway should call upstream media services from inside Docker networking.

Live media-host evidence confirms the deployed gateway listener is present on the media-host LAN address at TCP `8088`.

This report does not prove that OpenClaw reaches only the gateway path, because no reachability probing from the OpenClaw host was run and firewall state could not be read.

## Direct Media/Admin Surface Exposure

Status: direct host-published surfaces are present.

From the media-host published-port inventory:

- Jellyfin is directly host-published on all IPv4 and IPv6 interfaces at TCP `8096`.
- n8n is directly host-published on all IPv4 and IPv6 interfaces at TCP `5678`.
- Gluetun publishes qBittorrent web UI TCP `8080` and NZBGet web UI TCP `6789` on all IPv4 and IPv6 interfaces.
- Nginx Proxy Manager, Authentik, and AdGuard also expose admin or service ports on all interfaces, though they are infrastructure surfaces rather than media app APIs.
- Sonarr, Radarr, Prowlarr, Jellyseerr, qBittorrent, and NZBGet did not show direct host-published ports on their own container rows.

This is a boundary risk for OPN-175: the current live media host is not limited to only the OpenClaw gateway listener from the perspective of host-published ports. Whether OpenClaw can actually reach those direct surfaces still depends on firewall/routing state, which was not confirmed.

## n8n Runtime And Mount Review

Status: n8n runtime present; Docker socket and broad host mounts not observed.

Live Docker inventory confirms an `n8n` container is running and published on all IPv4 and IPv6 interfaces at TCP `5678`.

Targeted Docker metadata confirms:

- `n8n` is not privileged.
- `n8n` has a private IPC mode.
- `n8n` has an application data bind mount only.
- No Docker socket mount was observed.
- No broad host mount was observed.

## Follow-Up Issues Needed

Created follow-up issues:

- OPN-196: Review and restrict direct Jellyfin host exposure on TCP `8096` if OpenClaw/media boundary policy requires gateway-only media access.
- OPN-197: Audit n8n exposure and runtime mounts. Mount/socket inspection is now answered by this report; direct TCP `5678` exposure still needs a policy decision.
- OPN-198: Identify gluetun-published TCP `6789` and TCP `8080`. Identification is now answered by this report; qBittorrent and NZBGet web UI exposure still needs a policy decision.

Additional follow-up needed: provide elevated read-only firewall status access or another approved way to capture firewall rules without making changes.

## OPN-175 Readiness

OPN-175 can proceed to firewall policy drafting, but not enforcement, using these live findings.

The firewall policy should account for the observed live host-published surfaces:

- Gateway listener on media-host LAN TCP `8088`.
- Direct Jellyfin host exposure on TCP `8096`.
- Direct n8n host exposure on TCP `5678`, with no Docker socket or broad host mount observed.
- qBittorrent web UI exposure through gluetun TCP `8080`.
- NZBGet web UI exposure through gluetun TCP `6789`.
- Infrastructure exposures including Nginx Proxy Manager, Authentik, and AdGuard.

Before enforcement, OPN-175 still needs either UFW status or an approved equivalent firewall rules readout, plus optional OpenClaw-origin reachability checks to distinguish host-published ports from actually reachable surfaces.
