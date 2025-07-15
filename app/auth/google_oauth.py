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
from app.auth.models import UserInDB
from app.config import settings
import gspread
import aiohttp
import asyncio
from app.database.supabase_db import SupabaseAuthDB

class GoogleOAuthHandler:
    """Handles Google OAuth flow and Search Console API access."""
    
    def __init__(self, db):
        self.db = db
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        self.scopes = [
            "https://www.googleapis.com/auth/webmasters",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "openid"
        ]
        # Simple cache to reduce API calls
        self._credentials_cache = {}
        self._cache_timeout = 300  # 5 minutes
        
        # Check if we have valid Google credentials
        if not (self.client_id and self.client_secret and 
                             self.client_id != 'your_google_client_id_here' and 
                self.client_secret != 'your_google_client_secret_here'):
            raise Exception("Google OAuth credentials required. Cannot start Solvia without proper configuration.")
    
    def get_auth_url(self, state: str = None) -> str:
        """Generate Google OAuth authorization URL."""
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
        auth_url, generated_state = flow.authorization_url(state=state, prompt='select_account')
        return auth_url
    
    async def handle_callback(self, code: str, user_email: str, jwt_token: str = None) -> Dict:
        """Handle OAuth callback and store credentials."""
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
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Store credentials in Supabase using the user's JWT
        self._store_credentials(user_email, credentials, jwt_token=jwt_token)
        
        result = {
            "success": True,
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "expires_at": credentials.expiry.isoformat() if credentials.expiry else None
        }
        return result
    
    def _store_credentials(self, user_email: str, credentials: Credentials, jwt_token: str = None):
        """Store OAuth credentials in Supabase."""
        # Prepare credential data
        cred_data = {
            'email': user_email,
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token or '',
            'expires_at': credentials.expiry.isoformat() if credentials.expiry else None,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }

        # Use user-scoped Supabase client if jwt_token is provided
        if jwt_token:
            user_db = SupabaseAuthDB(access_token=jwt_token)
            response = user_db.supabase.table('gsc_connections').upsert(cred_data, on_conflict=['email']).execute()
        else:
            response = self.db.supabase.table('gsc_connections').upsert(cred_data, on_conflict=['email']).execute()

        # Cache the credentials
        cache_key = f"creds_{user_email}"
        self._credentials_cache[cache_key] = {
            'credentials': credentials,
            'timestamp': datetime.now()
        }
    
    def get_credentials(self, user_email: str) -> Optional[Credentials]:
        """Get stored OAuth credentials for user from Supabase."""
        
        # Check cache first
        cache_key = f"creds_{user_email}"
        if cache_key in self._credentials_cache:
            cached_data = self._credentials_cache[cache_key]
            if datetime.now() - cached_data['timestamp'] < timedelta(seconds=self._cache_timeout):
                return cached_data['credentials']
            else:
                # Cache expired, remove it
                del self._credentials_cache[cache_key]
        
        # Query Supabase for credentials
        response = self.db.supabase.table('gsc_connections').select('*').eq('email', user_email).execute()
        
        if not response.data or len(response.data) == 0:
            return None
        
        cred_row = response.data[0]
        refresh_token = cred_row.get('refresh_token')
        credentials = Credentials(
            token=cred_row.get('access_token'),
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.scopes
        )
        
        # Check if credentials are valid
        if not credentials.token:
            return None
        
        # Refresh token if expired and we have a refresh token
        if credentials.expired:
            if credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                    self._store_credentials(user_email, credentials)
                except Exception as refresh_error:
                    pass # No print statements here
        
        # Cache the credentials
        self._credentials_cache[cache_key] = {
            'credentials': credentials,
            'timestamp': datetime.now()
        }
        return credentials
    
    async def get_gsc_properties(self, user_email: str) -> List[Dict]:
        """Get user's Google Search Console properties."""
        credentials = self.get_credentials(user_email)
        if not credentials:
            return []
        try:
            # Build the Search Console API service
            service = build('searchconsole', 'v1', credentials=credentials)
            # Get the list of sites
            sites_list = service.sites().list().execute()
            if 'siteEntry' in sites_list:
                properties = []
                for site in sites_list['siteEntry']:
                    # Treat permissionLevel == 'siteOwner' as sufficient for ownership
                    is_owner = site.get('permissionLevel') == 'siteOwner'
                    properties.append({
                        'siteUrl': site['siteUrl'],
                        'permissionLevel': site['permissionLevel'],
                        'isVerified': is_owner
                    })
                return properties
            else:
                return []
        except Exception as e:
            return []

    def _clear_credentials(self, user_email: str):
        """Clear corrupted credentials for a user from Supabase."""
        try:
            # Delete credentials from Supabase
            self.db.supabase.table('gsc_connections').delete().eq('email', user_email).execute()
            # Clear from cache
            cache_key = f"creds_{user_email}"
            if cache_key in self._credentials_cache:
                del self._credentials_cache[cache_key]
        except Exception as e:
            pass # No print statements here

class GSCDataFetcher:
    """Handles fetching and storing GSC data."""
    
    def __init__(self, oauth_handler: GoogleOAuthHandler, db):
        self.oauth_handler = oauth_handler
        self.db = db
    
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
            
            # Add 30-day comparison changes to summary (preserving current values)
            current_summary['impressions_change'] = current_summary.get('total_impressions', 0) - comparison_summary.get('total_impressions', 0)
            current_summary['clicks_change'] = current_summary.get('total_clicks', 0) - comparison_summary.get('total_clicks', 0)
            current_summary['ctr_change'] = current_summary.get('avg_ctr', 0) - comparison_summary.get('avg_ctr', 0)
            current_summary['position_change'] = current_summary.get('avg_position', 0) - comparison_summary.get('avg_position', 0)
            
            # Calculate SEO score change based on 30-day comparison
            current_seo_score = self._calculate_simplified_seo_score(current_summary)
            previous_seo_score = self._calculate_simplified_seo_score(comparison_summary)
            current_summary['seo_score_change'] = current_seo_score - previous_seo_score
            
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
            # Check for common errors
            if e.resp.status == 403:
                pass # No print statements here
            if e.resp.status == 404:
                pass # No print statements here
            return {}
        except Exception as e:
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
            metrics_json = json.dumps(metrics)
            
            try:
                cell = self.db.get_or_create_sheet(
                    'gsc-metrics', 
                    headers=['user_email', 'property_url', 'metrics_json', 'last_updated']
                ).find(user_email)
                if cell:
                    # Use batch update for multiple cells
                    self.db.get_or_create_sheet(
                        'gsc-metrics', 
                        headers=['user_email', 'property_url', 'metrics_json', 'last_updated']
                    ).batch_update([
                        {'range': f'B{cell.row}', 'values': [[property_url]]},
                        {'range': f'C{cell.row}', 'values': [[metrics_json]]},
                        {'range': f'D{cell.row}', 'values': [[datetime.utcnow().isoformat()]]}
                    ])
                else:
                    # User not found, append a new row
                    self.db.get_or_create_sheet(
                        'gsc-metrics', 
                        headers=['user_email', 'property_url', 'metrics_json', 'last_updated']
                    ).append_row([
                        user_email,
                        property_url,
                        metrics_json,
                        datetime.utcnow().isoformat()
                    ])
            except gspread.exceptions.GSpreadException:
                self.db.get_or_create_sheet(
                    'gsc-metrics', 
                    headers=['user_email', 'property_url', 'metrics_json', 'last_updated']
                ).append_row([
                    user_email,
                    property_url,
                    metrics_json,
                    datetime.utcnow().isoformat()
                ])
        except Exception as e:
            pass # No print statements here
    
    async def get_stored_metrics(self, user_email: str, website_url: str) -> Optional[Dict]:
        """Get stored metrics for a user's website from Google Sheets."""
        try:
            cell = self.db.get_or_create_sheet(
                'gsc-metrics',
                headers=['user_email', 'property_url', 'metrics_json', 'last_updated']
            ).find(user_email)
            
            if cell:
                row_data = self.db.get_or_create_sheet(
                    'gsc-metrics',
                    headers=['user_email', 'property_url', 'metrics_json', 'last_updated']
                ).row_values(cell.row)
                if len(row_data) >= 3 and row_data[1] == website_url:
                    metrics_json = row_data[2]
                return {
                        "metrics": json.loads(metrics_json),
                        "last_updated": row_data[3] if len(row_data) > 3 else datetime.utcnow().isoformat()
                }
            return None
        except Exception as e:
            return None

    # REMOVED: All keyword analysis functions - not displayed on dashboard

# REMOVED: PageSpeedInsightsFetcher class and all its methods - no longer used in Solvia

# REMOVED: MobileUsabilityFetcher class and all its methods - mobile metrics not displayed on dashboard
# REMOVED: IndexingCrawlabilityFetcher class - indexing metrics not displayed on dashboard  
# REMOVED: BusinessContextFetcher class - business metrics not displayed on dashboard

# Initialize the optimized components (only keeping PageSpeed fetcher for displayed UX metrics) 