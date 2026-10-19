param(
    [string]$Destination = ""
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path "docker-compose.yml")) {
    throw "Run this script from the repository root."
}

$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
if ([string]::IsNullOrWhiteSpace($Destination)) {
    $Destination = Join-Path (Get-Location) "backups/$stamp"
}
New-Item -ItemType Directory -Force -Path $Destination | Out-Null

Write-Host "Backing up PostgreSQL to $Destination/postgres.dump"
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/carmarket-backup.dump'
if ($LASTEXITCODE -ne 0) { throw "pg_dump failed" }
docker compose cp postgres:/tmp/carmarket-backup.dump "$Destination/postgres.dump"
docker compose exec -T postgres rm -f /tmp/carmarket-backup.dump

Write-Host "Backing up MinIO data to $Destination/minio-data"
docker compose cp minio:/data "$Destination/minio-data"

Write-Host "Backup completed: $Destination"
