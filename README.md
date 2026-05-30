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
* qBittorrent – Torrents
* NZBGet – Usenet

### Management

* Sonarr – TV
* Radarr – Movies
* Prowlarr – Indexers
* Bazarr – Subtitles

### Utilities

* Cleanuparr – Cleanup automation
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
* `request.home.lab`
* `cleanup.home.lab`
* `torrent.home.lab`
* `usenet.home.lab`
* `speedtest.home.lab`

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

## ⚠️ Notes

* Do **not** proxy apps like Sonarr directly — always via Authentik
* Use internal URLs for widgets to avoid SSL/auth issues
* Glances runs in `host` mode → accessed via host IP

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
