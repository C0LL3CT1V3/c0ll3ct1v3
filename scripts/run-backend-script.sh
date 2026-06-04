#!/usr/bin/env bash
# Run a backend script with project deps (Docker). Usage:
#   ./scripts/run-backend-script.sh migrate_storage_prefixes.py --dry-run
#   ./scripts/run-backend-script.sh seed_artist_tenant.py
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="${1:?script name under backend/scripts/}"
shift
cd "$ROOT"
COMPOSE="docker compose"
if ! docker compose version >/dev/null 2>&1; then
  COMPOSE="docker-compose"
fi
exec $COMPOSE -f docker-compose.dev.yml exec -T backend python "scripts/${SCRIPT}" "$@"
