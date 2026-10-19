param(
    [switch]$Volumes,
    [switch]$Yes
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker was not found in PATH."
}
& docker compose version *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose v2 is required (docker compose)."
}

if ($Volumes -and -not $Yes) {
    $answer = Read-Host 'This deletes PostgreSQL, Redis, MinIO and Ollama data. Type "yes" to continue'
    if ($answer -ne "yes") {
        Write-Host "Aborted. No data was deleted."
        exit 1
    }
}

if ($Volumes) {
    Write-Host "Stopping the stack and deleting all persistent volumes..."
    & docker compose --profile ai down --remove-orphans --volumes
}
else {
    Write-Host "Stopping the complete stack (core + ai)..."
    & docker compose --profile ai down --remove-orphans
}
if ($LASTEXITCODE -ne 0) {
    throw "docker compose down failed."
}

Write-Host ""
Write-Host "Bulgaria Auto CarMarket is stopped."
Write-Host "Persistent volumes are preserved."
Write-Host "Start again with: .\scripts\start.ps1"
