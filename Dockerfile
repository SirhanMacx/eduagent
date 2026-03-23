FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies for document processing (PyMuPDF, python-docx, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install the package with telegram support
COPY pyproject.toml README.md ./
COPY eduagent/ eduagent/
RUN pip install --no-cache-dir '.[telegram]'

# Teacher data volume
VOLUME /data
ENV EDUAGENT_DATA_DIR=/data

EXPOSE 8000

# Default: run the web dashboard
CMD ["eduagent", "serve", "--host", "0.0.0.0", "--port", "8000"]
