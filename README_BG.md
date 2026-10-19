# Bulgaria Auto CarMarket

Self-hosted платформа за събиране, структуриране, съхранение, обновяване и анализ на
автомобилни обяви от български сайтове. Проектът е контейнеризиран изцяло и работи без
външни платени API услуги.

> **Важно за достъпа до източниците:** единственият конектор, който е проверен и включен
> по подразбиране, е **Cars.bg**. Останалите източници са документирани като
> `NEEDS_PERMISSION` или `BLOCKED` и не се обхождат, докато достъпът не бъде потвърден.
> Вижте [docs/SOURCES.md](docs/SOURCES.md).

> English version: [README.md](README.md).

## Съдържание

- [Архитектура](#архитектура)
- [Технологичен стек](#технологичен-стек)
- [Бърз старт без AI](#бърз-старт-без-ai)
- [Управление на приложението (start / stop / restart)](#управление-на-приложението-start--stop--restart)
- [Мобилни приложения (Android и iOS)](#мобилни-приложения-android-и-ios)
- [Стартиране с локален AI (Ollama)](#стартиране-с-локален-ai-ollama)
- [GPU и CPU режим](#gpu-и-cpu-режим)
- [Източници и разрешен достъп](#източници-и-разрешен-достъп)
- [Scraping настройки](#scraping-настройки)
- [AI анализ](#ai-анализ)
- [REST API](#rest-api)
- [База данни и дедупликация](#база-данни-и-дедупликация)
- [Надграждане и миграции](#надграждане-и-миграции)
- [Backup и restore](#backup-и-restore)
- [Тестове](#тестове)
- [Проверки и резултати](#проверки-и-резултати)
- [Troubleshooting](#troubleshooting)
- [Известни ограничения](#известни-ограничения)
- [Сигурност](#сигурност)
- [Структура на проекта](#структура-на-проекта)
- [Лиценз](#лиценз)

## Архитектура

```mermaid
flowchart TD
    subgraph core["Основни услуги"]
        UI["frontend<br/>React + Vite<br/>nginx :8080 · /api proxy"]
        API["backend<br/>FastAPI :8000<br/>REST · auth · статистики"]
        DB[("PostgreSQL<br/>основна база")]
        REDIS[("Redis<br/>broker + result backend")]
        MINIO[("MinIO (S3)<br/>снимки + архиви")]
        SCRAPER["scraper-worker<br/>Celery опашка: scrape<br/>Playwright архиви"]
        SCHEDULER["scheduler<br/>Celery beat<br/>периодични задачи"]
    end

    subgraph ai["AI профил (опционален)"]
        AIWORKER["ai-worker<br/>Celery опашка: ai"]
        OLLAMA["ollama :11434<br/>qwen3:4b"]
    end

    MOBILE["Android / iOS приложения<br/>Capacitor WebView<br/>адрес на сървъра при старт"]

    UI -->|"HTTP /api"| API
    MOBILE -->|"REST /api"| API
    API --> DB
    API -->|"заявки/график"| REDIS
    API -->|"проверка на bucket"| MINIO
    SCHEDULER -->|"планирани run-ове"| REDIS
    REDIS -->|"scrape задачи"| SCRAPER
    REDIS -->|"AI задачи"| AIWORKER
    SCRAPER --> DB
    SCRAPER --> MINIO
    AIWORKER --> DB
    AIWORKER --> OLLAMA
```

Услуги в `docker-compose.yml`:

| Услуга | Роля | Профил |
|---|---|---|
| `frontend` | React dashboard, nginx reverse proxy | core |
| `backend` | FastAPI, миграции, seed, health | core |
| `scraper-worker` | Celery worker за `scrape` опашката, Playwright за архиви | core |
| `scheduler` | Celery beat за периодични задачи | core |
| `postgres` | PostgreSQL 16 | core |
| `redis` | Redis 7, broker и result backend | core |
| `minio` | S3-compatible object storage | core |
| `minio-init` | еднократна настройка на правата върху volume-а | core |
| `ai-worker` | Celery worker за `ai` опашката | `ai` |
| `ollama` | Локален LLM сървър | `ai` |

## Технологичен стек

- Python 3.12+, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic 2
- PostgreSQL 16, Redis 7, Celery 5
- httpx, BeautifulSoup, Playwright
- React 18, TypeScript, Vite, Tailwind CSS, React Router, lucide-react
- MinIO (S3-compatible object storage)
- Ollama с модел **qwen3:4b** (опционален)
- Docker Engine и Docker Compose
- pytest

Зависимостите са фиксирани в [`backend/requirements.txt`](backend/requirements.txt) и
[`frontend/package.json`](frontend/package.json).

> MinIO се стартира от pinned community image `alpine/minio`, защото official
> `minio/minio` image не е публично достъпен в Docker Hub към момента на проверката.
> Използваният release е фиксиран и работи като S3-compatible storage.

## Бърз старт без AI

Изисквания: Docker Engine 24+, Docker Compose v2, поне ~4 GB свободна RAM за core услугите.

> Най-бързо: `sh scripts/start.sh` стартира целия стек (core + AI профил) и изчаква
> health checks. Вижте [Управление на приложението](#управление-на-приложението-start--stop--restart).

1. Копирайте примерната конфигурация и сменете всички пароли:

   ```bash
   cp .env.example .env
   ```

   Генерирайте силен администраторски ключ, например:

   ```bash
   openssl rand -hex 32
   ```

   На Windows PowerShell:

   ```powershell
   -join ((48..57) + (97..102) | Get-Random -Count 64 | ForEach-Object {[char]$_})
   ```

   Сложете стойността в `ADMIN_API_KEY`. Сменете също `POSTGRES_PASSWORD`,
   `MINIO_ROOT_PASSWORD` и `S3_SECRET_KEY` (последните две трябва да съвпадат).

2. Стартирайте core услугите:

   ```bash
   docker compose up -d --build
   ```

   Тази команда **не** стартира Ollama и ai-worker, защото те са в профил `ai`.

3. Проверете health checks:

   ```bash
   docker compose ps
   curl http://localhost:8000/api/health
   ```

4. Отворете:

   - Dashboard: <http://localhost:8080>
   - API docs: <http://localhost:8000/docs>
   - MinIO console: <http://localhost:9001>

5. Въведете администраторския ключ в горната лента на dashboard-а. Ключът се пази
   само в `sessionStorage` и се изпраща като `X-Admin-Key`.

6. От страница **Scraping** стартирайте първия run за Cars.bg. По подразбиране са
   разрешени 1–2 страници и малък брой обяви, за да не се натоварва сайтът.

Backend контейнерът изчаква PostgreSQL, изпълнява `alembic upgrade head`, seed-ва
източниците и AI настройките и едва след това стартира. Workers и scheduler зависят от
health check-а на backend.

## Управление на приложението (start / stop / restart)

Скриптовете са в [`scripts/`](scripts/) и управляват **целия** стек — core услугите и
AI профила (`ollama`, `ai-worker`), плюс еднократния `minio-init`.

### Linux / macOS / Git Bash

```bash
sh scripts/start.sh              # build + стартира всичко и изчаква health checks
sh scripts/start.sh --no-build   # стартира без rebuild
sh scripts/start.sh --restart    # спира всичко и го стартира отново
sh scripts/start.sh --pull-model # изтегля OLLAMA_MODEL, ако липсва

sh scripts/stop.sh               # спира и премахва всички контейнери, пази данните
sh scripts/stop.sh --volumes     # ИЗТРИВА всички volumes (иска потвърждение)
```

Ако скриптовете не са изпълними:

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

### Поведение

- `start` проверява Docker и Docker Compose, създава `.env` от `.env.example`, ако липсва,
  изгражда и стартира всички услуги, после чака `backend` и `frontend` да отговорят.
- Моделът **не се изтегля автоматично** при всяко стартиране. Скриптът само отчита дали
  `qwen3:4b` е наличен; използвайте `--pull-model`/`-PullModel` за изрично изтегляне.
- `stop` изпълнява `docker compose --profile ai down --remove-orphans`, т.е. спира и
  премахва контейнерите и мрежата (core + AI), но **запазва** named volumes с PostgreSQL,
  Redis, MinIO и Ollama данни.
- `--volumes`/`-Volumes` е деструктивно и изисква потвърждение (или `--yes`/`-Yes`).
- За рестарт използвайте `--restart`/`-Restart` или последователно `stop` и `start`.

## Мобилни приложения (Android и iOS)

Native мобилните обвивки са генерирани с **Capacitor 8** и се намират в
[`android/`](android/) и [`ios/`](ios/). Те използват отново React dashboard-а и
комуникират със същия FastAPI backend през REST, без дублиран UI код.

### Адрес на сървъра по време на изпълнение

Адресът на self-hosted backend-а се задава при стартиране, а не се вгражда в приложението:

- При първо стартиране на native приложението диалогът **Сървър** се отваря автоматично.
- Въведете root или API URL, например `http://192.168.1.10:8000` или
  `https://carmarket.example.com/api`. Липсващият `/api` суфикс се добавя автоматично.
- В Android емулатора хост машината е достъпна на `http://10.0.2.2:8000`; на физическо
  устройство използвайте LAN IP адреса на хоста.
- Адресът се пази в `localStorage` и може да се промени по-късно от бутона **Сървър** в
  горната лента.
- Уеб build-ът продължава да използва относителния `/api`; задайте `VITE_API_BASE` при
  build, ако API-то е на друг origin.
- Backend CORS позволява `capacitor://localhost`, `http://localhost` и `https://localhost`
  — origin-ите на Capacitor WebView.

Използвайте HTTPS извън локална разработка. Генерираните native проекти разрешават
cleartext HTTP, защото платформата е предназначена за self-hosted сървъри в локална
мрежа; при публичен store build с HTTPS-only backend премахнете
`android:usesCleartextTraffic` и iOS ATS изключението.

### Предварителни изисквания

- Node.js 20+ и `npm`
- Android: JDK 21, Android Studio, Android SDK Platform 36, Build-Tools 36
- iOS: macOS с Xcode 16+ (iOS проектът не може да се build-ва на Windows)
- Достъпен работещ backend, например `docker compose up -d --build`

### Синхронизиране на web активите

От `frontend/`:

```bash
npm ci
npm run mobile:sync          # build на web + sync за двете платформи
npm run mobile:android       # build и sync само за Android
npm run mobile:ios           # build и sync само за iOS (препоръчително на macOS)
```

### Build и стартиране на Android

Отворете проекта в Android Studio:

```bash
cd frontend
npm run mobile:android:open
```

Или build-нете debug APK от командния ред:

```bash
cd android
# Windows
gradlew.bat assembleDebug
# Linux / macOS
./gradlew assembleDebug
```

APK-то се записва в `android/app/build/outputs/apk/debug/app-debug.apk`.

Debug APK-то в това repository е build-нато с JDK 21 и Android SDK 36 и е тествано на
Android 36 емулатор: първоначална настройка на сървъра, dashboard данни, обяви и
навигация с hardware back бутона работят. От емулатора използвайте
`http://10.0.2.2:8000`; на физическо устройство използвайте LAN IP адреса на хоста.

Изисквания за CLI build: `JAVA_HOME` сочи към JDK 21, `ANDROID_HOME` или
`ANDROID_SDK_ROOT` сочи към SDK с Platform 36 и Build-Tools 36, а
`android/local.properties` съдържа `sdk.dir=...`, ако SDK-то не се открива автоматично.
Capacitor копира web build-а в APK-то при `cap sync`.

За release build конфигурирайте signing в `android/app/build.gradle` (или Android Studio)
и изпълнете `gradlew.bat bundleRelease` / `./gradlew bundleRelease` за AAB.

### Build и стартиране на iOS

На macOS с Xcode:

```bash
cd frontend
npm run mobile:ios
npm run mobile:ios:open
```

В Xcode изберете target `App`, задайте development team за подписване, проверете bundle
identifier `bg.carmarket.app` и стартирайте на симулатор или устройство. Deployment
target е iOS 15.0. Увеличете `MARKETING_VERSION` / `CURRENT_PROJECT_VERSION` преди
App Store release.

iOS проектът, app metadata, `Info.plist` и SPM пакетът са генерирани и се синхронизират,
но компилирането и стартирането изискват macOS с Xcode; те не са изпълнени на Windows
машината, използвана за Android проверката.

### Native скриптове за стартиране и спиране

Помощните скриптове в [`scripts/`](scripts/) обхващат native build/run/stop процеса:

| Действие | macOS / Linux | Windows |
| --- | --- | --- |
| Стартиране на Android | `sh scripts/start-android.sh` | `powershell -File .\scripts\start-android.ps1` |
| Спиране на Android | `sh scripts/stop-android.sh` | `powershell -File .\scripts\stop-android.ps1` |
| Стартиране на iOS | `sh scripts/start-ios.sh` | само macOS |
| Спиране на iOS | `sh scripts/stop-ios.sh` | само macOS |

- `start-android` build-ва web активите и debug APK-то, стартира емулатор, ако няма
  свързано устройство, изчаква да зареди и после инсталира и стартира приложението.
  Скриптът **не** стартира Docker; за backend използвайте `scripts/start.sh`.
  Опции: `--avd NAME`, `--device SERIAL`, `--headless`, `--no-build`, `--no-install`,
  `--wait SECONDS`.
- `stop-android` спира приложението и изключва работещите емулатори. С
  `--keep-emulator` емулаторът остава включен.
- `start-ios` изисква macOS с Xcode 16+. Build-ва приложението, стартира симулатор и го
  инсталира и отваря. Опции: `--device NAME|UDID`, `--no-build`, `--no-install`.
- `stop-ios` спира приложението и изключва стартираните симулатори. С
  `--keep-simulator` те остават включени.

PowerShell скриптовете приемат същите опции с едно тире (`-Avd`, `-Device`,
`-Headless`, `-NoBuild`, `-NoInstall`, `-WaitSeconds`).

От Android емулатора използвайте `http://10.0.2.2:8000`; iOS симулаторът може да
използва `http://localhost:8000`.

### Native конфигурация

- Име: **Bulgaria Auto CarMarket**; app ID / bundle ID: `bg.carmarket.app`.
  Променете ги в [`frontend/capacitor.config.ts`](frontend/capacitor.config.ts) и
  обновете native проектите (или добавете платформите отново) при нужда от други
  идентификатори.
- Android: `android/app/src/main/AndroidManifest.xml` съдържа
  `android:usesCleartextTraffic="true"` за self-hosted HTTP сървъри.
- iOS: `ios/App/App/Info.plist` съдържа `NSAppTransportSecurity` изключение по същата
  причина.
- Генерираните web asset папки (`android/app/src/main/assets/public`,
  `ios/App/App/public`) са в `.gitignore` и се пресъздават от `npm run mobile:sync`.
- Android hardware back бутонът първо затваря диалога за сървър или навигационното
  меню, после минава назад през SPA историята и затваря приложението само от dashboard
  началото.
- Push notifications, deep links и store metadata все още не са включени.

## Стартиране с локален AI (Ollama)

AI модулът е **опционален**. При `AI_ENABLED=false` всички scraping, филтри, статистики,
история и дедупликация работят нормално.

1. Включете AI в `.env`:

   ```dotenv
   AI_ENABLED=true
   OLLAMA_MODEL=qwen3:4b
   AI_DEFAULT_TASK=best_deals
   AI_AUTO_ANALYZE=false
   AI_ANALYZE_IMAGES=false
   ```

   Ако базата вече е създадена, тези стойности не се презаписват автоматично — използвайте
   страница **AI настройки** в UI.

2. Стартирайте AI профила:

   ```bash
   docker compose --profile ai up -d --build
   ```

3. Изтеглете модела **ръчно** (не се изтегля автоматично при всяко стартиране):

   ```bash
   docker compose exec ollama ollama pull qwen3:4b
   ```

4. Проверете наличните модели:

   ```bash
   docker compose exec ollama ollama list
   ```

5. В UI отворете **AI настройки** → **Провери връзката**. Очакваното състояние е
   `достъпен` и `моделът е наличен`. След това включете AI модула и запазете.

6. Стартирайте ръчен анализ. По подразбиране:
   - модел: `qwen3:4b`
   - тип: `best_deals`
   - автоматичен анализ след scraping: **изключен**
   - включване на описания: **включено**
   - анализ на снимки: **изключен** (qwen3:4b е текстов модел)

AI задачите се изпълняват в отделна `ai` опашка и не блокират scraping-а. При липсващ
модел, недостъпен Ollama, невалиден JSON или прекъсната задача статусът се записва като
`failed`/`cancelled`, с ограничени retry опити и exponential backoff.

## GPU и CPU режим

По подразбиране Ollama работи на **CPU** и не изисква NVIDIA GPU. Това е бавно, но
функционално; не се обещава конкретна скорост.

За NVIDIA GPU:

1. Инсталирайте NVIDIA driver и NVIDIA Container Toolkit на хоста.
2. Проверете, че Docker вижда GPU:
   ```bash
   docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
   ```
3. Стартирайте с допълнителния override:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile ai up -d --build
   ```

Ограничете паралелните inference задачи чрез `AI_MAX_CONCURRENCY` (по подразбиране 1).
Не се обещава конкретна VRAM употреба; при недостатъчна памет използвайте CPU режим или
намалете `num_ctx`/броя кандидати.

## Източници и разрешен достъп

Пълното проучване е в [docs/SOURCES.md](docs/SOURCES.md). Накратко:

| Източник | Статус | Причина |
|---|---|---|
| Cars.bg | `verified` | robots.txt позволява; HTML структурата е проверена с реални страници |
| Mobile.bg | `needs_permission` | Общи условия ограничават търговското ползване на данните |
| Auto.bg | `needs_permission` | Общи условия ограничават търговското ползване на данните |
| OLX.bg | `blocked` | robots.txt връща HTTP 403 от CloudFront |
| Bazar.bg | `needs_permission` | robots.txt забранява редица пътища; условията изискват преглед |
| CarMarket.bg | `needs_permission` | Общи условия забраняват копиране за търговски цели без съгласие |

Опит за включване на източник със статус `needs_permission` или `blocked` през API/UI
връща HTTP 409. Това е защита, а не бъг. Платформата не заобикаля CAPTCHA, login,
anti-bot защити или изрични ограничения.

## Scraping настройки

Настройките са на ниво източник и се редактират от **Източници** (изисква admin ключ).
Бутонът **Провери** извиква `health_check` на конектора; за gated източници връща
`NEEDS_PERMISSION`/`BLOCKED` без да прави заявка към сайта.

- `max_concurrency` — паралелни заявки (по подразбиране 1)
- `requests_per_second` — темпо (по подразбиране 0.5)
- `timeout_seconds`, `retry_limit`, `backoff_seconds`
- `max_pages_per_run`, `max_listings_per_run`
- `download_images` — изтегляне в MinIO (по подразбиране **false**)
- `archive_html` — HTML + screenshot чрез Playwright (по подразбиране **false**;
  глобалният `ARCHIVE_ENABLED` е само fallback, ако ключът липсва в конфигурацията)

Допълнително:

- Преди всеки run се проверява `robots.txt`; при невъзможност за проверка run-ът се
  проваля (fail closed).
- Заявките са само към разрешените хостове на източника.
- Има лимити за размер, брой redirect-и и MIME тип.
- Scheduler-ът стартира само включени search jobs; по подразбиране seed-натият job е
  изключен, за да няма неочакван трафик. Включва се и се настройва от **Източници** →
  **Периодични scraping задачи** (интервал в минути, 5–10080).
- Ръчен run може да се стартира от **Scraping** с по-малки лимити.

## AI анализ

### Типове анализи

- `best_deals` — най-изгодни сделки спрямо сходни автомобили
- `price_anomalies` — подозрително ниски/високи цени
- `market_overview` — пазарен преглед по марки, региони, цени и пробег

### Как работи

1. Филтрира активните обяви в PostgreSQL.
2. Групира сходни автомобили и изчислява медиани за цена и пробег чрез SQL/Python.
3. Изчислява статистически score (цена, пробег, пълнота на данните, скорост на обновяване).
4. Подава ограничен набор от кандидати и статистики към `qwen3:4b`.
5. Валидира JSON отговора с Pydantic.
6. Премахва всички непознати listing ID-та и URL адреси; оригиналните URL-и се вземат
   от базата, не от модела.
7. Записва резултата в `ai_analysis_runs` заедно с модел, версия на промпта и филтри.

Описанията на обявите се третират като **недоверено съдържание**. Системният промпт
изрично забранява инструкции от описанията да променят поведението на модела.

### AI настройки в UI

- включване/изключване на AI
- избор на инсталиран Ollama модел
- проверка на връзката
- тип анализ по подразбиране
- автоматичен анализ след scrape run
- включване на описания
- анализ на снимки (записва се като изключен; изисква проверен vision модел)
- ръчно стартиране, история, прогрес, грешки, retry и cancel

## REST API

Всички пътища са с префикс `/api`. Пълната документация е на `/docs`.

| Метод | Път | Описание |
|---|---|---|
| GET | `/api/health` | health check (DB, Redis, версия) |
| GET | `/api/listings` | server-side pagination, сортиране и филтри |
| GET | `/api/listings/filters` | налични стойности за филтрите |
| GET | `/api/listings/{id}` | детайли, снимки, източник |
| GET | `/api/listings/{id}/price-history` | история на цената |
| GET | `/api/statistics/market` | пазарни статистики |
| GET | `/api/sources` | източници и статуси |
| PUT | `/api/sources/{id}` | настройки (admin) |
| POST | `/api/sources/{id}/health` | проверка на конектора (admin) |
| GET | `/api/search-jobs` | периодични scraping задачи |
| PUT | `/api/search-jobs/{id}` | включване/интервал (admin) |
| GET | `/api/scrape-runs` | история на scraping задачите |
| POST | `/api/scrape-runs` | ръчен run (admin) |
| GET | `/api/scrape-runs/{id}` | детайли + грешки |
| GET | `/api/scrape-runs/{id}/errors` | грешки за run |
| POST | `/api/scrape-runs/{id}/retry` | повторен run (admin) |
| GET | `/api/errors` | всички scraper грешки |
| GET | `/api/dedup/candidates` | кандидати за дубликати |
| POST | `/api/dedup/candidates/{id}/resolve` | resolve (admin) |
| GET | `/api/ai/settings` | AI настройки |
| PUT | `/api/ai/settings` | промяна (admin) |
| GET | `/api/ai/models` | инсталирани Ollama модели |
| GET | `/api/ai/health` | връзка и наличие на модела |
| POST | `/api/ai/analyze` | ръчен анализ (admin) |
| GET | `/api/ai/results` | история на анализите |
| GET | `/api/ai/jobs/{id}` | статус на задача |
| GET | `/api/ai/results/{id}` | структуриран резултат |
| POST | `/api/ai/jobs/{id}/retry` | повторен анализ (admin) |
| POST | `/api/ai/jobs/{id}/cancel` | отказ (admin) |

Административните endpoints изискват header `X-Admin-Key`. Секрети не се връщат в API
отговори и не се логват.

## База данни и дедупликация

Основни таблици:

- `sources`, `search_jobs`
- `listings`, `listing_images`, `price_history`, `listing_snapshots`
- `scrape_runs`, `scraper_errors`
- `deduplication_candidates`
- `ai_analysis_runs`, `ai_settings`

Ключови поведения:

- Уникален индекс по `(source_id, source_listing_id)` за идемпотентен upsert.
- При промяна на цената се добавя ред в `price_history`; старите цени не се трият.
- Скритите/премахнатите обяви не се трият автоматично; статусът се сменя на `inactive`
  след `STALE_LISTING_DAYS` (по подразбиране 14) от scheduled задача.
- Кандидатите за дубликати се създават при сходни марка/модел/година, цена, пробег и
  локация. Resolution не трие история; маркира обявата като `duplicate` и пази връзка.
- Канонична при resolve е обявата от проверен източник.

Миграциите са в [`backend/alembic/versions`](backend/alembic/versions). Backend контейнерът
изпълнява `alembic upgrade head` при стартиране.

### Надграждане и миграции

1. Направете backup (вижте [Backup и restore](#backup-и-restore)).
2. Обновете кода и при нужда добавете новите ключове от `.env.example` в `.env`.
3. Изградете и стартирайте отново:
   ```bash
   docker compose up -d --build
   ```
4. Backend контейнерът изчаква PostgreSQL и изпълнява `alembic upgrade head` преди
   стартиране. Проверете:
   ```bash
   docker compose logs backend
   curl http://localhost:8000/api/health
   ```
5. При AI профил: `docker compose --profile ai up -d --build`.

Alembic downgrade не се препоръчва при production данни; използвайте backup/restore
при нужда от връщане назад.

## Backup и restore

Примерни скриптове:

Linux/macOS/Git Bash:

```bash
scripts/backup.sh
# създава ./backups/<UTC timestamp>/postgres.dump и minio-data
```

```bash
scripts/restore.sh ./backups/<UTC timestamp>
```

Windows PowerShell (Docker Desktop):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\backup.ps1
powershell -ExecutionPolicy Bypass -File scripts\restore.ps1 -Source .\backups\<UTC timestamp>
```

Restore-ът спира application услугите, възстановява PostgreSQL с `pg_restore --clean
--if-exists`, копира MinIO данните и стартира услугите отново. Ако използвате AI,
стартирайте след restore с `docker compose --profile ai up -d`.

Препоръки:

- Правете backup преди всяка миграция.
- Проверявайте backup-а на отделна инстанция.
- Пазете `.env` и паролите извън Git.
- За production използвайте TLS reverse proxy пред frontend контейнера.

## Тестове

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

Docker конфигурация:

```bash
docker compose config --quiet
```

Live smoke test за проверения конектор (само при разрешен достъп и с интернет):

```bash
python scripts/verify_cars_bg.py
```

Тестовете покриват:

- парсване на локални Cars.bg HTML fixtures
- нормализиране, цена, пробег, гориво, мощност
- дедупликация
- история на цените и идемпотентен upsert
- валидация на AI резултати и премахване на халюцинации
- Ollama недостъпен/липсващ модел/невалиден JSON
- API, admin guard-ове и AI_ENABLED=false
- Alembic миграция върху SQLite
- Compose услуги, профили, health checks и non-root потребители

## Проверки и резултати

Проверено в тази среда на 2026-10-19:

- `pytest -q` → **34 passed**
- `npm run build` → успешен production build (TypeScript + Vite)
- `docker compose config --quiet` → успешна валидация
- `docker compose up -d --build` → core услугите са `healthy`:
  `backend`, `frontend`, `scraper-worker`, `scheduler`, `postgres`, `redis`, `minio`
- `docker compose --profile ai up -d` → `ollama` и `ai-worker` са `healthy`
- `docker compose exec ollama ollama pull qwen3:4b` → моделът е изтеглен (2.5 GB)
- `GET /api/ai/health` → `reachable=true`, `model_available=true`
- `python scripts/verify_cars_bg.py` → robots allow, search HTTP 200, 20 карти,
  оферта HTTP 200, нормализирани 2009 / 2300 EUR / 265000 км / 6 снимки
- Ръчен Cars.bg scrape (1 страница, максимум 2 обяви) → **2 нови обяви, 0 грешки,
  3 HTTP заявки, 4.64 s**, реални URL адреси и снимки
- Изтегляне на снимки в MinIO → **10 downloaded изображения**, 40 стари metadata записа
  със статус `skipped`; в bucket-а има 12 обекта (снимки + HTML/screenshot архив)
- Playwright archive → успешен snapshot с HTML и PNG в MinIO
- `docker compose exec scraper-worker python` + Playwright Chromium → успешен launch
- Scheduler тест → run с `triggered_by=scheduler`, 1 обява, 0 грешки (job-ът е изключен
  отново след проверката)
- Concurrency тест (`max_concurrency=2`, 2 обяви) → 2 нови обяви, 0 грешки
- Ръчен AI анализ `best_deals` с qwen3:4b на CPU → **completed за 109.8 s**, 2 кандидата,
  валиден JSON, 0 validation warnings, оригиналните URL адреси са взети от базата
- Recovery тест → прекъснат AI run е маркиран като `failed` при рестарт на worker-а
- `scripts/backup.ps1` → успешен `postgres.dump` + копие на MinIO data
- След проверката AI модулът е върнат на `enabled=false` (ръчен режим по подразбиране)

> AI inference на CPU е бавен (наблюдавани ~11 токена/сек в тази среда). Това не е
> гаранция за скорост и не се обещава конкретна производителност.

## Troubleshooting

### Backend не стартира / `database not ready`

- Проверете `docker compose ps` и health-а на `postgres`.
- Уверете се, че `POSTGRES_PASSWORD` в `.env` съвпада с паролата в `DATABASE_URL`.
- Вижте логовете: `docker compose logs -f backend postgres`.

### `Object storage is not ready`

- Проверете `minio` health и console на <http://localhost:9001>.
- `S3_ACCESS_KEY`/`S3_SECRET_KEY` трябва да съвпадат с `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD`.
- Ако bucket липсва, backend го създава при стартиране.

### AI: `моделът липсва`

```bash
docker compose exec ollama ollama list
docker compose exec ollama ollama pull qwen3:4b
```

Моделът не се изтегля автоматично. Ако Ollama е стартиран без профил `ai`, AI worker-ът
също не работи.

### AI задача стои в `pending`

- Проверете дали `ai-worker` е стартиран: `docker compose --profile ai ps`.
- Проверете Redis и health-а на worker-а.
- Вижте `docker compose logs -f ai-worker`.

### `401` при admin действия

- Въведете `ADMIN_API_KEY` в горната лента на UI.
- Ключът се пази само в текущата сесия; след презареждане на tab-а може да трябва да се въведе отново.

### Port conflicts

Променете `BACKEND_PORT`, `FRONTEND_PORT`, `MINIO_PORT`, `MINIO_CONSOLE_PORT` в `.env`.
Ollama не е публикуван на хоста; достъпът е само през Docker мрежата, за да няма конфликти
с други локални Ollama инстанции.

## Известни ограничения

- Само Cars.bg е проверен и включен. Другите източници изискват разрешение или са блокирани.
- Няма заобикаляне на CAPTCHA, login, anti-bot защити или платени API-та.
- qwen3:4b е текстов модел; анализът на снимки е изключен.
- Качеството на AI анализа зависи от локалния модел и наличните данни; резултатът не е
  техническа експертиза и не гарантира състоянието на автомобила.
- Локалният AI на CPU може да бъде бавен; паралелността е ограничена.
- Scheduler-ът не стартира автоматично scraping, докато не включите search job.
- Няма вградено управление на потребители; административният достъп е с API ключ.
- Няма автоматично изтегляне на Ollama модела.
- Платформата е предназначена за личен/self-hosted анализ; спазвайте условията на всеки
  източник и приложимото законодателство.

## Сигурност

- Всички тайни са в environment variables; `.env` е в `.gitignore`.
- Admin endpoints изискват `X-Admin-Key`; сравнението е с `secrets.compare_digest`.
- Backend, worker и frontend контейнерите работят с non-root потребители.
- SSRF защита: само http/https, проверка на DNS резолюция, забрана на private/loopback/
  link-local адреси, ограничени redirect-и.
- Ограничения за размер на HTML, снимки и архиви; проверка на MIME тип.
- Снимките и архивите се изключени по подразбиране и се включват изрично.
- Архивираният HTML се съхранява само в object storage и не се сервира/изпълнява от
  приложението.
- Логовете са structured JSON и не съдържат тайни, cookies или токени.
- Nginx добавя security headers и проксира само `/api/`.

## Структура на проекта

```text
backend/
  app/
    api/           REST endpoints и dependencies
    connectors/    интерфейс, robots gate, Cars.bg и gated модули
    core/          config, logging, security
    db/            engine, session, Base
    models/        SQLAlchemy модели
    schemas/       Pydantic схеми
    services/      scraping, dedup, images, storage, AI, statistics
    tasks/         Celery app, scrape/ai/scheduler tasks
    main.py        FastAPI app
    seed.py        начални източници и AI настройки
  alembic/         миграции
  tests/           unit/integration/API/migration/compose тестове
frontend/
  src/
    api/           fetch client и TypeScript типове
    components/    Layout, Badge, PriceChart, Pagination и др.
    pages/         Dashboard, Listings, Sources, Scraping, AI, Errors, Dedup
scripts/           start, stop, Android/iOS lifecycle, backup, restore, live verify
docs/              SOURCES.md
android/           Capacitor Android проект (Gradle, Android Studio)
ios/               Capacitor iOS проект (Xcode, Swift Package Manager)
frontend/capacitor.config.ts
docker-compose.yml
docker-compose.gpu.yml
.env.example
README.md          документация на английски
README_BG.md       документация на български (този файл)
```

## Лиценз

MIT. Вижте [LICENSE](LICENSE).
