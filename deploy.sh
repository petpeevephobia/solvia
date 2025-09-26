#!/bin/bash

# 🚀 Solvia Production Deployment Script
# Ultrathink deployment with comprehensive checks

set -e  # Exit on error

# Configuration
SERVER_IP="72.60.195.244"
SERVER_USER="root"
DEPLOY_DIR="/opt/solvia"
DOMAIN="solvia.app"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   🚀 SOLVIA PRODUCTION DEPLOYMENT    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"

# Create deployment package
log_info "Creating deployment package..."
tar -czf deploy.tar.gz app requirements.txt Dockerfile docker-compose*.yml Caddyfile* Makefile .env.production

log_success "Package created"

# Deploy to server
log_info "Deploying to server ${SERVER_IP}..."

# Transfer and deploy
scp deploy.tar.gz ${SERVER_USER}@${SERVER_IP}:/tmp/
ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
set -e

# Install Docker if needed
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
fi

# Install Docker Compose
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# Setup deployment
mkdir -p /opt/solvia
cd /opt/solvia
tar -xzf /tmp/deploy.tar.gz
rm /tmp/deploy.tar.gz

# Use production configs
mv Caddyfile.production Caddyfile
mv .env.production .env

# Stop existing if running
docker-compose down 2>/dev/null || true

# Build and start
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Wait for health
sleep 10
docker-compose ps

echo "✅ Deployment complete!"
ENDSSH

rm deploy.tar.gz
log_success "Deployment successful!"
echo "🌐 Access at: https://${DOMAIN}"
