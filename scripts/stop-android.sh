#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
cd "$ROOT_DIR"

APP_ID="bg.carmarket.app"
DEVICE=""
KEEP_EMULATOR=0

usage() {
    cat <<'EOF'
Usage: scripts/stop-android.sh [options]

Force-stops Bulgaria Auto CarMarket on connected Android devices and shuts down
running Android emulators. App data and the installed APK are kept.

Options:
  --device SERIAL   Only stop this device/emulator
  --keep-emulator   Stop the app but leave the emulator running
  -h, --help        Show this help
EOF
}

die() {
    printf 'Error: %s\n' "$*" >&2
    exit 1
}

say() {
    printf '%s\n' "$*"
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --device)
            [ "$#" -ge 2 ] || die "--device requires a value."
            DEVICE=$2
            shift 2
            ;;
        --keep-emulator)
            KEEP_EMULATOR=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf 'Unknown option: %s\n' "$1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

resolve_sdk() {
    for candidate in "${ANDROID_HOME:-}" "${ANDROID_SDK_ROOT:-}"; do
        if [ -n "$candidate" ] &&
            { [ -x "$candidate/platform-tools/adb" ] || [ -x "$candidate/platform-tools/adb.exe" ]; }; then
            printf '%s' "$candidate"
            return 0
        fi
    done

    if [ -f "$ROOT_DIR/android/local.properties" ]; then
        candidate=$(sed -n 's/^sdk\.dir=//p' "$ROOT_DIR/android/local.properties" | tail -n 1 | tr -d '\r')
        if [ -n "$candidate" ]; then
            candidate=$(printf '%s' "$candidate" | sed 's/\\\\/\//g; s/\\:/:/g')
            if [ -x "$candidate/platform-tools/adb" ] || [ -x "$candidate/platform-tools/adb.exe" ]; then
                printf '%s' "$candidate"
                return 0
            fi
        fi
    fi

    for candidate in \
        "$HOME/Library/Android/sdk" \
        "$HOME/Android/Sdk" \
        "/usr/local/share/android-sdk" \
        "/opt/android-sdk"; do
        if [ -x "$candidate/platform-tools/adb" ] || [ -x "$candidate/platform-tools/adb.exe" ]; then
            printf '%s' "$candidate"
            return 0
        fi
    done

    return 1
}

ANDROID_SDK=$(resolve_sdk || true)
if [ -n "$ANDROID_SDK" ]; then
    if [ -x "$ANDROID_SDK/platform-tools/adb" ]; then
        ADB="$ANDROID_SDK/platform-tools/adb"
    else
        ADB="$ANDROID_SDK/platform-tools/adb.exe"
    fi
else
    ADB=$(command -v adb 2>/dev/null || true)
fi
[ -n "$ADB" ] && [ -x "$ADB" ] || die "adb was not found. Install Android platform-tools or set ANDROID_HOME."

if [ -n "$DEVICE" ]; then
    SERIALS=$DEVICE
    if ! "$ADB" devices 2>/dev/null | tr -d '\r' | awk '$1 == "'"$DEVICE"'" && $2 == "device" { found = 1 } END { exit !found }'; then
        die "Device '$DEVICE' is not connected or is not ready."
    fi
else
    SERIALS=$("$ADB" devices 2>/dev/null | tr -d '\r' | awk 'NR > 1 && $2 == "device" { print $1 }')
fi

if [ -z "$SERIALS" ]; then
    say "No running Android devices or emulators found."
    exit 0
fi

for SERIAL in $SERIALS; do
    say "Stopping the app on $SERIAL…"
    "$ADB" -s "$SERIAL" shell am force-stop "$APP_ID" >/dev/null 2>&1 || true

    if [ "$KEEP_EMULATOR" -eq 0 ]; then
        case "$SERIAL" in
            emulator-*)
                if "$ADB" -s "$SERIAL" emu kill >/dev/null 2>&1; then
                    say "Shut down emulator $SERIAL."
                else
                    say "Could not shut down emulator $SERIAL (it may already be stopping)."
                fi
                ;;
        esac
    fi
done

if [ "$KEEP_EMULATOR" -eq 1 ]; then
    say "App stopped; emulator left running."
else
    say "Android app stopped."
fi
