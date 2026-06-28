# OPN-175 Firewall Policy Evidence And Draft

## Scope

This is an evidence and drafting pass for OPN-175.

No firewall rules, UFW changes, iptables changes, nftables changes, reverse-proxy changes, Docker changes, service restarts, or network configuration changes were applied.

All rules below are DRAFT ONLY - NOT APPLIED.

Related evidence:

- OPN-190 completed live media boundary audit.
- `diagnostics/build-lanes/2026-06-28-opn-190-live-media-boundary-audit.md`

## Approved Command Packet

The operator approved read-only inventory commands for:

- Proxmox host.
- OpenClaw Ubuntu VM.
- Media Ubuntu Docker host.

The current workspace shell is on `media-homelab`, the media Ubuntu Docker host. The full media-host command packet was run locally.

OpenClaw VM access was not available from this workspace through `openclaw-lab`, `openclaw`, or `openclaw-ubuntu` hostnames.

Proxmox SSH access was not used because the configured `media-proxmox` target produced a host-key changed warning for `192.168.1.108`. This report does not bypass SSH host-key verification.

The configured `media-ubuntu` SSH alias also could not be used because it referenced a missing identity file. This did not block media-host inventory because the workspace itself is the media host.

## Commands Run

Media Ubuntu Docker host, run locally:

```bash
hostname
ip addr
ip route
ss -tulpn
sudo ufw status verbose || true
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
docker network ls
docker inspect media-api-gateway n8n --format '{{json .NetworkSettings.Networks}}' || true
docker inspect media-api-gateway n8n --format '{{json .Mounts}}' || true
curl -sS -I --max-time 5 http://192.168.1.103:8088/health || true
curl -sS --max-time 5 http://192.168.1.103:8088/health || true
```

OpenClaw access discovery:

```bash
getent hosts openclaw-lab || true
getent hosts openclaw || true
getent hosts openclaw-ubuntu || true
ssh -o BatchMode=yes -o ConnectTimeout=8 openclaw-lab hostname || true
ssh -o BatchMode=yes -o ConnectTimeout=8 openclaw hostname || true
ssh -o BatchMode=yes -o ConnectTimeout=8 openclaw-ubuntu hostname || true
```

Proxmox access attempt:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=8 media-proxmox '<approved read-only packet>'
```

## Current Observed Inventory

### Media Ubuntu Docker Host

Hostname: `media-homelab`.

Observed addresses and routes:

- LAN: `192.168.1.103/24` on `ens18`.
- Default route: `192.168.1.1`.
- Tailscale: `100.119.203.72/32` on `tailscale0`.
- Docker bridge networks are present for app stacks.

Firewall state:

- `sudo ufw status verbose` was later provided by the operator from the media host.
- UFW status: `inactive`.
- Current media-host filtering is therefore not being enforced by UFW.

Observed host listeners from `ss -tulpn` and Docker published ports:

| Host port | Bind | Evidence | Classification | Policy decision |
| --- | --- | --- | --- | --- |
| 22/tcp | all IPv4/IPv6 | host SSH | LAN-only or Tailscale-only | keep reachable only from trusted admin networks |
| 53/tcp+udp | all IPv4/IPv6 | AdGuard | LAN-only | allow only from LAN clients that use this DNS server |
| 80/tcp | all IPv4/IPv6 | Nginx Proxy Manager | reverse-proxy-only | allow LAN to proxy only |
| 81/tcp | all IPv4/IPv6 | Nginx Proxy Manager admin | LAN-only or Tailscale-only | restrict to admin clients only |
| 443/tcp | all IPv4/IPv6 | Nginx Proxy Manager | reverse-proxy-only | allow LAN to proxy only |
| 111/tcp+udp | all IPv4/IPv6 | rpcbind | should-not-be-exposed | deny unless a specific NFS/RPC need is approved |
| 5678/tcp | all IPv4/IPv6 | n8n | reverse-proxy-only or should-not-be-exposed | do not expose directly; require proxy/auth review |
| 6789/tcp | all IPv4/IPv6 | gluetun -> NZBGet UI per OPN-190 | reverse-proxy-only or should-not-be-exposed | do not expose directly |
| 8080/tcp | all IPv4/IPv6 | gluetun -> qBittorrent UI per OPN-190 | reverse-proxy-only or should-not-be-exposed | do not expose directly |
| 8088/tcp | `192.168.1.103` only | `openclaw-gateway` -> container `8080` | OpenClaw-only | allow only from OpenClaw runtime IP once confirmed |
| 8090/tcp | all IPv4/IPv6 | AdGuard admin mapping | LAN-only or Tailscale-only | restrict to admin clients only |
| 8096/tcp | all IPv4/IPv6 | Jellyfin | reverse-proxy-only or LAN-only | do not expose to OpenClaw directly; prefer proxy/auth decision |
| 9000/tcp | all IPv4/IPv6 | Authentik HTTP | reverse-proxy-only | restrict direct access to proxy/LAN admin path |
| 9443/tcp | all IPv4/IPv6 | Authentik HTTPS | reverse-proxy-only | restrict direct access to proxy/LAN admin path |
| 3001/tcp | all IPv4/IPv6 | AdGuard admin mapping | LAN-only or Tailscale-only | restrict to admin clients only |
| Tailscale high ports | Tailscale address | Tailscale daemon | Tailscale-only | keep within Tailscale interface |
| Local high ports | `127.0.0.1` | local dev/editor processes | localhost-only | no LAN exposure |

Docker containers with exposed container-only ports but no host-published port should stay internal-only unless a separate issue approves exposure. Examples include Paperless internals, Sonarr, Radarr, Prowlarr, Jellyseerr, Bazarr, Autoscan, Glances, Homepage, Komodo internals, MongoDB, and Authentik PostgreSQL.

Gateway evidence:

- Live gateway container is named `openclaw-gateway`, not `media-api-gateway`.
- `media-api-gateway` does not exist as a live Docker object on this host.
- `openclaw-gateway` publishes `192.168.1.103:8088->8080/tcp`.
- `curl -I http://192.168.1.103:8088/health` returns HTTP `405 Method Not Allowed`, which is expected for `HEAD` against this FastAPI route.
- `curl http://192.168.1.103:8088/health` returns `{"status":"ok"}`.

n8n targeted inspection:

- `n8n` is attached to `proxy_net` and `utilities_net`.
- Observed mount: `/data/configs/n8n` to `/home/node/.n8n`.
- No Docker socket mount was shown by the approved mount inspection.
- No broad host mount was shown by the approved mount inspection.

### OpenClaw Ubuntu VM

OpenClaw inventory was provided by the operator from the `ubuntu-openclaw` VM.

Hostname: `openclaw-lab`.

Observed addresses and routes:

- LAN: `192.168.1.16/24` on `enp6s18`.
- Default route: `192.168.1.1`.
- Docker bridge networks are present.

Firewall state:

- `sudo ufw status verbose` reported `Status: inactive`.
- `sudo ufw status numbered` reported `Status: inactive`.
- `ufw` is installed at `/usr/sbin/ufw`.
- `ufw.service` is enabled and `active (exited)`.
- Current OpenClaw filtering is therefore not being enforced by UFW.

Observed host listeners from `ss -tulpn`:

| Host port | Bind | Evidence | Classification | Policy decision |
| --- | --- | --- | --- | --- |
| 22/tcp | all IPv4/IPv6 | SSH | LAN-only or Tailscale-only | keep reachable only from trusted admin networks |
| 80/tcp | all IPv4/IPv6 | HTTP listener | reverse-proxy-only or LAN-only | verify intended Caddy/reverse-proxy role before allowing broadly |
| 53/tcp+udp | loopback only | local resolver | localhost-only | no LAN exposure observed |
| 2019/tcp | loopback only | Caddy admin API candidate | localhost-only | no LAN exposure observed |
| 8080/tcp | loopback only | local OpenClaw/app listener candidate | localhost-only | no LAN exposure observed |
| Local high ports | loopback only | local dev/app processes | localhost-only | no LAN exposure observed |

Connectivity check from OpenClaw to the media gateway:

- `curl -I http://192.168.1.103:8088/health` returned HTTP `405 Method Not Allowed`, expected for `HEAD`.
- `curl http://192.168.1.103:8088/health` returned `{"status":"ok"}`.
- This confirms OpenClaw can reach the approved media gateway endpoint at `192.168.1.103:8088`.

System health:

- `systemctl --failed` reported `0 loaded units listed`.

Remaining OpenClaw evidence gap before enforcement:

- None for the current report-only drafting pass.

### Proxmox Host

Proxmox inventory was provided by the operator from a root shell on `proxmox`.

Observed addresses and routes:

- LAN: `192.168.1.108/24` on `vmbr0`.
- Default route: `192.168.1.1`.
- `nic0` is enslaved to `vmbr0`.
- Proxmox firewall bridge devices are present for VM IDs `100` and `101`.

Firewall state:

- `sudo` is not installed on the Proxmox host.
- `ufw` is not installed on the Proxmox host.
- No UFW rules exist to draft against on this host; Proxmox firewall/nftables policy needs a separate explicit enforcement plan if host-level filtering is desired.
- `/etc/pve/firewall/cluster.fw`, `/etc/pve/nodes/$(hostname)/host.fw`, and `/etc/pve/firewall/101.fw` did not print any configured rules in the operator-provided output.
- `pve-firewall status` reported `Status: disabled/running`.
- Proxmox firewall is therefore not enforcing policy, even though VM `101` has `firewall=1` on `net0`.

Observed host listeners from `ss -tulpn`:

| Host port | Bind | Evidence | Classification | Policy decision |
| --- | --- | --- | --- | --- |
| 22/tcp | all IPv4/IPv6 | `sshd` | LAN-only or Tailscale-only | keep reachable only from trusted admin networks |
| 111/tcp+udp | all IPv4/IPv6 | `rpcbind` | should-not-be-exposed unless approved | deny/restrict if not required for approved storage/RPC use |
| 25/tcp | loopback only | `postfix master` | localhost-only | no LAN exposure observed |
| 85/tcp | loopback only | `pvedaemon` | localhost-only | no LAN exposure observed |
| 323/udp | loopback only | `chronyd` | localhost-only | no LAN exposure observed |
| 3128/tcp | all IPv4/IPv6 | `spiceproxy` | LAN-only or Tailscale-only | restrict to admin clients only |
| 8006/tcp | all IPv4/IPv6 | `pveproxy` | LAN-only or Tailscale-only | restrict to admin clients only |
| Local high port | `127.0.0.1` | local dev/editor process | localhost-only | no LAN exposure observed |

Connectivity check from Proxmox to the media gateway:

- `curl -I http://192.168.1.103:8088/health` returned HTTP `405 Method Not Allowed`, expected for `HEAD`.
- `curl http://192.168.1.103:8088/health` returned `{"status":"ok"}`.

System health:

- `systemctl --failed` reported `0 loaded units listed`.
- `pvesh get /nodes/$(hostname)/status` reported Proxmox `pve-manager/9.2.3`, kernel `7.0.6-2-pve`, EFI secure boot enabled, 6 CPU cores, and 32 GiB host RAM.

VM inventory:

- VM `100`: `ubuntu-docker`, running, 12288 MiB RAM, 124 GiB boot disk.
- VM `101`: `ubuntu-openclaw`, running, 12288 MiB RAM, 96 GiB boot disk.

VM `101` selected config:

- `name: ubuntu-openclaw`
- `cores: 2`
- `memory: 12288`
- `net0: virtio=BC:24:11:53:9D:88,bridge=vmbr0,firewall=1`
- No `ipconfig` line was present in the filtered output.
- Proxmox VM firewall is enabled for the OpenClaw VM network device.

Still needed before enforcement:

- Decide whether Proxmox enforcement should use Proxmox firewall, nftables, or another host-level mechanism. UFW is not present on this host.

## Boundary Classification

| Surface | Classification | Rationale |
| --- | --- | --- |
| Media host `127.0.0.1` dev/editor ports | localhost-only | loopback bind only |
| Media host SSH `22/tcp` | LAN-only or Tailscale-only | admin access only |
| Media host AdGuard DNS `53/tcp+udp` | LAN-only | DNS service for LAN clients |
| Media host Nginx Proxy Manager `80/tcp`, `443/tcp` | reverse-proxy-only | intended ingress to proxied apps |
| Media host NPM admin `81/tcp` | LAN-only or Tailscale-only | admin surface |
| Media host Authentik `9000/tcp`, `9443/tcp` | reverse-proxy-only | auth infrastructure; avoid broad direct access |
| Media host `openclaw-gateway` `8088/tcp` | OpenClaw-only | intended OpenClaw/media boundary |
| Media host n8n `5678/tcp` | should-not-be-exposed directly | route through proxy/auth or close direct host exposure |
| Media host Jellyfin `8096/tcp` | reverse-proxy-only or LAN-only | do not expose directly to OpenClaw in gateway-only model |
| Media host qBittorrent UI via gluetun `8080/tcp` | should-not-be-exposed directly | downloader admin UI |
| Media host NZBGet UI via gluetun `6789/tcp` | should-not-be-exposed directly | downloader admin UI |
| Media host AdGuard admin mappings `8090/tcp`, `3001/tcp` | LAN-only or Tailscale-only | admin surface |
| Media host rpcbind `111/tcp+udp` | should-not-be-exposed | no approved boundary need recorded |
| Media host internal Docker-only container ports | localhost/internal-only | no host publishing observed |
| Proxmox `8006/tcp` | LAN-only or Tailscale-only | hypervisor admin surface |
| Proxmox `3128/tcp` | should-not-be-exposed unless approved | observed by OPN-190 but not classified by repo policy |
| Proxmox `111/tcp` | should-not-be-exposed unless approved | observed by OPN-190 but not classified by repo policy |

## Draft Firewall Policy

All commands in this section are DRAFT ONLY - NOT APPLIED.

The confirmed OpenClaw LAN address is `192.168.1.16`.

Replace `<ADMIN_LAN_CIDR>` and `<TAILSCALE_CIDR>` with the operator-approved admin source ranges before enforcement. Based on current media evidence, likely candidate ranges are:

- `<ADMIN_LAN_CIDR>`: `192.168.1.0/24`
- `<TAILSCALE_CIDR>`: `100.64.0.0/10`

### Media Host Draft UFW Shape

```bash
# DRAFT ONLY - NOT APPLIED
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Preserve admin access first.
sudo ufw allow from <ADMIN_LAN_CIDR> to any port 22 proto tcp comment 'OPN-175 admin SSH from LAN'
sudo ufw allow from <TAILSCALE_CIDR> to any port 22 proto tcp comment 'OPN-175 admin SSH from Tailscale'

# Keep LAN DNS available only to LAN clients if this host is the LAN DNS server.
sudo ufw allow from 192.168.1.0/24 to any port 53 proto tcp comment 'OPN-175 AdGuard DNS TCP from LAN'
sudo ufw allow from 192.168.1.0/24 to any port 53 proto udp comment 'OPN-175 AdGuard DNS UDP from LAN'

# Keep proxy ingress available only on intended LAN/proxy boundary.
sudo ufw allow from 192.168.1.0/24 to any port 80 proto tcp comment 'OPN-175 NPM HTTP from LAN'
sudo ufw allow from 192.168.1.0/24 to any port 443 proto tcp comment 'OPN-175 NPM HTTPS from LAN'

# Restrict admin-only web UIs to trusted admin sources.
sudo ufw allow from <ADMIN_LAN_CIDR> to any port 81 proto tcp comment 'OPN-175 NPM admin from admin LAN'
sudo ufw allow from <TAILSCALE_CIDR> to any port 81 proto tcp comment 'OPN-175 NPM admin from Tailscale'
sudo ufw allow from <ADMIN_LAN_CIDR> to any port 8090 proto tcp comment 'OPN-175 AdGuard admin from admin LAN'
sudo ufw allow from <TAILSCALE_CIDR> to any port 8090 proto tcp comment 'OPN-175 AdGuard admin from Tailscale'
sudo ufw allow from <ADMIN_LAN_CIDR> to any port 3001 proto tcp comment 'OPN-175 AdGuard admin alt from admin LAN'
sudo ufw allow from <TAILSCALE_CIDR> to any port 3001 proto tcp comment 'OPN-175 AdGuard admin alt from Tailscale'

# Allow only OpenClaw to reach the media gateway.
sudo ufw allow from 192.168.1.16 to 192.168.1.103 port 8088 proto tcp comment 'OPN-175 OpenClaw to openclaw-gateway only'

# Optional: allow direct Jellyfin only if LAN direct access remains approved.
sudo ufw allow from 192.168.1.0/24 to any port 8096 proto tcp comment 'OPN-175 Jellyfin LAN direct if approved'

# Explicitly deny direct/admin surfaces that should be closed to non-approved clients.
sudo ufw deny 111/tcp comment 'OPN-175 deny rpcbind TCP'
sudo ufw deny 111/udp comment 'OPN-175 deny rpcbind UDP'
sudo ufw deny 5678/tcp comment 'OPN-175 deny direct n8n'
sudo ufw deny 6789/tcp comment 'OPN-175 deny direct NZBGet UI via gluetun'
sudo ufw deny 8080/tcp comment 'OPN-175 deny direct qBittorrent UI via gluetun'
sudo ufw deny 8088/tcp comment 'OPN-175 deny media gateway from non-OpenClaw sources'
sudo ufw deny 9000/tcp comment 'OPN-175 deny direct Authentik HTTP except explicit allows'
sudo ufw deny 9443/tcp comment 'OPN-175 deny direct Authentik HTTPS except explicit allows'
```

Important: UFW rule order matters. The `allow from 192.168.1.16 ... port 8088` rule must be before the general `deny 8088/tcp` rule. Confirm with `sudo ufw status numbered` before enforcement.

### Proxmox Host Draft Policy Shape

Proxmox does not have UFW installed. The following is not directly executable on the current Proxmox host unless UFW is deliberately installed in a separately approved change. Prefer a separate Proxmox firewall or nftables enforcement plan for this host.

```bash
# DRAFT ONLY - NOT APPLIED
sudo ufw default deny incoming
sudo ufw default allow outgoing

sudo ufw allow from <ADMIN_LAN_CIDR> to any port 22 proto tcp comment 'OPN-175 Proxmox SSH from admin LAN'
sudo ufw allow from <TAILSCALE_CIDR> to any port 22 proto tcp comment 'OPN-175 Proxmox SSH from Tailscale'
sudo ufw allow from <ADMIN_LAN_CIDR> to any port 8006 proto tcp comment 'OPN-175 Proxmox UI from admin LAN'
sudo ufw allow from <TAILSCALE_CIDR> to any port 8006 proto tcp comment 'OPN-175 Proxmox UI from Tailscale'

sudo ufw deny 111/tcp comment 'OPN-175 deny Proxmox rpcbind TCP unless approved'
sudo ufw deny 111/udp comment 'OPN-175 deny Proxmox rpcbind UDP unless approved'
sudo ufw deny 3128/tcp comment 'OPN-175 deny Proxmox 3128 unless approved'
```

### OpenClaw Ubuntu VM Draft UFW Shape

OpenClaw UFW is installed but currently inactive. These rules remain draft-only until an enforcement pass is explicitly approved.

```bash
# DRAFT ONLY - NOT APPLIED
sudo ufw default deny incoming
sudo ufw default allow outgoing

sudo ufw allow from <ADMIN_LAN_CIDR> to any port 22 proto tcp comment 'OPN-175 OpenClaw SSH from admin LAN'
sudo ufw allow from <TAILSCALE_CIDR> to any port 22 proto tcp comment 'OPN-175 OpenClaw SSH from Tailscale'

# If OpenClaw has only local app listeners, do not allow app ports inbound.
# If a reverse proxy must reach OpenClaw, add a narrow allow from the proxy host only:
sudo ufw allow from 192.168.1.103 to any port <OPENCLAW_PROXY_PORT> proto tcp comment 'OPN-175 proxy to OpenClaw service if approved'

# Egress rule shape if outbound filtering is enabled in a later pass:
sudo ufw allow out to 192.168.1.103 port 8088 proto tcp comment 'OPN-175 OpenClaw egress to media gateway'
```

## Rollback Commands

All commands in this section are DRAFT ONLY - NOT APPLIED.

Lowest-risk rollback before applying an enforcement packet:

```bash
sudo ufw status numbered
sudo ufw allow from <ADMIN_LAN_CIDR> to any port 22 proto tcp
sudo ufw allow from <TAILSCALE_CIDR> to any port 22 proto tcp
sudo ufw reload
sudo ufw status verbose
```

Rollback individual numbered rules:

```bash
sudo ufw status numbered
sudo ufw delete <RULE_NUMBER>
sudo ufw reload
sudo ufw status verbose
```

Emergency rollback to stop UFW filtering while preserving installed rules:

```bash
sudo ufw disable
sudo ufw status verbose
```

Do not run emergency rollback over SSH unless there is an alternate console path or Tailscale/admin access has been verified.

## Enforcement Approval Needed

Before any enforcement pass, get explicit approval for the exact commands and substitutions:

1. Confirm `<ADMIN_LAN_CIDR>` and whether Tailscale should be an allowed admin path.
2. Decide whether Proxmox enforcement should use Proxmox firewall, nftables, or another host-level mechanism. UFW is not present on Proxmox.
3. If using Proxmox firewall, draft explicit Proxmox firewall rules instead of UFW commands and account for `pve-firewall status` currently reporting `disabled/running`.
4. Confirm whether to enable UFW on media and OpenClaw during an enforcement pass, since both are currently `Status: inactive`.
5. Confirm whether direct LAN Jellyfin `8096/tcp` remains allowed or should be proxy-only.
6. Confirm whether Authentik direct `9000/tcp`/`9443/tcp` should be allowed from any source or proxy/admin-only.
7. Confirm whether Proxmox `111` and `3128` are expected or should be denied.
8. Run `sudo ufw status numbered` on media/OpenClaw before UFW enforcement so rule ordering and rollback numbers are known.

## Risks

- Media-host UFW is currently inactive, so Docker-published services are not being restricted by UFW on this host.
- Docker-published ports are broader than the intended gateway-only OpenClaw/media model.
- The live gateway is `openclaw-gateway` on `192.168.1.103:8088`; policies and docs should not refer to a deployed `media-api-gateway` container unless one is later created.
- Proxmox SSH from this workspace still has a host-key mismatch, but operator-provided Proxmox console evidence is now recorded.
- OpenClaw UFW is currently inactive, so OpenClaw inbound services are not being restricted by UFW on this host.
