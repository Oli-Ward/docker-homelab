# Plane Home Lab Access Implementation Plan

> **Archived 2026-07-12:** This plan is stale after review against Linear OPN-264. OPN-264 is now an umbrella/cutover-readiness ticket; Plane install, access, and live readiness work lives in child tickets and diagnostics. Keep this file as historical implementation context, not as an active plan.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the existing Plane Commercial Edition install at `https://plane.home.lab`, keep Plane-native login working for desktop/mobile/API use, and add it to Homepage.

**Architecture:** Keep Plane's installer-managed Docker stack intact. Route Nginx Proxy Manager to Plane's current host-published HTTP port and do not place Authentik proxy auth in front of Plane unless desktop login, iPhone login, and API/token flows are revalidated afterward. Track only the Homepage dashboard entry in Git.

**Tech Stack:** Nginx Proxy Manager, Authentik embedded outpost proxy provider, Homepage YAML, Docker read-only inspection, curl verification.

## Global Constraints

- Do not run `docker compose up`, `docker compose down`, `docker compose pull`, or restart containers directly.
- Do not commit `.env` files, secrets, certificates, private keys, runtime state, database files, logs, or session history.
- External access flows through DNS, Nginx Proxy Manager, then Authentik where required.
- Homepage safe dashboard config is repo-managed under `apps/utilities/homepage`.
- Validate with non-deploying checks and live readbacks only.

---

### Task 1: Confirm Live Plane Target And Auth Pattern

**Files:**
- Read: running Docker container/network metadata.
- Read: Nginx Proxy Manager route metadata.

**Interfaces:**
- Consumes: existing Plane stack already running.
- Produces: selected proxy target `http://192.168.1.103:8085` and a Plane-native auth decision.

- [ ] **Step 1: Confirm Plane target**

Run:

```bash
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Networks}}\t{{.Ports}}' | rg -i 'plane|nginx|authentik'
curl -k -sS -o /dev/null -D - http://127.0.0.1:8085/ | sed -n '1,20p'
```

Expected: Plane proxy is running, HTTP on host port `8085` returns `HTTP/1.1 200 OK`.

- [ ] **Step 2: Confirm no Plane forward-auth requirement**

Check the Plane NPM proxy host configuration without printing secrets.

Expected: `https://plane.home.lab` returns the Plane app directly and does not redirect unauthenticated users to Authentik. Keep this behavior unless mobile login and API/token flows are revalidated with Authentik in front.

### Task 2: Add Plane To NPM

**Files:**
- Modify live external UI state: Nginx Proxy Manager proxy host.

**Interfaces:**
- Consumes: Plane upstream on `http://192.168.1.103:8085`.
- Produces: `plane.home.lab` proxy host returning the Plane app through homelab TLS.

- [ ] **Step 1: Create or update NPM proxy host**

Create idempotently:

```text
Domain: plane.home.lab
Forward hostname/IP: 192.168.1.103
Forward port: 8085
Scheme: http
SSL: existing home.lab certificate if available
Custom Nginx: no Authentik auth_request snippet unless native/mobile/API flows have been revalidated
```

Expected: NPM has one enabled proxy host for `plane.home.lab`.

### Task 3: Add Homepage Card And Verify

**Files:**
- Modify: `apps/utilities/homepage/services.yaml`

**Interfaces:**
- Consumes: `https://plane.home.lab`.
- Produces: Homepage `System > Plane` card.

- [ ] **Step 1: Add Homepage card**

Add under `System`:

```yaml
    - Plane:
        icon: mdi-airplane
        href: https://plane.home.lab
        description: Issue Tracker
        siteMonitor: https://plane.home.lab
```

Expected: YAML parses and Homepage has a visible Plane link after its normal config reload/redeploy path.

- [ ] **Step 2: Verify**

Run:

```bash
python3 - <<'PY'
import yaml
with open('homepage/services.yaml', 'r', encoding='utf-8') as f:
    yaml.safe_load(f)
PY
curl -k -sS -o /dev/null -D - https://plane.home.lab/ | sed -n '1,30p'
```

Expected: YAML parse exits 0; unauthenticated HTTPS request returns the Plane app over NPM/TLS.
