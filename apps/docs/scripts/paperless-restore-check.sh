#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=/home/oli/docker/apps/docs
BACKUP_ROOT=/mnt/storage/05_Backups/paperless
DB_DIR="$BACKUP_ROOT/db"
BACKUP_FILE="${1:-}"

if [ -z "$BACKUP_FILE" ]; then
  BACKUP_FILE="$(find "$DB_DIR" -maxdepth 1 -type f -name 'paperless-db-*.dump' -print0 \
    | xargs -0 ls -t 2>/dev/null | head -n 1 || true)"
fi

if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
  echo "No DB backup file found. Provide one as first argument."
  exit 1
fi

set -a
# shellcheck source=/dev/null
source "$SCRIPT_DIR/.env"
set +a

: "${PAPERLESS_DBPASS:?PAPERLESS_DBPASS is required}"
: "${PAPERLESS_DBNAME:?PAPERLESS_DBNAME is required}"
: "${PAPERLESS_DBUSER:?PAPERLESS_DBUSER is required}"

SANDBOX_NAME="paperless-restore-check-$(date +%s)"

cleanup() {
  docker stop "$SANDBOX_NAME" >/dev/null 2>&1 || true
  docker rm "$SANDBOX_NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker run --name "$SANDBOX_NAME" -d \
  -e POSTGRES_DB="$PAPERLESS_DBNAME" \
  -e POSTGRES_USER="$PAPERLESS_DBUSER" \
  -e POSTGRES_PASSWORD="$PAPERLESS_DBPASS" \
  postgres:18.4 >/dev/null

READY=0
for _ in $(seq 1 30); do
  if docker exec "$SANDBOX_NAME" pg_isready -U "$PAPERLESS_DBUSER" -d "$PAPERLESS_DBNAME" >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 2
done

if [ "$READY" -ne 1 ]; then
  echo "temporary restore database did not become ready"
  exit 1
fi

docker exec -i -e PGPASSWORD="$PAPERLESS_DBPASS" "$SANDBOX_NAME" \
  pg_restore -U "$PAPERLESS_DBUSER" -d "$PAPERLESS_DBNAME" --no-owner --if-exists --clean < "$BACKUP_FILE"

HAS_TABLE="$(docker exec -e PGPASSWORD="$PAPERLESS_DBPASS" "$SANDBOX_NAME" \
  psql -U "$PAPERLESS_DBUSER" -d "$PAPERLESS_DBNAME" -t -A -c "SELECT to_regclass('public.documents_document') IS NOT NULL;")"

if [ "$HAS_TABLE" != "t" ]; then
  echo "Restore failed: documents_document table is missing"
  exit 1
fi

COUNT="$(docker exec -e PGPASSWORD="$PAPERLESS_DBPASS" "$SANDBOX_NAME" \
  psql -U "$PAPERLESS_DBUSER" -d "$PAPERLESS_DBNAME" -t -A -c "SELECT count(*) FROM documents_document;")"

echo "restore check complete, documents_document count: $COUNT"
