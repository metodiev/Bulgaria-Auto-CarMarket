#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
cd "$ROOT_DIR"

BUILD=1
RESTART=0
PULL_MODEL=0
WAIT_SECONDS=${START_WAIT_SECONDS:-180}

usage() {
    cat <<'EOF'
Usage: scripts/start.sh [options]

Starts the complete Bulgaria Auto CarMarket stack (core services + AI profile).

Options:
  --no-build     Start without rebuilding images
  --restart      Stop everything first, then start again
  --pull-model   Pull OLLAMA_MODEL if it is not installed (can take several GB)
  -h, --help     Show this help

Environment:
  START_WAIT_SECONDS   Seconds to wait for health checks (default: 180)
EOF
}

for arg in "$@"; do
    case "$arg" in
        --no-build) BUILD=0 ;;
        --restart) RESTART=1 ;;
        --pull-model) PULL_MODEL=1 ;;
        -h|--help) usage; exit 0 ;;
        *)
            echo "Unknown option: $arg" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker was not found in PATH. Install Docker Engine or Docker Desktop and try again." >&2
    exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
    echo "Docker Compose v2 is required (docker compose)." >&2
    exit 1
fi
if ! docker info >/dev/null 2>&1; then
    echo "The Docker daemon is not reachable. Start Docker Desktop / Docker Engine first." >&2
    exit 1
fi

if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "Created .env from .env.example."
        echo "Review ADMIN_API_KEY and all passwords before exposing the app."
    else
        echo "Missing .env and .env.example. Cannot start." >&2
        exit 1
    fi
fi

read_env() {
    name=$1
    default=$2
    value=$(grep -E "^[[:space:]]*${name}=" .env 2>/dev/null | tail -n 1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//; s/[[:space:]]*$//' || true)
    if [ -z "$value" ]; then
        printf '%s' "$default"
    else
        printf '%s' "$value"
    fi
}

BACKEND_PORT=$(read_env BACKEND_PORT 8000)
FRONTEND_PORT=$(read_env FRONTEND_PORT 8080)
OLLAMA_MODEL=$(read_env OLLAMA_MODEL qwen3:4b)

if [ "$RESTART" -eq 1 ]; then
    echo "Restart requested: stopping the current stack first."
    sh "$SCRIPT_DIR/stop.sh"
fi

echo "Starting Bulgaria Auto CarMarket (all profiles, including AI)…"
if [ "$BUILD" -eq 1 ]; then
    docker compose --profile ai up -d --build --remove-orphans
else
    docker compose --profile ai up -d --remove-orphans
fi

http_ok() {
    url=$1
    if command -v curl >/dev/null 2>&1; then
        curl -fsS -o /dev/null --max-time 3 "$url"
    elif command -v wget >/dev/null 2>&1; then
        wget -q -O /dev/null --timeout=3 "$url"
    else
        return 0
    fi
}

wait_for_url() {
    url=$1
    label=$2
    elapsed=0
    printf 'Waiting for %s' "$label"
    while [ "$elapsed" -lt "$WAIT_SECONDS" ]; do
        if http_ok "$url"; then
            printf ' ready\n'
            return 0
        fi
        printf '.'
        sleep 3
        elapsed=$((elapsed + 3))
    done
    printf ' timed out\n' >&2
    return 1
}

if ! wait_for_url "http://localhost:${BACKEND_PORT}/api/health" "backend health"; then
    echo "Backend did not become healthy within ${WAIT_SECONDS}s." >&2
    echo "Inspect logs with: docker compose logs --tail=100 backend" >&2
    exit 1
fi

wait_for_url "http://localhost:${FRONTEND_PORT}/" "frontend" || {
    echo "Frontend did not become available within ${WAIT_SECONDS}s." >&2
    echo "Inspect logs with: docker compose logs --tail=100 frontend" >&2
    exit 1
}

MODEL_STATE="инсталиран"
if ! docker compose exec -T ollama ollama list 2>/dev/null | awk 'NR > 1 { print $1 }' | grep -qx "$OLLAMA_MODEL"; then
    if [ "$PULL_MODEL" -eq 1 ]; then
        echo "Pulling Ollama model ${OLLAMA_MODEL}…"
        if docker compose exec -T ollama ollama pull "$OLLAMA_MODEL"; then
            MODEL_STATE="инсталиран (изтеглен сега)"
        else
            MODEL_STATE="липсва (изтеглянето е неуспешно)"
        fi
    else
        MODEL_STATE="липсва"
    fi
fi

echo
echo "Bulgaria Auto CarMarket is running."
echo "  Dashboard:   http://localhost:${FRONTEND_PORT}"
echo "  API docs:    http://localhost:${BACKEND_PORT}/docs"
echo "  MinIO:       http://localhost:$(read_env MINIO_CONSOLE_PORT 9001)"
echo "  Ollama model: ${OLLAMA_MODEL} (${MODEL_STATE})"
echo
echo "Admin API key is read from .env (ADMIN_API_KEY). Enter it in the dashboard top bar."
if [ "$MODEL_STATE" = "липсва" ]; then
    echo "Pull the model with: docker compose exec ollama ollama pull ${OLLAMA_MODEL}"
fi
echo "Show status with: docker compose --profile ai ps"
echo "Stop everything with: ./scripts/stop.sh"
