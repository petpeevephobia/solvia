"""
RAG (Retrieval-Augmented Generation) System for Intelligent SEO Issue Analysis
Clean, modular implementation for SEO audit insights
"""
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from dataclasses import dataclass, asdict
from enum import Enum

import openai
from app.config import settings
from app.database.supabase_db import SupabaseAuthDB

logger = logging.getLogger(__name__)

class IssueSeverity(str, Enum):
    """Issue severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class SEOIssue:
    """Clean data structure for SEO issues"""
    title: str
    description: str
    severity: IssueSeverity
    impact: str
    recommendation: str
    category: str
    data_points: Dict[str, Any]
    confidence_score: float = 0.9
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

class SEOKnowledgeBase:
    """
    SEO best practices knowledge base for RAG
    This provides context for AI to make informed recommendations
    """
    
    @staticmethod
    def get_seo_context() -> str:
        """Get SEO best practices context for AI"""
        return """
        SEO Best Practices Knowledge Base:
        
        1. TRAFFIC ANALYSIS:
        - Healthy sites show consistent growth in organic traffic
        - Sudden drops (>20%) indicate potential penalties or technical issues
        - CTR below 2% suggests poor meta descriptions or titles
        
        2. POSITION METRICS:
        - Average position > 20 means poor visibility
        - Position improvements correlate with content quality
        - Positions 1-3 get 60% of clicks
        
        3. TECHNICAL SEO:
        - Page speed affects rankings (Core Web Vitals)
        - Mobile-friendliness is crucial (60%+ traffic is mobile)
        - HTTPS is a ranking factor
        
        4. CONTENT ISSUES:
        - Thin content (<300 words) ranks poorly
        - Missing meta descriptions hurt CTR
        - Duplicate content causes ranking issues
        
        5. USER EXPERIENCE:
        - High bounce rate (>70%) signals poor UX
        - Low time on page (<30 seconds) indicates content mismatch
        - Poor navigation hurts user engagement
        """
    
    @staticmethod
    def get_issue_templates() -> Dict[str, Dict[str, str]]:
        """Get template responses for common issues"""
        return {
            "low_traffic": {
                "title": "Low Organic Traffic",
                "impact": "Your website is missing potential customers",
                "recommendation": "Focus on content optimization and keyword targeting"
            },
            "poor_ctr": {
                "title": "Poor Click-Through Rate",
                "impact": "Users see your site but aren't clicking",
                "recommendation": "Improve meta titles and descriptions to be more compelling"
            },
            "high_position": {
                "title": "Poor Search Rankings",
                "impact": "Your content appears too far down in search results",
                "recommendation": "Improve content quality and build authoritative backlinks"
            },
            "no_impressions": {
                "title": "Minimal Search Visibility",
                "impact": "Your website isn't appearing in search results",
                "recommendation": "Submit sitemap to Google and create targeted content"
            }
        }

class RAGAnalyzer:
    """
    Main RAG analyzer for intelligent SEO issue detection
    Combines data analysis with AI insights
    """
    
    def __init__(self):
        self.db = SupabaseAuthDB()
        self.knowledge_base = SEOKnowledgeBase()
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def analyze_audit_data(
        self, 
        audit_data: Dict[str, Any],
        website_url: str
    ) -> List[SEOIssue]:
        """
        Analyze audit data and generate intelligent issues with AI
        
        Args:
            audit_data: Raw audit data from GSC and analysis
            website_url: The website being analyzed
            
        Returns:
            List of SEO issues with AI-enhanced recommendations
        """
        # Extract key metrics
        metrics = self._extract_metrics(audit_data)
        
        # Detect issues from data
        detected_issues = self._detect_data_issues(metrics)
        
        # Enhance with AI insights
        enhanced_issues = await self._enhance_with_ai(
            detected_issues, 
            metrics, 
            website_url
        )
        
        # Sort by severity and impact
        enhanced_issues.sort(
            key=lambda x: (
                self._severity_rank(x.severity),
                -x.confidence_score
            )
        )
        
        return enhanced_issues[:3]  # Return top 3 issues
    
    def _extract_metrics(self, audit_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant metrics from audit data"""
        return {
            "seo_score": audit_data.get("seo_score", 0),
            "clicks": audit_data.get("organic_traffic", 0),
            "impressions": audit_data.get("impressions", 0),
            "ctr": audit_data.get("ctr", 0),
            "avg_position": audit_data.get("avg_position", 0),
            "clicks_change": audit_data.get("clicks_change", 0),
            "impressions_change": audit_data.get("impressions_change", 0),
            "position_change": audit_data.get("position_change", 0),
            "keywords": audit_data.get("keywords", 0)
        }
    
    def _detect_data_issues(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect issues from metrics using rules"""
        issues = []
        templates = self.knowledge_base.get_issue_templates()
        
        # Check for low traffic
        if metrics["clicks"] < 100:
            issues.append({
                **templates["low_traffic"],
                "severity": IssueSeverity.CRITICAL,
                "category": "traffic",
                "data": {
                    "current_clicks": metrics["clicks"],
                    "threshold": 100
                }
            })
        
        # Check for poor CTR
        if metrics["impressions"] > 0 and metrics["ctr"] < 2:
            issues.append({
                **templates["poor_ctr"],
                "severity": IssueSeverity.HIGH,
                "category": "engagement",
                "data": {
                    "current_ctr": metrics["ctr"],
                    "benchmark": 2.0
                }
            })
        
        # Check for poor rankings
        if metrics["avg_position"] > 20:
            issues.append({
                **templates["high_position"],
                "severity": IssueSeverity.HIGH,
                "category": "visibility",
                "data": {
                    "current_position": metrics["avg_position"],
                    "target_position": 10
                }
            })
        
        # Check for no impressions
        if metrics["impressions"] == 0:
            issues.append({
                **templates["no_impressions"],
                "severity": IssueSeverity.CRITICAL,
                "category": "visibility",
                "data": {
                    "impressions": 0,
                    "needs_indexing": True
                }
            })
        
        return issues
    
    async def _enhance_with_ai(
        self,
        issues: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        website_url: str
    ) -> List[SEOIssue]:
        """Enhance detected issues with AI insights"""
        if not issues:
            return []
        
        # Prepare context for AI
        context = self._prepare_ai_context(issues, metrics, website_url)
        
        try:
            # Get AI insights
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self._get_ai_system_prompt()},
                    {"role": "user", "content": context}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            # Parse AI response
            ai_insights = self._parse_ai_response(response.choices[0].message.content)
            
            # Create enhanced issues
            enhanced_issues = []
            for idx, issue in enumerate(issues):
                insight = ai_insights.get(idx, {})
                
                enhanced_issue = SEOIssue(
                    title=issue["title"],
                    description=insight.get("description", issue.get("impact", "")),
                    severity=issue["severity"],
                    impact=insight.get("impact", issue.get("impact", "")),
                    recommendation=insight.get("recommendation", issue.get("recommendation", "")),
                    category=issue["category"],
                    data_points=issue.get("data", {}),
                    confidence_score=0.95
                )
                enhanced_issues.append(enhanced_issue)
            
            return enhanced_issues
            
        except Exception as e:
            logger.error(f"AI enhancement failed: {e}")
            # Fallback to basic issues
            return [
                SEOIssue(
                    title=issue["title"],
                    description=issue.get("impact", ""),
                    severity=issue["severity"],
                    impact=issue.get("impact", ""),
                    recommendation=issue.get("recommendation", ""),
                    category=issue["category"],
                    data_points=issue.get("data", {}),
                    confidence_score=0.7
                )
                for issue in issues
            ]
    
    def _prepare_ai_context(
        self,
        issues: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        website_url: str
    ) -> str:
        """Prepare context for AI analysis"""
        return f"""
        Website: {website_url}
        
        Current Metrics:
        - SEO Score: {metrics['seo_score']}/100
        - Monthly Clicks: {metrics['clicks']}
        - Monthly Impressions: {metrics['impressions']}
        - Click-Through Rate: {metrics['ctr']:.2f}%
        - Average Position: {metrics['avg_position']:.1f}
        
        Detected Issues:
        {json.dumps(issues, indent=2)}
        
        Please provide actionable insights for each issue with:
        1. A clear description of why this matters
        2. The business impact in simple terms
        3. A specific, actionable recommendation
        
        Format your response as JSON with keys: description, impact, recommendation
        """
    
    def _get_ai_system_prompt(self) -> str:
        """Get system prompt for AI"""
        return f"""
        You are an expert SEO consultant analyzing website performance data.
        
        {self.knowledge_base.get_seo_context()}
        
        Your task is to provide clear, actionable insights that non-technical 
        business owners can understand and implement.
        
        Focus on:
        1. Business impact (lost revenue, missed customers)
        2. Simple explanations (avoid jargon)
        3. Specific actions they can take
        
        Always respond in JSON format with clear recommendations.
        """
    
    def _parse_ai_response(self, response: str) -> Dict[int, Dict[str, str]]:
        """Parse AI response into structured insights"""
        try:
            # Clean up response - remove markdown code blocks
            clean_response = response.strip()
            if clean_response.startswith('```'):
                # Remove code block markers
                lines = clean_response.split('\n')
                # Find JSON content between code blocks
                json_lines = []
                in_json = False
                for line in lines:
                    if line.strip() == '```json' or line.strip() == '```':
                        in_json = not in_json
                        continue
                    if in_json:
                        json_lines.append(line)
                clean_response = '\n'.join(json_lines)
            
            # Try to parse as JSON
            insights = json.loads(clean_response)
            if isinstance(insights, list):
                return {i: item for i, item in enumerate(insights)}
            elif isinstance(insights, dict):
                return {0: insights}
        except:
            # Fallback to enhanced text parsing with richer details
            clean_text = response.replace('```json', '').replace('```', '').strip()
            
            # Extract meaningful content for progressive disclosure
            sentences = clean_text.split('.')
            
            # Create a richer description from the AI response
            description = clean_text[:300] if len(clean_text) > 50 else "Issue detected based on your website's SEO metrics"
            impact = clean_text[300:500] if len(clean_text) > 300 else "This issue may significantly impact your search visibility and organic traffic"
            
            return {
                0: {
                    "description": description,
                    "impact": impact,
                    "recommendation": "Review and address this issue to improve your SEO score and search visibility"
                }
            }
        return {}
    
    def _severity_rank(self, severity: IssueSeverity) -> int:
        """Get numeric rank for severity sorting"""
        ranks = {
            IssueSeverity.CRITICAL: 0,
            IssueSeverity.HIGH: 1,
            IssueSeverity.MEDIUM: 2,
            IssueSeverity.LOW: 3
        }
        return ranks.get(severity, 3)

# Singleton instance
rag_analyzer = RAGAnalyzer()