"""
Website Content Crawler for Solvia
===================================
Crawls and analyzes actual website content to understand business type,
services, and content for intelligent SEO recommendations.
"""

import aiohttp
import asyncio
import logging
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, urljoin
import re
from datetime import datetime

logger = logging.getLogger(__name__)


class WebsiteCrawler:
    """
    Crawls website content to analyze and understand the actual business,
    services, and content for accurate SEO recommendations.
    """

    def __init__(self):
        self.session = None
        self.timeout = aiohttp.ClientTimeout(total=10)

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def crawl_website(self, website_url: str, max_pages: int = 5) -> Dict:
        """
        Crawl website and extract content, metadata, and business information.

        Args:
            website_url: Website URL to crawl
            max_pages: Maximum number of pages to crawl

        Returns:
            Dictionary with website analysis
        """
        try:
            if not self.session:
                self.session = aiohttp.ClientSession(timeout=self.timeout)

            # Ensure proper URL format
            if not website_url.startswith(('http://', 'https://')):
                website_url = f'https://{website_url}'

            logger.info(f"Starting crawl of {website_url}")

            # Crawl main page first
            main_page_content = await self._fetch_page(website_url)
            if not main_page_content:
                logger.error(f"Failed to fetch {website_url}")
                return self._get_fallback_analysis(website_url)

            # Parse main page
            soup = BeautifulSoup(main_page_content, 'html.parser')

            # Extract key information
            analysis = {
                'url': website_url,
                'crawled_at': datetime.now().isoformat(),
                'title': self._extract_title(soup),
                'meta_description': self._extract_meta_description(soup),
                'headings': self._extract_headings(soup),
                'content_summary': self._extract_content_summary(soup),
                'business_type': self._detect_business_type(soup, website_url),
                'keywords_found': self._extract_keywords(soup),
                'services': self._extract_services(soup),
                'location': self._extract_location(soup),
                'contact_info': self._extract_contact_info(soup),
                'social_links': self._extract_social_links(soup),
                'technology_stack': self._detect_technology(soup, main_page_content),
                'page_count': 1,
                'internal_links': self._extract_internal_links(soup, website_url)[:10]
            }

            # Crawl additional pages if needed
            if max_pages > 1 and analysis['internal_links']:
                additional_content = []
                for link in analysis['internal_links'][:max_pages-1]:
                    try:
                        page_content = await self._fetch_page(link)
                        if page_content:
                            page_soup = BeautifulSoup(page_content, 'html.parser')
                            additional_content.append(self._extract_content_summary(page_soup))
                            analysis['page_count'] += 1
                    except:
                        continue

                if additional_content:
                    analysis['additional_content'] = ' '.join(additional_content[:3])

            # Generate intelligent summary
            analysis['summary'] = self._generate_summary(analysis)

            logger.info(f"Successfully crawled {website_url}: {analysis['business_type']}")
            return analysis

        except Exception as e:
            logger.error(f"Error crawling {website_url}: {e}")
            return self._get_fallback_analysis(website_url)

    async def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch page content with error handling."""
        try:
            async with self.session.get(url, ssl=False) as response:
                if response.status == 200:
                    return await response.text()
                logger.warning(f"Got status {response.status} for {url}")
                return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.text.strip()

        # Fallback to h1
        h1_tag = soup.find('h1')
        if h1_tag:
            return h1_tag.text.strip()

        return "No title found"

    def _extract_meta_description(self, soup: BeautifulSoup) -> str:
        """Extract meta description."""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'].strip()

        # Try og:description
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        if og_desc and og_desc.get('content'):
            return og_desc['content'].strip()

        return ""

    def _extract_headings(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Extract all headings organized by level."""
        headings = {
            'h1': [h.text.strip() for h in soup.find_all('h1')[:5]],
            'h2': [h.text.strip() for h in soup.find_all('h2')[:10]],
            'h3': [h.text.strip() for h in soup.find_all('h3')[:10]]
        }
        return headings

    def _extract_content_summary(self, soup: BeautifulSoup) -> str:
        """Extract main content summary from page."""
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Try to find main content areas
        main_areas = soup.find_all(['main', 'article', 'section'])
        if main_areas:
            text = ' '.join([area.get_text() for area in main_areas[:3]])
        else:
            text = soup.get_text()

        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)

        # Return first 500 words
        words = text.split()[:500]
        return ' '.join(words)

    def _detect_business_type(self, soup: BeautifulSoup, url: str) -> str:
        """Detect business type from content and URL."""
        content = soup.get_text().lower()
        domain = urlparse(url).netloc.lower()

        # Check for personal portfolio indicators
        personal_indicators = [
            'portfolio', 'resume', 'cv', 'about me', 'my projects',
            'personal', 'freelancer', 'developer', 'designer',
            'software engineer', 'web developer', 'full-stack',
            'years of experience', 'skills', 'github', 'linkedin'
        ]

        personal_score = sum(1 for indicator in personal_indicators if indicator in content)

        # Check for business indicators
        business_indicators = [
            'services', 'solutions', 'products', 'pricing',
            'contact us', 'our team', 'company', 'corporation',
            'ltd', 'llc', 'inc', 'pte', 'about us'
        ]

        business_score = sum(1 for indicator in business_indicators if indicator in content)

        # Specific industry detection
        industries = {
            'technology': ['software', 'technology', 'it services', 'development', 'programming', 'coding', 'api', 'cloud'],
            'construction': ['construction', 'building', 'contractor', 'renovation', 'architecture', 'engineering'],
            'healthcare': ['health', 'medical', 'clinic', 'hospital', 'doctor', 'patient', 'treatment'],
            'education': ['education', 'learning', 'school', 'university', 'course', 'training', 'student'],
            'ecommerce': ['shop', 'store', 'buy', 'cart', 'product', 'price', 'checkout', 'shipping'],
            'consulting': ['consulting', 'advisory', 'strategy', 'management', 'business solutions'],
            'finance': ['finance', 'investment', 'banking', 'insurance', 'loan', 'credit'],
            'marketing': ['marketing', 'advertising', 'seo', 'digital', 'social media', 'branding']
        }

        detected_industry = 'general'
        max_industry_score = 0

        for industry, keywords in industries.items():
            score = sum(1 for keyword in keywords if keyword in content)
            if score > max_industry_score:
                max_industry_score = score
                detected_industry = industry

        # Determine if personal or business
        if personal_score > business_score and personal_score > 3:
            if 'developer' in content or 'engineer' in content or 'programmer' in content:
                return 'personal_portfolio_developer'
            elif 'designer' in content:
                return 'personal_portfolio_designer'
            else:
                return 'personal_portfolio'
        elif detected_industry != 'general':
            return f'{detected_industry}_business'
        else:
            return 'general_business'

    def _extract_keywords(self, soup: BeautifulSoup) -> List[str]:
        """Extract important keywords from content."""
        content = soup.get_text().lower()

        # Remove common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     'of', 'with', 'by', 'from', 'about', 'as', 'is', 'was', 'are', 'were'}

        # Extract words
        words = re.findall(r'\b[a-z]+\b', content)
        word_freq = {}

        for word in words:
            if len(word) > 3 and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Sort by frequency
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)

        # Return top keywords
        return [word for word, _ in sorted_words[:20]]

    def _extract_services(self, soup: BeautifulSoup) -> List[str]:
        """Extract services or offerings from content."""
        services = []

        # Look for services sections
        service_sections = soup.find_all(['section', 'div'], class_=re.compile('service|offering|solution|product', re.I))

        for section in service_sections[:5]:
            headings = section.find_all(['h2', 'h3', 'h4'])
            for heading in headings:
                service_text = heading.text.strip()
                if service_text and len(service_text) < 100:
                    services.append(service_text)

        # Also check list items
        service_lists = soup.find_all(['ul', 'ol'])
        for lst in service_lists[:3]:
            items = lst.find_all('li')
            for item in items[:5]:
                text = item.text.strip()
                if 5 < len(text) < 100 and any(word in text.lower() for word in ['service', 'offer', 'provide', 'solution']):
                    services.append(text)

        return list(set(services))[:10]

    def _extract_location(self, soup: BeautifulSoup) -> str:
        """Extract location information."""
        content = soup.get_text()

        # Common location patterns
        locations = []

        # Check for Singapore
        if 'singapore' in content.lower():
            locations.append('Singapore')

        # Check for other major cities
        cities = ['kuala lumpur', 'jakarta', 'bangkok', 'manila', 'hong kong',
                 'tokyo', 'sydney', 'melbourne', 'london', 'new york']

        for city in cities:
            if city in content.lower():
                locations.append(city.title())

        # Check address patterns
        address_pattern = r'\b\d{1,5}\s+\w+\s+(street|road|avenue|lane|drive|place|boulevard)\b'
        addresses = re.findall(address_pattern, content, re.I)
        if addresses:
            locations.append('Address found')

        return ', '.join(locations[:3]) if locations else 'Not specified'

    def _extract_contact_info(self, soup: BeautifulSoup) -> Dict:
        """Extract contact information."""
        content = soup.get_text()
        contact = {}

        # Email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, content)
        if emails:
            contact['email'] = emails[0]

        # Phone
        phone_pattern = r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}'
        phones = re.findall(phone_pattern, content)
        if phones:
            contact['phone'] = phones[0]

        return contact

    def _extract_social_links(self, soup: BeautifulSoup) -> List[str]:
        """Extract social media links."""
        social_domains = ['facebook.com', 'twitter.com', 'linkedin.com',
                         'instagram.com', 'youtube.com', 'github.com']

        social_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            for domain in social_domains:
                if domain in href:
                    social_links.append(href)
                    break

        return list(set(social_links))[:5]

    def _detect_technology(self, soup: BeautifulSoup, html_content: str) -> List[str]:
        """Detect technology stack."""
        tech_stack = []

        # Check meta generators
        generator = soup.find('meta', attrs={'name': 'generator'})
        if generator and generator.get('content'):
            tech_stack.append(generator['content'])

        # Check for common frameworks
        if 'wp-content' in html_content:
            tech_stack.append('WordPress')
        if 'react' in html_content.lower():
            tech_stack.append('React')
        if 'vue' in html_content.lower():
            tech_stack.append('Vue.js')
        if 'angular' in html_content.lower():
            tech_stack.append('Angular')
        if 'bootstrap' in html_content.lower():
            tech_stack.append('Bootstrap')

        return tech_stack[:5]

    def _extract_internal_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract internal links for further crawling."""
        internal_links = []
        parsed_base = urlparse(base_url)

        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            parsed_url = urlparse(full_url)

            # Check if internal link
            if parsed_url.netloc == parsed_base.netloc:
                internal_links.append(full_url)

        return list(set(internal_links))[:20]

    def _generate_summary(self, analysis: Dict) -> str:
        """Generate intelligent summary of website."""
        business_type = analysis['business_type']
        title = analysis['title']
        location = analysis['location']
        services = analysis['services']

        if 'personal_portfolio' in business_type:
            summary = f"This is a personal portfolio website for {title}. "
            if 'developer' in business_type:
                summary += "The site showcases software development skills and projects. "
            elif 'designer' in business_type:
                summary += "The site showcases design work and creative projects. "
        else:
            industry = business_type.replace('_business', '')
            summary = f"This is a {industry} business website. "

        if location != 'Not specified':
            summary += f"The business appears to be based in {location}. "

        if services:
            summary += f"Key services/offerings include: {', '.join(services[:3])}. "

        if analysis['keywords_found']:
            top_keywords = ', '.join(analysis['keywords_found'][:5])
            summary += f"Main content themes: {top_keywords}."

        return summary

    def _get_fallback_analysis(self, website_url: str) -> Dict:
        """Provide fallback analysis when crawling fails."""
        domain = urlparse(website_url).netloc

        # Intelligent domain analysis
        business_type = 'general_business'
        if any(word in domain for word in ['tech', 'it', 'soft', 'dev', 'code']):
            business_type = 'technology_business'
        elif any(word in domain for word in ['build', 'construct', 'contractor']):
            business_type = 'construction_business'
        elif any(word in domain for word in ['health', 'med', 'clinic', 'doctor']):
            business_type = 'healthcare_business'
        elif any(word in domain for word in ['shop', 'store', 'buy', 'mart']):
            business_type = 'ecommerce_business'

        return {
            'url': website_url,
            'crawled_at': datetime.now().isoformat(),
            'title': f"Website at {domain}",
            'business_type': business_type,
            'summary': f"Unable to crawl {website_url} directly. Business type estimated as {business_type} based on domain analysis.",
            'location': 'Singapore' if '.sg' in domain else 'Not specified',
            'fallback': True
        }


async def analyze_website(url: str) -> Dict:
    """
    Convenience function to analyze a website.

    Args:
        url: Website URL to analyze

    Returns:
        Website analysis dictionary
    """
    async with WebsiteCrawler() as crawler:
        return await crawler.crawl_website(url)