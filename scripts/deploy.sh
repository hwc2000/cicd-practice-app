#!/usr/bin/env bash
set -euo pipefail

APP_NAME="cicd-practice-app"
IMAGE_NAME="cicd-practice-app:latest"
IMAGE_TAR="/tmp/cicd-practice-app.tar"
PORT="8000"

docker load -i "${IMAGE_TAR}"
docker rm -f "${APP_NAME}" >/dev/null 2>&1 || true
docker run -d \
  --name "${APP_NAME}" \
  --restart unless-stopped \
  -p "${PORT}:8000" \
  "${IMAGE_NAME}"
