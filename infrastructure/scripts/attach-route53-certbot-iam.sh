#!/bin/bash
# Attach Route 53 DNS-01 permissions to the EC2 instance role (run with admin AWS creds).
# Usage:
#   ./infrastructure/scripts/attach-route53-certbot-iam.sh EC2_INSTANCE_ID
#   ./infrastructure/scripts/attach-route53-certbot-iam.sh --role-name MyEc2Role
set -euo pipefail

DOMAIN="${DOMAIN:-c0ll3ct1v3.xyz}"
POLICY_NAME="${POLICY_NAME:-CertbotRoute53DNS01}"
ROLE_NAME=""

usage() {
  echo "Usage: $0 EC2_INSTANCE_ID"
  echo "   or: $0 --role-name IAM_ROLE_NAME"
  echo ""
  echo "Run from a machine with IAM admin creds (laptop/hermes), not from the EC2 instance."
  exit 1
}

if [ $# -eq 0 ]; then
  usage
fi

if [ "$1" = "--role-name" ]; then
  [ $# -ge 2 ] || usage
  ROLE_NAME="$2"
else
  INSTANCE_ID="$1"
  PROFILE_ARN="$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].IamInstanceProfile.Arn' \
    --output text)"
  if [ -z "$PROFILE_ARN" ] || [ "$PROFILE_ARN" = "None" ]; then
    echo "No IAM instance profile on $INSTANCE_ID. Attach one in EC2 console first."
    exit 1
  fi
  PROFILE_NAME="${PROFILE_ARN##*/}"
  ROLE_NAME="$(aws iam get-instance-profile \
    --instance-profile-name "$PROFILE_NAME" \
    --query 'InstanceProfile.Roles[0].RoleName' \
    --output text)"
fi

ZONE_ID="$(aws route53 list-hosted-zones-by-name \
  --dns-name "$DOMAIN" \
  --query 'HostedZones[0].Id' \
  --output text | sed 's|/hostedzone/||')"

if [ -z "$ZONE_ID" ] || [ "$ZONE_ID" = "None" ]; then
  echo "Could not find Route 53 hosted zone for $DOMAIN"
  exit 1
fi

POLICY_FILE="$(mktemp)"
trap 'rm -f "$POLICY_FILE"' EXIT

cat > "$POLICY_FILE" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CertbotRoute53List",
      "Effect": "Allow",
      "Action": [
        "route53:ListHostedZones",
        "route53:GetChange"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CertbotRoute53ChallengeRecords",
      "Effect": "Allow",
      "Action": "route53:ChangeResourceRecordSets",
      "Resource": "arn:aws:route53:::hostedzone/${ZONE_ID}"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name "$POLICY_NAME" \
  --policy-document "file://${POLICY_FILE}"

echo "Attached inline policy ${POLICY_NAME} to role ${ROLE_NAME}"
echo "Hosted zone: ${ZONE_ID} (${DOMAIN})"
echo ""
echo "On EC2, verify: aws sts get-caller-identity && ./infrastructure/scripts/setup-ssl.sh"
