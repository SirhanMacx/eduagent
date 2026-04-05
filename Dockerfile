FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY clawed/ clawed/
COPY eduagent/ eduagent/

# Base deps only — optional extras (browser, voice, etc.) add too much
# to a slim container. Install them manually if needed.
RUN pip install --no-cache-dir -e .

VOLUME /data
ENV EDUAGENT_DATA_DIR=/data

EXPOSE 8000

# Default: localhost only. Override with --host 0.0.0.0 behind a reverse proxy.
CMD ["clawed", "serve", "--host", "127.0.0.1", "--port", "8000"]
