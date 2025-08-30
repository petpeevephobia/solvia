"""
Keyword-Based RAG Agent (No Embeddings Required)
=================================================
Production-ready RAG implementation using PostgreSQL full-text search.
Provides user-isolated, keyword-based search with proper error handling.
Fallback solution when embedding models are not available.
"""

import logging
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

import openai
from supabase import Client

logger = logging.getLogger(__name__)


@dataclass
class KeywordRAGConfig:
    """Clean configuration for keyword-based RAG settings"""
    model: str = "gpt-4o-mini"
    max_context_length: int = 8000
    min_rank_score: float = 0.01  # Lowered from 0.1 for better recall
    max_results: int = 10
    temperature: float = 0.3
    collections_to_search: List[str] = field(default_factory=lambda: [
        'gsc_data', 'audit_results', 'seo_knowledge', 'user_interactions'
    ])


@dataclass
class KeywordSearchResult:
    """Clean structure for keyword search results"""
    content: str
    rank_score: float
    collection: str
    metadata: Dict
    created_at: datetime
    matched_terms: List[str]


class KeywordRAGAgent:
    """
    Production-ready keyword-based RAG agent using PostgreSQL full-text search.
    No embeddings required - uses PostgreSQL's native text search capabilities.
    Ensures user isolation, clean code patterns, and optimal performance.
    """
    
    def __init__(self, supabase_client: Client, openai_api_key: str, config: KeywordRAGConfig = None):
        """
        Initialize keyword RAG agent with clean dependency injection.
        
        Args:
            supabase_client: Initialized Supabase client
            openai_api_key: OpenAI API key for chat completions only
            config: Optional RAG configuration
        """
        self.supabase = supabase_client
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
        self.config = config or KeywordRAGConfig()
        
        # Create service role client for RLS bypass (RAG operations need system access)
        import os
        service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        if service_role_key:
            from supabase import create_client
            self.service_supabase = create_client(
                os.getenv('SUPABASE_URL'),
                service_role_key
            )
        else:
            self.service_supabase = self.supabase
        
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
        
    def _create_search_vector(self, content: str) -> str:
        """
        Create PostgreSQL tsvector from content for full-text search.
        
        Args:
            content: Content to vectorize
            
        Returns:
            Content prepared for tsvector creation
        """
        # Clean and prepare content for better search
        cleaned = content.lower().strip()
        
        # Remove extra whitespace and normalize
        words = cleaned.split()
        normalized_content = ' '.join(words)
        
        return normalized_content[:5000]  # Limit for performance
        
    async def index_document(
        self,
        user_email: str,
        content: str,
        collection_name: str,
        metadata: Optional[Dict] = None,
        website_url: Optional[str] = None
    ) -> bool:
        """
        Index a document into keyword search with user isolation.
        
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
            # Generate unique document ID
            document_id = self._generate_document_id(content, collection_name, user_email)
            
            # Prepare search-optimized content
            search_content = self._create_search_vector(content)
            
            # Prepare data for insertion
            data = {
                'user_email': user_email,
                'website_url': website_url,
                'collection_name': collection_name,
                'document_id': document_id,
                'content': content[:10000],  # Full content for display
                'search_content': search_content,  # Optimized for search
                'metadata': json.dumps(metadata or {}),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Use service role client for RAG operations (bypasses RLS)
            result = self.service_supabase.table('keyword_documents').upsert(
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
    ) -> List[KeywordSearchResult]:
        """
        Search for similar documents using PostgreSQL full-text search.
        
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
            # Use configured collections if not specified
            collections = collections or self.config.collections_to_search
            limit = limit or self.config.max_results
            
            # Prepare search query for PostgreSQL
            search_query = self._prepare_search_query(query)
            
            results = []
            
            # Search each collection
            for collection in collections:
                try:
                    # Call Supabase RPC function for keyword search
                    response = self.service_supabase.rpc('search_documents_fulltext', {
                        'search_query': search_query,
                        'query_user_email': user_email,
                        'query_collection': collection,
                        'match_count': limit,
                        'min_rank': self.config.min_rank_score,
                        'website_filter': website_url
                    }).execute()
                    
                    # Parse results
                    for item in response.data:
                        matched_terms = self._extract_matched_terms(query, item['content'])
                        
                        results.append(KeywordSearchResult(
                            content=item['content'],
                            rank_score=float(item['rank_score']) if item['rank_score'] else 0.0,
                            collection=item['collection_name'],
                            metadata=item['metadata'] if isinstance(item['metadata'], dict) else {},
                            created_at=datetime.fromisoformat(item['created_at']),
                            matched_terms=matched_terms
                        ))
                        
                except Exception as e:
                    logger.warning(f"Failed to search collection {collection}: {e}")
                    continue
                    
            # Sort by rank score and limit
            results.sort(key=lambda x: x.rank_score, reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
            
    def _prepare_search_query(self, query: str) -> str:
        """
        Prepare query for PostgreSQL full-text search.
        
        Args:
            query: Raw search query
            
        Returns:
            Formatted query for tsquery
        """
        # Clean and prepare query
        words = query.lower().strip().split()
        
        # Remove common stop words but keep important SEO terms
        stop_words = {'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 
                     'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 
                     'that', 'the', 'to', 'was', 'will', 'with'}
        
        filtered_words = [w for w in words if len(w) > 2 and w not in stop_words]
        
        if not filtered_words:
            filtered_words = words  # Fallback to original if all filtered
            
        # Use both AND and OR for flexible matching
        if len(filtered_words) > 1:
            # Try AND first for exact matches, fallback to OR
            and_query = ' & '.join(filtered_words[:5])
            or_query = ' | '.join(filtered_words[:8])
            return f"({and_query}) | ({or_query})"
        else:
            return filtered_words[0] if filtered_words else query
        
    def _extract_matched_terms(self, query: str, content: str) -> List[str]:
        """
        Extract which terms from the query matched in the content.
        
        Args:
            query: Original search query
            content: Matched content
            
        Returns:
            List of matched terms
        """
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        
        matches = query_words.intersection(content_words)
        return list(matches)
        
    async def get_augmented_context(
        self,
        user_email: str,
        query: str,
        include_gsc_data: bool = True,
        include_audit_history: bool = True
    ) -> str:
        """
        Get augmented context for AI response generation using keyword search.
        
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
                    # Add rank indicator (star rating based on rank score)
                    stars = min(5, max(1, int(item.rank_score * 10)))
                    rank_indicator = "★" * stars
                    
                    # Show matched terms if available
                    matched_terms_str = ""
                    if item.matched_terms:
                        matched_terms_str = f" [Matched: {', '.join(item.matched_terms[:3])}]"
                    
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
                    collection_context += f"\n{rank_indicator} {item.content[:500]}{matched_terms_str}{metadata_str}\n"
                    
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
        Generate AI response with keyword-based RAG augmentation.
        
        Args:
            user_email: User's email
            query: User query
            conversation_history: Optional conversation context
            
        Returns:
            AI-generated response
        """
        try:
            # Get augmented context using keyword search
            context = await self.get_augmented_context(user_email, query)
            
            # Build messages for OpenAI
            messages = [
                {
                    "role": "system",
                    "content": """You are Solvia, an expert SEO assistant with access to the user's real Google Search Console data and audit history.
                    Use the provided context to give specific, data-driven advice. Always reference actual metrics when available.
                    Be concise but thorough. Focus on actionable recommendations.
                    
                    Note: You're using keyword-based search (not semantic), so focus on exact terms and phrases mentioned in the context."""
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
                    "content": f"Relevant context from your data (keyword search):\n{context}"
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
        Index audit results for future keyword-based RAG retrieval.
        
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
            SEO Audit Summary for {website_url}
            Date: {audit_data.get('audit_date', datetime.now().isoformat())}
            SEO Score: {audit_data.get('seo_score', 'N/A')} out of 100
            Critical Issues Found: {len(audit_data.get('critical_issues', []))}
            Total Issues Detected: {len(audit_data.get('issues', []))}
            Performance Analysis: {audit_data.get('performance_summary', '')}
            Traffic Analysis: {audit_data.get('traffic_summary', '')}
            Technical SEO Status: {audit_data.get('technical_summary', '')}
            """
            
            await self.index_document(
                user_email=user_email,
                content=summary_content,
                collection_name='audit_results',
                metadata={
                    'type': 'audit_summary',
                    'website': website_url,
                    'score': audit_data.get('seo_score'),
                    'date': audit_data.get('audit_date'),
                    'critical_count': len(audit_data.get('critical_issues', []))
                },
                website_url=website_url
            )
            
            # Index each issue for granular search
            for issue in audit_data.get('issues', []):
                issue_content = f"""
                SEO Issue: {issue.get('title', 'Unknown Issue')}
                Severity Level: {issue.get('severity', 'Unknown')}
                Category: {issue.get('category', 'General')}
                Problem Description: {issue.get('description', '')}
                Recommended Solution: {issue.get('recommendation', '')}
                Business Impact: {issue.get('impact', '')}
                Technical Details: {issue.get('technical_details', '')}
                Priority Score: {issue.get('priority_score', 0)}
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
                        'date': audit_data.get('audit_date'),
                        'priority': issue.get('priority_score', 0)
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
        Get user's document statistics for keyword search.
        
        Args:
            user_email: User's email
            
        Returns:
            Statistics dictionary
        """
        try:
            response = self.service_supabase.rpc('get_user_document_stats', {
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