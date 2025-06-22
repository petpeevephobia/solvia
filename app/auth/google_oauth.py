"""
Google OAuth and Search Console API integration for Solvia.
"""
import os
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.database import GoogleSheetsDB
from app.auth.models import UserInDB
from app.config import settings
import gspread

class GoogleOAuthHandler:
    """Handles Google OAuth flow and Search Console API access."""
    
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        self.scopes = [
            'https://www.googleapis.com/auth/webmasters.readonly',
            # 'https://www.googleapis.com/auth/indexing' # Temporarily disabled for debugging
        ]
        self.db = GoogleSheetsDB()
        
        # Simple cache to reduce API calls
        self._credentials_cache = {}
        self._cache_timeout = 300  # 5 minutes
        
        # Debug: Check if credentials are loaded
        print(f"[DEBUG] Google OAuth Configuration:")
        print(f"[DEBUG] Client ID loaded: {'Yes' if self.client_id and self.client_id != 'your_google_client_id_here' else 'No'}")
        print(f"[DEBUG] Client Secret loaded: {'Yes' if self.client_secret and self.client_secret != 'your_google_client_secret_here' else 'No'}")
        print(f"[DEBUG] Redirect URI: {self.redirect_uri}")
        
        # Check if we're in demo mode (no Google credentials)
        self.demo_mode = not (self.client_id and self.client_secret and 
                             self.client_id != 'your_google_client_id_here' and 
                             self.client_secret != 'your_google_client_secret_here')
        if self.demo_mode:
            print("[WARNING] Google OAuth running in DEMO MODE - no real GSC connection available")
            print("[INFO] To enable real GSC connection, set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your .env file")
            print("[INFO] See GOOGLE_OAUTH_SETUP.md for setup instructions")
        else:
            print("[SUCCESS] Google OAuth credentials loaded successfully!")
    
    def get_auth_url(self, state: str = None) -> str:
        """Generate Google OAuth authorization URL."""
        if self.demo_mode:
            # Return a demo URL that will trigger the demo flow
            demo_url = f"{self.redirect_uri}?demo=true&state={state or 'demo'}"
            print(f"[DEBUG] Demo mode - returning demo URL: {demo_url}")
            return demo_url
        
        try:
            print(f"[DEBUG] Generating real OAuth URL for user (state): {state}")
            
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
                scopes=self.scopes
            )
            flow.redirect_uri = self.redirect_uri
            
            # The state is used for CSRF protection and to pass the user's email.
            auth_url, generated_state = flow.authorization_url(state=state)
            
            print(f"[DEBUG] State passed to authorization_url: '{state}'")
            print(f"[DEBUG] State in generated auth_url: '{generated_state}'")
            
            return auth_url
        except Exception as e:
            print(f"[ERROR] Error generating auth URL: {e}")
            # Fallback to demo mode
            fallback_url = f"{self.redirect_uri}?demo=true&state={state or 'demo'}"
            print(f"[DEBUG] Fallback to demo URL: {fallback_url}")
            return fallback_url
    
    async def handle_callback(self, code: str, user_email: str) -> Dict:
        """Handle OAuth callback and store credentials."""
        if self.demo_mode or code == 'demo':
            # Demo mode - simulate successful connection
            return {
                "success": True,
                "demo_mode": True,
                "message": "Demo mode - GSC connection simulated"
            }
        
        try:
            print(f"[DEBUG] handle_callback received state (user_email): {user_email}")

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
                scopes=self.scopes
            )
            flow.redirect_uri = self.redirect_uri
            
            # Exchange code for tokens
            print(f"[DEBUG] Exchanging authorization code for token for user: {user_email}")
            flow.fetch_token(code=code)
            credentials = flow.credentials
            print(f"[DEBUG] Token fetched successfully for user: {user_email}")
            
            # Store credentials in Google Sheets
            self._store_credentials(user_email, credentials)
            
            return {
                "success": True,
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "expires_at": credentials.expiry.isoformat() if credentials.expiry else None
            }
        except Exception as e:
            print(f"[ERROR] Error in handle_callback for user {user_email}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _store_credentials(self, user_email: str, credentials: Credentials):
        """Store OAuth credentials in Google Sheets."""
        try:
            print(f"[DEBUG] _store_credentials called for user: {user_email}")
            # Create gsc_connections sheet if it doesn't exist
            try:
                gsc_connections_sheet = self.db.client.open_by_key(self.db.users_sheet.spreadsheet.id).worksheet('gsc-connections')
            except:
                # Create the sheet if it doesn't exist
                gsc_connections_sheet = self.db.client.open_by_key(self.db.users_sheet.spreadsheet.id).add_worksheet(
                    title='gsc-connections', 
                    rows=1000, 
                    cols=6
                )
                # Add headers
                gsc_connections_sheet.append_row([
                    'user_email', 'access_token', 'refresh_token', 'expires_at', 'created_at', 'updated_at'
                ])
            
            # Check if user already has credentials
            try:
                cell = gsc_connections_sheet.find(user_email)
                # Update existing credentials
                print(f"[DEBUG] Found existing credentials for {user_email} at row {cell.row}. Updating token.")
                gsc_connections_sheet.update_cell(cell.row, 2, credentials.token)
                gsc_connections_sheet.update_cell(cell.row, 3, credentials.refresh_token or '')
                gsc_connections_sheet.update_cell(cell.row, 4, credentials.expiry.isoformat() if credentials.expiry else '')
                gsc_connections_sheet.update_cell(cell.row, 6, datetime.utcnow().isoformat())
            except:
                # Add new credentials
                print(f"[DEBUG] No existing credentials for {user_email}. Adding new row.")
                gsc_connections_sheet.append_row([
                    user_email,
                    credentials.token,
                    credentials.refresh_token or '',
                    credentials.expiry.isoformat() if credentials.expiry else '',
                    datetime.utcnow().isoformat(),
                    datetime.utcnow().isoformat()
                ])
            print(f"[SUCCESS] Stored credentials for {user_email}")
        except Exception as e:
            print(f"[ERROR] Error in _store_credentials: {e}")
    
    def get_credentials(self, user_email: str) -> Optional[Credentials]:
        """Get stored OAuth credentials for user."""
        # Check cache first
        cache_key = f"creds_{user_email}"
        if cache_key in self._credentials_cache:
            cached_data = self._credentials_cache[cache_key]
            if datetime.now() - cached_data['timestamp'] < timedelta(seconds=self._cache_timeout):
                print(f"[DEBUG] Returning cached credentials for {user_email}")
                return cached_data['credentials']
            else:
                # Cache expired, remove it
                print(f"[DEBUG] Cache expired for {user_email}")
                del self._credentials_cache[cache_key]
        
        try:
            print(f"[DEBUG] get_credentials called for user: {user_email}")
            # Get gsc-connections sheet
            gsc_connections_sheet = self.db.client.open_by_key(self.db.users_sheet.spreadsheet.id).worksheet('gsc-connections')
            
            # Find user's credentials
            print(f"[DEBUG] Searching for '{user_email}' in gsc-connections sheet...")
            cell = gsc_connections_sheet.find(user_email)
            
            if not cell:
                print(f"[DEBUG] User '{user_email}' not found in gsc-connections sheet.")
                return None
            
            print(f"[DEBUG] Found user '{user_email}' at row {cell.row}, column {cell.col}.")
            # Get credentials data
            credentials_data = gsc_connections_sheet.row_values(cell.row)
            
            # Debug credential data
            print(f"[DEBUG] Credentials data length: {len(credentials_data)}")
            print(f"[DEBUG] Access token present: {bool(credentials_data[1] if len(credentials_data) > 1 else None)}")
            print(f"[DEBUG] Refresh token present: {bool(credentials_data[2] if len(credentials_data) > 2 else None)}")
            
            # Check if we have the minimum required data
            if len(credentials_data) < 3 or not credentials_data[1]:
                print(f"[ERROR] Invalid credentials data for {user_email}: insufficient data")
                return None
            
            refresh_token = credentials_data[2] if len(credentials_data) > 2 and credentials_data[2] else None
            
            credentials = Credentials(
                token=credentials_data[1],
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=self.scopes
            )
            
            # Check if credentials are valid
            if not credentials.token:
                print(f"[ERROR] No access token found for {user_email}")
                return None
            
            # Refresh token if expired and we have a refresh token
            if credentials.expired:
                if credentials.refresh_token:
                    print(f"[DEBUG] Credentials for {user_email} expired. Refreshing token.")
                    try:
                        credentials.refresh(Request())
                        self._store_credentials(user_email, credentials)
                    except Exception as refresh_error:
                        print(f"[ERROR] Failed to refresh token for {user_email}: {refresh_error}")
                        # Return the expired credentials anyway - they might still work for some operations
                else:
                    print(f"[WARNING] Credentials for {user_email} expired but no refresh token available")
            
            # Cache the credentials
            print(f"[DEBUG] Caching new credentials for {user_email}")
            self._credentials_cache[cache_key] = {
                'credentials': credentials,
                'timestamp': datetime.now()
            }
            
            return credentials
        except Exception as e:
            print(f"[ERROR] Error in get_credentials: {e}")
            return None
    
    async def get_gsc_properties(self, user_email: str) -> List[Dict]:
        """Get user's Google Search Console properties."""
        print(f"[DEBUG] get_gsc_properties called for user: {user_email}")
        print(f"[DEBUG] Demo mode: {self.demo_mode}")
        
        if self.demo_mode:
            # Return demo properties
            demo_properties = [
                {
                    'siteUrl': 'https://example.com',
                    'permissionLevel': 'siteOwner',
                    'isVerified': True
                },
                {
                    'siteUrl': 'https://demo-site.com',
                    'permissionLevel': 'siteOwner',
                    'isVerified': True
                }
            ]
            print(f"[DEBUG] Returning demo properties: {demo_properties}")
            return demo_properties
        
        credentials = self.get_credentials(user_email)
        if not credentials:
            print(f"[DEBUG] No credentials found for user: {user_email}")
            # Clear any corrupted credentials
            self._clear_credentials(user_email)
            return []
        
        try:
            service = build('searchconsole', 'v1', credentials=credentials)
            sites = service.sites().list().execute()
            
            properties = []
            for site in sites.get('siteEntry', []):
                properties.append({
                    'siteUrl': site['siteUrl'],
                    'permissionLevel': site['permissionLevel'],
                    'isVerified': True
                })
            
            print(f"[DEBUG] Retrieved real properties: {properties}")
            return properties
        except HttpError as e:
            print(f"Error fetching GSC properties: {e}")
            # If it's an authentication error, clear the credentials
            if "401" in str(e) or "403" in str(e):
                print(f"[DEBUG] Authentication error, clearing credentials for {user_email}")
                self._clear_credentials(user_email)
            return []
        except Exception as e:
            print(f"Unexpected error fetching GSC properties: {e}")
            # Clear credentials on any unexpected error
            self._clear_credentials(user_email)
            return []

    def _clear_credentials(self, user_email: str):
        """Clear corrupted credentials for a user."""
        try:
            print(f"[DEBUG] Clearing credentials for user: {user_email}")
            gsc_connections_sheet = self.db.client.open_by_key(self.db.users_sheet.spreadsheet.id).worksheet('gsc-connections')
            
            # Find and delete the user's credentials
            cell = gsc_connections_sheet.find(user_email)
            if cell:
                gsc_connections_sheet.delete_rows(cell.row)
                print(f"[DEBUG] Deleted credentials for {user_email}")
            
            # Clear from cache
            cache_key = f"creds_{user_email}"
            if cache_key in self._credentials_cache:
                del self._credentials_cache[cache_key]
                print(f"[DEBUG] Cleared credentials from cache for {user_email}")
        except Exception as e:
            print(f"[ERROR] Error clearing credentials for {user_email}: {e}")

class GSCDataFetcher:
    """Fetches SEO data from Google Search Console."""
    
    def __init__(self, oauth_handler: GoogleOAuthHandler):
        self.oauth_handler = oauth_handler
        self.db = GoogleSheetsDB()
    
    async def fetch_metrics(self, user_email: str, property_url: str, days: int = 30) -> Dict:
        """Fetch SEO metrics for a property."""
        credentials = self.oauth_handler.get_credentials(user_email)
        if not credentials:
            return {}
        
        try:
            service = build('searchconsole', 'v1', credentials=credentials)
            
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)

            # 1. Fetch time-series data
            time_series_request = {
                'startDate': start_date.isoformat(),
                'endDate': end_date.isoformat(),
                'dimensions': ['date'],
                'rowLimit': 5000
            }
            time_series_response = service.searchanalytics().query(
                siteUrl=property_url,
                body=time_series_request
            ).execute()

            # 2. Fetch summary data (no dimensions)
            summary_request = {
                'startDate': start_date.isoformat(),
                'endDate': end_date.isoformat()
            }
            summary_response = service.searchanalytics().query(
                siteUrl=property_url,
                body=summary_request
            ).execute()
            
            # Process both responses
            metrics = self._process_analytics_data(time_series_response, summary_response)
            
            # Store the data
            self._store_metrics(user_email, property_url, metrics)
            
            return metrics
        except HttpError as e:
            print(f"Error fetching GSC metrics: {e}")
            return {}
    
    def _process_analytics_data(self, time_series_response: Dict, summary_response: Dict) -> Dict:
        """Process Google Search Console analytics response."""
        # Process summary data from the dimensionless query
        summary_rows = summary_response.get('rows', [])
        summary = {
            'total_clicks': 0,
            'total_impressions': 0,
            'avg_ctr': 0,
            'avg_position': 0
        }
        if summary_rows:
            summary_data = summary_rows[0]
            summary['total_clicks'] = summary_data.get('clicks', 0)
            summary['total_impressions'] = summary_data.get('impressions', 0)
            summary['avg_ctr'] = round(summary_data.get('ctr', 0) * 100, 2)
            summary['avg_position'] = round(summary_data.get('position', 0), 1)

        # Process time series data
        time_series_rows = time_series_response.get('rows', [])
        dates = []
        clicks_data = []
        impressions_data = []
        
        for row in time_series_rows:
            dates.append(row['keys'][0])
            clicks_data.append(row['clicks'])
            impressions_data.append(row['impressions'])
        
        time_series = {
            'dates': dates,
            'clicks': clicks_data,
            'impressions': impressions_data
        }
        
        start_date = dates[0] if dates else None
        end_date = dates[-1] if dates else None

        return {
            'summary': summary,
            'time_series': time_series,
            'last_updated': datetime.now().isoformat(),
            'start_date': start_date,
            'end_date': end_date
        }
    
    def _store_metrics(self, user_email: str, property_url: str, metrics: Dict):
        """Store SEO metrics in Google Sheets."""
        try:
            # Create seo_data sheet if it doesn't exist
            try:
                seo_data_sheet = self.db.client.open_by_key(self.db.users_sheet.spreadsheet.id).worksheet('seo-data')
            except:
                # Create the sheet if it doesn't exist
                seo_data_sheet = self.db.client.open_by_key(self.db.users_sheet.spreadsheet.id).add_worksheet(
                    title='seo-data', 
                    rows=10000, 
                    cols=5
                )
                # Add headers
                seo_data_sheet.append_row([
                    'user_email', 'website_url', 'metrics_data', 'last_updated', 'created_at'
                ])
            
            # Check if user already has data for this website
            try:
                # Find existing record
                cell = seo_data_sheet.find(user_email)
                if cell:
                    # Update existing data
                    seo_data_sheet.update_cell(cell.row, 3, json.dumps(metrics))
                    seo_data_sheet.update_cell(cell.row, 4, datetime.utcnow().isoformat())
                else:
                    # Add new data
                    seo_data_sheet.append_row([
                        user_email,
                        property_url,
                        json.dumps(metrics),
                        datetime.utcnow().isoformat(),
                        datetime.utcnow().isoformat()
                    ])
            except:
                # Add new data
                seo_data_sheet.append_row([
                    user_email,
                    property_url,
                    json.dumps(metrics),
                    datetime.utcnow().isoformat(),
                    datetime.utcnow().isoformat()
                ])
        except Exception as e:
            print(f"Error storing metrics: {e}")
    
    async def get_stored_metrics(self, user_email: str, website_url: str) -> Optional[Dict]:
        """Get stored SEO metrics for a user's website."""
        try:
            # Get seo_data sheet
            seo_data_sheet = self.db.client.open_by_key(self.db.users_sheet.spreadsheet.id).worksheet('seo-data')
            
            # Find user's data
            cell = seo_data_sheet.find(user_email)
            if not cell:
                return None
            
            # Get data
            data = seo_data_sheet.row_values(cell.row)
            
            if len(data) >= 4:
                return {
                    'metrics': json.loads(data[2]),
                    'last_updated': data[3]
                }
            return None
        except Exception as e:
            print(f"Error getting stored metrics: {e}")
            return None 