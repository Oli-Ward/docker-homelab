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
add_appdata "ryot-postgres"
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
