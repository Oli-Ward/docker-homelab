# OPN-158 Appdata Root Migration Checklist

This is the operator checklist for moving mutable container app state from `/data/configs` to `APPDATA_ROOT`, recommended as `/srv/appdata`.

Do not delete old `/data/configs/...` directories during the first migration. Keep them as rollback until each stack has redeployed through Komodo and passed smoke checks.

## Scope

Keep these paths on `DATA_ROOT`:

```text
${DATA_ROOT}/media/...
${DATA_ROOT}/downloads
${DATA_ROOT}/media/Photos
```

Move mutable app state to `APPDATA_ROOT`:

```text
${APPDATA_ROOT}/<service>
```

Deliberate exception:

```text
apps/utilities/homepage -> /app/config
```

Homepage dashboard config is repo-managed. Homepage widget secrets remain in the untracked `apps/utilities/.env`.

## Before Any Stack Migration

1. Confirm a current backup or checkpoint exists for the stack being migrated.
2. Confirm the stack is not doing critical work.
3. Confirm the target root exists:

```bash
sudo install -d -m 0750 /srv/appdata
```

4. Copy state before changing or redeploying the stack:

```bash
sudo install -d -m 0750 /srv/appdata/<service>
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/<service>/ /srv/appdata/<service>/
sudo find /srv/appdata/<service> -maxdepth 1 -ls
```

5. Compare ownership and permissions with the original source:

```bash
sudo find /data/configs/<service> -maxdepth 1 -ls
sudo find /srv/appdata/<service> -maxdepth 1 -ls
```

6. Validate compose rendering with non-secret placeholders before redeploying:

```bash
env PUID=1000 PGID=1000 TZ=Pacific/Auckland DATA_ROOT=/data APPDATA_ROOT=/srv/appdata docker compose -f <stack>/compose.yml config >/tmp/<stack>-opn-158.yml
```

7. Redeploy only the affected stack through Komodo.
8. Smoke-test the service UI/API and any dependent Homepage widgets.
9. Leave the old `/data/configs/<service>` directory in place until rollback is no longer needed.

## Stack Copy Map

### apps/utilities

High-risk services: Speedtest Tracker and n8n. iCloudPD stores auth cookies under its config directory.

```bash
sudo install -d -m 0750 /srv/appdata/glances /srv/appdata/icloudpd /srv/appdata/speedtest-tracker /srv/appdata/n8n
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/glances/ /srv/appdata/glances/
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/icloudpd/ /srv/appdata/icloudpd/
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/speedtest-tracker/ /srv/appdata/speedtest-tracker/
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/n8n/ /srv/appdata/n8n/
```

Do not copy Homepage from `/data/configs/homepage` for this ticket. Homepage config is repo-managed under `apps/utilities/homepage`.

### apps/arr-stack

High-risk services: Radarr, Sonarr, Prowlarr, Bazarr, and Cleanuparr.

```bash
sudo install -d -m 0750 /srv/appdata/radarr /srv/appdata/sonarr /srv/appdata/prowlarr /srv/appdata/bazarr /srv/appdata/autoscan /srv/appdata/cleanuparr
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/radarr/ /srv/appdata/radarr/
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/sonarr/ /srv/appdata/sonarr/
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/prowlarr/ /srv/appdata/prowlarr/
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/bazarr/ /srv/appdata/bazarr/
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/autoscan/ /srv/appdata/autoscan/
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/cleanuparr/ /srv/appdata/cleanuparr/
```

### apps/media

High-risk services: Jellyfin and Jellyseerr.

```bash
sudo install -d -m 0750 /srv/appdata/jellyfin /srv/appdata/jellyseerr
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/jellyfin/ /srv/appdata/jellyfin/
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/jellyseerr/ /srv/appdata/jellyseerr/
```

### apps/downloads

High-risk services: qBittorrent, NZBGet, and Gluetun.

```bash
sudo install -d -m 0750 /srv/appdata/qbittorrent /srv/appdata/nzbget /srv/appdata/flaresolverr /srv/appdata/gluetun
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/qbittorrent/ /srv/appdata/qbittorrent/
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/nzbget/ /srv/appdata/nzbget/
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/flaresolverr/ /srv/appdata/flaresolverr/
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/gluetun/ /srv/appdata/gluetun/
```

### apps/docs

High-risk services: Paperless, PostgreSQL, and Redis.

```bash
sudo install -d -m 0750 /srv/appdata/paperless/{data,postgres,redis,media,consume,export}
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/paperless/data/ /srv/appdata/paperless/data/
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/paperless/postgres/ /srv/appdata/paperless/postgres/
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/paperless/redis/ /srv/appdata/paperless/redis/
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/paperless/media/ /srv/appdata/paperless/media/
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/paperless/consume/ /srv/appdata/paperless/consume/
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/paperless/export/ /srv/appdata/paperless/export/
```

### infra/proxy/nginx-proxy-manager

High-risk service: Nginx Proxy Manager. The LetsEncrypt directory may contain certificate material.

```bash
sudo install -d -m 0750 /srv/appdata/nginx-proxy-manager/{data,letsencrypt}
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/nginx-proxy-manager/data/ /srv/appdata/nginx-proxy-manager/data/
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/nginx-proxy-manager/letsencrypt/ /srv/appdata/nginx-proxy-manager/letsencrypt/
```

### infra/dns/adguard

High-risk service: AdGuard Home DNS.

```bash
sudo install -d -m 0750 /srv/appdata/adguard/{work,conf}
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/adguard/work/ /srv/appdata/adguard/work/
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/adguard/conf/ /srv/appdata/adguard/conf/
```

### identity/authentik

High-risk service: Authentik and PostgreSQL.

No `/data/configs` mount is changed by this ticket. Authentik currently uses a named PostgreSQL volume and repo-relative `./data`, `./certs`, and `./custom-templates` mounts. Treat Authentik as high risk for backup planning, but do not migrate it under `APPDATA_ROOT` without a separate issue.

## Rollback

1. Revert the affected compose file to the previous mount path, or deploy the previous Git commit through Komodo.
2. Redeploy only the affected stack through Komodo.
3. Confirm the service sees the original `/data/configs/<service>` state.
4. Keep `/srv/appdata/<service>` intact until you have inspected any writes made during the attempted migration.

Do not remove either old or new state directories as part of rollback unless a separate destructive cleanup has been explicitly approved.
