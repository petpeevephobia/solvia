from supabase import create_client, Client
import os
from typing import Optional, Dict, Any, List
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
        self.supabase_url = SUPABASE_URL
        self.service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        # Create service role client for RLS bypass operations
        if self.service_role_key:
            self.service_supabase = create_client(SUPABASE_URL, self.service_role_key)
        else:
            self.service_supabase = self.supabase
            
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
            # Use service role key to bypass RLS for this operation
            service_supabase = create_client(self.supabase_url, self.service_role_key)
            
            # Query the user_websites table in Supabase
            response = service_supabase.table('user_websites').select('website_url').eq('email', email).execute()
            
            if response.data and len(response.data) > 0:
                website_url = response.data[0].get('website_url')
                if website_url:
                    return website_url
            
            return None
            
        except Exception as e:
            print(f"[SupabaseAuth] Error getting selected GSC property: {e}")
            return None

    def get_user_website(self, email: str) -> Optional[str]:
        """
        Get the user's selected website URL as a string.
        """
        try:
            # Use service role key to bypass RLS for this operation
            service_supabase = create_client(self.supabase_url, self.service_role_key)
            
            # Query the user_websites table in Supabase
            response = service_supabase.table('user_websites').select('website_url').eq('email', email).execute()
            
            if response.data and len(response.data) > 0:
                website_url = response.data[0].get('website_url')
                return website_url
            
            return None
            
        except Exception as e:
            print(f"[SupabaseAuth] Error getting user website: {e}")
            return None



    def get_user_website_dict(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get the user's selected website URL as a dictionary.
        """
        try:
            # Use service role key to bypass RLS for this operation
            service_supabase = create_client(self.supabase_url, self.service_role_key)
            
            # Query the user_websites table in Supabase
            response = service_supabase.table('user_websites').select('*').eq('email', email).execute()
            
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
            # Use service role key to bypass RLS for this operation
            service_supabase = create_client(self.supabase_url, self.service_role_key)
            
            # Check if user already has a website entry
            existing = service_supabase.table('user_websites').select('id').eq('email', email).execute()
            if existing.data and len(existing.data) > 0:
                row_id = existing.data[0]['id']
                response = service_supabase.table('user_websites').update({
                    'email': email,  # Set email in case it was NULL before
                    'website_url': website_url,
                    'updated_at': datetime.utcnow().isoformat()
                }).eq('id', row_id).execute()
            else:
                response = service_supabase.table('user_websites').insert({
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
                "user_email": user_email,
                "website_url": website_url,
                "start_date": date_range['start_date'].isoformat(),
                "end_date": date_range['end_date'].isoformat(),
                "seo_score": metrics.get('seo_score', 0),
                "impressions": metrics.get('organic_traffic', 0),
                "clicks": metrics.get('clicks', 0),  # Use actual clicks count
                "ctr": metrics.get('ctr', 0),
                "avg_position": metrics.get('avg_position', 0),
                "cache_date": today.isoformat(),
                "created_at": datetime.now().isoformat()
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
                return {
                    'seo_score': cache_entry['seo_score'],
                    'organic_traffic': cache_entry['impressions'],
                    'clicks': cache_entry['clicks'],  # Include actual clicks count
                    'avg_position': cache_entry['avg_position'],
                    'ctr': cache_entry['ctr']
                }
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

    async def get_or_create_user_session(self, email: str) -> Dict[str, Any]:
        """
        Get or create a user session for Google OAuth users.
        This creates a user session without requiring password authentication.
        """
        try:
            # Try to use service role key for OAuth operations
            service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            supabase_client = self.supabase
            
            if service_role_key:
                # Use service role key to bypass RLS
                from supabase import create_client
                supabase_client = create_client(os.getenv("SUPABASE_URL"), service_role_key)
                print(f"Using service role key for user session creation for {email}")
            else:
                print(f"No service role key available for user session creation for {email}")
            
            # Check if user session already exists
            response = supabase_client.table('user_sessions').select('*').eq('email', email).execute()
            
            if response.data and len(response.data) > 0:
                # Update existing session
                session_data = response.data[0]
                update_data = {
                    'last_login': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                }
                
                supabase_client.table('user_sessions').update(update_data).eq('email', email).execute()
                
                return {
                    'id': session_data['id'],
                    'email': session_data['email'],
                    'name': session_data.get('name'),
                    'picture': session_data.get('picture'),
                    'last_login': update_data['last_login']
                }
            else:
                # Create new user session
                session_data = {
                    'email': email,
                    'name': None,  # Will be filled from Google profile if needed
                    'picture': None,  # Will be filled from Google profile if needed
                    'access_token': None,
                    'refresh_token': None,
                    'selected_website': None,
                    'last_login': datetime.utcnow().isoformat(),
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                }
                
                response = supabase_client.table('user_sessions').insert(session_data).execute()
                
                if response.data and len(response.data) > 0:
                    return {
                        'id': response.data[0]['id'],
                        'email': response.data[0]['email'],
                        'name': response.data[0].get('name'),
                        'picture': response.data[0].get('picture'),
                        'last_login': response.data[0]['last_login']
                    }
                else:
                    raise Exception("Failed to create user session")
                    
        except Exception as e:
            print(f"[SupabaseAuth] Error getting/creating user session: {e}")
            raise e

    async def get_user_session(self, user_email: str) -> Optional[Dict[str, Any]]:
        """
        Get user session by email.
        """
        try:
            response = self.supabase.table('user_sessions').select('*').eq('email', user_email).execute()
            
            if response.data and len(response.data) > 0:
                session_data = response.data[0]
                return {
                    'id': session_data['id'],
                    'email': session_data['email'],
                    'name': session_data.get('name'),
                    'picture': session_data.get('picture'),
                    'selected_website': session_data.get('selected_website'),
                    'last_login': session_data.get('last_login'),
                    'created_at': session_data.get('created_at'),
                    'updated_at': session_data.get('updated_at')
                }
            return None
            
        except Exception as e:
            print(f"[SupabaseAuth] Error getting user session: {e}")
            return None

    def get_gsc_metrics_cache(self, user_email: str, website_url: str, date_range: dict) -> Optional[Dict]:
        """
        Get cached GSC metrics for a user's website and date range.
        """
        try:
            start_date = date_range['start_date']
            end_date = date_range['end_date']
            
            # Query the cache table with flexible date matching
            # First try exact match
            response = self.supabase.table('gsc_metrics_cache') \
                .select('*') \
                .eq('user_email', user_email) \
                .eq('website_url', website_url) \
                .eq('start_date', start_date.strftime('%Y-%m-%d')) \
                .eq('end_date', end_date.strftime('%Y-%m-%d')) \
                .order('created_at', desc=True) \
                .limit(1) \
                .execute()

            # If no exact match, try most recent cache for this user/website
            if not response.data:
                from datetime import timedelta
                print(f"[CACHE] No exact date match, trying most recent cache for {user_email}")
                response = self.supabase.table('gsc_metrics_cache') \
                    .select('*') \
                    .eq('user_email', user_email) \
                    .eq('website_url', website_url) \
                    .order('created_at', desc=True) \
                    .limit(1) \
                    .execute()
                print(f"[CACHE] Most recent cache lookup: {len(response.data) if response.data else 0} records")
                if response.data:
                    print(f"[CACHE] Found recent cache with {response.data[0].get('impressions', 0)} impressions")
            
            if response.data and len(response.data) > 0:
                cache_entry = response.data[0]
                return {
                    'clicks': cache_entry.get('clicks', 0),
                    'organic_traffic': cache_entry.get('impressions', 0),
                    'ctr': cache_entry.get('ctr', 0),
                    'avg_position': cache_entry.get('avg_position', 0),
                    'seo_score': cache_entry.get('seo_score', 0)
                }
            return None
            
        except Exception as e:
            print(f"[SupabaseAuth] Error getting GSC metrics cache: {e}")
            return None

    def store_gsc_metrics_cache(self, user_email: str, website_url: str, metrics: dict, date_range: dict) -> bool:
        """
        Store GSC metrics in cache for a user's website and date range.
        Also updates the SEO score from the latest audit if available.
        """
        try:
            start_date = date_range['start_date']
            end_date = date_range['end_date']
            
            # Check if there's a recent audit with updated SEO score
            latest_audit = self.get_latest_audit(user_email, website_url)
            if latest_audit and latest_audit.get('seo_score'):
                # Use the SEO score from the latest audit
                metrics['seo_score'] = latest_audit['seo_score']
            
            cache_data = {
                'user_email': user_email,
                'website_url': website_url,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'seo_score': metrics.get('seo_score', 0),
                'impressions': metrics.get('organic_traffic', 0),
                'clicks': metrics.get('clicks', 0),
                'ctr': metrics.get('ctr', 0),
                'avg_position': metrics.get('avg_position', 0),
                'cache_date': datetime.utcnow().date().strftime('%Y-%m-%d'),
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Insert or update cache entry with service role key
            if self.service_role_key:
                service_client = create_client(self.supabase_url, self.service_role_key)
            else:
                service_client = self.supabase
                
            response = service_client.table('gsc_metrics_cache').upsert(cache_data, on_conflict=['user_email,website_url,start_date,end_date']).execute()
            
            return True if response.data else False
            
        except Exception as e:
            print(f"[SupabaseAuth] Error storing GSC metrics cache: {e}")
            return False

    def get_dashboard_cache(self, user_email: str, website_url: str) -> Optional[Dict]:
        """
        Get cached dashboard data for a user's website.
        """
        try:
            # For now, return None as we don't have a dashboard cache table
            # This can be implemented later if needed
            return None
            
        except Exception as e:
            print(f"[SupabaseAuth] Error getting dashboard cache: {e}")
            return None

    def store_dashboard_cache(self, user_email: str, website_url: str, dashboard_data: dict) -> bool:
        """
        Store dashboard data in cache for a user's website.
        """
        try:
            # For now, return True as we don't have a dashboard cache table
            # This can be implemented later if needed
            return True
            
        except Exception as e:
            print(f"[SupabaseAuth] Error storing dashboard cache: {e}")
            return False

    def store_chat_message(self, user_email: str, message_content: str, message_type: str, sender_name: str) -> str:
        """
        Store a chat message in the database using service role key to bypass RLS.
        """
        try:
            # Use service role key to bypass RLS for chat storage
            if self.service_role_key:
                service_client = create_client(self.supabase_url, self.service_role_key)
            else:
                service_client = self.supabase
                
            message_data = {
                'user_email': user_email,
                'message_content': message_content,
                'message_type': message_type,
                'sender_name': sender_name,
                'created_at': datetime.utcnow().isoformat()
            }
            
            response = service_client.table('chat_messages').insert(message_data).execute()
            
            if response.data and len(response.data) > 0:
                return str(response.data[0]['id'])
            else:
                raise Exception("Failed to store chat message")
                
        except Exception as e:
            print(f"[SupabaseAuth] Error storing chat message: {e}")
            raise e

    def get_chat_messages(self, user_email: str, limit: int = 50) -> list:
        """
        Get chat messages for a user using service role key.
        """
        try:
            print(f"[CHAT RETRIEVAL] Getting messages for user: {user_email}")
            
            # Use service role key to bypass RLS for chat retrieval
            if self.service_role_key:
                print(f"[CHAT RETRIEVAL] Using service role key")
                service_client = create_client(self.supabase_url, self.service_role_key)
            else:
                print(f"[CHAT RETRIEVAL] Using regular client")
                service_client = self.supabase
                
            response = service_client.table('chat_messages') \
                .select('*') \
                .eq('user_email', user_email) \
                .order('created_at', desc=True) \
                .limit(limit) \
                .execute()
            
            print(f"[CHAT RETRIEVAL] Found {len(response.data)} messages")
            
            if response.data:
                # Return in chronological order (oldest first)
                messages = list(reversed(response.data))
                print(f"[CHAT RETRIEVAL] Returning {len(messages)} messages")
                return messages
            return []
            
        except Exception as e:
            print(f"[SupabaseAuth] Error getting chat messages: {e}")
            return []

    def store_website_content(self, user_email: str, website_url: str, content_data: dict) -> bool:
        """
        Store website content analysis data.
        """
        try:
            content_data_to_store = {
                'email': user_email,
                'website_url': website_url,
                'title_tags': content_data.get('title_tags', {}),
                'meta_descriptions': content_data.get('meta_descriptions', {}),
                'page_content': content_data.get('page_content', {}),
                'fetched_at': datetime.utcnow().isoformat(),
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Insert new content entry
            response = self.supabase.table('website_content').insert(content_data_to_store).execute()
            
            return True if response.data else False
            
        except Exception as e:
            print(f"[SupabaseAuth] Error storing website content: {e}")
            return False
    
    # ===========================
    # AUDIT STORAGE METHODS
    # ===========================
    
    def store_audit_result(self, user_email: str, audit_data: dict, website_url: str) -> Optional[str]:
        """
        Store audit result in database using service role key to bypass RLS
        """
        try:
            # Use service role key to bypass RLS
            print(f"[AUDIT STORAGE] Service role key available: {bool(self.service_role_key)}")
            if self.service_role_key:
                print("[AUDIT STORAGE] Using service role key to bypass RLS")
                service_client = create_client(self.supabase_url, self.service_role_key)
            else:
                print("[AUDIT STORAGE] WARNING: No service role key, using regular client")
                service_client = self.supabase
                
            # Use the audit_id from the audit_data if it exists, otherwise generate new one
            import uuid
            audit_id = audit_data.get('audit_id', str(uuid.uuid4()))
            
            audit_record = {
                'audit_id': audit_id,  # Use existing audit_id from audit_data
                'user_email': user_email,
                'website_url': website_url,
                'audit_data': audit_data,  # JSON data
                'seo_score': audit_data.get('seo_score', 0),
                'critical_issues': audit_data.get('critical_issues', 0),
                'status': 'completed',
                'created_at': datetime.utcnow().isoformat()
            }
            
            response = service_client.table('audit_results').insert(audit_record).execute()
            
            if response.data and len(response.data) > 0:
                return audit_id  # Return the UUID we generated
            return None
            
        except Exception as e:
            print(f"[SupabaseAuth] Error storing audit result: {e}")
            return None
    
    def get_audit_history(self, user_email: str, limit: int = 10, offset: int = 0) -> List[dict]:
        """
        Get user's audit history with pagination support using service role key
        """
        try:
            # Use service role key to bypass RLS
            if self.service_role_key:
                service_client = create_client(self.supabase_url, self.service_role_key)
                query = (service_client
                        .table('audit_results')
                        .select('*')
                        .eq('user_email', user_email)
                        .order('created_at', desc=True))
            else:
                query = (self.supabase
                        .table('audit_results')
                        .select('*')
                        .eq('user_email', user_email)
                        .order('created_at', desc=True))
            
            # Apply offset and limit
            if offset > 0:
                query = query.range(offset, offset + limit - 1)
            else:
                query = query.limit(limit)
            
            response = query.execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            print(f"[SupabaseAuth] Error getting audit history: {e}")
            return []
    
    def get_audit_by_id(self, audit_id: str, user_email: str) -> Optional[dict]:
        """
        Get specific audit by ID using service role key to bypass RLS
        """
        try:
            # Use service role key to bypass RLS for system operations
            if self.service_role_key:
                service_client = create_client(self.supabase_url, self.service_role_key)
                response = (service_client
                           .table('audit_results')
                           .select('*')
                           .eq('audit_id', audit_id)  # Fixed: use 'audit_id' not 'id'
                           .eq('user_email', user_email)
                           .single()
                           .execute())
            else:
                response = (self.supabase
                           .table('audit_results')
                           .select('*')
                           .eq('audit_id', audit_id)  # Fixed: use 'audit_id' not 'id'
                           .eq('user_email', user_email)
                           .single()
                           .execute())
            
            return response.data if response.data else None
            
        except Exception as e:
            print(f"[SupabaseAuth] Error getting audit by ID: {e}")
            print(f"[SupabaseAuth] Audit ID: {audit_id}, User Email: {user_email}")
            return None
    
    def update_audit_status(self, audit_id: str, user_email: str, status: str, pdf_path: Optional[str] = None) -> bool:
        """
        Update audit status or metadata using service role key
        """
        try:
            # Use service role key to bypass RLS
            if self.service_role_key:
                service_client = create_client(self.supabase_url, self.service_role_key)
            else:
                service_client = self.supabase
                
            update_data = {
                'status': status,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if pdf_path:
                update_data['pdf_path'] = pdf_path
            
            response = (service_client
                       .table('audit_results')
                       .update(update_data)
                       .eq('audit_id', audit_id)  # Use audit_id instead of id
                       .eq('user_email', user_email)
                       .execute())
            
            return True if response.data else False
            
        except Exception as e:
            print(f"[SupabaseAuth] Error updating audit status: {e}")
            return False
    
    def update_gsc_cache_with_audit_score(self, user_email: str, website_url: str, seo_score: float) -> bool:
        """
        Update the GSC metrics cache with the latest audit SEO score
        """
        try:
            # Use service role key to bypass RLS
            if self.service_role_key:
                service_client = create_client(self.supabase_url, self.service_role_key)
            else:
                service_client = self.supabase
            
            # Update the most recent cache entry with the new SEO score
            from datetime import datetime
            response = (service_client
                       .table('gsc_metrics_cache')
                       .update({'seo_score': seo_score, 'updated_at': datetime.utcnow().isoformat()})
                       .eq('user_email', user_email)
                       .eq('website_url', website_url)
                       .execute())
            
            if response.data:
                print(f"[SupabaseAuth] Updated GSC cache with audit score: {seo_score}")
                return True
            return False
            
        except Exception as e:
            print(f"[SupabaseAuth] Error updating GSC cache with audit score: {e}")
            return False
    
    def get_latest_audit(self, user_email: str, website_url: str) -> Optional[dict]:
        """
        Get most recent audit for a specific website using service role key
        """
        try:
            # Use service role key to bypass RLS
            if self.service_role_key:
                service_client = create_client(self.supabase_url, self.service_role_key)
            else:
                service_client = self.supabase
                
            print(f"[get_latest_audit] Searching for audit: user_email={user_email}, website_url={website_url}")
            
            response = (service_client
                       .table('audit_results')
                       .select('*')
                       .eq('user_email', user_email)
                       .eq('website_url', website_url)
                       .order('created_at', desc=True)
                       .limit(1)
                       .execute())
            
            print(f"[get_latest_audit] Found {len(response.data)} audits")
            
            return response.data[0] if response.data else None
            
        except Exception as e:
            print(f"[SupabaseAuth] Error getting latest audit: {e}")
            return None 