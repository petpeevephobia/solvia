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
        print(f"Error getting current user: {e}")
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
        print(f"Google OAuth callback - Code: {code[:20]}..., State: {state}")
        
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
            
            print(f"Google OAuth - User email: {user_email}")
            
            # Store user session in database
            await db.store_user_session(user_email, user_info)
            
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
            print(f"OAuth failed: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to complete OAuth process: {error_msg}"
            )
            
    except Exception as e:
        print(f"OAuth callback error: {e}")
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
        print(f"Processing message for user: {current_user}")
        print(f"Message content: {message.message_content}")
        
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
        # Handle different paragraph separators: double line breaks, single line breaks with proper spacing, etc.
        paragraphs = []
        
        # First try to split by double line breaks (most common)
        if '\n\n' in ai_response:
            paragraphs = [p.strip() for p in ai_response.split('\n\n') if p.strip()]
            print(f"Split by double line breaks: {len(paragraphs)} paragraphs")
        else:
            # If no double line breaks, try to split by single line breaks that create natural paragraphs
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
            
            print(f"Split by single line breaks: {len(paragraphs)} paragraphs")
        
        # If still only one paragraph, try to split by sentence patterns that indicate new topics
        if len(paragraphs) <= 1 and len(ai_response) > 200:  # Only for longer responses
            # Look for patterns that indicate new sections
            import re
            # Split by sentences that start with common transition words or are standalone
            sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', ai_response)
            
            # Group sentences into logical paragraphs
            current_group = []
            paragraphs = []
            
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence:
                    current_group.append(sentence)
                    
                    # Start a new paragraph if this sentence seems like a new topic
                    # (starts with common transition words or is a standalone statement)
                    transition_words = ['for example', 'however', 'additionally', 'furthermore', 'moreover', 'in addition', 'also', 'besides', 'meanwhile', 'conversely', 'on the other hand', 'if you', 'when you', 'let me know', 'i can help']
                    
                    if any(sentence.lower().startswith(word) for word in transition_words) and len(current_group) > 1:
                        paragraphs.append(' '.join(current_group[:-1]))
                        current_group = [current_group[-1]]
            
            # Add the last group
            if current_group:
                paragraphs.append(' '.join(current_group))
            
            print(f"Split by sentence patterns: {len(paragraphs)} paragraphs")
        
        # Debug logging
        print(f"Original response length: {len(ai_response)}")
        print(f"Number of paragraphs detected: {len(paragraphs)}")
        for i, p in enumerate(paragraphs):
            print(f"Paragraph {i+1}: {p[:50]}...")
        
        # Fallback: If we still have only one paragraph but the response is long and contains multiple sentences,
        # force split it into logical chunks
        if len(paragraphs) <= 1 and len(ai_response) > 150:
            import re
            # Count sentences
            sentences = re.split(r'(?<=[.!?])\s+', ai_response)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            if len(sentences) >= 3:  # If we have 3+ sentences, split them
                # Group sentences into chunks of 2-3 sentences each
                chunks = []
                current_chunk = []
                
                for sentence in sentences:
                    current_chunk.append(sentence)
                    
                    # Start a new chunk after 2-3 sentences
                    if len(current_chunk) >= 2 and len(chunks) < 2:  # Max 3 chunks
                        chunks.append(' '.join(current_chunk))
                        current_chunk = []
                
                # Add remaining sentences to the last chunk
                if current_chunk:
                    if chunks:
                        chunks[-1] += ' ' + ' '.join(current_chunk)
                    else:
                        chunks.append(' '.join(current_chunk))
                
                if len(chunks) > 1:
                    paragraphs = chunks
                    print(f"Force split into {len(paragraphs)} chunks")
        
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
    """Generate Solvia's response using OpenAI GPT-4o-mini with conversation context."""
    
    # Get Solvia's custom instructions
    agent_instructions = get_agent_instructions("solvia")
    
    try:
        # Get recent conversation history (last 10 messages)
        recent_messages = await db.get_chat_messages(user_email, 10)
        
        # Debug logging
        print(f"User email: {user_email}")
        print(f"Number of recent messages found: {len(recent_messages)}")
        
        # Build conversation context
        messages = [{"role": "system", "content": agent_instructions}]
        
        # Add recent conversation history
        for msg in recent_messages:
            if msg["message_type"] == "user":
                messages.append({"role": "user", "content": msg["message_content"]})
            elif msg["message_type"] == "ai":
                messages.append({"role": "assistant", "content": msg["message_content"]})
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Debug logging
        print(f"Total messages being sent to AI: {len(messages)}")
        print(f"Conversation context:")
        for i, msg in enumerate(messages):
            print(f"  {i}: {msg['role']} - {msg['content'][:100]}...")
        
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
        print(f"OpenAI API Error: {str(e)}")
        print(f"API Key: {settings.OPENAI_API_KEY[:10]}..." if settings.OPENAI_API_KEY else "No API key")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OpenAI API error: {str(e)}"
        )







 