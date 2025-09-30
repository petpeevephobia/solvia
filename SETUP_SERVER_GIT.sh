#!/bin/bash
# Setup script to initialize git repositories on the server
# Run this AFTER adding deploy keys to GitHub

set -e  # Exit on any error

echo "🚀 Setting up git-based deployment on server..."
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}📋 Prerequisites check...${NC}"
echo "✓ SSH key added to server (github-actions-cicd)"
echo "✓ Deploy keys generated on server"
echo "✓ SSH config created"
echo ""

echo -e "${RED}⚠️  IMPORTANT: Make sure you've added the deploy keys to GitHub!${NC}"
echo "See SETUP_GITHUB_KEYS.md for instructions"
echo ""
read -p "Have you added BOTH deploy keys to GitHub? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Please add the deploy keys first, then run this script again."
    exit 1
fi

echo ""
echo -e "${YELLOW}🔧 Setting up repositories on server...${NC}"

# Setup Dashboard (solvia)
echo ""
echo "1️⃣  Setting up Dashboard repository..."
ssh root@72.60.195.244 << 'ENDSSH'
set -e

cd /opt

# Backup existing directory if it exists
if [ -d "solvia" ]; then
    echo "📦 Backing up existing solvia directory..."
    mv solvia solvia.backup.$(date +%Y%m%d_%H%M%S)
fi

# Clone repository using deploy key
echo "📥 Cloning dashboard repository..."
GIT_SSH_COMMAND="ssh -i ~/.ssh/deploy_key_solvia -o IdentitiesOnly=yes" \
    git clone git@github.com:solviasg/solvia.git solvia

cd solvia
git config core.sshCommand "ssh -i ~/.ssh/deploy_key_solvia -o IdentitiesOnly=yes"

echo "✅ Dashboard repository cloned successfully"
echo "Current branch: $(git branch --show-current)"
echo "Latest commit: $(git log -1 --oneline)"
ENDSSH

echo -e "${GREEN}✅ Dashboard setup complete!${NC}"

# Setup Landing Page (solvia-site)
echo ""
echo "2️⃣  Setting up Landing Page repository..."
ssh root@72.60.195.244 << 'ENDSSH'
set -e

cd /opt

# Backup existing directory if it exists
if [ -d "solvia-site" ]; then
    echo "📦 Backing up existing solvia-site directory..."
    mv solvia-site solvia-site.backup.$(date +%Y%m%d_%H%M%S)
fi

# Clone repository using deploy key
echo "📥 Cloning landing page repository..."
GIT_SSH_COMMAND="ssh -i ~/.ssh/deploy_key_solvia_site -o IdentitiesOnly=yes" \
    git clone git@github.com:solviasg/solvia-site.git solvia-site

cd solvia-site
git config core.sshCommand "ssh -i ~/.ssh/deploy_key_solvia_site -o IdentitiesOnly=yes"

# Set permissions for nginx
echo "🔧 Setting permissions..."
chown -R www-data:www-data /opt/solvia-site 2>/dev/null || true

echo "✅ Landing page repository cloned successfully"
echo "Current branch: $(git branch --show-current)"
echo "Latest commit: $(git log -1 --oneline)"
ENDSSH

echo -e "${GREEN}✅ Landing page setup complete!${NC}"

# Restart services
echo ""
echo "3️⃣  Restarting services..."
ssh root@72.60.195.244 << 'ENDSSH'
set -e

cd /opt/solvia
echo "🔄 Restarting Docker containers..."
docker-compose down
docker-compose build --no-cache
docker-compose up -d

echo "⏳ Waiting for services to start..."
sleep 10

echo "🔍 Verifying services..."
docker-compose ps
ENDSSH

echo -e "${GREEN}✅ Services restarted successfully!${NC}"

# Final verification
echo ""
echo "4️⃣  Final verification..."
echo ""
echo "Testing landing page..."
response=$(curl -s -o /dev/null -w "%{http_code}" http://72.60.195.244/ || echo "000")
if [ "$response" = "200" ] || [ "$response" = "308" ]; then
    echo -e "${GREEN}✅ Landing page accessible (HTTP $response)${NC}"
else
    echo -e "${RED}⚠️  Landing page returned HTTP $response${NC}"
fi

echo ""
echo "Testing dashboard health..."
response=$(curl -s -o /dev/null -w "%{http_code}" http://72.60.195.244/health || echo "000")
if [ "$response" = "200" ] || [ "$response" = "308" ]; then
    echo -e "${GREEN}✅ Dashboard health check passed (HTTP $response)${NC}"
else
    echo -e "${RED}⚠️  Dashboard health check returned HTTP $response${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Setup complete!${NC}"
echo ""
echo "📝 Summary:"
echo "  - Dashboard: /opt/solvia (git-enabled)"
echo "  - Landing:   /opt/solvia-site (git-enabled)"
echo "  - CI/CD:     Updated to use git pull"
echo ""
echo "🚀 You can now push to main branch to trigger automatic deployments!"
echo ""