"""
Google OAuth and Search Console API integration for Solvia.
"""
import os
import json
import math
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
import aiohttp
import asyncio

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
                    'siteUrl': '',
                    'permissionLevel': 'siteOwner',
                    'isVerified': True
                },
                {
                    'siteUrl': '',
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
    """Handles fetching and storing GSC data."""
    
    def __init__(self, oauth_handler: GoogleOAuthHandler):
        self.oauth_handler = oauth_handler
        self.db = GoogleSheetsDB()
    
    async def fetch_metrics(self, user_email: str, property_url: str, days: int = 30) -> Dict:
        """Fetch SEO metrics from GSC for current period and 30 days ago, calculate the difference."""
        try:
            credentials = self.oauth_handler.get_credentials(user_email)
            if not credentials or not credentials.valid:
                raise Exception("Invalid or missing Google credentials")

            # Define date ranges for 30-day comparison
            today = datetime.utcnow().date()
            current_end_date = today - timedelta(days=2)  # Data is usually delayed
            
            # Calculate start of current month for current period
            current_month_start = current_end_date.replace(day=1)
            current_start_date = current_month_start

            # Calculate 30 days ago period (single day for comparison)
            comparison_date = current_end_date - timedelta(days=30)
            
            # Fetch data for current period (full month)
            print(f"[DEBUG] Fetching data for current period: {current_start_date} to {current_end_date}")
            current_metrics = await self.get_gsc_data(
                credentials, property_url, 
                current_start_date.strftime('%Y-%m-%d'), 
                current_end_date.strftime('%Y-%m-%d')
            )

            # Fetch data for 30 days ago (single day)
            print(f"[DEBUG] Fetching data for 30 days ago: {comparison_date}")
            comparison_metrics = await self.get_gsc_data(
                credentials, property_url, 
                comparison_date.strftime('%Y-%m-%d'), 
                comparison_date.strftime('%Y-%m-%d')
            )
            
            # Calculate deltas between current totals and 30-day-ago totals
            summary = current_metrics.get('summary', {})
            comparison_summary = comparison_metrics.get('summary', {})
            
            # Add 30-day comparison changes to summary
            summary['impressions_change'] = summary.get('total_impressions', 0) - comparison_summary.get('total_impressions', 0)
            summary['clicks_change'] = summary.get('total_clicks', 0) - comparison_summary.get('total_clicks', 0)
            summary['ctr_change'] = summary.get('avg_ctr', 0) - comparison_summary.get('avg_ctr', 0)
            summary['position_change'] = summary.get('avg_position', 0) - comparison_summary.get('avg_position', 0)

            print(f"[DEBUG] Calculated Deltas: CTR Change={summary['ctr_change']}, Position Change={summary['position_change']}")
            
            # Calculate SEO score change (we'll need to get additional data for full calculation)
            # For now, we'll calculate a simplified score based on available GSC data
            current_seo_score = self._calculate_simplified_seo_score(summary)
            previous_seo_score = self._calculate_simplified_seo_score(comparison_summary)
            summary['seo_score_change'] = current_seo_score - previous_seo_score
            
            print(f"[DEBUG] SEO Score Change: Current={current_seo_score}, Previous={previous_seo_score}, Change={summary['seo_score_change']}")
            
            # Combine metrics
            final_metrics = {
                'summary': summary,
                'time_series': current_metrics.get('time_series', {}),
                'start_date': current_start_date.strftime('%Y-%m-%d'),
                'end_date': current_end_date.strftime('%Y-%m-%d'),
                'website_url': property_url,
            }
            
            # Store the combined metrics
            self._store_metrics(user_email, property_url, final_metrics)
            
            return final_metrics
            
        except Exception as e:
            print(f"[ERROR] Error in fetch_metrics: {e}")
            return {}
    
    def _calculate_simplified_seo_score(self, summary: Dict) -> float:
        """Calculate a simplified SEO score based on GSC data only."""
        try:
            # Get values with defaults
            avg_ctr = summary.get('avg_ctr', 0)
            avg_position = summary.get('avg_position', 0)
            total_impressions = summary.get('total_impressions', 0)
            total_clicks = summary.get('total_clicks', 0)
            
            # Define metrics with weights (simplified version focusing on GSC data)
            metrics = [
                # CTR - normalize to 0-1 (good CTR is around 10%)
                {'value': avg_ctr, 'weight': 30, 'norm': lambda v: min(v / 0.10, 1)},
                # Position - normalize to 0-1 (position 1 is best, 10+ is poor)
                {'value': avg_position, 'weight': 30, 'norm': lambda v: max((10 - v) / 10, 0) if v > 0 else 0},
                # Impressions - logarithmic scale
                {'value': total_impressions, 'weight': 20, 'norm': lambda v: min(math.log10(v + 1) / 6, 1)},
                # Clicks - logarithmic scale
                {'value': total_clicks, 'weight': 20, 'norm': lambda v: min(math.log10(v + 1) / 5, 1)},
            ]
            
            # Calculate weighted score
            total_weight = sum(m['weight'] for m in metrics)
            if total_weight == 0:
                return 0
                
            score = 0
            for metric in metrics:
                if metric['value'] is not None and not math.isnan(metric['value']):
                    normalized_value = max(0, min(metric['norm'](metric['value']), 1))
                    score += normalized_value * metric['weight']
            
            return round(score * 100 / total_weight)
            
        except Exception as e:
            print(f"[ERROR] Error calculating simplified SEO score: {e}")
            return 0
        
    async def get_gsc_data(self, credentials: Credentials, property_url: str, start_date: str, end_date: str) -> Dict:
        """Fetch GSC analytics data for a given date range."""
        try:
            service = build('webmasters', 'v3', credentials=credentials)
            
            # Time series data (for charts)
            time_series_request = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': ['date']
            }
            time_series_response = service.searchanalytics().query(
                siteUrl=property_url, body=time_series_request
            ).execute()

            # Summary data (for main stats)
            summary_request = {
                'startDate': start_date,
                'endDate': end_date
            }
            summary_response = service.searchanalytics().query(
                siteUrl=property_url, body=summary_request
            ).execute()
            
            return self._process_analytics_data(time_series_response, summary_response, start_date, end_date)
            
        except HttpError as e:
            print(f"[ERROR] HTTP error fetching GSC data: {e}")
            # Check for common errors
            if e.resp.status == 403:
                print("[INFO] User may not have permissions for this property or Search Console API is not enabled.")
            if e.resp.status == 404:
                print("[INFO] Property not found or user has no access.")
            return {}
        except Exception as e:
            print(f"[ERROR] General error fetching GSC data: {e}")
            return {}
    
    def _process_analytics_data(self, time_series_response: Dict, summary_response: Dict, start_date: str = None, end_date: str = None) -> Dict:
        """Process raw GSC analytics data into structured format."""
        
        # Process summary data
        summary = {
            'total_clicks': 0,
            'total_impressions': 0,
            'avg_ctr': 0,
            'avg_position': 0
        }
        if summary_response and 'rows' in summary_response and len(summary_response['rows']) > 0:
            summary_row = summary_response['rows'][0]
            summary['total_clicks'] = summary_row['clicks']
            summary['total_impressions'] = summary_row['impressions']
            summary['avg_ctr'] = summary_row['ctr']
            summary['avg_position'] = summary_row['position']

        # Process time series data with complete date range
        time_series = {
            'dates': [],
            'clicks': [],
            'impressions': [],
            'ctr': [],
            'positions': []
        }
        
        # Create a dictionary of existing data for quick lookup
        existing_data = {}
        if time_series_response and 'rows' in time_series_response:
            for row in time_series_response['rows']:
                date_str = row['keys'][0]
                existing_data[date_str] = {
                    'clicks': row['clicks'],
                    'impressions': row['impressions'],
                    'ctr': row['ctr'],
                    'position': row['position']
                }
        
        # Generate complete date range if start_date and end_date are provided
        if start_date and end_date:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            current_date = start
            
            while current_date <= end:
                date_str = current_date.strftime('%Y-%m-%d')
                time_series['dates'].append(date_str)
                
                if date_str in existing_data:
                    # Use actual data
                    data = existing_data[date_str]
                    time_series['clicks'].append(data['clicks'])
                    time_series['impressions'].append(data['impressions'])
                    time_series['ctr'].append(data['ctr'])
                    time_series['positions'].append(data['position'])
                else:
                    # Use zero values for missing data (including future dates)
                    time_series['clicks'].append(0)
                    time_series['impressions'].append(0)
                    time_series['ctr'].append(0)
                    time_series['positions'].append(0)
                
                current_date += timedelta(days=1)
        else:
            # Fallback to original behavior if no date range provided
            for row in sorted(time_series_response['rows'], key=lambda r: r['keys'][0]):
                time_series['dates'].append(row['keys'][0])
                time_series['clicks'].append(row['clicks'])
                time_series['impressions'].append(row['impressions'])
                time_series['ctr'].append(row['ctr'])
                time_series['positions'].append(row['position'])

        return {
            "summary": summary,
            "time_series": time_series
        }
    
    def _store_metrics(self, user_email: str, property_url: str, metrics: Dict):
        """Store the latest GSC metrics in Google Sheets."""
        try:
            metrics_sheet = self.db.get_or_create_sheet(
                'gsc-metrics', 
                headers=['user_email', 'property_url', 'metrics_json', 'last_updated']
            )
            metrics_json = json.dumps(metrics)
            
            try:
                cell = metrics_sheet.find(user_email)
                metrics_sheet.update_cell(cell.row, 2, property_url)
                metrics_sheet.update_cell(cell.row, 3, metrics_json)
                metrics_sheet.update_cell(cell.row, 4, datetime.utcnow().isoformat())
            except gspread.exceptions.CellNotFound:
                metrics_sheet.append_row([
                    user_email,
                    property_url,
                    metrics_json,
                    datetime.utcnow().isoformat()
                ])
        except Exception as e:
            print(f"[ERROR] Error storing metrics: {e}")
    
    async def get_stored_metrics(self, user_email: str, website_url: str) -> Optional[Dict]:
        """Get stored metrics for a user's website from Google Sheets."""
        try:
            metrics_sheet = self.db.get_or_create_sheet(
                'gsc-metrics',
                headers=['user_email', 'property_url', 'metrics_json', 'last_updated']
            )
            cell = metrics_sheet.find(user_email)
            
            if cell:
                row_data = metrics_sheet.row_values(cell.row)
                if len(row_data) >= 3 and row_data[1] == website_url:
                    metrics_json = row_data[2]
                return {
                        "metrics": json.loads(metrics_json),
                        "last_updated": row_data[3] if len(row_data) > 3 else datetime.utcnow().isoformat()
                }
            return None
        except Exception as e:
            print(f"[ERROR] Error getting stored metrics: {e}")
            return None

    async def fetch_keyword_data(self, user_email: str, property_url: str, days: int = 90) -> Dict:
        """Fetch keyword performance data from Google Search Console."""
        try:
            print(f"[DEBUG] fetch_keyword_data called for {property_url}")
            
            # Get user's GSC credentials
            credentials = self.oauth_handler.get_credentials(user_email)
            if not credentials:
                print("[ERROR] No GSC credentials found")
                return {}
            
            print(f"[DEBUG] GSC credentials obtained successfully")
            
            # Build GSC service
            service = build('webmasters', 'v3', credentials=credentials)
            
            # Calculate date range
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            # Request keyword data
            request = {
                'startDate': start_date.isoformat(),
                'endDate': end_date.isoformat(),
                'dimensions': ['query'],
                'rowLimit': 5000,  # Get up to 5000 keywords
                'startRow': 0
            }
            
            print(f"[DEBUG] Keyword data request: {request}")
            
            # Execute the request
            response = service.searchanalytics().query(
                siteUrl=property_url, 
                body=request
            ).execute()
            
            print(f"[DEBUG] Keyword data response received")
            print(f"[DEBUG] Response keys: {response.keys() if response else 'None'}")
            
            # Process the keyword data
            keyword_data = self._process_keyword_data(response, property_url)
            
            print(f"[DEBUG] Processed keyword data: {keyword_data}")
            
            return keyword_data
            
        except Exception as e:
            print(f"[ERROR] Error fetching keyword data: {e}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            return {}

    def _process_keyword_data(self, response: Dict, property_url: str) -> Dict:
        """Process raw keyword data into structured format."""
        try:
            if not response or 'rows' not in response:
                print("[DEBUG] No keyword data found in response")
                return {
                    'total_keywords': 0,
                    'avg_position': 0.0,
                    'opportunities': 0,
                    'branded_keywords': 0,
                    'top_keywords': "",
                    'keyword_insights': "No keyword data available yet. This is normal for new websites.",
                    'keywords_list': []
                }
            
            rows = response['rows']
            print(f"[DEBUG] Processing {len(rows)} keyword rows")
            
            # Extract domain for branded keyword detection
            from urllib.parse import urlparse
            parsed = urlparse(property_url)
            domain = parsed.netloc.replace("www.", "")
            
            # Process each keyword
            total_keywords = len(rows)
            total_position = 0
            opportunities = 0
            branded_keywords = 0
            keyword_details = []
            
            for row in rows:
                keyword = row['keys'][0]
                position = row['position']
                impressions = row['impressions']
                clicks = row['clicks']
                ctr = row['ctr']
                
                # Calculate total position
                total_position += position
                
                # Check for opportunities (keywords in positions 4-20 with good impressions)
                if 4 <= position <= 20 and impressions >= 10:
                    opportunities += 1
                
                # Check for branded keywords
                if self._is_branded_keyword(keyword, domain):
                    branded_keywords += 1
                
                # Store keyword details for top keywords
                keyword_details.append({
                    'keyword': keyword,
                    'position': position,
                    'impressions': impressions,
                    'clicks': clicks,
                    'ctr': ctr
                })
            
            # Calculate average position
            avg_position = total_position / total_keywords if total_keywords > 0 else 0.0
            
            # Get top 5 keywords by clicks
            top_keywords = sorted(keyword_details, key=lambda x: x['clicks'], reverse=True)[:5]
            top_keywords_text = "; ".join([kw['keyword'] for kw in top_keywords])
            
            # Generate insights
            keyword_insights = self._generate_keyword_insights(
                total_keywords, avg_position, opportunities, branded_keywords, top_keywords
            )
            
            return {
                'total_keywords': total_keywords,
                'avg_position': round(avg_position, 1),
                'opportunities': opportunities,
                'branded_keywords': branded_keywords,
                'top_keywords': top_keywords_text,
                'keyword_insights': keyword_insights,
                'keywords_list': keyword_details
            }
            
        except Exception as e:
            print(f"[ERROR] Error processing keyword data: {e}")
            return {
                'total_keywords': 0,
                'avg_position': 0.0,
                'opportunities': 0,
                'branded_keywords': 0,
                'top_keywords': "",
                'keyword_insights': f"Error processing keyword data: {str(e)}",
                'keywords_list': []
            }

    def _is_branded_keyword(self, keyword: str, domain: str) -> bool:
        """Check if a keyword contains the brand/domain name."""
        try:
            # Extract brand name from domain (remove TLD)
            brand_parts = domain.split('.')[0].lower()
            
            # Check if keyword contains brand name
            keyword_lower = keyword.lower()
            
            # Common brand indicators
            brand_indicators = [
                brand_parts,
                brand_parts.replace('-', ' '),
                brand_parts.replace('_', ' '),
                brand_parts.replace('-', ''),
                brand_parts.replace('_', '')
            ]
            
            return any(indicator in keyword_lower for indicator in brand_indicators)
            
        except Exception as e:
            print(f"[ERROR] Error checking branded keyword: {e}")
            return False

    def _generate_keyword_insights(self, total_keywords: int, avg_position: float, 
                                 opportunities: int, branded_keywords: int, 
                                 top_keywords: list) -> str:
        """Generate insights based on keyword performance data."""
        try:
            insights = []
            
            if total_keywords == 0:
                return "No keyword data available yet. This is normal for new websites."
            
            # Overall keyword portfolio assessment
            if total_keywords < 10:
                insights.append("Small keyword portfolio. Focus on expanding content to target more relevant keywords.")
            elif total_keywords < 100:
                insights.append("Growing keyword portfolio. Continue creating content around relevant topics.")
            else:
                insights.append(f"Strong keyword portfolio with {total_keywords} ranking terms.")
            
            # Position analysis
            if avg_position <= 3:
                insights.append("Excellent average position. Focus on maintaining rankings and improving CTR.")
            elif avg_position <= 10:
                insights.append("Good average position. Opportunities to improve rankings for better visibility.")
            else:
                insights.append("Average position needs improvement. Focus on content optimization and backlink building.")
            
            # Opportunity analysis
            if opportunities > 0:
                insights.append(f"Found {opportunities} high-opportunity keywords in positions 4-20. Prioritize these for optimization.")
            
            # Branded keyword analysis
            branded_percentage = (branded_keywords / total_keywords * 100) if total_keywords > 0 else 0
            if branded_percentage > 50:
                insights.append("High percentage of branded keywords. Consider expanding non-branded keyword targeting.")
            elif branded_percentage < 10:
                insights.append("Low branded keyword presence. Focus on brand awareness and branded search optimization.")
            
            # Top keyword insights
            if top_keywords:
                top_keyword = top_keywords[0]['keyword']
                insights.append(f"Top performing keyword: '{top_keyword}' with {top_keywords[0]['clicks']} clicks.")
            
            return " ".join(insights)
            
        except Exception as e:
            print(f"[ERROR] Error generating keyword insights: {e}")
            return "Keyword performance analysis completed."

class PageSpeedInsightsFetcher:
    """Handles fetching PageSpeed Insights data."""
    
    def __init__(self):
        self.api_key = settings.PAGESPEED_API_KEY
        self.base_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    
    async def fetch_pagespeed_data(self, url: str, strategy: str = "mobile", raw: bool = False) -> Dict:
        """Fetch PageSpeed Insights data for a given URL."""
        if not self.api_key:
            print("[WARNING] PageSpeed API key not configured")
            return self._get_demo_data()
        
        # Handle domain properties (convert sc-domain:domain.com to https://domain.com)
        if url.startswith('sc-domain:'):
            domain = url.replace('sc-domain:', '')
            url = f"https://{domain}"
            print(f"[DEBUG] Converted domain property to URL for PageSpeed: {url}")
        
        # Follow redirects to get the final URL
        final_url = await self._get_final_url(url)
        print(f"[DEBUG] Final URL after redirects: {final_url}")
        
        try:
            params = {
                'url': final_url,
                'key': self.api_key,
                'strategy': strategy,
                'category': 'performance'
            }
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    print(f"[DEBUG] PageSpeed API response status: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        print(f"[DEBUG] PageSpeed API response received")
                        if raw:
                            return data
                        # Process and return summary for frontend
                        lh = data.get("lighthouseResult", {})
                        audits = lh.get("audits", {})
                        categories = lh.get("categories", {})
                        performance = categories.get("performance", {})
                        return {
                            "performance_score": round(performance.get("score", 0) * 100),
                            "lcp": {"value": audits.get("largest-contentful-paint", {}).get("numericValue", 0) / 1000},
                            "fcp": {"value": audits.get("first-contentful-paint", {}).get("numericValue", 0) / 1000},
                            "cls": {"value": audits.get("cumulative-layout-shift", {}).get("numericValue", 0)},
                        }
                    else:
                        error_text = await response.text()
                        print(f"[ERROR] PageSpeed API error: {response.status}")
                        print(f"[ERROR] PageSpeed API response: {error_text}")
                        return self._get_demo_data()
                        
        except Exception as e:
            print(f"[ERROR] Error fetching PageSpeed data: {e}")
            return self._get_demo_data()
    
    async def _get_final_url(self, url: str) -> str:
        """Follow redirects to get the final URL."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, allow_redirects=True) as response:
                    return str(response.url)
        except Exception as e:
            print(f"[WARNING] Could not follow redirects for {url}: {e}")
            return url
    
    def _process_pagespeed_data(self, data: Dict) -> Dict:
        """Process raw PageSpeed Insights data into structured format."""
        try:
            print(f"[DEBUG] Processing PageSpeed data: {data.keys()}")
            
            lighthouse_result = data.get('lighthouseResult', {})
            audits = lighthouse_result.get('audits', {})
            
            # Extract Core Web Vitals
            lcp = audits.get('largest-contentful-paint', {})
            fcp = audits.get('first-contentful-paint', {})
            cls = audits.get('cumulative-layout-shift', {})
            
            # Extract performance score
            categories = lighthouse_result.get('categories', {})
            performance = categories.get('performance', {})
            performance_score = performance.get('score', 0)
            
            result = {
                'performance_score': round(performance_score * 100),
                'lcp': {
                    'value': lcp.get('numericValue', 0) / 1000,  # Convert to seconds
                    'score': lcp.get('score', 0)
                },
                'fcp': {
                    'value': fcp.get('numericValue', 0) / 1000,  # Convert to seconds
                    'score': fcp.get('score', 0)
                },
                'cls': {
                    'value': cls.get('numericValue', 0),
                    'score': cls.get('score', 0)
                },
                'last_updated': datetime.utcnow().isoformat()
            }
            
            print(f"[DEBUG] Processed PageSpeed result: {result}")
            return result
        except Exception as e:
            print(f"[ERROR] Error processing PageSpeed data: {e}")
            return self._get_demo_data()
    
    def _get_demo_data(self) -> Dict:
        """Return empty data when API is not available."""
        return {
            'performance_score': 0,
            'lcp': {'value': 0, 'score': 0},
            'fcp': {'value': 0, 'score': 0},
            'cls': {'value': 0, 'score': 0},
            'last_updated': datetime.utcnow().isoformat()
        }

# Create PageSpeed Insights fetcher instance
pagespeed_fetcher = PageSpeedInsightsFetcher()

class MobileUsabilityFetcher:
    """Fetcher for mobile usability data using GSC and PageSpeed Insights."""

    def __init__(self):
        self.pagespeed_fetcher = PageSpeedInsightsFetcher()

    async def fetch_mobile_data(self, url: str) -> Dict:
        """Fetch mobile-friendly test data for a given URL via GSC and PageSpeed."""
        print(f"[DEBUG] Fetching mobile data via GSC and PageSpeed for: {url}")
        
        try:
            # Convert domain property to actual URL if needed
            if url.startswith('sc-domain:'):
                domain = url.replace('sc-domain:', '')
                actual_url = f"https://{domain}"
            else:
                actual_url = url
            
            # Get the final URL after redirects
            final_url = await self._get_final_url(actual_url)
            print(f"[DEBUG] Final URL for mobile analysis: {final_url}")
            
            # Get PageSpeed data for mobile performance (raw=True)
            pagespeed_data = await self.pagespeed_fetcher.fetch_pagespeed_data(final_url, strategy="mobile", raw=True)
            
            # Get GSC mobile usability data
            gsc_mobile_data = await self._get_gsc_mobile_data(url, final_url)
            
            # Combine both data sources
            return self._process_mobile_data(pagespeed_data, gsc_mobile_data)

        except Exception as e:
            print(f"Error fetching mobile data: {e}")
            return self._get_demo_data()
    
    async def _get_final_url(self, url: str) -> str:
        """Get the final URL after following redirects."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url, allow_redirects=True) as response:
                    final_url = str(response.url)
                    print(f"[DEBUG] Final URL after redirects: {final_url}")
                    return final_url
        except Exception as e:
            print(f"Error getting final URL: {e}")
            return url
    
    async def _get_gsc_mobile_data(self, site_url: str, page_url: str) -> Dict:
        """Get mobile usability data from Google Search Console."""
        try:
            # This would require GSC API credentials
            # For now, we'll use PageSpeed data as a proxy
            print(f"[DEBUG] Getting GSC mobile data for site: {site_url}, page: {page_url}")
            
            # Return basic mobile data structure
            return {
                'mobile_friendly': True,  # Assume mobile-friendly if PageSpeed works
                'issues_count': 0,
                'critical_issues': 0,
                'warning_issues': 0,
                'issues': []
            }
        except Exception as e:
            print(f"Error getting GSC mobile data: {e}")
            return {
                'mobile_friendly': False,
                'issues_count': 0,
                'critical_issues': 0,
                'warning_issues': 0,
                'issues': []
            }
    
    def _process_mobile_data(self, pagespeed_data: Dict, gsc_mobile_data: Dict) -> Dict:
        """Process PageSpeed and GSC data to extract mobile usability info."""
        try:
            print("[DEBUG] Raw PageSpeed data:", pagespeed_data)
            if not pagespeed_data:
                print("[WARNING] No PageSpeed data available for mobile analysis")
                return self._get_demo_data()
            
            # Extract mobile-specific metrics from PageSpeed
            lighthouse_result = pagespeed_data.get('lighthouseResult', {})
            audits = lighthouse_result.get('audits', {})
            print("[DEBUG] Audits received:", audits)
            
            # Mobile-specific audits
            viewport_audit = audits.get('viewport', {})
            font_display_audit = audits.get('font-display', {})
            tap_targets_audit = audits.get('tap-targets', {})
            content_width_audit = audits.get('content-width', {})
            
            # Determine mobile friendliness based on audits with detailed explanations
            mobile_issues = []
            critical_issues = 0
            warning_issues = 0
            
            # Check viewport configuration
            if viewport_audit.get('score', 1) < 1:
                mobile_issues.append({
                    'title': 'Viewport Configuration Issue',
                    'description': 'Your page lacks a proper viewport meta tag, causing it to display incorrectly on mobile devices.',
                    'impact': 'Visitors on mobile will see a zoomed-out desktop version that\'s hard to read and navigate.',
                    'solution': 'Add <meta name="viewport" content="width=device-width, initial-scale=1"> to your HTML head.',
                    'severity': 'critical'
                })
                critical_issues += 1
            
            # Check font display with detailed explanation
            if font_display_audit.get('score', 1) < 1:
                font_details = font_display_audit.get('details', {})
                font_items = font_details.get('items', [])
                
                if font_items:
                    # Count the number of problematic fonts without showing URLs
                    font_count = len(font_items[:3])
                    font_text = f"{font_count} web fonts" if font_count > 1 else "A web font"
                    
                    mobile_issues.append({
                        'title': 'Font Display Performance Issue',
                        'description': f'{font_text} are blocking text display during page load.',
                        'impact': 'Visitors see invisible text for several seconds while fonts load, creating a poor reading experience and potential bounce.',
                        'solution': 'Add font-display: swap; to your CSS @font-face rules to show fallback text immediately.',
                        'severity': 'warning'
                    })
                else:
                    mobile_issues.append({
                        'title': 'Font Display Performance Issue',
                        'description': 'Web fonts are blocking text display during page load.',
                        'impact': 'Visitors see invisible text while fonts load, creating a frustrating reading experience.',
                        'solution': 'Add font-display: swap; to your CSS @font-face rules to show fallback text immediately.',
                        'severity': 'warning'
                    })
                warning_issues += 1
            
            # Check tap targets with specific measurements
            if tap_targets_audit.get('score', 1) < 1:
                tap_details = tap_targets_audit.get('details', {})
                tap_items = tap_details.get('items', [])
                
                if tap_items:
                    small_targets = len([item for item in tap_items if item.get('size', '').endswith('px')])
                    mobile_issues.append({
                        'title': 'Touch Target Size Issue',
                        'description': f'{small_targets} clickable elements are too small or too close together for mobile users.',
                        'impact': 'Visitors struggle to tap buttons and links accurately, leading to frustration and accidental clicks.',
                        'solution': 'Ensure all clickable elements are at least 44px tall and have 8px spacing between them.',
                        'severity': 'critical'
                    })
                else:
                    mobile_issues.append({
                        'title': 'Touch Target Size Issue',
                        'description': 'Some clickable elements are too small or too close together for mobile users.',
                        'impact': 'Visitors struggle to tap buttons and links accurately, leading to frustration.',
                        'solution': 'Ensure all clickable elements are at least 44px tall and have 8px spacing.',
                        'severity': 'critical'
                    })
                critical_issues += 1
            
            # Check content width
            if content_width_audit.get('score', 1) < 1:
                mobile_issues.append({
                    'title': 'Content Width Issue',
                    'description': 'Page content is wider than the mobile screen, requiring horizontal scrolling.',
                    'impact': 'Visitors must scroll horizontally to read content, creating a poor mobile experience.',
                    'solution': 'Use responsive CSS with max-width: 100% and avoid fixed-width elements wider than the viewport.',
                    'severity': 'critical'
                })
                critical_issues += 1
            
            # Performance metrics
            performance_score = pagespeed_data.get('lighthouseResult', {}).get('categories', {}).get('performance', {}).get('score', 0) * 100
            
            # Add performance-related issues that affect mobile experience
            lcp = audits.get('largest-contentful-paint', {})
            fcp = audits.get('first-contentful-paint', {})
            cls = audits.get('cumulative-layout-shift', {})
            
            # Check LCP (Largest Contentful Paint)
            if lcp and lcp.get('numericValue') is not None:
                lcp_seconds = lcp.get('numericValue', 0) / 1000
                if lcp_seconds > 4.0:
                    mobile_issues.append({
                        'title': 'Slow Content Loading (LCP)',
                        'description': f'Your main content takes {lcp_seconds:.1f} seconds to load on mobile (should be under 2.5s).',
                        'impact': 'Visitors see a blank screen for too long, leading to frustration and potential abandonment.',
                        'solution': 'Optimize images, reduce server response time, and prioritize loading of above-the-fold content.',
                        'severity': 'critical'
                    })
                    critical_issues += 1
                elif lcp_seconds > 2.5:
                    mobile_issues.append({
                        'title': 'Slow Content Loading (LCP)',
                        'description': f'Your main content takes {lcp_seconds:.1f} seconds to load on mobile (should be under 2.5s).',
                        'impact': 'Visitors experience noticeable delays when viewing your content.',
                        'solution': 'Optimize images, reduce server response time, and prioritize loading of above-the-fold content.',
                        'severity': 'warning'
                    })
                    warning_issues += 1
            elif not lcp or lcp.get('numericValue') is None:
                mobile_issues.append({
                    'title': 'Loading Performance Unknown',
                    'description': 'Unable to measure how quickly your content loads on mobile devices.',
                    'impact': 'Cannot assess if visitors experience slow loading times.',
                    'solution': 'Ensure your site is accessible to performance testing tools and check for blocking scripts.',
                    'severity': 'warning'
                })
                warning_issues += 1
            
            # Check FCP (First Contentful Paint)
            if fcp and fcp.get('numericValue') is not None:
                fcp_seconds = fcp.get('numericValue', 0) / 1000
                if fcp_seconds > 3.0:
                    mobile_issues.append({
                        'title': 'Slow Initial Display (FCP)',
                        'description': f'Your page takes {fcp_seconds:.1f} seconds to show any content on mobile (should be under 1.8s).',
                        'impact': 'Visitors see a completely blank page for too long, creating uncertainty about whether the site is working.',
                        'solution': 'Minimize render-blocking resources, optimize CSS delivery, and reduce server response time.',
                        'severity': 'critical'
                    })
                    critical_issues += 1
                elif fcp_seconds > 1.8:
                    mobile_issues.append({
                        'title': 'Slow Initial Display (FCP)',
                        'description': f'Your page takes {fcp_seconds:.1f} seconds to show any content on mobile (should be under 1.8s).',
                        'impact': 'Visitors experience a noticeable delay before seeing any content.',
                        'solution': 'Minimize render-blocking resources and optimize CSS delivery.',
                        'severity': 'warning'
                    })
                    warning_issues += 1
            
            # Check CLS (Cumulative Layout Shift)
            if cls and cls.get('numericValue') is not None:
                cls_value = cls.get('numericValue', 0)
                if cls_value > 0.25:
                    mobile_issues.append({
                        'title': 'Layout Shifting Issues (CLS)',
                        'description': f'Page elements move unexpectedly during loading (CLS: {cls_value:.2f}, should be under 0.1).',
                        'impact': 'Visitors accidentally tap wrong buttons or lose their reading position as content shifts around.',
                        'solution': 'Set explicit dimensions for images and ads, avoid inserting content above existing content.',
                        'severity': 'critical'
                    })
                    critical_issues += 1
                elif cls_value > 0.1:
                    mobile_issues.append({
                        'title': 'Layout Shifting Issues (CLS)',
                        'description': f'Some page elements move during loading (CLS: {cls_value:.2f}, should be under 0.1).',
                        'impact': 'Visitors may experience minor disruptions as content shifts.',
                        'solution': 'Set explicit dimensions for images and avoid inserting content above existing content.',
                        'severity': 'warning'
                    })
                    warning_issues += 1
            
            # If no specific issues found but performance is very low, add general explanation
            if performance_score < 10 and not mobile_issues:
                mobile_issues.append({
                    'title': 'Poor Mobile Performance',
                    'description': 'Your site has very poor mobile performance but specific issues could not be identified.',
                    'impact': 'Visitors likely experience slow loading and poor responsiveness on mobile devices.',
                    'solution': 'Check if your site blocks performance testing tools, optimize images, and reduce JavaScript.',
                    'severity': 'critical'
                })
                critical_issues += 1
            
            print("[DEBUG] Mobile issues detected:", mobile_issues)
            
            # Determine overall mobile friendliness
            is_mobile_friendly = critical_issues == 0 and performance_score > 50
            
            # Generate insights
            insights = self._generate_mobile_insights(is_mobile_friendly, mobile_issues, performance_score)
            
            return {
                'mobile_friendly': 'Yes' if is_mobile_friendly else 'No',
                'issues_count': len(mobile_issues),
                'critical_issues': critical_issues,
                'warning_issues': warning_issues,
                'issues': mobile_issues,
                'performance_score': round(performance_score, 1),
                'insights': insights,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"Error processing mobile data: {e}")
            return self._get_demo_data()
    
    def _generate_mobile_insights(self, is_mobile_friendly: bool, issues: List, performance_score: float) -> str:
        """Generate mobile usability insights."""
        if is_mobile_friendly:
            if performance_score > 80:
                return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block; vertical-align: text-top; margin-right: 8px;"><polyline points="20,6 9,17 4,12"></polyline></svg>Excellent mobile experience with high performance'
            elif performance_score > 60:
                return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block; vertical-align: text-top; margin-right: 8px;"><polyline points="20,6 9,17 4,12"></polyline></svg>Good mobile experience with room for performance improvements'
            else:
                return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block; vertical-align: text-top; margin-right: 8px;"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>Mobile-friendly but performance needs optimization'
        else:
            if issues:
                # Extract titles from issue objects for the insight summary
                issue_titles = []
                for issue in issues[:3]:
                    if isinstance(issue, dict):
                        issue_titles.append(issue.get('title', 'Unknown issue'))
                    else:
                        issue_titles.append(str(issue))
                return f'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#EF4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block; vertical-align: text-top; margin-right: 8px;"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>Issues detected: {", ".join(issue_titles)}'
    
    def _get_demo_data(self) -> Dict:
        """Return empty mobile usability data when real data is not available."""
        return {
            'mobile_friendly': 'No',
            'issues_count': 0,
            'critical_issues': 0,
            'warning_issues': 0,
            'issues': [],
            'performance_score': 0,
            'insights': 'No mobile usability data available',
            'last_updated': datetime.utcnow().isoformat()
        }

# Create Mobile Usability fetcher instance
mobile_fetcher = MobileUsabilityFetcher()

class IndexingCrawlabilityFetcher:
    """Fetcher for indexing and crawlability data from Google Search Console."""
    
    def __init__(self, credentials):
        self.credentials = credentials
        self.service = build('searchconsole', 'v1', credentials=credentials)
    
    def fetch_indexing_data(self, site_url):
        """Fetch indexing and crawlability metrics."""
        try:
            print(f"[DEBUG] Fetching indexing data for site: {site_url}")
            
            # Get sitemap information
            print("[DEBUG] Fetching sitemap information...")
            sitemaps = self._get_sitemaps(site_url)
            print(f"[DEBUG] Sitemap data: {sitemaps}")
            
            # Get URL inspection data (sample of indexed pages)
            print("[DEBUG] Fetching indexed pages information...")
            indexed_pages = self._get_indexed_pages(site_url)
            print(f"[DEBUG] Indexed pages data: {indexed_pages}")
            
            # Get crawl stats
            print("[DEBUG] Fetching crawl statistics...")
            crawl_stats = self._get_crawl_stats(site_url)
            print(f"[DEBUG] Crawl stats data: {crawl_stats}")
            
            result = {
                'sitemap_status': sitemaps.get('status', 'Unknown'),
                'sitemap_count': sitemaps.get('count', 0),
                'indexed_pages': indexed_pages.get('count', 0),
                'index_status': indexed_pages.get('status', 'Unknown'),
                'crawl_errors': crawl_stats.get('errors', 0),
                'crawl_success_rate': crawl_stats.get('success_rate', 0),
                'last_crawl': crawl_stats.get('last_crawl', 'Unknown'),
                'insights': self._generate_insights(sitemaps, indexed_pages, crawl_stats)
            }
            
            print(f"[DEBUG] Final indexing result: {result}")
            return result
        except Exception as e:
            print(f"Error fetching indexing data: {e}")
            # Return empty data if API calls fail
            print("[INFO] Using empty indexing data due to API error")
            return {
                'sitemap_status': 'Unknown',
                'sitemap_count': 0,
                'indexed_pages': 0,
                'index_status': 'Unknown',
                'crawl_errors': 0,
                'crawl_success_rate': 0,
                'last_crawl': 'Unknown',
                'insights': ['No indexing data available']
            }
    
    def _get_sitemaps(self, site_url):
        """Get sitemap information."""
        try:
            print(f"[DEBUG] Calling sitemaps().list() for site: {site_url}")
            request = self.service.sitemaps().list(siteUrl=site_url)
            response = request.execute()
            print(f"[DEBUG] Sitemaps API response: {response}")
            
            sitemaps = response.get('sitemap', [])
            if sitemaps:
                # Check if sitemaps are being processed successfully
                successful_sitemaps = [s for s in sitemaps if s.get('isPending') == False]
                result = {
                    'status': 'Active' if successful_sitemaps else 'Pending',
                    'count': len(sitemaps),
                    'successful': len(successful_sitemaps)
                }
                print(f"[DEBUG] Processed sitemap result: {result}")
                return result
            else:
                print("[DEBUG] No sitemaps found")
                return {'status': 'Not Found', 'count': 0, 'successful': 0}
        except Exception as e:
            print(f"Error fetching sitemaps: {e}")
            return {'status': 'Error', 'count': 0, 'successful': 0}
    
    def _get_indexed_pages(self, site_url):
        """Get information about indexed pages."""
        try:
            # Convert domain property to actual URL if needed
            if site_url.startswith('sc-domain:'):
                domain = site_url.replace('sc-domain:', '')
                sample_url = f"https://{domain}/"
            else:
                sample_url = f"{site_url.rstrip('/')}/"
            
            print(f"[DEBUG] Calling URL inspection for sample URL: {sample_url}")
            print(f"[DEBUG] Site URL for inspection: {site_url}")
            
            request = self.service.urlInspection().index().inspect(
                body={
                    'inspectionUrl': sample_url,
                    'siteUrl': site_url
                }
            )
            response = request.execute()
            print(f"[DEBUG] URL inspection API response: {response}")
            
            inspection_result = response.get('inspectionResult', {})
            index_status = inspection_result.get('indexStatusResult', {})
            
            result = {
                'status': index_status.get('verdict', 'Unknown'),
                'count': 1,  # This is just a sample, not total count
                'last_seen': index_status.get('lastCrawlTime', 'Unknown')
            }
            print(f"[DEBUG] Processed URL inspection result: {result}")
            return result
        except Exception as e:
            print(f"Error fetching indexed pages: {e}")
            return {'status': 'Error', 'count': 0, 'last_seen': 'Unknown'}
    
    def _get_crawl_stats(self, site_url):
        """Get crawl statistics."""
        try:
            # Use sitemaps as a proxy for crawl health since direct crawl stats are limited
            end_date = datetime.now().date()
            print(f"[DEBUG] Checking crawl health via sitemaps for site: {site_url}")
            
            sitemaps = self._get_sitemaps(site_url)
            if sitemaps['status'] == 'Active':
                result = {
                    'success_rate': 90,  # Active sitemaps indicate good crawl health
                    'errors': 0,
                    'last_crawl': end_date.isoformat()
                }
            elif sitemaps['status'] == 'Pending':
                result = {
                    'success_rate': 50,  # Pending sitemaps indicate some issues
                    'errors': 0,
                    'last_crawl': end_date.isoformat()
                }
            else:
                result = {
                    'success_rate': 0,  # No sitemaps indicate crawl problems
                    'errors': 0,
                    'last_crawl': 'Unknown'
                }
            
            print(f"[DEBUG] Processed crawl stats result: {result}")
            return result
        except Exception as e:
            print(f"Error fetching crawl stats: {e}")
            return {'success_rate': 0, 'errors': 0, 'last_crawl': 'Unknown'}
    
    def _generate_insights(self, sitemaps, indexed_pages, crawl_stats):
        """Generate insights based on the data."""
        insights = []
        
        # Sitemap insights
        if sitemaps['status'] == 'Active':
            insights.append('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block; vertical-align: text-top; margin-right: 8px;"><polyline points="20,6 9,17 4,12"></polyline></svg>Sitemap is active and being processed')
        elif sitemaps['status'] == 'Pending':
            insights.append('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block; vertical-align: text-top; margin-right: 8px;"><circle cx="12" cy="12" r="10"></circle><polyline points="12,6 12,12 16,14"></polyline></svg>Sitemap is pending processing')
        elif sitemaps['status'] == 'Not Found':
            insights.append('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block; vertical-align: text-top; margin-right: 8px;"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>No sitemap found - consider adding one')
        else:
            insights.append('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#EF4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block; vertical-align: text-top; margin-right: 8px;"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>Sitemap issues detected')
        
        # Indexing insights
        if indexed_pages['status'] == 'PASS':
            insights.append('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block; vertical-align: text-top; margin-right: 8px;"><polyline points="20,6 9,17 4,12"></polyline></svg>Pages are being indexed properly')
        elif indexed_pages['status'] == 'FAIL':
            insights.append('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#EF4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block; vertical-align: text-top; margin-right: 8px;"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>Indexing issues detected')
        else:
            insights.append('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block; vertical-align: text-top; margin-right: 8px;"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>Indexing status unclear')
        
        # Crawl insights
        if crawl_stats['success_rate'] > 80:
            insights.append('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block; vertical-align: text-top; margin-right: 8px;"><polyline points="20,6 9,17 4,12"></polyline></svg>Crawling is working well')
        elif crawl_stats['success_rate'] > 50:
            insights.append('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block; vertical-align: text-top; margin-right: 8px;"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>Some crawling issues detected')
        else:
            insights.append('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#EF4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block; vertical-align: text-top; margin-right: 8px;"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>Crawling problems detected')
        
        return insights 

class BusinessContextFetcher:
    """Fetcher for business context and intelligence data."""
    
    def __init__(self):
        self.business_analyzer = None
        # Don't import here - will import when needed
    
    async def fetch_business_data(self, url: str) -> Dict:
        """Fetch business context and intelligence data."""
        try:
            print(f"[DEBUG] Fetching business context data for: {url}")
            
            # Convert domain property to actual URL if needed
            final_url = await self._get_final_url(url)
            print(f"[DEBUG] Final URL for business analysis: {final_url}")
            
            # Try to import and use the business analyzer
            if self.business_analyzer is None:
                try:
                    import sys
                    import os
                    # Add the project root to the path if not already there
                    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    if project_root not in sys.path:
                        sys.path.insert(0, project_root)
                    
                    # Try direct import from file path
                    import importlib.util
                    spec = importlib.util.spec_from_file_location(
                        "business_analysis", 
                        os.path.join(project_root, "core", "modules", "business_analysis.py")
                    )
                    business_analysis_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(business_analysis_module)
                    BusinessAnalyzer = business_analysis_module.BusinessAnalyzer
                    
                    self.business_analyzer = BusinessAnalyzer()
                    print("[DEBUG] BusinessAnalyzer successfully imported and initialized via direct file import")
                except Exception as e:
                    print(f"Warning: BusinessAnalyzer not available: {e}")
                    print(f"[DEBUG] Current sys.path: {sys.path[:3]}...")  # Show first 3 paths
                    self.business_analyzer = False  # Mark as failed
            
            if self.business_analyzer and self.business_analyzer is not False:
                # Use the business analyzer if available
                business_data = self.business_analyzer.analyze_business(final_url)
                print(f"[DEBUG] Business analysis completed: {business_data}")
                
                # Format the data for the frontend
                result = self._format_business_data(business_data)
                print(f"[DEBUG] Formatted business data: {result}")
                return result
            else:
                # Fallback to basic analysis
                print("[DEBUG] Using fallback business analysis")
                return await self._fallback_business_analysis(final_url)
                
        except Exception as e:
            print(f"Error fetching business context data: {e}")
            print("[INFO] Using empty business data due to error")
            return self._get_demo_data()
    
    async def _get_final_url(self, url: str) -> str:
        """Get the final URL after following redirects."""
        try:
            # Convert domain property to actual URL if needed
            if url.startswith('sc-domain:'):
                domain = url.replace('sc-domain:', '')
                actual_url = f"https://{domain}"
            else:
                actual_url = url
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(actual_url, allow_redirects=True) as response:
                    final_url = str(response.url)
                    print(f"[DEBUG] Final URL after redirects: {final_url}")
                    return final_url
        except Exception as e:
            print(f"Error getting final URL: {e}")
            # Return the original URL if we can't get the final URL
            if url.startswith('sc-domain:'):
                domain = url.replace('sc-domain:', '')
                return f"https://{domain}"
            return url
    
    def _format_business_data(self, business_data: Dict) -> Dict:
        """Format business analysis data for frontend consumption."""
        try:
            return {
                'business_type': business_data.get('business_model', 'Unknown'),
                'target_market': business_data.get('target_market', 'Unknown'),
                'industry_sector': business_data.get('industry_sector', 'General'),
                'company_size': business_data.get('company_size', 'Unknown'),
                'primary_age_group': business_data.get('primary_age_group', 'General'),
                'income_level': business_data.get('income_level', 'Mid-Range'),
                'audience_sophistication': business_data.get('audience_sophistication', 'General'),
                'geographic_focus': business_data.get('geographic_focus', 'Local'),
                'business_maturity': business_data.get('business_maturity', 'Established'),
                'technology_platform': business_data.get('technology_platform', 'Standard'),
                'content_strategy': business_data.get('content_marketing', {}).get('strategy', 'Basic'),
                'competitive_position': business_data.get('competitive_position', 'Standard'),
                'insights': business_data.get('business_insights', []),
                'seo_recommendations': business_data.get('seo_strategy_recommendations', []),
                'last_updated': datetime.utcnow().isoformat()
            }
        except Exception as e:
            print(f"Error formatting business data: {e}")
            return self._get_demo_data()
    
    async def _fallback_business_analysis(self, url: str) -> Dict:
        """Basic business analysis when the full analyzer is not available."""
        try:
            # URL should already be converted to actual URL by the calling method
            actual_url = url
            print(f"[DEBUG] Fallback analysis using URL: {actual_url}")
            
            import aiohttp
            from bs4 import BeautifulSoup
            
            async with aiohttp.ClientSession() as session:
                async with session.get(actual_url) as response:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Basic analysis
                    text_content = soup.get_text().lower()
                    
                    # Determine business type
                    if any(word in text_content for word in ['shop', 'buy', 'cart', 'checkout']):
                        business_type = 'E-commerce'
                    elif any(word in text_content for word in ['service', 'consulting', 'expert']):
                        business_type = 'Professional Services'
                    elif any(word in text_content for word in ['software', 'app', 'platform']):
                        business_type = 'SaaS'
                    else:
                        business_type = 'Information/Content'
                    
                    # Determine target market
                    if any(word in text_content for word in ['business', 'enterprise', 'corporate']):
                        target_market = 'B2B'
                    else:
                        target_market = 'B2C'
                    
                    return {
                        'business_type': business_type,
                        'target_market': target_market,
                        'industry_sector': 'General',
                        'company_size': 'Small',
                        'primary_age_group': 'General',
                        'income_level': 'Mid-Range',
                        'audience_sophistication': 'General',
                        'geographic_focus': 'Local',
                        'business_maturity': 'Established',
                        'technology_platform': 'Standard',
                        'content_strategy': 'Basic',
                        'competitive_position': 'Standard',
                        'insights': [
                            f"Identified as {business_type} business targeting {target_market} market",
                            "Basic analysis completed - connect GSC for deeper insights"
                        ],
                        'seo_recommendations': [
                            "Focus on local SEO if serving local customers",
                            "Optimize for mobile users",
                            "Create valuable, relevant content"
                        ],
                        'last_updated': datetime.utcnow().isoformat()
                    }
        except Exception as e:
            print(f"Error in fallback business analysis: {e}")
            return self._get_demo_data()
    
    def _get_demo_data(self) -> Dict:
        """Return empty business context data when real data is not available."""
        return {
            'business_type': 'Unknown',
            'target_market': 'Unknown',
            'industry_sector': 'Unknown',
            'company_size': 'Unknown',
            'primary_age_group': 'Unknown',
            'income_level': 'Unknown',
            'audience_sophistication': 'Unknown',
            'geographic_focus': 'Unknown',
            'business_maturity': 'Unknown',
            'technology_platform': 'Unknown',
            'content_strategy': 'Unknown',
            'competitive_position': 'Unknown',
            'insights': [],
            'seo_recommendations': [],
            'last_updated': datetime.utcnow().isoformat()
        }

# Create Business Context fetcher instance
business_fetcher = BusinessContextFetcher() 