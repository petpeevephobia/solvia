"""
Google OAuth routes for Solvia.
"""
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from app.auth.models import (
    UserResponse, TokenResponse, GoogleAuthRequest, GoogleCallbackRequest
)
from app.ai.agent_instructions import get_agent_instructions

import openai

# Chat models
class ChatMessage(BaseModel):
    message_content: str
    message_type: str = "user"  # "user" or "ai"
    sender_name: Optional[str] = None

class ChatResponse(BaseModel):
    message_id: int
    message_content: str
    message_type: str
    sender_name: Optional[str] = None
    created_at: datetime

class ChatHistoryResponse(BaseModel):
    messages: List[ChatResponse]
    success: bool
from app.auth.utils import create_access_token, verify_token
from app.database.supabase_db import SupabaseAuthDB
from app.config import settings
from app.auth.google_oauth import GoogleOAuthHandler
import uuid
import time
import markdown

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

# Initialize database and Google OAuth handler
db = SupabaseAuthDB()
google_oauth = GoogleOAuthHandler(db)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current user from JWT token."""
    token = credentials.credentials
    email = verify_token(token)
    
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return email


@router.post("/logout")
async def logout(current_user: str = Depends(get_current_user)):
    """Logout user and deactivate session."""
    try:
        # Deactivate user session in database
        await db.deactivate_session(current_user)
        
        return {
            "message": "Successfully logged out",
            "success": True
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to logout"
        )


@router.get("/me")
async def get_current_user_info(current_user: str = Depends(get_current_user)):
    """Get current user information from session."""
    try:
        # Get user session from database using email from JWT
        user_session = await db.get_user_session(current_user)
        
        if user_session:
            # Update last login timestamp
            await db.update_last_login(current_user)
        
            return {
                "email": user_session.get("email"),
                "name": user_session.get("name"),
                "picture": user_session.get("picture"),
                "last_login": user_session.get("last_login")
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User session not found"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )


# Google OAuth routes
@router.get("/google/authorize")
async def google_authorize(request: Request):
    """Generate Google OAuth authorization URL."""
    try:
        # Generate OAuth URL without requiring authentication first
        auth_url = google_oauth.get_auth_url(state="user_email")
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate authorization URL"
        )


@router.get("/google/callback")
async def google_callback(
    code: str = Query(...),
    state: str = Query(...),
    request: Request = None
):
    """Handle Google OAuth callback."""
    try:
        # Get OAuth handler
        oauth_handler = GoogleOAuthHandler()
        
        # Handle OAuth callback
        oauth_result = await oauth_handler.handle_callback(code)
        
        if oauth_result["success"]:
            # Get user info from OAuth result
            user_info = oauth_result["user_info"]
            user_email = user_info.get('email')
            
            if not user_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No email address received from Google"
                )
            
            # Store user session in database with tokens
            await db.store_user_session(
                user_email, 
                user_info, 
                oauth_result.get("access_token"),
                oauth_result.get("refresh_token")
            )
            
            # Create JWT token
            access_token_expires = timedelta(minutes=30)
            access_token = create_access_token(
                data={"sub": user_email},
                expires_delta=access_token_expires
            )
            
            # Redirect to dashboard with token
            redirect_url = f"/dashboard?access_token={access_token}"
            return RedirectResponse(url=redirect_url, status_code=302)
        else:
            error_msg = oauth_result.get('error', 'Unknown OAuth error')

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to complete OAuth process: {error_msg}"
            )
            
    except Exception as e:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete OAuth process"
        )


@router.get("/google/callback/test")
async def google_callback_test():
    """Test endpoint to verify callback route is accessible."""
    return {"message": "Google callback route is working!"}


# Chat endpoints
@router.post("/chat/send")
async def send_message(
    message: ChatMessage,
    current_user: str = Depends(get_current_user)
):
    """Send a chat message and get AI response."""
    try:
        # Debug logging

        
        # Store user message
        user_message_id = await db.store_chat_message(
            current_user, 
            message.message_content, 
            "user", 
            message.sender_name
        )
        
        # Generate AI response using Solvia with conversation context
        ai_response = await generate_ai_response(message.message_content, current_user)
        
        # Split response into paragraphs
        paragraphs = []
        
        # First try to split by double line breaks (most common)
        if '\n\n' in ai_response:
            paragraphs = [p.strip() for p in ai_response.split('\n\n') if p.strip()]
        else:
            # If no double line breaks, try to split by single line breaks
            lines = ai_response.split('\n')
            current_paragraph = ""
            
            for line in lines:
                line = line.strip()
                if line:  # Non-empty line
                    if current_paragraph:
                        current_paragraph += " " + line
                    else:
                        current_paragraph = line
                else:  # Empty line - end of paragraph
                    if current_paragraph:
                        paragraphs.append(current_paragraph)
                        current_paragraph = ""
            
            # Add the last paragraph if there is one
            if current_paragraph:
                paragraphs.append(current_paragraph)
        
        # If only one paragraph, send as single message
        if len(paragraphs) <= 1:
            ai_message_id = await db.store_chat_message(
                current_user, 
                ai_response, 
                "ai", 
                "Solvia"
            )
            
            return {
                "user_message_id": user_message_id,
                "ai_message_id": ai_message_id,
                "ai_response": ai_response,
                "ai_responses": [ai_response],
                "success": True
            }
        else:
            # Store multiple AI messages
            ai_message_ids = []
            ai_responses = []
            
            for paragraph in paragraphs:
                ai_message_id = await db.store_chat_message(
                    current_user, 
                    paragraph, 
                    "ai", 
                    "Solvia"
                )
                ai_message_ids.append(ai_message_id)
                ai_responses.append(paragraph)
            
            return {
                "user_message_id": user_message_id,
                "ai_message_ids": ai_message_ids,
                "ai_response": ai_response,  # Keep for backward compatibility
                "ai_responses": ai_responses,
                "success": True
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )


@router.get("/chat/history")
async def get_chat_history(
    current_user: str = Depends(get_current_user),
    limit: int = 50
):
    """Get chat history for the current user."""
    try:
        messages = await db.get_chat_messages(current_user, limit)
        
        chat_responses = []
        for msg in messages:
            chat_responses.append(ChatResponse(
                message_id=msg["id"],
                message_content=msg["message_content"],
                message_type=msg["message_type"],
                sender_name=msg["sender_name"],
                created_at=msg["created_at"]
            ))
        
        return ChatHistoryResponse(
            messages=chat_responses,
            success=True
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chat history: {str(e)}"
        )


async def generate_ai_response(user_message: str, user_email: str) -> str:
    """Generate Solvia's response using OpenAI GPT-4o-mini with conversation context and GSC data."""
    
    # Get Solvia's custom instructions
    agent_instructions = get_agent_instructions("solvia")
    
    try:
        # Get recent conversation history (last 10 messages)
        recent_messages = await db.get_chat_messages(user_email, 10)
        
        # Always include GSC metrics context for Solvia
        # Detect date range in user message
        date_range = detect_date_range(user_message)
        
        # Get GSC metrics for every response
        gsc_context = ""
        try:
            # Get user's selected website
            selected_website = await db.get_user_website(user_email)
            if selected_website:
                # Get OAuth handler
                oauth_handler = GoogleOAuthHandler()
                
                # Get GSC metrics with custom date range if specified
                gsc_metrics = await oauth_handler.get_gsc_metrics(user_email, selected_website, date_range)
                
                if gsc_metrics:
                    # Calculate clicks from impressions and CTR
                    clicks = int(gsc_metrics.get('organic_traffic', 0) * (gsc_metrics.get('ctr', 0) / 100))
                    
                    # Format date range description
                    date_description = get_date_range_description(date_range)
                    
                    # Add note about default range if not custom
                    range_note = ""
                    if not date_range.get('is_custom_range', False):
                        range_note = "\nNote: I'm showing you the last 30 days of data by default. You can ask for specific time periods like 'last week', 'this month', or 'last 3 months'."
                    
                    gsc_context = f"""
IMPORTANT: You MUST use ONLY the following real Google Search Console data. Do NOT make up or hallucinate any metrics.

Current Google Search Console Data ({date_description}):
- Impressions: {gsc_metrics.get('organic_traffic', 0):,}
- Clicks: {clicks:,}
- CTR: {gsc_metrics.get('ctr', 0):.2f}%
- Average Position: {gsc_metrics.get('avg_position', 0):.1f}
- SEO Score: {gsc_metrics.get('seo_score', 0):.1f}/100
- Website: {selected_website}{range_note}

CRITICAL INSTRUCTIONS:
1. ALWAYS reference these exact numbers when discussing SEO metrics
2. NEVER invent or estimate different values
3. If asked about CTR, say exactly {gsc_metrics.get('ctr', 0):.2f}%
4. If asked about SEO score, say exactly {gsc_metrics.get('seo_score', 0):.1f}/100
5. If asked about impressions, say exactly {gsc_metrics.get('organic_traffic', 0):,}
6. If asked about average position, say exactly {gsc_metrics.get('avg_position', 0):.1f}
"""
        except Exception as e:
            print(f"Error getting GSC data for context: {e}")
            gsc_context = ""
        
        # Build conversation context
        messages = [{"role": "system", "content": agent_instructions + gsc_context}]
        
        # Add recent conversation history
        for msg in recent_messages:
            if msg["message_type"] == "user":
                messages.append({"role": "user", "content": msg["message_content"]})
            elif msg["message_type"] == "ai":
                messages.append({"role": "assistant", "content": msg["message_content"]})
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Set OpenAI API key
        openai.api_key = settings.OPENAI_API_KEY
        
        # Create chat completion with OpenAI
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        
        # Process markdown in the response
        ai_response_text = response.choices[0].message.content
        processed_response = markdown.markdown(ai_response_text, extensions=['extra'])
        
        return processed_response
            
    except Exception as e:
        print(f"Error in generate_ai_response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OpenAI API error: {str(e)}"
        )

def detect_date_range(user_message: str) -> dict:
    """Detect date range from user message and return start/end dates."""
    import re
    from datetime import datetime, timedelta
    
    message_lower = user_message.lower()
    
    # Default to last 30 days
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    is_custom_range = False
    
    # Detect specific time periods
    if any(word in message_lower for word in ['last week', 'past week', 'this week']):
        start_date = end_date - timedelta(days=7)
        is_custom_range = True
    elif any(word in message_lower for word in ['last month', 'past month', 'this month']):
        start_date = end_date - timedelta(days=30)
        is_custom_range = True
    elif any(word in message_lower for word in ['last 3 months', 'past 3 months', '3 months']):
        start_date = end_date - timedelta(days=90)
        is_custom_range = True
    elif any(word in message_lower for word in ['last 6 months', 'past 6 months', '6 months']):
        start_date = end_date - timedelta(days=180)
        is_custom_range = True
    elif any(word in message_lower for word in ['last year', 'past year', 'this year']):
        start_date = end_date - timedelta(days=365)
        is_custom_range = True
    elif any(word in message_lower for word in ['yesterday', 'yesterday\'s']):
        start_date = end_date - timedelta(days=1)
        end_date = end_date - timedelta(days=1)
        is_custom_range = True
    elif any(word in message_lower for word in ['today', 'today\'s']):
        start_date = end_date
        is_custom_range = True
    elif any(word in message_lower for word in ['last 7 days', 'past 7 days']):
        start_date = end_date - timedelta(days=7)
        is_custom_range = True
    elif any(word in message_lower for word in ['last 14 days', 'past 14 days']):
        start_date = end_date - timedelta(days=14)
        is_custom_range = True
    elif any(word in message_lower for word in ['last 60 days', 'past 60 days']):
        start_date = end_date - timedelta(days=60)
        is_custom_range = True
    elif any(word in message_lower for word in ['last 90 days', 'past 90 days']):
        start_date = end_date - timedelta(days=90)
        is_custom_range = True
    
    return {
        'start_date': start_date,
        'end_date': end_date,
        'is_custom_range': is_custom_range
    }

def get_date_range_description(date_range: dict) -> str:
    """Get a human-readable description of the date range."""
    start_date = date_range['start_date']
    end_date = date_range['end_date']
    
    if start_date == end_date:
        return f"on {start_date.strftime('%B %d, %Y')}"
    else:
        days_diff = (end_date - start_date).days
        if days_diff == 1:
            return f"on {start_date.strftime('%B %d, %Y')}"
        elif days_diff == 7:
            return "in the last 7 days"
        elif days_diff == 14:
            return "in the last 14 days"
        elif days_diff == 30:
            return "in the last 30 days"
        elif days_diff == 60:
            return "in the last 60 days"
        elif days_diff == 90:
            return "in the last 90 days"
        elif days_diff == 180:
            return "in the last 6 months"
        elif days_diff == 365:
            return "in the last year"
        else:
            return f"from {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}"

# GSC Property models
class GSCProperty(BaseModel):
    siteUrl: str
    permissionLevel: str

class PropertySelectionRequest(BaseModel):
    siteUrl: str
    permissionLevel: str

@router.get("/gsc/properties")
async def get_gsc_properties(current_user: str = Depends(get_current_user)):
    """Get user's Google Search Console properties."""
    try:
        # Get user session to get their OAuth credentials
        user_session = await db.get_user_session(current_user)
        
        if not user_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User session not found"
            )
        
        # Get OAuth handler
        oauth_handler = GoogleOAuthHandler()
        
        # Get user's GSC properties
        properties = await oauth_handler.get_gsc_properties(current_user)
        
        return {
            "success": True,
            "properties": properties
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get GSC properties"
        )

@router.post("/gsc/select-property")
async def select_gsc_property(
    request: PropertySelectionRequest,
    current_user: str = Depends(get_current_user)
):
    """Select a Google Search Console property for the user."""
    try:
        # Store the selected property in the database
        await db.store_user_website(current_user, request.siteUrl)
        
        return {
            "success": True,
            "message": "Property selected successfully"
        }
    except Exception as e:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to select property"
        )

@router.get("/gsc/selected-website")
async def get_selected_website(current_user: str = Depends(get_current_user)):
    """Get the user's selected website."""
    try:
        user_session = await db.get_user_session(current_user)
        
        if user_session and user_session.get('selected_website'):
            return {
                "success": True,
                "selected_website": user_session.get('selected_website')
            }
        else:
            return {
                "success": False,
                "selected_website": None
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get selected website"
        )

@router.get("/gsc/metrics")
async def get_gsc_metrics(current_user: str = Depends(get_current_user)):
    """Get GSC metrics for the user's selected website with caching."""
    try:
        # Get user session to get their OAuth credentials
        user_session = await db.get_user_session(current_user)
        
        if not user_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User session not found"
            )
        
        selected_website = user_session.get('selected_website')
        if not selected_website:
            return {
                "success": False,
                "message": "No website selected",
                "metrics": {
                    "seo_score": 0,
                    "organic_traffic": 0,
                    "avg_position": 0,
                    "ctr": 0
                }
            }
        
        # Default to last 30 days
        from datetime import datetime, timedelta
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        date_range = {
            'start_date': start_date,
            'end_date': end_date
        }
        
        # Check cache first
        cached_metrics = await db.get_gsc_metrics_cache(current_user, selected_website, date_range)
        
        if cached_metrics:
            print(f"Using cached GSC metrics for {current_user}")
            return {
                "success": True,
                "metrics": cached_metrics
            }
        
        # If no cache, fetch from GSC API
        print(f"Fetching fresh GSC metrics for {current_user}")
        oauth_handler = GoogleOAuthHandler()
        metrics = await oauth_handler.get_gsc_metrics(current_user, selected_website, date_range)
        
        # Cache the results
        if metrics:
            await db.store_gsc_metrics_cache(current_user, selected_website, metrics, date_range)
        
        return {
            "success": True,
            "metrics": metrics
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get GSC metrics"
        )







 