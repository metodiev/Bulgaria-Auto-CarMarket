#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
cd "$ROOT_DIR"

APP_ID="bg.carmarket.app"
DEVICE=""
KEEP_SIMULATOR=0

usage() {
    cat <<'EOF'
Usage: scripts/stop-ios.sh [options]

Stops Bulgaria Auto CarMarket in the iOS Simulator and shuts the simulator down.
The app remains installed.

Options:
  --device NAME       Simulator name or UDID (default: all booted simulators)
  --keep-simulator    Stop the app but leave the simulator running
  -h, --help          Show this help
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
        --keep-simulator)
            KEEP_SIMULATOR=1
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

[ "$(uname -s)" = "Darwin" ] || die "iOS simulators require macOS with Xcode. This script cannot run on $(uname -s)."
command -v xcrun >/dev/null 2>&1 || die "xcrun was not found. Install Xcode and its command-line tools."

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
    UDIDS=$(line_udid "$LINE")
else
    UDIDS=$(simulator_lines | grep -F "(Booted)" | while IFS= read -r line; do
        line_udid "$line"
    done)
fi

if [ -z "$UDIDS" ]; then
    say "No booted iOS simulators found."
    exit 0
fi

for UDID in $UDIDS; do
    NAME=$(line_name "$(simulator_lines | grep -F "($UDID)" | head -n 1)")
    [ -n "$NAME" ] || NAME=$UDID
    say "Stopping the app on $NAME…"
    xcrun simctl terminate "$UDID" "$APP_ID" >/dev/null 2>&1 || true

    if [ "$KEEP_SIMULATOR" -eq 0 ]; then
        if xcrun simctl shutdown "$UDID" >/dev/null 2>&1; then
            say "Shut down $NAME."
        else
            say "Could not shut down $NAME (it may already be stopping)."
        fi
    fi
done

if [ "$KEEP_SIMULATOR" -eq 1 ]; then
    say "App stopped; simulator left running."
else
    say "iOS app stopped."
fi
