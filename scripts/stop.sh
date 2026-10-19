#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
cd "$ROOT_DIR"

REMOVE_VOLUMES=0
ASSUME_YES=0

usage() {
    cat <<'EOF'
Usage: scripts/stop.sh [options]

Stops and removes every Bulgaria Auto CarMarket container, including the AI profile.
Named volumes (PostgreSQL, Redis, MinIO, Ollama) are kept unless --volumes is given.

Options:
  --volumes      Also delete all persistent data volumes (DESTRUCTIVE)
  --yes          Skip the confirmation prompt for --volumes
  -h, --help     Show this help
EOF
}

for arg in "$@"; do
    case "$arg" in
        --volumes) REMOVE_VOLUMES=1 ;;
        --yes|-y) ASSUME_YES=1 ;;
        -h|--help) usage; exit 0 ;;
        *)
            echo "Unknown option: $arg" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker was not found in PATH." >&2
    exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
    echo "Docker Compose v2 is required (docker compose)." >&2
    exit 1
fi

if [ "$REMOVE_VOLUMES" -eq 1 ] && [ "$ASSUME_YES" -eq 0 ]; then
    printf 'This deletes PostgreSQL, Redis, MinIO and Ollama data. Type "yes" to continue: '
    read -r answer
    if [ "$answer" != "yes" ]; then
        echo "Aborted. No data was deleted."
        exit 1
    fi
fi

if [ "$REMOVE_VOLUMES" -eq 1 ]; then
    echo "Stopping the stack and deleting all persistent volumes…"
    docker compose --profile ai down --remove-orphans --volumes
else
    echo "Stopping the complete stack (core + ai)…"
    docker compose --profile ai down --remove-orphans
fi

echo
echo "Bulgaria Auto CarMarket is stopped."
echo "Persistent volumes are preserved."
echo "Start again with: ./scripts/start.sh"
