#!/bin/bash
# Solvia API Startup Script
# This script ensures the correct binary is running

cd "$(dirname "$0")"

# Kill any existing processes on port 8080
echo "Stopping any existing API processes..."
pkill -f solvia-api 2>/dev/null
lsof -ti :8080 | xargs kill -9 2>/dev/null
sleep 1

# Build the latest version
echo "Building latest API..."
go build -o solvia-api ./cmd/api/

if [ $? -ne 0 ]; then
    echo "Build failed!"
    exit 1
fi

# Start the API
echo "Starting Solvia API..."
./solvia-api
