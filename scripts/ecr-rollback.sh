#!/usr/bin/env bash
# Point ECR :latest at an already-pushed git SHA (no rebuild). Then rolling-restart on the box.
#
#   ./scripts/ecr-rollback.sh <40-char-or-short-sha>
#   # on EC2: cd /home/ubuntu/c0ll3ct1v3 && ./scripts/prod-up.sh --force
set -euo pipefail

SHA="${1:-}"
if [[ ! "$SHA" =~ ^[0-9a-fA-F]{7,40}$ ]]; then
  echo "Usage: $0 <git-sha-already-pushed-to-ecr>" >&2
  exit 1
fi

REGION="${AWS_REGION:-${REGION:-us-east-2}}"

for repo in c0ll3ct1v3-backend c0ll3ct1v3-frontend c0ll3ct1v3-worker; do
  echo "Retagging ${repo}:latest <- ${SHA}"
  MANIFEST=$(aws ecr batch-get-image \
    --region "$REGION" \
    --repository-name "$repo" \
    --image-ids "imageTag=${SHA}" \
    --query 'images[0].imageManifest' \
    --output text)
  if [[ -z "$MANIFEST" || "$MANIFEST" == "None" ]]; then
    echo "ERROR: no image ${repo}:${SHA} in ${REGION}. Push that SHA first (or use the full 40-char tag)." >&2
    exit 1
  fi
  aws ecr put-image \
    --region "$REGION" \
    --repository-name "$repo" \
    --image-tag latest \
    --image-manifest "$MANIFEST" >/dev/null
done

echo "ECR :latest now points at ${SHA}."
echo "On the prod box: cd /home/ubuntu/c0ll3ct1v3 && ./scripts/prod-up.sh --force"
