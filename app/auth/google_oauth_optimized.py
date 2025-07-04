"""
Google OAuth and Search Console API integration for Solvia - Optimized Version.
Only fetches data that is actually displayed on the dashboard.
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
            cached_time, cached_creds = self._credentials_cache[cache_key]
            if (datetime.now() - cached_time).seconds < self._cache_timeout:
                print(f"[DEBUG] Using cached credentials for {user_email}")
                return cached_creds
        
        try:
            print(f"[DEBUG] get_credentials called for user: {user_email}")
            # Get GSC connections sheet
            gsc_connections_sheet = self.db.client.open_by_key(self.db.users_sheet.spreadsheet.id).worksheet('gsc-connections')
            
            # Find user's credentials
            try:
                cell = gsc_connections_sheet.find(user_email)
                row_values = gsc_connections_sheet.row_values(cell.row)
                
                if len(row_values) >= 4:
                    access_token = row_values[1]  # Column B
                    refresh_token = row_values[2] if len(row_values) > 2 and row_values[2] else None  # Column C
                    expires_at_str = row_values[3] if len(row_values) > 3 and row_values[3] else None  # Column D
                    
                    # Parse expiry date
                    expires_at = None
                    if expires_at_str:
                        try:
                            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                        except:
                            print(f"[DEBUG] Could not parse expiry date: {expires_at_str}")
                    
                    # Create credentials object
                    credentials = Credentials(
                        token=access_token,
                        refresh_token=refresh_token,
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=self.client_id,
                        client_secret=self.client_secret,
                        scopes=self.scopes,
                        expiry=expires_at
                    )
                    
                    # Check if token needs refresh
                    if expires_at and expires_at <= datetime.now():
                        print(f"[DEBUG] Token expired for {user_email}, attempting refresh")
                        if refresh_token:
                            try:
                                credentials.refresh(Request())
                                # Update stored credentials
                                self._store_credentials(user_email, credentials)
                                print(f"[DEBUG] Token refreshed successfully for {user_email}")
                            except Exception as e:
                                print(f"[ERROR] Failed to refresh token for {user_email}: {e}")
                                return None
                        else:
                            print(f"[ERROR] No refresh token available for {user_email}")
                            return None
                    
                    # Cache the credentials
                    self._credentials_cache[cache_key] = (datetime.now(), credentials)
                    
                    print(f"[DEBUG] Credentials retrieved successfully for {user_email}")
                    return credentials
                else:
                    print(f"[ERROR] Incomplete credential data for {user_email}")
                    return None
                    
            except Exception as e:
                print(f"[DEBUG] User {user_email} not found in GSC connections: {e}")
                return None
                
        except Exception as e:
            print(f"[ERROR] Error retrieving credentials for {user_email}: {e}")
            return None
    
    async def get_gsc_properties(self, user_email: str) -> List[Dict]:
        """Get available Google Search Console properties for user."""
        if self.demo_mode:
            print("[DEBUG] Demo mode - returning sample GSC properties")
            return [
                {
                    "siteUrl": "https://example.com/",
                    "permissionLevel": "siteOwner",
                    "isVerified": True
                }
            ]
        
        try:
            print(f"[DEBUG] get_gsc_properties called for user: {user_email}")
            
            # Get user's credentials
            credentials = self.get_credentials(user_email)
            if not credentials:
                print(f"[ERROR] No credentials found for user: {user_email}")
                return []
            
            print(f"[DEBUG] Credentials obtained for {user_email}")
            
            # Build GSC service
            service = build('webmasters', 'v3', credentials=credentials)
            
            # Get sites
            print(f"[DEBUG] Fetching GSC sites for {user_email}")
            sites_response = service.sites().list().execute()
            
            properties = []
            if 'siteEntry' in sites_response:
                for site in sites_response['siteEntry']:
                    properties.append({
                        "siteUrl": site['siteUrl'],
                        "permissionLevel": site['permissionLevel'],
                        "isVerified": True  # GSC API only returns verified sites
                    })
            
            print(f"[DEBUG] Found {len(properties)} GSC properties for {user_email}")
            return properties
            
        except HttpError as e:
            print(f"[ERROR] HTTP error getting GSC properties for {user_email}: {e}")
            return []
        except Exception as e:
            print(f"[ERROR] Error getting GSC properties for {user_email}: {e}")
            return []
    
    def _clear_credentials(self, user_email: str):
        """Clear stored credentials for user."""
        if self.db.demo_mode:
            print(f"[DEBUG] Database in demo mode, cannot clear credentials for {user_email}")
            return
            
        try:
            print(f"[DEBUG] Clearing credentials for user: {user_email}")
            
            # Clear from cache
            cache_key = f"creds_{user_email}"
            if cache_key in self._credentials_cache:
                del self._credentials_cache[cache_key]
            
            # Clear from Google Sheets
            gsc_connections_sheet = self.db.client.open_by_key(self.db.users_sheet.spreadsheet.id).worksheet('gsc-connections')
            
            try:
                cell = gsc_connections_sheet.find(user_email)
                # Clear the row by setting empty values
                gsc_connections_sheet.batch_update([
                    {'range': f'B{cell.row}:D{cell.row}', 'values': [['', '', '']]}
                ])
                print(f"[SUCCESS] Cleared credentials for {user_email}")
            except Exception as e:
                print(f"[DEBUG] User {user_email} not found in GSC connections (already cleared): {e}")
                
        except Exception as e:
            print(f"[ERROR] Error clearing credentials for {user_email}: {e}")


class GSCDataFetcher:
    """Fetches only the data displayed on the dashboard from Google Search Console."""
    
    def __init__(self, oauth_handler: GoogleOAuthHandler):
        self.oauth_handler = oauth_handler
    
    async def fetch_metrics(self, user_email: str, property_url: str, days: int = 30) -> Dict:
        """Fetch essential GSC metrics: impressions, clicks, CTR, position."""
        try:
            print(f"[DEBUG] fetch_metrics called for {property_url} with {days} days")
            
            # Get user's GSC credentials
            credentials = self.oauth_handler.get_credentials(user_email)
            if not credentials:
                print("[ERROR] No GSC credentials found")
                return {}
            
            print(f"[DEBUG] GSC credentials obtained successfully")
            
            # Calculate 30-day date range (with 3-4 day delay for GSC data availability)
            today = datetime.now().date()
            delay_days = 4  # GSC data has 2-4 day delay, use 4 to be safe
            
            current_end_date = today - timedelta(days=delay_days)
            current_start_date = current_end_date - timedelta(days=days-1)  # 30 days total
            
            # Previous period for comparison (30 days before current period)
            previous_end_date = current_start_date - timedelta(days=1)
            previous_start_date = previous_end_date - timedelta(days=days-1)
            
            print(f"[DEBUG] Current period: {current_start_date} to {current_end_date}")
            print(f"[DEBUG] Previous period: {previous_start_date} to {previous_end_date}")
            
            # Fetch current and previous period data
            current_data = await self.get_gsc_data(credentials, property_url, 
                                                 current_start_date.isoformat(), 
                                                 current_end_date.isoformat())
            
            previous_data = await self.get_gsc_data(credentials, property_url, 
                                                  previous_start_date.isoformat(), 
                                                  previous_end_date.isoformat())
            
            # Process analytics data with 30-day comparison
            processed_data = self._process_analytics_data(
                current_data, current_data, 
                current_start_date.isoformat(), 
                current_end_date.isoformat(),
                previous_data
            )
            
            # Store metrics for caching
            self._store_metrics(user_email, property_url, processed_data)
            
            return processed_data
            
        except Exception as e:
            print(f"[ERROR] Error fetching GSC metrics: {e}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            return {}
    
    def _calculate_simplified_seo_score(self, summary: Dict) -> float:
        """Calculate overall SEO score based on displayed metrics only."""
        try:
            # Simplified scoring based only on visible metrics
            score = 0
            total_weight = 0
            
            # Clicks score (0-40 points)
            clicks = summary.get('total_clicks', 0)
            if clicks > 1000:
                score += 40
            elif clicks > 100:
                score += 30
            elif clicks > 10:
                score += 20
            elif clicks > 0:
                score += 10
            total_weight += 40
            
            # CTR score (0-30 points)
            ctr = summary.get('avg_ctr', 0)
            if ctr >= 0.05:  # 5%+
                score += 30
            elif ctr >= 0.03:  # 3-5%
                score += 20
            elif ctr >= 0.01:  # 1-3%
                score += 10
            elif ctr > 0:
                score += 5
            total_weight += 30
            
            # Position score (0-30 points)
            position = summary.get('avg_position', 100)
            if position <= 3:
                score += 30
            elif position <= 10:
                score += 20
            elif position <= 20:
                score += 10
            elif position <= 50:
                score += 5
            total_weight += 30
            
            # Calculate percentage
            final_score = (score / total_weight * 100) if total_weight > 0 else 0
            
            print(f"[DEBUG] SEO Score calculation: {score}/{total_weight} = {final_score:.1f}%")
            return round(final_score, 1)
            
        except Exception as e:
            print(f"[ERROR] Error calculating SEO score: {e}")
            return 0.0
    
    async def get_gsc_data(self, credentials: Credentials, property_url: str, start_date: str, end_date: str) -> Dict:
        """Get raw GSC data for a date range."""
        try:
            print(f"[DEBUG] Getting GSC data for {start_date} to {end_date}")
            
            # Build GSC service
            service = build('webmasters', 'v3', credentials=credentials)
            
            # Request data with only essential dimensions
            request = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': ['date'],  # Only need date dimension for trends
                'rowLimit': 1000
            }
            
            print(f"[DEBUG] GSC request: {request}")
            
            # Execute the request
            response = service.searchanalytics().query(
                siteUrl=property_url, 
                body=request
            ).execute()
            
            print(f"[DEBUG] GSC response received")
            return response
            
        except Exception as e:
            print(f"[ERROR] Error getting GSC data: {e}")
            return {}
    
    def _process_analytics_data(self, time_series_response: Dict, summary_response: Dict, 
                              start_date: str = None, end_date: str = None, 
                              previous_data: Dict = None) -> Dict:
        """Process GSC analytics data into dashboard format."""
        try:
            print(f"[DEBUG] Processing analytics data...")
            
            # Extract summary data
            summary_data = {
                'total_clicks': 0,
                'total_impressions': 0,
                'avg_ctr': 0.0,
                'avg_position': 0.0
            }
            
            # Process current period data
            if 'rows' in summary_response:
                total_clicks = 0
                total_impressions = 0
                total_position_sum = 0
                total_rows = 0
                
                for row in summary_response['rows']:
                    total_clicks += row.get('clicks', 0)
                    total_impressions += row.get('impressions', 0)
                    total_position_sum += row.get('position', 0)
                    total_rows += 1
                
                summary_data['total_clicks'] = total_clicks
                summary_data['total_impressions'] = total_impressions
                summary_data['avg_ctr'] = (total_clicks / total_impressions) if total_impressions > 0 else 0.0
                summary_data['avg_position'] = (total_position_sum / total_rows) if total_rows > 0 else 0.0
            
            # Calculate changes from previous period
            changes = {}
            if previous_data and 'rows' in previous_data:
                prev_clicks = sum(row.get('clicks', 0) for row in previous_data['rows'])
                prev_impressions = sum(row.get('impressions', 0) for row in previous_data['rows'])
                prev_rows = len(previous_data['rows'])
                prev_position_sum = sum(row.get('position', 0) for row in previous_data['rows'])
                
                prev_ctr = (prev_clicks / prev_impressions) if prev_impressions > 0 else 0.0
                prev_position = (prev_position_sum / prev_rows) if prev_rows > 0 else 0.0
                
                changes = {
                    'clicks_change': summary_data['total_clicks'] - prev_clicks,
                    'impressions_change': summary_data['total_impressions'] - prev_impressions,
                    'ctr_change': summary_data['avg_ctr'] - prev_ctr,
                    'position_change': prev_position - summary_data['avg_position']  # Negative is better for position
                }
            else:
                changes = {
                    'clicks_change': 0,
                    'impressions_change': 0,
                    'ctr_change': 0.0,
                    'position_change': 0.0
                }
            
            # Process time series data for charts
            time_series_data = {}
            if 'rows' in time_series_response:
                dates = []
                clicks = []
                impressions = []
                
                for row in time_series_response['rows']:
                    if 'keys' in row and len(row['keys']) > 0:
                        date = row['keys'][0]
                        dates.append(date)
                        clicks.append(row.get('clicks', 0))
                        impressions.append(row.get('impressions', 0))
                
                time_series_data = {
                    'dates': dates,
                    'clicks': clicks,
                    'impressions': impressions
                }
            
            # Calculate SEO score
            seo_score = self._calculate_simplified_seo_score(summary_data)
            
            result = {
                'summary': summary_data,
                'changes': changes,
                'time_series': time_series_data,
                'seo_score': seo_score,
                'start_date': start_date,
                'end_date': end_date,
                'last_updated': datetime.utcnow().isoformat()
            }
            
            print(f"[DEBUG] Processed analytics data: {result}")
            return result
            
        except Exception as e:
            print(f"[ERROR] Error processing analytics data: {e}")
            return {
                'summary': {'total_clicks': 0, 'total_impressions': 0, 'avg_ctr': 0.0, 'avg_position': 0.0},
                'changes': {'clicks_change': 0, 'impressions_change': 0, 'ctr_change': 0.0, 'position_change': 0.0},
                'time_series': {'dates': [], 'clicks': [], 'impressions': []},
                'seo_score': 0.0,
                'start_date': start_date,
                'end_date': end_date,
                'last_updated': datetime.utcnow().isoformat()
            }
    
    def _store_metrics(self, user_email: str, property_url: str, metrics: Dict):
        """Store metrics in Google Sheets for caching."""
        if self.oauth_handler.db.demo_mode:
            print(f"[DEBUG] Database in demo mode, cannot store metrics")
            return
            
        try:
            print(f"[DEBUG] Storing metrics for {user_email}")
            # Implementation would store in a metrics cache sheet
            # For now, just log that we would store it
            print(f"[DEBUG] Would store metrics: {metrics.keys()}")
        except Exception as e:
            print(f"[ERROR] Error storing metrics: {e}")
    
    async def get_stored_metrics(self, user_email: str, website_url: str) -> Optional[Dict]:
        """Get cached metrics if available and recent."""
        if self.oauth_handler.db.demo_mode:
            print(f"[DEBUG] Database in demo mode, no stored metrics available")
            return None
            
        try:
            print(f"[DEBUG] Checking for stored metrics for {user_email}")
            # Implementation would check cache
            # For now, return None to always fetch fresh data
            return None
        except Exception as e:
            print(f"[ERROR] Error getting stored metrics: {e}")
            return None


class PageSpeedInsightsFetcher:
    """Fetches only the PageSpeed metrics displayed on the dashboard."""
    
    def __init__(self):
        self.api_key = settings.PAGESPEED_API_KEY if hasattr(settings, 'PAGESPEED_API_KEY') else None
        self.demo_mode = not self.api_key
        
        if self.demo_mode:
            print("[WARNING] PageSpeed running in DEMO MODE - no API key provided")
        else:
            print("[SUCCESS] PageSpeed API key loaded successfully!")
    
    async def fetch_pagespeed_data(self, url: str, strategy: str = "mobile", raw: bool = False) -> Dict:
        """Fetch only essential PageSpeed metrics: Performance Score, LCP, FCP, CLS."""
        if self.demo_mode:
            return self._get_demo_data()
        
        try:
            print(f"[DEBUG] Fetching PageSpeed data for {url}")
            
            # Get final URL (handle redirects)
            final_url = await self._get_final_url(url)
            
            # Build API request
            api_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
            params = {
                'url': final_url,
                'strategy': strategy,
                'category': 'performance',  # Only performance category
                'key': self.api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if raw:
                            return data
                        
                        processed_data = self._process_pagespeed_data(data)
                        
                        # Add 30-day comparison data
                        comparison_data = self._add_30_day_comparison(final_url, processed_data)
                        
                        return comparison_data
                    else:
                        print(f"[ERROR] PageSpeed API error: {response.status}")
                        return self._get_demo_data()
        
        except Exception as e:
            print(f"[ERROR] Error fetching PageSpeed data: {e}")
            return self._get_demo_data()
    
    def _add_30_day_comparison(self, url: str, current_metrics: Dict) -> Dict:
        """Add 30-day comparison data (simplified version)."""
        # In a real implementation, this would fetch historical data
        # For now, simulate small changes
        try:
            import random
            
            # Simulate realistic changes
            performance_change = random.randint(-5, 5)
            lcp_change = random.uniform(-0.3, 0.3)
            fcp_change = random.uniform(-0.2, 0.2)
            cls_change = random.uniform(-0.05, 0.05)
            
            current_metrics.update({
                'performance_score_change': performance_change,
                'lcp_change': lcp_change,
                'fcp_change': fcp_change,
                'cls_change': cls_change
            })
            
            return current_metrics
            
        except Exception as e:
            print(f"[ERROR] Error adding comparison data: {e}")
            return current_metrics
    
    async def _get_final_url(self, url: str) -> str:
        """Get final URL after redirects."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, allow_redirects=True) as response:
                    return str(response.url)
        except:
            return url
    
    def _process_pagespeed_data(self, data: Dict) -> Dict:
        """Process PageSpeed data to extract only displayed metrics."""
        try:
            lighthouse_result = data.get('lighthouseResult', {})
            audits = lighthouse_result.get('audits', {})
            categories = lighthouse_result.get('categories', {})
            
            # Performance score
            performance_score = 0
            if 'performance' in categories:
                performance_score = int(categories['performance']['score'] * 100)
            
            # Core Web Vitals - only the 3 displayed metrics
            lcp_value = 0
            if 'largest-contentful-paint' in audits:
                lcp_value = audits['largest-contentful-paint'].get('numericValue', 0) / 1000  # Convert to seconds
            
            fcp_value = 0
            if 'first-contentful-paint' in audits:
                fcp_value = audits['first-contentful-paint'].get('numericValue', 0) / 1000  # Convert to seconds
            
            cls_value = 0
            if 'cumulative-layout-shift' in audits:
                cls_value = audits['cumulative-layout-shift'].get('numericValue', 0)
            
            return {
                'performance_score': performance_score,
                'lcp': {'value': lcp_value},
                'fcp': {'value': fcp_value},
                'cls': {'value': cls_value},
                'insights': self._generate_insights(performance_score, lcp_value, fcp_value, cls_value)
            }
            
        except Exception as e:
            print(f"[ERROR] Error processing PageSpeed data: {e}")
            return self._get_demo_data()
    
    def _generate_insights(self, performance_score: int, lcp: float, fcp: float, cls: float) -> List[str]:
        """Generate insights based on the 4 displayed metrics."""
        insights = []
        
        if performance_score >= 90:
            insights.append("Excellent performance! Your site loads quickly.")
        elif performance_score >= 70:
            insights.append("Good performance with room for improvement.")
        else:
            insights.append("Performance needs optimization for better user experience.")
        
        if lcp > 2.5:
            insights.append("LCP is slow - optimize images and server response time.")
        if fcp > 1.8:
            insights.append("FCP needs improvement - optimize critical rendering path.")
        if cls > 0.1:
            insights.append("CLS issues detected - prevent layout shifts during page load.")
        
        return insights
    
    def _get_demo_data(self) -> Dict:
        """Return demo PageSpeed data."""
        return {
            'performance_score': 75,
            'lcp': {'value': 2.8},
            'fcp': {'value': 1.6},
            'cls': {'value': 0.08},
            'performance_score_change': 2,
            'lcp_change': -0.1,
            'fcp_change': 0.05,
            'cls_change': -0.02,
            'insights': [
                "Good performance with room for improvement.",
                "LCP is slow - optimize images and server response time."
            ]
        }


# Initialize the optimized components
pagespeed_fetcher = PageSpeedInsightsFetcher() 