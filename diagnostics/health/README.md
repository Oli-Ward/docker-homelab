# Health Diagnostics

This directory holds repeatable, read-only operational checks for the homelab. It is evidence for decisions; it is not a deployment mechanism.

Do not start, stop, recreate, pull, prune, or update Docker resources while collecting these snapshots. Komodo remains the source of truth for deployment actions.

## Before/After Heavy Job Snapshot

Use `health-snapshot.sh` before heavy maintenance jobs where it would be useful to prove whether the job changed host health, Docker stability, disk pressure, RAM pressure, or recent system warnings.

Good candidates:

- storage migrations or large `rsync` runs
- Proxmox or VM backups
- media Docker updates deployed through Komodo
- large recommendation imports
- OpenClaw state map generation
- Headroom or skill routing evaluations
- Paperless imports, exports, and OCR-heavy batches

Run the script from the repository root and pass a short job slug plus the command to run after `--`:

```bash
diagnostics/health/health-snapshot.sh paperless-export -- paperless-exporter --help
diagnostics/health/health-snapshot.sh opn-177-dummy -- bash -lc 'printf "dummy job\n"; sleep 1'
```

The output path is:

```text
diagnostics/health/YYYY-MM-DD-<job>.md
```

Each report uses one combined file with these sections:

```text
# Health snapshot: <job>

## Before
## Command/job run
## After
## Diff / observations
## Recommendation / follow-up
```

The checks are read-only and intentionally omit secrets, full environment output, Docker inspect environment output, private keys, certificates, and full service logs. If a deeper follow-up is needed, capture it separately with a narrow command that is safe for the specific service.

The script supports both the OpenClaw VM and the media Docker host where possible:

- RAM, disk, uptime, process, failed systemd unit, and recent warning/error checks run on normal Linux guests.
- Docker checks run only when the Docker CLI is available and the daemon is reachable.
- `systemctl`, `journalctl`, `hostnamectl`, and virtualization checks are best effort, so reports include an explanatory note when a command is unavailable.
- The script does not deploy, restart, stop, pull, update, prune, or otherwise mutate Docker or systemd state.

## RAM Snapshot Workflow

Use this workflow when deciding whether RAM should be moved between OpenClaw and the media Docker host.

Capture at least three snapshots before reallocating RAM:

1. A quiet baseline after the hosts have been up for at least 30 minutes.
2. A normal-use snapshot while media services are active.
3. A pressure snapshot during the heaviest expected workload, such as Jellyfin transcoding, Paperless OCR, imports, indexer activity, or downloads.

Record exact timestamps, hostnames, and whether each command was run on the Proxmox node, the OpenClaw runtime host, or the media Docker host.

## Proxmox Allocation

Run on the Proxmox node. These commands show what RAM is assigned, not what is used inside each guest.

```bash
qm list
qm config <openclaw-vmid>
qm config <media-vmid>
pct list
pct config <openclaw-ctid>
pct config <media-ctid>
pvesh get /nodes/$(hostname)/qemu --output-format json
pvesh get /nodes/$(hostname)/lxc --output-format json
```

Evidence to record:

- OpenClaw VM or container ID.
- Media VM or container ID.
- Assigned memory for each guest.
- Ballooning settings, if enabled.
- Whether either guest has a hard cap, swap setting, or dynamic memory behavior.

## Guest Usage

Run on both the OpenClaw runtime host and the media Docker host.

```bash
date -Iseconds
hostnamectl --static 2>/dev/null || hostname
systemd-detect-virt 2>/dev/null || true
uptime
free -h
vmstat 1 5
ps aux --sort=-%mem | head -n 20
```

Evidence to record:

- Total RAM visible inside the guest.
- Used, free, buff/cache, available, and swap.
- Load average and CPU idle/wait from `vmstat`.
- Top memory-heavy processes.
- Whether the guest appears to be a VM, container, or bare-metal host.

## Docker Container Usage

Run on Docker hosts. These commands are read-only.

```bash
docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}'
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
docker info --format 'Docker MemoryLimit={{.MemoryLimit}} NCPU={{.NCPU}} CgroupDriver={{.CgroupDriver}} CgroupVersion={{.CgroupVersion}}'
docker inspect $(docker ps -q) --format '{{.Name}} Memory={{.HostConfig.Memory}} MemorySwap={{.HostConfig.MemorySwap}} OomKillDisable={{.HostConfig.OomKillDisable}}'
```

Evidence to record:

- Highest memory containers by absolute usage.
- Whether important services have explicit Docker memory limits.
- Whether Docker reports a memory limit lower than the guest total.
- Containers with unhealthy or recently restarted status.

Do not inspect or print container environment variables unless there is an explicit diagnostic need. Environment output can contain secrets.

## Pressure Signals

Run on each guest during the same snapshot window.

```bash
journalctl -k --since '24 hours ago' --no-pager | rg -i 'out of memory|oom|memory allocation failure|killed process'
```

Also record:

- Swap in/out from `vmstat`.
- Low `available` memory from `free -h`.
- Persistent IO wait during workloads.
- Container restarts, unhealthy statuses, or application logs that mention memory pressure.

## Recommendation Outcomes

Use one of these outcomes for each dated snapshot:

- `move RAM to OpenClaw`: OpenClaw shows sustained pressure and media has comfortable available memory across the same observation window.
- `move RAM to media`: media shows sustained pressure and OpenClaw has comfortable available memory across the same observation window.
- `leave allocation unchanged`: both sides have enough available memory and no pressure signals.
- `monitor longer`: evidence is real but too narrow, too quiet, or missing a representative workload.
- `blocked by missing evidence`: required host access or command output is unavailable.

Confidence levels:

- `high`: at least three snapshots across quiet, normal, and heavy workloads, with Proxmox allocation and both guest usage records.
- `medium`: at least two useful snapshots and no contradictory pressure signals.
- `provisional`: a single snapshot or a snapshot missing one side of the comparison.
