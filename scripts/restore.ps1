param(
    [Parameter(Mandatory = $true)]
    [string]$Source
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path "docker-compose.yml")) {
    throw "Run this script from the repository root."
}
if (-not (Test-Path (Join-Path $Source "postgres.dump"))) {
    throw "Missing $Source/postgres.dump"
}

Write-Host "Stopping application services..."
docker compose --profile ai stop backend scraper-worker ai-worker scheduler frontend

Write-Host "Restoring PostgreSQL..."
docker compose cp "$Source/postgres.dump" postgres:/tmp/carmarket-restore.dump
docker compose exec -T postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists /tmp/carmarket-restore.dump'
if ($LASTEXITCODE -ne 0) { throw "pg_restore failed" }
docker compose exec -T postgres rm -f /tmp/carmarket-restore.dump

$minioSource = Join-Path $Source "minio-data"
if (Test-Path $minioSource) {
    Write-Host "Restoring MinIO data..."
    docker compose cp "$minioSource/." minio:/data/
}

Write-Host "Starting application services..."
docker compose up -d

Write-Host "Restore completed."
