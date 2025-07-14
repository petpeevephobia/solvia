import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from typing import Dict, List, Optional, Tuple, Any
import time

class MetadataAnalyzer:
    """Analyzes website metadata, images, and SEO elements."""
    
    def __init__(self):
        self.max_pages = 10  # Limit analysis to first 10 pages
        self.timeout = 30  # 30 second timeout per request
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        
    async def analyze_website(self, website_url: str) -> Optional[Dict[str, Any]]:
        """Analyze a website's metadata and SEO elements."""
        try:
            print(f"[DEBUG] Starting metadata analysis for: {website_url}")
            # Clean and normalize the URL
            base_url = self._normalize_url(website_url)
            if not base_url:
                print("[DEBUG] Invalid base URL, aborting analysis.")
                return None
            
            # Get list of pages to analyze
            pages_to_analyze = await self._discover_pages(base_url)
            
            if not pages_to_analyze:
                print("[DEBUG] No pages found to analyze.")
                return None
            
            # Analyze each page
            analysis_results = []
            async with aiohttp.ClientSession() as session:
                
                for i, page_url in enumerate(pages_to_analyze[:self.max_pages]):
                    page_analysis = await self._analyze_page(session, page_url)
                    if page_analysis:
                        analysis_results.append(page_analysis)
            
            # Aggregate results
            if not analysis_results:
                print("[DEBUG] No successful page analyses.")
                return None
                
            aggregated_results = self._aggregate_results(analysis_results)
            
            return aggregated_results
            
        except Exception as e:
            print(f"[DEBUG] Exception in analyze_website: {e}")
            return None
    
    def _normalize_url(self, url: str) -> Optional[str]:
        """Normalize and validate a URL."""
        try:
            if url.startswith('sc-domain:'):
                url = url.replace('sc-domain:', '')
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            parsed = urlparse(url)
            if not parsed.netloc:
                return None
            
            return f"{parsed.scheme}://{parsed.netloc}"
            
        except Exception as e:
            return None

    async def _discover_pages(self, base_url: str) -> List[str]:
        """Discover pages to analyze from sitemap and homepage."""
        try:
            pages = set()
            
            # Try to get sitemap pages
            sitemap_pages = await self._get_sitemap_pages(base_url)
            pages.update(sitemap_pages)
            
            # Get homepage links as fallback
            homepage_links = await self._get_homepage_links(base_url)
            pages.update(homepage_links)
            
            # Always include the homepage
            pages.add(base_url)
            
            return list(pages)
            
        except Exception as e:
            return [base_url]  # Return at least the homepage

    async def _get_sitemap_pages(self, base_url: str) -> List[str]:
        """Get pages from sitemap.xml."""
        try:
            sitemap_urls = [
                f"{base_url}/sitemap.xml",
                f"{base_url}/sitemap_index.xml",
                f"{base_url}/sitemap/sitemap.xml"
            ]
            
            pages = []
            async with aiohttp.ClientSession() as session:
                for sitemap_url in sitemap_urls:
                    try:
                        async with session.get(sitemap_url) as response:
                            if response.status == 200:
                                content = await response.text()
                                pages.extend(self._parse_sitemap(content, base_url))
                                break
                                
                    except Exception as e:
                        continue
            
            return pages
            
        except Exception as e:
            return []

    def _parse_sitemap(self, content: str, base_url: str) -> List[str]:
        """Parse sitemap XML content."""
        try:
            # Simple regex-based parsing
            url_pattern = r'<loc>(.*?)</loc>'
            url_matches = re.findall(url_pattern, content, re.IGNORECASE)
            
            return [url.strip() for url in url_matches if url.strip()]
        except Exception as e:
            return []

    async def _get_homepage_links(self, base_url: str) -> List[str]:
        """Get links from homepage."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(base_url) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # Extract links using regex
                        link_pattern = r'href=["\']([^"\']+)["\']'
                        links = re.findall(link_pattern, content)
                        
                        # Filter and normalize links
                        valid_links = []
                        for link in links:
                            if link.startswith('/'):
                                valid_links.append(urljoin(base_url, link))
                            elif link.startswith('http') and base_url in link:
                                valid_links.append(link)
                        
                        return valid_links[:10]  # Limit to first 10 links
            
            return []
            
        except Exception as e:
            return []

    async def _analyze_page(self, session: aiohttp.ClientSession, page_url: str) -> Optional[Dict[str, Any]]:
        """Analyze a single page for metadata and SEO elements."""
        try:
            print(f"[DEBUG] Fetching page: {page_url}")
            async with session.get(page_url) as response:
                print(f"[DEBUG] HTTP status for {page_url}: {response.status}")
                if response.status != 200:
                    print(f"[DEBUG] Non-200 status for {page_url}, skipping.")
                    return None
                content = await response.text()
                # Extract metadata
                analysis = {
                    'url': page_url,
                    'title': self._extract_title(content),
                    'meta_description': self._extract_meta_description(content),
                    'meta_keywords': self._extract_meta_keywords(content),
                    'h1_tags': self._extract_h1_tags(content),
                    'h2_tags': self._extract_h2_tags(content),
                    'images_without_alt': self._find_images_without_alt(content),
                    'canonical_url': self._extract_canonical_url(content),
                    'robots_meta': self._extract_robots_meta(content),
                    'og_tags': self._extract_og_tags(content),
                    'twitter_tags': self._extract_twitter_tags(content),
                    'schema_markup': self._extract_schema_markup(content)
                }
                return analysis
        except Exception as e:
            print(f"[DEBUG] Exception in _analyze_page for {page_url}: {e}")
            return None
    
    def _is_title_optimized(self, title: str) -> bool:
        """Check if title tag is optimized."""
        if not title:
            return False
        
        # Good title: 30-60 characters, not too generic
        length = len(title)
        if length < 30 or length > 60:
            return False
        
        # Check for generic titles
        generic_titles = ['home', 'welcome', 'untitled', 'page', 'website']
        if title.lower().strip() in generic_titles:
            return False
        
        return True
    
    def _is_description_optimized(self, description: str) -> bool:
        """Check if meta description is optimized."""
        if not description:
            return False
        
        # Good description: 120-160 characters
        length = len(description)
        return 120 <= length <= 160
    
    def _are_h1_tags_optimized(self, h1_tags: List) -> bool:
        """Check if H1 tags are optimized."""
        # Should have exactly 1 H1 tag per page
        if len(h1_tags) != 1:
            return False
        
        # H1 should not be empty
        h1_text = h1_tags[0].get_text().strip()
        return len(h1_text) > 0
    
    def _aggregate_results(self, analysis_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            print(f"[DEBUG] Aggregating results for {len(analysis_results)} pages.")
            aggregated = {
                'total_pages_analyzed': len(analysis_results),
                'pages_with_titles': 0,
                'pages_with_descriptions': 0,
                'pages_with_keywords': 0,
                'total_h1_tags': 0,
                'total_h2_tags': 0,
                'images_with_alt': 0,
                'images_without_alt_count': 0,
                'pages_with_canonical': 0,
                'pages_with_robots_meta': 0,
                'pages_with_og_tags': 0,
                'pages_with_twitter_tags': 0,
                'pages_with_schema': 0,
                'issues': []
            }
            for result in analysis_results:
                if result.get('title'):
                    aggregated['pages_with_titles'] += 1
                if result.get('meta_description'):
                    aggregated['pages_with_descriptions'] += 1
                if result.get('meta_keywords'):
                    aggregated['pages_with_keywords'] += 1
                if result.get('canonical_url'):
                    aggregated['pages_with_canonical'] += 1
                if result.get('robots_meta'):
                    aggregated['pages_with_robots_meta'] += 1
                if result.get('og_tags'):
                    aggregated['pages_with_og_tags'] += 1
                if result.get('twitter_tags'):
                    aggregated['pages_with_twitter_tags'] += 1
                if result.get('schema_markup'):
                    aggregated['pages_with_schema'] += 1
                h1s = result.get('h1_tags', [])
                aggregated['total_h1_tags'] += len(h1s)
                if len(h1s) > 0:
                    aggregated['images_with_alt'] += 1  # count pages with at least one h1
                aggregated['total_h2_tags'] += len(result.get('h2_tags', []))
                images_without_alt = result.get('images_without_alt', [])
                aggregated['images_without_alt_count'] += len(images_without_alt)
            # Calculate percentages
            total_pages = aggregated['total_pages_analyzed']
            meta_titles = int((aggregated['pages_with_titles'] / total_pages) * 100) if total_pages > 0 else 0
            meta_descriptions = int((aggregated['pages_with_descriptions'] / total_pages) * 100) if total_pages > 0 else 0
            h1_tags = int((aggregated['images_with_alt'] / total_pages) * 100) if total_pages > 0 else 0
            total_images = aggregated['images_with_alt'] + aggregated['images_without_alt_count']
            image_alt_text = int((aggregated['images_with_alt'] / total_images) * 100) if total_images > 0 else 0
            # Add dashboard fields
            aggregated['meta_titles'] = meta_titles
            aggregated['meta_descriptions'] = meta_descriptions
            aggregated['image_alt_text'] = image_alt_text
            aggregated['h1_tags'] = h1_tags
            print(f"[DEBUG] Final aggregated metrics: {aggregated}")
            return aggregated
        except Exception as e:
            print(f"[DEBUG] Exception in _aggregate_results: {e}")
            return {}
    
    def _generate_insights(self, titles_opt: int, titles_total: int,
                          descs_opt: int, descs_total: int,
                          alts_opt: int, alts_total: int,
                          h1_opt: int, h1_total: int) -> List[str]:
        """Generate insights based on analysis results."""
        insights = []
        
        # Title insights
        title_rate = (titles_opt / titles_total) * 100 if titles_total > 0 else 0
        if title_rate < 70:
            insights.append(f"Only {titles_opt} out of {titles_total} pages have optimized meta titles. Consider improving title length and uniqueness.")
        elif title_rate >= 90:
            insights.append(f"Excellent! {titles_opt} out of {titles_total} pages have well-optimized meta titles.")
        
        # Description insights
        desc_rate = (descs_opt / descs_total) * 100 if descs_total > 0 else 0
        if desc_rate < 70:
            insights.append(f"Meta descriptions need improvement on {descs_total - descs_opt} pages. Aim for 120-160 characters.")
        elif desc_rate >= 90:
            insights.append(f"Great work! {descs_opt} out of {descs_total} pages have optimized meta descriptions.")
        
        # Image alt text insights
        if alts_total > 0:
            alt_rate = (alts_opt / alts_total) * 100
            if alt_rate < 80:
                insights.append(f"Image accessibility needs attention: {alts_total - alts_opt} out of {alts_total} images are missing alt text.")
            elif alt_rate >= 95:
                insights.append(f"Excellent image accessibility! {alts_opt} out of {alts_total} images have alt text.")
        
        # H1 insights
        h1_rate = (h1_opt / h1_total) * 100 if h1_total > 0 else 0
        if h1_rate < 80:
            insights.append(f"H1 tag structure needs improvement on {h1_total - h1_opt} pages. Each page should have exactly one H1 tag.")
        elif h1_rate >= 95:
            insights.append(f"Perfect H1 structure! {h1_opt} out of {h1_total} pages have properly optimized H1 tags.")
        
        if not insights:
            insights.append("Overall metadata optimization looks good. Continue monitoring for new content.")
        
        return insights 

    def _extract_title(self, content: str) -> str:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        title_tag = soup.find('title')
        return title_tag.get_text().strip() if title_tag else ''

    def _extract_meta_description(self, content: str) -> str:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        desc_tag = soup.find('meta', attrs={'name': 'description'})
        return desc_tag['content'].strip() if desc_tag and desc_tag.has_attr('content') else ''

    def _extract_meta_keywords(self, content: str) -> str:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        kw_tag = soup.find('meta', attrs={'name': 'keywords'})
        return kw_tag['content'].strip() if kw_tag and kw_tag.has_attr('content') else ''

    def _extract_h1_tags(self, content: str) -> list:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        return [h1.get_text().strip() for h1 in soup.find_all('h1')]

    def _extract_h2_tags(self, content: str) -> list:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        return [h2.get_text().strip() for h2 in soup.find_all('h2')]

    def _find_images_without_alt(self, content: str) -> list:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        return [img['src'] for img in soup.find_all('img') if not img.has_attr('alt') or not img['alt'].strip()]

    def _extract_canonical_url(self, content: str) -> str:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        link_tag = soup.find('link', rel='canonical')
        return link_tag['href'].strip() if link_tag and link_tag.has_attr('href') else ''

    def _extract_robots_meta(self, content: str) -> str:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        robots_tag = soup.find('meta', attrs={'name': 'robots'})
        return robots_tag['content'].strip() if robots_tag and robots_tag.has_attr('content') else ''

    def _extract_og_tags(self, content: str) -> dict:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        og_tags = {}
        for tag in soup.find_all('meta'):
            if tag.has_attr('property') and tag['property'].startswith('og:'):
                og_tags[tag['property']] = tag['content'] if tag.has_attr('content  ') else ''
        return og_tags

    def _extract_twitter_tags(self, content: str) -> dict:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        twitter_tags = {}
        for tag in soup.find_all('meta'):
            if tag.has_attr('name') and tag['name'].startswith('twitter:'):
                twitter_tags[tag['name']] = tag['content'] if tag.has_attr('content') else ''
        return twitter_tags

    def _extract_schema_markup(self, content: str) -> list:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        scripts = soup.find_all('script', type='application/ld+json')
        return [script.string for script in scripts if script.string] 