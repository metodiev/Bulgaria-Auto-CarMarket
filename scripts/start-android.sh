#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
cd "$ROOT_DIR"

APP_ID="bg.carmarket.app"
ACTIVITY="bg.carmarket.app/.MainActivity"
APK_PATH="$ROOT_DIR/android/app/build/outputs/apk/debug/app-debug.apk"

AVD=""
DEVICE=""
HEADLESS=0
NO_BUILD=0
NO_INSTALL=0
WAIT_SECONDS=180

usage() {
    cat <<'EOF'
Usage: scripts/start-android.sh [options]

Builds the web app and debug APK, starts an Android emulator when no device is
connected, then installs and launches Bulgaria Auto CarMarket.

Options:
  --avd NAME        AVD to start (default: $ANDROID_AVD or the first AVD)
  --device SERIAL   Use an already connected device/emulator
  --headless        Start the emulator without a window
  --no-build        Skip the web build and Gradle; reuse the existing APK
  --no-install      Only make sure a device is running; do not install/launch
  --wait SECONDS    Emulator boot timeout in seconds (default: 180)
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
        --avd)
            [ "$#" -ge 2 ] || die "--avd requires a value."
            AVD=$2
            shift 2
            ;;
        --device)
            [ "$#" -ge 2 ] || die "--device requires a value."
            DEVICE=$2
            shift 2
            ;;
        --headless)
            HEADLESS=1
            shift
            ;;
        --no-build)
            NO_BUILD=1
            shift
            ;;
        --no-install)
            NO_INSTALL=1
            shift
            ;;
        --wait)
            [ "$#" -ge 2 ] || die "--wait requires a value."
            WAIT_SECONDS=$2
            shift 2
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

case "$WAIT_SECONDS" in
    ''|*[!0-9]*) die "--wait must be a whole number of seconds." ;;
esac

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
    if [ -x "$ANDROID_SDK/emulator/emulator" ]; then
        EMULATOR="$ANDROID_SDK/emulator/emulator"
    elif [ -x "$ANDROID_SDK/emulator/emulator.exe" ]; then
        EMULATOR="$ANDROID_SDK/emulator/emulator.exe"
    else
        EMULATOR=""
    fi
else
    ADB=$(command -v adb 2>/dev/null || true)
    EMULATOR=$(command -v emulator 2>/dev/null || true)
fi

[ -n "$ADB" ] && [ -x "$ADB" ] || die "adb was not found. Install Android platform-tools or set ANDROID_HOME."
[ -n "$EMULATOR" ] || EMULATOR=""
if [ -n "$EMULATOR" ]; then
    [ -x "$EMULATOR" ] || EMULATOR=""
fi

adb_devices() {
    "$ADB" devices 2>/dev/null | tr -d '\r' | awk 'NR > 1 && $2 == "device" { print $1 }'
}

select_existing_device() {
    if [ -n "$DEVICE" ]; then
        if ! adb_devices | grep -qx "$DEVICE"; then
            die "Device '$DEVICE' is not connected or is not ready. Run: adb devices"
        fi
        printf '%s' "$DEVICE"
        return 0
    fi
    adb_devices | head -n 1
}

SELECTED=$(select_existing_device)

if [ "$NO_BUILD" -eq 0 ]; then
    command -v npm >/dev/null 2>&1 || die "npm was not found in PATH."
    command -v java >/dev/null 2>&1 || die "Java was not found in PATH. JDK 21 is required."
    [ -d "$ROOT_DIR/frontend/node_modules" ] || die "frontend/node_modules is missing. Run: cd frontend && npm ci"

    say "Building web assets and the Android debug APK…"
    (cd "$ROOT_DIR/frontend" && npm run mobile:android)
    (
        cd "$ROOT_DIR/android"
        if [ -n "$ANDROID_SDK" ]; then
            export ANDROID_HOME="$ANDROID_SDK"
            export ANDROID_SDK_ROOT="$ANDROID_SDK"
        fi
        if [ -x ./gradlew ]; then
            ./gradlew assembleDebug
        else
            sh ./gradlew assembleDebug
        fi
    )
fi

if [ -z "$SELECTED" ]; then
    [ -n "$EMULATOR" ] || die "No Android device is connected and the emulator binary was not found."
    if [ -z "$AVD" ]; then
        AVD=${ANDROID_AVD:-}
    fi
    if [ -z "$AVD" ]; then
        AVD=$("$EMULATOR" -list-avds 2>/dev/null | head -n 1)
    fi
    [ -n "$AVD" ] || die "No AVD is available. Create one in Android Studio or pass --avd NAME."

    BEFORE=$(adb_devices | tr '\n' ' ')
    LOG_FILE="${TMPDIR:-/tmp}/carmarket-android-emulator.log"

    if [ "$HEADLESS" -eq 1 ]; then
        "$EMULATOR" -avd "$AVD" -no-window -no-audio -no-boot-anim \
            -gpu swiftshader_indirect >"$LOG_FILE" 2>&1 &
    else
        "$EMULATOR" -avd "$AVD" -no-audio -no-boot-anim \
            -gpu swiftshader_indirect >"$LOG_FILE" 2>&1 &
    fi
    EMULATOR_PID=$!
    say "Started emulator '$AVD' (PID $EMULATOR_PID, log $LOG_FILE)."

    DEADLINE=$(( $(date +%s) + WAIT_SECONDS ))
    while [ "$(date +%s)" -lt "$DEADLINE" ]; do
        if ! kill -0 "$EMULATOR_PID" 2>/dev/null; then
            die "The emulator exited during startup. See $LOG_FILE."
        fi
        for candidate in $(adb_devices); do
            case " $BEFORE " in
                *" $candidate "*) continue ;;
            esac
            SELECTED=$candidate
            break
        done
        [ -n "$SELECTED" ] && break
        sleep 2
    done
    [ -n "$SELECTED" ] || die "Timed out waiting for the emulator to appear. See $LOG_FILE."
fi

say "Waiting for $SELECTED to finish booting…"
BOOTED=0
ELAPSED=0
while [ "$ELAPSED" -lt "$WAIT_SECONDS" ]; do
    STATE=$("$ADB" -s "$SELECTED" get-state 2>/dev/null || true)
    BOOT=$("$ADB" -s "$SELECTED" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r\n ' || true)
    if [ "$STATE" = "device" ] && [ "$BOOT" = "1" ]; then
        BOOTED=1
        break
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
done
[ "$BOOTED" -eq 1 ] || die "Timed out waiting for $SELECTED to boot."

BACKEND_PORT=8000
if [ -f "$ROOT_DIR/.env" ]; then
    ENV_PORT=$(sed -n 's/^BACKEND_PORT=//p' "$ROOT_DIR/.env" | tail -n 1 | tr -d '\r')
    [ -n "$ENV_PORT" ] && BACKEND_PORT=$ENV_PORT
fi

if [ "$NO_INSTALL" -eq 0 ]; then
    [ -f "$APK_PATH" ] || die "APK not found at $APK_PATH. Run without --no-build first."
    say "Installing the APK on $SELECTED…"
    INSTALL_OUTPUT=$("$ADB" -s "$SELECTED" install -r "$APK_PATH" 2>&1) || {
        printf '%s\n' "$INSTALL_OUTPUT" >&2
        die "adb install failed."
    }
    printf '%s\n' "$INSTALL_OUTPUT" | grep -q "Success" || {
        printf '%s\n' "$INSTALL_OUTPUT" >&2
        die "adb install did not report success."
    }

    "$ADB" -s "$SELECTED" shell am force-stop "$APP_ID" >/dev/null 2>&1 || true
    "$ADB" -s "$SELECTED" shell am start -n "$ACTIVITY" >/dev/null
    say "Launched Bulgaria Auto CarMarket on $SELECTED."
fi

say ""
if command -v curl >/dev/null 2>&1 &&
    curl -fsS --max-time 2 "http://localhost:$BACKEND_PORT/api/health" >/dev/null 2>&1; then
    say "Backend is reachable at http://localhost:$BACKEND_PORT."
else
    say "Warning: the backend is not reachable at http://localhost:$BACKEND_PORT."
    say "Start it with: scripts/start.sh"
fi

case "$SELECTED" in
    emulator-*)
        say "In the Android emulator use http://10.0.2.2:$BACKEND_PORT as the server URL."
        ;;
    *)
        say "On a physical device use the host machine's LAN IP, e.g. http://192.168.1.10:$BACKEND_PORT."
        ;;
esac
say "Stop it with: scripts/stop-android.sh"
