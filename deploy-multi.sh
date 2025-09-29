#!/bin/bash

# Solvia Multi-Repository Deployment Script
# Deploys both landing page and dashboard from separate repos

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SERVER_USER="root"
SERVER_HOST="72.60.195.244"
BASE_DIR="/root/solvia"
DASHBOARD_REPO="https://github.com/petpeevephobia/solvia.git"
LANDING_REPO="https://github.com/solviasg/solvia-site.git"

echo -e "${GREEN}🚀 Solvia Multi-Repo Deployment${NC}"
echo "=================================="

# Function to check command success
check_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $1${NC}"
    else
        echo -e "${RED}✗ $1 failed${NC}"
        exit 1
    fi
}

# Deploy to server
echo -e "${YELLOW}📦 Connecting to server...${NC}"

ssh $SERVER_USER@$SERVER_HOST << 'ENDSSH'
set -e

echo "📁 Creating directory structure..."
mkdir -p /root/solvia
cd /root/solvia

# Clone or update dashboard repository
echo "🔄 Updating dashboard repository..."
if [ -d "solvia-dashboard" ]; then
    cd solvia-dashboard
    git pull origin 5-solvia-agent
else
    git clone -b 5-solvia-agent https://github.com/petpeevephobia/solvia.git solvia-dashboard
    cd solvia-dashboard
fi

# Clone or update landing page repository
echo "🔄 Updating landing page repository..."
cd /root/solvia
if [ -d "solvia-site" ]; then
    cd solvia-site
    git pull origin main
else
    git clone https://github.com/solviasg/solvia-site.git solvia-site
fi

# Go back to dashboard directory for Docker operations
cd /root/solvia/solvia-dashboard

# Copy production configs if they don't exist
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Please create it from .env.example"
    exit 1
fi

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.multi.yml down || true

# Build and start new containers
echo "🏗️  Building Docker images..."
docker-compose -f docker-compose.multi.yml build

echo "🚀 Starting services..."
docker-compose -f docker-compose.multi.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service status
docker-compose -f docker-compose.multi.yml ps

echo "✅ Deployment complete!"
echo ""
echo "Services running:"
echo "  - Landing Page: https://solvia.sg/"
echo "  - Dashboard: https://solvia.sg/spa"
echo "  - API Docs: https://solvia.sg/docs"
echo ""
echo "Check logs with: docker-compose -f docker-compose.multi.yml logs -f"

ENDSSH

check_status "Deployment completed"

echo -e "${GREEN}✨ Deployment successful!${NC}"
echo ""
echo "Access your sites at:"
echo "  • Landing: https://solvia.sg"
echo "  • Dashboard: https://solvia.sg/spa"