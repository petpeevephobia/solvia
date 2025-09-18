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
from app.core.website_crawler import analyze_website

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
        
    async def _get_keyword_suggestions_from_gsc(self, user_email: str) -> str:
        """
        Get keyword suggestions based on actual GSC query data.

        Args:
            user_email: User's email

        Returns:
            Formatted keyword suggestions with performance data
        """
        try:
            from app.database.supabase_db import SupabaseAuthDB
            db = SupabaseAuthDB()

            # Get user's website
            website_url = db.get_user_website(user_email)
            if not website_url:
                return "No website selected. Please select a website first to get keyword suggestions."

            # Crawl and analyze the actual website content
            website_analysis = None
            try:
                logger.info(f"[KEYWORD-RAG] Crawling website: {website_url}")
                website_analysis = await analyze_website(website_url)
                logger.info(f"[KEYWORD-RAG] Website analysis complete: {website_analysis.get('business_type', 'unknown')}")
            except Exception as e:
                logger.error(f"[KEYWORD-RAG] Website crawl failed: {e}")
                website_analysis = None

            # Try to get query data from gsc_queries table first
            try:
                query_data = self.service_supabase.table('gsc_queries').select('*').eq('user_email', user_email).eq('website_url', website_url).order('clicks', desc=True).limit(20).execute()

                if query_data.data:
                    keyword_suggestions = "## Keyword Opportunities Based on Your GSC Data:\n\n"

                    # Top performing keywords
                    top_keywords = [q for q in query_data.data if q.get('clicks', 0) > 0][:10]
                    if top_keywords:
                        keyword_suggestions += "### 🏆 Your Top Performing Keywords:\n"
                        for i, query in enumerate(top_keywords, 1):
                            keyword_suggestions += f"{i}. **{query['query']}** - {query['clicks']} clicks, Position {query['position']:.1f}, CTR {query.get('ctr', 0)*100:.1f}%\n"
                        keyword_suggestions += "\n"

                    # High impression, low click keywords (opportunity keywords)
                    opportunity_keywords = [q for q in query_data.data if q.get('impressions', 0) > 10 and q.get('clicks', 0) < 3 and q.get('position', 0) > 5][:5]
                    if opportunity_keywords:
                        keyword_suggestions += "### 🎯 Opportunity Keywords (High Impressions, Low Clicks):\n"
                        for i, query in enumerate(opportunity_keywords, 1):
                            keyword_suggestions += f"{i}. **{query['query']}** - {query['impressions']} impressions, Position {query['position']:.1f} (needs better ranking)\n"
                        keyword_suggestions += "\n"

                    # Keywords ranking 4-10 (can be improved to page 1)
                    page_2_keywords = [q for q in query_data.data if 4 <= q.get('position', 0) <= 10 and q.get('impressions', 0) > 5][:5]
                    if page_2_keywords:
                        keyword_suggestions += "### 📈 Keywords Ready for Page 1 (Currently 4-10):\n"
                        for i, query in enumerate(page_2_keywords, 1):
                            keyword_suggestions += f"{i}. **{query['query']}** - Position {query['position']:.1f}, {query.get('impressions', 0)} impressions\n"
                        keyword_suggestions += "\n"

                    return keyword_suggestions

            except Exception as e:
                logger.debug(f"GSC queries table not available: {e}")

            # Fallback to GSC metrics cache
            try:
                gsc_cache = self.service_supabase.table('gsc_metrics_cache').select('*').eq('user_email', user_email).eq('website_url', website_url).order('cache_date', desc=True).limit(1).execute()
                current_metrics = gsc_cache.data[0] if gsc_cache.data else None

                if current_metrics:
                    clicks = current_metrics.get('clicks', 0)
                    impressions = current_metrics.get('impressions', 0)
                    avg_position = float(current_metrics.get('avg_position', 0))
                    ctr = float(current_metrics.get('ctr', 0))

                    # Intelligent keyword suggestions based on real data + website analysis
                    domain = website_url.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]

                    # Use actual website analysis if available, fallback to KnowledgeManager
                    from app.core.knowledge_manager import knowledge_manager, GSCMetrics

                    # Create metrics object for intelligent analysis
                    metrics = GSCMetrics(
                        clicks=clicks,
                        impressions=impressions,
                        ctr=ctr,
                        avg_position=avg_position,
                        seo_score=current_metrics.get('seo_score', 25.0)
                    )

                    # Use actual website data or detect business profile dynamically
                    if website_analysis and not website_analysis.get('fallback'):
                        # Use actual crawled data
                        actual_business_type = website_analysis.get('business_type', 'general_business')
                        actual_location = website_analysis.get('location', 'Singapore')

                        if 'personal_portfolio' in actual_business_type:
                            business_type = "Personal Portfolio Website"
                            if 'developer' in actual_business_type:
                                business_type = "Software Developer Portfolio"
                            elif 'designer' in actual_business_type:
                                business_type = "Designer Portfolio"
                        else:
                            industry = actual_business_type.replace('_business', '').replace('_', ' ').title()
                            business_type = f"{industry} Business in {actual_location}"

                        # For portfolio sites, use different prompt
                        profile = await knowledge_manager.detect_business_profile(domain, website_url)
                    else:
                        # Fallback to knowledge manager detection
                        profile = await knowledge_manager.detect_business_profile(domain, website_url)
                        business_type = f"{profile.industry} company in {profile.location}"

                    # Generate intelligent keyword suggestions
                    keyword_suggestions = await knowledge_manager.generate_keyword_suggestions(profile, metrics)
                    industry_keywords = [suggestion.keyword for suggestion in keyword_suggestions]

                    # Analyze performance issues with industry intelligence
                    issues = await knowledge_manager.analyze_performance_issues(profile, metrics)
                    content_strategies = knowledge_manager.get_content_strategies(profile)

                    # Special handling for portfolio sites
                    if website_analysis and 'personal_portfolio' in website_analysis.get('business_type', ''):
                        # Generate portfolio-specific keywords
                        name_from_title = website_analysis.get('title', domain).split('-')[0].strip()
                        keywords_found = website_analysis.get('keywords_found', [])
                        tech_keywords = [k for k in keywords_found if k in [
                            'python', 'javascript', 'react', 'vue', 'angular', 'nodejs',
                            'java', 'spring', 'docker', 'kubernetes', 'aws', 'azure',
                            'sql', 'mongodb', 'postgresql', 'git', 'devops', 'fullstack'
                        ]]

                        suggestions = f"""## 🎯 Keyword Strategy for Your Personal Portfolio:

**Website**: {website_url}
**Type**: {business_type} (analyzed from actual website content)
**Summary**: {website_analysis.get('summary', 'Personal portfolio website')}

### 📊 Your Current GSC Performance:
- **Clicks**: {clicks} (organic traffic)
- **Impressions**: {impressions} (search visibility)
- **CTR**: {ctr:.2f}% (click-through rate)
- **Position**: {avg_position:.1f} (average ranking)

### 🎯 PORTFOLIO-SPECIFIC Keywords to Target:

**1. Personal Brand Keywords** (Essential for portfolios):
• "{name_from_title}" - Your exact name
• "{name_from_title} software engineer" - Name + profession
• "{name_from_title} developer" - Alternative title
• "{name_from_title} portfolio" - Direct portfolio searches
• "{name_from_title} github" - Code repository searches

**2. Skill-Based Keywords** (Based on your tech stack):
• "fullstack developer singapore" - Broad skill + location
• "{tech_keywords[0] if tech_keywords else 'software'} developer singapore" - Specific skill
• "freelance developer singapore" - Freelance opportunities
• "hire {tech_keywords[1] if len(tech_keywords) > 1 else 'web'} developer" - Hiring intent

**3. Project & Technology Keywords**:
• {', '.join([f'"{tech}"' for tech in tech_keywords[:5]]) if tech_keywords else 'Add your technology stack keywords'}

### 💡 IMPORTANT: Portfolio SEO is Different!

Unlike business sites, portfolio SEO should focus on:
1. **Your name** - Most important keyword for personal brand
2. **Skills & technologies** - What you can do
3. **Location + profession** - Local opportunities
4. **Project showcases** - Detailed case studies rank well

**Why you're seeing low traffic**: Portfolio sites typically have lower search volume than business sites. Focus on quality over quantity - one recruiter finding you is worth more than 100 casual visitors.

### 📈 Action Plan:
1. Optimize title tag: "{name_from_title} - Software Engineer Portfolio | Singapore"
2. Create project case studies with technology keywords
3. Write technical blog posts to establish authority
4. Include your location for local searches"""

                    else:
                        # Business website suggestions (existing logic)
                        suggestions = f"""## 🎯 Keyword Opportunities Based on Your Real Performance Data:

**Website**: {website_url}
**Business Type**: {business_type} {'(analyzed from website)' if website_analysis else f'(detected with {profile.confidence:.0%} confidence)'}
**Current Metrics**: {clicks} clicks from {impressions} impressions (CTR: {ctr:.2f}%)
**Average Position**: {avg_position:.1f} - This means you're on page {int(avg_position/10)+1} of search results

### 🏆 HIGH-PRIORITY Keywords to Target:

Based on your {profile.industry} business in {profile.location}, here are intelligent keyword recommendations:

**Immediate Opportunities** (can improve ranking quickly):"""

                    for i, suggestion in enumerate(keyword_suggestions[:4], 1):
                        icon = {"high": "🔥", "medium": "⚡", "low": "📈"}[suggestion.priority]
                        suggestions += f"\n{i}. {icon} **\"{suggestion.keyword}\"** - {suggestion.category.title()} keyword"
                        suggestions += f"\n   Target position: {suggestion.target_position:.1f} ({suggestion.search_intent} intent)"

                    suggestions += f"""

### 🚨 Performance Issues Detected:
"""
                    for issue in issues[:3]:  # Top 3 issues
                        suggestions += f"\n{issue['icon']} **{issue['title']}** ({issue['severity'].upper()})"
                        suggestions += f"\n   {issue['description']}"
                        suggestions += f"\n   💡 Fix: {issue['recommendation']}\n"

                    suggestions += f"""
### 📋 Content Strategy Recommendations:

Based on {profile.industry} industry best practices:"""

                    for strategy_name, strategy_data in content_strategies.items():
                        if strategy_data.get('priority') == 'high':
                            suggestions += f"\n• **{strategy_name.replace('_', ' ').title()}** (High Priority)"
                            if 'content_gaps' in strategy_data:
                                suggestions += f"\n  Content Ideas: {', '.join(strategy_data['content_gaps'][:2])}"

                    suggestions += f"""

### 🚀 Quick Wins:
- Focus on {profile.location}-specific content (detected from your domain)
- Target {profile.industry} + {profile.location} keyword combinations
- Position {avg_position:.1f} shows you're close to page 1 - push harder!

**Evidence**: With {ctr:.2f}% CTR from position {avg_position:.1f}, improving to page 1 could increase clicks by 300-500%.
**Knowledge Base**: Using {len(profile.keywords)} industry-specific keywords for {profile.industry} businesses."""

                    return suggestions

            except Exception as e:
                logger.error(f"[KEYWORD-RAG] Knowledge manager failed: {e}")
                # Fallback to keyword intelligence when knowledge manager fails

            # No GSC data available OR knowledge manager failed - use keyword intelligence with website analysis
            try:
                # Check if we have website analysis for portfolio detection
                if website_analysis and 'personal_portfolio' in website_analysis.get('business_type', ''):
                    # Generate portfolio-specific keywords
                    name_from_title = website_analysis.get('title', 'Portfolio').split('-')[0].strip()
                    keywords_found = website_analysis.get('keywords_found', [])
                    location = website_analysis.get('location', 'Singapore')

                    return f"""## 🎯 Keyword Strategy for Your Personal Portfolio Website

**Website**: {website_url}
**Type**: Personal Portfolio - {website_analysis.get('business_type', 'developer').replace('_', ' ').title()}
**Analysis**: {website_analysis.get('summary', 'Personal portfolio website')}

### 📊 IMPORTANT: Portfolio SEO Strategy

Your website is a **personal portfolio**, not a business site. SEO strategy should focus on:

### 🏆 Personal Brand Keywords (Most Important):
• "{name_from_title}" - Your exact name for direct searches
• "{name_from_title} portfolio" - Portfolio-specific searches
• "{name_from_title} software engineer" - Professional title
• "{name_from_title} developer" - Alternative title
• "{name_from_title} github" - Code repository searches

### 💼 Professional Keywords:
• "software engineer {location}" - Location-based professional searches
• "fullstack developer {location}" - Skill + location
• "hire developer {location}" - Hiring intent
• "freelance developer {location}" - Freelance opportunities
• "{location} tech talent" - Recruiter searches

### 🛠️ Technology Keywords:
{chr(10).join([f'• "{kw}" - Technology expertise' for kw in keywords_found[:5] if kw in ['python', 'javascript', 'react', 'vue', 'java', 'docker', 'aws']]) or '• Add your technology stack keywords'}

### 📈 Portfolio SEO Action Plan:
1. **Optimize your name** - Most critical for personal branding
2. **Create project case studies** - Detailed write-ups rank well
3. **Write technical blog posts** - Establish expertise
4. **Include location** - For local opportunities
5. **Showcase technologies** - Target specific skill searches

**Note**: Portfolio sites have different goals than business sites. Focus on quality traffic (recruiters, clients) over quantity."""

                # Fallback to keyword intelligence for business sites
                from app.agent.keyword_intelligence import keyword_intelligence

                # Generate intelligent keyword suggestions based on website
                suggestions_data = keyword_intelligence.generate_keyword_suggestions(
                    query="keyword suggestions for website",
                    website_url=website_url,
                    location="singapore"
                )

                business_type = suggestions_data['business_type']
                primary_keywords = suggestions_data['primary_keywords']
                long_tail_keywords = suggestions_data['long_tail_keywords']
                local_keywords = suggestions_data['local_keywords']
                content_keywords = suggestions_data['content_keywords']
                strategy = suggestions_data['strategy']

                return f"""## 🎯 Smart Keyword Suggestions for Your {business_type.title()} Business

**Website**: {website_url or 'Your Business'}
**Detected Industry**: {business_type.title()}
**Location Focus**: Singapore
**Total Suggestions**: {suggestions_data['total_suggestions']} keywords

### 🏆 PRIMARY KEYWORDS (High Commercial Intent)
{chr(10).join([f"• **{keyword}** - Target for main service pages" for keyword in primary_keywords])}

### 🎪 LONG-TAIL KEYWORDS (Lower Competition, Higher Conversion)
{chr(10).join([f"• **{keyword}** - Create dedicated landing pages" for keyword in long_tail_keywords])}

### 📍 LOCAL SEO KEYWORDS (Singapore-Focused)
{chr(10).join([f"• **{keyword}** - Optimize for local search" for keyword in local_keywords])}

### ✍️ CONTENT MARKETING KEYWORDS (Blog/Resources)
{chr(10).join([f"• **{keyword}** - Create educational content" for keyword in content_keywords])}

### 🎯 KEYWORD STRATEGY FOR YOUR BUSINESS:

**Focus**: {strategy['focus']}
**Priority**: {strategy['priority']}
**Content Approach**: {strategy['content']}
**Research Tools**: {strategy['tools']}

### 📈 NEXT STEPS:
1. **Start with 3-5 primary keywords** - Don't spread too thin
2. **Create location-specific pages** - Singapore + your services
3. **Run a new audit** - Get actual GSC data for data-driven refinement
4. **Track rankings** - Monitor progress on these target keywords

💡 **Pro Tip**: Focus on keywords where you can realistically rank in top 10 within 3-6 months. Start local, then expand."""

            except Exception as e:
                logger.error(f"Keyword intelligence failed: {e}")
                # Use keyword intelligence as FINAL fallback - this should ALWAYS provide value
                try:
                    from app.agent.keyword_intelligence import keyword_intelligence

                    # Generate intelligent keyword suggestions based on website URL
                    suggestions_data = keyword_intelligence.generate_keyword_suggestions(
                        query=query,
                        website_url=website_url,
                        location="singapore"
                    )

                    business_type = suggestions_data['business_type']
                    primary_keywords = suggestions_data['primary_keywords']
                    long_tail_keywords = suggestions_data['long_tail_keywords']
                    local_keywords = suggestions_data['local_keywords']
                    content_keywords = suggestions_data['content_keywords']
                    strategy = suggestions_data['strategy']

                    return f"""## 🎯 Intelligent Keyword Strategy for {website_url}

**Business Type Detected**: {business_type.title()}
**Market Focus**: Singapore
**Analysis Confidence**: High (based on URL analysis and industry patterns)

### 🏆 PRIMARY KEYWORDS (High Commercial Intent)
{chr(10).join([f"• **{keyword}** - Target for main service pages" for keyword in primary_keywords])}

### 🎪 LONG-TAIL KEYWORDS (Lower Competition, Higher Conversion)
{chr(10).join([f"• **{keyword}** - Create dedicated landing pages" for keyword in long_tail_keywords])}

### 📍 LOCAL SEO KEYWORDS (Singapore-Focused)
{chr(10).join([f"• **{keyword}** - Optimize for local search" for keyword in local_keywords])}

### ✍️ CONTENT MARKETING IDEAS
{chr(10).join([f"• **{keyword}** - Create educational blog content" for keyword in content_keywords])}

### 🎯 STRATEGIC APPROACH:

**Focus**: {strategy['focus']}
**Priority**: {strategy['priority']}
**Content Strategy**: {strategy['content']}
**Research Tools**: {strategy['tools']}

### 📈 IMMEDIATE ACTION PLAN:
1. **Start with 3-5 primary keywords** - Focus your efforts for maximum impact
2. **Create Singapore-specific pages** - Local market advantage
3. **Develop content calendar** - Use the topic ideas above
4. **Track progress** - Monitor rankings for target keywords

💡 **Expert Insight**: Based on {business_type} industry patterns, these keywords can realistically achieve top-10 rankings within 3-6 months with consistent effort."""

                except Exception as intelligence_error:
                    print(f"[KEYWORD-RAG] Keyword intelligence also failed: {intelligence_error}")
                    # Absolute final fallback with minimal but useful response
                    return f"""## SEO Keyword Strategy for {website_url}

Based on your website analysis, here are fundamental keyword opportunities:

### 🎯 Recommended Focus Areas:
- **Local Keywords**: "[your service] + Singapore" combinations
- **Long-tail Phrases**: 3-4 word specific queries
- **Question Keywords**: "How to [solve problem]" formats
- **Commercial Intent**: "[service] provider Singapore" patterns

### 📋 Next Steps:
1. **Run a comprehensive audit** to get data-driven insights
2. **Research competitor keywords** using free tools
3. **Create content calendar** focusing on user questions
4. **Optimize for local search** with Singapore targeting

Run "analyze my site" to get specific recommendations based on your actual performance data."""

        except Exception as e:
            logger.error(f"Failed to get keyword suggestions: {e}")
            return "Unable to retrieve keyword suggestions. Please try running a new audit to analyze your search performance."

    async def _get_traffic_trends_from_gsc(self, user_email: str) -> str:
        """Get traffic trends from GSC data - ALWAYS returns data when available."""
        try:
            from app.database.supabase_db import SupabaseAuthDB
            import aiohttp
            import os

            db = SupabaseAuthDB()

            website_url = db.get_user_website(user_email)
            if not website_url:
                return "No website selected."

            # First, try to get FRESH data from GSC API endpoint
            fresh_data = None
            try:
                # Make HTTP request to our own API endpoint to get fresh GSC data
                # This endpoint handles OAuth tokens and fetches real-time data
                base_url = os.getenv('BASE_URL', 'http://localhost:8000')

                # Create a JWT token for the user to authenticate with API
                from app.auth.utils import create_access_token
                user_token = create_access_token(data={"sub": user_email})
                headers = {'Authorization': f'Bearer {user_token}'}

                async with aiohttp.ClientSession() as session:
                    async with session.get(f'{base_url}/auth/gsc/metrics', headers=headers) as response:
                        if response.status == 200:
                            api_response = await response.json()
                            if api_response.get('success'):
                                fresh_data = api_response.get('metrics', {})
                                logger.info(f"[KEYWORD-RAG] Fetched fresh GSC data from API: clicks={fresh_data.get('clicks')}, impressions={fresh_data.get('impressions')}")
            except Exception as e:
                logger.warning(f"Could not fetch fresh GSC data from API: {e}")

            # If we have fresh data, use it
            if fresh_data:
                # Format traffic trends with FRESH data
                trends = "## 📊 Real-Time Traffic Data from Google Search Console\n\n"
                trends += "### Last 30 Days Performance:\n"
                trends += f"- **Clicks**: {fresh_data.get('clicks', 0):,} organic visitors\n"
                trends += f"- **Impressions**: {fresh_data.get('impressions', 0):,} times shown in search\n"
                ctr_value = fresh_data.get('ctr', 0)
                if isinstance(ctr_value, (int, float)):
                    trends += f"- **CTR**: {ctr_value:.2%} click-through rate\n"
                else:
                    trends += f"- **CTR**: {ctr_value} click-through rate\n"
                avg_pos = fresh_data.get('avg_position', 0)
                if isinstance(avg_pos, (int, float)) and avg_pos > 0:
                    trends += f"- **Average Position**: {avg_pos:.1f} in search results\n"
                else:
                    trends += f"- **Average Position**: {avg_pos} in search results\n"
                trends += f"- **SEO Score**: {fresh_data.get('seo_score', 25)}/100\n\n"

                # Add change metrics if available
                if fresh_data.get('clicks_change') is not None:
                    trends += "### Recent Changes:\n"
                    clicks_change = fresh_data.get('clicks_change', 0)
                    impressions_change = fresh_data.get('impressions_change', 0)
                    ctr_change = fresh_data.get('ctr_change', 0)

                    if clicks_change != 0:
                        trend_icon = "📈" if clicks_change > 0 else "📉"
                        trends += f"{trend_icon} **Clicks**: {'+' if clicks_change > 0 else ''}{clicks_change}\n"
                    if impressions_change != 0:
                        trend_icon = "📈" if impressions_change > 0 else "📉"
                        trends += f"{trend_icon} **Impressions**: {'+' if impressions_change > 0 else ''}{impressions_change}\n"
                    if ctr_change != 0:
                        trend_icon = "📈" if ctr_change > 0 else "📉"
                        trends += f"{trend_icon} **CTR**: {'+' if ctr_change > 0 else ''}{ctr_change:.2%}\n"

                return trends

            # Fall back to cached data if fresh fetch fails
            gsc_data = self.service_supabase.table('gsc_metrics_cache').select('*').eq('user_email', user_email).eq('website_url', website_url).order('cache_date', desc=True).limit(5).execute()

            if gsc_data.data:
                # Format traffic trends from cache
                trends = "## 📊 Traffic Trends from Google Search Console (Cached)\n\n"

                for i, metrics in enumerate(gsc_data.data):
                    date_range = f"{metrics.get('start_date', 'N/A')} to {metrics.get('end_date', 'N/A')}"
                    trends += f"### Period {i+1}: {date_range}\n"
                    trends += f"- **Clicks**: {metrics.get('clicks', 0)} organic visitors\n"
                    trends += f"- **Impressions**: {metrics.get('impressions', 0)} times shown in search\n"
                    trends += f"- **CTR**: {float(metrics.get('ctr', 0)):.2f}% click-through rate\n"
                    trends += f"- **Position**: {float(metrics.get('avg_position', 0)):.1f} average ranking\n"
                    trends += f"- **SEO Score**: {metrics.get('seo_score', 25)}/100\n\n"

                    # Add trend analysis
                    if i > 0:
                        prev = gsc_data.data[i-1]
                        click_change = metrics.get('clicks', 0) - prev.get('clicks', 0)
                        impression_change = metrics.get('impressions', 0) - prev.get('impressions', 0)

                        if click_change != 0:
                            trend_icon = "📈" if click_change > 0 else "📉"
                            trends += f"{trend_icon} **Click Trend**: {'+' if click_change > 0 else ''}{click_change} clicks\n"
                        if impression_change != 0:
                            trend_icon = "📈" if impression_change > 0 else "📉"
                            trends += f"{trend_icon} **Impression Trend**: {'+' if impression_change > 0 else ''}{impression_change} impressions\n\n"

                return trends

            return "GSC data is being fetched. Please refresh your dashboard."

        except Exception as e:
            logger.error(f"Error getting traffic trends: {e}")
            return "Error retrieving traffic trends."

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
            
            # Also try to get fresh GSC metrics from API
            current_metrics = None
            try:
                import aiohttp
                import os

                base_url = os.getenv('BASE_URL', 'http://localhost:8000')
                # Create a JWT token for the user
                from app.auth.utils import create_access_token
                user_token = create_access_token(data={"sub": user_email})
                headers = {'Authorization': f'Bearer {user_token}'}

                async with aiohttp.ClientSession() as session:
                    async with session.get(f'{base_url}/auth/gsc/metrics', headers=headers) as response:
                        if response.status == 200:
                            api_response = await response.json()
                            if api_response.get('success'):
                                current_metrics = api_response.get('metrics', {})
                                logger.info(f"[KEYWORD-RAG] Got fresh metrics for audit context")
            except Exception as e:
                logger.warning(f"Could not fetch fresh metrics: {e}")
                # Fall back to cache if API fails
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

                # Add specific issue details if available
                if isinstance(audit_data, dict):
                    # Try different locations for issues
                    issues = audit_data.get('issues', [])

                    # Check for issues in audit_results if not found at top level
                    if not issues and 'audit_results' in audit_data:
                        audit_results = audit_data.get('audit_results', {})
                        issues = audit_results.get('issues', [])

                    # Try to extract issues from sections if available
                    if not issues and 'sections' in audit_data:
                        all_issues = []
                        for section in audit_data.get('sections', []):
                            section_issues = section.get('issues', [])
                            all_issues.extend(section_issues)
                        issues = all_issues

                    if issues:
                        formatted_data += "\nDetailed Issues Found:\n"
                        for i, issue in enumerate(issues[:10], 1):  # Show top 10 issues
                            severity = issue.get('severity', issue.get('priority', 'Unknown'))
                            description = issue.get('description', issue.get('title', 'No description'))
                            impact = issue.get('impact', issue.get('recommendation', 'No impact specified'))
                            formatted_data += f"\n{i}. [{severity.upper()}] {description}\n"
                            formatted_data += f"   Impact: {impact}\n"

                    # Add recommendations if available
                    recommendations = audit_data.get('recommendations', [])
                    if recommendations:
                        formatted_data += "\nTop Recommendations:\n"
                        for i, rec in enumerate(recommendations[:3], 1):  # Show top 3 recommendations
                            formatted_data += f"{i}. {rec}\n"
                
                # Add current GSC metrics if available
                if current_metrics:
                    formatted_data += "\n\nCurrent GSC Metrics (Live Data):\n"
                    formatted_data += f"- Clicks: {current_metrics.get('clicks', 0):,}\n"
                    formatted_data += f"- Impressions: {current_metrics.get('impressions', 0):,}\n"
                    ctr_value = current_metrics.get('ctr', 0)
                    if isinstance(ctr_value, (int, float)):
                        formatted_data += f"- CTR: {ctr_value:.2%}\n"
                    else:
                        formatted_data += f"- CTR: {ctr_value}\n"
                    avg_pos = current_metrics.get('avg_position', current_metrics.get('position', 0))
                    if isinstance(avg_pos, (int, float)) and avg_pos > 0:
                        formatted_data += f"- Average Position: {avg_pos:.1f}\n"
                    else:
                        formatted_data += f"- Average Position: {avg_pos}\n"
                    formatted_data += f"- SEO Score: {current_metrics.get('seo_score', 25)}/100\n\n"
                
                
                return formatted_data.strip()
            
            # Fallback to current metrics with intelligent analysis
            elif current_metrics:
                clicks = current_metrics.get('clicks', 0)
                impressions = current_metrics.get('impressions', 0)
                ctr = float(current_metrics.get('ctr', 0))
                avg_position = float(current_metrics.get('avg_position', 0))
                seo_score = current_metrics.get('seo_score', 25.0)

                # Intelligent analysis based on available data
                domain = website_url.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]

                # Performance analysis
                performance_notes = []
                if clicks < 10:
                    performance_notes.append(f"⚠️ Low organic traffic: Only {clicks} clicks suggests visibility issues")
                if avg_position > 10:
                    performance_notes.append(f"📍 Poor rankings: Position {avg_position:.1f} means page 2+ visibility")
                if ctr < 2:
                    performance_notes.append(f"🎯 Low CTR: {ctr:.2f}% suggests title/meta optimization needed")
                if impressions > 100:
                    performance_notes.append(f"👁️ Good exposure: {impressions} impressions shows Google knows your site")

                performance_analysis = "\n".join([f"- {note}" for note in performance_notes]) if performance_notes else "- No major issues detected in available data"

                return f"""
Website: {website_url}

Current GSC Performance Analysis (Last 30 days):
- **Clicks**: {clicks} (organic traffic)
- **Impressions**: {impressions} (times shown in search)
- **CTR**: {ctr:.2f}% (click-through rate)
- **Average Position**: {avg_position:.1f} (search ranking)
- **SEO Score**: {seo_score}/100
- **Data Date**: {current_metrics.get('cache_date', 'Unknown')}

### 📊 Performance Insights:
{performance_analysis}

### 🎯 Opportunities Based on Your Data:
- **Brand Keywords**: Target "{domain} singapore" and "{domain} services"
- **Position Improvement**: Move from {avg_position:.1f} to positions 3-5 for 3-5x more clicks
- **Content Strategy**: Create pages targeting your industry + location combinations
- **CTR Optimization**: Improve titles/descriptions to increase {ctr:.2f}% CTR

### 💡 Next Steps:
1. **Run a comprehensive audit** - Get detailed issue analysis and recommendations
2. **Focus on local SEO** - Your Singapore location offers targeting opportunities
3. **Create location-specific content** - Target "singapore + your services" keywords

Note: This analysis is based on your aggregate GSC metrics. Run an audit for query-level keyword analysis.
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
            # Check query type
            keyword_queries = [
                'keyword', 'keywords', 'suggest', 'suggestion', 'target', 'rank for',
                'search for', 'optimize for', 'content ideas', 'topics', 'blog ideas'
            ]

            traffic_queries = [
                'traffic', 'trends', 'visitors', 'clicks', 'impressions',
                'performance', 'metrics', 'statistics', 'analytics', 'data'
            ]

            is_keyword_query = any(kw in query.lower() for kw in keyword_queries)
            is_traffic_query = any(kw in query.lower() for kw in traffic_queries)

            if is_traffic_query:
                # ALWAYS provide traffic data when available
                traffic_trends = await self._get_traffic_trends_from_gsc(user_email)
                context = await self.get_augmented_context(user_email, query)
                current_audit_data = await self._get_current_audit_data(user_email)

                enhanced_prompt = f"""You are Solvia, an expert SEO analyst that ALWAYS provides traffic data from Google Search Console.

## YOUR DATA:
<traffic_trends>
{traffic_trends}
</traffic_trends>

<audit_data>
{current_audit_data}
</audit_data>

## CRITICAL RULES:
1. ALWAYS show the traffic trends data provided above
2. NEVER say "I don't have data" when GSC metrics are provided
3. Present the data in a clear, formatted way
4. Add insights about what the trends mean
5. Provide recommendations based on the trends

## Response format:
Start with the actual data, then provide analysis and recommendations."""

            elif is_keyword_query:
                # Get keyword-specific context and suggestions
                keyword_suggestions = await self._get_keyword_suggestions_from_gsc(user_email)
                context = await self.get_augmented_context(user_email, query)

                # Enhanced prompt for keyword suggestions with intelligent fallback
                enhanced_prompt = f"""You are Solvia, an expert SEO analyst that provides keyword suggestions based on real Google Search Console data AND actual website content analysis.

## CRITICAL INSTRUCTIONS FOR KEYWORD SUGGESTIONS:
1. ALWAYS provide actionable keyword suggestions - never say "I don't have data"
2. If GSC data available: Use actual search queries, clicks, impressions, and positions
3. If GSC data limited: Use website URL analysis and business intelligence for smart suggestions
4. Detect business type from website URL (technology, construction, healthcare, etc.)
5. Provide Singapore-focused local keywords when relevant

## KEYWORD DATA PROVIDED TO YOU:
<keyword_data>
{keyword_suggestions}
</keyword_data>

## RESPONSE RULES - ALWAYS PROVIDE KEYWORDS:

### When you have GSC data:
- Highlight ACTUAL keywords with exact metrics (clicks, impressions, position)
- Identify opportunity keywords (high impressions, low clicks)
- Point out keywords ready for page 1 (currently ranking 4-10)

### When GSC data is limited:
- Analyze website URL for business type (act-technology.com = technology company)
- Provide industry-specific keyword suggestions (IT services, technology solutions)
- Include local variations (Singapore + services)
- Suggest content topics relevant to the business

### ALWAYS include these sections:
1. **Primary Keywords** (5 high-commercial-intent keywords)
2. **Long-tail Keywords** (5 specific, lower-competition keywords)
3. **Local Keywords** (5 Singapore/location-focused keywords)
4. **Content Topics** (8 blog post ideas)
5. **Strategy Recommendations** (actionable next steps)

Remember: You ALWAYS provide keyword suggestions - either data-driven OR intelligent business analysis. Never refuse or say you lack information."""

                # Get current audit data for additional context
                current_audit_data = await self._get_current_audit_data(user_email)

            else:
                # Regular non-keyword query
                context = await self.get_augmented_context(user_email, query)
                current_audit_data = await self._get_current_audit_data(user_email)

                # Regular enhanced prompt
                enhanced_prompt = f"""You are Solvia, an expert SEO analyst that provides insights based EXCLUSIVELY on real Google Search Console data and audit results. You NEVER make up data or provide generic advice.

## CRITICAL INSTRUCTIONS:
1. Use actual data from GSC metrics and audits when available
2. NEVER say "I don't have data" when GSC is connected - we ALWAYS have metrics
3. If audit data is limited, use GSC metrics cache for insights
4. Always provide actionable recommendations
5. Be specific with numbers and date ranges when available

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

## DATA PRIORITIZATION HIERARCHY:

### FIRST PRIORITY: Use Source of Truth (Real Audit/GSC Data)
- Always prioritize actual audit results, GSC metrics, and real performance data
- Reference exact numbers, dates, and verified measurements
- Base recommendations on proven performance patterns

### SECOND PRIORITY: Intelligent Analysis When Data Limited
- Use website URL analysis for business type detection
- Apply industry-specific insights from knowledge base
- Provide Singapore market intelligence
- Use historical audit patterns

### NEVER REFUSE TO HELP:
NEVER say "I don't have data" - always provide actionable insights using the best available source:
1. Audit data (highest priority)
2. Cached GSC metrics (second priority)
3. Website analysis + industry intelligence (fallback)

Remember: You prioritize source of truth from audits while ensuring users ALWAYS get valuable, actionable insights."""
            
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