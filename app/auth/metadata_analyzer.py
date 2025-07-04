import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from typing import Dict, List, Optional, Tuple
import time

class MetadataAnalyzer:
    """Analyzes website metadata, images, and SEO elements."""
    
    def __init__(self):
        self.max_pages = 10  # Limit analysis to first 10 pages
        self.timeout = 30  # 30 second timeout per request
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        
    async def analyze_website(self, website_url: str) -> Optional[Dict]:
        """Analyze a website's metadata and SEO elements."""
        try:
            print(f"[METADATA] Starting analysis for: {website_url}")
            
            # Clean and normalize the URL
            base_url = self._normalize_url(website_url)
            if not base_url:
                print(f"[METADATA] Invalid URL: {website_url}")
                return None
            
            # Get list of pages to analyze
            pages_to_analyze = await self._discover_pages(base_url)
            print(f"[METADATA] Found {len(pages_to_analyze)} pages to analyze")
            
            if not pages_to_analyze:
                print(f"[METADATA] No pages found to analyze")
                return None
            
            # Analyze each page
            analysis_results = []
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={'User-Agent': self.user_agent}
            ) as session:
                
                for i, page_url in enumerate(pages_to_analyze[:self.max_pages]):
                    print(f"[METADATA] Analyzing page {i+1}/{min(len(pages_to_analyze), self.max_pages)}: {page_url}")
                    
                    page_analysis = await self._analyze_page(session, page_url)
                    if page_analysis:
                        analysis_results.append(page_analysis)
                    
                    # Small delay to be respectful
                    await asyncio.sleep(0.5)
            
            # Aggregate results
            if not analysis_results:
                print(f"[METADATA] No successful page analyses")
                return None
                
            aggregated_results = self._aggregate_results(analysis_results)
            
            # Print comprehensive image summary
            self._print_website_image_summary(analysis_results, aggregated_results)
            
            print(f"[METADATA] Analysis complete: {aggregated_results}")
            
            return aggregated_results
            
        except Exception as e:
            print(f"[METADATA] Error analyzing website {website_url}: {e}")
            return None
    
    def _normalize_url(self, url: str) -> Optional[str]:
        """Normalize and validate URL."""
        try:
            # Handle GSC property formats
            if url.startswith('sc-domain:'):
                # Convert sc-domain:example.com to https://example.com
                domain = url.replace('sc-domain:', '')
                url = f"https://{domain}"
            elif not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            # Parse and validate
            parsed = urlparse(url)
            if not parsed.netloc:
                return None
                
            return f"{parsed.scheme}://{parsed.netloc}"
            
        except Exception as e:
            print(f"[METADATA] Error normalizing URL {url}: {e}")
            return None
    
    async def _discover_pages(self, base_url: str) -> List[str]:
        """Discover pages on the website to analyze."""
        try:
            pages = [base_url]  # Always include homepage
            
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={'User-Agent': self.user_agent}
            ) as session:
                
                # Try to get sitemap first
                sitemap_pages = await self._get_sitemap_pages(session, base_url)
                if sitemap_pages:
                    pages.extend(sitemap_pages[:self.max_pages-1])  # Reserve 1 slot for homepage
                    return list(set(pages))  # Remove duplicates
                
                # Fallback: crawl homepage for internal links
                homepage_links = await self._get_homepage_links(session, base_url)
                if homepage_links:
                    pages.extend(homepage_links[:self.max_pages-1])
                
                return list(set(pages))  # Remove duplicates
                
        except Exception as e:
            print(f"[METADATA] Error discovering pages: {e}")
            return [base_url]  # Return at least the homepage
    
    async def _get_sitemap_pages(self, session: aiohttp.ClientSession, base_url: str) -> List[str]:
        """Try to get pages from sitemap.xml."""
        try:
            sitemap_urls = [
                f"{base_url}/sitemap.xml",
                f"{base_url}/sitemap_index.xml",
                f"{base_url}/robots.txt"  # Check robots.txt for sitemap
            ]
            
            for sitemap_url in sitemap_urls:
                try:
                    async with session.get(sitemap_url) as response:
                        if response.status == 200:
                            content = await response.text()
                            
                            if sitemap_url.endswith('robots.txt'):
                                # Extract sitemap URLs from robots.txt
                                sitemap_matches = re.findall(r'Sitemap:\s*(.+)', content, re.IGNORECASE)
                                for sitemap_match in sitemap_matches:
                                    sitemap_match = sitemap_match.strip()
                                    async with session.get(sitemap_match) as sitemap_response:
                                        if sitemap_response.status == 200:
                                            sitemap_content = await sitemap_response.text()
                                            return self._parse_sitemap(sitemap_content)
                            else:
                                return self._parse_sitemap(content)
                                
                except Exception as e:
                    print(f"[METADATA] Error fetching {sitemap_url}: {e}")
                    continue
            
            return []
            
        except Exception as e:
            print(f"[METADATA] Error getting sitemap pages: {e}")
            return []
    
    def _parse_sitemap(self, sitemap_content: str) -> List[str]:
        """Parse sitemap XML content."""
        try:
            # Simple regex approach for XML parsing
            url_matches = re.findall(r'<loc>(.*?)</loc>', sitemap_content)
            return [url.strip() for url in url_matches if url.strip()]
        except Exception as e:
            print(f"[METADATA] Error parsing sitemap: {e}")
            return []
    
    async def _get_homepage_links(self, session: aiohttp.ClientSession, base_url: str) -> List[str]:
        """Get internal links from homepage."""
        try:
            async with session.get(base_url) as response:
                if response.status != 200:
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                links = []
                domain = urlparse(base_url).netloc
                
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    
                    # Convert relative URLs to absolute
                    full_url = urljoin(base_url, href)
                    
                    # Only include internal links
                    if urlparse(full_url).netloc == domain:
                        links.append(full_url)
                
                return links[:self.max_pages]
                
        except Exception as e:
            print(f"[METADATA] Error getting homepage links: {e}")
            return []
    
    async def _analyze_page(self, session: aiohttp.ClientSession, page_url: str) -> Optional[Dict]:
        """Analyze a single page for metadata and SEO elements."""
        try:
            async with session.get(page_url) as response:
                if response.status != 200:
                    print(f"[METADATA] Failed to fetch {page_url}: {response.status}")
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Analyze meta title
                title_tag = soup.find('title')
                title_text = title_tag.get_text().strip() if title_tag else ""
                title_optimized = self._is_title_optimized(title_text)
                
                # Analyze meta description
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                desc_text = meta_desc.get('content', '').strip() if meta_desc else ""
                desc_optimized = self._is_description_optimized(desc_text)
                
                # Analyze H1 tags
                h1_tags = soup.find_all('h1')
                h1_optimized = self._are_h1_tags_optimized(h1_tags)
                
                # Analyze images with detailed console output 
                images = soup.find_all('img')
                images_with_alt = [img for img in images if img.get('alt', '').strip()]
                
                # Highlight image tags in terminal
                self._highlight_image_tags(page_url, images)
                
                return {
                    'url': page_url,
                    'title': title_text,
                    'title_optimized': title_optimized,
                    'meta_description': desc_text,
                    'description_optimized': desc_optimized,
                    'h1_count': len(h1_tags),
                    'h1_optimized': h1_optimized,
                    'total_images': len(images),
                    'images_with_alt': len(images_with_alt),
                    'images_optimized': len(images_with_alt) == len(images) if images else True
                }
                
        except Exception as e:
            print(f"[METADATA] Error analyzing page {page_url}: {e}")
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
    
    def _highlight_image_tags(self, page_url: str, images: List) -> None:
        """Highlight and display image tags found on the page."""
        try:
            print(f"\n{'='*80}")
            print(f"🖼️  IMAGE ANALYSIS FOR: {page_url}")
            print(f"{'='*80}")
            
            if not images:
                print("❌ No <img> tags found on this page")
                print(f"{'='*80}\n")
                return
            
            print(f"📊 Found {len(images)} image(s) on this page:")
            print("-" * 80)
            
            for i, img in enumerate(images, 1):
                # Extract image attributes
                src = img.get('src', '')
                alt = img.get('alt', '')
                title = img.get('title', '')
                width = img.get('width', '')
                height = img.get('height', '')
                loading = img.get('loading', '')
                
                # Color coding for terminal output
                status_icon = "✅" if alt.strip() else "❌"
                alt_status = "HAS ALT TEXT" if alt.strip() else "MISSING ALT TEXT"
                
                print(f"\n🏷️  IMAGE #{i} - {status_icon} {alt_status}")
                print(f"   📂 Source: {src[:100]}{'...' if len(src) > 100 else ''}")
                
                if alt.strip():
                    print(f"   ✨ Alt Text: \"{alt}\"")
                else:
                    print(f"   ⚠️  Alt Text: [EMPTY - NEEDS ATTENTION]")
                
                if title.strip():
                    print(f"   🏷️  Title: \"{title}\"")
                
                # Additional attributes
                attrs = []
                if width: attrs.append(f"width={width}")
                if height: attrs.append(f"height={height}")
                if loading: attrs.append(f"loading={loading}")
                
                if attrs:
                    print(f"   📐 Attributes: {', '.join(attrs)}")
                
                # Show the actual HTML tag (truncated for readability)
                img_html = str(img)
                if len(img_html) > 200:
                    img_html = img_html[:200] + "..."
                print(f"   🔍 HTML: {img_html}")
                
                print("-" * 80)
            
            # Summary statistics
            images_with_alt = len([img for img in images if img.get('alt', '').strip()])
            images_without_alt = len(images) - images_with_alt
            alt_percentage = (images_with_alt / len(images)) * 100 if images else 0
            
            print(f"\n📈 SUMMARY FOR THIS PAGE:")
            print(f"   • Total Images: {len(images)}")
            print(f"   • With Alt Text: {images_with_alt} ✅")
            print(f"   • Without Alt Text: {images_without_alt} ❌")
            print(f"   • Alt Text Coverage: {alt_percentage:.1f}%")
            
            if alt_percentage < 100:
                print(f"   ⚠️  RECOMMENDATION: Add alt text to {images_without_alt} image(s) for better accessibility")
            else:
                print(f"   🎉 EXCELLENT: All images have alt text!")
            
            print(f"{'='*80}\n")
            
        except Exception as e:
            print(f"[METADATA] Error highlighting image tags: {e}")
    
    def _print_website_image_summary(self, analysis_results: List[Dict], aggregated_results: Dict) -> None:
        """Print a comprehensive summary of all images found across the website."""
        try:
            print(f"\n{'🌐'*40}")
            print(f"🖼️  WEBSITE-WIDE IMAGE ANALYSIS SUMMARY")
            print(f"{'🌐'*40}")
            
            total_pages = len(analysis_results)
            total_images = aggregated_results.get('image_alt_text_total', 0)
            images_with_alt = aggregated_results.get('image_alt_text_optimized', 0)
            images_without_alt = total_images - images_with_alt
            
            print(f"📊 OVERALL STATISTICS:")
            print(f"   • Pages Analyzed: {total_pages}")
            print(f"   • Total Images Found: {total_images}")
            print(f"   • Images with Alt Text: {images_with_alt} ✅")
            print(f"   • Images without Alt Text: {images_without_alt} ❌")
            
            if total_images > 0:
                coverage_percentage = (images_with_alt / total_images) * 100
                print(f"   • Alt Text Coverage: {coverage_percentage:.1f}%")
                
                # Performance rating
                if coverage_percentage >= 95:
                    rating = "🏆 EXCELLENT"
                    color = "✅"
                elif coverage_percentage >= 80:
                    rating = "👍 GOOD"
                    color = "🟡"
                elif coverage_percentage >= 60:
                    rating = "⚠️ NEEDS IMPROVEMENT"
                    color = "🟠"
                else:
                    rating = "❌ POOR"
                    color = "🔴"
                
                print(f"   • Accessibility Rating: {color} {rating}")
            else:
                print(f"   • Alt Text Coverage: N/A (No images found)")
            
            print(f"\n📋 PAGE-BY-PAGE BREAKDOWN:")
            print("-" * 80)
            
            for i, result in enumerate(analysis_results, 1):
                page_images = result.get('total_images', 0)
                page_with_alt = result.get('images_with_alt', 0)
                page_without_alt = page_images - page_with_alt
                page_url = result.get('url', 'Unknown')
                
                # Truncate URL for display
                display_url = page_url if len(page_url) <= 60 else page_url[:57] + "..."
                
                status_icon = "✅" if page_without_alt == 0 and page_images > 0 else "❌" if page_without_alt > 0 else "➖"
                
                print(f"{i:2d}. {status_icon} {display_url}")
                print(f"     Images: {page_images} total, {page_with_alt} with alt, {page_without_alt} missing alt")
            
            print("-" * 80)
            
            if images_without_alt > 0:
                print(f"\n🔧 RECOMMENDATIONS:")
                print(f"   • Add alt text to {images_without_alt} images across {total_pages} pages")
                print(f"   • Focus on decorative images: use alt=\"\" for purely decorative images")
                print(f"   • Descriptive alt text: describe the image content and context")
                print(f"   • Keep alt text concise: aim for 125 characters or less")
                print(f"   • Avoid redundant phrases: don't start with 'image of' or 'picture of'")
            else:
                print(f"\n🎉 CONGRATULATIONS!")
                print(f"   • All {total_images} images across your website have alt text!")
                print(f"   • Your website meets accessibility standards for images")
                print(f"   • Continue this excellent practice for any new images you add")
            
            print(f"\n{'🌐'*40}\n")
            
        except Exception as e:
            print(f"[METADATA] Error printing website image summary: {e}")
    
    def _aggregate_results(self, results: List[Dict]) -> Dict:
        """Aggregate analysis results from multiple pages."""
        try:
            total_pages = len(results)
            
            # Count optimized elements
            titles_optimized = sum(1 for r in results if r['title_optimized'])
            descriptions_optimized = sum(1 for r in results if r['description_optimized'])
            h1_optimized = sum(1 for r in results if r['h1_optimized'])
            
            # Count images
            total_images = sum(r['total_images'] for r in results)
            images_with_alt = sum(r['images_with_alt'] for r in results)
            
            # Calculate percentages for SEO score
            title_percentage = round((titles_optimized / total_pages) * 100) if total_pages > 0 else 0
            desc_percentage = round((descriptions_optimized / total_pages) * 100) if total_pages > 0 else 0
            h1_percentage = round((h1_optimized / total_pages) * 100) if total_pages > 0 else 0
            alt_percentage = round((images_with_alt / total_images) * 100) if total_images > 0 else 100
            
            # Generate insights
            insights = self._generate_insights(
                titles_optimized, total_pages,
                descriptions_optimized, total_pages,
                images_with_alt, total_images,
                h1_optimized, total_pages
            )
            
            return {
                # Counts for display
                "meta_titles_optimized": titles_optimized,
                "meta_titles_total": total_pages,
                "meta_descriptions_optimized": descriptions_optimized,
                "meta_descriptions_total": total_pages,
                "image_alt_text_optimized": images_with_alt,
                "image_alt_text_total": total_images,
                "h1_tags_optimized": h1_optimized,
                "h1_tags_total": total_pages,
                
                # Percentages for SEO score calculation
                "meta_titles": title_percentage,
                "meta_descriptions": desc_percentage,
                "image_alt_text": alt_percentage,
                "h1_tags": h1_percentage,
                
                "insights": insights,
                "pages_analyzed": total_pages
            }
            
        except Exception as e:
            print(f"[METADATA] Error aggregating results: {e}")
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