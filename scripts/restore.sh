#!/usr/bin/env sh
set -eu

if [ "${1:-}" = "" ]; then
    echo "Usage: scripts/restore.sh ./backups/<timestamp>" >&2
    exit 2
fi

SOURCE="$1"

if [ ! -f "$SOURCE/postgres.dump" ]; then
    echo "Missing $SOURCE/postgres.dump" >&2
    exit 2
fi

echo "Stopping application services..."
docker compose stop backend scraper-worker ai-worker scheduler frontend

echo "Restoring PostgreSQL..."
docker compose cp "$SOURCE/postgres.dump" postgres:/tmp/carmarket-restore.dump
docker compose exec -T postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists /tmp/carmarket-restore.dump'
docker compose exec -T postgres rm -f /tmp/carmarket-restore.dump

if [ -d "$SOURCE/minio-data" ]; then
    echo "Restoring MinIO data..."
    docker compose cp "$SOURCE/minio-data/." minio:/data/
fi

echo "Starting application services..."
docker compose up -d

echo "Restore completed."
