"""
Clean Architecture: Knowledge Manager
===================================
Central system for managing SEO knowledge, business detection, and response generation.
Replaces hardcoded business logic with configurable, version-controlled knowledge.
"""

import yaml
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class BusinessProfile:
    """Detected business profile with confidence scoring"""
    domain: str
    industry: str
    location: str
    confidence: float
    keywords: List[str]
    strategies: Dict[str, Any]

@dataclass
class GSCMetrics:
    """Standardized GSC metrics for analysis"""
    clicks: int
    impressions: int
    ctr: float
    avg_position: float
    seo_score: float

@dataclass
class KeywordSuggestion:
    """Individual keyword suggestion with metadata"""
    keyword: str
    category: str  # 'brand', 'industry', 'local', 'long_tail'
    priority: str  # 'high', 'medium', 'low'
    target_position: float
    search_intent: str

class KnowledgeManager:
    """
    Central knowledge management system for RAG.
    Loads business intelligence from YAML files and provides clean interfaces.
    """

    def __init__(self, knowledge_path: str = None):
        """Initialize with knowledge directory path"""
        self.knowledge_path = knowledge_path or os.path.join(
            os.path.dirname(__file__), '..', 'knowledge'
        )
        self._industry_cache = {}
        self._patterns_cache = {}
        self._seo_categories_cache = {}
        self._load_all_knowledge()

    def _load_all_knowledge(self):
        """Load all knowledge files into memory cache"""
        try:
            # Load domain patterns
            patterns_file = os.path.join(self.knowledge_path, 'business_detection', 'domain_patterns.yaml')
            if os.path.exists(patterns_file):
                with open(patterns_file, 'r') as f:
                    self._patterns_cache = yaml.safe_load(f)

            # Load industry knowledge
            industries_dir = os.path.join(self.knowledge_path, 'industries')
            if os.path.exists(industries_dir):
                for file_path in Path(industries_dir).glob('*.yaml'):
                    industry_name = file_path.stem
                    with open(file_path, 'r') as f:
                        self._industry_cache[industry_name] = yaml.safe_load(f)

            # Load SEO categories knowledge
            seo_categories_dir = os.path.join(self.knowledge_path, 'seo_categories')
            if os.path.exists(seo_categories_dir):
                for file_path in Path(seo_categories_dir).glob('*.yaml'):
                    category_name = file_path.stem
                    with open(file_path, 'r') as f:
                        self._seo_categories_cache[category_name] = yaml.safe_load(f)

            logger.info(f"Loaded knowledge: {len(self._industry_cache)} industries, {len(self._seo_categories_cache)} SEO categories, patterns available")

        except Exception as e:
            logger.error(f"Failed to load knowledge: {e}")
            # Initialize with minimal fallback
            self._init_fallback_knowledge()

    def _init_fallback_knowledge(self):
        """Initialize minimal fallback knowledge if files are unavailable"""
        self._patterns_cache = {
            'domain_patterns': {
                'construction': {
                    'keywords': ['akar', 'build', 'construct'],
                    'confidence_weights': {'keyword_match': 0.7}
                }
            }
        }
        self._industry_cache = {
            'construction': {
                'industry': 'construction',
                'locations': {
                    'singapore': {
                        'primary_keywords': [
                            'construction company singapore',
                            'building contractor singapore'
                        ]
                    }
                }
            }
        }

    async def detect_business_profile(self, domain: str, website_url: str = None) -> BusinessProfile:
        """
        Intelligent business profile detection from domain and optional content analysis.

        Args:
            domain: Domain name (e.g., 'akarco.sg')
            website_url: Full URL for additional context

        Returns:
            BusinessProfile with detected industry, location, and confidence
        """
        # Clean domain for analysis
        clean_domain = domain.replace('https://', '').replace('http://', '').replace('www.', '')
        domain_parts = clean_domain.split('.')

        # Detect industry
        industry, industry_confidence = self._detect_industry(clean_domain)

        # Detect location
        location, location_confidence = self._detect_location(clean_domain)

        # Calculate overall confidence
        overall_confidence = (industry_confidence + location_confidence) / 2

        # Get industry-specific knowledge
        industry_data = self._industry_cache.get(industry, {})
        location_data = industry_data.get('locations', {}).get(location, {})

        # Extract keywords for this industry + location combination
        keywords = location_data.get('primary_keywords', [])
        if not keywords:
            # Fallback to generic keywords
            keywords = [f"{domain_parts[0]} {location}", f"{industry} {location}"]

        # Get strategies
        strategies = industry_data.get('content_strategies', {})

        return BusinessProfile(
            domain=domain,
            industry=industry,
            location=location,
            confidence=overall_confidence,
            keywords=keywords,
            strategies=strategies
        )

    def _detect_industry(self, domain: str) -> tuple[str, float]:
        """Detect industry from domain with confidence scoring"""
        patterns = self._patterns_cache.get('domain_patterns', {})

        best_match = 'general_business'
        best_confidence = 0.1

        for industry, pattern_data in patterns.items():
            confidence = 0.0
            weights = pattern_data.get('confidence_weights', {})

            # Check keyword matches
            keywords = pattern_data.get('keywords', [])
            for keyword in keywords:
                if keyword in domain.lower():
                    confidence += weights.get('keyword_match', 0.5)
                    break

            # Check TLD hints
            tld_hints = pattern_data.get('tld_hints', [])
            for tld in tld_hints:
                if domain.endswith(tld):
                    confidence += weights.get('tld_match', 0.3)
                    break

            if confidence > best_confidence:
                best_match = industry
                best_confidence = confidence

        return best_match, best_confidence

    def _detect_location(self, domain: str) -> tuple[str, float]:
        """Detect location from domain with confidence scoring"""
        patterns = self._patterns_cache.get('location_patterns', {})

        best_match = 'global'
        best_confidence = 0.3

        for location, pattern_data in patterns.items():
            confidence = 0.0
            weights = pattern_data.get('confidence_weights', {})

            # Check domain indicators
            indicators = pattern_data.get('domain_indicators', [])
            for indicator in indicators:
                if indicator in domain.lower():
                    confidence += weights.get('domain_match', 0.5)
                    break

            # Check TLD hints
            tld_hints = pattern_data.get('tld_hints', [])
            for tld in tld_hints:
                if domain.endswith(tld):
                    confidence += weights.get('tld_match', 0.5)
                    break

            if confidence > best_confidence:
                best_match = location
                best_confidence = confidence

        return best_match, best_confidence

    async def generate_keyword_suggestions(
        self,
        profile: BusinessProfile,
        metrics: GSCMetrics
    ) -> List[KeywordSuggestion]:
        """
        Generate intelligent keyword suggestions based on business profile and performance data.

        Args:
            profile: Detected business profile
            metrics: Current GSC performance metrics

        Returns:
            List of prioritized keyword suggestions
        """
        suggestions = []

        # Get industry data
        industry_data = self._industry_cache.get(profile.industry, {})
        location_data = industry_data.get('locations', {}).get(profile.location, {})

        # Brand keywords (highest priority)
        domain_name = profile.domain.split('.')[0]
        brand_keywords = [
            f"{domain_name} {profile.location}",
            f"{domain_name} services",
        ]

        for keyword in brand_keywords:
            suggestions.append(KeywordSuggestion(
                keyword=keyword,
                category='brand',
                priority='high',
                target_position=max(1, metrics.avg_position - 2),
                search_intent='navigational'
            ))

        # Industry keywords
        primary_keywords = location_data.get('primary_keywords', [])
        for keyword in primary_keywords[:3]:  # Top 3
            suggestions.append(KeywordSuggestion(
                keyword=keyword,
                category='industry',
                priority='high' if metrics.avg_position > 10 else 'medium',
                target_position=max(1, metrics.avg_position - 3),
                search_intent='commercial'
            ))

        # Long-tail opportunities (if low traffic)
        if metrics.clicks < 10:
            long_tail = location_data.get('long_tail', [])
            for keyword in long_tail[:2]:  # Top 2
                suggestions.append(KeywordSuggestion(
                    keyword=keyword,
                    category='long_tail',
                    priority='medium',
                    target_position=max(1, metrics.avg_position - 1),
                    search_intent='informational'
                ))

        return suggestions

    async def analyze_performance_issues(
        self,
        profile: BusinessProfile,
        metrics: GSCMetrics
    ) -> List[Dict[str, Any]]:
        """
        Analyze performance issues based on industry-specific thresholds.

        Args:
            profile: Business profile
            metrics: Performance metrics

        Returns:
            List of detected issues with recommendations
        """
        issues = []
        industry_data = self._industry_cache.get(profile.industry, {})
        thresholds = industry_data.get('performance_thresholds', {})

        # Analyze traffic
        traffic_thresholds = thresholds.get('traffic', {'low': 10, 'medium': 50})
        if metrics.clicks < traffic_thresholds['low']:
            issues.append({
                'title': 'Low Organic Traffic',
                'severity': 'critical' if metrics.clicks < 5 else 'high',
                'description': f'Only {metrics.clicks} clicks in the last 30 days for {profile.industry} business',
                'impact': f'Missing {max(0, traffic_thresholds["medium"] - metrics.clicks)} potential clicks per month',
                'recommendation': f'Focus on {profile.location}-specific {profile.industry} keywords',
                'icon': '📈'
            })

        # Analyze rankings
        position_thresholds = thresholds.get('position', {'page_1': 10})
        if metrics.avg_position > position_thresholds['page_1']:
            issues.append({
                'title': 'Poor Search Rankings',
                'severity': 'high',
                'description': f'Average position {metrics.avg_position:.1f} means low visibility for {profile.industry}',
                'impact': 'Pages appear on page 2+ of search results',
                'recommendation': f'Optimize content for {profile.industry} + {profile.location} keywords',
                'icon': '🎯'
            })

        # Analyze CTR
        ctr_thresholds = thresholds.get('ctr', {'low': 2.0})
        if metrics.ctr < ctr_thresholds['low']:
            issues.append({
                'title': 'Low Click-Through Rate',
                'severity': 'medium',
                'description': f'CTR {metrics.ctr:.2f}% is below {profile.industry} average',
                'impact': 'Users see your content but don\'t click',
                'recommendation': f'Improve meta titles with {profile.industry} keywords and {profile.location} focus',
                'icon': '🖱️'
            })

        return issues

    def get_content_strategies(self, profile: BusinessProfile) -> Dict[str, Any]:
        """Get content strategies for the business profile"""
        industry_data = self._industry_cache.get(profile.industry, {})
        return industry_data.get('content_strategies', {})

    def get_available_industries(self) -> List[str]:
        """Get list of available industries in knowledge base"""
        return list(self._industry_cache.keys())

    def get_seo_category_knowledge(self, category: str) -> Dict[str, Any]:
        """Get knowledge for specific SEO category (analytics, technical, local, etc.)"""
        return self._seo_categories_cache.get(category, {})

    def get_available_seo_categories(self) -> List[str]:
        """Get list of available SEO categories in knowledge base"""
        return list(self._seo_categories_cache.keys())

    def get_seo_guidance(self, question_type: str, profile: BusinessProfile = None) -> str:
        """Get specific SEO guidance based on question type and business profile"""
        guidance = ""

        # Determine which SEO category to use based on question
        if any(keyword in question_type.lower() for keyword in ['analytics', 'tracking', 'measure', 'roi', 'performance']):
            category_data = self.get_seo_category_knowledge('analytics')
            if profile and profile.industry in ['construction', 'healthcare', 'technology']:
                specific_guidance = category_data.get('business_specific_reports', {}).get(profile.industry, {})
                if specific_guidance:
                    guidance += f"For your {profile.industry} business: "
                    key_metrics = specific_guidance.get('key_metrics', [])
                    if key_metrics:
                        guidance += f"Focus on {', '.join(key_metrics[:3])}. "

        elif any(keyword in question_type.lower() for keyword in ['technical', 'meta', 'title', 'schema', 'crawl']):
            category_data = self.get_seo_category_knowledge('technical_seo')
            if profile and profile.industry in category_data.get('industry_implementations', {}):
                industry_tech = category_data['industry_implementations'][profile.industry]
                priorities = industry_tech.get('technical_priorities', [])
                if priorities:
                    guidance += f"Technical priorities for {profile.industry}: {', '.join(priorities[:3])}. "

        elif any(keyword in question_type.lower() for keyword in ['local', 'near me', 'citation', 'google business']):
            category_data = self.get_seo_category_knowledge('local_seo')
            if profile and profile.location:
                guidance += f"For local SEO in {profile.location}: "
                if profile.location.lower() == 'singapore':
                    sg_citations = category_data.get('citations', {}).get('singapore_specific', [])
                    if sg_citations:
                        guidance += f"Focus on Singapore-specific directories: {', '.join(sg_citations[:2])}. "

        return guidance if guidance else "Based on SEO best practices: "

    def reload_knowledge(self):
        """Reload knowledge from files (for development/testing)"""
        self._industry_cache = {}
        self._patterns_cache = {}
        self._seo_categories_cache = {}
        self._load_all_knowledge()

# Global instance for easy access
knowledge_manager = KnowledgeManager()