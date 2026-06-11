#!/usr/bin/env bash
# Build and push production images to ECR. Run on a machine with disk space (not the small EC2 box).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

REGION="${AWS_REGION:-${REGION:-us-east-2}}"
AWS_ACCOUNT="${AWS_ACCOUNT:-$(aws sts get-caller-identity --query Account --output text)}"
REGISTRY="${ECR_REGISTRY:-${AWS_ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com}"

# Load frontend/.env without bash `source` (unquoted spaces in values break sourcing).
load_frontend_env() {
  [[ -f frontend/.env ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line#"${line%%[![:space:]]*}"}"
    [[ -z "$line" || "$line" == \#* ]] && continue
    if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      key="${BASH_REMATCH[1]}"
      val="${BASH_REMATCH[2]}"
      val="${val%$'\r'}"
      if [[ "$val" =~ ^\".*\"$ ]]; then
        val="${val:1:${#val}-2}"
      elif [[ "$val" =~ ^\'.*\'$ ]]; then
        val="${val:1:${#val}-2}"
      fi
      export "$key=$val"
    fi
  done < frontend/.env
}

load_frontend_env

export REACT_APP_AUTH0_DOMAIN="${REACT_APP_AUTH0_DOMAIN:?Set REACT_APP_AUTH0_DOMAIN (or add to frontend/.env)}"
export REACT_APP_AUTH0_CLIENT_ID="${REACT_APP_AUTH0_CLIENT_ID:?Set REACT_APP_AUTH0_CLIENT_ID (or add to frontend/.env)}"
export REACT_APP_AUTH0_AUDIENCE="${REACT_APP_AUTH0_AUDIENCE:?Set REACT_APP_AUTH0_AUDIENCE (or add to frontend/.env)}"
export REACT_APP_API_URL="/api"
export REACT_APP_AUTH0_SCOPE="${REACT_APP_AUTH0_SCOPE:-openid profile email}"
export REACT_APP_AUTH0_MFA_ACR="${REACT_APP_AUTH0_MFA_ACR:-http://schemas.openid.net/pape/policies/2007/06/multi-factor}"
export REACT_APP_DROPBOX_APP_KEY="${REACT_APP_DROPBOX_APP_KEY:-}"
export REACT_APP_GOOGLE_CLIENT_ID="${REACT_APP_GOOGLE_CLIENT_ID:-}"
export REACT_APP_GOOGLE_API_KEY="${REACT_APP_GOOGLE_API_KEY:-}"
export REACT_APP_GOOGLE_APP_ID="${REACT_APP_GOOGLE_APP_ID:-}"
export REACT_APP_DEFAULT_TENANT="${REACT_APP_DEFAULT_TENANT:-}"

if [[ -z "$REACT_APP_DROPBOX_APP_KEY" || -z "$REACT_APP_GOOGLE_CLIENT_ID" ]]; then
  echo "ERROR: Cloud import keys missing. Ensure frontend/.env exists in $ROOT with REACT_APP_DROPBOX_APP_KEY and REACT_APP_GOOGLE_*." >&2
  exit 1
fi

echo "Registry: $REGISTRY (region $REGION)"
echo "Frontend build env: DROPBOX=${REACT_APP_DROPBOX_APP_KEY:0:4}… GOOGLE_CLIENT=${REACT_APP_GOOGLE_CLIENT_ID:0:12}…"

for repo in c0ll3ct1v3-backend c0ll3ct1v3-frontend c0ll3ct1v3-worker; do
  aws ecr describe-repositories --repository-names "$repo" --region "$REGION" >/dev/null 2>&1 \
    || aws ecr create-repository --repository-name "$repo" --region "$REGION"
done

aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"

docker build -f backend/Dockerfile.prod -t c0ll3ct1v3-backend:latest ./backend
docker build -f backend/Dockerfile.worker -t c0ll3ct1v3-worker:latest ./backend

# --no-cache: prior builds cached empty REACT_APP_* layers when args were not passed.
docker build --no-cache -f frontend/Dockerfile.prod \
  --build-arg REACT_APP_API_URL \
  --build-arg REACT_APP_AUTH0_DOMAIN \
  --build-arg REACT_APP_AUTH0_CLIENT_ID \
  --build-arg REACT_APP_AUTH0_AUDIENCE \
  --build-arg REACT_APP_AUTH0_SCOPE \
  --build-arg REACT_APP_AUTH0_MFA_ACR \
  --build-arg REACT_APP_DROPBOX_APP_KEY \
  --build-arg REACT_APP_GOOGLE_CLIENT_ID \
  --build-arg REACT_APP_GOOGLE_API_KEY \
  --build-arg REACT_APP_GOOGLE_APP_ID \
  --build-arg REACT_APP_DEFAULT_TENANT \
  -t c0ll3ct1v3-frontend:latest ./frontend

for name in backend frontend worker; do
  docker tag "c0ll3ct1v3-${name}:latest" "$REGISTRY/c0ll3ct1v3-${name}:latest"
  docker push "$REGISTRY/c0ll3ct1v3-${name}:latest"
done

echo "Pushed to $REGISTRY"
