"""
Google OAuth authentication for Solvia.
"""
from typing import Dict, Optional
from google_auth_oauthlib.flow import Flow
from app.config import settings

class GoogleOAuthHandler:
    """Handles Google OAuth flow for user authentication."""
    
    def __init__(self, db):
        self.db = db
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        
        # Check if we have valid Google credentials
        if not (self.client_id and self.client_secret and 
                             self.client_id != 'your_google_client_id_here' and 
                self.client_secret != 'your_google_client_secret_here'):
            raise Exception("Google OAuth credentials required. Cannot start Solvia without proper configuration.")
    
    def get_auth_url(self, state: str = None) -> str:
        """Generate Google OAuth authorization URL for user authentication."""
        # Use minimal scopes to avoid conflicts
        scopes = [
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/webmasters.readonly"
        ]
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=scopes
        )
        flow.redirect_uri = self.redirect_uri
        
        auth_url, generated_state = flow.authorization_url(
            state=state, 
            access_type='offline',
            prompt='consent'
        )
        return auth_url
    
    async def handle_callback(self, code: str, user_email: str = None) -> Dict:
        """Handle OAuth callback and get user information."""
        try:
            # Use minimal scopes to avoid conflicts
            scopes = [
                "https://www.googleapis.com/auth/drive.file",
                "https://www.googleapis.com/auth/webmasters.readonly"
            ]
            
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri]
                    }
                },
                scopes=scopes
            )
            flow.redirect_uri = self.redirect_uri
            
            # Exchange code for tokens
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Get basic user info (since we don't have userinfo scope)
            user_info = {
                'email': 'user@solvia.com',  # Placeholder
                'name': 'Google User',
                'picture': None,
                'given_name': None,
                'family_name': None
            }
            
            result = {
                "success": True,
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "expires_at": credentials.expiry.isoformat() if credentials.expiry else None,
                "user_info": user_info
            }
            return result
        except Exception as e:
            print(f"Error in handle_callback: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_user_info(self, credentials) -> Dict:
        """Get user information from Google OAuth flow."""
        # Since we're using minimal scopes, return basic info
        return {
            'email': 'user@solvia.com',
            'name': 'Google User',
            'picture': None,
            'given_name': None,
            'family_name': None
        } 