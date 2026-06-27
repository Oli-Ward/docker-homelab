# OPN-193 Media Compose Backup Readback Audit

## Scope

This audit captures read-only evidence for the live media Docker Compose repository and current backup/readback posture.

No compose files, backup jobs, Komodo settings, live containers, or secret-bearing files were changed. Real `.env` and `compose.env` file contents were not opened or copied.

## Evidence Summary

- Repository path in the active checkout: `/home/oli/docker`.
- Live Docker Compose labels point running stack config files back to `/home/oli/docker/...`.
- Git tracks the Compose YAML files and example env files needed to reconstruct intended stack configuration.
- Real stack env files are ignored by Git and appear only as ignored paths in status output.
- Repo documentation currently contains migration/checkpoint guidance and Komodo Mongo backup wiring, but no proven automated backup/readback workflow for the media Docker config repository or appdata was found in this read-only audit.

## Compose Repo And Stack Locations

Tracked Compose files from `git ls-files '*compose*.yml' '*compose*.yaml'`:

```text
apps/arr-stack/compose.yml
apps/docs/compose.yml
apps/downloads/compose.yml
apps/media/compose.yml
apps/openclaw-gateway/compose.yml
apps/utilities/compose.yml
identity/authentik/compose.yml
infra/dns/adguard/compose.yml
infra/proxy/nginx-proxy-manager/compose.yml
platform/komodo/mongo.compose.yaml
```

Live Docker labels confirm running Compose config paths and working directories under this repo:

| Compose project | Live config file | Live env file path | Working directory |
| --- | --- | --- | --- |
| `arr-stack` | `/home/oli/docker/apps/arr-stack/compose.yml` | `/home/oli/docker/apps/arr-stack/.env` | `/home/oli/docker/apps/arr-stack` |
| `downloads` | `/home/oli/docker/apps/downloads/compose.yml` | `/home/oli/docker/apps/downloads/.env` | `/home/oli/docker/apps/downloads` |
| `media` | `/home/oli/docker/apps/media/compose.yml` | `/home/oli/docker/apps/media/.env` | `/home/oli/docker/apps/media` |
| `docs` | `/home/oli/docker/apps/docs/compose.yml` | `/home/oli/docker/apps/docs/.env` | `/home/oli/docker/apps/docs` |
| `utilities` | `/home/oli/docker/apps/utilities/compose.yml` | `/home/oli/docker/apps/utilities/.env` | `/home/oli/docker/apps/utilities` |
| `adguard` | `/home/oli/docker/infra/dns/adguard/compose.yml` | `/home/oli/docker/infra/dns/adguard/.env` | `/home/oli/docker/infra/dns/adguard` |
| `authentik` | `/home/oli/docker/identity/authentik/compose.yml` | `/home/oli/docker/identity/authentik/.env` | `/home/oli/docker/identity/authentik` |
| `komodo` | `/home/oli/docker/platform/komodo/mongo.compose.yaml` | `/home/oli/docker/platform/komodo/compose.env` | `/home/oli/docker/platform/komodo` |
| `nginx-proxy-manager` | `/home/oli/docker/infra/proxy/nginx-proxy-manager/compose.yml` | none shown in Compose labels | `/home/oli/docker/infra/proxy/nginx-proxy-manager` |

The live label evidence means running containers were created from this checkout path, not from a separate visible compose repository path.

Current working tree status during this audit showed unrelated local edits and untracked diagnostics content:

```text
 M apps/openclaw-gateway/README.md
 M apps/openclaw-gateway/compose.yml
 M apps/openclaw-gateway/example.env
 M docs/superpowers/plans/2026-06-28-opn-193-media-compose-backup-readback-audit.md
?? diagnostics/backup/
?? diagnostics/build-lanes/
?? docs/superpowers/plans/2026-06-28-opn-190-live-media-boundary-audit.md
```

Only `docs/superpowers/plans/2026-06-28-opn-193-media-compose-backup-readback-audit.md` and this report belong to `OPN-193`. The OpenClaw Gateway files, `diagnostics/build-lanes/`, and `OPN-190` plan were treated as unrelated existing work and were not modified for this audit.

## Git Tracking And Secret Exclusions

Relevant `.gitignore` rules:

```text
.env
data/
configs/
*.db
*.sqlite
ssl/
backups/
.worktrees/
platform/komodo/backups/
platform/komodo/compose.env
identity/authentik/data/
identity/authentik/certs/
identity/authentik/custom-templates/
identity/authentik/database/
identity/authentik/logs/
identity/authentik/media/
identity/authentik/static/
identity/authentik/templates/
identity/authentik/tmp/
```

Tracked example env files:

```text
apps/arr-stack/example.env
apps/docs/example.env
apps/downloads/example.env
apps/media/example.env
apps/openclaw-gateway/example.env
apps/utilities/example.env
infra/dns/adguard/.env.example
infra/proxy/nginx-proxy-manager/example.env
platform/komodo/compose.example.env
```

Ignored real env paths from `git status --ignored --short -- ':*.env' ':**/.env' ':**/*.env'`:

```text
!! apps/arr-stack/.env
!! apps/docs/.env
!! apps/downloads/.env
!! apps/media/.env
!! apps/openclaw-gateway/.env
!! apps/utilities/.env
!! identity/authentik/.env
!! infra/dns/adguard/.env
!! platform/komodo/compose.env
```

The ignore posture protects real stack env files from normal Git tracking. The read-only evidence did not prove whether every secret-bearing setting outside these env files is excluded; certificate/state directories are ignored by broad and Authentik-specific rules.

## Backup And Readback Evidence

Evidence found:

- `README.md` lists "Automated backups" only under future improvements.
- `AGENTS.md` instructs agents to confirm backups/checkpoints before stateful or storage-affecting changes and not to perform backup, restore, migration, or destructive cleanup unless explicitly asked.
- `docs/migrations/2026-06-28-opn-158-appdata-root-migration.md` documents an operator migration checklist that includes confirming backups/checkpoints, copying app state with `rsync`, validating compose rendering, Komodo redeploy, smoke checks, and rollback. This is migration guidance, not proof that a backup job currently exists or has been read back.
- `platform/komodo/mongo.compose.yaml` mounts `${COMPOSE_KOMODO_BACKUPS_PATH}:/backups` for Komodo Core and comments that this stores dated backups of the Komodo database.
- `apps/docs/README.md` says scheduled Paperless exports, PostgreSQL backups, retention, and restore verification are tracked separately by `OPN-155`.

No repo-managed Restic, Borg, rsync timer, backup script, restore/readback script, or documented media Docker config backup verification run was found by:

```bash
rg -n --hidden -g '!*.env' -g '!**/.env' -g '!**/.git/**' '(backup|restore|readback|restic|borg|rsync|snapshot|appdata|APPDATA_ROOT|DATA_ROOT|Komodo)' .
```

This does not rule out backup jobs managed outside the repo, such as in Komodo UI, cron, systemd timers, NAS tooling, hypervisor snapshots, or another host.

## Unknowns

- Whether a live external backup job currently captures `/home/oli/docker`, `/srv/appdata`, `/data/configs`, or other Docker config/appdata paths.
- Whether any current backup has been restored or read back successfully.
- Whether Komodo's database backup path is configured and populated at runtime, because this audit did not open `platform/komodo/compose.env` or inspect the mounted backup directory.
- Whether secret-bearing configuration exists outside `.env`, `compose.env`, certificates, and ignored runtime state directories.
- Whether `OPN-192` will add encrypted config/appdata backup automation or readback verification that supersedes these unknowns.

## Safety Notes

- Docker commands used were read-only: `docker ps` and `docker inspect`.
- No `docker compose up`, `docker compose down`, `docker compose pull`, restart, prune, backup mutation, restore, or Komodo mutation commands were run.
- Secret-bearing files were referenced by path only. Their contents were not printed.
- The report itself is documentation-only and contains no raw secret values.

## Verification Commands

Commands run for this audit:

```bash
git status --short
git ls-files '*compose*.yml' '*compose*.yaml'
sed -n '1,220p' .gitignore
git ls-files '*.env' '.env' '**/.env'
git ls-files '*example.env' '*.env.example'
git status --ignored --short -- ':*.env' ':**/.env' ':**/*.env'
rg -n --hidden -g '!*.env' -g '!**/.env' -g '!**/.git/**' '(backup|restore|readback|restic|borg|rsync|snapshot|appdata|APPDATA_ROOT|DATA_ROOT|Komodo)' .
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Labels}}'
docker ps --format '{{.Names}}' | while IFS= read -r c; do docker inspect "$c" --format '{{.Name}}|{{index .Config.Labels "com.docker.compose.project"}}|{{index .Config.Labels "com.docker.compose.project.config_files"}}|{{index .Config.Labels "com.docker.compose.project.environment_file"}}|{{index .Config.Labels "com.docker.compose.project.working_dir"}}'; done
sed -n '1,220p' README.md
sed -n '1,210p' docs/migrations/2026-06-28-opn-158-appdata-root-migration.md
sed -n '35,95p' platform/komodo/mongo.compose.yaml
```
