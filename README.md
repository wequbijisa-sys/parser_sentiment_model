# Streaming Text Ingestion System

A production-style Python repository for collecting legal public text data, storing raw records in MinIO, and sending each collected text to a configurable model inference API under strict rate limits.

This project **does not train models**, **does not build training features**, and **does not implement scraping evasion**. It focuses only on collection, raw storage, replay, rate limiting, request sending, logging, and lightweight metrics hooks.


## Документация на русском

Подробная инструкция по установке, настройке `.env`, запуску через Poetry/pip, локальному MinIO, batch/live/replay режимам и решению ошибки `Poetry could not find a pyproject.toml file` находится в [`docs/RU_RUNBOOK.md`](docs/RU_RUNBOOK.md).

## Architecture overview

```text
Public APIs / feeds
   │
   ▼
SourceCollector plugins ──► TextItem schema ──► MinIO raw storage
   │                              │
   │                              ▼
   └────────────────────► Rate limiter ──► ModelAPIClient ──► model endpoint
                                  ▲
                                  │
                         Replay from MinIO
```

### Repository tree

```text
.
├── src/text_ingestion/
│   ├── api/model_client.py        # Generic model inference HTTP client
│   ├── cli.py                     # CLI entrypoints for batch, live, replay
│   ├── collectors/                # Source adapter plugin contracts and adapters
│   ├── config.py                  # Environment-based settings
│   ├── flows/                     # Batch, live polling, and replay orchestration
│   ├── logging.py                 # Structured JSON logging setup
│   ├── metrics.py                 # Replaceable in-process metrics hook
│   ├── models.py                  # Canonical TextItem and request/response schemas
│   ├── rate_limit/limiter.py      # Async token bucket rate limiting
│   ├── storage/minio_store.py     # MinIO/S3 raw storage abstraction
│   └── utils/                     # Hashing and time helpers
├── tests/                         # Unit tests
├── scripts/bootstrap_minio.py     # Bucket creation helper
├── .env.example                   # All configurable settings
├── Dockerfile
├── docker-compose.yml             # Optional placeholder model endpoint
└── pyproject.toml
```

## Key design decisions

- **Clean source plugin interface:** every source implements `SourceCollector.collect()` and yields canonical `TextItem` objects.
- **Legal/public access only:** Reddit uses the official API via PRAW, RSS uses public feed URLs, and reviews are represented by a configurable public API adapter.
- **Raw-first storage:** each raw item is stored as JSON in MinIO partitioned by source and collection date.
- **Replayable by design:** replay reads stored JSON/JSONL records from MinIO and sends them back through the same model API client and rate limiters.
- **Strict rate limiting:** a concurrency-safe async token bucket supports global requests per minute, optional per-source RPM, and optional burst size.
- **Environment-driven config:** all endpoints, credentials, tokens, limits, and source options are configured via environment variables.
- **Observability-ready logs:** logs are structured JSON with source IDs and request correlation IDs, suitable for Loki/Grafana pipelines.

## Setup

### Local Python

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
# Optional Reddit support:
pip install -e '.[reddit,dev]'
cp .env.example .env
```

### Existing MinIO and optional placeholder endpoint

This repository no longer starts its own MinIO container. Point the app at your existing MinIO/S3-compatible service with environment variables, then bootstrap the bucket if needed:

```bash
python scripts/bootstrap_minio.py
```

For a local placeholder model endpoint only, you can run:

```bash
docker compose up -d http-echo
```

## Configuration

Copy `.env.example` to `.env` and edit values:

```env
MINIO_ENDPOINT=http://localhost:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
MINIO_BUCKET=raw-text-items

MODEL_API_URL=http://localhost:8080/predict
MODEL_API_AUTH_TOKEN=
GLOBAL_REQUESTS_PER_MINUTE=60
PER_SOURCE_REQUESTS_PER_MINUTE=reddit:30,rss:120,reviews:20
BURST_SIZE=10

RSS_FEED_URLS=https://hnrss.org/frontpage
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REVIEWS_API_URL=
```

## Usage

### Batch ingestion

Run one collection pass, store raw items, and send each item to your model endpoint:

```bash
text-ingest batch --source rss --max-items 25
```

Multiple sources can be enabled:

```bash
text-ingest batch --source rss --source reddit --source reviews --max-items 50
```

### Live polling

Continuously poll selected sources:

```bash
text-ingest live --source rss --max-items-per-poll 25
```

`POLLING_INTERVAL_SECONDS` controls sleep time between poll cycles.

### Replay from MinIO

Replay all stored items:

```bash
text-ingest replay
```

Replay one partition prefix:

```bash
text-ingest replay --prefix 'source=rss/year=2026/' --max-items 100
```

## Adding a source

1. Create a new file under `src/text_ingestion/collectors/`.
2. Subclass `SourceCollector`.
3. Implement `collect()` to yield `TextItem` objects.
4. Register it in `src/text_ingestion/cli.py` or your own application factory.

The adapter should use official APIs, public feeds, or explicitly permitted endpoints only.

## Model endpoint contract

The generic client sends JSON like:

```json
{
  "text": "example text",
  "correlation_id": "uuid",
  "source_name": "rss",
  "source_item_id": "source-native-id",
  "metadata": {"content_hash": "sha256"}
}
```

It sends `X-Correlation-ID` on every request. If `MODEL_API_AUTH_TOKEN` is configured, it sends `Authorization: Bearer <token>` by default. Change `MODEL_API_AUTH_HEADER` if your endpoint expects a different header.

## Storage layout

Raw objects are written to MinIO as JSON:

```text
source=<source_name>/year=<YYYY>/month=<MM>/day=<DD>/<content_hash>.json
```

This supports partitioned retrieval and replay by prefix.

## Testing

```bash
pytest
ruff check .
```

The tests cover schema validation, rate limiting behavior, storage round trips, model API client behavior, and a mock source adapter.

## Compliance notes

- Do not add stealth scraping, CAPTCHA bypass, anti-bot bypass, credential sharing, or Terms-of-Service evasion logic.
- Validate that each configured source is permitted for your intended use.
- Some APIs require authentication, application approval, rate limits, or attribution. Configure credentials via environment variables only.
