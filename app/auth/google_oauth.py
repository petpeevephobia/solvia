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
            'https://www.googleapis.com/auth/webmasters',  # Full access needed for URL Inspection API
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
        # Check if database is in demo mode
        if self.db.demo_mode:
            print(f"[DEBUG] Database in demo mode, cannot store credentials for {user_email}")
            return
            
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
                # Update existing credentials using batch update
                print(f"[DEBUG] Found existing credentials for {user_email} at row {cell.row}. Updating token.")
                gsc_connections_sheet.batch_update([
                    {'range': f'B{cell.row}', 'values': [[credentials.token]]},
                    {'range': f'C{cell.row}', 'values': [[credentials.refresh_token or '']]},
                    {'range': f'D{cell.row}', 'values': [[credentials.expiry.isoformat() if credentials.expiry else '']]},
                    {'range': f'F{cell.row}', 'values': [[datetime.utcnow().isoformat()]]}
                ])
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
        # Check if database is in demo mode
        if self.db.demo_mode:
            print(f"[DEBUG] Database in demo mode, no credentials available for {user_email}")
            return None
            
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
            # If we're in demo mode or rate limited, don't clear credentials
            if not self.db.demo_mode:
                # Only clear credentials if we can actually access the database
                try:
                    self._clear_credentials(user_email)
                except Exception as clear_error:
                    print(f"[WARNING] Could not clear credentials due to: {clear_error}")
                return []
        
        try:
            service = build('searchconsole', 'v1', credentials=credentials)
            sites = service.sites().list().execute()
            
            properties = []
            for site in sites.get('siteEntry', []):
                site_url = site['siteUrl']
                permission = site['permissionLevel']
                
                properties.append({
                    'siteUrl': site_url,
                    'permissionLevel': permission,
                    'isVerified': True
                })
            
                # Show detailed info about each property
                if site_url.startswith('sc-domain:'):
                    print(f"[DEBUG] Found DOMAIN property: {site_url} (permission: {permission})")
                else:
                    print(f"[DEBUG] Found URL PREFIX property: {site_url} (permission: {permission})")
            
            print(f"[DEBUG] Retrieved {len(properties)} properties total")
            print(f"[DEBUG] Full properties list: {properties}")
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
        # Check if database is in demo mode
        if self.db.demo_mode:
            print(f"[DEBUG] Database in demo mode, cannot clear credentials for {user_email}")
            return
            
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
        """Fetch SEO metrics from GSC for the last 30 days comparing vs previous 30 days."""
        try:
            credentials = self.oauth_handler.get_credentials(user_email)
            if not credentials or not credentials.valid:
                raise Exception("Invalid or missing Google credentials")

            # Calculate 30-day date ranges
            today = datetime.utcnow().date()
            current_end_date = today - timedelta(days=3)  # Data is usually delayed by 3-4 days
            current_start_date = current_end_date - timedelta(days=days - 1)  # 30 days total
            
            # For comparison, get the previous 30 days
            comparison_end_date = current_start_date - timedelta(days=1)
            comparison_start_date = comparison_end_date - timedelta(days=days - 1)
            
            print(f"[DEBUG] Fetching current 30-day data: {current_start_date} to {current_end_date}")
            print(f"[DEBUG] Fetching comparison 30-day data: {comparison_start_date} to {comparison_end_date}")
            print(f"[DEBUG] Today is: {today}, using end date: {current_end_date} (3 days delay)")
            
            # Fetch data for current 30 days
            current_metrics = await self.get_gsc_data(
                credentials, property_url, 
                current_start_date.strftime('%Y-%m-%d'), 
                current_end_date.strftime('%Y-%m-%d')
            )

            # Fetch data for comparison 30 days
            comparison_metrics = await self.get_gsc_data(
                credentials, property_url, 
                comparison_start_date.strftime('%Y-%m-%d'), 
                comparison_end_date.strftime('%Y-%m-%d')
            )
            
            # Calculate deltas between current 30 days and previous 30 days
            current_summary = current_metrics.get('summary', {})
            comparison_summary = comparison_metrics.get('summary', {})
            
            print(f"[DEBUG] Current 30-day metrics summary: {current_summary}")
            print(f"[DEBUG] Previous 30-day metrics summary: {comparison_summary}")
            
            # Add 30-day comparison changes to summary (preserving current values)
            current_summary['impressions_change'] = current_summary.get('total_impressions', 0) - comparison_summary.get('total_impressions', 0)
            current_summary['clicks_change'] = current_summary.get('total_clicks', 0) - comparison_summary.get('total_clicks', 0)
            current_summary['ctr_change'] = current_summary.get('avg_ctr', 0) - comparison_summary.get('avg_ctr', 0)
            current_summary['position_change'] = current_summary.get('avg_position', 0) - comparison_summary.get('avg_position', 0)

            print(f"[DEBUG] Final summary after adding changes: {current_summary}")

            print(f"[DEBUG] 30-Day vs 30-Day Comparison Results:")
            print(f"[DEBUG] - Impressions: {current_summary.get('total_impressions', 0)} vs {comparison_summary.get('total_impressions', 0)} = {current_summary['impressions_change']:+}")
            print(f"[DEBUG] - Clicks: {current_summary.get('total_clicks', 0)} vs {comparison_summary.get('total_clicks', 0)} = {current_summary['clicks_change']:+}")
            print(f"[DEBUG] - CTR: {current_summary.get('avg_ctr', 0):.3f} vs {comparison_summary.get('avg_ctr', 0):.3f} = {current_summary['ctr_change']:+.3f}")
            print(f"[DEBUG] - Position: {current_summary.get('avg_position', 0):.1f} vs {comparison_summary.get('avg_position', 0):.1f} = {current_summary['position_change']:+.1f}")
            
            # Calculate SEO score change based on 30-day comparison
            current_seo_score = self._calculate_simplified_seo_score(current_summary)
            previous_seo_score = self._calculate_simplified_seo_score(comparison_summary)
            current_summary['seo_score_change'] = current_seo_score - previous_seo_score
            
            print(f"[DEBUG] SEO Score: {current_seo_score} vs {previous_seo_score} = {current_summary['seo_score_change']:+}")
            
            # Use the current 30-day data for time series (already fetched)
            chart_metrics = current_metrics
            
            # Combine metrics
            final_metrics = {
                'summary': current_summary,
                'time_series': chart_metrics.get('time_series', {}),
                'start_date': current_start_date.strftime('%Y-%m-%d'),
                'end_date': current_end_date.strftime('%Y-%m-%d'),
                'comparison_start_date': comparison_start_date.strftime('%Y-%m-%d'),
                'comparison_end_date': comparison_end_date.strftime('%Y-%m-%d'),
                'website_url': property_url,
                # Add visibility_performance metrics for dashboard caching
                'visibility_performance': {
                    'metrics': {
                        'impressions': { 'current_value': current_summary.get('total_impressions', 0) },
                        'clicks': { 'current_value': current_summary.get('total_clicks', 0) },
                        'ctr': { 'current_value': current_summary.get('avg_ctr', 0) },
                        'avg_position': { 'current_value': current_summary.get('avg_position', 0) }
                    }
                }
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
            if not metrics_sheet:  # Demo mode
                print(f"[DEBUG] Demo mode - cannot store metrics for {user_email}")
                return
                
            metrics_json = json.dumps(metrics)
            
            try:
                cell = metrics_sheet.find(user_email)
                # Use batch update for multiple cells
                metrics_sheet.batch_update([
                    {'range': f'B{cell.row}', 'values': [[property_url]]},
                    {'range': f'C{cell.row}', 'values': [[metrics_json]]},
                    {'range': f'D{cell.row}', 'values': [[datetime.utcnow().isoformat()]]}
                ])
            except gspread.exceptions.GSpreadException:
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
            if not metrics_sheet:  # Demo mode
                print(f"[DEBUG] Demo mode - cannot get stored metrics for {user_email}")
                return None
                
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

    # REMOVED: All keyword analysis functions - not displayed on dashboard

class PageSpeedInsightsFetcher:
    """Handles fetching PageSpeed Insights data."""
    
    def __init__(self):
        self.api_key = settings.PAGESPEED_API_KEY
        self.base_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
        self.storage_key_prefix = "psi_metrics_"
        # Import here to avoid circular imports
        from app.database import GoogleSheetsDB
        self.db = GoogleSheetsDB()
    
    async def fetch_pagespeed_data(self, url: str, strategy: str = "mobile", raw: bool = False) -> Dict:
        """Fetch PageSpeed Insights data for a given URL with 30-day comparison."""
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
                        
                        # Process current data - only the 4 metrics displayed on dashboard
                        lh = data.get("lighthouseResult", {})
                        audits = lh.get("audits", {})
                        categories = lh.get("categories", {})
                        performance = categories.get("performance", {})
                        
                        current_metrics = {
                            "performance_score": round(performance.get("score", 0) * 100),
                            "lcp": {"value": audits.get("largest-contentful-paint", {}).get("numericValue", 0) / 1000},
                            "fcp": {"value": audits.get("first-contentful-paint", {}).get("numericValue", 0) / 1000},
                            "cls": {"value": audits.get("cumulative-layout-shift", {}).get("numericValue", 0)},
                        }
                        
                        # Add 30-day comparison
                        current_metrics = self._add_30_day_comparison(final_url, current_metrics)
                        
                        return current_metrics
                    else:
                        error_text = await response.text()
                        print(f"[ERROR] PageSpeed API error: {response.status}")
                        print(f"[ERROR] PageSpeed API response: {error_text}")
                        return self._get_demo_data()
                        
        except Exception as e:
            print(f"[ERROR] Error fetching PageSpeed data: {e}")
            return self._get_demo_data()
    
    def _add_30_day_comparison(self, url: str, current_metrics: Dict) -> Dict:
        """Add 30-day comparison to PageSpeed metrics."""
        try:
            # Get stored metrics from 30 days ago
            storage_key = f"{self.storage_key_prefix}{url}"
            stored_data = self.db.get_temp_data(storage_key)
            
            current_date = datetime.utcnow().date()
            comparison_date = current_date - timedelta(days=30)
            
            previous_metrics = None
            if stored_data:
                # Look for metrics from exactly 30 days ago (within 1 day tolerance)
                for stored_date_str, metrics in stored_data.items():
                    stored_date = datetime.strptime(stored_date_str, '%Y-%m-%d').date()
                    if abs((stored_date - comparison_date).days) <= 1:
                        previous_metrics = metrics
                        break
            
            if previous_metrics:
                # Calculate changes
                current_metrics['performance_score_change'] = current_metrics['performance_score'] - previous_metrics.get('performance_score', 0)
                current_metrics['lcp_change'] = current_metrics['lcp']['value'] - previous_metrics.get('lcp', {}).get('value', 0)
                current_metrics['fcp_change'] = current_metrics['fcp']['value'] - previous_metrics.get('fcp', {}).get('value', 0)
                current_metrics['cls_change'] = current_metrics['cls']['value'] - previous_metrics.get('cls', {}).get('value', 0)
                
                print(f"[DEBUG] PageSpeed 30-Day Comparison:")
                print(f"[DEBUG] - Performance Score: {current_metrics['performance_score']} vs {previous_metrics.get('performance_score', 0)} = {current_metrics['performance_score_change']:+}")
                print(f"[DEBUG] - LCP: {current_metrics['lcp']['value']:.2f}s vs {previous_metrics.get('lcp', {}).get('value', 0):.2f}s = {current_metrics['lcp_change']:+.2f}s")
                print(f"[DEBUG] - FCP: {current_metrics['fcp']['value']:.2f}s vs {previous_metrics.get('fcp', {}).get('value', 0):.2f}s = {current_metrics['fcp_change']:+.2f}s")
                print(f"[DEBUG] - CLS: {current_metrics['cls']['value']:.3f} vs {previous_metrics.get('cls', {}).get('value', 0):.3f} = {current_metrics['cls_change']:+.3f}")
            else:
                # No previous data - set changes to 0
                current_metrics['performance_score_change'] = 0
                current_metrics['lcp_change'] = 0
                current_metrics['fcp_change'] = 0
                current_metrics['cls_change'] = 0
                print(f"[DEBUG] No PageSpeed data from 30 days ago - showing zero changes")
            
            # Store current metrics for future comparison
            if not stored_data:
                stored_data = {}
            stored_data[current_date.strftime('%Y-%m-%d')] = {
                'performance_score': current_metrics['performance_score'],
                'lcp': current_metrics['lcp'],
                'fcp': current_metrics['fcp'],
                'cls': current_metrics['cls']
            }
            
            # Keep only last 60 days of data
            cutoff_date = current_date - timedelta(days=60)
            stored_data = {
                date_str: metrics for date_str, metrics in stored_data.items()
                if datetime.strptime(date_str, '%Y-%m-%d').date() >= cutoff_date
            }
            
            self.db.store_temp_data(storage_key, stored_data)
            
            return current_metrics
            
        except Exception as e:
            print(f"[ERROR] Error in PageSpeed 30-day comparison: {e}")
            # Return metrics without comparison data
            current_metrics['performance_score_change'] = 0
            current_metrics['lcp_change'] = 0
            current_metrics['fcp_change'] = 0
            current_metrics['cls_change'] = 0
            return current_metrics
    
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
        """Return empty data when API is not available - only displayed metrics."""
        return {
            'performance_score': 0,
            'performance_score_change': 0,
            'lcp': {'value': 0, 'score': 0},
            'lcp_change': 0,
            'fcp': {'value': 0, 'score': 0},
            'fcp_change': 0,
            'cls': {'value': 0, 'score': 0},
            'cls_change': 0,
            'last_updated': datetime.utcnow().isoformat()
        }

# REMOVED: MobileUsabilityFetcher class and all its methods - mobile metrics not displayed on dashboard
# REMOVED: IndexingCrawlabilityFetcher class - indexing metrics not displayed on dashboard  
# REMOVED: BusinessContextFetcher class - business metrics not displayed on dashboard

# Initialize the optimized components (only keeping PageSpeed fetcher for displayed UX metrics)
pagespeed_fetcher = PageSpeedInsightsFetcher() 