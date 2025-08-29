"""
Supabase pgvector RAG Agent
===========================
Clean, production-ready RAG implementation using Supabase pgvector.
Provides user-isolated, semantic search with proper error handling.
Replaces ChromaDB with native PostgreSQL vector operations.
"""

import logging
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import numpy as np

import openai
from supabase import Client

logger = logging.getLogger(__name__)


@dataclass
class RAGConfig:
    """Clean configuration for RAG settings"""
    model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-ada-002"  # More widely available model
    max_context_length: int = 8000
    min_relevance_score: float = 0.7
    max_results: int = 10
    temperature: float = 0.3
    collections_to_search: List[str] = field(default_factory=lambda: [
        'gsc_data', 'audit_results', 'seo_knowledge', 'user_interactions'
    ])


@dataclass
class SearchResult:
    """Clean structure for search results"""
    content: str
    relevance: float
    collection: str
    metadata: Dict
    created_at: datetime


class SupabaseRAGAgent:
    """
    Production-ready RAG agent using Supabase pgvector.
    Ensures user isolation, clean code patterns, and optimal performance.
    """
    
    def __init__(self, supabase_client: Client, openai_api_key: str, config: RAGConfig = None):
        """
        Initialize RAG agent with clean dependency injection.
        
        Args:
            supabase_client: Initialized Supabase client
            openai_api_key: OpenAI API key for embeddings
            config: Optional RAG configuration
        """
        self.supabase = supabase_client
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
        self.config = config or RAGConfig()
        
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text using OpenAI.
        
        Args:
            text: Input text to embed
            
        Returns:
            1536-dimensional embedding vector
        """
        try:
            response = self.openai_client.embeddings.create(
                model=self.config.embedding_model,
                input=text[:8000]  # Limit input length
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
            
    def _prepare_vector_for_postgres(self, embedding: List[float]) -> str:
        """
        Convert embedding to PostgreSQL vector format.
        
        Args:
            embedding: List of floats
            
        Returns:
            JSON string representation for PostgreSQL
        """
        return json.dumps(embedding)
        
    def _generate_document_id(self, content: str, collection: str, user_email: str) -> str:
        """
        Generate deterministic document ID for deduplication.
        
        Args:
            content: Document content
            collection: Collection name
            user_email: User email
            
        Returns:
            Unique document ID
        """
        id_string = f"{user_email}|{collection}|{content[:200]}"
        return hashlib.sha256(id_string.encode()).hexdigest()[:16]
        
    async def index_document(
        self,
        user_email: str,
        content: str,
        collection_name: str,
        metadata: Optional[Dict] = None,
        website_url: Optional[str] = None
    ) -> bool:
        """
        Index a document into Supabase pgvector with user isolation.
        
        Args:
            user_email: User's email for isolation
            content: Document content to index
            collection_name: Collection to store in
            metadata: Optional metadata
            website_url: Optional website URL
            
        Returns:
            Success status
        """
        try:
            # Generate embedding
            embedding = self._generate_embedding(content)
            
            # Generate unique document ID
            document_id = self._generate_document_id(content, collection_name, user_email)
            
            # Prepare data for insertion
            data = {
                'user_email': user_email,
                'website_url': website_url,
                'collection_name': collection_name,
                'document_id': document_id,
                'content': content[:10000],  # Limit content size
                'embedding': self._prepare_vector_for_postgres(embedding),
                'metadata': json.dumps(metadata or {}),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Upsert into Supabase (handles duplicates)
            result = self.supabase.table('embeddings').upsert(
                data,
                on_conflict='user_email,collection_name,document_id'
            ).execute()
            
            logger.debug(f"Indexed document for {user_email} in {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index document: {e}")
            return False
            
    async def search_similar(
        self,
        user_email: str,
        query: str,
        collections: Optional[List[str]] = None,
        website_url: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[SearchResult]:
        """
        Search for similar documents with user isolation.
        
        Args:
            user_email: User's email for isolation
            query: Search query
            collections: Optional list of collections to search
            website_url: Optional website filter
            limit: Maximum results
            
        Returns:
            List of search results ordered by relevance
        """
        try:
            # Generate query embedding
            query_embedding = self._generate_embedding(query)
            
            # Use configured collections if not specified
            collections = collections or self.config.collections_to_search
            limit = limit or self.config.max_results
            
            results = []
            
            # Search each collection
            for collection in collections:
                try:
                    # Call Supabase RPC function for vector search
                    response = self.supabase.rpc('search_embeddings', {
                        'query_embedding': query_embedding,
                        'query_user_email': user_email,
                        'query_collection': collection,
                        'match_count': limit,
                        'match_threshold': self.config.min_relevance_score
                    }).execute()
                    
                    # Parse results
                    for item in response.data:
                        results.append(SearchResult(
                            content=item['content'],
                            relevance=item['similarity'],
                            collection=item['collection_name'],
                            metadata=item['metadata'] if isinstance(item['metadata'], dict) else {},
                            created_at=datetime.fromisoformat(item['created_at'])
                        ))
                        
                except Exception as e:
                    logger.warning(f"Failed to search collection {collection}: {e}")
                    continue
                    
            # Sort by relevance and limit
            results.sort(key=lambda x: x.relevance, reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
            
    async def get_augmented_context(
        self,
        user_email: str,
        query: str,
        include_gsc_data: bool = True,
        include_audit_history: bool = True
    ) -> str:
        """
        Get augmented context for AI response generation.
        
        Args:
            user_email: User's email
            query: User query
            include_gsc_data: Include GSC metrics
            include_audit_history: Include past audits
            
        Returns:
            Formatted context string for AI
        """
        try:
            # Search for relevant documents
            results = await self.search_similar(
                user_email=user_email,
                query=query,
                collections=['gsc_data', 'audit_results', 'seo_knowledge', 'user_interactions']
            )
            
            if not results:
                return ""
                
            # Build context with clean formatting
            context_parts = []
            
            # Group results by collection for better organization
            by_collection = {}
            for result in results:
                if result.collection not in by_collection:
                    by_collection[result.collection] = []
                by_collection[result.collection].append(result)
                
            # Format each collection's results
            for collection, items in by_collection.items():
                collection_context = f"\n## {self._format_collection_name(collection)}:\n"
                
                for item in items[:3]:  # Limit items per collection
                    # Add relevance indicator
                    relevance_indicator = "⭐" * min(5, int(item.relevance * 5))
                    
                    # Format metadata if present
                    metadata_str = ""
                    if item.metadata:
                        important_keys = ['date', 'source', 'type', 'severity']
                        metadata_parts = [
                            f"{k}: {v}" for k, v in item.metadata.items()
                            if k in important_keys and v
                        ]
                        if metadata_parts:
                            metadata_str = f" ({', '.join(metadata_parts)})"
                    
                    # Add to context
                    collection_context += f"\n{relevance_indicator} {item.content[:500]}{metadata_str}\n"
                    
                context_parts.append(collection_context)
                
            # Combine all context
            full_context = "\n".join(context_parts)
            
            # Ensure context fits within limits
            if len(full_context) > self.config.max_context_length:
                full_context = full_context[:self.config.max_context_length] + "..."
                
            return full_context
            
        except Exception as e:
            logger.error(f"Failed to get augmented context: {e}")
            return ""
            
    def _format_collection_name(self, collection: str) -> str:
        """Format collection name for display"""
        formatting = {
            'gsc_data': '📊 Google Search Console Data',
            'audit_results': '🔍 SEO Audit Results',
            'seo_knowledge': '📚 SEO Best Practices',
            'user_interactions': '💬 Previous Conversations',
            'website_content': '🌐 Website Content'
        }
        return formatting.get(collection, collection.replace('_', ' ').title())
        
    async def generate_response(
        self,
        user_email: str,
        query: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """
        Generate AI response with RAG augmentation.
        
        Args:
            user_email: User's email
            query: User query
            conversation_history: Optional conversation context
            
        Returns:
            AI-generated response
        """
        try:
            # Get augmented context
            context = await self.get_augmented_context(user_email, query)
            
            # Build messages for OpenAI
            messages = [
                {
                    "role": "system",
                    "content": """You are Solvia, an expert SEO assistant with access to the user's real Google Search Console data and audit history.
                    Use the provided context to give specific, data-driven advice. Always reference actual metrics when available.
                    Be concise but thorough. Focus on actionable recommendations."""
                }
            ]
            
            # Add conversation history if provided
            if conversation_history:
                for msg in conversation_history[-5:]:  # Last 5 messages
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })
                    
            # Add context and query
            if context:
                messages.append({
                    "role": "system",
                    "content": f"Relevant context from your data:\n{context}"
                })
                
            messages.append({
                "role": "user",
                "content": query
            })
            
            # Generate response
            response = self.openai_client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return "I encountered an error while processing your request. Please try again."
            
    async def index_audit_results(
        self,
        user_email: str,
        website_url: str,
        audit_data: Dict
    ) -> bool:
        """
        Index audit results for future RAG retrieval.
        
        Args:
            user_email: User's email
            website_url: Website URL
            audit_data: Audit results dictionary
            
        Returns:
            Success status
        """
        try:
            # Index overall audit summary
            summary_content = f"""
            SEO Audit for {website_url}
            Date: {audit_data.get('audit_date', datetime.now().isoformat())}
            Overall Score: {audit_data.get('seo_score', 'N/A')}/100
            Critical Issues: {len(audit_data.get('critical_issues', []))}
            Total Issues: {len(audit_data.get('issues', []))}
            """
            
            await self.index_document(
                user_email=user_email,
                content=summary_content,
                collection_name='audit_results',
                metadata={
                    'type': 'audit_summary',
                    'website': website_url,
                    'score': audit_data.get('seo_score'),
                    'date': audit_data.get('audit_date')
                },
                website_url=website_url
            )
            
            # Index each issue for granular search
            for issue in audit_data.get('issues', []):
                issue_content = f"""
                Issue: {issue.get('title', 'Unknown')}
                Severity: {issue.get('severity', 'Unknown')}
                Category: {issue.get('category', 'Unknown')}
                Description: {issue.get('description', '')}
                Recommendation: {issue.get('recommendation', '')}
                Impact: {issue.get('impact', '')}
                """
                
                await self.index_document(
                    user_email=user_email,
                    content=issue_content,
                    collection_name='audit_results',
                    metadata={
                        'type': 'audit_issue',
                        'severity': issue.get('severity'),
                        'category': issue.get('category'),
                        'website': website_url,
                        'date': audit_data.get('audit_date')
                    },
                    website_url=website_url
                )
                
            logger.info(f"Indexed audit results for {user_email} - {website_url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index audit results: {e}")
            return False
            
    async def get_user_stats(self, user_email: str) -> Dict:
        """
        Get user's embedding statistics.
        
        Args:
            user_email: User's email
            
        Returns:
            Statistics dictionary
        """
        try:
            response = self.supabase.rpc('get_user_embeddings_stats', {
                'query_user_email': user_email
            }).execute()
            
            stats = {
                'total_documents': 0,
                'collections': {}
            }
            
            for item in response.data:
                stats['total_documents'] += item['document_count']
                stats['collections'][item['collection_name']] = {
                    'count': item['document_count'],
                    'last_updated': item['last_updated']
                }
                
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get user stats: {e}")
            return {'total_documents': 0, 'collections': {}}