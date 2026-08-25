#!/usr/bin/env bash
# CodeBuild deploy stage: SSM into prod EC2, reset to this commit, rolling prod-up.
# Polls get-command-invocation until the shell on the box finishes (not fire-and-forget).
set -euo pipefail

INSTANCE_ID="${EC2_INSTANCE_ID:?EC2_INSTANCE_ID is required}"
DEPLOY_PATH="${DEPLOY_PATH:-/home/ubuntu/c0ll3ct1v3}"
REGION="${AWS_REGION:-us-east-2}"
SHA="${CODEBUILD_RESOLVED_SOURCE_VERSION:?CODEBUILD_RESOLVED_SOURCE_VERSION is required}"
FORCE="${DEPLOY_FORCE:-0}"

if [[ ! "$SHA" =~ ^[0-9a-fA-F]{7,40}$ ]]; then
  echo "ERROR: refusing to reset to non-SHA source version: $SHA" >&2
  exit 1
fi
if [[ ! "$INSTANCE_ID" =~ ^i-[0-9a-fA-F]+$ ]]; then
  echo "ERROR: invalid EC2_INSTANCE_ID: $INSTANCE_ID" >&2
  exit 1
fi
if [[ "$DEPLOY_PATH" != /home/ubuntu/c0ll3ct1v3 ]]; then
  echo "ERROR: refusing unexpected DEPLOY_PATH: $DEPLOY_PATH" >&2
  exit 1
fi

export SHELL_LINE="set -euo pipefail; cd ${DEPLOY_PATH}; git fetch --prune origin main; git reset --hard ${SHA}; DEPLOY_FORCE=${FORCE} ./scripts/prod-up.sh"
PARAMS=$(python3 -c 'import json, os; print(json.dumps({"commands": [os.environ["SHELL_LINE"]]}))')

echo "SSM AWS-RunShellScript on ${INSTANCE_ID} @ ${SHA}"
CMD_ID=$(aws ssm send-command \
  --region "$REGION" \
  --instance-ids "$INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --comment "c0ll3ct1v3 pipeline ${SHA}" \
  --timeout-seconds 900 \
  --parameters "$PARAMS" \
  --query "Command.CommandId" \
  --output text)

echo "Command id: $CMD_ID"
STATUS="Pending"
DEADLINE=$((SECONDS + 900))
while (( SECONDS < DEADLINE )); do
  STATUS=$(aws ssm get-command-invocation \
    --region "$REGION" \
    --command-id "$CMD_ID" \
    --instance-id "$INSTANCE_ID" \
    --query "Status" \
    --output text 2>/dev/null || echo "Pending")
  echo "SSM status: $STATUS"
  case "$STATUS" in
    Success)
      aws ssm get-command-invocation \
        --region "$REGION" \
        --command-id "$CMD_ID" \
        --instance-id "$INSTANCE_ID" \
        --query "StandardOutputContent" \
        --output text
      exit 0
      ;;
    Failed|Cancelled|TimedOut|Cancelling|Undeliverable|Terminated)
      echo "----- stdout -----"
      aws ssm get-command-invocation \
        --region "$REGION" \
        --command-id "$CMD_ID" \
        --instance-id "$INSTANCE_ID" \
        --query "StandardOutputContent" \
        --output text || true
      echo "----- stderr -----"
      aws ssm get-command-invocation \
        --region "$REGION" \
        --command-id "$CMD_ID" \
        --instance-id "$INSTANCE_ID" \
        --query "StandardErrorContent" \
        --output text || true
      exit 1
      ;;
  esac
  sleep 5
done

echo "ERROR: timed out waiting for SSM command $CMD_ID (last status: $STATUS)" >&2
exit 1
