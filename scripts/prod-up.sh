#!/usr/bin/env bash
# Production deploy helper for legacy docker-compose v1 + Docker Engine 29.
# Removes stale containers first to avoid KeyError: 'ContainerConfig' on recreate.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMPOSE=(docker-compose -f docker-compose.prod.yml)

echo "Stopping and removing existing prod containers..."
"${COMPOSE[@]}" down --remove-orphans 2>/dev/null || true

# Hash-prefixed leftovers from failed recreate attempts
mapfile -t STALE < <(docker ps -aq --filter name=c0ll3ct1v3 2>/dev/null || true)
if ((${#STALE[@]})); then
  docker rm -f "${STALE[@]}" 2>/dev/null || true
fi

echo "Starting production stack..."
"${COMPOSE[@]}" up -d --remove-orphans

echo ""
"${COMPOSE[@]}" ps
