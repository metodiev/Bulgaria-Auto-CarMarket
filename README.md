# Bulgaria Auto CarMarket

A self-hosted platform for collecting, normalizing, storing, refreshing, and analyzing
vehicle listings from Bulgarian websites. The whole project is containerized and runs
without any paid external API.

> **Source access notice:** the only connector that is verified and enabled by default is
> **Cars.bg**. The remaining sources are documented as `NEEDS_PERMISSION` or `BLOCKED` and
> are not crawled until access is confirmed. See [docs/SOURCES.md](docs/SOURCES.md)
> (currently written in Bulgarian).

> Българска версия на документацията: [README_BG.md](README_BG.md).

## Table of contents

- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Quick start without AI](#quick-start-without-ai)
- [Application management (start / stop / restart)](#application-management-start--stop--restart)
- [Running with local AI (Ollama)](#running-with-local-ai-ollama)
- [GPU and CPU mode](#gpu-and-cpu-mode)
- [Sources and permitted access](#sources-and-permitted-access)
- [Scraping settings](#scraping-settings)
- [AI analysis](#ai-analysis)
- [REST API](#rest-api)
- [Database and deduplication](#database-and-deduplication)
- [Upgrades and migrations](#upgrades-and-migrations)
- [Backup and restore](#backup-and-restore)
- [Tests](#tests)
- [Verification results](#verification-results)
- [Troubleshooting](#troubleshooting)
- [Known limitations](#known-limitations)
- [Security](#security)
- [Project structure](#project-structure)
- [License](#license)

## Architecture

```text
                         ┌──────────────────────────────┐
                         │  frontend (React + Vite)      │
                         │  nginx :8080, /api proxy      │
                         └──────────────┬───────────────┘
                                        │
                         ┌──────────────▼───────────────┐
                         │  backend (FastAPI :8000)      │
                         │  REST, auth, statistics       │
                         └───┬──────────┬──────────┬────┘
                             │          │          │
                  ┌──────────▼──┐  ┌────▼─────┐  ┌─▼─────────────┐
                  │ PostgreSQL  │  │ Redis     │  │ MinIO (S3)    │
                  │ primary DB  │  │ broker    │  │ images/archive│
                  └─────────────┘  └────┬─────┘  └───────────────┘
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              │                         │                         │
   ┌──────────▼──────────┐   ┌──────────▼──────────┐   ┌─────────▼─────────┐
   │ scraper-worker      │   │ scheduler            │   │ ai-worker         │
   │ Celery queue scrape │   │ Celery beat           │   │ Celery queue ai   │
   │ Playwright archive  │   │ due search jobs       │   │ profile: ai       │
   └─────────────────────┘   └──────────────────────┘   └─────────┬─────────┘
                                                                  │
                                                        ┌─────────▼─────────┐
                                                        │ ollama :11434     │
                                                        │ qwen3:4b          │
                                                        │ profile: ai       │
                                                        └───────────────────┘
```

Services in `docker-compose.yml`:

| Service | Role | Profile |
|---|---|---|
| `frontend` | React dashboard, nginx reverse proxy | core |
| `backend` | FastAPI, migrations, seed, health | core |
| `scraper-worker` | Celery worker for the `scrape` queue, Playwright archives | core |
| `scheduler` | Celery beat for periodic tasks | core |
| `postgres` | PostgreSQL 16 | core |
| `redis` | Redis 7, broker and result backend | core |
| `minio` | S3-compatible object storage | core |
| `minio-init` | one-off volume permission setup | core |
| `ai-worker` | Celery worker for the `ai` queue | `ai` |
| `ollama` | Local LLM server | `ai` |

## Technology stack

- Python 3.12+, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic 2
- PostgreSQL 16, Redis 7, Celery 5
- httpx, BeautifulSoup, Playwright
- React 18, TypeScript, Vite, Tailwind CSS, React Router, lucide-react
- MinIO (S3-compatible object storage)
- Ollama with the **qwen3:4b** model (optional)
- Docker Engine and Docker Compose
- pytest

Dependencies are pinned in [`backend/requirements.txt`](backend/requirements.txt) and
[`frontend/package.json`](frontend/package.json).

> MinIO runs from the pinned community image `alpine/minio` because the official
> `minio/minio` image was not publicly available on Docker Hub at the time of verification.
> The release is pinned and works as S3-compatible storage.

## Quick start without AI

Requirements: Docker Engine 24+, Docker Compose v2, at least ~4 GB of free RAM for the
core services.

> Fastest path: `sh scripts/start.sh` starts the full stack (core + AI profile) and waits
> for health checks. See
> [Application management](#application-management-start--stop--restart).

1. Copy the example configuration and change every password:

   ```bash
   cp .env.example .env
   ```

   Generate a strong admin key, for example:

   ```bash
   openssl rand -hex 32
   ```

   On Windows PowerShell:

   ```powershell
   -join ((48..57) + (97..102) | Get-Random -Count 64 | ForEach-Object {[char]$_})
   ```

   Put the value into `ADMIN_API_KEY`. Also change `POSTGRES_PASSWORD`,
   `MINIO_ROOT_PASSWORD`, and `S3_SECRET_KEY` (the last two must match).

2. Start the core services:

   ```bash
   docker compose up -d --build
   ```

   This command does **not** start Ollama and ai-worker, because they belong to the `ai`
   profile.

3. Verify health checks:

   ```bash
   docker compose ps
   curl http://localhost:8000/api/health
   ```

4. Open:

   - Dashboard: <http://localhost:8080>
   - API docs: <http://localhost:8000/docs>
   - MinIO console: <http://localhost:9001>

5. Enter the admin key in the dashboard's top bar. The key is kept only in
   `sessionStorage` and is sent as `X-Admin-Key`.

6. Start the first Cars.bg run from the **Scraping** page. The defaults allow 1–2 pages
   and a small number of listings so the site is not overloaded.

The backend container waits for PostgreSQL, runs `alembic upgrade head`, seeds sources and
AI settings, and only then starts. Workers and the scheduler depend on the backend health
check.

## Application management (start / stop / restart)

The scripts live in [`scripts/`](scripts/) and manage the **entire** stack — the core
services, the AI profile (`ollama`, `ai-worker`), and the one-off `minio-init` service.

### Linux / macOS / Git Bash

```bash
sh scripts/start.sh              # build + start everything and wait for health checks
sh scripts/start.sh --no-build   # start without rebuilding
sh scripts/start.sh --restart    # stop everything and start it again
sh scripts/start.sh --pull-model # pull OLLAMA_MODEL if it is missing

sh scripts/stop.sh               # stop and remove all containers, keep data
sh scripts/stop.sh --volumes     # DELETE all volumes (asks for confirmation)
```

If the scripts are not executable:

```bash
chmod +x scripts/start.sh scripts/stop.sh
```

### Windows PowerShell

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start.ps1
powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -NoBuild
powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -Restart
powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -PullModel

powershell -ExecutionPolicy Bypass -File scripts\stop.ps1
powershell -ExecutionPolicy Bypass -File scripts\stop.ps1 -Volumes
```

### Behavior

- `start` checks Docker and Docker Compose, creates `.env` from `.env.example` if missing,
  builds and starts every service, then waits for `backend` and `frontend` to respond.
- The model is **not downloaded automatically** on every start. The script only reports
  whether `qwen3:4b` is available; use `--pull-model`/`-PullModel` for an explicit pull.
- `stop` runs `docker compose --profile ai down --remove-orphans`, i.e. it stops and
  removes the containers and network (core + AI) but **preserves** the named volumes with
  PostgreSQL, Redis, MinIO, and Ollama data.
- `--volumes`/`-Volumes` is destructive and requires confirmation (or `--yes`/`-Yes`).
- To restart, use `--restart`/`-Restart` or run `stop` followed by `start`.

## Running with local AI (Ollama)

The AI module is **optional**. With `AI_ENABLED=false`, scraping, filters, statistics,
history, and deduplication all work normally.

1. Enable AI in `.env`:

   ```dotenv
   AI_ENABLED=true
   OLLAMA_MODEL=qwen3:4b
   AI_DEFAULT_TASK=best_deals
   AI_AUTO_ANALYZE=false
   AI_ANALYZE_IMAGES=false
   ```

   If the database already exists, these values are not overwritten automatically — use
   the **AI settings** page in the UI.

2. Start the AI profile:

   ```bash
   docker compose --profile ai up -d --build
   ```

3. Download the model **manually** (it is not pulled automatically on every start):

   ```bash
   docker compose exec ollama ollama pull qwen3:4b
   ```

4. Check the installed models:

   ```bash
   docker compose exec ollama ollama list
   ```

5. In the UI, open **AI settings** → **Check connection**. The expected state is
   `reachable` and `model available`. Then enable the AI module and save.

6. Start a manual analysis. Defaults:
   - model: `qwen3:4b`
   - task: `best_deals`
   - automatic analysis after scraping: **off**
   - include descriptions: **on**
   - image analysis: **off** (qwen3:4b is a text model)

AI tasks run in a separate `ai` queue and do not block scraping. A missing model,
unreachable Ollama, invalid JSON, or an interrupted task results in a
`failed`/`cancelled` status, with limited retries and exponential backoff.

## GPU and CPU mode

By default, Ollama runs on **CPU** and does not require an NVIDIA GPU. It is slow but
functional; no specific speed is promised.

For NVIDIA GPU:

1. Install the NVIDIA driver and NVIDIA Container Toolkit on the host.
2. Verify that Docker can see the GPU:
   ```bash
   docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
   ```
3. Start with the additional override:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile ai up -d --build
   ```

Limit parallel inference tasks with `AI_MAX_CONCURRENCY` (default 1). No specific VRAM
usage is promised; if memory is insufficient, use CPU mode or reduce `num_ctx` and the
number of candidates.

## Sources and permitted access

The full research is in [docs/SOURCES.md](docs/SOURCES.md) (Bulgarian). Summary:

| Source | Status | Reason |
|---|---|---|
| Cars.bg | `verified` | robots.txt allows access; the HTML structure was verified against real pages |
| Mobile.bg | `needs_permission` | Terms of use restrict commercial use of the data |
| Auto.bg | `needs_permission` | Terms of use restrict commercial use of the data |
| OLX.bg | `blocked` | robots.txt returns HTTP 403 from CloudFront |
| Bazar.bg | `needs_permission` | robots.txt disallows several paths; terms need review |
| CarMarket.bg | `needs_permission` | Terms of use prohibit copying for commercial purposes without consent |

Attempting to enable a source with `needs_permission` or `blocked` status through the API
or UI returns HTTP 409. This is a safeguard, not a bug. The platform does not bypass
CAPTCHA, login, anti-bot protections, or explicit restrictions.

## Scraping settings

Settings are per source and are edited from **Sources** (admin key required). The
**Check** button calls the connector's `health_check`; for gated sources it returns
`NEEDS_PERMISSION`/`BLOCKED` without making a request to the website.

- `max_concurrency` — parallel requests (default 1)
- `requests_per_second` — request rate (default 0.5)
- `timeout_seconds`, `retry_limit`, `backoff_seconds`
- `max_pages_per_run`, `max_listings_per_run`
- `download_images` — download to MinIO (default **false**)
- `archive_html` — HTML + screenshot via Playwright (default **false**; the global
  `ARCHIVE_ENABLED` is only a fallback when the key is missing from the configuration)

Additionally:

- `robots.txt` is checked before every run; if it cannot be checked, the run fails
  (fail closed).
- Requests go only to the source's allowed hosts.
- There are limits on response size, redirect count, and MIME type.
- The scheduler starts only enabled search jobs; the seeded job is disabled by default to
  avoid unexpected traffic. Enable and configure it from **Sources** → **Scheduled
  scraping jobs** (interval in minutes, 5–10080).
- A manual run can be started from **Scraping** with smaller limits.

## AI analysis

### Analysis types

- `best_deals` — best value compared with similar vehicles
- `price_anomalies` — suspiciously low/high prices
- `market_overview` — market overview by make, region, price, and mileage

### How it works

1. Filters active listings in PostgreSQL.
2. Groups similar vehicles and computes price and mileage medians through SQL/Python.
3. Computes a statistical score (price, mileage, data completeness, refresh recency).
4. Sends a limited candidate set and statistics to `qwen3:4b`.
5. Validates the JSON response with Pydantic.
6. Removes every unknown listing ID and URL; original URLs are taken from the database,
   not from the model.
7. Stores the result in `ai_analysis_runs` together with the model, prompt version, and
   filters.

Listing descriptions are treated as **untrusted content**. The system prompt explicitly
forbids instructions inside descriptions from changing the model's behavior.

### AI settings in the UI

- enable/disable AI
- choose an installed Ollama model
- check the connection
- default analysis type
- automatic analysis after a scrape run
- include descriptions
- image analysis (stored as disabled; requires a verified vision model)
- manual start, history, progress, errors, retry, and cancel

## REST API

All paths are prefixed with `/api`. Full documentation is available at `/docs`.

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | health check (DB, Redis, version) |
| GET | `/api/listings` | server-side pagination, sorting, and filters |
| GET | `/api/listings/filters` | available filter values |
| GET | `/api/listings/{id}` | details, images, source |
| GET | `/api/listings/{id}/price-history` | price history |
| GET | `/api/statistics/market` | market statistics |
| GET | `/api/sources` | sources and statuses |
| PUT | `/api/sources/{id}` | settings (admin) |
| POST | `/api/sources/{id}/health` | connector check (admin) |
| GET | `/api/search-jobs` | scheduled scraping jobs |
| PUT | `/api/search-jobs/{id}` | enable/interval (admin) |
| GET | `/api/scrape-runs` | scraping run history |
| POST | `/api/scrape-runs` | manual run (admin) |
| GET | `/api/scrape-runs/{id}` | details + errors |
| GET | `/api/scrape-runs/{id}/errors` | errors for a run |
| POST | `/api/scrape-runs/{id}/retry` | retry a run (admin) |
| GET | `/api/errors` | all scraper errors |
| GET | `/api/dedup/candidates` | duplicate candidates |
| POST | `/api/dedup/candidates/{id}/resolve` | resolve (admin) |
| GET | `/api/ai/settings` | AI settings |
| PUT | `/api/ai/settings` | update (admin) |
| GET | `/api/ai/models` | installed Ollama models |
| GET | `/api/ai/health` | connection and model availability |
| POST | `/api/ai/analyze` | manual analysis (admin) |
| GET | `/api/ai/results` | analysis history |
| GET | `/api/ai/jobs/{id}` | job status |
| GET | `/api/ai/results/{id}` | structured result |
| POST | `/api/ai/jobs/{id}/retry` | retry analysis (admin) |
| POST | `/api/ai/jobs/{id}/cancel` | cancel (admin) |

Admin endpoints require the `X-Admin-Key` header. Secrets are not returned in API
responses and are not logged.

## Database and deduplication

Main tables:

- `sources`, `search_jobs`
- `listings`, `listing_images`, `price_history`, `listing_snapshots`
- `scrape_runs`, `scraper_errors`
- `deduplication_candidates`
- `ai_analysis_runs`, `ai_settings`

Key behaviors:

- A unique index on `(source_id, source_listing_id)` enables idempotent upserts.
- A price change appends a row to `price_history`; old prices are never deleted.
- Hidden/removed listings are not deleted automatically; their status changes to
  `inactive` after `STALE_LISTING_DAYS` (default 14) via a scheduled task.
- Duplicate candidates are created for similar make/model/year, price, mileage, and
  location. Resolution does not delete history; it marks the listing as `duplicate` and
  keeps the link.
- The canonical listing on resolution is the one from a verified source.

Migrations live in [`backend/alembic/versions`](backend/alembic/versions). The backend
container runs `alembic upgrade head` at startup.

## Upgrades and migrations

1. Create a backup (see [Backup and restore](#backup-and-restore)).
2. Update the code and add any new keys from `.env.example` to `.env` if needed.
3. Rebuild and start:
   ```bash
   docker compose up -d --build
   ```
4. The backend container waits for PostgreSQL and runs `alembic upgrade head` before
   starting. Verify:
   ```bash
   docker compose logs backend
   curl http://localhost:8000/api/health
   ```
5. With the AI profile: `docker compose --profile ai up -d --build`.

Alembic downgrade is not recommended with production data; use backup/restore when you
need to roll back.

## Backup and restore

Example scripts:

Linux/macOS/Git Bash:

```bash
scripts/backup.sh
# creates ./backups/<UTC timestamp>/postgres.dump and minio-data
```

```bash
scripts/restore.sh ./backups/<UTC timestamp>
```

Windows PowerShell (Docker Desktop):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\backup.ps1
powershell -ExecutionPolicy Bypass -File scripts\restore.ps1 -Source .\backups\<UTC timestamp>
```

Restore stops the application services, restores PostgreSQL with `pg_restore --clean
--if-exists`, copies the MinIO data, and starts the services again. If you use AI, start
with `docker compose --profile ai up -d` after the restore.

Recommendations:

- Create a backup before every migration.
- Verify the backup on a separate instance.
- Keep `.env` and passwords out of Git.
- For production, put a TLS reverse proxy in front of the frontend container.

## Tests

Backend:

```bash
cd backend
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest -q
```

Frontend:

```bash
cd frontend
npm ci
npm run build
```

Docker configuration:

```bash
docker compose config --quiet
```

Live smoke test for the verified connector (only with permitted access and internet):

```bash
python scripts/verify_cars_bg.py
```

The tests cover:

- parsing local Cars.bg HTML fixtures
- normalization, price, mileage, fuel, power
- deduplication
- price history and idempotent upsert
- AI result validation and hallucination removal
- unreachable Ollama, missing model, invalid JSON
- API, admin guards, and `AI_ENABLED=false`
- Alembic migration on SQLite
- Compose services, profiles, health checks, and non-root users

## Verification results

Verified in this environment on 2026-10-19:

- `pytest -q` → **34 passed**
- `npm run build` → successful production build (TypeScript + Vite)
- `docker compose config --quiet` → successful validation
- `docker compose up -d --build` → core services are `healthy`:
  `backend`, `frontend`, `scraper-worker`, `scheduler`, `postgres`, `redis`, `minio`
- `docker compose --profile ai up -d` → `ollama` and `ai-worker` are `healthy`
- `docker compose exec ollama ollama pull qwen3:4b` → model downloaded (2.5 GB)
- `GET /api/ai/health` → `reachable=true`, `model_available=true`
- `python scripts/verify_cars_bg.py` → robots allow, search HTTP 200, 20 cards,
  offer HTTP 200, normalized 2009 / 2300 EUR / 265000 km / 6 images
- Manual Cars.bg scrape (1 page, max 2 listings) → **2 new listings, 0 errors,
  3 HTTP requests, 4.64 s**, real URLs and images
- Image download to MinIO → **10 downloaded images**, 40 older metadata rows with
  `skipped` status; the bucket contains 12 objects (images + HTML/screenshot archive)
- Playwright archive → successful snapshot with HTML and PNG in MinIO
- `docker compose exec scraper-worker python` + Playwright Chromium → successful launch
- Scheduler test → run with `triggered_by=scheduler`, 1 listing, 0 errors (the job was
  disabled again after the check)
- Concurrency test (`max_concurrency=2`, 2 listings) → 2 new listings, 0 errors
- Manual AI analysis `best_deals` with qwen3:4b on CPU → **completed in 109.8 s**,
  2 candidates, valid JSON, 0 validation warnings, original URLs taken from the database
- Recovery test → an interrupted AI run was marked `failed` when the worker restarted
- `scripts/backup.ps1` → successful `postgres.dump` + MinIO data copy
- After verification, the AI module was returned to `enabled=false` (manual mode by
  default)

> AI inference on CPU is slow (~11 tokens/sec observed in this environment). This is not
> a speed guarantee and no specific performance is promised.

## Troubleshooting

### Backend does not start / `database not ready`

- Check `docker compose ps` and the `postgres` health.
- Make sure `POSTGRES_PASSWORD` in `.env` matches the password in `DATABASE_URL`.
- Inspect the logs: `docker compose logs -f backend postgres`.

### `Object storage is not ready`

- Check the `minio` health and console at <http://localhost:9001>.
- `S3_ACCESS_KEY`/`S3_SECRET_KEY` must match `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD`.
- If the bucket is missing, the backend creates it at startup.

### AI: `model is missing`

```bash
docker compose exec ollama ollama list
docker compose exec ollama ollama pull qwen3:4b
```

The model is not downloaded automatically. If Ollama was started without the `ai` profile,
the AI worker is not running either.

### AI job stays in `pending`

- Check whether `ai-worker` is running: `docker compose --profile ai ps`.
- Check Redis and the worker health.
- Inspect `docker compose logs -f ai-worker`.

### `401` on admin actions

- Enter `ADMIN_API_KEY` in the UI's top bar.
- The key is kept only for the current session; after reloading the tab you may need to
  enter it again.

### Port conflicts

Change `BACKEND_PORT`, `FRONTEND_PORT`, `MINIO_PORT`, and `MINIO_CONSOLE_PORT` in `.env`.
Ollama is not published on the host; it is reachable only through the Docker network, to
avoid conflicts with other local Ollama instances.

## Known limitations

- Only Cars.bg is verified and enabled. The other sources require permission or are
  blocked.
- There is no bypassing of CAPTCHA, login, anti-bot protections, or paid APIs.
- qwen3:4b is a text model; image analysis is disabled.
- AI analysis quality depends on the local model and available data; the result is not a
  technical inspection and does not guarantee the vehicle's condition.
- Local AI on CPU can be slow; concurrency is limited.
- The scheduler does not start scraping automatically until you enable a search job.
- There is no built-in user management; administrative access uses an API key.
- There is no automatic download of the Ollama model.
- The platform is intended for personal/self-hosted analysis; respect each source's terms
  and applicable law.

## Security

- All secrets are environment variables; `.env` is in `.gitignore`.
- Admin endpoints require `X-Admin-Key`; comparison uses `secrets.compare_digest`.
- Backend, worker, and frontend containers run as non-root users.
- SSRF protection: only http/https, DNS resolution checks, private/loopback/link-local
  addresses are rejected, redirects are limited.
- Size limits for HTML, images, and archives; MIME type checks.
- Images and archives are disabled by default and must be enabled explicitly.
- Archived HTML is stored only in object storage and is not served or executed by the
  application.
- Logs are structured JSON and do not contain secrets, cookies, or tokens.
- Nginx adds security headers and proxies only `/api/`.

## Project structure

```text
backend/
  app/
    api/           REST endpoints and dependencies
    connectors/    interface, robots gate, Cars.bg and gated modules
    core/          config, logging, security
    db/            engine, session, Base
    models/        SQLAlchemy models
    schemas/       Pydantic schemas
    services/      scraping, dedup, images, storage, AI, statistics
    tasks/         Celery app, scrape/ai/scheduler tasks
    main.py        FastAPI app
    seed.py        initial sources and AI settings
  alembic/         migrations
  tests/           unit/integration/API/migration/compose tests
frontend/
  src/
    api/           fetch client and TypeScript types
    components/    Layout, Badge, PriceChart, Pagination, etc.
    pages/         Dashboard, Listings, Sources, Scraping, AI, Errors, Dedup
scripts/           start, stop, backup, restore, live verify
docs/              SOURCES.md
docker-compose.yml
docker-compose.gpu.yml
.env.example
README.md          English documentation (this file)
README_BG.md       Bulgarian documentation
```

## License

MIT. See [LICENSE](LICENSE).
