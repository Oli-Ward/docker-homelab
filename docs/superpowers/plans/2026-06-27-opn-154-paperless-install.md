# OPN-154 Paperless-ngx Install Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dedicated `apps/docs` Paperless-ngx stack, document deployment/validation, and add a link-only Paperless entry to live Homepage config.

**Architecture:** Paperless runs as its own Komodo-managed Docker Compose stack with a Paperless web container, PostgreSQL database, Redis broker, Gotenberg, and Tika. Paperless web is reachable only through `proxy_net` and Nginx Proxy Manager; support services remain on an internal docs network. Durable app state, document media, consume, and export paths stay under `${APPDATA_ROOT}/paperless`.

**Tech Stack:** Docker Compose, Paperless-ngx `2.20.15`, PostgreSQL `18.4`, Redis `8.2.7`, Gotenberg `8.34.0`, Apache Tika `3.3.1.0-full`, Homepage YAML, Komodo deployment.

---

## Implementation Deviations

- PostgreSQL 18 uses `/var/lib/postgresql` as the container bind target in `apps/docs/compose.yml`; the original `/var/lib/postgresql/data` target caused fresh init failure.
- `/mnt/storage` was not mounted inside the media Ubuntu VM during validation, so Paperless media, consume, and export paths initially lived under `/data/configs/paperless`.
- OPN-158 later moved repo-managed mutable app state to `${APPDATA_ROOT}/paperless`. Live inspection on 2026-06-28 still showed the running Paperless containers mounted from `/data/configs/paperless`, so the stack needs an OPN-158 state copy and Komodo redeploy before live state matches current repo config.
- Long-term archive/off-host backup storage remains deferred to OPN-155 and the storage-mount follow-up.

## File Map

- Create `apps/docs/compose.yml`: Paperless stack definition with explicit container names, internal network, `proxy_net`, bind mounts, pinned image tags, and no host port publication.
- Create `apps/docs/example.env`: committed placeholder env file documenting required deployment variables only.
- Create `apps/docs/README.md`: short deployment, NPM/Auth, admin setup, manual export, validation, and rollback notes.
- Modify repo-managed `apps/utilities/homepage/services.yaml`: add a link-only `Documents > Paperless-ngx` entry.
- Modify repo-managed `apps/utilities/homepage/settings.yaml`: add `Documents` layout between `Download Management` and `System`.
- Keep `backups/homepage/*` untouched.
- Keep real `apps/docs/.env` untracked and do not create it in this plan.

## Sources Checked

- Paperless setup docs recommend Docker Compose templates, PostgreSQL for new installs, bind mount customization, reverse-proxy `PAPERLESS_URL`, timezone/OCR settings, and UID/GID mapping.
- Paperless release page shows `v2.20.15` as the latest stable release and `v3.0.0-beta.rc1` as a pre-release.
- Docker Hub shows current versioned tags for PostgreSQL, Redis, Gotenberg, and Apache Tika.

## Task 1: Add Docs Stack Compose

**Files:**
- Create: `apps/docs/compose.yml`

- [ ] **Step 1: Create `apps/docs/compose.yml`**

Use this exact compose content:

```yaml
services:
  paperless-broker:
    image: docker.io/library/redis:8.2.7
    container_name: paperless-broker
    restart: unless-stopped
    volumes:
      - ${APPDATA_ROOT}/paperless/redis:/data
    networks:
      - docs_net

  paperless-db:
    image: docker.io/library/postgres:18.4
    container_name: paperless-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${PAPERLESS_DBNAME}
      POSTGRES_USER: ${PAPERLESS_DBUSER}
      POSTGRES_PASSWORD: ${PAPERLESS_DBPASS}
    volumes:
      - ${APPDATA_ROOT}/paperless/postgres:/var/lib/postgresql
    networks:
      - docs_net

  paperless-gotenberg:
    image: docker.io/gotenberg/gotenberg:8.34.0
    container_name: paperless-gotenberg
    restart: unless-stopped
    command:
      - gotenberg
      - --chromium-disable-javascript=true
      - --chromium-allow-list=file:///tmp/.*
    networks:
      - docs_net

  paperless-tika:
    image: docker.io/apache/tika:3.3.1.0-full
    container_name: paperless-tika
    restart: unless-stopped
    networks:
      - docs_net

  paperless-webserver:
    image: ghcr.io/paperless-ngx/paperless-ngx:2.20.15
    container_name: paperless-webserver
    restart: unless-stopped
    depends_on:
      - paperless-broker
      - paperless-db
      - paperless-gotenberg
      - paperless-tika
    environment:
      USERMAP_UID: ${PUID}
      USERMAP_GID: ${PGID}
      PAPERLESS_REDIS: redis://paperless-broker:6379
      PAPERLESS_DBENGINE: postgresql
      PAPERLESS_DBHOST: paperless-db
      PAPERLESS_DBNAME: ${PAPERLESS_DBNAME}
      PAPERLESS_DBUSER: ${PAPERLESS_DBUSER}
      PAPERLESS_DBPASS: ${PAPERLESS_DBPASS}
      PAPERLESS_SECRET_KEY: ${PAPERLESS_SECRET_KEY}
      PAPERLESS_URL: ${PAPERLESS_URL}
      PAPERLESS_TIME_ZONE: ${TZ}
      PAPERLESS_OCR_LANGUAGE: eng
      PAPERLESS_TIKA_ENABLED: 1
      PAPERLESS_TIKA_GOTENBERG_ENDPOINT: http://paperless-gotenberg:3000
      PAPERLESS_TIKA_ENDPOINT: http://paperless-tika:9998
    volumes:
      - ${APPDATA_ROOT}/paperless/data:/usr/src/paperless/data
      - ${APPDATA_ROOT}/paperless/media:/usr/src/paperless/media
      - ${APPDATA_ROOT}/paperless/consume:/usr/src/paperless/consume
      - ${APPDATA_ROOT}/paperless/export:/usr/src/paperless/export
    networks:
      - docs_net
      - proxy_net

networks:
  docs_net:
  proxy_net:
    external: true
```

- [ ] **Step 2: Validate compose syntax with placeholder env values**

Run:

```bash
PUID=1000 PGID=1000 TZ=Pacific/Auckland DATA_ROOT=/data APPDATA_ROOT=/srv/appdata PAPERLESS_DBNAME=paperless PAPERLESS_DBUSER=paperless PAPERLESS_DBPASS=example-password PAPERLESS_SECRET_KEY=example-secret-key PAPERLESS_URL=https://paperless.home.lab docker compose -f apps/docs/compose.yml config
```

Expected: exit code `0`, rendered services for all five Paperless containers, no `ports:` section for `paperless-webserver`.

- [ ] **Step 3: Commit compose stack**

Run:

```bash
git add apps/docs/compose.yml
git commit -m "OPN-154: add Paperless docs compose stack"
```

Expected: commit succeeds and includes only `apps/docs/compose.yml`.

## Task 2: Add Docs Stack Env Example

**Files:**
- Create: `apps/docs/example.env`

- [ ] **Step 1: Create `apps/docs/example.env`**

Use this exact content:

```dotenv
# Copy to apps/docs/.env in Komodo and replace all secret values there.
# Do not commit the real .env file.

PUID=1000
PGID=1000
TZ=Pacific/Auckland
DATA_ROOT=/data
APPDATA_ROOT=/srv/appdata

PAPERLESS_URL=https://paperless.home.lab
PAPERLESS_DBNAME=paperless
PAPERLESS_DBUSER=paperless
PAPERLESS_DBPASS=replace-with-secure-database-password
PAPERLESS_SECRET_KEY=replace-with-output-of-python-secrets-token-urlsafe-64
```

- [ ] **Step 2: Verify no real secret values were added**

Run:

```bash
rg -n "api[_-]?key|token|password|secret" apps/docs/example.env
rg -n "replace-with" apps/docs/example.env
```

Expected: the first scan reports only placeholder variable names and placeholder values, and the second scan reports only the two `replace-with-*` placeholder lines. No concrete credential values should appear.

- [ ] **Step 3: Commit env example**

Run:

```bash
git add apps/docs/example.env
git commit -m "OPN-154: document Paperless env variables"
```

Expected: commit succeeds and includes only `apps/docs/example.env`.

## Task 3: Add Docs Stack README

**Files:**
- Create: `apps/docs/README.md`

- [ ] **Step 1: Create `apps/docs/README.md`**

Use this exact content:

```markdown
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
```

- [ ] **Step 2: Scan README for secrets**

Run:

```bash
rg -n "password|secret|token|key|api[_-]?key" apps/docs/README.md
```

Expected: only generic documentation references appear; no concrete secret values appear.

- [ ] **Step 3: Commit README**

Run:

```bash
git add apps/docs/README.md
git commit -m "OPN-154: document Paperless docs stack"
```

Expected: commit succeeds and includes only `apps/docs/README.md`.

## Task 4: Update Repo-Managed Homepage Config

**Files:**
- Modify: `apps/utilities/homepage/services.yaml`
- Modify: `apps/utilities/homepage/settings.yaml`

- [ ] **Step 1: Inspect the current repo-managed Homepage files**

Run:

```bash
sed -n '120,170p' apps/utilities/homepage/services.yaml
sed -n '20,40p' apps/utilities/homepage/settings.yaml
```

Expected: the `Download Management` and `System` sections are visible so `Documents` can be inserted between them.

- [ ] **Step 2: Add `Documents` service section**

Insert this section in `apps/utilities/homepage/services.yaml` after the `Download Management` section and before the `System` section:

```yaml
# Documents
- Documents:
    - Paperless-ngx:
        icon: paperless-ngx.png
        href: https://paperless.home.lab
        description: Documents
```

- [ ] **Step 3: Add `Documents` layout**

Insert this layout block in `apps/utilities/homepage/settings.yaml` after `Download Management` and before `System`:

```yaml
  Documents:
    style: row
    columns: 4
    icon: mdi-file-document
```

- [ ] **Step 4: Validate Homepage YAML parses**

Run:

```bash
python3 - <<'PY'
import yaml
for path in ['apps/utilities/homepage/services.yaml', 'apps/utilities/homepage/settings.yaml']:
    with open(path) as f:
        yaml.safe_load(f)
    print(f'{path}: ok')
PY
```

Expected: both files print `ok` and the command exits `0`.

- [ ] **Step 5: Verify no backup snapshot was touched**

Run:

```bash
git status --short apps/utilities/homepage backups
```

Expected: only intentional `apps/utilities/homepage` changes appear, and no tracked `backups/homepage/*` changes appear.

## Task 5: Final Repo Verification And Linear Update

**Files:**
- Check: `apps/docs/compose.yml`
- Check: `apps/docs/example.env`
- Check: `apps/docs/README.md`
- Check: `docs/superpowers/specs/2026-06-27-opn-154-paperless-install-design.md`
- Check: `docs/superpowers/plans/2026-06-27-opn-154-paperless-install.md`

- [ ] **Step 1: Run compose config verification**

Run:

```bash
PUID=1000 PGID=1000 TZ=Pacific/Auckland DATA_ROOT=/data APPDATA_ROOT=/srv/appdata PAPERLESS_DBNAME=paperless PAPERLESS_DBUSER=paperless PAPERLESS_DBPASS=example-password PAPERLESS_SECRET_KEY=example-secret-key PAPERLESS_URL=https://paperless.home.lab docker compose -f apps/docs/compose.yml config >/tmp/opn-154-compose-rendered.yml
```

Expected: exit code `0`.

- [ ] **Step 2: Verify no Paperless host port is published**

Run:

```bash
rg -n "ports:" /tmp/opn-154-compose-rendered.yml
```

Expected: no matches.

- [ ] **Step 3: Verify committed docs do not contain live secrets**

Run:

```bash
rg -n "tskey-api|BEGIN .*PRIVATE KEY|AKIA[0-9A-Z]{16}|openclaw-paperless-key" apps/docs
```

Expected: no matches.

- [ ] **Step 4: Check worktree state**

Run:

```bash
git status --short
```

Expected: only intentional uncommitted files remain. Commit `docs/superpowers/specs/2026-06-27-opn-154-paperless-install-design.md` and `docs/superpowers/plans/2026-06-27-opn-154-paperless-install.md` if they are still untracked.

- [ ] **Step 5: Move OPN-154 active and leave deployment notes**

Before deployment work starts, move OPN-154 to the workspace active state. Add a Linear comment with:

```text
Implementation plan written at docs/superpowers/plans/2026-06-27-opn-154-paperless-install.md.

Scope for this pass:
- Add apps/docs Paperless Compose stack.
- Document env/deploy/manual admin/export/rollback.
- Add live Homepage Documents link.

Deployment still requires Komodo, NPM, Authentik, manual admin creation, and upload/search smoke test.
```

- [ ] **Step 6: Stop before claiming OPN-154 done**

Do not mark OPN-154 complete until the manual deployment criteria in `apps/docs/README.md` have been performed:

- Komodo deploy succeeds.
- NPM route works.
- Authentik gates access.
- Paperless admin exists.
- Disposable document upload/search works.
- Persistence survives container recreation.
- Homepage link appears.
