# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HEALTH_EXPENDITURE_DB=/app/data/prototype.db \
    SOURCE_DATA_DIR=/app/candidate_data

WORKDIR /app

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app

COPY requirements.txt ./
RUN pip install --no-cache-dir --requirement requirements.txt

COPY schema.sql ./
COPY config/ ./config/
COPY candidate_data/ ./candidate_data/
COPY src/ ./src/
COPY docker/entrypoint.sh /usr/local/bin/health-expenditure-entrypoint

RUN mkdir -p /app/data \
    && chown -R app:app /app /usr/local/bin/health-expenditure-entrypoint \
    && chmod 0555 /usr/local/bin/health-expenditure-entrypoint

USER app

EXPOSE 8000

HEALTHCHECK --interval=20s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).read()"]

ENTRYPOINT ["health-expenditure-entrypoint"]
