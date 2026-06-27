# OPN-154 Paperless-ngx Install Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dedicated `apps/docs` Paperless-ngx stack, document deployment/validation, and add a link-only Paperless entry to live Homepage config.

**Architecture:** Paperless runs as its own Komodo-managed Docker Compose stack with a Paperless web container, PostgreSQL database, Redis broker, Gotenberg, and Tika. Paperless web is reachable only through `proxy_net` and Nginx Proxy Manager; support services remain on an internal docs network. Durable app state stays under `${DATA_ROOT}/configs/paperless`, while document media/consume/export paths bind to long-term storage.

**Tech Stack:** Docker Compose, Paperless-ngx `2.20.15`, PostgreSQL `18.4`, Redis `8.2.7`, Gotenberg `8.34.0`, Apache Tika `3.3.1.0-full`, Homepage YAML, Komodo deployment.

---

## File Map

- Create `apps/docs/compose.yml`: Paperless stack definition with explicit container names, internal network, `proxy_net`, bind mounts, pinned image tags, and no host port publication.
- Create `apps/docs/example.env`: committed placeholder env file documenting required deployment variables only.
- Create `apps/docs/README.md`: short deployment, NPM/Auth, admin setup, manual export, validation, and rollback notes.
- Modify live `/data/configs/homepage/services.yaml`: add a link-only `Documents > Paperless-ngx` entry.
- Modify live `/data/configs/homepage/settings.yaml`: add `Documents` layout between `Download Management` and `System`.
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
      - ${DATA_ROOT}/configs/paperless/redis:/data
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
      - ${DATA_ROOT}/configs/paperless/postgres:/var/lib/postgresql/data
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
      - ${DATA_ROOT}/configs/paperless/data:/usr/src/paperless/data
      - /mnt/storage/01_Documents/paperless/media:/usr/src/paperless/media
      - /mnt/storage/01_Documents/paperless/consume:/usr/src/paperless/consume
      - /mnt/storage/05_Backups/paperless/export:/usr/src/paperless/export
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
PUID=1000 PGID=1000 TZ=Pacific/Auckland DATA_ROOT=/data PAPERLESS_DBNAME=paperless PAPERLESS_DBUSER=paperless PAPERLESS_DBPASS=example-password PAPERLESS_SECRET_KEY=example-secret-key PAPERLESS_URL=https://paperless.home.lab docker compose -f apps/docs/compose.yml config
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
${DATA_ROOT}/configs/paperless/data       Paperless app data
${DATA_ROOT}/configs/paperless/postgres   PostgreSQL state
${DATA_ROOT}/configs/paperless/redis      Redis state
/mnt/storage/01_Documents/paperless/media Paperless-managed live document media
/mnt/storage/01_Documents/paperless/consume Consume drop zone
/mnt/storage/05_Backups/paperless/export  Manual export output
```

Do not manually edit files in the live media directory. Use Paperless, exports, or the future gateway path.

## Deployment

Deploy this stack through Komodo using `apps/docs/compose.yml` and an untracked `apps/docs/.env` based on `example.env`.

Generate `PAPERLESS_SECRET_KEY` outside Git:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Create the host directories before first deploy if Komodo does not create them:

```bash
mkdir -p /data/configs/paperless/{data,postgres,redis}
mkdir -p /mnt/storage/01_Documents/paperless/{media,consume}
mkdir -p /mnt/storage/05_Backups/paperless/export
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
/mnt/storage/05_Backups/paperless/export
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
5. Leave Paperless config, database, media, consume, and export directories intact.

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

## Task 4: Update Live Homepage Config

**Files:**
- Modify: `/data/configs/homepage/services.yaml`
- Modify: `/data/configs/homepage/settings.yaml`

- [ ] **Step 1: Back up live Homepage files to `/tmp`**

Run:

```bash
cp /data/configs/homepage/services.yaml /tmp/homepage-services.yaml.opn-154.bak
cp /data/configs/homepage/settings.yaml /tmp/homepage-settings.yaml.opn-154.bak
```

Expected: both backup files exist under `/tmp`.

- [ ] **Step 2: Add `Documents` service section**

Insert this section in `/data/configs/homepage/services.yaml` after the `Download Management` section and before the `System` section:

```yaml
# Documents
- Documents:
    - Paperless-ngx:
        icon: paperless-ngx.png
        href: https://paperless.home.lab
        description: Documents
```

- [ ] **Step 3: Add `Documents` layout**

Insert this layout block in `/data/configs/homepage/settings.yaml` after `Download Management` and before `System`:

```yaml
  Documents:
    style: row
    columns: 4
    icon: mdi-file-document
```

- [ ] **Step 4: Validate Homepage YAML parses**

Run:

```bash
ruby -e 'require "yaml"; YAML.load_file("/data/configs/homepage/services.yaml"); YAML.load_file("/data/configs/homepage/settings.yaml"); puts "homepage yaml ok"'
```

Expected: prints `homepage yaml ok` and exits `0`.

- [ ] **Step 5: Verify no backup snapshot was touched**

Run:

```bash
git status --short backups /data/configs/homepage/services.yaml /data/configs/homepage/settings.yaml
```

Expected: no tracked `backups/homepage/*` changes. Live `/data` files may not appear in Git status because they are outside the repo.

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
PUID=1000 PGID=1000 TZ=Pacific/Auckland DATA_ROOT=/data PAPERLESS_DBNAME=paperless PAPERLESS_DBUSER=paperless PAPERLESS_DBPASS=example-password PAPERLESS_SECRET_KEY=example-secret-key PAPERLESS_URL=https://paperless.home.lab docker compose -f apps/docs/compose.yml config >/tmp/opn-154-compose-rendered.yml
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
