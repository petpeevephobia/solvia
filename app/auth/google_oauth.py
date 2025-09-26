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
# import gspread  # No longer needed - migrated to Supabase
# import aiohttp  # Only needed for web scraping feature
import asyncio
from app.database.supabase_db import SupabaseAuthDB
from supabase import create_client
from app.config import settings

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

        # Device trust cache for remembering devices
        self._trusted_devices_cache = {}
        self._device_trust_timeout = 2592000  # 30 days in seconds

        # Check if we have valid Google credentials
        if not (self.client_id and self.client_secret and
                self.client_id != 'your_google_client_id_here' and
                self.client_secret != 'your_google_client_secret_here'):
            raise Exception("Google OAuth credentials required. Cannot start Solvia without proper configuration.")
    
    def get_auth_url(self, state: str = None, remember_device: bool = False) -> str:
        """Generate Google OAuth authorization URL with device remembering support."""
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

        # CRITICAL: access_type='offline' is required to get refresh tokens
        # Device remembering logic:
        # - For returning users with trusted devices: prompt='none' (skip consent)
        # - For new devices or forced re-auth: prompt='consent' to ensure refresh tokens
        # Note: Using 'consent' instead of 'select_account' to force consent screen and get refresh tokens
        prompt_value = 'none' if remember_device else 'consent'

        print(f"[OAUTH URL] 🔧 Generating OAuth URL with parameters:")
        print(f"[OAUTH URL]   - prompt: {prompt_value}")
        print(f"[OAUTH URL]   - access_type: offline")
        print(f"[OAUTH URL]   - remember_device: {remember_device}")

        auth_url, generated_state = flow.authorization_url(
            state=state,
            prompt=prompt_value,
            access_type='offline',
            # Enable incremental authorization to reduce consent friction
            include_granted_scopes='true'
        )
        return auth_url

    def generate_device_fingerprint(self, request_headers: dict, user_agent: str = None, ip_address: str = None) -> str:
        """Generate a unique device fingerprint for device remembering."""
        import hashlib

        # Extract key identifying information
        user_agent = user_agent or request_headers.get('user-agent', '')
        accept_language = request_headers.get('accept-language', '')
        accept_encoding = request_headers.get('accept-encoding', '')

        # Create fingerprint from stable browser characteristics
        fingerprint_data = f"{user_agent}|{accept_language}|{accept_encoding}|{ip_address or 'unknown'}"

        # Generate SHA-256 hash for fingerprint
        fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()[:32]

        return fingerprint

    def is_device_trusted(self, user_email: str, device_fingerprint: str) -> bool:
        """Check if a device is trusted for the user."""
        cache_key = f"trust_{user_email}_{device_fingerprint}"

        # Check memory cache first
        if cache_key in self._trusted_devices_cache:
            trust_data = self._trusted_devices_cache[cache_key]
            if (datetime.now() - trust_data['timestamp']).total_seconds() < self._device_trust_timeout:
                return True
            else:
                # Trust expired, remove from cache
                del self._trusted_devices_cache[cache_key]

        # Check database for persistent trust
        try:
            service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY
            if service_role_key:
                service_db = create_client(settings.SUPABASE_URL, service_role_key)
                response = service_db.table('trusted_devices').select('*').eq('user_email', user_email).eq('device_fingerprint', device_fingerprint).execute()

                if response.data and len(response.data) > 0:
                    trust_record = response.data[0]
                    created_at = datetime.fromisoformat(trust_record['created_at'].replace('Z', '+00:00'))

                    # Check if trust hasn't expired (30 days)
                    if (datetime.now(created_at.tzinfo) - created_at).total_seconds() < self._device_trust_timeout:
                        # Cache for quick access
                        self._trusted_devices_cache[cache_key] = {
                            'timestamp': datetime.now(),
                            'trusted': True
                        }
                        return True
                    else:
                        # Remove expired trust record
                        service_db.table('trusted_devices').delete().eq('id', trust_record['id']).execute()
        except Exception as e:
            print(f"[DEVICE TRUST] Error checking device trust: {e}")

        return False

    def mark_device_trusted(self, user_email: str, device_fingerprint: str, user_agent: str = None):
        """Mark a device as trusted for 30 days."""
        cache_key = f"trust_{user_email}_{device_fingerprint}"

        # Cache in memory
        self._trusted_devices_cache[cache_key] = {
            'timestamp': datetime.now(),
            'trusted': True
        }

        # Store in database for persistence
        try:
            service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY
            if service_role_key:
                service_db = create_client(settings.SUPABASE_URL, service_role_key)

                trust_data = {
                    'user_email': user_email,
                    'device_fingerprint': device_fingerprint,
                    'user_agent': user_agent or 'unknown',
                    'created_at': datetime.utcnow().isoformat(),
                    'expires_at': (datetime.utcnow() + timedelta(seconds=self._device_trust_timeout)).isoformat()
                }

                # Upsert the trust record
                service_db.table('trusted_devices').upsert(trust_data, on_conflict='user_email,device_fingerprint').execute()
                print(f"[DEVICE TRUST] Device marked as trusted for {user_email}")
        except Exception as e:
            print(f"[DEVICE TRUST] Error storing device trust: {e}")

    async def handle_callback(self, code: str, jwt_token: str = None) -> Dict:
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
        
        # Get the actual user email from Google OAuth response
        actual_user_email = await self._get_user_email_from_credentials(credentials)
        
        if not actual_user_email:
            raise Exception("Could not retrieve user email from Google credentials.")
        
        # Store credentials in Supabase using the user's JWT
        self._store_credentials(actual_user_email, credentials, jwt_token=jwt_token)
        
        result = {
            "success": True,
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "expires_at": credentials.expiry.isoformat() if credentials.expiry else None,
            "email": actual_user_email
        }
        return result
    
    def _store_credentials(self, user_email: str, credentials: Credentials, jwt_token: str = None):
        """Store OAuth credentials in Supabase using service role key."""
        print(f"[CREDENTIALS STORE] 🏗️ Storing credentials for {user_email}")
        print(f"[CREDENTIALS STORE] 📊 Credential details received from Google:")
        print(f"[CREDENTIALS STORE]   - Has access_token: {'Yes' if credentials.token else 'No'}")
        print(f"[CREDENTIALS STORE]   - Has refresh_token: {'Yes' if credentials.refresh_token else 'No'}")
        print(f"[CREDENTIALS STORE]   - Token expiry: {credentials.expiry}")
        print(f"[CREDENTIALS STORE]   - Token URI: {credentials.token_uri}")
        print(f"[CREDENTIALS STORE]   - Client ID: {credentials.client_id}")
        print(f"[CREDENTIALS STORE]   - Scopes: {credentials.scopes}")

        if not credentials.refresh_token:
            print(f"[CREDENTIALS STORE] ⚠️ WARNING: Google did not provide a refresh token!")
            print(f"[CREDENTIALS STORE] 🔧 This means automatic token refresh will not work")
            print(f"[CREDENTIALS STORE] 💡 User will need to re-authenticate when token expires")

        # Prepare credential data
        cred_data = {
            'email': user_email,
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token or '',
            'expires_at': credentials.expiry.isoformat() if credentials.expiry else None,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        print(f"[CREDENTIALS STORE] 💾 Data to store: {cred_data}")
        
        try:
            # Always use service role key to bypass RLS for credential storage
            service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY
            if service_role_key:
                print(f"[CREDENTIALS STORE] Using service role key for storage")
                service_db = create_client(settings.SUPABASE_URL, service_role_key)
                response = service_db.table('gsc_connections').upsert(cred_data, on_conflict=['email']).execute()
                if response.data:
                    print(f"[CREDENTIALS STORE] Successfully stored credentials for {user_email}")
                else:
                    print(f"[CREDENTIALS STORE] No response data when storing credentials")
            else:
                # Fallback to JWT token if provided
                if jwt_token:
                    print(f"[CREDENTIALS STORE] No service role key, using JWT token")
                    user_db = SupabaseAuthDB(access_token=jwt_token)
                    response = user_db.supabase.table('gsc_connections').upsert(cred_data, on_conflict=['email']).execute()
                    print(f"[CREDENTIALS STORE] Successfully stored with JWT token")
                else:
                    print(f"[CREDENTIALS STORE] ERROR: No service role key or JWT token available")
                    response = None
        except Exception as e:
            print(f"[CREDENTIALS STORE] Error storing credentials: {e}")
            response = None

        # Clear the cache so fresh credentials are fetched from database
        cache_key = f"creds_{user_email}"
        if cache_key in self._credentials_cache:
            del self._credentials_cache[cache_key]
            print(f"[CREDENTIALS STORE] Cleared cache for {user_email} to force fresh fetch")
        
    
    async def _get_user_email_from_credentials(self, credentials: Credentials) -> Optional[str]:
        """Get user email from Google OAuth credentials."""
        try:
            # Build the userinfo service
            service = build('oauth2', 'v2', credentials=credentials)
            
            # Get user info
            user_info = service.userinfo().get().execute()
            
            # Extract email
            email = user_info.get('email')
            return email
        except Exception as e:
            print(f"Error getting user email from credentials: {e}")
            return None
    
    def get_credentials(self, user_email: str) -> Optional[Credentials]:
        """Get stored OAuth credentials for user from Supabase."""
        
        print(f"[CREDENTIALS DEBUG] Getting credentials for {user_email}")
        
        # Check cache first
        cache_key = f"creds_{user_email}"
        if cache_key in self._credentials_cache:
            cached_data = self._credentials_cache[cache_key]
            if datetime.now() - cached_data['timestamp'] < timedelta(seconds=self._cache_timeout):
                print(f"[CREDENTIALS DEBUG] Found credentials in cache for {user_email}")
                return cached_data['credentials']
            else:
                # Cache expired, remove it
                del self._credentials_cache[cache_key]
                print(f"[CREDENTIALS DEBUG] Cache expired for {user_email}")
        
        print(f"[CREDENTIALS DEBUG] Querying Supabase for credentials for {user_email}")
        
        # Use service role key to bypass RLS when reading credentials
        service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY
        if service_role_key:
            print(f"[CREDENTIALS DEBUG] Using service role key to bypass RLS")
            from supabase import create_client
            service_supabase = create_client(settings.SUPABASE_URL, service_role_key)
            response = service_supabase.table('gsc_connections').select('*').eq('email', user_email).execute()
        else:
            print(f"[CREDENTIALS DEBUG] No service role key available, using standard client")
            response = self.db.supabase.table('gsc_connections').select('*').eq('email', user_email).execute()
        
        print(f"[CREDENTIALS DEBUG] Supabase response: {response.data}")
        
        if not response.data or len(response.data) == 0:
            print(f"[CREDENTIALS DEBUG] No credentials found in Supabase for {user_email}")
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
            print(f"[CREDENTIALS DEBUG] No access token found for {user_email}")
            return None

        # Check if credentials are expired - if so, don't cache them
        # Let verify_gsc_credentials() handle refresh logic comprehensively
        if credentials.expired:
            print(f"[CREDENTIALS DEBUG] Credentials expired for {user_email}, not caching")
            # Don't cache expired credentials - let verify_gsc_credentials handle refresh
            return credentials

        # Only cache valid, non-expired credentials
        self._credentials_cache[cache_key] = {
            'credentials': credentials,
            'timestamp': datetime.now()
        }
        print(f"[CREDENTIALS DEBUG] Cached valid credentials for {user_email}")
        return credentials
    
    async def get_gsc_properties(self, user_email: str) -> List[Dict]:
        """Get user's Google Search Console properties."""
        print(f"[GSC OAUTH] Getting properties for user: {user_email}")
        
        credentials = self.get_credentials(user_email)
        if not credentials:
            print(f"[GSC OAUTH] No credentials found for user: {user_email}")
            return []
        
        print(f"[GSC OAUTH] Credentials found, building service...")
        
        try:
            # Build the Search Console API service
            service = build('searchconsole', 'v1', credentials=credentials)
            print(f"[GSC OAUTH] Service built successfully")
            
            # Get the list of sites
            print(f"[GSC OAUTH] Fetching sites list...")
            try:
                sites_list = service.sites().list().execute()
            except AttributeError as attr_error:
                print(f"[GSC OAUTH] AttributeError with sites: {attr_error}")
                # Try alternative method
                sites_list = service.sites().list().execute()
            print(f"[GSC OAUTH] Sites list response: {sites_list}")
            
            if 'siteEntry' in sites_list:
                properties = []
                for site in sites_list['siteEntry']:
                    # Treat permissionLevel == 'siteOwner' as sufficient for ownership
                    is_owner = site.get('permissionLevel') == 'siteOwner'
                    
                    # Extract account name from user email
                    account_name = user_email.split('@')[0]
                    account_name = account_name.replace('.', ' ').replace('_', ' ')
                    account_name = ' '.join(word.capitalize() for word in account_name.split())
                    
                    property_data = {
                        'siteUrl': site['siteUrl'],
                        'permissionLevel': site['permissionLevel'],
                        'isVerified': is_owner,
                        'accountEmail': user_email,
                        'accountName': account_name
                    }
                    properties.append(property_data)
                    print(f"[GSC OAUTH] Added property: {property_data}")
                
                print(f"[GSC OAUTH] Returning {len(properties)} properties")
                return properties
            else:
                print(f"[GSC OAUTH] No siteEntry found in response")
                return []
        except Exception as e:
            print(f"[GSC OAUTH] Error getting GSC properties: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _clear_credentials(self, user_email: str):
        """Clear corrupted credentials for a user from Supabase."""
        try:
            print(f"[CREDENTIALS CLEAR] Clearing credentials for {user_email}")

            # Use service role key to bypass RLS when clearing credentials
            service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY
            if service_role_key:
                from supabase import create_client
                service_supabase = create_client(settings.SUPABASE_URL, service_role_key)
                service_supabase.table('gsc_connections').delete().eq('email', user_email).execute()
                print(f"[CREDENTIALS CLEAR] Cleared from database for {user_email}")
            else:
                # Fallback to regular client
                self.db.supabase.table('gsc_connections').delete().eq('email', user_email).execute()
                print(f"[CREDENTIALS CLEAR] Cleared from database (fallback) for {user_email}")

            # Clear from cache
            cache_key = f"creds_{user_email}"
            if cache_key in self._credentials_cache:
                del self._credentials_cache[cache_key]
                print(f"[CREDENTIALS CLEAR] Cleared from cache for {user_email}")

        except Exception as e:
            print(f"[CREDENTIALS CLEAR] Error clearing credentials for {user_email}: {e}")

    def _expire_credentials_for_testing(self, user_email: str):
        """Expire credentials (for testing refresh functionality) without deleting refresh tokens."""
        try:
            print(f"[CREDENTIALS EXPIRE] 🧪 Starting credential expiry for testing refresh for {user_email}")

            # Use service role key to bypass RLS
            service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY
            if service_role_key:
                print(f"[CREDENTIALS EXPIRE] 🔑 Using service role key for database access")
                from supabase import create_client
                service_supabase = create_client(settings.SUPABASE_URL, service_role_key)

                # Set expiry to 1 hour ago to simulate expired token
                from datetime import datetime, timedelta
                expired_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()
                current_time = datetime.utcnow().isoformat()

                print(f"[CREDENTIALS EXPIRE] ⏰ Setting token expiry to: {expired_time} (1 hour ago)")
                print(f"[CREDENTIALS EXPIRE] 📅 Current time: {current_time}")

                # First, let's check what's currently in the database
                current_response = service_supabase.table('gsc_connections').select('*').eq('email', user_email).execute()
                if current_response.data:
                    current_creds = current_response.data[0]
                    print(f"[CREDENTIALS EXPIRE] 📊 Current credential status:")
                    print(f"[CREDENTIALS EXPIRE]   - Has access_token: {'Yes' if current_creds.get('access_token') else 'No'}")
                    print(f"[CREDENTIALS EXPIRE]   - Has refresh_token: {'Yes' if current_creds.get('refresh_token') else 'No'}")
                    print(f"[CREDENTIALS EXPIRE]   - Current expires_at: {current_creds.get('expires_at')}")

                # Update only the expires_at field, keeping refresh_token intact
                update_data = {
                    'expires_at': expired_time,
                    'updated_at': current_time
                }

                print(f"[CREDENTIALS EXPIRE] 💾 Updating database with expired time...")
                update_response = service_supabase.table('gsc_connections').update(update_data).eq('email', user_email).execute()
                print(f"[CREDENTIALS EXPIRE] 💾 Database update response: {update_response.data}")

                # Verify the update worked
                verify_response = service_supabase.table('gsc_connections').select('*').eq('email', user_email).execute()
                if verify_response.data:
                    updated_creds = verify_response.data[0]
                    print(f"[CREDENTIALS EXPIRE] ✅ Verification - Updated credential status:")
                    print(f"[CREDENTIALS EXPIRE]   - New expires_at: {updated_creds.get('expires_at')}")
                    print(f"[CREDENTIALS EXPIRE]   - Refresh token preserved: {'Yes' if updated_creds.get('refresh_token') else 'No'}")

            else:
                print(f"[CREDENTIALS EXPIRE] ⚠️ No service role key, using regular client")
                # Fallback to regular client
                from datetime import datetime, timedelta
                expired_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()

                update_data = {
                    'expires_at': expired_time,
                    'updated_at': datetime.utcnow().isoformat()
                }

                self.db.supabase.table('gsc_connections').update(update_data).eq('email', user_email).execute()
                print(f"[CREDENTIALS EXPIRE] Set credentials to expired (fallback) for {user_email}")

            # Clear from cache so fresh (expired) credentials are fetched
            cache_key = f"creds_{user_email}"
            if cache_key in self._credentials_cache:
                del self._credentials_cache[cache_key]
                print(f"[CREDENTIALS EXPIRE] 🧹 Cleared cache for {user_email}")
            else:
                print(f"[CREDENTIALS EXPIRE] 🧹 No cache entry found for {user_email}")

            print(f"[CREDENTIALS EXPIRE] 🎉 ✅ Successfully expired credentials for testing for {user_email}")

        except Exception as e:
            print(f"[CREDENTIALS EXPIRE] 💥 ❌ Error expiring credentials for {user_email}: {e}")
            import traceback
            print(f"[CREDENTIALS EXPIRE] 📜 Full error traceback:")
            traceback.print_exc()

    def clear_credentials_cache(self, user_email: str):
        """Clear credentials cache for a user (useful after refresh operations)."""
        cache_key = f"creds_{user_email}"
        if cache_key in self._credentials_cache:
            del self._credentials_cache[cache_key]
            print(f"[CREDENTIALS CACHE] Cleared cache for {user_email}")
    
    def get_gsc_metrics(self, user_email: str, website_url: str, date_range: dict = None) -> dict:
        """Get Google Search Console metrics for a specific website."""
        print(f"[GSC OAUTH] Getting metrics for {user_email} on {website_url}")
        
        credentials = self.get_credentials(user_email)
        if not credentials:
            print(f"[GSC OAUTH] No credentials found for user: {user_email}")
            raise Exception("No credentials found")
        
        try:
            # Build the Search Console API service
            service = build('searchconsole', 'v1', credentials=credentials)
            
            # Set default date range if not provided
            if not date_range:
                from datetime import datetime, timedelta
                end_date = datetime.now().date() - timedelta(days=1)  # GSC data available until yesterday
                start_date = end_date - timedelta(days=30)
                date_range = {
                    'start_date': start_date,
                    'end_date': end_date
                }
            
            # First, get summary data (no dimensions) to get accurate CTR
            summary_request = {
                'startDate': date_range['start_date'].strftime('%Y-%m-%d'),
                'endDate': date_range['end_date'].strftime('%Y-%m-%d')
            }
            
            print(f"[GSC OAUTH] Fetching summary data for date range: {summary_request['startDate']} to {summary_request['endDate']}")
            
            # Execute the summary request
            try:
                print(f"[GSC API CALL] ⚡ Making summary request to Google: {summary_request}")
                summary_response = service.searchAnalytics().query(
                    siteUrl=website_url,
                    body=summary_request
                ).execute()
                print(f"[GSC API RESPONSE] 📊 Google summary response: {summary_response}")
            except AttributeError as attr_error:
                print(f"[GSC OAUTH] AttributeError with searchAnalytics: {attr_error}")
                # Try alternative method
                print(f"[GSC API CALL] ⚡ Making summary request (fallback) to Google: {summary_request}")
                summary_response = service.searchanalytics().query(
                    siteUrl=website_url,
                    body=summary_request
                ).execute()
                print(f"[GSC API RESPONSE] 📊 Google summary response (fallback): {summary_response}")
            
            # Get detailed data for other metrics
            detailed_request = {
                'startDate': date_range['start_date'].strftime('%Y-%m-%d'),
                'endDate': date_range['end_date'].strftime('%Y-%m-%d'),
                'dimensions': ['query', 'page'],
                'rowLimit': 1000
            }
            
            # Execute the detailed request
            try:
                print(f"[GSC API CALL] ⚡ Making detailed request to Google: {detailed_request}")
                detailed_response = service.searchAnalytics().query(
                    siteUrl=website_url,
                    body=detailed_request
                ).execute()
                print(f"[GSC API RESPONSE] 📊 Google detailed response: {detailed_response}")
            except AttributeError as attr_error:
                print(f"[GSC OAUTH] AttributeError with searchAnalytics: {attr_error}")
                # Try alternative method
                print(f"[GSC API CALL] ⚡ Making detailed request (fallback) to Google: {detailed_request}")
                detailed_response = service.searchanalytics().query(
                    siteUrl=website_url,
                    body=detailed_request
                ).execute()
                print(f"[GSC API RESPONSE] 📊 Google detailed response (fallback): {detailed_response}")
            
            # Calculate metrics using summary data for accurate CTR
            metrics = self._calculate_metrics_with_summary(summary_response, detailed_response.get('rows', []))
            
            print(f"[GSC OAUTH] Successfully fetched metrics: {metrics}")
            return metrics
            
        except Exception as e:
            error_str = str(e).lower()
            print(f"[GSC OAUTH] Error getting GSC metrics: {e}")

            # ULTRATHINK AUTOMATIC RETRY: Check for 401/authentication errors
            if '401' in error_str or 'unauthorized' in error_str or 'invalid_grant' in error_str or 'credentials' in error_str:
                print(f"[GSC OAUTH AUTO-RETRY] 🔄 401/Auth error detected, attempting automatic token refresh...")

                try:
                    # Try to refresh credentials automatically
                    from app.auth.utils import verify_gsc_credentials

                    print(f"[GSC OAUTH AUTO-RETRY] 🚀 Calling verify_gsc_credentials for automatic refresh...")
                    refresh_success = verify_gsc_credentials(user_email)

                    if refresh_success:
                        print(f"[GSC OAUTH AUTO-RETRY] 🎉 ✅ Automatic refresh successful! Retrying GSC API call...")

                        # Get fresh credentials and retry the API call
                        fresh_credentials = self.get_credentials(user_email)
                        if fresh_credentials:
                            print(f"[GSC OAUTH AUTO-RETRY] 🔄 Retrying API call with fresh credentials...")

                            # Rebuild service with fresh credentials
                            service = build('searchconsole', 'v1', credentials=fresh_credentials)

                            # Retry the summary request
                            try:
                                print(f"[GSC OAUTH AUTO-RETRY] ⚡ Retry: Making summary request to Google: {summary_request}")
                                summary_response = service.searchAnalytics().query(
                                    siteUrl=website_url,
                                    body=summary_request
                                ).execute()
                                print(f"[GSC OAUTH AUTO-RETRY] 📊 Retry: Google summary response: {summary_response}")

                                # Retry the detailed request
                                print(f"[GSC OAUTH AUTO-RETRY] ⚡ Retry: Making detailed request to Google: {detailed_request}")
                                detailed_response = service.searchAnalytics().query(
                                    siteUrl=website_url,
                                    body=detailed_request
                                ).execute()
                                print(f"[GSC OAUTH AUTO-RETRY] 📊 Retry: Google detailed response: {detailed_response}")

                                # Calculate metrics with the retry data
                                metrics = self._calculate_metrics_with_summary(summary_response, detailed_response.get('rows', []))
                                print(f"[GSC OAUTH AUTO-RETRY] 🎉 ✅ Retry successful! Returning metrics: {metrics}")
                                return metrics

                            except Exception as retry_error:
                                print(f"[GSC OAUTH AUTO-RETRY] 💥 ❌ Retry API call failed: {retry_error}")
                        else:
                            print(f"[GSC OAUTH AUTO-RETRY] 💥 ❌ Could not get fresh credentials after refresh")
                    else:
                        print(f"[GSC OAUTH AUTO-RETRY] 💥 ❌ Automatic refresh failed")

                except Exception as retry_exception:
                    print(f"[GSC OAUTH AUTO-RETRY] 💥 ❌ Exception during automatic retry: {retry_exception}")

                print(f"[GSC OAUTH AUTO-RETRY] 💥 ❌ All retry attempts failed, returning empty metrics")

            return self._get_empty_metrics()
    
    def _calculate_metrics_with_summary(self, summary_response: dict, detailed_rows: list) -> dict:
        """Calculate metrics using GSC summary data for accurate CTR."""
        
        # Get summary data (this gives us the accurate CTR from GSC)
        summary_data = None
        if summary_response and 'rows' in summary_response and len(summary_response['rows']) > 0:
            summary_data = summary_response['rows'][0]
        
        if not summary_data:
            return self._get_empty_metrics()
        
        # Get accurate metrics from summary data
        total_clicks = summary_data.get('clicks', 0)
        total_impressions = summary_data.get('impressions', 0)
        gsc_ctr = summary_data.get('ctr', 0)  # This is the accurate CTR from GSC
        avg_position = summary_data.get('position', 0)
        
        # Debug logging
        print(f"[GSC OAUTH] Debug - Summary clicks: {total_clicks}, Summary impressions: {total_impressions}")
        print(f"[GSC OAUTH] Debug - GSC Summary CTR: {gsc_ctr * 100}%")
        print(f"[GSC OAUTH] Debug - GSC Summary Position: {avg_position}")
        
        # Calculate SEO score (simplified algorithm)
        seo_score = self._calculate_seo_score(total_clicks, total_impressions, gsc_ctr, avg_position)
        
        return {
            'seo_score': round(seo_score, 1),
            'organic_traffic': total_clicks,
            'avg_position': round(avg_position, 1),
            'ctr': round(gsc_ctr * 100, 2),  # Convert to percentage
            'impressions': total_impressions,
            'keywords': len(detailed_rows)
        }
    
    def _calculate_metrics(self, rows: list) -> dict:
        """Calculate aggregated metrics from GSC rows."""
        if not rows:
            return self._get_empty_metrics()
        
        total_clicks = sum(row.get('clicks', 0) for row in rows)
        total_impressions = sum(row.get('impressions', 0) for row in rows)
        total_position = sum(row.get('position', 0) for row in rows) / len(rows) if rows else 0
        
        # Get CTR directly from GSC (average of individual CTR values)
        gsc_ctr = sum(row.get('ctr', 0) for row in rows) / len(rows) if rows else 0
        
        # Debug logging
        print(f"[GSC OAUTH] Debug - Total clicks: {total_clicks}, Total impressions: {total_impressions}")
        print(f"[GSC OAUTH] Debug - GSC CTR: {gsc_ctr * 100}%")
        
        # Calculate SEO score (simplified algorithm)
        seo_score = self._calculate_seo_score(total_clicks, total_impressions, gsc_ctr, total_position)
        
        return {
            'seo_score': round(seo_score, 1),
            'organic_traffic': total_clicks,
            'avg_position': round(total_position, 1),
            'ctr': round(gsc_ctr * 100, 2),  # Convert to percentage
            'impressions': total_impressions,
            'keywords': len(rows)
        }
    
    def _calculate_seo_score(self, clicks: int, impressions: int, ctr: float, position: float) -> float:
        """Calculate SEO score using unified scoring engine."""
        # Import here to avoid circular dependency
        from app.core.seo_scoring import SEOScoringEngine
        
        # Use unified scoring engine for consistency
        score = SEOScoringEngine.calculate_score(
            clicks=clicks,
            impressions=impressions,
            ctr=ctr,
            position=position,
            historical_data=None  # No historical data for simple metrics
        )
        
        return score
    
    def _get_empty_metrics(self) -> dict:
        """Return empty metrics structure with base SEO score."""
        # Import here to avoid circular dependency
        from app.core.seo_scoring import SEOScoringEngine
        
        # Calculate base score for no data
        base_score = SEOScoringEngine.calculate_score(
            clicks=0,
            impressions=0,
            ctr=0,
            position=0,
            historical_data=None
        )
        
        return {
            'seo_score': base_score,  # Unified base score (25.0)
            'organic_traffic': 0,
            'avg_position': 0,
            'ctr': 0,
            'impressions': 0,
            'keywords': 0
        }

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
            
            # Return the processed metrics with comparison data
            return {
                "summary": current_summary,
                "time_series": current_metrics.get('time_series', {}),
                "start_date": current_start_date.strftime('%Y-%m-%d'),
                "end_date": current_end_date.strftime('%Y-%m-%d')
            }
            
        except Exception as e:
            return {}
    
    async def fetch_keywords(self, user_email: str, property_url: str, days: int = 30) -> List[Dict]:
        """Fetch keywords from GSC for the last 30 days."""
        try:
            credentials = self.oauth_handler.get_credentials(user_email)
            if not credentials or not credentials.valid:
                raise Exception("Invalid or missing Google credentials")

            # Calculate 30-day date range
            today = datetime.utcnow().date()
            end_date = today - timedelta(days=3)  # Data is usually delayed by 3-4 days
            start_date = end_date - timedelta(days=days - 1)  # 30 days total
            
            # Build the Search Console API service
            service = build('webmasters', 'v3', credentials=credentials)
            
            # Request keywords data
            request = {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'dimensions': ['query'],
                'rowLimit': 1000  # Get up to 1000 keywords
            }
            
            response = service.searchanalytics().query(
                siteUrl=property_url, body=request
            ).execute()
            
            keywords = []
            if 'rows' in response:
                for row in response['rows']:
                    # Handle null/undefined values with defaults
                    ctr = row.get('ctr', 0)
                    if ctr is None:
                        ctr = 0
                    
                    keywords.append({
                        'query': row['keys'][0],
                        'clicks': row.get('clicks', 0),
                        'impressions': row.get('impressions', 0),
                        'ctr': ctr,
                        'position': row.get('position', 0)
                    })
            
            # Sort by position (best first)
            keywords.sort(key=lambda x: x['position'])
            
            return keywords
            
        except HttpError as e:
            print(f"HTTP Error fetching keywords: {e}")
            if e.resp.status == 403:
                raise Exception("Access denied to Google Search Console. Please check your permissions.")
            elif e.resp.status == 404:
                raise Exception("Property not found in Google Search Console.")
            else:
                raise Exception(f"Google Search Console API error: {e}")
        except Exception as e:
            print(f"Error fetching keywords: {e}")
            raise Exception(f"Failed to fetch keywords: {str(e)}")
    
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
    
    # REMOVED: Google Sheets integration methods - migrated to Supabase
    # def _store_metrics(self, user_email: str, property_url: str, metrics: Dict):
    #     """Store the latest GSC metrics in Google Sheets."""
    #     # Method removed - now using Supabase for data storage
    
    # async def get_stored_metrics(self, user_email: str, website_url: str) -> Optional[Dict]:
    #     """Get stored metrics for a user's website from Google Sheets."""
    #     # Method removed - now using Supabase for data storage

    # REMOVED: All keyword analysis functions - not displayed on dashboard

# REMOVED: PageSpeedInsightsFetcher class and all its methods - no longer used in Solvia

# REMOVED: MobileUsabilityFetcher class and all its methods - mobile metrics not displayed on dashboard
# REMOVED: IndexingCrawlabilityFetcher class - indexing metrics not displayed on dashboard  
# REMOVED: BusinessContextFetcher class - business metrics not displayed on dashboard

# Initialize the optimized components (only keeping PageSpeed fetcher for displayed UX metrics) 