#!/usr/bin/env bash
# One-time AWS setup for production media storage (bucket c0ll3ct1v3-vaults).
# Run where AWS CLI is authenticated (account 756090160994).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUCKET="${S3_MEDIA_BUCKET:-c0ll3ct1v3-vaults}"
REGION="${AWS_REGION:-us-east-2}"
IAM_USER="${S3_MEDIA_IAM_USER:-c0ll3ct1v3-media}"
POLICY_NAME="${S3_MEDIA_POLICY_NAME:-C0ll3ct1v3VaultMediaAccess}"

echo "Account: $(aws sts get-caller-identity --query Account --output text)"
echo "Bucket:  $BUCKET ($REGION)"

aws s3api head-bucket --bucket "$BUCKET" >/dev/null
echo "✓ Bucket exists"

echo "Applying CORS (browser presigned uploads)..."
aws s3api put-bucket-cors --bucket "$BUCKET" --cors-configuration "file://${ROOT}/scripts/aws-s3-cors.json"
echo "✓ CORS configured"

POLICY_ARN=$(aws iam list-policies --scope Local --query "Policies[?PolicyName=='${POLICY_NAME}'].Arn | [0]" --output text)
if [[ "$POLICY_ARN" == "None" || -z "$POLICY_ARN" ]]; then
  POLICY_ARN=$(aws iam create-policy \
    --policy-name "$POLICY_NAME" \
    --policy-document "file://${ROOT}/scripts/aws-s3-media-policy.json" \
    --description "S3 access for c0ll3ct1v3 media API" \
    --query Policy.Arn --output text)
  echo "✓ Created IAM policy $POLICY_NAME"
else
  aws iam create-policy-version \
    --policy-arn "$POLICY_ARN" \
    --policy-document "file://${ROOT}/scripts/aws-s3-media-policy.json" \
    --set-as-default >/dev/null 2>&1 || true
  echo "✓ IAM policy $POLICY_NAME exists ($POLICY_ARN)"
fi

if ! aws iam get-user --user-name "$IAM_USER" >/dev/null 2>&1; then
  aws iam create-user --user-name "$IAM_USER" >/dev/null
  echo "✓ Created IAM user $IAM_USER"
else
  echo "✓ IAM user $IAM_USER exists"
fi

aws iam attach-user-policy --user-name "$IAM_USER" --policy-arn "$POLICY_ARN" 2>/dev/null || true
echo "✓ Policy attached to $IAM_USER"

KEY_COUNT=$(aws iam list-access-keys --user-name "$IAM_USER" --query 'length(AccessKeyMetadata)' --output text)
if [[ "$KEY_COUNT" -ge 2 ]]; then
  echo ""
  echo "WARN: $IAM_USER already has 2 access keys. Delete an old key in IAM console before creating another."
  echo "      Or set SPACES_ACCESS_KEY / SPACES_SECRET_KEY from an existing key in backend/.env on EC2."
else
  echo ""
  echo "Creating access key for $IAM_USER (save output — secret is shown once):"
  aws iam create-access-key --user-name "$IAM_USER" --output json
fi

echo ""
echo "=== backend/.env on EC2 (paste access key from above) ==="
cat <<EOF
SPACES_ENABLED=true
SPACES_ENDPOINT=https://s3.${REGION}.amazonaws.com
SPACES_REGION=${REGION}
SPACES_BUCKET=${BUCKET}
SPACES_PUBLIC_ENDPOINT=
SPACES_ACCESS_KEY=PASTE_ACCESS_KEY_ID
SPACES_SECRET_KEY=PASTE_SECRET_ACCESS_KEY
MEDIA_CDN_BASE_URL=
EOF

echo ""
echo "Keep bucket private (public access block ON). Uploads use presigned URLs + CORS."
echo "Then: docker compose -f docker-compose.prod.yml up -d --force-recreate backend media-worker"
