"""
Main FastAPI application for Solvia authentication system.
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import os

from .auth.routes import router as auth_router
from .config import settings

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Solvia Authentication API - SEO on AI Autopilot",
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
        "message": "Welcome to Solvia Authentication API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "ui": "/ui",
        "dashboard": "/dashboard"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "solvia-auth"
    }

@app.get("/ui")
async def serve_ui():
    """Serve the authentication UI."""
    ui_file = os.path.join(static_dir, "index.html")
    if os.path.exists(ui_file):
        return FileResponse(ui_file)
    else:
        return {
            "error": "UI not found",
            "message": "Please ensure the UI files are in the static directory"
        }

@app.get("/dashboard")
async def serve_dashboard():
    """Serve the dashboard UI."""
    dashboard_file = os.path.join(static_dir, "dashboard.html")
    if os.path.exists(dashboard_file):
        return FileResponse(dashboard_file)
    else:
        return {
            "error": "Dashboard not found",
            "message": "Please ensure the dashboard files are in the static directory"
        }

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