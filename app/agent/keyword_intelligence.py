"""
Keyword Intelligence Module
===========================
Provides intelligent keyword suggestions when GSC data is unavailable.
Leverages knowledge base and industry patterns.
"""

import yaml
import os
from typing import List, Dict, Any, Optional
from pathlib import Path


class KeywordIntelligence:
    """Generate intelligent keyword suggestions using knowledge base and industry patterns."""

    def __init__(self):
        self.knowledge_path = Path(__file__).parent.parent / "knowledge"
        self._load_knowledge_base()

    def _load_knowledge_base(self):
        """Load all knowledge base files."""
        self.industry_data = {}
        self.seo_categories = {}

        # Load industry patterns
        industry_file = self.knowledge_path / "business_detection" / "domain_patterns.yaml"
        if industry_file.exists():
            with open(industry_file, 'r') as f:
                self.industry_data = yaml.safe_load(f)

        # Load SEO category knowledge
        seo_files = [
            "analytics.yaml",
            "technical_seo.yaml",
            "local_seo.yaml"
        ]

        for filename in seo_files:
            file_path = self.knowledge_path / "seo_categories" / filename
            if file_path.exists():
                with open(file_path, 'r') as f:
                    category_name = filename.replace('.yaml', '')
                    self.seo_categories[category_name] = yaml.safe_load(f)

    def detect_business_type(self, website_url: Optional[str] = None, business_description: Optional[str] = None) -> str:
        """Detect business type from URL or description."""
        if not website_url and not business_description:
            return "general"

        text_to_analyze = (website_url or "").lower() + " " + (business_description or "").lower()

        # Check against industry patterns
        if 'business_types' in self.industry_data:
            for industry, data in self.industry_data['business_types'].items():
                if 'keywords' in data:
                    keywords = data['keywords']
                    matches = sum(1 for keyword in keywords if keyword.lower() in text_to_analyze)
                    if matches >= 2:  # At least 2 keyword matches
                        return industry

        return "general"

    def get_industry_keywords(self, industry: str, location: str = "singapore") -> Dict[str, List[str]]:
        """Get industry-specific keyword suggestions."""

        keyword_templates = {
            "construction": {
                "primary": [
                    "construction company {location}",
                    "building contractor {location}",
                    "renovation services {location}",
                    "home builder {location}",
                    "commercial construction {location}"
                ],
                "long_tail": [
                    "best construction company in {location}",
                    "affordable renovation services {location}",
                    "commercial building contractor {location}",
                    "residential construction {location}",
                    "construction project management {location}"
                ],
                "local": [
                    "construction near me",
                    "builders in {location}",
                    "local construction company",
                    "trusted contractor {location}",
                    "{location} building services"
                ]
            },
            "healthcare": {
                "primary": [
                    "medical clinic {location}",
                    "healthcare services {location}",
                    "specialist doctor {location}",
                    "medical center {location}",
                    "health screening {location}"
                ],
                "long_tail": [
                    "best medical clinic in {location}",
                    "comprehensive health checkup {location}",
                    "family doctor {location}",
                    "preventive healthcare {location}",
                    "medical consultation {location}"
                ],
                "local": [
                    "doctor near me",
                    "medical clinic near me",
                    "healthcare {location}",
                    "trusted doctor {location}",
                    "{location} medical services"
                ]
            },
            "technology": {
                "primary": [
                    "software development {location}",
                    "IT services {location}",
                    "web development {location}",
                    "digital solutions {location}",
                    "technology consulting {location}"
                ],
                "long_tail": [
                    "custom software development {location}",
                    "enterprise IT solutions {location}",
                    "mobile app development {location}",
                    "cloud services {location}",
                    "digital transformation {location}"
                ],
                "local": [
                    "software company near me",
                    "IT support {location}",
                    "local web developer",
                    "tech company {location}",
                    "{location} software development"
                ]
            },
            "general": {
                "primary": [
                    "business services {location}",
                    "professional services {location}",
                    "local business {location}",
                    "service provider {location}",
                    "company {location}"
                ],
                "long_tail": [
                    "reliable business services {location}",
                    "trusted service provider {location}",
                    "local business directory {location}",
                    "professional consulting {location}",
                    "business solutions {location}"
                ],
                "local": [
                    "services near me",
                    "local business",
                    "professional services {location}",
                    "trusted company {location}",
                    "{location} business directory"
                ]
            }
        }

        if industry not in keyword_templates:
            industry = "general"

        # Format keywords with location
        formatted_keywords = {}
        for category, keywords in keyword_templates[industry].items():
            formatted_keywords[category] = [
                keyword.format(location=location) for keyword in keywords
            ]

        return formatted_keywords

    def get_content_keywords(self, business_type: str) -> List[str]:
        """Get content marketing keyword suggestions."""

        content_templates = {
            "construction": [
                "construction tips",
                "building guide",
                "renovation ideas",
                "construction trends",
                "building materials guide",
                "home improvement tips",
                "construction safety",
                "project planning guide"
            ],
            "healthcare": [
                "health tips",
                "wellness guide",
                "medical advice",
                "preventive care",
                "health screening guide",
                "nutrition tips",
                "fitness advice",
                "mental health"
            ],
            "technology": [
                "tech trends",
                "software guide",
                "digital transformation",
                "technology tips",
                "IT best practices",
                "cybersecurity guide",
                "cloud computing",
                "automation tools"
            ],
            "general": [
                "business tips",
                "industry guide",
                "best practices",
                "professional advice",
                "business growth",
                "success stories",
                "expert insights",
                "how-to guide"
            ]
        }

        return content_templates.get(business_type, content_templates["general"])

    def generate_keyword_suggestions(self,
                                   query: str,
                                   website_url: Optional[str] = None,
                                   business_description: Optional[str] = None,
                                   location: str = "singapore") -> Dict[str, Any]:
        """Generate comprehensive keyword suggestions."""

        # Detect business type
        business_type = self.detect_business_type(website_url, business_description)

        # Get industry-specific keywords
        industry_keywords = self.get_industry_keywords(business_type, location)

        # Get content keywords
        content_keywords = self.get_content_keywords(business_type)

        # Generate keyword research strategy
        strategy = self._generate_keyword_strategy(business_type, location)

        return {
            "business_type": business_type,
            "location": location,
            "primary_keywords": industry_keywords.get("primary", [])[:5],
            "long_tail_keywords": industry_keywords.get("long_tail", [])[:5],
            "local_keywords": industry_keywords.get("local", [])[:5],
            "content_keywords": content_keywords[:8],
            "strategy": strategy,
            "total_suggestions": len(industry_keywords.get("primary", [])) + len(industry_keywords.get("long_tail", [])) + len(content_keywords)
        }

    def _generate_keyword_strategy(self, business_type: str, location: str) -> Dict[str, str]:
        """Generate keyword research strategy."""

        strategies = {
            "construction": {
                "focus": "Target local service keywords with strong commercial intent",
                "priority": "Focus on '[service] + [location]' patterns for high conversion",
                "content": "Create project showcases, how-to guides, and local market insights",
                "tools": "Use Google Keyword Planner, local search suggestions, and competitor analysis"
            },
            "healthcare": {
                "focus": "Target health condition and treatment keywords with medical authority",
                "priority": "Focus on informational and local service keywords for patient acquisition",
                "content": "Create health education content, treatment guides, and wellness tips",
                "tools": "Use medical keyword tools, health topic research, and patient question analysis"
            },
            "technology": {
                "focus": "Target technical solution keywords with B2B commercial intent",
                "priority": "Focus on '[solution] + [industry]' patterns for enterprise clients",
                "content": "Create technical guides, case studies, and industry insights",
                "tools": "Use technical keyword research, B2B search analysis, and industry reports"
            },
            "general": {
                "focus": "Target broad business service keywords with local optimization",
                "priority": "Focus on '[service] + [location]' and '[service] near me' patterns",
                "content": "Create service pages, local market insights, and business guides",
                "tools": "Use Google Keyword Planner, local search tools, and competitor research"
            }
        }

        return strategies.get(business_type, strategies["general"])


# Global instance
keyword_intelligence = KeywordIntelligence()