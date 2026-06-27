# OPN-154 Paperless-ngx Install Design

## Goal

Install and validate a self-hosted Paperless-ngx instance on the media Docker host so later document automation can use a controlled gateway path. This issue covers the Paperless infrastructure install, secure access path, initial validation, and local documentation. It does not build the OpenClaw gateway or scheduled backup automation.

## Scope

In scope:

- Add a dedicated document-services stack under `apps/docs`.
- Install Paperless-ngx with PostgreSQL, Redis, Gotenberg, and Tika.
- Configure durable bind mounts for app state, document media, consume input, and manual exports.
- Expose Paperless through Nginx Proxy Manager at `https://paperless.home.lab`.
- Place Authentik Proxy Auth in front of Paperless while keeping Paperless local auth enabled.
- Add a link-only Paperless entry to the live Homepage config.
- Validate the install with a real disposable upload/search smoke test.
- Document final paths, URL, manual admin setup, manual export, validation, and rollback.

Out of scope:

- OpenClaw gateway implementation.
- Direct OpenClaw access to Paperless or document filesystem paths.
- Scheduled Paperless backups and restore verification; this is tracked by OPN-155.
- Homepage Paperless widgets or additional Homepage API credentials.

## Stack Shape

Create `apps/docs` as the stack boundary. The directory name stays generic so it can host a future document-service replacement, but runtime names should be explicit while Paperless is the active implementation.

Expected files:

- `apps/docs/compose.yml`
- `apps/docs/example.env`
- `apps/docs/README.md`

Expected services:

- `paperless-webserver`
- `paperless-db`
- `paperless-broker`
- `paperless-gotenberg`
- `paperless-tika`

Use versioned image tags for Paperless, PostgreSQL, Redis, Gotenberg, and Tika. Verify current stable tags during implementation instead of guessing versions from memory.

Use the official-style Paperless Docker shape with PostgreSQL and Redis. Include Gotenberg and Tika from the first deploy so Office/PDF extraction behavior is available before real documents are imported.

## Storage

Keep application state under the existing repo convention:

```text
${DATA_ROOT}/configs/paperless/
```

Use long-term document storage for Paperless payloads:

```text
/mnt/storage/01_Documents/paperless/media
/mnt/storage/01_Documents/paperless/consume
```

Use the backup mount for manual exports:

```text
/mnt/storage/05_Backups/paperless/export
```

Paperless owns the live media directory. Humans and automation should not edit files inside the live media path directly. The consume path is a narrow future-friendly drop zone, not a broad host mount.

## Network And Auth

Paperless web joins `proxy_net`; database, broker, Gotenberg, and Tika stay on an internal docs network unless Paperless requires otherwise.

Do not publish a host `ports:` mapping for Paperless. Nginx Proxy Manager should reach Paperless over Docker networking and route:

```text
https://paperless.home.lab -> http://paperless-webserver:8000
```

Authentik Proxy Auth should sit in front of the NPM route as the homelab access gate. Paperless local auth remains enabled. The initial Paperless admin user is created manually after deployment; no admin password should be stored in compose files, committed examples, or documentation.

## Secrets

Commit only placeholder configuration in `apps/docs/example.env`. The real `apps/docs/.env` remains untracked for Komodo.

Keep these values out of Git:

- Paperless secret key
- PostgreSQL password
- Admin credentials
- API tokens
- Gateway secrets

If a Paperless API token is created during OPN-154, document it as gateway-owned future integration material. OpenClaw should not call Paperless directly and should not receive raw filesystem access to document storage.

## Homepage

Update the live Homepage config under `${DATA_ROOT}/configs/homepage`, not the `backups/homepage` snapshot files.

Add a `Documents` section between `Download Management` and `System`. Add a link-only entry:

```yaml
- Documents:
    - Paperless-ngx:
        icon: paperless-ngx.png
        href: https://paperless.home.lab
        description: Documents
```

Also add `Documents` to the Homepage layout in the same position. Do not add a Paperless Homepage widget or create a Homepage API token in this issue.

## Validation

Before OPN-154 is considered complete:

- Deploy the docs stack through Komodo.
- Confirm Paperless starts successfully.
- Confirm NPM routes `https://paperless.home.lab` to Paperless.
- Confirm Authentik Proxy Auth gates access before Paperless local auth.
- Create the initial admin user manually.
- Confirm configured bind mounts exist on the expected host paths.
- Upload a disposable sample document.
- Confirm the sample document is processed and searchable.
- Confirm document/media persistence survives container recreation.
- Confirm the Homepage `Documents` entry appears and links to Paperless.
- Document any Paperless API token creation path for the separate gateway work without storing token values in Git.

## Manual Export

OPN-154 defines the manual export path but does not automate backups. Document a manual export command using Paperless' exporter to write into:

```text
/mnt/storage/05_Backups/paperless/export
```

Scheduled export, PostgreSQL backup, retention, and restore verification are tracked by OPN-155.

## Rollback

Normal rollback should preserve data by default:

- Stop/remove the `apps/docs` stack.
- Remove or disable the NPM proxy host.
- Remove or disable the Authentik application/provider wiring.
- Remove the Homepage `Documents` entry if desired.
- Leave `/data/configs/paperless` and `/mnt/storage/.../paperless` intact.

Destructive cleanup of Paperless config, database, media, consume, and export directories must be a separate explicit step.
