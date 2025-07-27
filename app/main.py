"""
Main FastAPI application for Solvia Google OAuth authentication.
"""
import os
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

# Add project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles 
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from .auth.routes import router as auth_router, get_current_user
from .config import settings

from dotenv import load_dotenv
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Solvia Google OAuth Authentication API",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create static directory if it doesn't exist
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

# Mount static files
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include auth routes
app.include_router(auth_router)

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Solvia Google OAuth Authentication API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "ui": "/ui"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "solvia-auth"
    }

@app.get("/ui")
def serve_ui():
    file_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="UI file not found")
    return FileResponse(file_path)

@app.get("/dashboard")
def serve_dashboard():
    file_path = os.path.join(os.path.dirname(__file__), "static", "dashboard.html")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Dashboard file not found")
    return FileResponse(file_path)

@app.get("/login")
def serve_login():
    file_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Login file not found")
    return FileResponse(file_path)

@app.get("/settings")
async def serve_settings():
    """Serve the settings page."""
    return FileResponse(
        os.path.join(os.path.dirname(__file__), "static", "settings.html"),
        media_type="text/html"
    )

@app.get("/api/health")
async def api_health():
    """API health check."""
    return {
        "status": "healthy",
        "service": "solvia-auth-api",
        "version": settings.APP_VERSION
    }

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    ) 