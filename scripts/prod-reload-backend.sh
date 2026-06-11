#!/usr/bin/env bash
# Recreate backend + media-worker after backend/.env changes (S3 keys, etc.).
# Does not pull or touch db/redis/frontend — use ./scripts/prod-up.sh for full deploy.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

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
  echo "ERROR: Docker Compose not found." >&2
  exit 1
fi

echo "ECR registry: $ECR_REGISTRY"
echo "Recreating backend + media-worker (--no-deps)..."
"${COMPOSE[@]}" up -d --force-recreate --no-deps backend media-worker
"${COMPOSE[@]}" ps backend media-worker
