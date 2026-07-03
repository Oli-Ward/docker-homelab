#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=/home/oli/docker/apps/docs
BACKUP_ROOT=/mnt/storage/05_Backups/paperless
EXPORT_DIR="$BACKUP_ROOT/export"
DB_DIR="$BACKUP_ROOT/db"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
TMP_DIR="/usr/src/paperless/export/run-$TIMESTAMP"

mkdir -p "$EXPORT_DIR" "$DB_DIR"

set -a
# shellcheck source=/dev/null
source "$SCRIPT_DIR/.env"
set +a

: "${PAPERLESS_DBPASS:?PAPERLESS_DBPASS is required}"
: "${PAPERLESS_DBNAME:?PAPERLESS_DBNAME is required}"
: "${PAPERLESS_DBUSER:?PAPERLESS_DBUSER is required}"

cd "$SCRIPT_DIR"

docker compose -f compose.yml exec -T paperless-webserver sh -lc "mkdir -p '$TMP_DIR' && cd /usr/src/paperless/src && python3 manage.py document_exporter '$TMP_DIR'"

docker compose -f compose.yml exec -T paperless-webserver \
  sh -lc "tar -C /usr/src/paperless/export -czf - \"run-$TIMESTAMP\"" \
  > "$EXPORT_DIR/paperless-export-$TIMESTAMP.tar.gz"
docker compose -f compose.yml exec -T paperless-webserver sh -lc "rm -rf '$TMP_DIR'"

docker compose -f compose.yml exec -T -e PGPASSWORD="$PAPERLESS_DBPASS" paperless-db \
  pg_dump -Fc "$PAPERLESS_DBNAME" -U "$PAPERLESS_DBUSER" > "$DB_DIR/paperless-db-$TIMESTAMP.dump"

find "$EXPORT_DIR" -type f -name "paperless-export-*.tar.gz" -mtime +14 -delete
find "$DB_DIR" -type f -name "paperless-db-*.dump" -mtime +14 -delete

echo "paperless backup complete: $TIMESTAMP"
