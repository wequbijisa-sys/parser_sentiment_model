# Подробная инструкция по запуску Streaming Text Ingestion

Эта инструкция описывает запуск приложения локально: установка зависимостей, настройка `.env`, запуск MinIO, запуск batch/live/replay потоков и решение частой ошибки Poetry:

```text
Poetry could not find a pyproject.toml file in ... or its parents
```

## 1. Что делает приложение

Приложение собирает публичные тексты из разрешённых API/источников, сохраняет сырые записи в MinIO и отправляет каждый текст в ваш endpoint модели как inference-запрос.

Поддерживаемые режимы:

- **batch** — один проход по выбранным источникам;
- **live** — постоянный polling источников с заданным интервалом;
- **replay** — повторная отправка ранее сохранённых записей из MinIO.

Поддерживаемые источники из коробки:

- RSS/news feeds;
- Reddit через официальный API и PRAW;
- универсальный адаптер для публичного Reviews API.

## 2. Важное про ошибку Poetry `pyproject.toml not found`

Ошибка:

```text
Poetry could not find a pyproject.toml file in /path/to/streaming-ingestion or its parents
```

означает, что вы запускаете `poetry install` **не из корня репозитория** или в папку были скопированы не все файлы проекта.

В корне проекта обязательно должен быть файл:

```text
pyproject.toml
```

Проверьте это так:

```bash
pwd
find . -maxdepth 1 -name pyproject.toml -print
```

Если команда `find` ничего не выводит, вы находитесь не в корне проекта. Перейдите в папку, где лежит `pyproject.toml`:

```bash
cd /путь/к/streaming-ingestion
```

Если вы создаёте отдельный новый репозиторий, перенесите туда **все** файлы и папки из этого проекта, включая:

```text
pyproject.toml
src/
tests/
.env.example
README.md
Dockerfile
docker-compose.yml
scripts/
docs/
```

После этого снова выполните:

```bash
poetry install --with dev
```

## 3. Требования

Нужно установить:

- Python 3.11 или новее;
- Docker и Docker Compose — для локального MinIO;
- Poetry 2.x или обычный `pip`/`venv`;
- доступ к вашему model API endpoint.

Проверка версий:

```bash
python --version
poetry --version
docker --version
docker compose version
```

## 4. Установка через Poetry

Перейдите в корень проекта:

```bash
cd /путь/к/streaming-ingestion
```

Проверьте наличие `pyproject.toml`:

```bash
test -f pyproject.toml && echo "OK: pyproject.toml найден"
```

Рекомендуем хранить виртуальное окружение внутри проекта:

```bash
poetry config virtualenvs.in-project true
```

Установите зависимости для запуска и разработки:

```bash
poetry install --with dev
```

Если нужен Reddit-источник, установите дополнительную группу зависимостей:

```bash
poetry install --with dev --extras reddit
```

Проверка CLI:

```bash
poetry run text-ingest --help
```

## 5. Альтернативная установка через venv + pip

Если вы не используете Poetry:

```bash
cd /путь/к/streaming-ingestion
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Для Reddit:

```bash
pip install -e '.[reddit,dev]'
```

Проверка CLI:

```bash
text-ingest --help
```

## 6. Настройка переменных окружения

Скопируйте пример файла окружения:

```bash
cp .env.example .env
```

Минимальная локальная конфигурация:

```env
LOG_LEVEL=INFO

MINIO_ENDPOINT=http://localhost:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
MINIO_BUCKET=raw-text-items
MINIO_REGION=us-east-1
MINIO_SECURE=false

MODEL_API_URL=http://localhost:8080/predict
MODEL_API_AUTH_TOKEN=
MODEL_API_AUTH_HEADER=Authorization
MODEL_API_TIMEOUT_SECONDS=10
MODEL_API_MAX_RETRIES=3

GLOBAL_REQUESTS_PER_MINUTE=60
PER_SOURCE_REQUESTS_PER_MINUTE=
BURST_SIZE=

POLLING_INTERVAL_SECONDS=60
BATCH_MAX_ITEMS=100

RSS_FEED_URLS=https://hnrss.org/frontpage
```

Для реального endpoint модели замените:

```env
MODEL_API_URL=https://ваш-домен.example.com/predict
MODEL_API_AUTH_TOKEN=ваш_токен_если_нужен
```

Если endpoint ожидает другой заголовок авторизации, измените:

```env
MODEL_API_AUTH_HEADER=X-API-Key
```

> Секреты не нужно коммитить. Файл `.env` добавлен в `.gitignore`.

## 7. Подключение к существующему MinIO

Отдельный MinIO-контейнер из этого репозитория запускать не нужно. Используйте ваш уже существующий сервис, например:

```yaml
minio:
  image: minio/minio:${S3_VERSION}
  container_name: dev_minio
  ports:
    - "9001:9001"
    - "9000:9000"
  environment:
    MINIO_ROOT_USER: ${AWS_ACCESS_KEY_ID}
    MINIO_ROOT_PASSWORD: ${AWS_SECRET_ACCESS_KEY}
  command: server /data --console-address ":9001"
```

Для такой конфигурации в `.env` приложения достаточно указать:

```env
MINIO_ENDPOINT=http://localhost:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
MINIO_BUCKET=raw-text-items
MINIO_REGION=us-east-1
MINIO_SECURE=false
```

Также поддерживаются старые имена переменных `MINIO_ENDPOINT_URL`, `MINIO_ACCESS_KEY` и `MINIO_SECRET_KEY`, если вам удобнее использовать их.

Если bucket ещё не создан, создайте его из настроек `.env`:

Poetry:

```bash
poetry run python scripts/bootstrap_minio.py
```

pip/venv:

```bash
python scripts/bootstrap_minio.py
```

## 8. Быстрый smoke test с RSS

Убедитесь, что в `.env` задан RSS feed:

```env
RSS_FEED_URLS=https://hnrss.org/frontpage
```

Запустите один batch-проход на 5 элементов:

Poetry:

```bash
poetry run text-ingest batch --source rss --max-items 5
```

pip/venv:

```bash
text-ingest batch --source rss --max-items 5
```

Что должно произойти:

1. приложение прочитает RSS feed;
2. преобразует entries в `TextItem`;
3. сохранит JSON-записи в MinIO;
4. отправит тексты в `MODEL_API_URL`;
5. выведет структурированные JSON-логи.

## 9. Запуск batch ingestion

Один источник:

```bash
poetry run text-ingest batch --source rss --max-items 25
```

Несколько источников:

```bash
poetry run text-ingest batch --source rss --source reddit --source reviews --max-items 50
```

Для Reddit необходимо заполнить `.env`:

```env
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=streaming-text-ingestion/0.1 by your-company
REDDIT_SUBREDDITS=MachineLearning,python
REDDIT_LIMIT=25
```

Для reviews-адаптера необходимо указать API:

```env
REVIEWS_API_URL=https://example.com/public/reviews
REVIEWS_API_TOKEN=если_нужен
```

Ожидаемый формат reviews API:

- JSON object с полем `items`, где `items` — список reviews;
- или сразу JSON list.

Адаптер ищет текст в полях `text`, `body`, `review` или `content`.

## 10. Запуск live polling

Live-режим постоянно опрашивает источники и делает паузу `POLLING_INTERVAL_SECONDS` между циклами:

```bash
poetry run text-ingest live --source rss --max-items-per-poll 25
```

Остановить процесс можно через:

```bash
Ctrl+C
```

Для production лучше запускать этот процесс под supervisor/systemd/Kubernetes Job/Deployment, чтобы была автоматическая перезагрузка при сбоях.

## 11. Replay из MinIO

Replay отправляет уже сохранённые записи в model API повторно.

Replay всех записей:

```bash
poetry run text-ingest replay
```

Replay только RSS partition:

```bash
poetry run text-ingest replay --prefix 'source=rss/' --max-items 100
```

Replay за год:

```bash
poetry run text-ingest replay --prefix 'source=rss/year=2026/' --max-items 100
```

Формат ключей в MinIO:

```text
source=<source_name>/year=<YYYY>/month=<MM>/day=<DD>/<content_hash>.json
```

## 12. Настройка rate limiting

Глобальный лимит запросов в model API задаётся так:

```env
GLOBAL_REQUESTS_PER_MINUTE=60
```

Это означает максимум 60 запросов в минуту суммарно по всем источникам.

Опциональные лимиты по источникам:

```env
PER_SOURCE_REQUESTS_PER_MINUTE=reddit:30,rss:120,reviews:20
```

Опциональный burst:

```env
BURST_SIZE=10
```

Если `BURST_SIZE` не задан, ёмкость token bucket равна RPM соответствующего limiter.

## 13. Логи и correlation IDs

Приложение пишет структурированные JSON-логи. Для каждого запроса в model API создаётся correlation ID и отправляется HTTP-заголовок:

```text
X-Correlation-ID: <uuid>
```

Это удобно для трассировки пути записи:

```text
source -> MinIO object -> model request -> model response
```

Уровень логов задаётся в `.env`:

```env
LOG_LEVEL=INFO
```

## 14. Запуск тестов и проверок

Poetry:

```bash
poetry run pytest
poetry run ruff check .
poetry run black --check .
```

pip/venv:

```bash
pytest
ruff check .
black --check .
```

Если тесты падают с `ModuleNotFoundError`, зависимости не установлены в активное окружение. Проверьте:

```bash
which python
python -m pip list
poetry env info
```

## 15. Docker-образ приложения

Собрать образ:

```bash
docker build -t streaming-text-ingestion:local .
```

Показать help:

```bash
docker run --rm streaming-text-ingestion:local --help
```

Запуск batch из контейнера требует передать `.env` и доступ к MinIO/model API:

```bash
docker run --rm --env-file .env --network host streaming-text-ingestion:local batch --source rss --max-items 5
```

На macOS/Windows вместо `--network host` обычно нужно использовать адреса сервисов, доступные из Docker, например `host.docker.internal`.

## 16. Частые проблемы

### Poetry не видит `pyproject.toml`

Причина: команда запущена не из корня проекта или проект скопирован не полностью.

Решение:

```bash
pwd
find . -maxdepth 1 -name pyproject.toml -print
cd /путь/к/папке/где/лежит/pyproject.toml
poetry install --with dev
```

### MinIO недоступен

Проверьте ваш существующий контейнер/сервис MinIO в том compose-проекте, где он объявлен:

```bash
docker ps --filter name=dev_minio
docker logs dev_minio
```

Проверьте `.env` приложения:

```env
MINIO_ENDPOINT=http://localhost:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
```

### Model API возвращает ошибку

Проверьте:

- правильность `MODEL_API_URL`;
- нужен ли auth token;
- какой заголовок авторизации ожидает endpoint;
- соответствует ли payload contract вашему API.

Текущий generic payload:

```json
{
  "text": "example text",
  "correlation_id": "uuid",
  "source_name": "rss",
  "source_item_id": "source-id",
  "metadata": {"content_hash": "sha256"}
}
```

### Reddit не запускается

Проверьте, что установлен extra и заданы credentials:

```bash
poetry install --with dev --extras reddit
```

```env
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=...
```

## 17. Рекомендуемый порядок первого запуска

```bash
cd /путь/к/streaming-ingestion
find . -maxdepth 1 -name pyproject.toml -print
poetry config virtualenvs.in-project true
poetry install --with dev
cp .env.example .env
docker compose up -d http-echo  # опционально: только mock model endpoint
poetry run python scripts/bootstrap_minio.py
poetry run text-ingest batch --source rss --max-items 5
poetry run text-ingest replay --prefix 'source=rss/' --max-items 5
```

Если все команды выполнились без ошибок, локальный контур работает.
