#!/bin/bash

# Local development script for running both services
# Landing page and Dashboard from separate repos

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Starting Solvia Multi-Service Development${NC}"
echo "============================================"

# Check if solvia-site exists
if [ ! -d "../solvia-site" ]; then
    echo -e "${RED}Error: solvia-site repository not found!${NC}"
    echo "Please clone it first:"
    echo "  cd .. && git clone https://github.com/solviasg/solvia-site.git"
    exit 1
fi

# Option 1: Docker Compose (Recommended)
use_docker() {
    echo -e "${YELLOW}🐳 Starting with Docker Compose...${NC}"

    # Stop any existing containers
    docker-compose -f docker-compose.multi.yml down 2>/dev/null || true

    # Build and start
    docker-compose -f docker-compose.multi.yml up --build
}

# Option 2: Native Python + Simple HTTP Server
use_native() {
    echo -e "${YELLOW}🐍 Starting with native Python...${NC}"

    # Start landing page server in background
    echo "Starting landing page server..."
    cd ../solvia-site
    python3 -m http.server 3000 &
    LANDING_PID=$!
    cd ../solvia

    # Start dashboard server
    echo "Starting dashboard server..."
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi

    # Trap to kill both servers on exit
    trap "kill $LANDING_PID 2>/dev/null; exit" INT TERM EXIT

    # Run the main app
    python solvia.py
}

# Check command line argument
if [ "$1" == "docker" ]; then
    use_docker
elif [ "$1" == "native" ]; then
    use_native
else
    echo "Usage: ./run-multi.sh [docker|native]"
    echo ""
    echo "  docker - Run with Docker Compose (recommended)"
    echo "  native - Run with Python directly"
    echo ""
    echo "Services will be available at:"
    echo "  • Landing Page: http://localhost (docker) or http://localhost:3000 (native)"
    echo "  • Dashboard: http://localhost/spa (docker) or http://localhost:8000/spa (native)"
    exit 1
fi