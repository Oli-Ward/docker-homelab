# Docs Stack

Paperless-ngx runs here as the current document-management service.

## Services

- `paperless-webserver` - Paperless UI/API
- `paperless-db` - PostgreSQL database
- `paperless-broker` - Redis broker
- `paperless-gotenberg` - document conversion helper
- `paperless-tika` - text extraction helper

## Paths

```text
${APPDATA_ROOT}/paperless/data        Paperless app data
${APPDATA_ROOT}/paperless/postgres    PostgreSQL state
${APPDATA_ROOT}/paperless/redis       Redis state
${APPDATA_ROOT}/paperless/media       Paperless-managed live document media
${APPDATA_ROOT}/paperless/consume     Consume drop zone
${APPDATA_ROOT}/paperless/export      Manual export output
```

Do not manually edit files in the live Paperless media directory. Use Paperless, exports, or the future gateway path.

Paperless state now belongs under `${APPDATA_ROOT}/paperless`. Before redeploying this stack with the new path, copy the existing `/data/configs/paperless` tree to the configured app-state root and confirm backups/checkpoints exist.

## Deployment

Deploy this stack through Komodo using `apps/docs/compose.yml` and an untracked `apps/docs/.env` based on `example.env`.

Generate `PAPERLESS_SECRET_KEY` outside Git:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Create the host directories before first deploy if Komodo does not create them:

```bash
mkdir -p /srv/appdata/paperless/{data,postgres,redis,media,consume,export}
```

## Access

Nginx Proxy Manager should route:

```text
https://paperless.home.lab -> http://paperless-webserver:8000
```

Paperless should not publish a host port. Put Authentik Proxy Auth in front of the NPM route and keep Paperless local auth enabled.

Create the initial Paperless admin user manually after deployment. Do not store admin credentials in this repository.

## Gateway Token

If a Paperless API token is created for later automation, store it outside Git as the gateway-owned secret. OpenClaw should use the separate gateway path, not direct Paperless credentials or filesystem access.

## Manual Export

Manual export target:

```text
${APPDATA_ROOT}/paperless/export
```

Run an export from the deployed stack when needed:

```bash
docker compose -f apps/docs/compose.yml exec paperless-webserver document_exporter /usr/src/paperless/export
```

Scheduled exports, PostgreSQL backups, retention, and restore verification are tracked by OPN-155.

## Smoke Test

Before relying on the instance:

1. Open `https://paperless.home.lab`.
2. Confirm Authentik gates access before Paperless local auth.
3. Sign in with the manually created Paperless admin.
4. Upload a disposable sample document.
5. Confirm the document is processed and searchable.
6. Recreate the Paperless web container and confirm the document remains available.
7. Confirm Homepage shows `Documents > Paperless-ngx`.

## Rollback

Normal rollback preserves data:

1. Stop/remove the docs stack in Komodo.
2. Remove or disable the NPM proxy host.
3. Remove or disable Authentik wiring for Paperless.
4. Remove the Homepage `Documents` entry if desired.
5. Leave Paperless app-state, database, media, consume, and export directories intact.

Destructive cleanup of Paperless directories must be a separate explicit action.
