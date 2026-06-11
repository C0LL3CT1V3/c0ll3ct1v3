#!/usr/bin/env bash
# Production deploy: ECR login, pull images, start stack.
# Removes stale containers first (docker-compose v1 + Docker 29 ContainerConfig workaround).
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

COMPOSE=(docker-compose -f docker-compose.prod.yml)

echo "ECR registry: $ECR_REGISTRY"

echo "Logging into ECR..."
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ECR_REGISTRY"

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

echo ""
"${COMPOSE[@]}" ps
