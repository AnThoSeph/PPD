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
    xz-utils \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Download to a file first (pipe + tar -xJ fails without xz-utils on slim images).
RUN curl -fsSL "https://github.com/typst/typst/releases/download/v${TYPST_VERSION}/typst-x86_64-unknown-linux-musl.tar.xz" \
    -o /tmp/typst.tar.xz \
    && mkdir -p /tmp/typst-extract \
    && tar -xJf /tmp/typst.tar.xz -C /tmp/typst-extract \
    && install -m 755 "$(find /tmp/typst-extract -name typst -type f | head -1)" /usr/local/bin/typst \
    && rm -rf /tmp/typst.tar.xz /tmp/typst-extract

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
