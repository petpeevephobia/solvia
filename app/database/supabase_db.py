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
    
    async def store_user_session(self, user_email: str, user_info: Dict) -> bool:
        """Store minimal user session data."""
        try:
            session_data = {
                'email': user_email,
                'name': user_info.get('name'),
                'picture': user_info.get('picture'),
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
            print(f"Error getting user session: {e}")
            return None

    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email from user_sessions table."""
        try:
            response = self.supabase.table('user_sessions').select('*').eq('email', email).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error getting user by email: {e}")
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
            print(f"Error storing chat message: {e}")
            return 0

    async def get_chat_messages(self, user_email: str, limit: int = 50) -> List[Dict]:
        """Get chat messages for a specific user."""
        try:
            print(f"Fetching chat messages for user: {user_email}")
            response = self.supabase.table('chat_messages').select('*').eq('user_email', user_email).order('created_at', desc=False).limit(limit).execute()
            
            print(f"Database response: {len(response.data) if response.data else 0} messages found")
            if response.data:
                for i, msg in enumerate(response.data[:3]):  # Show first 3 messages
                    print(f"  Message {i+1}: {msg.get('message_type')} - {msg.get('message_content', '')[:50]}...")
                return response.data
            return []
        except Exception as e:
            print(f"Error getting chat messages: {e}")
            return [] 