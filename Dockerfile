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
RUN python -m venv /opt/venv
WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY main.py ./
COPY libs ./libs
ENV TZ=Asia/Taipei
USER app
CMD ["python", "main.py"]
