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

  * Used for supported apps (e.g. Cleanuparr, Jellyseerr)

---

## 📦 Services

### Media

* Jellyfin – Media server
* Jellyseerr – Requests
* Ryot – Media tracker
* qBittorrent – Torrents
* NZBGet – Usenet

### Management

* Sonarr – TV
* Radarr – Movies
* Prowlarr – Indexers
* Bazarr – Subtitles

### Utilities

* Cleanuparr – Cleanup automation
* n8n – Workflow automation
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
* `jellyseerr.home.lab`
* `ryot.home.lab`
* `cleanup.home.lab`
* `torrent.home.lab`
* `usenet.home.lab`
* `speedtest.home.lab`
* `n8n.home.lab`

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
* Use internal URLs for widgets to avoid SSL/auth issues
* Glances runs in `host` mode → accessed via host IP

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
