# OPN-192 Encrypted Media Appdata Backups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a manual-first encrypted backup workflow for selected media Docker app config/appdata paths and stack env files without installing a scheduler or mutating live services.

**Architecture:** Keep the workflow source-controlled as a script plus documentation. The script defaults to dry-run, requires explicit `--run` to write an encrypted `tar.gz.age` artifact, and requires an age recipient plus a destination guard file before writing. The docs define the first backup inventory, secret-handling rules, and restore-verification steps for a representative app.

**Tech Stack:** POSIX shell, `tar`, `gzip`, `age`, `sha256sum`, pytest subprocess tests, Docker Compose documentation.

---

## File Structure

- Create `scripts/backup-media-appdata.sh`
  - Manual backup runner.
  - Reads `APPDATA_ROOT`, `BACKUP_DEST`, and `BACKUP_AGE_RECIPIENT` or `BACKUP_AGE_RECIPIENT_FILE`.
  - Dry-run by default; `--run` creates encrypted archive.
  - Includes only the OPN-192 first-pass inventory.
  - Includes stack `.env` files by path when present, but never prints contents.
  - Requires destination guard file `.opn-192-media-backups-ok` for `--run`.
- Create `tests/test_backup_media_appdata_script.py`
  - Tests dry-run behavior, guard/recipient enforcement, and command construction using fake `tar`, `gzip`, and `age`.
- Create `docs/backup/media-appdata.md`
  - Durable workflow documentation, first backup set inventory, artifact format, secret rules, runbook, and Jellyseerr restore-verification checklist.
- Modify `README.md`
  - Add a short pointer to the new backup workflow documentation.
- Create this plan file.

## First Backup Set Inventory

Included `${APPDATA_ROOT}` subtrees:

```text
adguard/conf
adguard/work
autoscan
bazarr
cleanuparr
flaresolverr
glances
gluetun
icloudpd
jellyfin
jellyseerr
n8n
nginx-proxy-manager/data
nginx-proxy-manager/letsencrypt
nzbget
prowlarr
qbittorrent
radarr
sonarr
speedtest-tracker
```

Included stack env files when present:

```text
apps/arr-stack/.env
apps/downloads/.env
apps/media/.env
apps/openclaw-gateway/.env
apps/utilities/.env
infra/dns/adguard/.env
infra/proxy/nginx-proxy-manager/.env
```

Excluded:

```text
apps/docs/.env
${APPDATA_ROOT}/paperless/*
identity/authentik/*
platform/komodo/*
${DATA_ROOT}/media/*
${DATA_ROOT}/downloads/*
```

Rationale: Paperless remains in OPN-155. Authentik and Komodo are stateful infrastructure with separate backup/restore risk. Bulk media/download content is out of scope.

### Task 1: Add Backup Script Tests

**Files:**
- Create: `tests/test_backup_media_appdata_script.py`
- Future script under test: `scripts/backup-media-appdata.sh`

- [ ] **Step 1: Write a dry-run test**

Create `tests/test_backup_media_appdata_script.py` with:

```python
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "backup-media-appdata.sh"


def base_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["APPDATA_ROOT"] = str(tmp_path / "appdata")
    env["BACKUP_DEST"] = str(tmp_path / "backup")
    env["BACKUP_AGE_RECIPIENT"] = "age1example"
    return env


def test_backup_script_dry_run_lists_inventory_without_writing(tmp_path: Path):
    appdata = tmp_path / "appdata"
    backup = tmp_path / "backup"
    (appdata / "jellyfin").mkdir(parents=True)
    (appdata / "jellyseerr").mkdir(parents=True)
    backup.mkdir()

    result = subprocess.run(
        [str(SCRIPT), "--dry-run"],
        cwd=REPO_ROOT,
        env=base_env(tmp_path),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "DRY RUN" in result.stdout
    assert "appdata/jellyfin" in result.stdout
    assert "appdata/jellyseerr" in result.stdout
    assert not list(backup.iterdir())
```

- [ ] **Step 2: Run the dry-run test and verify RED**

Run:

```bash
pytest tests/test_backup_media_appdata_script.py::test_backup_script_dry_run_lists_inventory_without_writing -q
```

Expected: fail because `scripts/backup-media-appdata.sh` does not exist.

- [ ] **Step 3: Write guard and command-construction tests**

Append:

```python
def write_fake_tools(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "commands.log"
    for name in ("tar", "gzip", "age", "sha256sum"):
        tool = bin_dir / name
        tool.write_text(
            f"""#!/usr/bin/env sh
printf '%s\\n' "{name} $*" >> "{log}"
case "{name}" in
  tar) printf 'tar-bytes' ;;
  gzip) cat ;;
  age) cat ;;
  sha256sum) printf 'abc123  %s\\n' "$1" ;;
esac
""",
            encoding="utf-8",
        )
        tool.chmod(0o755)
    return bin_dir


def test_backup_script_requires_guard_file_for_run(tmp_path: Path):
    appdata = tmp_path / "appdata"
    (appdata / "jellyfin").mkdir(parents=True)
    (tmp_path / "backup").mkdir()

    result = subprocess.run(
        [str(SCRIPT), "--run"],
        cwd=REPO_ROOT,
        env=base_env(tmp_path),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert ".opn-192-media-backups-ok" in result.stderr


def test_backup_script_run_writes_encrypted_artifact_with_fake_tools(tmp_path: Path):
    appdata = tmp_path / "appdata"
    backup = tmp_path / "backup"
    (appdata / "jellyfin").mkdir(parents=True)
    (appdata / "jellyfin" / "config.xml").write_text("<xml />", encoding="utf-8")
    backup.mkdir()
    (backup / ".opn-192-media-backups-ok").write_text("ok\n", encoding="utf-8")
    bin_dir = write_fake_tools(tmp_path)
    env = base_env(tmp_path)
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["BACKUP_TIMESTAMP"] = "2026-07-01T09-30-00Z"

    result = subprocess.run(
        [str(SCRIPT), "--run"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    artifact = backup / "media-appdata-2026-07-01T09-30-00Z.tar.gz.age"
    assert result.returncode == 0
    assert artifact.exists()
    assert (backup / "media-appdata-2026-07-01T09-30-00Z.tar.gz.age.sha256").exists()
    commands = (tmp_path / "commands.log").read_text(encoding="utf-8")
    assert "tar" in commands
    assert "gzip" in commands
    assert "age -r age1example" in commands
    assert "config.xml" not in result.stdout
```

- [ ] **Step 4: Run the full script test file and verify RED**

Run:

```bash
pytest tests/test_backup_media_appdata_script.py -q
```

Expected: fail because the script is still missing.

### Task 2: Implement Manual Encrypted Backup Script

**Files:**
- Create: `scripts/backup-media-appdata.sh`

- [ ] **Step 1: Create the script**

Create `scripts/backup-media-appdata.sh`:

```sh
#!/usr/bin/env sh
set -eu

usage() {
  cat <<'EOF'
Usage: scripts/backup-media-appdata.sh [--dry-run|--run]

Manual-first encrypted backup for selected media Docker appdata/config paths.

Required environment:
  APPDATA_ROOT               Appdata root, for example /srv/appdata
  BACKUP_DEST                Destination directory for encrypted artifacts
  BACKUP_AGE_RECIPIENT       age recipient, or use BACKUP_AGE_RECIPIENT_FILE

Optional environment:
  BACKUP_AGE_RECIPIENT_FILE  File containing one age recipient
  BACKUP_TIMESTAMP           Stable timestamp override for tests

Safety:
  --dry-run is the default and writes nothing.
  --run requires BACKUP_DEST/.opn-192-media-backups-ok.
EOF
}

mode="dry-run"
case "${1:---dry-run}" in
  --dry-run) mode="dry-run" ;;
  --run) mode="run" ;;
  -h|--help) usage; exit 0 ;;
  *) usage >&2; exit 2 ;;
esac

APPDATA_ROOT=${APPDATA_ROOT:?Set APPDATA_ROOT}
BACKUP_DEST=${BACKUP_DEST:?Set BACKUP_DEST}
timestamp=${BACKUP_TIMESTAMP:-$(date -u +%Y-%m-%dT%H-%M-%SZ)}
artifact="$BACKUP_DEST/media-appdata-$timestamp.tar.gz.age"
manifest=$(mktemp)
trap 'rm -f "$manifest"' EXIT

recipient=""
if [ -n "${BACKUP_AGE_RECIPIENT:-}" ]; then
  recipient=$BACKUP_AGE_RECIPIENT
elif [ -n "${BACKUP_AGE_RECIPIENT_FILE:-}" ]; then
  recipient=$(sed -n '1p' "$BACKUP_AGE_RECIPIENT_FILE")
fi

if [ -z "$recipient" ]; then
  echo "Set BACKUP_AGE_RECIPIENT or BACKUP_AGE_RECIPIENT_FILE." >&2
  exit 2
fi

add_path() {
  path=$1
  if [ -e "$path" ]; then
    printf '%s\n' "$path" >> "$manifest"
  fi
}

add_appdata() {
  add_path "$APPDATA_ROOT/$1"
}

add_appdata "adguard/conf"
add_appdata "adguard/work"
add_appdata "autoscan"
add_appdata "bazarr"
add_appdata "cleanuparr"
add_appdata "flaresolverr"
add_appdata "glances"
add_appdata "gluetun"
add_appdata "icloudpd"
add_appdata "jellyfin"
add_appdata "jellyseerr"
add_appdata "n8n"
add_appdata "nginx-proxy-manager/data"
add_appdata "nginx-proxy-manager/letsencrypt"
add_appdata "nzbget"
add_appdata "prowlarr"
add_appdata "qbittorrent"
add_appdata "radarr"
add_appdata "sonarr"
add_appdata "speedtest-tracker"

add_path "apps/arr-stack/.env"
add_path "apps/downloads/.env"
add_path "apps/media/.env"
add_path "apps/openclaw-gateway/.env"
add_path "apps/utilities/.env"
add_path "infra/dns/adguard/.env"
add_path "infra/proxy/nginx-proxy-manager/.env"

if [ ! -s "$manifest" ]; then
  echo "No backup inputs exist for the configured APPDATA_ROOT." >&2
  exit 1
fi

if [ "$mode" = "dry-run" ]; then
  echo "DRY RUN: would create encrypted artifact:"
  echo "$artifact"
  echo "Included paths:"
  sed "s#^$APPDATA_ROOT#APPDATA_ROOT#" "$manifest"
  exit 0
fi

if [ ! -f "$BACKUP_DEST/.opn-192-media-backups-ok" ]; then
  echo "Refusing to write: missing $BACKUP_DEST/.opn-192-media-backups-ok" >&2
  exit 2
fi

mkdir -p "$BACKUP_DEST"
tar -C / -cf - -T "$manifest" | gzip -c | age -r "$recipient" -o "$artifact"
sha256sum "$artifact" > "$artifact.sha256"

echo "Encrypted backup artifact written:"
echo "$artifact"
echo "$artifact.sha256"
```

- [ ] **Step 2: Make it executable**

Run:

```bash
chmod +x scripts/backup-media-appdata.sh
```

- [ ] **Step 3: Run the script tests and verify GREEN**

Run:

```bash
pytest tests/test_backup_media_appdata_script.py -q
```

Expected: all tests pass.

### Task 3: Document Workflow And Restore Verification

**Files:**
- Create: `docs/backup/media-appdata.md`
- Modify: `README.md`

- [ ] **Step 1: Create workflow documentation**

Create `docs/backup/media-appdata.md` with:

```markdown
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
```

- [ ] **Step 2: Link docs from README**

Add under `README.md` future improvements/storage area:

```markdown
Manual encrypted appdata/config backups are documented in [`docs/backup/media-appdata.md`](docs/backup/media-appdata.md). This is a manual-first workflow and does not replace full VM backups.
```

### Task 4: Verify, Commit, And Update Linear

**Files:**
- All files above.

- [ ] **Step 1: Run verification**

Run:

```bash
pytest tests/test_backup_media_appdata_script.py -q
sh -n scripts/backup-media-appdata.sh
git diff --check
git status --short
```

Expected: tests pass, shell parses, diff check is clean, and only OPN-192 files are changed.

- [ ] **Step 2: Commit**

Run:

```bash
git add scripts/backup-media-appdata.sh tests/test_backup_media_appdata_script.py docs/backup/media-appdata.md README.md docs/superpowers/plans/2026-07-01-opn-192-encrypted-media-appdata-backups.md
git commit -m "OPN-192: add encrypted media appdata backup workflow"
```

- [ ] **Step 3: Final Linear update**

Comment:

```markdown
Outcome: repo-side manual-first workflow implemented.

What changed:
- Added encrypted appdata backup script.
- Added tests.
- Added backup and restore-verification docs.
- Linked docs from README.

Verification:
- `pytest tests/test_backup_media_appdata_script.py -q`
- `sh -n scripts/backup-media-appdata.sh`
- `git diff --check`

Commit: <hash>
Remaining follow-ups: run the first live manual backup only after confirming the backup destination and age recipient/private-key handling.
```

## Self-Review

- The plan covers all OPN-192 acceptance criteria.
- The script is manual-first and dry-run by default.
- No scheduler, live backup job, container restart, restore, or host mutation is added.
- Paperless is explicitly excluded for OPN-155.
- Secrets and backup artifacts remain out of Git.
