#!/bin/bash
# Check that the deployed cert covers apex + wildcard artist subdomains.
set -euo pipefail

DOMAIN="${1:-c0ll3ct1v3.xyz}"
SAMPLE_ARTIST="${2:-phillipjames}"
CERT_FILE="${3:-./infrastructure/ssl/cert.pem}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok() { echo -e "${GREEN}OK${NC} $1"; }
warn() { echo -e "${YELLOW}WARN${NC} $1"; }
fail() { echo -e "${RED}FAIL${NC} $1"; exit 1; }

check_host() {
  local host="$1"
  echo ""
  echo "=== $host ==="
  if ! getent hosts "$host" >/dev/null 2>&1 && ! dig +short "$host" | grep -q .; then
    warn "DNS does not resolve for $host"
    return 1
  fi
  if ! echo | openssl s_client -connect "${host}:443" -servername "$host" 2>/dev/null \
      | openssl x509 -noout -subject -dates -ext subjectAltName 2>/dev/null; then
    fail "Could not read TLS cert from $host:443"
  fi
}

if [ -f "$CERT_FILE" ]; then
  echo "Local cert file: $CERT_FILE"
  openssl x509 -in "$CERT_FILE" -noout -subject -dates -ext subjectAltName 2>/dev/null || true
  if openssl x509 -in "$CERT_FILE" -noout -text 2>/dev/null | grep -q "DNS:\\*\\.${DOMAIN}"; then
    ok "Local cert includes wildcard *.$DOMAIN"
  else
    warn "Local cert missing wildcard *.$DOMAIN — artist subdomains will show cert errors"
    warn "Re-run: ./infrastructure/scripts/setup-ssl.sh $DOMAIN"
  fi
else
  warn "No local cert at $CERT_FILE (check inside frontend container: /etc/nginx/ssl/cert.pem)"
fi

check_host "$DOMAIN"
check_host "www.$DOMAIN"
check_host "${SAMPLE_ARTIST}.${DOMAIN}"

echo ""
ok "Done. SAN must list DNS:*.$DOMAIN and DNS:$DOMAIN for artist subdomains to work."
