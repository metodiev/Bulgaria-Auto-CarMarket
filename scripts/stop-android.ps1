param(
    [string]$Device,
    [switch]$KeepEmulator,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$AppId = "bg.carmarket.app"

function Show-Usage {
    @"
Usage: scripts\stop-android.ps1 [options]

Force-stops Bulgaria Auto CarMarket on connected Android devices and shuts down
running Android emulators. App data and the installed APK are kept.

Options:
  -Device SERIAL   Only stop this device/emulator
  -KeepEmulator    Stop the app but leave the emulator running
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
if ($Sdk) {
    $Adb = Join-Path $Sdk "platform-tools\adb.exe"
}
if (-not $Adb -or -not (Test-Path $Adb)) {
    $adbCommand = Get-Command adb -ErrorAction SilentlyContinue
    if ($adbCommand) { $Adb = $adbCommand.Source }
}
if (-not $Adb -or -not (Test-Path $Adb)) {
    Fail "adb was not found. Install Android platform-tools or set ANDROID_HOME."
}

$devices = @(Get-AdbDevices)
if ($Device) {
    if ($devices -notcontains $Device) {
        Fail "Device '$Device' is not connected or is not ready."
    }
    $devices = @($Device)
}

if ($devices.Count -eq 0) {
    Write-Host "No running Android devices or emulators found."
    exit 0
}

foreach ($serial in $devices) {
    Write-Host "Stopping the app on $serial..."
    & $Adb -s $serial shell am force-stop $AppId | Out-Null

    if (-not $KeepEmulator -and $serial -like "emulator-*") {
        & $Adb -s $serial emu kill | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Shut down emulator $serial."
        }
        else {
            Write-Host "Could not shut down emulator $serial (it may already be stopping)."
        }
    }
}

if ($KeepEmulator) {
    Write-Host "App stopped; emulator left running."
}
else {
    Write-Host "Android app stopped."
}
