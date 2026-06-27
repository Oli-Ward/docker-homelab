# OPN-169 RAM Snapshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a repeatable, read-only RAM measurement workflow for comparing Proxmox allocation, OpenClaw runtime allocation, and media Docker host usage.

**Architecture:** Keep the workflow as documentation because this issue is observational and should not mutate live Docker or Proxmox state. Store reusable commands in `diagnostics/health/README.md` and dated evidence in `diagnostics/health/YYYY-MM-DD-openclaw-media-ram-snapshot.md`.

**Tech Stack:** Markdown, Linux read-only inspection commands, Docker read-only inspection commands, optional Proxmox CLI commands.

---

### Task 1: Add RAM Measurement Command Pack

**Files:**
- Create: `diagnostics/health/README.md`

- [x] **Step 1: Document the read-only collection workflow**

Create `diagnostics/health/README.md` with command groups for Proxmox allocation, OpenClaw runtime usage, media Docker host usage, container memory usage, pressure signals, and recommendation outcomes.

- [x] **Step 2: Include exact commands**

Include these commands in the document:

```bash
qm list
qm config <vmid>
pct list
pct config <ctid>
pvesh get /nodes/$(hostname)/qemu --output-format json
free -h
uptime
vmstat 1 5
ps aux --sort=-%mem | head -n 20
docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}'
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
journalctl -k --since '24 hours ago' --no-pager
```

- [x] **Step 3: Define recommendation outcomes**

Use these final states: `move RAM to OpenClaw`, `move RAM to media`, `leave allocation unchanged`, `monitor longer`, and `blocked by missing evidence`.

### Task 2: Add First Dated Snapshot

**Files:**
- Create: `diagnostics/health/2026-06-28-openclaw-media-ram-snapshot.md`

- [x] **Step 1: Capture media host evidence**

Run read-only commands on the media Docker host:

```bash
date -Iseconds
hostnamectl --static
systemd-detect-virt
uptime
free -h
docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}'
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
ps aux --sort=-%mem | head -n 16
docker info --format 'Docker MemoryLimit={{.MemoryLimit}} NCPU={{.NCPU}} CgroupDriver={{.CgroupDriver}} CgroupVersion={{.CgroupVersion}}'
docker inspect $(docker ps -q) --format '{{.Name}} Memory={{.HostConfig.Memory}} MemorySwap={{.HostConfig.MemorySwap}} OomKillDisable={{.HostConfig.OomKillDisable}}'
journalctl -k --since '24 hours ago' --no-pager
```

- [x] **Step 2: Record inaccessible evidence explicitly**

Record that `qm`, `pct`, and `pvesh` are unavailable in the media guest, so Proxmox allocation and OpenClaw allocation still need to be captured from the Proxmox node or OpenClaw host.

- [x] **Step 3: Add recommendation**

Use `monitor longer` with `provisional` confidence because the snapshot has real media-host data but lacks Proxmox and OpenClaw allocation evidence.

### Task 3: Link Diagnostics From README

**Files:**
- Modify: `README.md`

- [x] **Step 1: Add a short diagnostics section**

Add a concise section pointing to the RAM snapshot workflow and current snapshot so operators can find the evidence without reading Linear.

### Task 4: Verify Documentation

**Files:**
- Check: `diagnostics/health/README.md`
- Check: `diagnostics/health/2026-06-28-openclaw-media-ram-snapshot.md`
- Check: `README.md`

- [x] **Step 1: Verify required commands are documented**

Run:

```bash
rg -n "qm list|qm config|pvesh get|free -h|vmstat 1|docker stats --no-stream|docker ps --format|journalctl -k" diagnostics/health/README.md
```

Expected: every required command appears.

- [x] **Step 2: Verify snapshot sections exist**

Run:

```bash
rg -n "## Allocation|## Current Usage|## Pressure Signals|## Notable Memory Consumers|## Recommendation|## Remaining Evidence" diagnostics/health/2026-06-28-openclaw-media-ram-snapshot.md
```

Expected: every required section appears.

- [x] **Step 3: Verify README links diagnostics**

Run:

```bash
rg -n "RAM Diagnostics|diagnostics/health" README.md
```

Expected: README links the diagnostics command pack and dated snapshot.
