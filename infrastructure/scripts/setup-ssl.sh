#!/bin/bash

# C0ll3CT1V3 SSL Certificate Setup Script
# Issues a Let's Encrypt wildcard cert via Route 53 DNS-01 (artist subdomains).
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SSL_DIR="$PROJECT_ROOT/infrastructure/ssl"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.prod.yml"
EMAIL="${CERTBOT_EMAIL:-archie@c0ll3ctv3.xyz}"
DOMAIN="${1:-c0ll3ct1v3.xyz}"
WILDCARD_DOMAIN="*.$DOMAIN"

log_info "Setting up wildcard SSL for $DOMAIN and $WILDCARD_DOMAIN"
log_info "Certbot contact email: $EMAIL"

if [ ! -f "$COMPOSE_FILE" ]; then
    log_error "Run from the project root or ensure $COMPOSE_FILE exists"
    exit 1
fi

cd "$PROJECT_ROOT"

if ! command -v certbot &> /dev/null || ! python3 -c "import certbot_dns_route53" 2>/dev/null; then
    log_info "Installing Certbot and Route 53 DNS plugin..."
    sudo apt-get update
    sudo apt-get install -y certbot python3-certbot-dns-route53
else
    log_info "Certbot with Route 53 DNS plugin is already installed"
fi

mkdir -p "$SSL_DIR"

log_info "Checking Route 53 / AWS credentials..."
if ! aws sts get-caller-identity &>/dev/null; then
    log_error "AWS credentials not available on this host."
    log_error "Attach an EC2 instance role with Route 53 permissions, or configure AWS CLI."
    log_error "See infrastructure/scripts/aws-route53-certbot-iam-policy.json"
    exit 1
fi
log_info "AWS credentials OK"

log_info "Verifying DNS (apex + wildcard should resolve to this server)..."
PUBLIC_IP="$(curl -fsS ifconfig.me 2>/dev/null || curl -fsS ipinfo.io/ip 2>/dev/null || true)"
APEX_IP="$(dig +short "$DOMAIN" | tail -n1)"
WILD_IP="$(dig +short "artist-test.$DOMAIN" | tail -n1)"

if [ -n "$PUBLIC_IP" ] && [ -n "$APEX_IP" ] && [ "$APEX_IP" != "$PUBLIC_IP" ]; then
    log_warn "Apex $DOMAIN -> $APEX_IP, but this host is $PUBLIC_IP"
elif [ -n "$APEX_IP" ]; then
    log_info "Apex DNS resolves to $APEX_IP"
fi

if [ -z "$WILD_IP" ]; then
    log_warn "No wildcard DNS yet. Add a Route 53 A record: * -> your EC2 Elastic IP"
else
    log_info "Wildcard DNS sample resolves to $WILD_IP"
fi

if command -v ufw &> /dev/null; then
    sudo ufw allow 80/tcp 2>/dev/null || true
    sudo ufw allow 443/tcp 2>/dev/null || true
fi

log_info "Obtaining wildcard certificate from Let's Encrypt (Route 53 DNS challenge)..."
sudo certbot certonly \
    --dns-route53 \
    --non-interactive \
    --agree-tos \
    --email "$EMAIL" \
    -d "$DOMAIN" \
    -d "$WILDCARD_DOMAIN"

CERT_PATH="/etc/letsencrypt/live/$DOMAIN"
log_info "Copying certificates to $SSL_DIR..."
sudo cp "$CERT_PATH/fullchain.pem" "$SSL_DIR/cert.pem"
sudo cp "$CERT_PATH/privkey.pem" "$SSL_DIR/key.pem"
sudo chown "$USER:$USER" "$SSL_DIR/cert.pem" "$SSL_DIR/key.pem"
sudo chmod 644 "$SSL_DIR/cert.pem"
sudo chmod 600 "$SSL_DIR/key.pem"
log_info "Certificates copied"

log_info "Installing renewal deploy hook..."
RENEWAL_HOOK="/etc/letsencrypt/renewal-hooks/deploy/copy-c0ll3ct1v3-certs.sh"
sudo mkdir -p /etc/letsencrypt/renewal-hooks/deploy

sudo tee "$RENEWAL_HOOK" > /dev/null <<EOF
#!/bin/bash
set -e
DOMAIN="$DOMAIN"
SSL_DIR="$SSL_DIR"
COMPOSE_FILE="$COMPOSE_FILE"

cp "/etc/letsencrypt/live/\$DOMAIN/fullchain.pem" "\$SSL_DIR/cert.pem"
cp "/etc/letsencrypt/live/\$DOMAIN/privkey.pem" "\$SSL_DIR/key.pem"
chmod 644 "\$SSL_DIR/cert.pem"
chmod 600 "\$SSL_DIR/key.pem"

cd "$PROJECT_ROOT"
docker compose -f "\$COMPOSE_FILE" exec -T frontend nginx -s reload 2>/dev/null || true
EOF

sudo chmod +x "$RENEWAL_HOOK"

log_info "Testing certificate renewal (dry run)..."
if sudo certbot renew --dry-run; then
    log_info "Auto-renewal dry run succeeded"
else
    log_warn "Auto-renewal dry run failed; certs are installed but check IAM + Route 53 permissions"
fi

log_info ""
log_info "SSL setup completed."
log_info "Certs: $SSL_DIR"
log_info "Covers: $DOMAIN, *.$DOMAIN"
log_info ""
log_info "Next steps:"
log_info "1. Ensure Route 53 has A records for @, www, and * -> EC2 Elastic IP"
log_info "2. Start stack: docker compose -f docker-compose.prod.yml up -d"
log_info "3. Verify: curl -I https://$DOMAIN and https://phillipjames.$DOMAIN/epk"
log_info ""
