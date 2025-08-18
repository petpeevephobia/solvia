@echo off
echo ========================================
echo Solvia SEO Audit Tool - Auto Setup
echo ========================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11+ from https://python.org
    pause
    exit /b 1
)

echo Python found. Setting up virtual environment...

REM Remove existing venv if it exists
if exist venv (
    echo Removing existing virtual environment...
    rmdir /s /q venv
)

REM Create new virtual environment
echo Creating new virtual environment...
python -m venv venv

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install core packages
echo Installing core dependencies...
pip install fastapi uvicorn python-dotenv

echo Installing database dependencies...  
pip install supabase

echo Installing Google OAuth dependencies...
pip install google-auth google-auth-oauthlib google-api-python-client

echo Installing authentication dependencies...
pip install python-jose[cryptography] passlib[bcrypt] python-multipart email-validator

echo Installing AI and utility dependencies...
pip install openai markdown aiohttp

echo Installing additional dependencies...
pip install gspread fastapi-mail

REM Verify installation
echo.
echo Verifying installation...
python -c "import fastapi; print('✅ FastAPI installed')" 2>nul || echo "❌ FastAPI failed"
python -c "import uvicorn; print('✅ Uvicorn installed')" 2>nul || echo "❌ Uvicorn failed" 
python -c "import supabase; print('✅ Supabase installed')" 2>nul || echo "❌ Supabase failed"
python -c "from google.oauth2 import credentials; print('✅ Google Auth installed')" 2>nul || echo "❌ Google Auth failed"

echo.
echo ========================================
echo Setup complete! Starting Solvia...
echo ========================================
echo.
echo The application will be available at:
echo http://localhost:8000
echo.
echo Press Ctrl+C to stop the server
echo.

REM Run the application
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause
