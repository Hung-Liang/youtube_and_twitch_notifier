#!/usr/bin/env bash
# Create asset/ and log/ on the host and hand them to the container's app user.
# Run before `docker compose up`: the host user's uid may differ from the image's,
# and Docker creates a missing bind-mount source as root; either way app cannot write.
set -euo pipefail

cd "$(dirname "$0")/.."

# Must match APP_UID/APP_GID in the Dockerfile
APP_UID=${APP_UID:-1000}
APP_GID=${APP_GID:-1000}

mkdir -p asset log

for dir in asset log; do
  if [[ -n "$(find "$dir" \( ! -uid "$APP_UID" -o ! -gid "$APP_GID" \) -print -quit)" ]]; then
    echo "==> chown $dir to $APP_UID:$APP_GID"
    if [[ $(id -u) -eq 0 ]]; then
      chown -R "$APP_UID:$APP_GID" "$dir"
    else
      sudo chown -R "$APP_UID:$APP_GID" "$dir"
    fi
  fi
done
