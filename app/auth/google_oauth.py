"""
Google OAuth authentication for Solvia.
"""
from typing import Dict, Optional, List
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
            
            response = requests.post(token_url, data=token_data)
            
            if response.status_code == 200:
                token_info = response.json()
                
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
            
                result = {
                    "success": True,
                    "access_token": credentials.token,
                    "refresh_token": credentials.refresh_token,
                    "expires_at": credentials.expiry.isoformat() if credentials.expiry else None,
                    "user_info": user_info
                }
                return result
            else:
                return {
                    "success": False,
                    "error": f"Token exchange failed: {response.text}"
                }
                
        except Exception as e:
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
            # Fallback to basic info
            return {
                'email': 'user@solvia.com',
                'name': 'Google User',
                'picture': None,
                'given_name': None,
                'family_name': None
            } 

    async def get_gsc_properties(self, user_email: str) -> List[Dict]:
        """Get user's Google Search Console properties."""
        try:
            # Get user session to get their OAuth credentials
            from app.database.supabase_db import SupabaseAuthDB
            db = SupabaseAuthDB()
            user_session = await db.get_user_session(user_email)
            
            if not user_session:
                raise Exception("User session not found")
            

            
            # Check if we have the required tokens
            access_token = user_session.get('access_token')
            refresh_token = user_session.get('refresh_token')
            
            if not access_token:
                raise Exception("No access token found in user session")
            
            # Create credentials from stored session data
            from google.oauth2.credentials import Credentials
            credentials = Credentials(
                token=access_token,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=[
                    "https://www.googleapis.com/auth/userinfo.email",
                    "https://www.googleapis.com/auth/userinfo.profile",
                    "https://www.googleapis.com/auth/webmasters.readonly"
                ]
            )
            
            # Refresh token if needed
            if credentials.expired:
                if refresh_token:
                    import requests
                    credentials.refresh(requests.Request())
                    # Update the session with new tokens
                    await db.update_user_session_tokens(
                        user_email, 
                        credentials.token, 
                        credentials.refresh_token
                    )
                else:
                    # For now, return empty list - user would need to re-authenticate
                    return []
            
            # Build the Search Console service
            from googleapiclient.discovery import build
            service = build('searchconsole', 'v1', credentials=credentials)
            
            # Get the list of sites
            sites = service.sites().list().execute()
            
            properties = []
            if 'siteEntry' in sites:
                for site in sites['siteEntry']:
                    properties.append({
                        "siteUrl": site.get('siteUrl', ''),
                        "permissionLevel": site.get('permissionLevel', 'siteUnverifiedUser')
                    })
            
            return properties
            
        except Exception as e:
            return []

    async def get_gsc_metrics(self, user_email: str, site_url: str, date_range: Dict = None) -> Dict:
        """Get GSC metrics for a specific website."""
        try:
            print(f"Getting GSC metrics for {user_email} on {site_url}")
            
            # Get user session to get their OAuth credentials
            from app.database.supabase_db import SupabaseAuthDB
            db = SupabaseAuthDB()
            user_session = await db.get_user_session(user_email)
            
            if not user_session:
                raise Exception("User session not found")
            
            # Check if we have the required tokens
            access_token = user_session.get('access_token')
            refresh_token = user_session.get('refresh_token')
            
            print(f"Access token present: {bool(access_token)}")
            print(f"Refresh token present: {bool(refresh_token)}")
            
            if not access_token:
                raise Exception("No access token found in user session")
            
            # Create credentials from stored session data
            from google.oauth2.credentials import Credentials
            credentials = Credentials(
                token=access_token,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=[
                    "https://www.googleapis.com/auth/userinfo.email",
                    "https://www.googleapis.com/auth/userinfo.profile",
                    "https://www.googleapis.com/auth/webmasters.readonly"
                ]
            )
            
            # Refresh token if needed
            if credentials.expired:
                if refresh_token:
                    import requests
                    credentials.refresh(requests.Request())
                    # Update the session with new tokens
                    await db.update_user_session_tokens(
                        user_email, 
                        credentials.token, 
                        credentials.refresh_token
                    )
                else:
                    return {
                        "seo_score": 0,
                        "organic_traffic": 0,
                        "avg_position": 0
                    }
            
            # Build the Search Console service using the correct API
            from googleapiclient.discovery import build
            service = build('searchconsole', 'v1', credentials=credentials, cache_discovery=False)
            
            # Calculate date range (use provided date range or default to last 30 days)
            from datetime import datetime, timedelta
            if date_range:
                start_date = date_range['start_date']
                end_date = date_range['end_date']
            else:
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=30)
            
            # Get search analytics data using the correct API method
            request = {
                'startDate': start_date.isoformat(),
                'endDate': end_date.isoformat(),
                'dimensions': ['query'],
                'rowLimit': 1000
            }
            
            print(f"GSC API request: {request}")
            print(f"Available service methods: {[method for method in dir(service) if not method.startswith('_')]}")
            
            # Use the correct Search Console API method
            # The API method is 'searchanalytics' (lowercase)
            try:
                # Use the correct method name (lowercase)
                response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            except AttributeError as e:
                print(f"searchanalytics method not found: {e}")
                # Return default values if API fails
                return {
                    'seo_score': 0,
                    'organic_traffic': 0,
                    'avg_position': 0,
                    'ctr': 0
                }
            
            print(f"GSC API response: {response}")
            
            # Calculate metrics
            total_clicks = 0
            total_impressions = 0
            total_position = 0
            query_count = 0
            
            if 'rows' in response:
                print(f"Found {len(response['rows'])} rows in response")
                for row in response['rows']:
                    clicks = row.get('clicks', 0)
                    impressions = row.get('impressions', 0)
                    position = row.get('position', 0)
                    
                    total_clicks += clicks
                    total_impressions += impressions
                    total_position += position * impressions  # Weighted average
                    query_count += 1
            else:
                print("No rows found in GSC response")
            
            print(f"Calculated metrics - Clicks: {total_clicks}, Impressions: {total_impressions}, Position: {total_position}")
            
            # Calculate average position (weighted by impressions)
            avg_position = total_position / total_impressions if total_impressions > 0 else 0
            
            # Calculate SEO score (simplified - based on traffic and position)
            seo_score = min(100, max(0, (total_clicks * 10) + (50 - avg_position) * 2))
            
            # Calculate CTR (Click-Through Rate)
            ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
            
            final_metrics = {
                "seo_score": round(seo_score, 1),
                "organic_traffic": total_impressions,  # This will show as "Impressions" in UI
                "avg_position": round(avg_position, 1),
                "ctr": round(ctr, 2)  # New CTR metric
            }
            
            print(f"Final metrics: {final_metrics}")
            
            return final_metrics
            
        except Exception as e:
            print(f"Error getting GSC metrics: {str(e)}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            return {
                "seo_score": 0,
                "organic_traffic": 0,
                "avg_position": 0
            } 