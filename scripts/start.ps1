param(
    [switch]$NoBuild,
    [switch]$Restart,
    [switch]$PullModel,
    [int]$WaitSeconds = 180
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Get-EnvValue {
    param([string]$Name, [string]$Default)

    if (Test-Path ".env") {
        $line = Get-Content ".env" |
            Where-Object { $_ -match "^\s*$([regex]::Escape($Name))=" } |
            Select-Object -Last 1
        if ($line) {
            return ($line -split "=", 2)[1].Trim()
        }
    }
    return $Default
}

function Test-HttpOk {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400)
    }
    catch {
        return $false
    }
}

function Wait-ForUrl {
    param([string]$Url, [string]$Label)

    $elapsed = 0
    Write-Host -NoNewline "Waiting for $Label"
    while ($elapsed -lt $WaitSeconds) {
        if (Test-HttpOk -Url $Url) {
            Write-Host " ready"
            return $true
        }
        Write-Host -NoNewline "."
        Start-Sleep -Seconds 3
        $elapsed += 3
    }
    Write-Host " timed out"
    return $false
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker was not found in PATH. Install Docker Engine or Docker Desktop and try again."
}
& docker compose version *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose v2 is required (docker compose)."
}
& docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "The Docker daemon is not reachable. Start Docker Desktop / Docker Engine first."
}

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env from .env.example."
        Write-Host "Review ADMIN_API_KEY and all passwords before exposing the app."
    }
    else {
        throw "Missing .env and .env.example. Cannot start."
    }
}

$BackendPort = Get-EnvValue "BACKEND_PORT" "8000"
$FrontendPort = Get-EnvValue "FRONTEND_PORT" "8080"
$MinioConsolePort = Get-EnvValue "MINIO_CONSOLE_PORT" "9001"
$OllamaModel = Get-EnvValue "OLLAMA_MODEL" "qwen3:4b"

if ($Restart) {
    Write-Host "Restart requested: stopping the current stack first."
    & (Join-Path $PSScriptRoot "stop.ps1")
    if ($LASTEXITCODE -ne 0) {
        throw "stop.ps1 failed."
    }
}

Write-Host "Starting Bulgaria Auto CarMarket (all profiles, including AI)..."
if ($NoBuild) {
    & docker compose --profile ai up -d --remove-orphans
}
else {
    & docker compose --profile ai up -d --build --remove-orphans
}
if ($LASTEXITCODE -ne 0) {
    throw "docker compose up failed."
}

if (-not (Wait-ForUrl -Url "http://localhost:$BackendPort/api/health" -Label "backend health")) {
    throw "Backend did not become healthy within $WaitSeconds seconds. Inspect: docker compose logs --tail=100 backend"
}
if (-not (Wait-ForUrl -Url "http://localhost:$FrontendPort/" -Label "frontend")) {
    throw "Frontend did not become available within $WaitSeconds seconds. Inspect: docker compose logs --tail=100 frontend"
}

$ModelList = ""
$attempt = 0
while ($attempt -lt 15 -and [string]::IsNullOrWhiteSpace($ModelList)) {
    $ModelList = (& docker compose exec -T ollama ollama list 2>$null) -join "`n"
    if ([string]::IsNullOrWhiteSpace($ModelList)) {
        $attempt++
        Start-Sleep -Seconds 2
    }
}

$ModelState = "недостъпен"
if (-not [string]::IsNullOrWhiteSpace($ModelList)) {
    $pattern = "(?m)^$([regex]::Escape($OllamaModel))\s"
    if ([regex]::IsMatch($ModelList, $pattern)) {
        $ModelState = "инсталиран"
    }
    else {
        $ModelState = "липсва"
        if ($PullModel) {
            Write-Host "Pulling Ollama model $OllamaModel..."
            & docker compose exec -T ollama ollama pull $OllamaModel
            if ($LASTEXITCODE -eq 0) {
                $ModelState = "инсталиран (изтеглен сега)"
            }
            else {
                $ModelState = "липсва (изтеглянето е неуспешно)"
            }
        }
    }
}

Write-Host ""
Write-Host "Bulgaria Auto CarMarket is running."
Write-Host "  Dashboard:    http://localhost:$FrontendPort"
Write-Host "  API docs:     http://localhost:$BackendPort/docs"
Write-Host "  MinIO:        http://localhost:$MinioConsolePort"
Write-Host "  Ollama model: $OllamaModel ($ModelState)"
Write-Host ""
Write-Host "Admin API key is read from .env (ADMIN_API_KEY). Enter it in the dashboard top bar."
if ($ModelState -eq "липсва") {
    Write-Host "Pull the model with: docker compose exec ollama ollama pull $OllamaModel"
}
Write-Host "Show status with: docker compose --profile ai ps"
Write-Host "Stop everything with: .\scripts\stop.ps1"
