"""
Main FastAPI application for Solvia authentication system.
"""
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Load environment variables FIRST, before any other imports
from dotenv import load_dotenv
load_dotenv()

# Debug: Check if environment variables are loaded
print(f"[DEBUG] SUPABASE_URL: {os.getenv('SUPABASE_URL', 'NOT_FOUND')}")
print(f"[DEBUG] SUPABASE_KEY: {os.getenv('SUPABASE_KEY', 'NOT_FOUND')[:10]}..." if os.getenv('SUPABASE_KEY') else 'NOT_FOUND')

# Add project root to the Python path
# This is the directory that contains `app` and `core`
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.staticfiles import StaticFiles 
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from .auth.routes import router as auth_router, get_current_user
from .config import settings
from .database import db

# Import the analysis components
# from core.modules.business_analysis import BusinessAnalyzer

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

# Include enhanced data pipeline routes
from app.auth.enhanced_routes import enhanced_router
app.include_router(enhanced_router)

# Include audit engine routes (Milestone 2)
from app.audit.routes import audit_router
app.include_router(audit_router)

# Include agent routes for Solvia Agent feature
from app.agent import agent_router
app.include_router(agent_router, tags=["Solvia Agent"])

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
def serve_ui():
    return FileResponse("app/static/index.html")

@app.get("/dashboard")
async def serve_dashboard():
    """Serve the dashboard UI."""
    dashboard_file = os.path.join(static_dir, "dashboard.html")
    if os.path.exists(dashboard_file):
        return FileResponse(
            dashboard_file,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    else:
        return {
            "error": "Dashboard not found",
            "message": "Please ensure the dashboard files are in the static directory"
        }

@app.get("/domain-selection")
async def serve_domain_selection():
    """Serve the domain selection UI."""
    domain_selection_file = os.path.join(static_dir, "domain-selection.html")
    if os.path.exists(domain_selection_file):
        return FileResponse(domain_selection_file)
    else:
        return {
            "error": "Domain selection page not found",
            "message": "Please ensure the domain selection files are in the static directory"
        }



@app.get("/setup")
async def serve_setup_wizard():
    """Serve the setup wizard UI."""
    setup_file = os.path.join(static_dir, "setup_wizard.html")
    if os.path.exists(setup_file):
        return FileResponse(setup_file)
    else:
        return {
            "error": "Setup wizard not found",
            "message": "Please ensure the setup wizard files are in the static directory"
        }

@app.get("/property-selection")
async def serve_property_selection(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    request: Request = None
):
    """Serve the property selection UI and handle OAuth callbacks."""
    
    # If this is an OAuth callback (has code parameter), handle it
    if code and state:
        
        if error:
            return FileResponse(os.path.join(static_dir, "property_selection.html"))
        
        try:
            # Import the Google OAuth handler
            from app.auth.google_oauth import GoogleOAuthHandler
            from app.database.supabase_db import SupabaseAuthDB
            
            # Initialize OAuth handler
            db = SupabaseAuthDB()
            google_oauth = GoogleOAuthHandler(db)
            
            # The state parameter contains the user's email
            user_email = state
            
            if not user_email:
                return FileResponse(os.path.join(static_dir, "property_selection.html"))
            
            # Handle the OAuth callback without JWT token (we'll store credentials using email)
            result = await google_oauth.handle_callback(code, jwt_token=None)
            
            # Serve the property selection page
            property_file = os.path.join(static_dir, "property_selection.html")
            if os.path.exists(property_file):
                return FileResponse(property_file)
            else:
                return {
                    "error": "Property selection page not found",
                    "message": "Please ensure the property selection files are in the static directory"
                }
                
        except Exception as e:
            # Still serve the page even if OAuth fails
            property_file = os.path.join(static_dir, "property_selection.html")
            if os.path.exists(property_file):
                return FileResponse(property_file)
            else:
                return {
                    "error": "Property selection page not found",
                    "message": "Please ensure the property selection files are in the static directory"
                }
    
    # Regular property selection page request (no OAuth callback)
    property_file = os.path.join(static_dir, "property_selection.html")
    if os.path.exists(property_file):
        return FileResponse(property_file)
    else:
        return {
            "error": "Property selection page not found",
            "message": "Please ensure the property selection files are in the static directory"
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

@app.get("/login")
def serve_login():
    return FileResponse("app/static/index.html")

@app.get("/test-auth")
async def serve_auth_test():
    """Serve auth token debug page."""
    return FileResponse("/Users/jarotekosaputra/Documents/SOLVIA/App/solvia/test_auth_token.html", headers={
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    })

@app.get("/test-chat")
async def serve_chat_test():
    """Simple chat alignment test page."""
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chat Alignment Test - Solvia</title>
    <style>
        body { font-family: Inter, sans-serif; background: #F9FAFB; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; background: white; border-radius: 12px; padding: 20px; }
        .test-header { background: #FEF3E7; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .sidebar-test { width: 80px; height: 200px; background: white; border: 1px solid #E5E7EB; padding: 16px; margin-bottom: 20px; display: flex; flex-direction: column; gap: 10px; }
        .nav-icon { width: 32px; height: 32px; background: #F3F4F6; border-radius: 8px; display: flex; align-items: center; justify-content: center; padding: 12px; }
        .chat-container { border: 1px solid #E5E7EB; border-radius: 12px; padding: 20px; height: 300px; overflow-y: auto; margin-bottom: 20px; }
        .chat-message { display: flex; gap: 12px; margin-bottom: 16px; align-items: flex-start; }
        .chat-message.user { flex-direction: row-reverse; }
        .message-avatar { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 14px; flex-shrink: 0; }
        .message-avatar.ai { background: #EC6019; color: white; }
        .message-avatar.user { background: #6B7280; color: white; }
        .message-content { flex: 1; max-width: 70%; }
        .chat-message.user .message-content { display: flex; justify-content: flex-end; }
        .message-text { padding: 12px 16px; border-radius: 18px; font-size: 14px; color: #1F2937; line-height: 1.5; word-wrap: break-word; }
        .message-content.ai .message-text { background: #FEF3E7; border-bottom-left-radius: 6px; }
        .message-content.user .message-text { background: #E5E7EB; border-bottom-right-radius: 6px; }
        button { padding: 10px 20px; margin: 5px; border: 1px solid #EC6019; border-radius: 8px; background: white; color: #EC6019; cursor: pointer; }
        button:hover { background: #EC6019; color: white; }
        .success { background: #d4edda; color: #155724; padding: 10px; border-radius: 4px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="test-header">
            <h1>🧪 Solvia Chat & Sidebar Test</h1>
            <p><strong>Expected Results:</strong></p>
            <ul>
                <li>✅ AI messages on LEFT with orange avatar</li>
                <li>✅ User messages on RIGHT with gray avatar</li>
                <li>✅ Sidebar icons centered in collapsed state</li>
            </ul>
        </div>
        
        <h3>Sidebar Test (Collapsed - 80px width):</h3>
        <div class="sidebar-test">
            <div class="nav-icon">🏠</div>
            <div class="nav-icon">👥</div>
            <div class="nav-icon">⚙️</div>
            <div class="nav-icon">👤</div>
        </div>
        
        <h3>Chat Alignment Test:</h3>
        <div class="chat-container" id="chatContainer">
            <div class="chat-message ai">
                <div class="message-avatar ai">🤖</div>
                <div class="message-content ai">
                    <div class="message-text">Hi! I'm Solvia, your SEO assistant. This message should appear on the LEFT.</div>
                </div>
            </div>
            <div class="chat-message user">
                <div class="message-avatar user">👤</div>
                <div class="message-content user">
                    <div class="message-text">Hello! I need help with SEO. This message should appear on the RIGHT.</div>
                </div>
            </div>
        </div>
        
        <button onclick="addAI()">Add AI Message (LEFT)</button>
        <button onclick="addUser()">Add User Message (RIGHT)</button>
        <button onclick="clear()">Clear</button>
        
        <div id="result"></div>
    </div>
    
    <script>
        function addAI() {
            addMsg('ai', 'AI message: I can help you improve your SEO rankings!');
        }
        function addUser() {
            addMsg('user', 'User message: Can you run an audit for my website?');
        }
        function addMsg(type, text) {
            const c = document.getElementById('chatContainer');
            const d = document.createElement('div');
            d.className = `chat-message ${type}`;
            d.innerHTML = `
                <div class="message-avatar ${type}">${type === 'user' ? '👤' : '🤖'}</div>
                <div class="message-content ${type}">
                    <div class="message-text">${text}</div>
                </div>
            `;
            c.appendChild(d);
            c.scrollTop = c.scrollHeight;
            document.getElementById('result').innerHTML = '<div class="success">✅ Message added! Check alignment above.</div>';
        }
        function clear() {
            document.getElementById('chatContainer').innerHTML = '';
            document.getElementById('result').innerHTML = '';
        }
    </script>
</body>
</html>'''
    return HTMLResponse(content=html_content, headers={
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    ) 