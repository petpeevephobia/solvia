"""
Chat Integration with Adaptive RAG System
==========================================
Clean integration layer for chat functionality using adaptive RAG.
Automatically switches between keyword-based and vector-based RAG.
"""

import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import json

from app.agent.rag_factory import RAGFactory
from app.agent.keyword_rag_agent import KeywordRAGAgent
from app.agent.supabase_rag_agent import SupabaseRAGAgent
from app.database.supabase_db import SupabaseAuthDB

logger = logging.getLogger(__name__)


class ChatIntegrationSupabase:
    """
    Clean chat integration using adaptive RAG system.
    Handles chat messages, context retrieval, and audit indexing.
    Automatically switches between keyword and vector RAG based on API capabilities.
    """
    
    def __init__(self):
        """Initialize chat integration with dependency injection"""
        self.db = SupabaseAuthDB()
        self.rag_agent: Optional[Union[KeywordRAGAgent, SupabaseRAGAgent]] = None
        self.rag_mode: str = "unknown"
        self._init_rag_agent()
        
    def _init_rag_agent(self):
        """Initialize RAG agent with auto-detection"""
        try:
            import os
            from dotenv import load_dotenv
            load_dotenv()
            
            openai_key = os.getenv('OPENAI_API_KEY')
            if not openai_key:
                raise ValueError("OPENAI_API_KEY not found in environment")
            
            # Test capabilities and create appropriate agent
            capabilities = RAGFactory.test_rag_capabilities(openai_key)
            
            # Create RAG agent using factory
            self.rag_agent = RAGFactory.create_rag_agent(
                supabase_client=self.db.supabase,
                openai_api_key=openai_key,
                mode=os.getenv('RAG_MODE', 'auto')
            )
            
            self.rag_mode = "vector" if isinstance(self.rag_agent, SupabaseRAGAgent) else "keyword"
            
            logger.info(f"✅ RAG agent initialized successfully in {self.rag_mode} mode")
            logger.info(f"   Chat API: {'✅' if capabilities['chat'] else '❌'}")
            logger.info(f"   Embeddings API: {'✅' if capabilities['embeddings'] else '❌'}")
            logger.info(f"   Recommended mode: {capabilities['recommended_mode']}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase RAG agent: {e}")
            self.rag_agent = None
            
    async def process_chat_message(
        self,
        user_email: str,
        message: str,
        website_url: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """
        Process a chat message with RAG augmentation.
        
        Args:
            user_email: User's email for isolation
            message: User's message
            website_url: Optional website context
            conversation_history: Previous conversation
            
        Returns:
            AI response with RAG context
        """
        try:
            if not self.rag_agent:
                return "I'm having trouble accessing the knowledge base. Please try again."
                
            # Store user message in chat history
            await self.db.store_chat_message(
                user_email=user_email,
                message_content=message,
                message_type="user",
                sender_name="User"
            )
            
            # Index the conversation for future retrieval
            await self.rag_agent.index_document(
                user_email=user_email,
                content=f"User question: {message}",
                collection_name="user_interactions",
                metadata={
                    "type": "chat",
                    "timestamp": datetime.now().isoformat(),
                    "website": website_url
                },
                website_url=website_url
            )
            
            # Generate response with RAG
            response = await self.rag_agent.generate_response(
                user_email=user_email,
                query=message,
                conversation_history=conversation_history
            )
            
            # Store AI response
            await self.db.store_chat_message(
                user_email=user_email,
                message_content=response,
                message_type="ai",
                sender_name="Solvia"
            )
            
            # Index the response for learning
            await self.rag_agent.index_document(
                user_email=user_email,
                content=f"Solvia response: {response}",
                collection_name="user_interactions",
                metadata={
                    "type": "chat_response",
                    "timestamp": datetime.now().isoformat(),
                    "website": website_url
                },
                website_url=website_url
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            return "I encountered an error while processing your request. Please try again."
            
    async def index_gsc_data(
        self,
        user_email: str,
        website_url: str,
        gsc_data: Dict[str, Any]
    ) -> bool:
        """
        Index GSC data for RAG retrieval.
        
        Args:
            user_email: User's email
            website_url: Website URL
            gsc_data: GSC metrics data
            
        Returns:
            Success status
        """
        try:
            if not self.rag_agent:
                return False
                
            # Format GSC data for indexing
            content = f"""
            Google Search Console Data for {website_url}
            Date Range: {gsc_data.get('start_date', 'N/A')} to {gsc_data.get('end_date', 'N/A')}
            Total Clicks: {gsc_data.get('clicks', 0):,}
            Total Impressions: {gsc_data.get('impressions', 0):,}
            Average CTR: {gsc_data.get('ctr', 0):.2%}
            Average Position: {gsc_data.get('avg_position', 0):.1f}
            """
            
            # Add top queries if available
            if 'top_queries' in gsc_data:
                content += "\n\nTop Search Queries:\n"
                for query in gsc_data['top_queries'][:10]:
                    content += f"- {query['query']}: {query['clicks']} clicks, position {query['position']:.1f}\n"
                    
            # Add top pages if available
            if 'top_pages' in gsc_data:
                content += "\n\nTop Pages:\n"
                for page in gsc_data['top_pages'][:10]:
                    content += f"- {page['page']}: {page['clicks']} clicks, {page['impressions']} impressions\n"
                    
            # Index in Supabase
            success = await self.rag_agent.index_document(
                user_email=user_email,
                content=content,
                collection_name='gsc_data',
                metadata={
                    'type': 'gsc_metrics',
                    'date_range': f"{gsc_data.get('start_date')}_{gsc_data.get('end_date')}",
                    'total_clicks': gsc_data.get('clicks', 0),
                    'total_impressions': gsc_data.get('impressions', 0),
                    'avg_ctr': gsc_data.get('ctr', 0),
                    'avg_position': gsc_data.get('avg_position', 0)
                },
                website_url=website_url
            )
            
            logger.info(f"✅ Indexed GSC data for {user_email} - {website_url}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to index GSC data: {e}")
            return False
            
    async def index_audit_results(
        self,
        user_email: str,
        website_url: str,
        audit_data: Dict[str, Any]
    ) -> bool:
        """
        Index audit results for RAG retrieval.
        
        Args:
            user_email: User's email
            website_url: Website URL
            audit_data: Audit results
            
        Returns:
            Success status
        """
        try:
            if not self.rag_agent:
                return False
                
            # Use the RAG agent's built-in audit indexing
            success = await self.rag_agent.index_audit_results(
                user_email=user_email,
                website_url=website_url,
                audit_data=audit_data
            )
            
            logger.info(f"✅ Indexed audit results for {user_email} - {website_url}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to index audit results: {e}")
            return False
            
    async def get_chat_context(
        self,
        user_email: str,
        query: str,
        website_url: Optional[str] = None
    ) -> str:
        """
        Get augmented context for a chat query.
        
        Args:
            user_email: User's email
            query: User query
            website_url: Optional website filter
            
        Returns:
            Formatted context string
        """
        try:
            if not self.rag_agent:
                return ""
                
            context = await self.rag_agent.get_augmented_context(
                user_email=user_email,
                query=query,
                include_gsc_data=True,
                include_audit_history=True
            )
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to get chat context: {e}")
            return ""
            
    async def get_user_stats(self, user_email: str) -> Dict:
        """
        Get user's RAG statistics.
        
        Args:
            user_email: User's email
            
        Returns:
            Statistics dictionary
        """
        try:
            if not self.rag_agent:
                return {'total_documents': 0, 'collections': {}}
                
            stats = await self.rag_agent.get_user_stats(user_email)
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get user stats: {e}")
            return {'total_documents': 0, 'collections': {}}


# Global instance for easy access
chat_integration = ChatIntegrationSupabase()