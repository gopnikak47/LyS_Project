# syntax=docker/dockerfile:1.7
# Image dùng chung cho api / worker / beat (cùng mã nguồn, khác lệnh chạy).
#
# Mạng có proxy TLS (CA nội bộ): build kèm secret tùy chọn, ví dụ
#   docker build --secret id=ca_bundle,src=/path/ca-bundle.crt ...
ARG PYTHON_VERSION=3.11

FROM ghcr.io/astral-sh/uv:0.12.22 AS uv

# ---------------------------------------------------------------- builder
FROM python:${PYTHON_VERSION}-slim AS builder
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /src

# Cài phụ thuộc trước (tận dụng cache layer khi chỉ sửa code).
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY apps/worker/pyproject.toml apps/worker/pyproject.toml
COPY packages/nlp/pyproject.toml packages/nlp/pyproject.toml
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=secret,id=ca_bundle,required=false \
    if [ -s /run/secrets/ca_bundle ]; then export SSL_CERT_FILE=/run/secrets/ca_bundle; fi; \
    uv sync --frozen --no-dev --all-packages --no-install-workspace

COPY apps/api apps/api
COPY apps/worker apps/worker
COPY packages/nlp packages/nlp
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=secret,id=ca_bundle,required=false \
    if [ -s /run/secrets/ca_bundle ]; then export SSL_CERT_FILE=/run/secrets/ca_bundle; fi; \
    uv sync --frozen --no-dev --all-packages --no-editable

# ---------------------------------------------------------------- runtime
FROM python:${PYTHON_VERSION}-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
RUN groupadd --gid 10001 app \
 && useradd --uid 10001 --gid app --create-home app \
 && mkdir -p /data/storage /data/models \
 && chown -R app:app /data
COPY --from=builder --chown=app:app /app/.venv /app/.venv
WORKDIR /app
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--timeout-graceful-shutdown", "20"]
