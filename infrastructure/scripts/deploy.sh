#!/bin/bash

# C0ll3CT1V3 Production Deployment Script
set -e

echo "🚀 Starting C0ll3CT1V3 deployment..."

# Configuration
PROJECT_NAME="c0ll3ct1v3"
BACKUP_DIR="/opt/backups"
DEPLOY_DIR="/opt/c0ll3ct1v3"
ENV_FILE="/opt/c0ll3ct1v3/.env"

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

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   log_error "This script should not be run as root"
   exit 1
fi

# Create backup
log_info "Creating backup..."
mkdir -p $BACKUP_DIR
timestamp=$(date +%Y%m%d_%H%M%S)
tar -czf "$BACKUP_DIR/c0ll3ct1v3_backup_$timestamp.tar.gz" -C /opt c0ll3ct1v3 2>/dev/null || true

# Pull latest code
log_info "Pulling latest code..."
cd $DEPLOY_DIR
git fetch origin
git reset --hard origin/main

# Build frontend
log_info "Building frontend..."
cd frontend
npm ci
npm run build
cd ..

# Stop services
log_info "Stopping services..."
docker-compose -f docker-compose.prod.yml down

# Pull latest images
log_info "Pulling latest Docker images..."
docker-compose -f docker-compose.prod.yml pull

# Start services
log_info "Starting services..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
log_info "Waiting for services to be healthy..."
sleep 30

# Run health checks
log_info "Running health checks..."
if curl -f http://localhost/health > /dev/null 2>&1; then
    log_info "✅ Health check passed!"
else
    log_error "❌ Health check failed!"
    exit 1
fi

# Clean up old images
log_info "Cleaning up old Docker images..."
docker image prune -f

log_info "🎉 Deployment completed successfully!"
log_info "Application is available at: http://localhost"
log_info "Monitoring: http://localhost:3001 (Grafana)"
