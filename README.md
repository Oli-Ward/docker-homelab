# 🏠 Home Lab Stack

A self-hosted media and automation stack with centralized authentication, reverse proxy routing, and service dashboard.

---

## 🔧 Core Components

* **Authentik** – Authentication (Proxy + OIDC)
* **Nginx Proxy Manager** – Reverse proxy + SSL
* **Docker + Komodo** – Container orchestration

---

## 🌐 Architecture

```text
DNS (*.home.lab)
      ↓
Nginx Proxy Manager
      ↓
Authentik (Auth Layer)
      ↓
Services (Sonarr, Radarr, etc.)
```

---

## 🔐 Authentication

* **Proxy Auth (Authentik)**

  * Used for apps without native auth (e.g. Sonarr, Radarr)
* **OIDC**

  * Used for supported apps with native login flow (e.g. Cleanuparr, Seerr)

---

## 📦 Services

### Media

* Jellyfin – Media server
* Seerr – Requests via Authentik OIDC
* Ryot – Media tracker
* qBittorrent – Torrents
* NZBGet – Usenet
* Tdarr – Media health checks and transcoding evaluation

### Management

* Sonarr – TV
* Radarr – Movies
* Prowlarr – Indexers
* Bazarr – Subtitles
* Maintainerr – Watched media cleanup
* Seekarr – Repeat-search automation helper (internal, dry-run first)
* Mediastarr – Missing-content/quality-upgrade helper
* Recyclarr – Sonarr/Radarr quality profile and format sync

### Utilities

* Cleanuparr – Cleanup automation
* n8n – Workflow automation
* Backrest – Restic backup management
* Glances – System metrics
* Speedtest Tracker – Network monitoring
* File Browser – File access

---

## 🌍 Domains

All services are exposed via:

```text
https://<service>.home.lab
```

Examples:

* `sonarr.home.lab`
* `radarr.home.lab`
* `seerr.home.lab`
* `ryot.home.lab`
* `cleanup.home.lab`
* `torrent.home.lab`
* `usenet.home.lab`
* `speedtest.home.lab`
* `mediastarr.home.lab`
* `n8n.home.lab`
* `maintainerr.home.lab`

---

## 🧠 Networking

* Internal communication uses **Docker service names**

  ```text
  http://sonarr:8989
  http://radarr:7878
  ```
* External access uses **NPM + domains**

  ```text
  https://sonarr.home.lab
  ```

---

## 🔒 SSL

* Internal CA used for `*.home.lab`
* Certificates mounted into containers where required
* Containers updated with:

  ```bash
  update-ca-certificates
  ```

---

## 💾 Storage Roots

`DATA_ROOT` is for user data:

* media libraries under `${DATA_ROOT}/media/...`
* downloads under `${DATA_ROOT}/downloads`
* photos under `${DATA_ROOT}/media/Photos`
* broad read-only browsing mounts, such as Homepage's `/data` view

`APPDATA_ROOT` is for mutable container app state:

* service config directories
* databases and generated state
* cookies, queues, caches, and certificate/config state

Recommended values:

```env
DATA_ROOT=/data
APPDATA_ROOT=/srv/appdata
```

Homepage is the deliberate exception. Its selected safe dashboard config is repo-managed under `apps/utilities/homepage` and mounted into the container with `./homepage:/app/config`; real widget secrets stay in the untracked stack `.env`.

Manual encrypted appdata/config backups are documented in [`docs/backup/media-appdata.md`](docs/backup/media-appdata.md). This is a manual-first workflow and does not replace full VM backups.

---

## ⚠️ Notes

* Do **not** proxy apps like Sonarr directly — always via Authentik
* Maintainerr must be exposed through Nginx Proxy Manager and protected by Authentik proxy auth before browser use
* Use internal URLs for widgets to avoid SSL/auth issues
* Backrest must start with config/appdata scope only; do not enable media-volume backups in the first rollout.
* Glances runs in `host` mode → accessed via host IP
* Mediastarr is exposed via `https://mediastarr.home.lab` with Nginx Proxy Manager and Authentik proxy auth.
* Tdarr must start with the dedicated test library and no full-library bulk transcode until resource usage and output safety are proven.
* Recyclarr is an internal scheduled/CLI service only; do not expose it through Nginx Proxy Manager or Authentik.

---

## 🩺 RAM Diagnostics

RAM allocation and usage snapshots live under [`diagnostics/health`](diagnostics/health/README.md).

Current snapshot:

* [`2026-06-28-openclaw-media-ram-snapshot.md`](diagnostics/health/2026-06-28-openclaw-media-ram-snapshot.md)

---

## 🚀 Status

✅ Fully functional
✅ Auth + Proxy + OIDC working
✅ Dashboard + widgets configured

---

## 📌 Future Improvements

* Centralized logging (Loki)
* Automated backups
* Expand OIDC coverage

---
