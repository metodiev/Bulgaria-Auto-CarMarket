#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
cd "$ROOT_DIR"

APP_ID="bg.carmarket.app"
DEVICE=""
NO_BUILD=0
NO_INSTALL=0
BUILD_DIR="$ROOT_DIR/ios/App/build"
APP_PATH="$BUILD_DIR/Build/Products/Debug-iphonesimulator/App.app"

usage() {
    cat <<'EOF'
Usage: scripts/start-ios.sh [options]

Builds and runs Bulgaria Auto CarMarket in the iOS Simulator. Requires macOS
with Xcode 16 or newer.

Options:
  --device NAME     Simulator name or UDID (default: booted iPhone, else first available)
  --no-build        Skip the web build and xcodebuild; reuse the existing .app
  --no-install      Only boot the simulator; do not install/launch the app
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
        --no-build)
            NO_BUILD=1
            shift
            ;;
        --no-install)
            NO_INSTALL=1
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

[ "$(uname -s)" = "Darwin" ] || die "iOS apps require macOS with Xcode. This script cannot run on $(uname -s)."
command -v xcrun >/dev/null 2>&1 || die "xcrun was not found. Install Xcode and its command-line tools."
command -v xcodebuild >/dev/null 2>&1 || die "xcodebuild was not found. Install Xcode."

simulator_lines() {
    xcrun simctl list devices available 2>/dev/null |
        grep -E '^[[:space:]]+(iPhone|iPad)' || true
}

line_name() {
    printf '%s' "$1" | sed -E 's/^[[:space:]]+//; s/ \([0-9A-Fa-f-]{36}\) \((Booted|Shutdown)\).*$//'
}

line_udid() {
    printf '%s\n' "$1" | sed -nE 's/.*\(([0-9A-Fa-f-]{36})\).*$/\1/p'
}

if [ -n "$DEVICE" ]; then
    if printf '%s' "$DEVICE" | grep -Eq '^[0-9A-Fa-f-]{36}$'; then
        LINE=$(simulator_lines | grep -F "($DEVICE)" | head -n 1)
    else
        LINE=$(simulator_lines | grep -F "$DEVICE (" | head -n 1)
    fi
    [ -n "$LINE" ] || die "Simulator '$DEVICE' was not found. Run: xcrun simctl list devices available"
else
    LINE=$(simulator_lines | grep -F "(Booted)" | head -n 1)
    if [ -z "$LINE" ]; then
        LINE=$(simulator_lines | head -n 1)
    fi
    [ -n "$LINE" ] || die "No iOS simulator is available. Install a simulator runtime in Xcode."
fi

UDID=$(line_udid "$LINE")
NAME=$(line_name "$LINE")
[ -n "$UDID" ] || die "Could not resolve the simulator UDID."

if printf '%s' "$LINE" | grep -q "(Booted)"; then
    say "Using booted simulator: $NAME ($UDID)"
else
    say "Booting simulator: $NAME ($UDID)"
    xcrun simctl boot "$UDID" 2>/dev/null || true
fi

open -a Simulator >/dev/null 2>&1 || true
xcrun simctl bootstatus "$UDID" -b

if [ "$NO_BUILD" -eq 0 ]; then
    command -v npm >/dev/null 2>&1 || die "npm was not found in PATH."
    [ -d "$ROOT_DIR/frontend/node_modules" ] || die "frontend/node_modules is missing. Run: cd frontend && npm ci"

    say "Building web assets and the iOS app…"
    (cd "$ROOT_DIR/frontend" && npm run mobile:ios)
    (
        cd "$ROOT_DIR/ios/App"
        xcodebuild \
            -project App.xcodeproj \
            -target App \
            -configuration Debug \
            -sdk iphonesimulator \
            -derivedDataPath "$BUILD_DIR" \
            CODE_SIGNING_ALLOWED=NO \
            build
    )
fi

if [ "$NO_INSTALL" -eq 0 ]; then
    [ -d "$APP_PATH" ] || die "App bundle not found at $APP_PATH. Run without --no-build first."
    say "Installing the app on $NAME…"
    xcrun simctl install "$UDID" "$APP_PATH"
    xcrun simctl terminate "$UDID" "$APP_ID" >/dev/null 2>&1 || true
    xcrun simctl launch "$UDID" "$APP_ID"
    say "Launched Bulgaria Auto CarMarket in the iOS Simulator."
fi

BACKEND_PORT=8000
if [ -f "$ROOT_DIR/.env" ]; then
    ENV_PORT=$(sed -n 's/^BACKEND_PORT=//p' "$ROOT_DIR/.env" | tail -n 1 | tr -d '\r')
    [ -n "$ENV_PORT" ] && BACKEND_PORT=$ENV_PORT
fi

say ""
if command -v curl >/dev/null 2>&1 &&
    curl -fsS --max-time 2 "http://localhost:$BACKEND_PORT/api/health" >/dev/null 2>&1; then
    say "Backend is reachable at http://localhost:$BACKEND_PORT."
else
    say "Warning: the backend is not reachable at http://localhost:$BACKEND_PORT."
    say "Start it with: scripts/start.sh"
fi
say "In the iOS Simulator use http://localhost:$BACKEND_PORT as the server URL."
say "Stop it with: scripts/stop-ios.sh"
