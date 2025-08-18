#!/bin/bash
echo "========================================"
echo "Solvia SEO Audit Tool - Auto Setup"
echo "========================================"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.11+ from https://python.org"
    exit 1
fi

echo "Python found. Setting up virtual environment..."

# Remove existing venv if it exists
if [ -d "venv" ]; then
    echo "Removing existing virtual environment..."
    rm -rf venv
fi

# Create new virtual environment
echo "Creating new virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install dependencies (avoiding Rust compilation issues)
echo "Installing core dependencies..."
pip install fastapi uvicorn python-dotenv

echo "Installing database dependencies..."
pip install supabase

echo "Installing Google OAuth dependencies..."
pip install google-auth google-auth-oauthlib google-api-python-client

echo "Installing authentication dependencies..."
pip install python-jose[cryptography] passlib[bcrypt] python-multipart email-validator

echo "Installing AI and utility dependencies..."
pip install openai markdown aiohttp

echo "Installing additional dependencies..."
pip install gspread fastapi-mail

# Verify critical packages
echo ""
echo "Verifying installation..."
python -c "import fastapi; print('✅ FastAPI installed')" 2>/dev/null || echo "❌ FastAPI failed"
python -c "import uvicorn; print('✅ Uvicorn installed')" 2>/dev/null || echo "❌ Uvicorn failed"
python -c "import supabase; print('✅ Supabase installed')" 2>/dev/null || echo "❌ Supabase failed"
python -c "from google.oauth2 import credentials; print('✅ Google Auth installed')" 2>/dev/null || echo "❌ Google Auth failed"

echo ""
echo "========================================"
echo "Setup complete! Starting Solvia..."
echo "========================================"
echo ""
echo "The application will be available at:"
echo "http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run the application
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000