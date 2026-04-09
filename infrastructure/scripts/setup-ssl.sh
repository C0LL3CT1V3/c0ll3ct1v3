#!/bin/bash

# C0ll3CT1V3 SSL Certificate Setup Script
# This script sets up Let's Encrypt SSL certificates using Certbot
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if domain is provided
if [ -z "$1" ]; then
    log_error "Usage: $0 <domain.com>"
    log_error "Example: $0 example.com"
    exit 1
fi

DOMAIN=$1
WWW_DOMAIN="www.$DOMAIN"
SSL_DIR="./infrastructure/ssl"
NGINX_CONF="./infrastructure/nginx.prod.conf"
EMAIL="admin@$DOMAIN"  # Let's Encrypt requires an email

log_info "Setting up SSL certificates for $DOMAIN and $WWW_DOMAIN"

# Check if running from project root
if [ ! -f "docker-compose.prod.yml" ]; then
    log_error "Please run this script from the project root directory"
    exit 1
fi

# Install Certbot if not already installed
if ! command -v certbot &> /dev/null; then
    log_info "Installing Certbot..."
    sudo apt-get update
    sudo apt-get install -y certbot python3-certbot-nginx
else
    log_info "Certbot is already installed"
fi

# Create SSL directory if it doesn't exist
mkdir -p "$SSL_DIR"

# Check if DNS is pointing to this server
log_info "Verifying DNS configuration..."
PUBLIC_IP=$(curl -s ifconfig.me || curl -s ipinfo.io/ip)
DOMAIN_IP=$(dig +short $DOMAIN | tail -n1)

if [ -z "$DOMAIN_IP" ]; then
    log_warn "DNS for $DOMAIN is not resolving. Make sure DNS is configured correctly."
    log_warn "Continuing anyway, but certificate generation may fail..."
else
    if [ "$DOMAIN_IP" != "$PUBLIC_IP" ]; then
        log_warn "DNS for $DOMAIN points to $DOMAIN_IP, but this server's IP is $PUBLIC_IP"
        log_warn "Certificate generation may fail. Please ensure DNS is pointing to this server."
    else
        log_info "✓ DNS is correctly pointing to this server"
    fi
fi

# Ensure ports 80 and 443 are open
log_info "Checking firewall configuration..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 80/tcp 2>/dev/null || true
    sudo ufw allow 443/tcp 2>/dev/null || true
fi

# Stop any running nginx/containers that might be using port 80
log_info "Stopping any services using ports 80/443..."
docker compose -f docker-compose.prod.yml down 2>/dev/null || true
sudo systemctl stop nginx 2>/dev/null || true

# Obtain certificates using standalone mode (since nginx isn't running yet)
log_info "Obtaining SSL certificates from Let's Encrypt..."
log_info "This will use standalone mode to verify domain ownership..."

# Request certificate for both domain and www subdomain
sudo certbot certonly --standalone \
    --non-interactive \
    --agree-tos \
    --email "$EMAIL" \
    -d "$DOMAIN" \
    -d "$WWW_DOMAIN" \
    --preferred-challenges http

if [ $? -eq 0 ]; then
    log_info "✓ Certificates obtained successfully!"
else
    log_error "Failed to obtain certificates. Please check:"
    log_error "1. DNS is pointing to this server"
    log_error "2. Ports 80 and 443 are open"
    log_error "3. No other service is using port 80"
    exit 1
fi

# Copy certificates to project SSL directory
log_info "Copying certificates to $SSL_DIR..."
CERT_PATH="/etc/letsencrypt/live/$DOMAIN"
sudo cp "$CERT_PATH/fullchain.pem" "$SSL_DIR/cert.pem"
sudo cp "$CERT_PATH/privkey.pem" "$SSL_DIR/key.pem"
sudo chown $USER:$USER "$SSL_DIR/cert.pem" "$SSL_DIR/key.pem"
sudo chmod 644 "$SSL_DIR/cert.pem"
sudo chmod 600 "$SSL_DIR/key.pem"

log_info "✓ Certificates copied to $SSL_DIR"

# Update nginx configuration with domain name
log_info "Updating nginx configuration..."
if [ -f "$NGINX_CONF" ]; then
    # Backup original config
    cp "$NGINX_CONF" "$NGINX_CONF.backup"
    
    # Update server_name in nginx config
    sed -i "s/server_name _;/server_name $DOMAIN $WWW_DOMAIN;/g" "$NGINX_CONF"
    
    log_info "✓ Nginx configuration updated"
else
    log_warn "Nginx config file not found at $NGINX_CONF"
fi

# Set up auto-renewal
log_info "Setting up certificate auto-renewal..."

# Create renewal hook script
RENEWAL_HOOK="/etc/letsencrypt/renewal-hooks/deploy/copy-certs.sh"
sudo mkdir -p /etc/letsencrypt/renewal-hooks/deploy

sudo tee "$RENEWAL_HOOK" > /dev/null <<EOF
#!/bin/bash
# Copy renewed certificates to project directory
cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem $SSL_DIR/cert.pem
cp /etc/letsencrypt/live/$DOMAIN/privkey.pem $SSL_DIR/key.pem
chown $USER:$USER $SSL_DIR/cert.pem $SSL_DIR/key.pem
chmod 644 $SSL_DIR/cert.pem
chmod 600 $SSL_DIR/key.pem

# Reload nginx in docker container if running
docker compose -f $(pwd)/docker-compose.prod.yml exec -T frontend nginx -s reload 2>/dev/null || true
EOF

sudo chmod +x "$RENEWAL_HOOK"

# Test renewal (dry run)
log_info "Testing certificate renewal..."
sudo certbot renew --dry-run

if [ $? -eq 0 ]; then
    log_info "✓ Auto-renewal is configured correctly"
else
    log_warn "Auto-renewal test failed, but certificates are installed"
fi

log_info ""
log_info "🎉 SSL setup completed successfully!"
log_info ""
log_info "Certificates are located at: $SSL_DIR"
log_info "Certificates will auto-renew via Certbot"
log_info ""
log_info "Next steps:"
log_info "1. Update your .env file with DOMAIN=$DOMAIN"
log_info "2. Start your services: docker compose -f docker-compose.prod.yml up -d"
log_info "3. Visit https://$DOMAIN to verify SSL is working"
log_info ""

