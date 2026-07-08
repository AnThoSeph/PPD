# PPD REST API — Python + Typst + Tesseract
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PPD_ALLOW_OPEN=1 \
    TYPST_VERSION=0.14.2

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "https://github.com/typst/typst/releases/download/v${TYPST_VERSION}/typst-x86_64-unknown-linux-musl.tar.xz" \
    | tar -xJ -C /tmp \
    && mv /tmp/typst-x86_64-unknown-linux-musl/typst /usr/local/bin/typst \
    && chmod +x /usr/local/bin/typst \
    && rm -rf /tmp/typst-*

COPY pyproject.toml README.md ./
COPY ppd ./ppd
COPY templates ./templates
COPY data/config.yaml ./data/config.yaml

RUN pip install --no-cache-dir -e .

RUN mkdir -p data/source output workspaces

# Cloud hosts (Render, Railway, Fly) inject PORT; local/docker default is 8765.
ENV PORT=8765
EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT:-8765}/health" || exit 1

CMD ["sh", "-c", "uvicorn ppd.http_server:app --host 0.0.0.0 --port ${PORT:-8765}"]
