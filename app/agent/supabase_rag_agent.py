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
    embedding_model: str = "text-embedding-3-small"  # Available in new API key
    max_context_length: int = 8000
    min_relevance_score: float = 0.3  # Lowered from 0.7 for better recall
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
            
            # Use service role client for RAG operations (bypasses RLS)
            result = self.service_supabase.table('embeddings').upsert(
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
                    response = self.service_supabase.rpc('search_embeddings', {
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
    
    async def _get_current_audit_data(self, user_email: str) -> str:
        """
        Get current audit data and GSC metrics for the user.
        
        Args:
            user_email: User's email
            
        Returns:
            Formatted audit data string for AI context
        """
        try:
            # Try to get recent audit data from database
            from app.database.supabase_db import SupabaseAuthDB
            db = SupabaseAuthDB()
            
            # Get user's website
            website_url = db.get_user_website(user_email)
            if not website_url:
                return "No website selected. Please select a website first."
            
            # Get latest audit from database
            latest_audit = db.get_latest_audit(user_email, website_url)
            
            # Also get current GSC metrics cache
            try:
                gsc_cache = self.service_supabase.table('gsc_metrics_cache').select('*').eq('user_email', user_email).eq('website_url', website_url).order('cache_date', desc=True).limit(1).execute()
                current_metrics = gsc_cache.data[0] if gsc_cache.data else None
            except:
                current_metrics = None
            
            # Format audit data for AI context
            if latest_audit and latest_audit.get('audit_data'):
                audit_data = latest_audit['audit_data']
                
                # Format the audit data
                formatted_data = f"""
Website: {website_url}
Audit Date: {latest_audit.get('created_at', 'Unknown')}
SEO Score: {latest_audit.get('seo_score', 'N/A')}/100

Audit Summary:
- Critical Issues: {latest_audit.get('critical_issues', 0)}
- High Issues: {latest_audit.get('high_issues', 0)}
- Medium Issues: {latest_audit.get('medium_issues', 0)}
- Total Issues: {latest_audit.get('total_issues', 0)}

"""
                
                # Add current GSC metrics if available
                if current_metrics:
                    formatted_data += f"""
Current GSC Metrics (Last 30 days):
- Clicks: {current_metrics.get('clicks', 0)}
- Impressions: {current_metrics.get('impressions', 0)}
- CTR: {current_metrics.get('ctr', 0):.2f}%
- Average Position: {current_metrics.get('avg_position', 0):.1f}
- Cache Date: {current_metrics.get('cache_date', 'Unknown')}

"""
                
                # Add specific issues if available in audit data
                if isinstance(audit_data, dict) and 'issues' in audit_data:
                    formatted_data += "\nSpecific Issues Found:\n"
                    for i, issue in enumerate(audit_data['issues'][:5], 1):  # Top 5 issues
                        if isinstance(issue, dict):
                            formatted_data += f"{i}. {issue.get('title', 'Unknown Issue')} (Severity: {issue.get('severity', 'Unknown')})\n"
                            if issue.get('description'):
                                formatted_data += f"   Description: {issue['description'][:100]}...\n"
                
                return formatted_data.strip()
            
            # Fallback to just current metrics if no audit available
            elif current_metrics:
                return f"""
Website: {website_url}
Current GSC Metrics (Last 30 days):
- Clicks: {current_metrics.get('clicks', 0)}
- Impressions: {current_metrics.get('impressions', 0)}
- CTR: {current_metrics.get('ctr', 0):.2f}%
- Average Position: {current_metrics.get('avg_position', 0):.1f}
- SEO Score: {current_metrics.get('seo_score', 25.0)}/100
- Cache Date: {current_metrics.get('cache_date', 'Unknown')}

Note: No recent audit data available. Consider running a new audit for detailed insights.
"""
            
            # No data available
            else:
                return f"""
Website: {website_url}
No recent audit or GSC data available.
Please refresh your dashboard to load current metrics or run a new audit.
"""
                
        except Exception as e:
            logger.error(f"Failed to get current audit data: {e}")
            return "Unable to retrieve current audit data. Please try refreshing your dashboard."
            
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
            
            # Get current GSC metrics for the user
            current_audit_data = await self._get_current_audit_data(user_email)
            
            # Enhanced system prompt with actual data injection
            enhanced_prompt = f"""You are Solvia, an expert SEO analyst that provides insights based EXCLUSIVELY on real Google Search Console data and audit results. You NEVER make up data or provide generic advice.

## CRITICAL INSTRUCTIONS:
1. ONLY use numbers, metrics, and data points that are explicitly provided in the context
2. If specific data is not available, say "I don't have that data in the current audit"
3. Always cite exact numbers with their date ranges
4. Never use placeholder values or estimates
5. Every insight must reference actual data from the provided context

## DATA CONTEXT PROVIDED TO YOU:
<audit_data>
{current_audit_data}
</audit_data>

## YOUR RESPONSE RULES:

### When analyzing SEO performance:
- State the EXACT SEO score: "Your SEO score is [exact_number]/100"
- Use ACTUAL metrics: "[exact_clicks] clicks from [exact_impressions] impressions"
- Reference REAL date ranges: "Based on data from [start_date] to [end_date]"
- Compare with ACTUAL historical data if available in context

### When identifying issues:
- Only mention issues that exist in the audit_data or context
- Cite specific affected pages with their exact URLs if available
- Provide exact impact metrics from the data
- Never invent problems that aren't in the data

### When making recommendations:
- Base every suggestion on a specific data point from the audit
- Prioritize based on actual impact scores in the data
- Never suggest generic SEO tactics without data backing

### When answering questions:
- "What are my top issues?" → List ONLY issues from the audit_data with their exact details
- "Show me traffic trends" → Reference ONLY the exact metrics and changes in the data
- "How is my site doing?" → Provide the EXACT seo_score and metrics

## HANDLING MISSING DATA:
If asked about data not in the context, respond:
"I don't have [specific_metric] data in your current audit. I can analyze the GSC metrics currently available based on your actual Google Search Console data."

Remember: You are a data analyst, not a fortune teller. Only state what the data explicitly shows."""
            
            # Build messages for OpenAI
            messages = [
                {
                    "role": "system",
                    "content": enhanced_prompt
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
            response = self.service_supabase.rpc('get_user_embeddings_stats', {
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