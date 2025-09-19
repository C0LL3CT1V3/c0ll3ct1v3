#!/bin/bash

# C0ll3CT1V3 Backup Script
set -e

# Configuration
BACKUP_DIR="/opt/backups"
PROJECT_DIR="/opt/c0ll3ct1v3"
RETENTION_DAYS=30

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Create backup directory
mkdir -p $BACKUP_DIR

# Generate timestamp
timestamp=$(date +%Y%m%d_%H%M%S)

log_info "Starting backup process..."

# Database backup
log_info "Backing up database..."
docker-compose -f $PROJECT_DIR/docker-compose.prod.yml exec -T postgres pg_dump -U postgres c0ll3ct1v3 > $BACKUP_DIR/db_backup_$timestamp.sql

# Application files backup
log_info "Backing up application files..."
tar -czf $BACKUP_DIR/app_backup_$timestamp.tar.gz -C $PROJECT_DIR .

# Docker volumes backup
log_info "Backing up Docker volumes..."
docker run --rm -v c0ll3ct1v3_postgres_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/postgres_data_$timestamp.tar.gz -C /data .

# Cleanup old backups
log_info "Cleaning up old backups..."
find $BACKUP_DIR -name "*.sql" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

log_info "✅ Backup completed successfully!"
log_info "Backup files:"
ls -la $BACKUP_DIR/*$timestamp*
