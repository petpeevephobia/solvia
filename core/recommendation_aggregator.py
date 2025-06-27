"""
Central Recommendation Aggregator for SEO Analysis
Consolidates and prioritizes recommendations across all analysis areas with unified scoring
"""

import json
from datetime import datetime
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class RecommendationAggregator:
    def __init__(self):
        self.recommendations = []
        self.business_context = {}
        
    def set_business_context(self, business_data: Dict[str, Any]):
        """Set business context for priority scoring adjustments."""
        self.business_context = business_data
        
    def add_technical_seo_recommendations(self, openai_analysis: Dict[str, Any]):
        """
        Process and score Technical SEO recommendations from OpenAI analysis.
        
        Args:
            openai_analysis (dict): Analysis containing recommendations from generate_seo_analysis()
        """
        print("\t🎯 Processing Technical SEO recommendations...")
        
        raw_recommendations = openai_analysis.get('recommendations', [])
        
        for rec in raw_recommendations:
            # Only process technical recommendations for now
            if self._is_technical_recommendation(rec):
                scored_rec = self._score_technical_recommendation(rec)
                self.recommendations.append(scored_rec)
                
        print(f"\t\t✓ Processed {len([r for r in self.recommendations if r['category'] == 'technical'])} technical recommendations")
        
    def _is_technical_recommendation(self, recommendation: Dict[str, Any]) -> bool:
        """Determine if a recommendation is technical SEO related."""
        action_type = recommendation.get('action_type', '').lower()
        title = recommendation.get('title', '').lower()
        description = recommendation.get('description', '').lower()
        
        # Technical SEO indicators
        technical_indicators = [
            'meta', 'technical_fix', 'core web vitals', 'page speed', 'loading',
            'mobile', 'crawl', 'index', 'robots', 'sitemap', 'schema',
            'structured data', 'canonical', 'redirect', 'ssl', 'https',
            'compression', 'caching', 'image optimization', 'lcp', 'cls', 'fid'
        ]
        
        return (action_type in ['meta_update', 'technical_fix'] or 
                any(indicator in title or indicator in description 
                    for indicator in technical_indicators))
    
    def _score_technical_recommendation(self, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score a technical recommendation based on the priority formula.
        Priority Score = (Business Impact × 0.4) + (SEO Impact × 0.3) + (Urgency × 0.2) + (10 - Implementation Effort × 0.1)
        """
        
        # Extract recommendation details
        title = recommendation.get('title', '')
        description = recommendation.get('description', '')
        action_type = recommendation.get('action_type', '')
        
        # Score each dimension (1-10)
        business_impact = self._calculate_business_impact(title, description, action_type)
        seo_impact = self._calculate_seo_impact(title, description, action_type)
        urgency = self._calculate_urgency(title, description, action_type)
        implementation_effort = self._calculate_implementation_effort(title, description, action_type)
        
        # Apply the priority formula
        priority_score = (
            (business_impact * 0.4) + 
            (seo_impact * 0.3) + 
            (urgency * 0.2) + 
            ((10 - implementation_effort) * 0.1)
        )
        
        # Create unified recommendation structure
        unified_rec = {
            'recommendation_id': f"tech_{hash(title)}_{datetime.now().timestamp():.0f}",
            'title': title,
            'category': 'technical',
            'subcategory': self._get_technical_subcategory(title, description, action_type),
            'priority_score': round(priority_score, 2),
            'business_impact': business_impact,
            'seo_impact': seo_impact,
            'urgency': urgency,
            'implementation_effort': implementation_effort,
            'description': description,
            'action_type': action_type,
            'implementation_steps': recommendation.get('implementation_steps', []),
            'success_metrics': self._get_success_metrics(title, description, action_type),
            'timeline': self._estimate_timeline(implementation_effort),
            'dependencies': [],  # Will be populated later
            'business_context_adjustment': self._get_business_context_adjustment(title, description)
        }
        
        return unified_rec
    
    def _calculate_business_impact(self, title: str, description: str, action_type: str) -> int:
        """Calculate business impact score (1-10) based on revenue potential and conversion impact."""
        
        title_lower = title.lower()
        desc_lower = description.lower()
        
        # High business impact indicators
        high_impact_indicators = [
            'conversion', 'ctr', 'click-through', 'user experience', 'mobile',
            'page speed', 'loading', 'bounce rate', 'core web vitals'
        ]
        
        medium_impact_indicators = [
            'meta description', 'title tag', 'structured data', 'schema',
            'crawling', 'indexing', 'sitemap'
        ]
        
        low_impact_indicators = [
            'canonical', 'robots.txt', 'redirect', 'url structure'
        ]
        
        # E-commerce gets higher business impact for conversion-related fixes
        if self.business_context.get('business_model') == 'E-commerce':
            if any(indicator in title_lower or indicator in desc_lower 
                   for indicator in ['mobile', 'page speed', 'loading', 'checkout']):
                return 9
        
        # SaaS gets higher impact for user experience
        if self.business_context.get('business_model') == 'SaaS':
            if any(indicator in title_lower or indicator in desc_lower 
                   for indicator in ['user experience', 'dashboard', 'performance']):
                return 8
        
        # Local services prioritize mobile and speed
        if self.business_context.get('business_model') == 'Local Services':
            if any(indicator in title_lower or indicator in desc_lower 
                   for indicator in ['mobile', 'local', 'page speed']):
                return 8
        
        # General scoring
        if any(indicator in title_lower or indicator in desc_lower 
               for indicator in high_impact_indicators):
            return 8
        elif any(indicator in title_lower or indicator in desc_lower 
                 for indicator in medium_impact_indicators):
            return 6
        elif any(indicator in title_lower or indicator in desc_lower 
                 for indicator in low_impact_indicators):
            return 4
        else:
            return 5  # Default
    
    def _calculate_seo_impact(self, title: str, description: str, action_type: str) -> int:
        """Calculate SEO impact score (1-10) based on ranking potential and traffic increase."""
        
        title_lower = title.lower()
        desc_lower = description.lower()
        
        # Critical SEO impact
        critical_seo_indicators = [
            'meta description', 'title tag', 'core web vitals', 'page speed',
            'mobile', 'crawl', 'index', 'sitemap'
        ]
        
        # High SEO impact
        high_seo_indicators = [
            'structured data', 'schema', 'internal linking', 'url optimization',
            'image optimization', 'compression'
        ]
        
        # Medium SEO impact  
        medium_seo_indicators = [
            'canonical', 'redirect', 'robots.txt', 'ssl', 'https'
        ]
        
        if any(indicator in title_lower or indicator in desc_lower 
               for indicator in critical_seo_indicators):
            return 9
        elif any(indicator in title_lower or indicator in desc_lower 
                 for indicator in high_seo_indicators):
            return 7
        elif any(indicator in title_lower or indicator in desc_lower 
                 for indicator in medium_seo_indicators):
            return 5
        else:
            return 6  # Default
    
    def _calculate_urgency(self, title: str, description: str, action_type: str) -> int:
        """Calculate urgency score (1-10) based on critical issues vs optimization opportunities."""
        
        title_lower = title.lower()
        desc_lower = description.lower()
        
        # Critical issues (high urgency)
        critical_indicators = [
            'error', 'broken', 'not working', 'missing', 'critical', 'blocking',
            'crawl error', 'index error', 'mobile usability', 'core web vitals'
        ]
        
        # Important but not critical
        important_indicators = [
            'optimize', 'improve', 'enhance', 'update', 'recommendation'
        ]
        
        # Nice to have
        optimization_indicators = [
            'consider', 'might', 'could', 'opportunity', 'suggestion'
        ]
        
        if any(indicator in title_lower or indicator in desc_lower 
               for indicator in critical_indicators):
            return 9
        elif any(indicator in title_lower or indicator in desc_lower 
                 for indicator in important_indicators):
            return 6
        elif any(indicator in title_lower or indicator in desc_lower 
                 for indicator in optimization_indicators):
            return 3
        else:
            return 5  # Default
    
    def _calculate_implementation_effort(self, title: str, description: str, action_type: str) -> int:
        """Calculate implementation effort score (1-10) based on technical complexity and time required."""
        
        title_lower = title.lower()
        desc_lower = description.lower()
        
        # High effort (complex, time-consuming)
        high_effort_indicators = [
            'restructure', 'rebuild', 'major changes', 'development', 'custom',
            'migration', 'overhaul', 'complete redesign'
        ]
        
        # Medium effort
        medium_effort_indicators = [
            'optimize', 'implement', 'configure', 'setup', 'install',
            'structured data', 'schema', 'internal linking'
        ]
        
        # Low effort (quick wins)
        low_effort_indicators = [
            'meta', 'title', 'description', 'alt text', 'update', 'add',
            'enable', 'fix', 'robots.txt', 'canonical'
        ]
        
        if any(indicator in title_lower or indicator in desc_lower 
               for indicator in high_effort_indicators):
            return 8
        elif any(indicator in title_lower or indicator in desc_lower 
                 for indicator in medium_effort_indicators):
            return 5
        elif any(indicator in title_lower or indicator in desc_lower 
                 for indicator in low_effort_indicators):
            return 2
        else:
            return 4  # Default
    
    def _get_technical_subcategory(self, title: str, description: str, action_type: str) -> str:
        """Categorize technical recommendations into subcategories."""
        
        title_lower = title.lower()
        desc_lower = description.lower()
        
        if 'meta' in title_lower or 'title' in title_lower:
            return 'meta_optimization'
        elif any(indicator in title_lower or indicator in desc_lower 
                 for indicator in ['core web vitals', 'page speed', 'loading', 'lcp', 'cls', 'fid']):
            return 'core_web_vitals'
        elif any(indicator in title_lower or indicator in desc_lower 
                 for indicator in ['mobile', 'responsive']):
            return 'mobile_optimization'
        elif any(indicator in title_lower or indicator in desc_lower 
                 for indicator in ['crawl', 'index', 'sitemap', 'robots']):
            return 'crawling_indexing'
        elif any(indicator in title_lower or indicator in desc_lower 
                 for indicator in ['schema', 'structured data']):
            return 'structured_data'
        else:
            return 'general_technical'
    
    def _get_success_metrics(self, title: str, description: str, action_type: str) -> List[str]:
        """Define success metrics for tracking recommendation effectiveness."""
        
        title_lower = title.lower()
        desc_lower = description.lower()
        
        if 'meta' in title_lower:
            return ['CTR improvement', 'SERP click-through increase']
        elif 'core web vitals' in title_lower or 'page speed' in title_lower:
            return ['LCP improvement', 'CLS reduction', 'FID improvement', 'Performance score increase']
        elif 'mobile' in title_lower:
            return ['Mobile usability score', 'Mobile traffic increase']
        elif 'crawl' in title_lower or 'index' in title_lower:
            return ['Indexed pages increase', 'Crawl error reduction']
        elif 'structured data' in title_lower or 'schema' in title_lower:
            return ['Rich snippet appearances', 'SERP feature visibility']
        else:
            return ['SEO score improvement', 'Search visibility increase']
    
    def _estimate_timeline(self, implementation_effort: int) -> str:
        """Estimate implementation timeline based on effort score."""
        
        if implementation_effort <= 3:
            return '1-3 days'
        elif implementation_effort <= 5:
            return '1-2 weeks'
        elif implementation_effort <= 7:
            return '2-4 weeks'
        else:
            return '1-2 months'
    
    def _get_business_context_adjustment(self, title: str, description: str) -> str:
        """Provide business context adjustment reasoning."""
        
        business_model = self.business_context.get('business_model', 'Unknown')
        
        if business_model == 'E-commerce':
            if 'mobile' in title.lower() or 'page speed' in title.lower():
                return 'High priority for e-commerce: Direct impact on conversion rates'
        elif business_model == 'SaaS':
            if 'user experience' in description.lower():
                return 'Critical for SaaS: Affects trial conversion and user retention'
        elif business_model == 'Local Services':
            if 'mobile' in title.lower():
                return 'Essential for local services: Mobile-first local search behavior'
        
        return 'Standard technical SEO improvement'
    
    def get_prioritized_recommendations(self) -> List[Dict[str, Any]]:
        """Return all recommendations sorted by priority score (highest first)."""
        return sorted(self.recommendations, key=lambda x: x['priority_score'], reverse=True)
    
    def get_technical_recommendations(self) -> List[Dict[str, Any]]:
        """Return only technical recommendations sorted by priority."""
        technical_recs = [r for r in self.recommendations if r['category'] == 'technical']
        return sorted(technical_recs, key=lambda x: x['priority_score'], reverse=True)
    
    def get_quick_wins(self, max_effort: int = 3) -> List[Dict[str, Any]]:
        """Get high-priority, low-effort recommendations (quick wins)."""
        quick_wins = [
            r for r in self.recommendations 
            if r['implementation_effort'] <= max_effort and r['priority_score'] >= 7.0
        ]
        return sorted(quick_wins, key=lambda x: x['priority_score'], reverse=True)
    
    def generate_action_plan_summary(self) -> Dict[str, Any]:
        """Generate a summary of the prioritized action plan."""
        
        technical_recs = self.get_technical_recommendations()
        quick_wins = self.get_quick_wins()
        
        return {
            'total_recommendations': len(self.recommendations),
            'technical_recommendations': len(technical_recs),
            'quick_wins': len(quick_wins),
            'average_priority_score': round(
                sum(r['priority_score'] for r in self.recommendations) / len(self.recommendations) 
                if self.recommendations else 0, 2
            ),
            'top_priority_recommendation': technical_recs[0] if technical_recs else None,
            'recommended_first_actions': quick_wins[:3],
            'business_model': self.business_context.get('business_model', 'Unknown')
        }
    
    def export_recommendations_json(self) -> str:
        """Export all recommendations as JSON for storage or API responses."""
        return json.dumps({
            'generated_at': datetime.now().isoformat(),
            'business_context': self.business_context,
            'recommendations': self.get_prioritized_recommendations(),
            'summary': self.generate_action_plan_summary()
        }, indent=2) 