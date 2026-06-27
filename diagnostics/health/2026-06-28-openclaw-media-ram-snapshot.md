# OpenClaw and Media RAM Snapshot: 2026-06-28

## Context

- Issue: `OPN-169`
- Captured at: `2026-06-28T08:43:54+12:00`
- Captured from: `media-homelab`
- Virtualization detected by guest: `kvm`
- Scope: real media Docker host data, with Proxmox and OpenClaw allocation still missing from this checkout/session.

## Allocation

### Media Docker Host

The media guest reports 11 GiB total RAM:

```text
Mem:            11Gi       6.0Gi       360Mi       425Mi       5.3Gi       4.9Gi
Swap:          2.9Gi       131Mi       2.8Gi
```

Docker reports memory accounting is enabled:

```text
Docker MemoryLimit=true NCPU=4 CgroupDriver=systemd CgroupVersion=2
```

Docker stats reported each container against a `5.706GiB` limit, while `free -h` reported `11GiB` total guest memory. Container inspection showed no explicit per-container memory limits:

```text
paperless-webserver Memory=0 MemorySwap=0 OomKillDisable=<nil>
paperless-db Memory=0 MemorySwap=0 OomKillDisable=<nil>
paperless-broker Memory=0 MemorySwap=0 OomKillDisable=<nil>
paperless-gotenberg Memory=0 MemorySwap=0 OomKillDisable=<nil>
paperless-tika Memory=0 MemorySwap=0 OomKillDisable=<nil>
speedtest-tracker Memory=0 MemorySwap=0 OomKillDisable=<nil>
n8n Memory=0 MemorySwap=0 OomKillDisable=<nil>
glances Memory=0 MemorySwap=0 OomKillDisable=<nil>
homepage Memory=0 MemorySwap=0 OomKillDisable=<nil>
nzbget Memory=0 MemorySwap=0 OomKillDisable=<nil>
qbittorrent Memory=0 MemorySwap=0 OomKillDisable=<nil>
bazarr Memory=0 MemorySwap=0 OomKillDisable=<nil>
sonarr Memory=0 MemorySwap=0 OomKillDisable=<nil>
radarr Memory=0 MemorySwap=0 OomKillDisable=<nil>
cleanuparr Memory=0 MemorySwap=0 OomKillDisable=<nil>
gluetun Memory=0 MemorySwap=0 OomKillDisable=<nil>
prowlarr Memory=0 MemorySwap=0 OomKillDisable=<nil>
jellyfin Memory=0 MemorySwap=0 OomKillDisable=<nil>
komodo-periphery-1 Memory=0 MemorySwap=0 OomKillDisable=<nil>
komodo-core-1 Memory=0 MemorySwap=0 OomKillDisable=<nil>
komodo-mongo-1 Memory=0 MemorySwap=0 OomKillDisable=<nil>
nginx-proxy-manager Memory=0 MemorySwap=0 OomKillDisable=<nil>
flaresolverr Memory=0 MemorySwap=0 OomKillDisable=<nil>
autoscan Memory=0 MemorySwap=0 OomKillDisable=<nil>
authentik-postgresql-1 Memory=0 MemorySwap=0 OomKillDisable=<nil>
adguard Memory=0 MemorySwap=0 OomKillDisable=<nil>
authentik-server Memory=0 MemorySwap=0 OomKillDisable=<nil>
jellyseerr Memory=0 MemorySwap=0 OomKillDisable=<nil>
authentik-worker-1 Memory=0 MemorySwap=0 OomKillDisable=<nil>
```

### Proxmox Host

Not captured in this session. `qm`, `pct`, and `pvesh` were not installed in the media guest:

```text
qm=
pct=
pvesh=
```

### OpenClaw Runtime

Not captured in this session. No OpenClaw host or Proxmox node output was available from the current shell.

## Current Usage

Media host uptime and load:

```text
08:43:55 up 18:12,  1 user,  load average: 0.69, 0.47, 0.45
```

Media host memory:

```text
Mem:            11Gi       6.0Gi       360Mi       425Mi       5.3Gi       4.9Gi
Swap:          2.9Gi       131Mi       2.8Gi
```

Short `vmstat` sample:

```text
procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----
 r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
10  2 134252 358384 276612 5279384    0    1  2015  2145   45  165  5  2 82 12  0
 0  0 134252 318744 276620 5329524    0    0 48256  7556 15612 34414 33 11 51  4  1
 0  0 134252 314020 276620 5329552    0    0     0   924 5017 8884  9  5 85  0  1
```

Container memory snapshot:

```text
NAME                     MEM USAGE / LIMIT     MEM %     CPU %
paperless-webserver      673.6MiB / 5.706GiB   11.53%    0.13%
paperless-db             52.8MiB / 5.706GiB    0.90%     0.00%
paperless-broker         15.85MiB / 5.706GiB   0.27%     0.22%
paperless-gotenberg      15.73MiB / 5.706GiB   0.27%     0.05%
paperless-tika           236.1MiB / 5.706GiB   4.04%     0.18%
speedtest-tracker        84.45MiB / 5.706GiB   1.45%     0.08%
n8n                      347.2MiB / 5.706GiB   5.94%     0.14%
glances                  92.01MiB / 5.706GiB   1.57%     1.03%
homepage                 104.5MiB / 5.706GiB   1.79%     0.00%
nzbget                   15.36MiB / 5.706GiB   0.26%     0.01%
qbittorrent              33.62MiB / 5.706GiB   0.58%     0.02%
bazarr                   241.8MiB / 5.706GiB   4.14%     0.12%
sonarr                   202MiB / 5.706GiB     3.46%     0.03%
radarr                   295.6MiB / 5.706GiB   5.06%     0.06%
cleanuparr               215.1MiB / 5.706GiB   3.68%     0.09%
gluetun                  116.5MiB / 5.706GiB   1.99%     0.02%
prowlarr                 173.4MiB / 5.706GiB   2.97%     0.04%
jellyfin                 419.6MiB / 5.706GiB   7.18%     0.01%
komodo-periphery-1       110.7MiB / 5.706GiB   1.90%     0.02%
komodo-core-1            80.78MiB / 5.706GiB   1.38%     0.23%
komodo-mongo-1           181.6MiB / 5.706GiB   3.11%     0.67%
nginx-proxy-manager      112.6MiB / 5.706GiB   1.93%     0.02%
flaresolverr             382.6MiB / 5.706GiB   6.55%     0.01%
autoscan                 43.73MiB / 5.706GiB   0.75%     0.01%
authentik-postgresql-1   255.8MiB / 5.706GiB   4.38%     0.01%
adguard                  68.33MiB / 5.706GiB   1.17%     0.01%
authentik-server         779MiB / 5.706GiB     13.33%    1.13%
jellyseerr               343.5MiB / 5.706GiB   5.88%     0.00%
authentik-worker-1       588.8MiB / 5.706GiB   10.08%    0.12%
```

## Pressure Signals

No kernel OOM or killed-process lines were found in the last 24 hours with:

```bash
journalctl -k --since '24 hours ago' --no-pager | rg -i 'out of memory|oom|memory allocation failure|killed process'
```

Swap is present but light in this snapshot: `131Mi` used out of `2.9Gi`.

The guest had `4.9Gi` available memory at capture time, which does not show immediate pressure. The `vmstat` sample included one interval with IO wait but did not show sustained swap-in or swap-out pressure.

## Notable Memory Consumers

Highest container memory usage in this snapshot:

- `authentik-server`: `779MiB`
- `paperless-webserver`: `673.6MiB`
- `authentik-worker-1`: `588.8MiB`
- `jellyfin`: `419.6MiB`
- `flaresolverr`: `382.6MiB`
- `n8n`: `347.2MiB`
- `jellyseerr`: `343.5MiB`
- `radarr`: `295.6MiB`
- `authentik-postgresql-1`: `255.8MiB`
- `bazarr`: `241.8MiB`

Highest host processes by RSS:

```text
USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
oli       213456  0.1  4.0 275243676 492920 ?    Ssl  Jun27   1:25 /usr/bin/jellyfin --ffmpeg=/usr/lib/jellyfin-ffmpeg/ffmpeg
oli       917337  8.1  3.9 27620700 485584 ?     Sl   08:41   0:11 /home/oli/.vscode-server/cli/servers/Stable-7e7950df89d055b5a378379db9ee14290772148a/server/node --dns-result-order=ipv4first /home/oli/.vscode-server/cli/servers/Stable-7e7950df89d055b5a378379db9ee14290772148a/server/out/bootstrap-fork --type=extensionHost --transformURIs --useHostProxy=false
oli       198196  0.8  2.8 1257424 343612 ?      Sl   Jun27   6:35 gunicorn: worker [authentik.root.asgi:application]
oli       214241  0.2  2.8 273105528 343208 ?    Ssl  Jun27   2:22 /app/radarr/bin/Radarr -nobrowser -data=/config
oli       634401  0.6  2.6 867156 321972 ?       Sl   03:04   2:07 gunicorn: worker [authentik.root.asgi:application]
oli       212831  0.3  2.5 274792860 308048 ?    Ssl  Jun27   2:26 ./Cleanuparr
oli       216584  0.1  2.4 27043040 297260 ?     Sl   Jun27   0:48 node /usr/local/bin/n8n
root      212736  0.2  2.4 21921104 293816 ?     Sl   Jun27   1:45 node dist/index.js
oli       197688  0.0  2.3 463172 281396 ?       Ssl  Jun27   0:17 python -m manage worker --pid-file /dev/shm//authentik-worker.pid
oli       198051  0.2  2.3 1127420 281236 ?      Sl   Jun27   1:45 python -m manage worker --pid-file /dev/shm//authentik-worker.pid
```

## Recommendation

Outcome: `monitor longer`

Confidence: `provisional`

Reasoning:

- The media Docker host does not show immediate RAM pressure in this snapshot.
- There is no captured evidence yet for OpenClaw allocation or OpenClaw runtime usage.
- Proxmox allocation was not visible from the media guest.
- Docker stats reported a lower memory denominator than the guest total, which should be checked from the host/cgroup configuration before making a reallocation decision.

Do not move RAM based on this snapshot alone. Capture Proxmox allocation and OpenClaw runtime usage, then repeat during a representative heavy workload.

## Remaining Evidence

Collect these before making a RAM reallocation:

- Proxmox `qm list` or `pct list` output for OpenClaw and media.
- Proxmox `qm config` or `pct config` output for both guests.
- OpenClaw `free -h`, `vmstat 1 5`, and top memory processes.
- At least one media snapshot while Jellyfin transcoding, Paperless OCR, or downloads are active.
- Explanation for the Docker stats `5.706GiB` memory limit versus the guest `11GiB` memory total.
