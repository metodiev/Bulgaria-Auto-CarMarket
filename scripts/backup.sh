#!/usr/bin/env sh
set -eu

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="${1:-./backups/$STAMP}"
mkdir -p "$DEST"

echo "Backing up PostgreSQL to $DEST/postgres.dump"
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/carmarket-backup.dump'
docker compose cp postgres:/tmp/carmarket-backup.dump "$DEST/postgres.dump"
docker compose exec -T postgres rm -f /tmp/carmarket-backup.dump

echo "Backing up MinIO data to $DEST/minio-data"
docker compose cp minio:/data "$DEST/minio-data"

echo "Backup completed: $DEST"
