"""
Business Analysis Module for SEO Audit Tool
Analyzes websites to understand business context and provide personalized SEO recommendations
"""

import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
import json
from datetime import datetime

class BusinessAnalyzer:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def analyze_business(self, url):
        """Complete business intelligence analysis of a website."""
        print(f"\t🔍 Analyzing business intelligence for {url}...")
        
        # Get website content
        response = self.session.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract all business intelligence
        business_data = {
            **self._analyze_business_model(soup, url),
            **self._analyze_target_audience(soup),
            **self._analyze_services_products(soup),
            **self._analyze_geographic_focus(soup),
            **self._analyze_business_maturity(soup),
            **self._analyze_technology_platform(soup),
            **self._analyze_content_marketing(soup),
            **self._analyze_contact_communication(soup),
            **self._analyze_competitive_position(soup)
        }
        
        # Generate insights and recommendations
        business_data['business_insights'] = self._generate_business_insights(business_data)
        business_data['seo_strategy_recommendations'] = self._generate_seo_strategy(business_data)
        
        print(f"\t\t✓ Business analysis completed - Model: {business_data.get('business_model', 'Unknown')}")
        return business_data
    
    def _analyze_business_model(self, soup, url):
        """Determine business model and target market."""
        print(f"\t\t\tAnalyzing business model...")
        
        text_content = soup.get_text().lower()
        
        # E-commerce indicators
        ecommerce_indicators = ['add to cart', 'shopping cart', 'checkout', 'buy now', 'add to bag', 'shop now', 'product', 'store', 'price', '$']
        ecommerce_score = sum(1 for indicator in ecommerce_indicators if indicator in text_content)
        
        # SaaS indicators
        saas_indicators = ['free trial', 'sign up', 'dashboard', 'api', 'subscription', 'pricing plans', 'software', 'platform', 'cloud']
        saas_score = sum(1 for indicator in saas_indicators if indicator in text_content)
        
        # Service business indicators
        service_indicators = ['consultation', 'consulting', 'services', 'expertise', 'professional', 'experience', 'solutions']
        service_score = sum(1 for indicator in service_indicators if indicator in text_content)
        
        # Local business indicators
        local_indicators = ['location', 'address', 'directions', 'hours', 'near me', 'local', 'visit us', 'call us']
        local_score = sum(1 for indicator in local_indicators if indicator in text_content)
        
        # Determine business model
        scores = {
            'E-commerce': ecommerce_score,
            'SaaS': saas_score,
            'Professional Services': service_score,
            'Local Services': service_score + local_score
        }
        
        business_model = max(scores.items(), key=lambda x: x[1])[0] if max(scores.values()) > 2 else 'Information/Content'
        
        # B2B vs B2C indicators
        b2b_indicators = ['enterprise', 'business', 'corporate', 'b2b', 'companies', 'organizations', 'team', 'workflow']
        b2c_indicators = ['personal', 'individual', 'family', 'home', 'consumer', 'lifestyle', 'fashion']
        
        b2b_score = sum(1 for indicator in b2b_indicators if indicator in text_content)
        b2c_score = sum(1 for indicator in b2c_indicators if indicator in text_content)
        
        target_market = 'B2B' if b2b_score > b2c_score else 'B2C'
        
        # Industry detection
        industry_keywords = {
            'Technology': ['software', 'tech', 'digital', 'IT', 'development', 'app'],
            'Healthcare': ['health', 'medical', 'doctor', 'clinic', 'wellness', 'therapy'],
            'Finance': ['finance', 'banking', 'investment', 'money', 'financial', 'accounting'],
            'Education': ['education', 'learning', 'course', 'training', 'school', 'university'],
            'Retail': ['retail', 'shopping', 'fashion', 'clothing', 'store'],
            'Real Estate': ['real estate', 'property', 'homes', 'realtor', 'mortgage'],
            'Marketing': ['marketing', 'advertising', 'promotion', 'brand', 'social media']
        }
        
        industry_sector = 'General'
        max_industry_score = 0
        for industry, keywords in industry_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_content)
            if score > max_industry_score:
                max_industry_score = score
                industry_sector = industry
        
        # Company size estimation
        size_indicators = {
            'Enterprise': ['fortune 500', 'global', 'worldwide', 'international', 'enterprise'],
            'Large': ['team of', 'employees', 'staff', 'offices', 'locations'],
            'Medium': ['growing', 'established', 'experienced', 'years'],
            'Small': ['small business', 'local', 'family owned', 'boutique'],
            'Startup': ['startup', 'new', 'innovative', 'disrupting', 'young company']
        }
        
        company_size = 'Small'  # Default
        for size, keywords in size_indicators.items():
            if any(keyword in text_content for keyword in keywords):
                company_size = size
                break
        
        return {
            'business_model': business_model,
            'target_market': target_market,
            'industry_sector': industry_sector,
            'company_size': company_size
        }
    
    def _analyze_target_audience(self, soup):
        """Analyze target audience characteristics."""
        print(f"\t\t\tAnalyzing target audience...")
        
        text_content = soup.get_text().lower()
        
        # Age demographics
        age_indicators = {
            'Young Adults': ['millennials', 'young', 'students', 'college', 'trendy', 'modern'],
            'Middle Age': ['professionals', 'families', 'parents', 'career', 'experienced'],
            'Seniors': ['seniors', 'retirement', 'elderly', 'mature', 'golden years']
        }
        
        primary_age_group = 'General'
        max_score = 0
        for age_group, indicators in age_indicators.items():
            score = sum(1 for indicator in indicators if indicator in text_content)
            if score > max_score:
                max_score = score
                primary_age_group = age_group
        
        # Income level indicators
        income_indicators = {
            'Luxury': ['luxury', 'premium', 'exclusive', 'high-end', 'elite', 'bespoke'],
            'Premium': ['quality', 'professional', 'premium', 'expert', 'sophisticated'],
            'Mid-Range': ['affordable', 'value', 'reasonable', 'competitive'],
            'Budget': ['cheap', 'budget', 'discount', 'low-cost', 'economical']
        }
        
        income_level = 'Mid-Range'  # Default
        max_score = 0
        for level, indicators in income_indicators.items():
            score = sum(1 for indicator in indicators if indicator in text_content)
            if score > max_score:
                max_score = score
                income_level = level
        
        # Audience sophistication
        sophistication_indicators = {
            'Expert': ['advanced', 'expert', 'professional', 'technical', 'specialized'],
            'High': ['experienced', 'knowledgeable', 'informed', 'savvy'],
            'General': ['easy', 'simple', 'user-friendly', 'accessible'],
            'Basic': ['beginner', 'basic', 'simple', 'easy to use']
        }
        
        audience_sophistication = 'General'  # Default
        max_score = 0
        for level, indicators in sophistication_indicators.items():
            score = sum(1 for indicator in indicators if indicator in text_content)
            if score > max_score:
                max_score = score
                audience_sophistication = level
        
        return {
            'primary_age_group': primary_age_group,
            'income_level': income_level,
            'audience_sophistication': audience_sophistication
        }
    
    def _analyze_services_products(self, soup):
        """Extract services and products information."""
        print(f"\t\t\tAnalyzing services/products...")
        
        text_content = soup.get_text().lower()
        
        # E-commerce detection
        has_ecommerce = any(indicator in text_content for indicator in [
            'add to cart', 'shopping cart', 'checkout', 'buy now', 'shop', 'store'
        ])
        
        # Local presence detection
        has_local_presence = any(indicator in text_content for indicator in [
            'address', 'location', 'visit us', 'directions', 'hours', 'phone'
        ])
        
        # Services extraction
        service_sections = soup.find_all(['div', 'section'], class_=re.compile(r'service|product', re.I))
        services = []
        for section in service_sections[:5]:
            text = section.get_text().strip()
            if 20 < len(text) < 200:
                services.append(text[:100])
        
        services_offered = '; '.join(services[:3]) if services else 'Not specified'
        
        # Pricing visibility
        pricing_indicators = soup.find_all(text=re.compile(r'\$\d+|\d+\s*USD|price|cost|fee', re.I))
        has_public_pricing = len(pricing_indicators) > 0
        
        # Business complexity (based on navigation and content)
        nav_links = len(soup.find_all('a'))
        complexity_score = min(10, max(1, nav_links // 10))
        
        return {
            'has_ecommerce': has_ecommerce,
            'has_local_presence': has_local_presence,
            'business_complexity_score': complexity_score,
            'services_offered': services_offered,
            'has_public_pricing': has_public_pricing,
            'service_count': len(services)
        }
    
    def _analyze_geographic_focus(self, soup):
        """Determine geographic focus and target markets."""
        print(f"\t\t\tAnalyzing geographic focus...")
        
        text_content = soup.get_text()
        
        # Location pattern matching
        location_patterns = [
            r'\b[A-Z][a-z]+,\s*[A-Z]{2}\b',  # City, State
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+,\s*[A-Z]{2}\b',  # City Name, State
        ]
        
        locations = []
        for pattern in location_patterns:
            matches = re.findall(pattern, text_content)
            locations.extend(matches[:3])
        
        target_locations = '; '.join(locations) if locations else ''
        
        # Geographic scope indicators
        global_indicators = ['worldwide', 'global', 'international', 'countries', 'worldwide shipping']
        national_indicators = ['nationwide', 'across the country', 'all states', 'national']
        regional_indicators = ['regional', 'tri-state', 'west coast', 'east coast', 'midwest']
        local_indicators = ['local', 'nearby', 'in your area', 'serving', 'community']
        
        text_lower = text_content.lower()
        
        if any(indicator in text_lower for indicator in global_indicators):
            geographic_scope = 'Global'
        elif any(indicator in text_lower for indicator in national_indicators):
            geographic_scope = 'National'
        elif any(indicator in text_lower for indicator in regional_indicators):
            geographic_scope = 'Regional'
        elif any(indicator in text_lower for indicator in local_indicators) or locations:
            geographic_scope = 'Local'
        else:
            geographic_scope = 'National'  # Default
        
        is_location_based = geographic_scope in ['Local', 'Regional'] or bool(locations)
        
        return {
            'geographic_scope': geographic_scope,
            'target_locations': target_locations,
            'is_location_based': is_location_based
        }
    
    def _analyze_business_maturity(self, soup):
        """Analyze business maturity and establishment."""
        print(f"\t\t\tAnalyzing business maturity...")
        
        text_content = soup.get_text().lower()
        
        # Maturity indicators
        maturity_indicators = {
            'Startup': ['startup', 'new', 'launching', 'innovative', 'disrupting', 'founded recently'],
            'Growing': ['growing', 'expanding', 'scaling', 'developing', 'emerging'],
            'Established': ['established', 'experienced', 'years of experience', 'proven', 'trusted'],
            'Mature': ['industry leader', 'market leader', 'decades', 'pioneer', 'veteran']
        }
        
        business_maturity = 'Growing'  # Default
        max_score = 0
        for maturity, indicators in maturity_indicators.items():
            score = sum(1 for indicator in indicators if indicator in text_content)
            if score > max_score:
                max_score = score
                business_maturity = maturity
        
        # Extract establishment year
        year_pattern = r'since\s+(\d{4})|established\s+(\d{4})|founded\s+(\d{4})'
        year_match = re.search(year_pattern, text_content)
        establishment_year = None
        if year_match:
            year = next(group for group in year_match.groups() if group)
            establishment_year = int(year) if 1900 <= int(year) <= 2024 else None
        
        # Experience indicators
        experience_indicators = ['years of experience', 'expertise', 'specialist', 'expert', 'professional']
        experience_indicators_found = any(indicator in text_content for indicator in experience_indicators)
        
        return {
            'business_maturity': business_maturity,
            'establishment_year': establishment_year,
            'experience_indicators': experience_indicators_found
        }
    
    def _analyze_technology_platform(self, soup):
        """Analyze technology platform and sophistication."""
        print(f"\t\t\tAnalyzing technology platform...")
        
        # Platform detection
        platform_indicators = {
            'WordPress': ['wp-content', 'wordpress', 'wp-includes'],
            'Shopify': ['shopify', 'cdn.shopify.com', 'myshopify.com'],
            'Wix': ['wix.com', 'wixstatic.com'],
            'Squarespace': ['squarespace', 'sqsp.com'],
            'Webflow': ['webflow.com', 'webflow.io'],
            'Custom': ['custom', 'bespoke', 'proprietary']
        }
        
        html_content = str(soup).lower()
        platform_detected = 'Unknown'
        for platform, indicators in platform_indicators.items():
            if any(indicator in html_content for indicator in indicators):
                platform_detected = platform
                break
        
        # Advanced features detection
        advanced_features = [
            'search functionality', 'user accounts', 'dashboard', 'api', 'integration',
            'automation', 'analytics', 'tracking', 'personalization'
        ]
        text_content = soup.get_text().lower()
        has_advanced_features = sum(1 for feature in advanced_features if feature in text_content) >= 2
        
        # Social media integration
        social_indicators = ['facebook', 'twitter', 'linkedin', 'instagram', 'youtube', 'social']
        social_media_integration = any(indicator in html_content for indicator in social_indicators)
        
        # Technology sophistication
        tech_indicators = {
            'Advanced': ['machine learning', 'ai', 'artificial intelligence', 'blockchain', 'cloud'],
            'High': ['api', 'integration', 'automation', 'analytics', 'dashboard'],
            'Medium': ['responsive', 'mobile', 'search', 'contact form'],
            'Basic': ['simple', 'basic', 'static', 'minimal']
        }
        
        tech_sophistication = 'Medium'  # Default
        max_score = 0
        for level, indicators in tech_indicators.items():
            score = sum(1 for indicator in indicators if indicator in text_content)
            if score > max_score:
                max_score = score
                tech_sophistication = level
        
        return {
            'platform_detected': platform_detected,
            'has_advanced_features': has_advanced_features,
            'social_media_integration': social_media_integration,
            'tech_sophistication': tech_sophistication
        }
    
    def _analyze_content_marketing(self, soup):
        """Analyze content marketing and lead generation."""
        print(f"\t\t\tAnalyzing content marketing...")
        
        text_content = soup.get_text().lower()
        
        # Content marketing indicators
        content_indicators = ['blog', 'articles', 'resources', 'guides', 'tips', 'news', 'insights']
        has_content_marketing = any(indicator in text_content for indicator in content_indicators)
        
        # Lead generation indicators
        lead_gen_indicators = ['newsletter', 'subscribe', 'download', 'free trial', 'demo', 'consultation']
        has_lead_generation = any(indicator in text_content for indicator in lead_gen_indicators)
        
        # Social proof indicators
        social_proof_indicators = ['testimonials', 'reviews', 'clients', 'customers', 'case studies', 'success stories']
        has_social_proof = any(indicator in text_content for indicator in social_proof_indicators)
        
        # Content maturity assessment
        content_elements = sum([
            has_content_marketing,
            has_lead_generation,
            has_social_proof,
            'about' in text_content,
            'contact' in text_content
        ])
        
        if content_elements >= 4:
            content_maturity = 'Advanced'
        elif content_elements >= 3:
            content_maturity = 'Mature'
        elif content_elements >= 2:
            content_maturity = 'Developing'
        else:
            content_maturity = 'Basic'
        
        return {
            'has_content_marketing': has_content_marketing,
            'has_lead_generation': has_lead_generation,
            'has_social_proof': has_social_proof,
            'content_maturity': content_maturity
        }
    
    def _analyze_contact_communication(self, soup):
        """Analyze contact methods and communication preferences."""
        print(f"\t\t\tAnalyzing contact communication...")
        
        text_content = soup.get_text().lower()
        html_content = str(soup).lower()
        
        # Phone prominence
        phone_patterns = [r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}', r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}']
        phone_prominence = any(re.search(pattern, soup.get_text()) for pattern in phone_patterns)
        
        # Contact forms
        has_contact_forms = 'contact' in text_content and ('form' in html_content or 'input' in html_content)
        
        # Live chat
        chat_indicators = ['live chat', 'chat with us', 'online chat', 'support chat']
        has_live_chat = any(indicator in text_content for indicator in chat_indicators)
        
        # Preferred contact method
        contact_methods = {
            'Phone': phone_prominence,
            'Email': 'email' in text_content or 'contact' in text_content,
            'Form': has_contact_forms,
            'Chat': has_live_chat,
            'Social': 'social' in text_content
        }
        
        preferred_contact_method = max(contact_methods.items(), key=lambda x: x[1])[0]
        
        return {
            'phone_prominence': phone_prominence,
            'has_contact_forms': has_contact_forms,
            'has_live_chat': has_live_chat,
            'preferred_contact_method': preferred_contact_method
        }
    
    def _analyze_competitive_position(self, soup):
        """Analyze competitive positioning and brand strength."""
        print(f"\t\t\tAnalyzing competitive positioning...")
        
        text_content = soup.get_text().lower()
        
        # Competitive positioning indicators
        leader_indicators = ['leader', 'leading', 'first', '#1', 'pioneer', 'industry leader']
        challenger_indicators = ['competitive', 'alternative', 'better than', 'compared to']
        niche_indicators = ['specialized', 'niche', 'boutique', 'custom', 'personalized']
        
        if any(indicator in text_content for indicator in leader_indicators):
            competitive_positioning = 'Leader'
        elif any(indicator in text_content for indicator in challenger_indicators):
            competitive_positioning = 'Challenger'
        elif any(indicator in text_content for indicator in niche_indicators):
            competitive_positioning = 'Niche'
        else:
            competitive_positioning = 'Follower'
        
        # Positioning strength
        strength_indicators = {
            'Dominant': ['market leader', 'industry standard', 'best in class'],
            'Strong': ['trusted', 'proven', 'established', 'recognized'],
            'Medium': ['quality', 'reliable', 'professional'],
            'Weak': ['new', 'trying', 'hoping', 'working towards']
        }
        
        positioning_strength = 'Medium'  # Default
        for strength, indicators in strength_indicators.items():
            if any(indicator in text_content for indicator in indicators):
                positioning_strength = strength
                break
        
        # Value proposition extraction
        value_prop_indicators = ['unique', 'difference', 'why choose', 'what makes us', 'our advantage']
        value_proposition = 'Quality service and expertise'  # Default
        for indicator in value_prop_indicators:
            if indicator in text_content:
                # Try to extract surrounding text
                pattern = rf'{indicator}[^.]*\.?'
                match = re.search(pattern, soup.get_text(), re.IGNORECASE)
                if match:
                    value_proposition = match.group()[:100]
                    break
        
        # Brand strength assessment
        brand_indicators = {
            'Very Strong': ['award', 'certified', 'accredited', 'recognized'],
            'Strong': ['trusted', 'established', 'reputation'],
            'Medium': ['professional', 'quality', 'experienced'],
            'Weak': ['new', 'growing', 'developing']
        }
        
        brand_strength = 'Medium'  # Default
        for strength, indicators in brand_indicators.items():
            if any(indicator in text_content for indicator in indicators):
                brand_strength = strength
                break
        
        # Trust indicators
        trust_elements = []
        trust_checks = {
            'SSL Certificate': 'https://' in str(soup),
            'Testimonials': 'testimonial' in text_content,
            'Reviews': 'review' in text_content,
            'Certifications': any(cert in text_content for cert in ['certified', 'accredited', 'licensed']),
            'Awards': 'award' in text_content,
            'Guarantees': any(guarantee in text_content for guarantee in ['guarantee', 'warranty', 'promise'])
        }
        
        trust_indicators = '; '.join([element for element, present in trust_checks.items() if present])
        
        return {
            'competitive_positioning': competitive_positioning,
            'positioning_strength': positioning_strength,
            'value_proposition': value_proposition,
            'brand_strength': brand_strength,
            'trust_indicators': trust_indicators or 'Basic website security'
        }
    
    def _generate_business_insights(self, business_data):
        """Generate business insights based on analysis."""
        insights = []
        
        # Business model insights
        model = business_data.get('business_model', '')
        if model == 'E-commerce':
            insights.append("E-commerce business with strong transactional focus")
        elif model == 'SaaS':
            insights.append("Software-as-a-Service model with subscription potential")
        elif model == 'Professional Services':
            insights.append("Service-based business requiring trust and expertise positioning")
        
        # Market insights
        if business_data.get('target_market') == 'B2B':
            insights.append("B2B focus requires professional credibility and case studies")
        else:
            insights.append("B2C focus benefits from emotional appeal and user reviews")
        
        # Geographic insights
        scope = business_data.get('geographic_scope', '')
        if scope == 'Local':
            insights.append("Local business needs local SEO optimization")
        elif scope == 'Global':
            insights.append("Global reach requires international SEO strategy")
        
        # Technology insights
        tech_level = business_data.get('tech_sophistication', '')
        if tech_level == 'Basic':
            insights.append("Basic technology setup may limit advanced SEO implementations")
        elif tech_level == 'Advanced':
            insights.append("Advanced technology allows for sophisticated SEO strategies")
        
        return '; '.join(insights) if insights else 'General business analysis completed'
    
    def _generate_seo_strategy(self, business_data):
        """Generate SEO strategy recommendations based on business analysis."""
        recommendations = []
        
        # Model-based recommendations
        model = business_data.get('business_model', '')
        if model == 'E-commerce':
            recommendations.append("Focus on product page optimization and transactional keywords")
            recommendations.append("Implement structured data for products and reviews")
        elif model == 'SaaS':
            recommendations.append("Target feature-based and comparison keywords")
            recommendations.append("Create comprehensive help documentation for long-tail SEO")
        elif model == 'Professional Services':
            recommendations.append("Build authority through thought leadership content")
            recommendations.append("Optimize for service-specific and local keywords")
        elif model == 'Local Services':
            recommendations.append("Prioritize local SEO and Google My Business optimization")
            recommendations.append("Target location-based and service keywords")
        
        # Geographic recommendations
        scope = business_data.get('geographic_scope', '')
        if scope == 'Local':
            recommendations.append("Implement local schema markup and NAP consistency")
        elif scope == 'Global':
            recommendations.append("Consider international SEO and hreflang implementation")
        
        # Content recommendations
        content_maturity = business_data.get('content_maturity', '')
        if content_maturity in ['Basic', 'Developing']:
            recommendations.append("Develop comprehensive content marketing strategy")
        
        # Competitive recommendations
        positioning = business_data.get('competitive_positioning', '')
        if positioning == 'Leader':
            recommendations.append("Focus on brand protection and thought leadership SEO")
        elif positioning == 'Challenger':
            recommendations.append("Target competitor comparison keywords and alternative searches")
        
        return '; '.join(recommendations) if recommendations else 'Implement comprehensive SEO strategy based on business goals'
    
    def _get_default_business_data(self):
        """Return default business data structure when analysis fails."""
        return {
            'business_model': 'Information/Content',
            'target_market': 'B2C',
            'industry_sector': 'General',
            'company_size': 'Small',
            'has_ecommerce': False,
            'has_local_presence': False,
            'business_complexity_score': 3,
            'primary_age_group': 'General',
            'income_level': 'Mid-Range',
            'audience_sophistication': 'General',
            'services_offered': 'Not specified',
            'has_public_pricing': False,
            'service_count': 0,
            'geographic_scope': 'National',
            'target_locations': '',
            'is_location_based': False,
            'business_maturity': 'Growing',
            'establishment_year': None,
            'experience_indicators': False,
            'platform_detected': 'Unknown',
            'has_advanced_features': False,
            'social_media_integration': False,
            'tech_sophistication': 'Medium',
            'has_content_marketing': False,
            'has_lead_generation': False,
            'has_social_proof': False,
            'content_maturity': 'Basic',
            'phone_prominence': False,
            'has_contact_forms': False,
            'has_live_chat': False,
            'preferred_contact_method': 'Email',
            'competitive_positioning': 'Follower',
            'positioning_strength': 'Medium',
            'value_proposition': 'Quality service and expertise',
            'brand_strength': 'Medium',
            'trust_indicators': 'Basic website security',
            'business_insights': 'Limited business analysis due to access restrictions',
            'seo_strategy_recommendations': 'Implement basic SEO best practices and content strategy'
        } 