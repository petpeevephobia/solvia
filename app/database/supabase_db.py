from supabase import create_client, Client
import os
from typing import Optional, Dict, Any
from datetime import datetime

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://your-project.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-anon-key")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) 

class SupabaseAuthDB:
    """
    Supabase Auth interface for registration, login, and email verification.
    Uses Supabase's built-in Auth API only.
    """
    def __init__(self, access_token: str = None):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        if access_token:
            self.supabase.auth.session = {"access_token": access_token}

    def register_user(self, email: str, password: str) -> dict:
        """
        Register a new user using Supabase Auth. Triggers email verification if enabled.
        Returns the Supabase response dict.
        """
        try:
            result = self.supabase.auth.sign_up({"email": email, "password": password})
            return result.__dict__ if hasattr(result, '__dict__') else dict(result)
        except Exception as e:
            print(f"[SupabaseAuth] Error registering user: {e}")
            return {"error": str(e)}

    def login_user(self, email: str, password: str) -> dict:
        """
        Log in a user using Supabase Auth. Returns session and user info if successful.
        """
        try:
            result = self.supabase.auth.sign_in_with_password({"email": email, "password": password})
            return result.__dict__ if hasattr(result, '__dict__') else dict(result)
        except Exception as e:
            print(f"[SupabaseAuth] Error logging in user: {e}")
            return {"error": str(e)}

    def get_user(self, access_token: str) -> Optional[dict]:
        """
        Get the current user from an access token (JWT).
        """
        try:
            user = self.supabase.auth.get_user(access_token)
            return user.__dict__ if hasattr(user, '__dict__') else dict(user)
        except Exception as e:
            print(f"[SupabaseAuth] Error getting user: {e}")
            return None

    def get_user_by_email(self, email: str):
        """
        Get user by email using Supabase's built-in auth system.
        Note: This method is limited as Supabase doesn't allow querying users by email directly.
        Instead, we should use the user's JWT token to get their info.
        """
        try:
            # For Supabase auth, we can't query users by email directly
            # Instead, we should use the user's session/JWT to get their info
            # This method is kept for compatibility but should be avoided
            print(f"[WARNING] get_user_by_email called for {email} - use get_user with JWT instead")
            return None
        except Exception as e:
            print(f"[SupabaseAuth] Error getting user by email: {e}")
            return None

    def get_selected_gsc_property(self, email: str) -> str | None:
        """
        Returns the selected GSC property URL for the given user.
        """
        try:
            # Query the user_websites table in Supabase
            response = self.supabase.table('user_websites').select('website_url').eq('email', email).execute()
            
            if response.data and len(response.data) > 0:
                website_url = response.data[0].get('website_url')
                if website_url:
                    return website_url
            
            return None
            
        except Exception as e:
            print(f"[SupabaseAuth] Error getting selected GSC property: {e}")
            return None

    def get_user_website(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get the user's selected website URL.
        """
        try:
            # Query the user_websites table in Supabase
            response = self.supabase.table('user_websites').select('*').eq('email', email).execute()
            
            if response.data and len(response.data) > 0:
                website_data = response.data[0]
                return {
                    "website_url": website_data.get('website_url', ''),
                    "created_at": website_data.get('created_at'),
                    "updated_at": website_data.get('updated_at')
                }
            
            return None
            
        except Exception as e:
            print(f"[SupabaseAuth] Error getting user website: {e}")
            return None

    def add_user_website(self, email: str, website_url: str) -> bool:
        """
        Add or update a user's selected website URL.
        """
        # Validation: website_url must be a non-empty string and match expected GSC property formats
        if not isinstance(website_url, str) or not website_url.strip():
            print(f"[VALIDATION ERROR] website_url is empty or not a string: {website_url}")
            return False
        if not (website_url.startswith('http://') or website_url.startswith('https://') or website_url.startswith('sc-domain:')):
            print(f"[VALIDATION ERROR] website_url does not match expected GSC formats: {website_url}")
            return False
        try:
            # Check if user already has a website entry
            existing = self.supabase.table('user_websites').select('id').eq('email', email).execute()
            if existing.data and len(existing.data) > 0:
                row_id = existing.data[0]['id']
                response = self.supabase.table('user_websites').update({
                    'email': email,  # Set email in case it was NULL before
                    'website_url': website_url,
                    'updated_at': datetime.utcnow().isoformat()
                }).eq('id', row_id).execute()
            else:
                response = self.supabase.table('user_websites').insert({
                    'email': email,
                    'website_url': website_url,
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                }).execute()
            return True if response.data else False
        except Exception as e:
            print(f"[SupabaseAuth] Error adding user website: {e}")
            return False

    def store_dashboard_cache(self, email: str, website_url: str, dashboard_data: Dict[str, Any]) -> bool:
        """
        Store dashboard cache data.
        """
        try:
            # Check if cache entry already exists for today
            today = datetime.utcnow().date().isoformat()
            existing = self.supabase.table('dashboard_cache').select('id').eq('email', email).eq('website_url', website_url).eq('cache_date', today).execute()
            
            cache_data = {
                'email': email,
                'website_url': website_url,
                'cache_data': dashboard_data,
                'cache_date': today,
                'created_at': datetime.utcnow().isoformat()
            }
            
            if existing.data and len(existing.data) > 0:
                # Update existing cache entry
                response = self.supabase.table('dashboard_cache').update(cache_data).eq('id', existing.data[0]['id']).execute()
            else:
                # Insert new cache entry
                response = self.supabase.table('dashboard_cache').insert(cache_data).execute()
            
            return True if response.data else False
            
        except Exception as e:
            print(f"[SupabaseAuth] Error storing dashboard cache: {e}")
            return False

    def get_dashboard_cache(self, email: str, website_url: str) -> Optional[Dict[str, Any]]:
        """
        Get cached dashboard data for today's date only. If no cache exists for today, return None to trigger fresh data fetch.
        """
        try:
            today = datetime.utcnow().date().isoformat()
            response = self.supabase.table('dashboard_cache') \
                .select('*') \
                .eq('email', email) \
                .eq('website_url', website_url) \
                .eq('cache_date', today) \
                .limit(1) \
                .execute()
            if response.data and len(response.data) > 0:
                cache_entry = response.data[0]
                return cache_entry.get('cache_data')
            return None
        except Exception as e:
            print(f"[SupabaseAuth] Error getting dashboard cache: {e}")
            return None

    def store_website_content(self, email: str, website_url: str, content_data: Dict[str, Any]) -> bool:
        """
        Store website content data including meta descriptions, title tags, and content.
        """
        try:
            # Check if content entry already exists for this user and website
            existing = self.supabase.table('website_content').select('id').eq('email', email).eq('website_url', website_url).execute()
            
            content_data_to_store = {
                'email': email,
                'website_url': website_url,
                'title_tags': content_data.get('title_tags', {}),
                'meta_descriptions': content_data.get('meta_descriptions', {}),
                'page_content': content_data.get('page_content', {}),
                'fetched_at': datetime.utcnow().isoformat(),
                'created_at': datetime.utcnow().isoformat()
            }
            
            if existing.data and len(existing.data) > 0:
                # Update existing content entry
                row_id = existing.data[0]['id']
                response = self.supabase.table('website_content').update(content_data_to_store).eq('id', row_id).execute()
            else:
                # Insert new content entry
                response = self.supabase.table('website_content').insert(content_data_to_store).execute()
            
            return True if response.data else False
            
        except Exception as e:
            print(f"[SupabaseAuth] Error storing website content: {e}")
            return False

    def get_website_content(self, email: str, website_url: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent stored website content data for a user's website.
        """
        try:
            # Convert GSC domain format to regular URL format for matching
            search_url = website_url
            if website_url.startswith('sc-domain:'):
                domain = website_url.replace('sc-domain:', '')
                search_url = f"https://{domain}"
            
            # Get the most recent content regardless of date
            response = self.supabase.table('website_content') \
                .select('*') \
                .eq('email', email) \
                .eq('website_url', search_url) \
                .order('fetched_at', desc=True) \
                .limit(1) \
                .execute()
            
            if response.data and len(response.data) > 0:
                content_entry = response.data[0]
                return {
                    'title_tags': content_entry.get('title_tags', {}),
                    'meta_descriptions': content_entry.get('meta_descriptions', {}),
                    'page_content': content_entry.get('page_content', {}),
                    'fetched_at': content_entry.get('fetched_at'),
                    'created_at': content_entry.get('created_at')
                }
            return None
            
        except Exception as e:
            print(f"[SupabaseAuth] Error getting website content: {e}")
            return None 