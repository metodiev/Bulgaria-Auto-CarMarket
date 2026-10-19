param(
    [string]$Avd,
    [string]$Device,
    [switch]$Headless,
    [switch]$NoBuild,
    [switch]$NoInstall,
    [ValidateRange(10, 3600)]
    [int]$WaitSeconds = 180,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$AppId = "bg.carmarket.app"
$Activity = "bg.carmarket.app/.MainActivity"
$ApkPath = Join-Path $Root "android\app\build\outputs\apk\debug\app-debug.apk"

function Show-Usage {
    @"
Usage: scripts\start-android.ps1 [options]

Builds the web app and debug APK, starts an Android emulator when no device is
connected, then installs and launches Bulgaria Auto CarMarket.

Options:
  -Avd NAME        AVD to start (default: `$env:ANDROID_AVD or the first AVD)
  -Device SERIAL   Use an already connected device/emulator
  -Headless        Start the emulator without a window
  -NoBuild         Skip the web build and Gradle; reuse the existing APK
  -NoInstall       Only make sure a device is running; do not install/launch
  -WaitSeconds N   Emulator boot timeout in seconds (default: 180)
  -Help            Show this help
"@
}

function Fail {
    param([string]$Message)
    Write-Host "Error: $Message" -ForegroundColor Red
    exit 1
}

function Resolve-AndroidSdk {
    $candidates = @()
    if ($env:ANDROID_HOME) { $candidates += $env:ANDROID_HOME }
    if ($env:ANDROID_SDK_ROOT) { $candidates += $env:ANDROID_SDK_ROOT }

    $properties = Join-Path $Root "android\local.properties"
    if (Test-Path $properties) {
        $line = Get-Content $properties |
            Where-Object { $_ -match '^sdk\.dir=' } |
            Select-Object -Last 1
        if ($line) {
            $value = ($line -split '=', 2)[1].Trim()
            $value = $value -replace '\\\\', '\' -replace '\\:', ':'
            $candidates += $value
        }
    }

    if ($env:LOCALAPPDATA) {
        $candidates += (Join-Path $env:LOCALAPPDATA "Android\Sdk")
    }
    $candidates += (Join-Path $HOME "AppData\Local\Android\Sdk")

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path (Join-Path $candidate "platform-tools\adb.exe"))) {
            return $candidate
        }
    }
    return $null
}

function Get-AdbDevices {
    $lines = & $Adb devices 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "adb devices failed."
    }
    $devices = @()
    foreach ($line in ($lines | Select-Object -Skip 1)) {
        $text = $line.Trim()
        if (-not $text) { continue }
        $parts = $text -split '\s+'
        if ($parts.Count -ge 2 -and $parts[1] -eq "device") {
            $devices += $parts[0]
        }
    }
    return $devices
}

if ($Help) {
    Show-Usage
    exit 0
}

$Sdk = Resolve-AndroidSdk
$Adb = $null
$Emulator = $null
if ($Sdk) {
    $Adb = Join-Path $Sdk "platform-tools\adb.exe"
    $Emulator = Join-Path $Sdk "emulator\emulator.exe"
}
if (-not $Adb -or -not (Test-Path $Adb)) {
    $adbCommand = Get-Command adb -ErrorAction SilentlyContinue
    if ($adbCommand) { $Adb = $adbCommand.Source }
}
if (-not $Adb -or -not (Test-Path $Adb)) {
    Fail "adb was not found. Install Android platform-tools or set ANDROID_HOME."
}
if (-not $Emulator -or -not (Test-Path $Emulator)) {
    $emulatorCommand = Get-Command emulator -ErrorAction SilentlyContinue
    if ($emulatorCommand) { $Emulator = $emulatorCommand.Source }
}

if (-not $NoBuild) {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        Fail "npm was not found in PATH."
    }
    if (-not (Get-Command java -ErrorAction SilentlyContinue)) {
        Fail "Java was not found in PATH. JDK 21 is required."
    }
    if (-not (Test-Path (Join-Path $Root "frontend\node_modules"))) {
        Fail "frontend\node_modules is missing. Run: cd frontend; npm ci"
    }

    Write-Host "Building web assets and the Android debug APK..."
    Push-Location (Join-Path $Root "frontend")
    try {
        npm run mobile:android
        if ($LASTEXITCODE -ne 0) { throw "npm run mobile:android failed." }
    }
    finally {
        Pop-Location
    }

    if ($Sdk) {
        $env:ANDROID_HOME = $Sdk
        $env:ANDROID_SDK_ROOT = $Sdk
    }
    Push-Location (Join-Path $Root "android")
    try {
        & .\gradlew.bat assembleDebug
        if ($LASTEXITCODE -ne 0) { throw "Gradle assembleDebug failed." }
    }
    finally {
        Pop-Location
    }
}

$devices = @(Get-AdbDevices)
$selected = $null
if ($Device) {
    if ($devices -notcontains $Device) {
        Fail "Device '$Device' is not connected or is not ready. Run: adb devices"
    }
    $selected = $Device
}
elseif ($devices.Count -gt 0) {
    $selected = $devices[0]
}

if (-not $selected) {
    if (-not $Emulator -or -not (Test-Path $Emulator)) {
        Fail "No Android device is connected and the emulator binary was not found."
    }
    if (-not $Avd) {
        $Avd = $env:ANDROID_AVD
    }
    if (-not $Avd) {
        $Avd = @(& $Emulator -list-avds 2>$null) | Select-Object -First 1
    }
    if (-not $Avd) {
        Fail "No AVD is available. Create one in Android Studio or pass -Avd NAME."
    }

    $before = @(Get-AdbDevices)
    $logPath = Join-Path ([IO.Path]::GetTempPath()) "carmarket-android-emulator.log"
    $errorLogPath = Join-Path ([IO.Path]::GetTempPath()) "carmarket-android-emulator.err.log"
    $arguments = @(
        "-avd", $Avd,
        "-no-audio",
        "-no-boot-anim",
        "-gpu", "swiftshader_indirect"
    )
    if ($Headless) {
        $arguments += "-no-window"
    }

    $process = Start-Process -FilePath $Emulator `
        -ArgumentList $arguments `
        -PassThru `
        -WindowStyle Hidden `
        -RedirectStandardOutput $logPath `
        -RedirectStandardError $errorLogPath
    Write-Host "Started emulator '$Avd' (PID $($process.Id), log $logPath)."

    $deadline = (Get-Date).AddSeconds($WaitSeconds)
    while ((Get-Date) -lt $deadline) {
        if ($process.HasExited) {
            Fail "The emulator exited during startup. See $logPath and $errorLogPath."
        }
        foreach ($candidate in @(Get-AdbDevices)) {
            if ($before -notcontains $candidate) {
                $selected = $candidate
                break
            }
        }
        if ($selected) { break }
        Start-Sleep -Seconds 2
    }
    if (-not $selected) {
        Fail "Timed out waiting for the emulator to appear. See $logPath."
    }
}

Write-Host "Waiting for $selected to finish booting..."
$deadline = (Get-Date).AddSeconds($WaitSeconds)
$booted = $false
while ((Get-Date) -lt $deadline) {
    $state = (& $Adb -s $selected get-state 2>$null | Out-String).Trim()
    $boot = (& $Adb -s $selected shell getprop sys.boot_completed 2>$null | Out-String).Trim()
    if ($state -eq "device" -and $boot -eq "1") {
        $booted = $true
        break
    }
    Start-Sleep -Seconds 2
}
if (-not $booted) {
    Fail "Timed out waiting for $selected to boot."
}

$backendPort = 8000
if (Test-Path (Join-Path $Root ".env")) {
    $envLine = Get-Content (Join-Path $Root ".env") |
        Where-Object { $_ -match '^BACKEND_PORT=' } |
        Select-Object -Last 1
    if ($envLine) {
        $value = ($envLine -split '=', 2)[1].Trim()
        if ($value) { $backendPort = [int]$value }
    }
}

if (-not $NoInstall) {
    if (-not (Test-Path $ApkPath)) {
        Fail "APK not found at $ApkPath. Run without -NoBuild first."
    }
    Write-Host "Installing the APK on $selected..."
    $installOutput = & $Adb -s $selected install -r $ApkPath 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0 -or $installOutput -notmatch "Success") {
        Write-Host $installOutput
        Fail "adb install failed."
    }

    & $Adb -s $selected shell am force-stop $AppId | Out-Null
    & $Adb -s $selected shell am start -n $Activity | Out-Null
    Write-Host "Launched Bulgaria Auto CarMarket on $selected."
}

Write-Host ""
$backendOk = $false
try {
    $response = Invoke-WebRequest -Uri "http://localhost:$backendPort/api/health" -UseBasicParsing -TimeoutSec 2
    $backendOk = $response.StatusCode -ge 200 -and $response.StatusCode -lt 400
}
catch {
    $backendOk = $false
}
if ($backendOk) {
    Write-Host "Backend is reachable at http://localhost:$backendPort."
}
else {
    Write-Host "Warning: the backend is not reachable at http://localhost:$backendPort."
    Write-Host "Start it with: scripts\start.ps1"
}

if ($selected -like "emulator-*") {
    Write-Host "In the Android emulator use http://10.0.2.2:$backendPort as the server URL."
}
else {
    Write-Host "On a physical device use the host machine's LAN IP, e.g. http://192.168.1.10:$backendPort."
}
Write-Host "Stop it with: scripts\stop-android.ps1"
