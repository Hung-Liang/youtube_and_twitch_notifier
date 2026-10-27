# syntax=docker/dockerfile:1

# Base and apt layers mirror anki-telegram so both images share them on the server; UID/GID match it too
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    TZ=UTC
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*
ARG APP_UID=1000
ARG APP_GID=1000
RUN groupadd -g ${APP_GID} app \
    && useradd -m -u ${APP_UID} -g ${APP_GID} -s /bin/bash app
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_NO_CACHE=1 \
    UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
# uv is mounted for this step only, so it stays out of the final image
RUN --mount=from=ghcr.io/astral-sh/uv:0.13.5,source=/uv,target=/bin/uv \
    uv sync --frozen --no-dev
COPY main.py ./
COPY libs ./libs
ENV TZ=Asia/Taipei
USER app
CMD ["python", "main.py"]
