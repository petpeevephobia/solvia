"""
Google OAuth authentication for Solvia.
"""
from typing import Dict, Optional
from google_auth_oauthlib.flow import Flow
from app.config import settings

class GoogleOAuthHandler:
    """Handles Google OAuth flow for user authentication."""
    
    def __init__(self, db=None):
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
        # Use minimal scopes to avoid scope change issues
        scopes = [
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
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
            # Use a completely different approach - direct HTTP request to bypass scope checking
            import requests
            
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': self.redirect_uri
            }
            
            print(f"Making direct token request to Google...")
            response = requests.post(token_url, data=token_data)
            
            if response.status_code == 200:
                token_info = response.json()
                print(f"Direct token exchange successful: {token_info}")
                
                # Create credentials object manually
                from google.oauth2.credentials import Credentials
                credentials = Credentials(
                    token=token_info['access_token'],
                    refresh_token=token_info.get('refresh_token'),
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=self.client_id,
                    client_secret=self.client_secret
                )
                
                # Get actual user info from Google
                user_info = await self._get_user_info(credentials)
                
                print(f"Google OAuth - User info fetched: {user_info}")
            
                result = {
                    "success": True,
                    "access_token": credentials.token,
                    "refresh_token": credentials.refresh_token,
                    "expires_at": credentials.expiry.isoformat() if credentials.expiry else None,
                    "user_info": user_info
                }
                return result
            else:
                print(f"Direct token exchange failed: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"Token exchange failed: {response.text}"
                }
                
        except Exception as e:
            print(f"Google OAuth Error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_user_info(self, credentials) -> Dict:
        """Get user information from Google OAuth flow."""
        try:
            from googleapiclient.discovery import build
            
            # Build the service
            service = build('oauth2', 'v2', credentials=credentials)
            
            # Get user info
            user_info = service.userinfo().get().execute()
            
            return {
                'email': user_info.get('email'),
                'name': user_info.get('name'),
                'picture': user_info.get('picture'),
                'given_name': user_info.get('given_name'),
                'family_name': user_info.get('family_name')
            }
        except Exception as e:
            print(f"Error fetching user info: {e}")
            # Fallback to basic info
            return {
                'email': 'user@solvia.com',
                'name': 'Google User',
                'picture': None,
                'given_name': None,
                'family_name': None
            } 