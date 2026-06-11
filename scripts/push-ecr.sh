#!/usr/bin/env bash
# Build and push production images to ECR. Run on a machine with disk space (not the small EC2 box).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

REGION="${AWS_REGION:-${REGION:-us-east-2}}"
AWS_ACCOUNT="${AWS_ACCOUNT:-$(aws sts get-caller-identity --query Account --output text)}"
REGISTRY="${ECR_REGISTRY:-${AWS_ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com}"

export REACT_APP_AUTH0_DOMAIN="${REACT_APP_AUTH0_DOMAIN:?Set REACT_APP_AUTH0_DOMAIN}"
export REACT_APP_AUTH0_CLIENT_ID="${REACT_APP_AUTH0_CLIENT_ID:?Set REACT_APP_AUTH0_CLIENT_ID}"
export REACT_APP_AUTH0_AUDIENCE="${REACT_APP_AUTH0_AUDIENCE:?Set REACT_APP_AUTH0_AUDIENCE}"
export REACT_APP_API_URL="${REACT_APP_API_URL:-/api}"

echo "Registry: $REGISTRY (region $REGION)"

for repo in c0ll3ct1v3-backend c0ll3ct1v3-frontend c0ll3ct1v3-worker; do
  aws ecr describe-repositories --repository-names "$repo" --region "$REGION" >/dev/null 2>&1 \
    || aws ecr create-repository --repository-name "$repo" --region "$REGION"
done

aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"

docker build -f backend/Dockerfile.prod -t c0ll3ct1v3-backend:latest ./backend
docker build -f backend/Dockerfile.worker -t c0ll3ct1v3-worker:latest ./backend
docker build -f frontend/Dockerfile.prod \
  --build-arg REACT_APP_AUTH0_DOMAIN \
  --build-arg REACT_APP_AUTH0_CLIENT_ID \
  --build-arg REACT_APP_AUTH0_AUDIENCE \
  --build-arg REACT_APP_API_URL \
  -t c0ll3ct1v3-frontend:latest ./frontend

for name in backend frontend worker; do
  docker tag "c0ll3ct1v3-${name}:latest" "$REGISTRY/c0ll3ct1v3-${name}:latest"
  docker push "$REGISTRY/c0ll3ct1v3-${name}:latest"
done

echo "Pushed to $REGISTRY"
