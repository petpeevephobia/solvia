"""
Simple RAG Agent for Solvia - No External Dependencies
Uses existing OpenAI and Supabase infrastructure
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from app.config import settings
from app.database.supabase_db import SupabaseAuthDB
import openai

logger = logging.getLogger(__name__)

class SimpleRAGAgent:
    """
    Lightweight RAG implementation using only OpenAI and Supabase
    No vector databases needed - uses smart context retrieval
    """
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.db = SupabaseAuthDB()
    
    async def process_chat_message(
        self, 
        user_message: str,
        user_email: str,
        website_url: Optional[str] = None
    ) -> str:
        """
        Main entry point for processing chat messages with RAG
        """
        try:
            # Get enhanced context
            context = await self.get_enhanced_context(
                user_message,
                user_email,
                website_url
            )
            
            # Generate contextual response
            response = await self.generate_contextual_response(
                user_message,
                context
            )
            
            return response
            
        except Exception as e:
            logger.error(f"RAG processing error: {e}")
            # Fallback to basic response
            return await self._generate_basic_response(user_message)
    
    async def get_enhanced_context(
        self, 
        user_message: str,
        user_email: str,
        website_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Gather all relevant context for the user's question
        Smart data retrieval based on message intent
        """
        
        context = {
            'gsc_metrics': {},
            'recent_audits': [],
            'top_issues': [],
            'historical_trends': {},
            'top_queries': [],
            'top_pages': [],
            'user_profile': {}
        }
        
        # If no website URL provided, get user's selected website
        if not website_url:
            website_url = await self.db.get_user_website(user_email)
        
        if not website_url:
            return context  # Return empty context if no website
        
        # 1. Always get current GSC metrics
        try:
            metrics = await self.db.get_cached_gsc_metrics(user_email, website_url)
            if metrics:
                context['gsc_metrics'] = {
                    'clicks': metrics.get('clicks', 0),
                    'impressions': metrics.get('impressions', 0),
                    'ctr': metrics.get('ctr', 0),
                    'avg_position': metrics.get('avg_position', 0),
                    'seo_score': metrics.get('seo_score', 25),
                    'date_range': metrics.get('date_range', '30 days')
                }
        except Exception as e:
            logger.error(f"Error fetching GSC metrics: {e}")
        
        # 2. Get recent audit results if asking about audits or issues
        if any(word in user_message.lower() for word in ['audit', 'issue', 'problem', 'fix', 'score']):
            try:
                # Query audit results
                recent_audits = await self.db._execute_query("""
                    SELECT audit_id, seo_score, created_at,
                           issues_count::json as issues
                    FROM audit_results 
                    WHERE user_email = %s 
                    ORDER BY created_at DESC 
                    LIMIT 3
                """, (user_email,))
                
                if recent_audits:
                    context['recent_audits'] = [
                        {
                            'audit_id': audit['audit_id'],
                            'seo_score': audit['seo_score'],
                            'created_at': audit['created_at'].isoformat(),
                            'issues': audit['issues'] if audit['issues'] else {}
                        }
                        for audit in recent_audits
                    ]
                    
                    # Get latest issues
                    latest_issues = await self.db._execute_query("""
                        SELECT title, severity, impact, recommendation
                        FROM audit_issues
                        WHERE audit_id = %s
                        ORDER BY 
                            CASE severity 
                                WHEN 'critical' THEN 1
                                WHEN 'high' THEN 2
                                WHEN 'medium' THEN 3
                                ELSE 4
                            END
                        LIMIT 5
                    """, (recent_audits[0]['audit_id'],))
                    
                    if latest_issues:
                        context['top_issues'] = latest_issues
                        
            except Exception as e:
                logger.error(f"Error fetching audit data: {e}")
        
        # 3. Get keyword/query data if asking about keywords
        if any(word in user_message.lower() for word in ['keyword', 'query', 'search', 'term', 'ranking']):
            try:
                # Get top performing queries from cache
                top_queries = await self.db._execute_query("""
                    SELECT query, clicks, impressions, ctr, position
                    FROM gsc_queries
                    WHERE user_email = %s AND website_url = %s
                    ORDER BY clicks DESC
                    LIMIT 10
                """, (user_email, website_url))
                
                if top_queries:
                    context['top_queries'] = top_queries
                else:
                    # Fallback to basic metrics
                    logger.info("No detailed query data available, using cache")
                    
            except Exception as e:
                logger.error(f"Error fetching query data: {e}")
        
        # 4. Get page performance if asking about pages or content
        if any(word in user_message.lower() for word in ['page', 'content', 'url', 'article', 'blog']):
            try:
                top_pages = await self.db._execute_query("""
                    SELECT page, clicks, impressions, ctr, position
                    FROM gsc_pages
                    WHERE user_email = %s AND website_url = %s
                    ORDER BY clicks DESC
                    LIMIT 10
                """, (user_email, website_url))
                
                if top_pages:
                    context['top_pages'] = top_pages
                    
            except Exception as e:
                logger.error(f"Error fetching page data: {e}")
        
        # 5. Calculate historical trends if asking about changes/trends
        if any(word in user_message.lower() for word in ['trend', 'change', 'increase', 'decrease', 'drop', 'growth']):
            try:
                historical_data = await self.db._execute_query("""
                    SELECT clicks, impressions, ctr, avg_position, cache_date
                    FROM gsc_metrics_cache
                    WHERE user_email = %s AND website_url = %s
                    ORDER BY cache_date DESC
                    LIMIT 30
                """, (user_email, website_url))
                
                if historical_data and len(historical_data) > 1:
                    context['historical_trends'] = self._calculate_trends(historical_data)
                    
            except Exception as e:
                logger.error(f"Error fetching historical data: {e}")
        
        # 6. Get user profile information
        context['user_profile'] = {
            'email': user_email,
            'website': website_url,
            'context_retrieved_at': datetime.now().isoformat()
        }
        
        return context
    
    async def generate_contextual_response(
        self,
        user_message: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Generate response using GPT-4o-mini with enhanced context
        """
        
        # Format context into readable text
        context_text = self._format_context_for_llm(context)
        
        # Build system prompt with context
        system_prompt = f"""You are Solvia, an expert SEO assistant with access to real-time search console data and audit history.

CURRENT DATA AND CONTEXT:
{context_text}

RESPONSE GUIDELINES:
1. Always reference specific data points from the context when available
2. Provide actionable insights based on the actual metrics
3. If you see concerning trends (drops > 20%), highlight them
4. Keep responses concise but data-driven
5. Suggest specific next steps the user can take
6. If data is limited, acknowledge it and suggest running an audit

Remember: You have access to real GSC data - use it to provide specific, personalized insights."""

        try:
            # Generate response with OpenAI
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=600
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return "I'm having trouble accessing the AI service right now. Please try again in a moment."
    
    def _format_context_for_llm(self, context: Dict[str, Any]) -> str:
        """Format context data into readable text for GPT"""
        
        formatted_sections = []
        
        # Format current GSC metrics
        if context.get('gsc_metrics'):
            metrics = context['gsc_metrics']
            formatted_sections.append(f"""📊 CURRENT PERFORMANCE METRICS ({metrics.get('date_range', '30 days')}):
• Total Clicks: {metrics.get('clicks', 0):,}
• Total Impressions: {metrics.get('impressions', 0):,}
• Average CTR: {metrics.get('ctr', 0):.2f}%
• Average Position: {metrics.get('avg_position', 0):.1f}
• SEO Score: {metrics.get('seo_score', 'N/A')}/100""")
        
        # Format recent audits
        if context.get('recent_audits'):
            audit_lines = ["📝 RECENT AUDIT HISTORY:"]
            for audit in context['recent_audits']:
                date = datetime.fromisoformat(audit['created_at']).strftime('%Y-%m-%d')
                issues = audit.get('issues', {})
                total_issues = sum(issues.get(k, 0) for k in ['critical', 'high', 'medium', 'low'])
                audit_lines.append(f"• {date}: Score {audit['seo_score']}/100, {total_issues} issues found")
            formatted_sections.append("\n".join(audit_lines))
        
        # Format top issues
        if context.get('top_issues'):
            issue_lines = ["⚠️ CURRENT TOP ISSUES:"]
            for issue in context['top_issues'][:3]:
                issue_lines.append(f"• [{issue['severity'].upper()}] {issue['title']}")
                issue_lines.append(f"  Impact: {issue['impact']}")
                issue_lines.append(f"  Fix: {issue['recommendation']}")
            formatted_sections.append("\n".join(issue_lines))
        
        # Format top queries
        if context.get('top_queries'):
            query_lines = ["🔍 TOP PERFORMING SEARCH QUERIES:"]
            for q in context['top_queries'][:5]:
                query_lines.append(
                    f"• \"{q['query']}\" - {q['clicks']} clicks, "
                    f"{q['impressions']} impressions, {q['ctr']:.2f}% CTR, "
                    f"Position {q['position']:.1f}"
                )
            formatted_sections.append("\n".join(query_lines))
        
        # Format top pages
        if context.get('top_pages'):
            page_lines = ["📄 TOP PERFORMING PAGES:"]
            for p in context['top_pages'][:5]:
                # Truncate long URLs
                url = p['page']
                if len(url) > 50:
                    url = url[:47] + "..."
                page_lines.append(
                    f"• {url}\n  {p['clicks']} clicks, {p['ctr']:.2f}% CTR, Position {p['position']:.1f}"
                )
            formatted_sections.append("\n".join(page_lines))
        
        # Format trends
        if context.get('historical_trends'):
            trends = context['historical_trends']
            trend_lines = ["📈 PERFORMANCE TRENDS:"]
            
            for metric, data in trends.items():
                if data['change'] != 0:
                    direction = "↑" if data['change'] > 0 else "↓"
                    trend_lines.append(
                        f"• {metric.replace('_', ' ').title()}: {direction} {abs(data['change']):.1f}% "
                        f"({data['direction']})"
                    )
            formatted_sections.append("\n".join(trend_lines))
        
        # Join all sections
        return "\n\n".join(formatted_sections) if formatted_sections else "No specific data available for this website."
    
    def _calculate_trends(self, historical_data: List[Dict]) -> Dict[str, Any]:
        """Calculate trend data from historical metrics"""
        
        if not historical_data or len(historical_data) < 2:
            return {}
        
        trends = {}
        
        # Get latest and previous periods
        latest = historical_data[0]
        week_ago = None
        month_ago = None
        
        for data in historical_data:
            days_diff = (datetime.now() - data['cache_date']).days
            if days_diff >= 7 and not week_ago:
                week_ago = data
            if days_diff >= 30 and not month_ago:
                month_ago = data
                break
        
        # Calculate click trends
        if latest.get('clicks') is not None:
            current_clicks = latest['clicks']
            
            if week_ago and week_ago.get('clicks'):
                week_change = ((current_clicks - week_ago['clicks']) / week_ago['clicks']) * 100
                trends['clicks_7d'] = {
                    'change': week_change,
                    'direction': 'improving' if week_change > 0 else 'declining'
                }
            
            if month_ago and month_ago.get('clicks'):
                month_change = ((current_clicks - month_ago['clicks']) / month_ago['clicks']) * 100
                trends['clicks_30d'] = {
                    'change': month_change,
                    'direction': 'improving' if month_change > 0 else 'declining'
                }
        
        # Calculate position trends
        if latest.get('avg_position') is not None:
            current_position = latest['avg_position']
            
            if week_ago and week_ago.get('avg_position'):
                # For position, lower is better
                position_change = week_ago['avg_position'] - current_position
                trends['position_7d'] = {
                    'change': position_change,
                    'direction': 'improving' if position_change > 0 else 'declining'
                }
        
        return trends
    
    async def _generate_basic_response(self, user_message: str) -> str:
        """Fallback response when context retrieval fails"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are Solvia, an SEO expert assistant. Provide helpful SEO advice."
                    },
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=400
            )
            return response.choices[0].message.content
        except:
            return "I'm having trouble processing your request. Please try again or run an audit for detailed insights."

# Singleton instance
simple_rag_agent = SimpleRAGAgent()