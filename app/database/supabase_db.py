from typing import Optional, Dict, List
from datetime import datetime
from supabase import create_client, Client
from app.config import settings


class SupabaseAuthDB:
    """Simplified Supabase integration for user sessions only."""
    
    def __init__(self):
        self.supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )
    
    async def store_user_session(self, user_email: str, user_info: Dict, access_token: str = None, refresh_token: str = None) -> bool:
        """Store minimal user session data."""
        try:
            session_data = {
                'email': user_email,
                'name': user_info.get('name'),
                'picture': user_info.get('picture'),
                'access_token': access_token,
                'refresh_token': refresh_token,
                'last_login': datetime.utcnow().isoformat()
            }
            
            # Upsert session data (create or update)
            response = self.supabase.table('user_sessions').upsert(session_data).execute()
            return True
        except Exception as e:
            return False

    async def get_user_session(self, user_email: str) -> Optional[Dict]:
        """Get user session from database."""
        try:
            response = self.supabase.table('user_sessions').select('*').eq('email', user_email).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            return None

    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email from user_sessions table."""
        try:
            response = self.supabase.table('user_sessions').select('*').eq('email', email).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            return None

    async def update_last_login(self, user_email: str) -> bool:
        """Update last login timestamp."""
        try:
            response = self.supabase.table('user_sessions').update({
                'last_login': datetime.utcnow().isoformat()
            }).eq('email', user_email).execute()
            return True
        except Exception as e:
            return False

    async def deactivate_session(self, user_email: str) -> bool:
        """Deactivate user session (logout)."""
        try:
            # For now, just return True since we don't have is_active column
            # You can add this column later if needed
            return True
        except Exception as e:
            return False

    async def store_chat_message(self, user_email: str, message_content: str, message_type: str, sender_name: str = None) -> int:
        """Store a chat message in the database."""
        try:
            result = self.supabase.table("chat_messages").insert({
                "user_email": user_email,
                "message_content": message_content,
                "message_type": message_type,
                "sender_name": sender_name,
                "created_at": datetime.utcnow().isoformat()
            }).execute()
            
            if result.data:
                return result.data[0]["id"]
            return 0
        except Exception as e:
            print(f"Error storing chat message: {str(e)}")
            return 0

    async def get_chat_messages(self, user_email: str, limit: int = 50) -> List[Dict]:
        """Get chat messages for a specific user."""
        try:
            response = self.supabase.table('chat_messages').select('*').eq('user_email', user_email).order('created_at', desc=False).limit(limit).execute()
            
            if response.data:
                return response.data
            return []
        except Exception as e:
            return [] 

    async def store_user_website(self, user_email: str, website_url: str) -> bool:
        """Store user's selected website. This will update the existing row, not create a new one."""
        try:
            # Update the user session with the selected website
            result = self.supabase.table("user_sessions").update({
                "selected_website": website_url,
                "updated_at": datetime.now().isoformat()
            }).eq("email", user_email).execute()
            
            return len(result.data) > 0
        except Exception as e:
            return False

    async def get_user_website(self, user_email: str) -> Optional[str]:
        """Get user's selected website."""
        try:
            response = self.supabase.table('user_sessions').select('selected_website').eq('email', user_email).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0].get('selected_website')
            return None
        except Exception as e:
            return None

    async def update_user_session_tokens(self, user_email: str, access_token: str, refresh_token: str) -> bool:
        """Update user session with new tokens."""
        try:
            result = self.supabase.table("user_sessions").update({
                "access_token": access_token,
                "refresh_token": refresh_token,
                "updated_at": datetime.now().isoformat()
            }).eq("email", user_email).execute()
            
            return len(result.data) > 0
        except Exception as e:
            return False

    async def store_gsc_metrics_cache(self, user_email: str, website_url: str, metrics: Dict, date_range: Dict) -> bool:
        """Store GSC metrics cache for a specific date range."""
        try:
            from datetime import datetime
            today = datetime.now().date()
            
            # Create cache entry
            cache_data = {
                "user_email": user_email,
                "website_url": website_url,
                "start_date": date_range['start_date'].isoformat(),
                "end_date": date_range['end_date'].isoformat(),
                "seo_score": metrics.get('seo_score', 0),
                "impressions": metrics.get('organic_traffic', 0),
                "clicks": int(metrics.get('organic_traffic', 0) * (metrics.get('ctr', 0) / 100)),
                "ctr": metrics.get('ctr', 0),
                "avg_position": metrics.get('avg_position', 0),
                "cache_date": today.isoformat(),
                "created_at": datetime.now().isoformat()
            }
            
            result = self.supabase.table("gsc_metrics_cache").insert(cache_data).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"Error storing GSC metrics cache: {e}")
            return False

    async def get_gsc_metrics_cache(self, user_email: str, website_url: str, date_range: Dict) -> Optional[Dict]:
        """Get cached GSC metrics for a specific date range."""
        try:
            from datetime import datetime
            today = datetime.now().date()
            
            # Check for today's cache with matching date range
            response = self.supabase.table('gsc_metrics_cache').select('*').eq('user_email', user_email).eq('website_url', website_url).eq('cache_date', today.isoformat()).eq('start_date', date_range['start_date'].isoformat()).eq('end_date', date_range['end_date'].isoformat()).order('created_at', desc=True).limit(1).execute()
            
            if response.data and len(response.data) > 0:
                cache_entry = response.data[0]
                return {
                    'seo_score': cache_entry['seo_score'],
                    'organic_traffic': cache_entry['impressions'],
                    'avg_position': cache_entry['avg_position'],
                    'ctr': cache_entry['ctr']
                }
            return None
        except Exception as e:
            print(f"Error getting GSC metrics cache: {e}")
            return None 