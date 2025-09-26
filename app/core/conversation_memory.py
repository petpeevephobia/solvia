"""
Conversation Memory System for Solvia Chat
Handles conversation persistence, management, and retrieval
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from uuid import uuid4
import json

class ConversationMemory:
    """
    Manages conversation state and persistence for chat sessions.
    Each conversation has a unique ID and maintains message history.
    """

    def __init__(self, db_instance):
        """
        Initialize conversation memory with database connection

        Args:
            db_instance: SupabaseAuthDB instance for database operations
        """
        self.db = db_instance

    def create_conversation(self, user_email: str, title: Optional[str] = None) -> str:
        """
        Create a new conversation for a user

        Args:
            user_email: User's email address
            title: Optional conversation title (auto-generated if not provided)

        Returns:
            conversation_id: Unique identifier for the new conversation
        """
        try:
            conversation_id = str(uuid4())

            # Auto-generate title if not provided
            if not title:
                now = datetime.now()
                title = f"Conversation - {now.strftime('%b %d, %Y %I:%M %p')}"

            conversation_data = {
                'conversation_id': conversation_id,
                'user_email': user_email,
                'title': title,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'message_count': 0,
                'is_active': True,
                'metadata': json.dumps({
                    'theme': 'seo_support',
                    'context': 'solvia_agent'
                })
            }

            # Store in database
            self.db.store_conversation(conversation_data)

            return conversation_id

        except Exception as e:
            print(f"[ConversationMemory] Error creating conversation: {e}")
            raise

    def get_user_conversations(self, user_email: str, limit: int = 20) -> List[Dict]:
        """
        Get all conversations for a user, sorted by most recent

        Args:
            user_email: User's email address
            limit: Maximum number of conversations to return

        Returns:
            List of conversation dictionaries
        """
        try:
            return self.db.get_user_conversations(user_email, limit)
        except Exception as e:
            print(f"[ConversationMemory] Error getting conversations: {e}")
            return []

    def get_conversation_messages(
        self,
        conversation_id: str,
        user_email: str,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Get all messages for a specific conversation

        Args:
            conversation_id: Conversation identifier
            user_email: User's email for verification
            limit: Optional limit on number of messages

        Returns:
            List of message dictionaries
        """
        try:
            return self.db.get_conversation_messages(conversation_id, user_email, limit)
        except Exception as e:
            print(f"[ConversationMemory] Error getting messages: {e}")
            return []

    def add_message(
        self,
        conversation_id: str,
        user_email: str,
        message_content: str,
        message_type: str,
        sender_name: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Add a message to a conversation

        Args:
            conversation_id: Conversation identifier
            user_email: User's email address
            message_content: The message text
            message_type: 'user' or 'ai'
            sender_name: Name of the sender
            metadata: Optional metadata (e.g., audit_id, attachments)

        Returns:
            message_id: Unique identifier for the message
        """
        try:
            message_id = str(uuid4())

            message_data = {
                'message_id': message_id,
                'conversation_id': conversation_id,
                'user_email': user_email,
                'message_content': message_content,
                'message_type': message_type,
                'sender_name': sender_name,
                'created_at': datetime.utcnow().isoformat(),
                'metadata': json.dumps(metadata) if metadata else None
            }

            # Store message
            self.db.store_conversation_message(message_data)

            # Update conversation's updated_at and message_count
            self.db.update_conversation_activity(conversation_id, user_email)

            return message_id

        except Exception as e:
            print(f"[ConversationMemory] Error adding message: {e}")
            raise

    def update_conversation_title(
        self,
        conversation_id: str,
        user_email: str,
        new_title: str
    ) -> bool:
        """
        Update the title of a conversation

        Args:
            conversation_id: Conversation identifier
            user_email: User's email for verification
            new_title: New title for the conversation

        Returns:
            Success boolean
        """
        try:
            return self.db.update_conversation_title(conversation_id, user_email, new_title)
        except Exception as e:
            print(f"[ConversationMemory] Error updating title: {e}")
            return False

    def delete_conversation(
        self,
        conversation_id: str,
        user_email: str
    ) -> bool:
        """
        Delete a conversation and all its messages

        Args:
            conversation_id: Conversation identifier
            user_email: User's email for verification

        Returns:
            Success boolean
        """
        try:
            return self.db.delete_conversation(conversation_id, user_email)
        except Exception as e:
            print(f"[ConversationMemory] Error deleting conversation: {e}")
            return False

    def get_or_create_active_conversation(
        self,
        user_email: str
    ) -> str:
        """
        Get the active conversation for a user, or create one if none exists

        Args:
            user_email: User's email address

        Returns:
            conversation_id: Active conversation identifier
        """
        try:
            # Check for active conversation
            active_conversation = self.db.get_active_conversation(user_email)

            if active_conversation:
                return active_conversation['conversation_id']

            # No active conversation, create new one
            return self.create_conversation(user_email)

        except Exception as e:
            print(f"[ConversationMemory] Error getting/creating conversation: {e}")
            # Fallback: create new conversation
            return self.create_conversation(user_email)

    def generate_smart_title(
        self,
        conversation_id: str,
        user_email: str,
        first_message: str
    ) -> str:
        """
        Generate a smart title based on the first message

        Args:
            conversation_id: Conversation identifier
            user_email: User's email address
            first_message: First user message in conversation

        Returns:
            Generated title
        """
        try:
            # Extract key topics from message
            message_lower = first_message.lower()

            # Check for common topics
            if 'audit' in message_lower:
                title = "SEO Audit Discussion"
            elif 'traffic' in message_lower:
                title = "Traffic Analysis"
            elif 'ranking' in message_lower or 'position' in message_lower:
                title = "Ranking Insights"
            elif 'issue' in message_lower or 'problem' in message_lower:
                title = "Issue Troubleshooting"
            elif 'improve' in message_lower or 'optimize' in message_lower:
                title = "Optimization Strategy"
            else:
                # Use first 50 chars of message as title
                title = first_message[:50] + ("..." if len(first_message) > 50 else "")

            # Update the conversation title
            self.update_conversation_title(conversation_id, user_email, title)

            return title

        except Exception as e:
            print(f"[ConversationMemory] Error generating title: {e}")
            return "New Conversation"

    def clear_all_conversations(
        self,
        user_email: str
    ) -> bool:
        """
        Clear all conversations for a user

        Args:
            user_email: User's email address

        Returns:
            Success boolean
        """
        try:
            return self.db.clear_user_conversations(user_email)
        except Exception as e:
            print(f"[ConversationMemory] Error clearing conversations: {e}")
            return False

    def export_conversation(
        self,
        conversation_id: str,
        user_email: str,
        format: str = 'json'
    ) -> Optional[Any]:
        """
        Export a conversation in specified format

        Args:
            conversation_id: Conversation identifier
            user_email: User's email address
            format: Export format ('json', 'text', 'markdown')

        Returns:
            Exported conversation data
        """
        try:
            # Get conversation details
            conversation = self.db.get_conversation_details(conversation_id, user_email)
            if not conversation:
                return None

            # Get all messages
            messages = self.get_conversation_messages(conversation_id, user_email)

            if format == 'json':
                return {
                    'conversation': conversation,
                    'messages': messages
                }
            elif format == 'text':
                text_output = f"Conversation: {conversation['title']}\n"
                text_output += f"Created: {conversation['created_at']}\n"
                text_output += "-" * 50 + "\n\n"

                for msg in messages:
                    sender = msg['sender_name']
                    text_output += f"{sender}: {msg['message_content']}\n\n"

                return text_output
            elif format == 'markdown':
                md_output = f"# {conversation['title']}\n\n"
                md_output += f"*Created: {conversation['created_at']}*\n\n"
                md_output += "---\n\n"

                for msg in messages:
                    sender = msg['sender_name']
                    if msg['message_type'] == 'user':
                        md_output += f"**{sender}**: {msg['message_content']}\n\n"
                    else:
                        md_output += f"*{sender}*: {msg['message_content']}\n\n"

                return md_output
            else:
                return None

        except Exception as e:
            print(f"[ConversationMemory] Error exporting conversation: {e}")
            return None