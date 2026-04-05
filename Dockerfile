FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy source
COPY pyproject.toml README.md ./
COPY clawed/ clawed/
COPY eduagent/ eduagent/

# Create empty CLI bundle dir (hatchling requires it)
RUN mkdir -p clawed/_cli_bundle && \
    echo '{"type":"module"}' > clawed/_cli_bundle/package.json

# Non-editable install, base deps only
RUN pip install --no-cache-dir .

VOLUME /data
ENV EDUAGENT_DATA_DIR=/data

EXPOSE 8000

# Default: localhost only. Override with --host 0.0.0.0 behind a reverse proxy.
CMD ["clawed", "serve", "--host", "127.0.0.1", "--port", "8000"]
