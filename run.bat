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

REM Install requirements (with fallback for Rust issues)
echo Installing dependencies...
pip install fastapi uvicorn supabase python-dotenv google-auth google-auth-oauthlib google-api-python-client openai markdown

REM Check if installation was successful
if errorlevel 1 (
    echo WARNING: Some dependencies may not have installed properly
    echo You may need to install Rust for full functionality
    echo Visit: https://rustup.rs/
)

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
