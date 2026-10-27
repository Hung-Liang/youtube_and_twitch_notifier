#!/usr/bin/env bash
# Build and (re)start the notifier. Safe to re-run after `git pull`.
# The previous image is kept as chu_yt_notification:prev for rollback.
set -euo pipefail

cd "$(dirname "$0")/.."

die() { echo "ERROR: $*" >&2; exit 1; }

[[ -f .env ]] || die ".env not found; copy it from .env_example and fill it in"

app_env=$(grep -E '^APP_ENV=' .env | tail -n1 | cut -d= -f2- | tr -d '"' || true)
if [[ "$app_env" == "dev" ]]; then
  [[ -f config/dev_config.py ]] || die "config/dev_config.py not found"
  echo "WARNING: APP_ENV=dev, loading config/dev_config.py"
else
  [[ -f config/config.py ]] || die "config/config.py not found"
fi

echo "==> Preparing asset/ and log/"
mkdir -p asset log

if docker image inspect chu_yt_notification:latest >/dev/null 2>&1; then
  echo "==> Tagging current image as :prev"
  docker tag chu_yt_notification:latest chu_yt_notification:prev
fi

echo "==> Building image"
docker compose build

echo "==> Checking config"
docker compose run --rm --no-deps notifier python main.py --check-config

echo "==> Starting notifier"
docker compose up -d
docker image prune -f

docker compose ps
echo "Done. Follow logs with: docker compose logs -f notifier"
echo "Rollback: docker tag chu_yt_notification:prev chu_yt_notification:latest && docker compose up -d"
