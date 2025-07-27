from typing import Optional, Dict
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
    
    async def store_user_session(self, user_email: str, user_info: Dict) -> bool:
        """Store minimal user session data."""
        try:
            session_data = {
                'email': user_email,
                'name': user_info.get('name'),
                'picture': user_info.get('picture'),
                'last_login': datetime.utcnow().isoformat(),
                'is_active': True
            }
            
            # Upsert session data (create or update)
            response = self.supabase.table('user_sessions').upsert(session_data).execute()
            return True
        except Exception as e:
            print(f"Error storing user session: {e}")
            return False
    
    async def get_user_session(self, user_email: str) -> Optional[Dict]:
        """Get user session by email."""
        try:
            response = self.supabase.table('user_sessions').select('*').eq('email', user_email).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error getting user session: {e}")
            return None
    
    async def update_last_login(self, user_email: str) -> bool:
        """Update last login timestamp."""
        try:
            response = self.supabase.table('user_sessions').update({
                'last_login': datetime.utcnow().isoformat()
            }).eq('email', user_email).execute()
            return True
        except Exception as e:
            print(f"Error updating last login: {e}")
            return False
    
    async def deactivate_session(self, user_email: str) -> bool:
        """Deactivate user session (logout)."""
        try:
            response = self.supabase.table('user_sessions').update({
                'is_active': False
            }).eq('email', user_email).execute()
            return True
        except Exception as e:
            print(f"Error deactivating session: {e}")
            return False 