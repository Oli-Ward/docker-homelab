# Plane Stack

Plane Commercial Edition is managed as a Komodo-deployed Docker Compose stack.

## Paths

```text
${APPDATA_ROOT}/plane/data/db              PostgreSQL state
${APPDATA_ROOT}/plane/data/redis           Redis state
${APPDATA_ROOT}/plane/data/mq              RabbitMQ state
${APPDATA_ROOT}/plane/data/minio           MinIO object state
${APPDATA_ROOT}/plane/data/monitor         Plane monitor state
${APPDATA_ROOT}/plane/data/email           Email TLS/runtime state
${APPDATA_ROOT}/plane/caddy                Plane internal proxy state
${APPDATA_ROOT}/plane/logs                 Plane app logs
```

The previous installer layout used `/opt/plane` for both config and state. This repo keeps Compose config in `apps/plane` and mutable state under `${APPDATA_ROOT}/plane`, normally `/srv/appdata/plane`.

## Deployment

Deploy through Komodo using:

```text
apps/plane/compose.yml
```

Use a Komodo environment based on `apps/plane/example.env`. Do not commit the real `.env`; it contains database passwords, application secrets, storage credentials, and integration tokens.

The default deployment intentionally excludes optional services behind Compose profiles:

```text
email       profile: email
pi-*        profile: pi
```

With the default `.env`, Plane should run 18 services. Enable optional services later by setting `COMPOSE_PROFILES=pi,email` and changing their replica counts from `0` to the desired count.

The current NPM route can continue to forward to the host's Plane proxy port:

```text
https://plane.home.lab -> http://192.168.1.103:8085
```

The Plane proxy service also joins `proxy_net`, so a later NPM cleanup can point at Docker DNS instead:

```text
https://plane.home.lab -> http://plane-proxy:80
```

## Migration From `/opt/plane`

Before moving state, confirm a VM snapshot or appdata backup exists. Plane includes PostgreSQL, Redis, RabbitMQ, and MinIO state.

Stop the old Plane stack through Komodo before copying state. Do not run two Plane stacks against the same data.

Copy state into `${APPDATA_ROOT}`:

```bash
sudo install -d -m 0750 /srv/appdata/plane
sudo rsync -aHAX --numeric-ids --info=progress2 /opt/plane/data/ /srv/appdata/plane/data/
sudo rsync -aHAX --numeric-ids --info=progress2 /opt/plane/logs/ /srv/appdata/plane/logs/
sudo rsync -aHAX --numeric-ids --info=progress2 /opt/plane/caddy/ /srv/appdata/plane/caddy/
```

Then deploy this stack through Komodo and verify the new containers use `/srv/appdata/plane` mounts.

Leave `/opt/plane` intact as rollback material until the repo-managed stack has been validated.

## TLS And Login Checks

Plane is exposed publicly as:

```text
https://plane.home.lab
```

Route Plane through Nginx Proxy Manager to the Plane proxy upstream, but keep
the Plane app on its native authentication flow. Do not place Authentik
forward-auth in front of the Plane web app unless desktop login, iPhone login,
and API/token flows are all revalidated afterward.

The public app URL variables must not point at `http://plane.home.lab:8085`; that port is the plain-HTTP Plane proxy upstream and will fail if a browser tries HTTPS on it.

After deployment, verify the backend sees the public URL and trusts the homelab CA:

```bash
docker inspect plane-api-1 --format '{{range .Config.Env}}{{println .}}{{end}}' \
  | grep -E '^(WEB_URL|PI_BASE_URL|CORS_ALLOWED_ORIGINS|SSL_CERT_FILE|REQUESTS_CA_BUNDLE|NODE_EXTRA_CA_CERTS)='

docker exec plane-api-1 python - <<'PY'
import urllib.request
for url in ["https://auth.home.lab/", "https://plane.home.lab/"]:
    print("URL", url)
    with urllib.request.urlopen(url, timeout=5) as response:
        print("OK", response.status, response.url)
PY
```

Expected:

```text
WEB_URL=https://plane.home.lab
PI_BASE_URL=https://plane.home.lab/pi
CORS_ALLOWED_ORIGINS=https://plane.home.lab
```

The Python check should not fail with `CERTIFICATE_VERIFY_FAILED`.

## Backup And Restore Coverage

Plane state is not part of the general media appdata backup script. Treat it as
a dedicated restore lane because it combines PostgreSQL, Redis, RabbitMQ, MinIO,
monitor state, Caddy state, and app logs under `${APPDATA_ROOT}/plane`.

Before Plane upgrades, migration imports, or state moves, confirm one of these
exists:

```text
full VM snapshot/checkpoint
dedicated encrypted archive of ${APPDATA_ROOT}/plane
service-aware database/object-store backup with matching restore notes
```

For a file-level backup, stop or quiesce Plane through Komodo first so the
database, queue, cache, and object-store files are consistent. Record the exact
compose revision, image version, archive name, hash verification result, and
restore-test location. Do not restore over live `${APPDATA_ROOT}/plane` without
a maintenance plan.

## Rollback

If the repo-managed deployment fails:

1. Stop the repo-managed Plane stack through Komodo.
2. Re-enable the old `/opt/plane` deployment if it is still present.
3. Point NPM back to the previous working upstream if it was changed.
4. Leave `/srv/appdata/plane` in place until you decide whether to retry or remove it.

Do not delete `/opt/plane` or `/srv/appdata/plane` without a separate backup and cleanup decision.
