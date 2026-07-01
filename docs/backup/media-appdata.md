# Media Appdata Encrypted Backups

This is the OPN-192 manual-first backup lane for selected media Docker app config/appdata paths. It complements full VM backups; it does not replace them.

## First Backup Set

Included `${APPDATA_ROOT}` paths:

- `adguard/conf`
- `adguard/work`
- `autoscan`
- `bazarr`
- `cleanuparr`
- `flaresolverr`
- `glances`
- `gluetun`
- `icloudpd`
- `jellyfin`
- `jellyseerr`
- `n8n`
- `nginx-proxy-manager/data`
- `nginx-proxy-manager/letsencrypt`
- `nzbget`
- `prowlarr`
- `qbittorrent`
- `radarr`
- `sonarr`
- `speedtest-tracker`

Included stack env files when present:

- `apps/arr-stack/.env`
- `apps/downloads/.env`
- `apps/media/.env`
- `apps/openclaw-gateway/.env`
- `apps/utilities/.env`
- `infra/dns/adguard/.env`
- `infra/proxy/nginx-proxy-manager/.env`

Excluded in this first pass:

- Paperless app state and exports; use OPN-155.
- Authentik state and PostgreSQL; handle as a dedicated high-risk restore lane.
- Komodo Mongo state; existing Komodo backup wiring remains separate.
- Bulk media libraries and downloads under `${DATA_ROOT}`.

## Artifact Format

The manual script writes:

```text
media-appdata-<utc-timestamp>.tar.gz.age
media-appdata-<utc-timestamp>.tar.gz.age.sha256
```

Encryption uses `age` with a recipient supplied by `BACKUP_AGE_RECIPIENT` or `BACKUP_AGE_RECIPIENT_FILE`. Store the age private key outside this repository.

## Secret Rules

- Do not commit real `.env` files.
- Do not paste decrypted archive contents into diagnostics or Linear.
- Do not store the age private key in this repo.
- Keep backup artifacts outside the repo; `backups/` is gitignored only as a last-resort guard.
- Use a destination guard file named `.opn-192-media-backups-ok` before allowing writes.

## Manual Backup

Dry-run first:

```bash
APPDATA_ROOT=/srv/appdata \
BACKUP_DEST=/mnt/backup/media-docker-appdata \
BACKUP_AGE_RECIPIENT_FILE=/path/to/age-recipient.txt \
scripts/backup-media-appdata.sh --dry-run
```

Create the destination guard after confirming the mount is the intended backup target:

```bash
touch /mnt/backup/media-docker-appdata/.opn-192-media-backups-ok
```

Run the encrypted backup:

```bash
APPDATA_ROOT=/srv/appdata \
BACKUP_DEST=/mnt/backup/media-docker-appdata \
BACKUP_AGE_RECIPIENT_FILE=/path/to/age-recipient.txt \
scripts/backup-media-appdata.sh --run
```

Verify the artifact hash:

```bash
sha256sum -c /mnt/backup/media-docker-appdata/media-appdata-<timestamp>.tar.gz.age.sha256
```

## Restore Verification: Jellyseerr Example

Do not restore over live state as a first test.

1. Create a temporary restore directory outside live appdata.
2. Verify the encrypted artifact hash.
3. Decrypt the archive with the age private key into a stream.
4. Extract only the `jellyseerr` subtree into the temporary restore directory.
5. Confirm expected files exist without printing secret values.
6. Compare ownership and permissions against live `${APPDATA_ROOT}/jellyseerr`.
7. Record the artifact name, hash verification result, and file-count summary.

Command shape:

```bash
mkdir -p /tmp/opn-192-restore-check
sha256sum -c /mnt/backup/media-docker-appdata/media-appdata-<timestamp>.tar.gz.age.sha256
age -d -i /path/to/age-private-key.txt \
  /mnt/backup/media-docker-appdata/media-appdata-<timestamp>.tar.gz.age \
  | tar -xz -C /tmp/opn-192-restore-check --wildcards 'srv/appdata/jellyseerr/*'
find /tmp/opn-192-restore-check -type f | wc -l
```

A live restore requires a separate maintenance plan: confirm backups, stop only the affected stack through Komodo, move the current appdata aside, restore the subtree, check ownership, redeploy through Komodo, smoke test, and keep the pre-restore tree until the app is verified.

## Rollback

This workflow does not change live services or install a scheduler. Rollback is to stop using the script and remove any encrypted artifacts from the backup destination if they were created in error. Do not delete decrypted restore-test directories until confirming they contain no needed evidence.
