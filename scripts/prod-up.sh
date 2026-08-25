#!/usr/bin/env bash
# Production deploy: pull app images and recreate app containers.
# Never restarts db/redis unless you pass --full (emergency only).
#
# Default path is rolling: busy-gate → pull → backend → worker → frontend → health.
# Open portal tabs keep their React state; there is a short API 502 while backend swaps.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

FORCE="${DEPLOY_FORCE:-0}"
FULL=0
IDLE_WAIT_SECONDS="${DEPLOY_BUSY_WAIT_SECONDS:-600}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force) FORCE=1 ;;
    --full) FULL=1 ;;
    -h|--help)
      echo "Usage: $0 [--force] [--full]"
      echo "  --force  skip the busy gate (in-flight uploads / recent auth)"
      echo "  --full   compose down the whole stack including db/redis (downtime)"
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
  shift
done

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

REGION="${AWS_REGION:-${REGION:-us-east-2}}"
AWS_ACCOUNT="${AWS_ACCOUNT:-$(aws sts get-caller-identity --query Account --output text)}"
export ECR_REGISTRY="${ECR_REGISTRY:-${AWS_ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com}"

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose -f docker-compose.prod.yml)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose -f docker-compose.prod.yml)
else
  echo "ERROR: Docker Compose not found. Install the plugin: sudo apt install docker-compose-plugin" >&2
  exit 1
fi

backend_running() {
  "${COMPOSE[@]}" exec -T backend true >/dev/null 2>&1
}

wait_for_idle() {
  if [[ "$FORCE" == "1" ]]; then
    echo "Busy gate skipped (--force)."
    return 0
  fi
  if ! backend_running; then
    echo "Backend is not running; skipping busy gate."
    return 0
  fi
  if ! "${COMPOSE[@]}" exec -T backend python -c "import app.services.deploy_gate" >/dev/null 2>&1; then
    echo "Running backend image has no deploy_gate yet; skipping busy gate for this ship."
    return 0
  fi

  echo "Waiting for idle portal (no in-flight uploads, no authenticated API for DEPLOY_IDLE_SECONDS)..."
  local deadline=$((SECONDS + IDLE_WAIT_SECONDS))
  local out
  while true; do
    if out=$("${COMPOSE[@]}" exec -T backend python -m app.services.deploy_gate 2>/dev/null); then
      echo "$out"
      echo "Portal is idle."
      return 0
    fi
    echo "${out:-busy-gate check failed}"
    if (( SECONDS >= deadline )); then
      echo "ERROR: still busy after ${IDLE_WAIT_SECONDS}s. Retry later or pass --force for an incident." >&2
      return 1
    fi
    sleep 15
  done
}

wait_http() {
  local url="$1"
  local extra=("${@:2}")
  local i
  for i in $(seq 1 30); do
    if curl -sf --max-time 5 "${extra[@]}" "$url" >/dev/null; then
      return 0
    fi
    sleep 3
  done
  echo "ERROR: ${url} did not become healthy" >&2
  return 1
}

health_check() {
  echo "Checking health..."
  wait_http "http://127.0.0.1:8000/health"
  local code
  code=$(curl -sk -o /dev/null -w '%{http_code}' --max-time 5 https://127.0.0.1/ || true)
  if [[ ! "$code" =~ ^(200|301|302)$ ]]; then
    echo "ERROR: nginx https://127.0.0.1/ returned ${code:-empty}" >&2
    return 1
  fi
  echo "Health ok (API /health + nginx ${code})."
}

ecr_login() {
  echo "ECR registry: $ECR_REGISTRY"
  echo "Logging into ECR..."
  aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ECR_REGISTRY"
}

rolling_up() {
  echo "Pulling app images (db/redis left running)..."
  "${COMPOSE[@]}" pull backend media-worker frontend

  echo "Recreating backend..."
  "${COMPOSE[@]}" up -d --no-deps --force-recreate --no-build backend
  wait_http "http://127.0.0.1:8000/health"

  echo "Recreating media-worker..."
  "${COMPOSE[@]}" up -d --no-deps --force-recreate --no-build media-worker

  echo "Recreating frontend (nginx)..."
  "${COMPOSE[@]}" up -d --no-deps --force-recreate --no-build frontend
}

full_down_up() {
  echo "WARNING: --full stops db and redis. In-progress work will fail and the site goes down." >&2
  echo "Stopping and removing existing prod containers..."
  "${COMPOSE[@]}" down --remove-orphans 2>/dev/null || true

  mapfile -t STALE < <(docker ps -aq --filter name=c0ll3ct1v3 2>/dev/null || true)
  if ((${#STALE[@]})); then
    docker rm -f "${STALE[@]}" 2>/dev/null || true
  fi

  echo "Pulling images..."
  "${COMPOSE[@]}" pull

  echo "Starting production stack..."
  "${COMPOSE[@]}" up -d --remove-orphans
}

ecr_login
wait_for_idle

if [[ "$FULL" == "1" ]]; then
  full_down_up
else
  rolling_up
fi

health_check
echo ""
"${COMPOSE[@]}" ps
