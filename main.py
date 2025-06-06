import os
import sys
from datetime import datetime, timedelta
import pandas as pd
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from pyairtable import Api
import pickle
from urllib.parse import urlparse, quote
import requests
import json
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# If modifying these scopes, delete the token.pickle file.
SCOPES = [
    'https://www.googleapis.com/auth/webmasters.readonly',
    'https://www.googleapis.com/auth/webmasters'
]





def get_gsc_credentials():
    """Gets valid credentials for Google Search Console API."""
    credentials = None
    
    if os.path.exists('config/token.pickle'):
        with open('config/token.pickle', 'rb') as token:
            credentials = pickle.load(token)
    
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError(
                    "credentials.json file not found. Please download it from Google Cloud Console."
                )
            
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', 
                SCOPES,
                redirect_uri='http://localhost:8085/'
            )
            credentials = flow.run_local_server(
                port=8085,
                success_message='Authentication successful! You may close this window.',
                open_browser=True
            )
        
        with open('config/token.pickle', 'wb') as token:
            pickle.dump(credentials, token)
    
    return credentials





def get_airtable_records():
    """Fetch records from Airtable."""
    try:
        api_key = os.getenv('AIRTABLE_API_KEY')
        base_id = os.getenv('AIRTABLE_BASE_ID')
        table_name = os.getenv('AIRTABLE_TABLE_NAME')
        
        # If any keys are missing, raise an error
        if not all([api_key, base_id, table_name]):
            raise ValueError("Missing required Airtable configuration")
            
        airtable = Api(api_key)
        # Get the table
        table = airtable.table(base_id, table_name)
        
        # Test the connection by getting records
        records = table.all()
        print(f"Successfully connected to Airtable table '{table_name}'")
        
        return table, records
        
    except Exception as e:
        print("\nError connecting to Airtable:")
        print(f"Base ID: {base_id}")
        print(f"Table name: {table_name}")
        print(f"Error details: {str(e)}")
        raise





def get_site_info(service, url):
    """
    Get site information and determine if it's a domain property or URL prefix.
    First checks as URL prefix for verification, then uses domain property if applicable.
    Returns tuple of (site_url, is_domain_property, original_property_type)
    """
    try:
        # List all sites to check property type
        sites = service.sites().list().execute()
        
        # Extract domain and create URL prefix version
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        url_prefix = f"https://{parsed.netloc}/"  # Force https for checking
        domain_property = f"sc-domain:{domain}"
        
        # First, find the original property type
        original_is_domain = False
        for site in sites.get('siteEntry', []):
            site_url = site.get('siteUrl', '')
            if site_url == domain_property:
                original_is_domain = True
                print(f"\tFound original domain property: {domain_property}")
                break
            elif site_url.startswith('http') and domain in site_url:
                print(f"\tFound original URL prefix property: {site_url}")
                break
        
        # For verification, always return URL prefix version first
        print(f"\tChecking URL prefix version: {url_prefix}")
        return url_prefix, False, original_is_domain
        
    except Exception as e:
        print(f"Error checking site type: {str(e)}")
        return url_prefix, False, False





def get_gsc_metrics(service, url, days=30):
    """
    Fetch metrics from Google Search Console for a specific URL.
    
    Args:
        service: GSC service instance
        url: URL to get metrics for
        days: Number of days to look back
    
    Returns:
        Dictionary containing metrics
    """
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    try:
        # First try with URL prefix format for verification
        site_url, is_domain_property, original_is_domain = get_site_info(service, url)
        print(f"\tVerifying access using URL prefix: {site_url}")
        
        # For initial verification, always use path for URL prefix
        parsed = urlparse(url)
        page_url = parsed.path + ('?' + parsed.query if parsed.query else '')
        if not page_url:
            page_url = '/'
            
        # Prepare request for verification
        request = {
            'startDate': start_date.isoformat(),
            'endDate': end_date.isoformat(),
            'dimensions': ['page'],
            'dimensionFilterGroups': [{
                'filters': [{
                    'dimension': 'page',
                    'operator': 'equals',
                    'expression': page_url
                }]
            }]
        }
        
        # Try URL prefix version first
        encoded_site_url = quote(site_url, safe=':/')
        try:
            print(f"\tVerifying access to: {site_url}")
            response = service.searchanalytics().query(
                siteUrl=encoded_site_url,
                body=request
            ).execute()
            print("Successfully verified URL access")
            
            # If original was domain property, switch back for actual data fetch
            if original_is_domain:
                print("\tSwitching back to domain property for data fetch...")
                domain = parsed.netloc.replace('www.', '')
                site_url = f"sc-domain:{domain}"
                encoded_site_url = quote(site_url, safe=':/')
                page_url = url  # Use full URL for domain property
                
                # Update request with full URL for domain property
                request['dimensionFilterGroups'][0]['filters'][0]['expression'] = page_url
                
                print(f"\tFetching data using domain property: {site_url}")
                response = service.searchanalytics().query(
                    siteUrl=encoded_site_url,
                    body=request
                ).execute()
            
        except Exception as e:
            # print(f"Error during verification: {str(e)}")
            if original_is_domain:
                print("\tFalling back to domain property due to insufficient permissions on URL prefix property")
                domain = parsed.netloc.replace('www.', '')
                site_url = f"sc-domain:{domain}"
                encoded_site_url = quote(site_url, safe=':/')
                # Update request with full URL for domain property
                request['dimensionFilterGroups'][0]['filters'][0]['expression'] = url
                try:
                    response = service.searchanalytics().query(
                        siteUrl=encoded_site_url,
                        body=request
                    ).execute()
                except Exception as e2:
                    print(f"Error fetching domain property data: {str(e2)}")
                    return {
                        'impressions': 0,
                        'clicks': 0,
                        'ctr': 0,
                        'average_position': 0
                    }
            else:
                return {
                    'impressions': 0,
                    'clicks': 0,
                    'ctr': 0,
                    'average_position': 0
                }
        
        if not response.get('rows'):
            print(f"\tNo data found for URL: {url}")
            return {
                'impressions': 0,
                'clicks': 0,
                'ctr': 0,
                'average_position': 0
            }
        
        row = response['rows'][0]
        metrics = {
            'impressions': int(row['impressions']),
            'clicks': int(row['clicks']),
            'ctr': round(row['ctr'] * 100, 2),
            'average_position': round(row['position'], 2)
        }
        print(f"\tRetrieved metrics for {url}: {metrics}")
        return metrics
        
    except Exception as e:
        error_message = str(e)
        print(f"\tError querying GSC for {url}: {error_message}")
        return {
            'impressions': 0,
            'clicks': 0,
            'ctr': 0,
            'average_position': 0
        }





def check_gsc_access(service):
    """Check GSC access and list available sites."""
    try:
        print("\nChecking Google Search Console access...")
        # Get list of sites user has access to
        sites = service.sites().list().execute()
        
        if not sites.get('siteEntry', []):
            print("No sites found in your Google Search Console account.")
            return []
        
        print("\nYou have access to these sites in GSC:")
        available_sites = []
        for site in sites['siteEntry']:
            permission_level = site.get('permissionLevel', 'Unknown')
            site_url = site.get('siteUrl', 'Unknown URL')
            available_sites.append(site_url)
            print(f"- {site_url} (Permission: {permission_level})")
            
        return available_sites
            
    except Exception as e:
        print(f"Error checking GSC access: {str(e)}")
        return []





def get_psi_metrics(url, strategy="mobile"):
    """Fetch PageSpeed Insights metrics for a given URL."""
    api_key = os.getenv("PSI_API_KEY")
    if not api_key:
        print("PSI_API_KEY env var not set; returning zeroed PSI metrics")
        return {
            "performance_score": 0,
            "first_contentful_paint": 0,
            "largest_contentful_paint": 0,
            "speed_index": 0,
            "time_to_interactive": 0,
            "total_blocking_time": 0,
            "cumulative_layout_shift": 0
        }
    endpoint = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    params = {"url": url, "strategy": strategy, "key": api_key}
    try:
        r = requests.get(endpoint, params=params)
        r.raise_for_status()
        data = r.json()
        lh = data.get("lighthouseResult", {})
        audits = lh.get("audits", {})
        perf_cat = lh.get("categories", {}).get("performance", {})
        return {
            "performance_score": round(perf_cat.get("score", 0) * 100, 2),
            "first_contentful_paint": round(audits.get("first-contentful-paint", {}).get("numericValue", 0) / 1000, 2),
            "largest_contentful_paint": round(audits.get("largest-contentful-paint", {}).get("numericValue", 0) / 1000, 2),
            "speed_index": round(audits.get("speed-index", {}).get("numericValue", 0) / 1000, 2),
            "time_to_interactive": round(audits.get("interactive", {}).get("numericValue", 0) / 1000, 2),
            "total_blocking_time": round(audits.get("total-blocking-time", {}).get("numericValue", 0), 2),
            "cumulative_layout_shift": round(audits.get("cumulative-layout-shift", {}).get("numericValue", 0), 2)
        }
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error fetching PSI metrics for {url}: {http_err}")
        try:
            print(f"Response body: {r.text}")
        except Exception:
            pass
        return {
            "performance_score": 0,
            "first_contentful_paint": 0,
            "largest_contentful_paint": 0,
            "speed_index": 0,
            "time_to_interactive": 0,
            "total_blocking_time": 0,
            "cumulative_layout_shift": 0
        }
    except Exception as e:
        print(f"Error fetching PSI metrics for {url}: {e}")
        return {
            "performance_score": 0,
            "first_contentful_paint": 0,
            "largest_contentful_paint": 0,
            "speed_index": 0,
            "time_to_interactive": 0,
            "total_blocking_time": 0,
            "cumulative_layout_shift": 0
        }





def get_sitemaps_status(service, url):
    """Fetch sitemap submission status and details for SEO audit reporting."""
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    url_prefix = f"https://{parsed.netloc}/"
    domain_property = f"sc-domain:{domain}"
    
    try:
        sites = service.sites().list().execute().get("siteEntry", [])
        original_is_domain = any(site.get("siteUrl") == domain_property for site in sites)
    except Exception:
        original_is_domain = False
    
    site_property = domain_property if original_is_domain else url_prefix
    
    try:
        print(f"Fetching sitemap submission data for {site_property}...")
        resp = service.sitemaps().list(siteUrl=site_property).execute()
        entries = resp.get("sitemap", [])
        
        if not entries:
            return {
                "sitemaps_submitted": "No sitemaps found",
                "sitemap_count": 0,
                "sitemap_errors": "N/A",
                "sitemap_warnings": "N/A",
                "last_submission": "N/A"
            }
        
        sitemap_details = []
        total_errors = 0
        total_warnings = 0
        latest_submission = ""
        
        for entry in entries:
            path = entry.get("path", "Unknown")
            last_submitted = entry.get("lastSubmitted", "Never")
            is_pending = entry.get("isPending", False)
            errors = int(entry.get("errors", 0))
            warnings = int(entry.get("warnings", 0))
            
            total_errors += errors
            total_warnings += warnings
            
            # Track latest submission
            if last_submitted != "Never" and (not latest_submission or last_submitted > latest_submission):
                latest_submission = last_submitted
            
            status = "Pending" if is_pending else "Processed"
            sitemap_details.append(f"{path} ({status}, E:{errors}, W:{warnings})")
        
        return {
            "sitemaps_submitted": "; ".join(sitemap_details),
            "sitemap_count": len(entries),
            "sitemap_errors": total_errors,
            "sitemap_warnings": total_warnings,
            "last_submission": latest_submission or "Never"
        }
        
    except Exception as e:
        print(f"\tError fetching sitemaps for {url}: {e}")
        return {
            "sitemaps_submitted": "Error fetching data",
            "sitemap_count": 0,
            "sitemap_errors": -1,
            "sitemap_warnings": -1, 
            "last_submission": ""
        }





def get_mobile_usability_from_psi(url):
    """Extract mobile usability data from PageSpeed Insights API."""
    print(f"\nChecking mobile usability via PageSpeed Insights for {url}...")
    
    api_key = os.getenv("PSI_API_KEY")
    if not api_key:
        print("\tPSI_API_KEY not set; skipping mobile usability check")
        return {
            "mobile_friendly_status": "NO_API_KEY",
            "mobile_friendly_issues_count": 0,
            "mobile_friendly_issues": "PSI API key not configured",
            "mobile_test_loading_state": "SKIPPED",
            "mobile_passed": "Unknown"
        }
    
    try:
        endpoint = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
        params = {
            "url": url, 
            "strategy": "mobile",
            "key": api_key,
            "category": "accessibility"  # This includes mobile usability
        }
        
        print(f"\tCalling PageSpeed Insights API for mobile analysis...")
        
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Extract mobile-friendly information from lighthouse result
        lighthouse = data.get("lighthouseResult", {})
        audits = lighthouse.get("audits", {})
        
        # Check key mobile usability audits
        viewport_audit = audits.get("viewport", {})
        tap_targets = audits.get("tap-targets", {})
        font_size = audits.get("font-size", {})
        
        mobile_issues = []
        
        # Check viewport configuration
        if viewport_audit.get("score") == 0:
            mobile_issues.append("VIEWPORT_NOT_CONFIGURED: " + viewport_audit.get("title", ""))
            
        # Check tap targets
        if tap_targets.get("score") == 0:
            mobile_issues.append("TAP_TARGETS_TOO_CLOSE: " + tap_targets.get("title", ""))
            
        # Check font size
        if font_size.get("score") == 0:
            mobile_issues.append("FONT_SIZE_TOO_SMALL: " + font_size.get("title", ""))
        
        # Determine overall mobile friendliness
        if len(mobile_issues) == 0:
            mobile_status = "MOBILE_FRIENDLY"
            mobile_passed = "Yes"
        else:
            mobile_status = "NOT_MOBILE_FRIENDLY" 
            mobile_passed = "No"
        
        print(f"\t✓ Mobile usability check completed: {mobile_status}")
        
        # Format for Airtable field types
        issues_text = "; ".join(mobile_issues) if mobile_issues else ""
        
        return {
            "mobile_friendly_status": mobile_status,
            "mobile_friendly_issues_count": len(mobile_issues),
            "mobile_friendly_issues": issues_text,
            "mobile_test_loading_state": "COMPLETE",
            "mobile_passed": mobile_passed
        }
        
    except Exception as e:
        print(f"\t✗ Error checking mobile usability for {url}: {e}")
        return {
            "mobile_friendly_status": "ERROR",
            "mobile_friendly_issues_count": -1,
            "mobile_friendly_issues": f"Exception: {str(e)}",
            "mobile_test_loading_state": "ERROR",
            "mobile_passed": "Unknown"
        }





def get_keyword_performance(service, url, days=90):
    """Get top performing keywords for a URL from GSC."""
    print(f"\nAnalyzing keyword performance for {url}...")
    
    # Get site property (domain vs URL prefix)
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    url_prefix = f"https://{parsed.netloc}/"
    domain_property = f"sc-domain:{domain}"
    
    try:
        sites = service.sites().list().execute().get("siteEntry", [])
        original_is_domain = any(site.get("siteUrl") == domain_property for site in sites)
    except Exception:
        original_is_domain = False
    
    site_property = domain_property if original_is_domain else url_prefix
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    try:
        print(f"\tFetching keyword data from GSC...")
        
        # Request top keywords for this specific URL
        request = {
            'startDate': start_date.isoformat(),
            'endDate': end_date.isoformat(),
            'dimensions': ['query'],
            'rowLimit': 50,  # Top 50 keywords
            'dimensionFilterGroups': [{
                'filters': [{
                    'dimension': 'page',
                    'operator': 'equals',
                    'expression': url if original_is_domain else parsed.path or '/'
                }]
            }]
        }
        
        encoded_site_url = quote(site_property, safe=':/')
        response = service.searchanalytics().query(
            siteUrl=encoded_site_url,
            body=request
        ).execute()
        
        keywords_data = []
        
        if response.get('rows'):
            print(f"\tFound {len(response['rows'])} keywords")
            
            for row in response['rows']:
                keyword = row['keys'][0]
                
                # Classify keyword intent
                intent = classify_keyword_intent(keyword)
                
                # Calculate opportunity score
                opportunity_score = calculate_opportunity_score({
                    'position': row['position'],
                    'impressions': row['impressions'],
                    'clicks': row['clicks'],
                    'ctr': row['ctr']
                })
                
                keyword_data = {
                    'keyword_text': keyword,
                    'current_position': round(row['position'], 2),
                    'monthly_impressions': int(row['impressions']),
                    'monthly_clicks': int(row['clicks']),
                    'keyword_ctr': round(row['ctr'] * 100, 2),
                    'intent_type': intent,
                    'opportunity_score': opportunity_score,
                    'traffic_potential': estimate_traffic_potential(row['position'], row['impressions']),
                    'target_priority': get_priority_level(opportunity_score)
                }
                
                keywords_data.append(keyword_data)
        
        # Get top 5 keywords for summary
        top_keywords = sorted(keywords_data, key=lambda x: x['monthly_clicks'], reverse=True)[:5]
        top_keywords_text = "; ".join([kw['keyword_text'] for kw in top_keywords])
        
        print(f"\tTop keywords: {top_keywords_text[:100]}...")
        
        return {
            'top_keywords': top_keywords_text,
            'total_keywords_tracked': len(keywords_data),
            'avg_keyword_position': round(sum([kw['current_position'] for kw in keywords_data]) / len(keywords_data), 2) if keywords_data else 0,
            'high_opportunity_keywords': len([kw for kw in keywords_data if kw['opportunity_score'] >= 7]),
            'branded_keywords_count': len([kw for kw in keywords_data if is_branded_keyword(kw['keyword_text'], domain)]),
            'keyword_cannibalization_risk': detect_cannibalization_risk(keywords_data)
        }
        
    except Exception as e:
        print(f"\tError fetching keyword data for {url}: {e}")
        return {
            'top_keywords': 'Error fetching data',
            'total_keywords_tracked': 0,
            'avg_keyword_position': 0,
            'high_opportunity_keywords': 0,
            'branded_keywords_count': 0,
            'keyword_cannibalization_risk': 'Low'
        }

def classify_keyword_intent(keyword):
    """Classify keyword search intent based on common patterns."""
    keyword_lower = keyword.lower()
    
    # Transactional intent indicators
    transactional_words = ['buy', 'purchase', 'order', 'shop', 'sale', 'deal', 'discount', 'cheap', 'price', 'cost', 'hire', 'book', 'subscribe']
    if any(word in keyword_lower for word in transactional_words):
        return 'Transactional'
    
    # Navigational intent indicators  
    navigational_words = ['login', 'sign in', 'account', 'dashboard', 'contact', 'about', 'careers', 'support']
    if any(word in keyword_lower for word in navigational_words):
        return 'Navigational'
    
    # Commercial intent indicators
    commercial_words = ['best', 'top', 'review', 'compare', 'vs', 'alternative', 'solution', 'service', 'company', 'agency']
    if any(word in keyword_lower for word in commercial_words):
        return 'Commercial'
    
    # Informational (default)
    return 'Informational'

def calculate_opportunity_score(keyword_data):
    """Calculate SEO opportunity score (1-10) based on performance metrics."""
    position = keyword_data['position']
    impressions = keyword_data['impressions']
    clicks = keyword_data['clicks']
    ctr = keyword_data['ctr']
    
    score = 0
    
    # Position scoring (worse position = higher opportunity)
    if position > 10:
        score += 4  # Page 2+ has high improvement potential
    elif position > 3:
        score += 3  # Position 4-10 has good potential  
    elif position > 1:
        score += 2  # Position 2-3 has some potential
    else:
        score += 1  # Position 1 has maintenance value
    
    # Impressions scoring (more impressions = more potential traffic)
    if impressions > 1000:
        score += 3
    elif impressions > 100:
        score += 2
    elif impressions > 10:
        score += 1
    
    # CTR scoring (low CTR for good position = opportunity)
    expected_ctr = get_expected_ctr(position)
    if ctr < expected_ctr * 0.7:  # 30% below expected
        score += 2
    elif ctr < expected_ctr * 0.9:  # 10% below expected  
        score += 1
    
    return min(score, 10)  # Cap at 10

def get_expected_ctr(position):
    """Get expected CTR based on position (industry averages)."""
    ctr_by_position = {
        1: 0.285, 2: 0.152, 3: 0.103, 4: 0.073, 5: 0.053,
        6: 0.040, 7: 0.031, 8: 0.024, 9: 0.019, 10: 0.016
    }
    return ctr_by_position.get(int(position), 0.01)

def estimate_traffic_potential(current_position, current_impressions):
    """Estimate potential monthly traffic if ranking in top 3."""
    if current_position <= 3:
        return int(current_impressions * 0.1)  # Already in top 3
    
    # Estimate impressions increase from ranking higher
    current_ctr = get_expected_ctr(current_position)
    top3_ctr = (get_expected_ctr(1) + get_expected_ctr(2) + get_expected_ctr(3)) / 3
    
    potential_traffic = int(current_impressions * (top3_ctr / current_ctr))
    return min(potential_traffic, current_impressions * 5)  # Cap at 5x current

def get_priority_level(opportunity_score):
    """Convert opportunity score to priority level."""
    if opportunity_score >= 8:
        return 'High'
    elif opportunity_score >= 5:
        return 'Medium'
    else:
        return 'Low'

def is_branded_keyword(keyword, domain):
    """Check if keyword contains brand name."""
    brand_name = domain.split('.')[0]  # Extract main domain
    return brand_name.lower() in keyword.lower()

def detect_cannibalization_risk(keywords_data):
    """Detect potential keyword cannibalization issues."""
    if len(keywords_data) < 2:
        return 'Low'
    
    # Check for very similar keywords with different positions
    similar_keywords = 0
    for i, kw1 in enumerate(keywords_data):
        for kw2 in keywords_data[i+1:]:
            # Simple similarity check (shared words)
            words1 = set(kw1['keyword_text'].lower().split())
            words2 = set(kw2['keyword_text'].lower().split())
            overlap = len(words1.intersection(words2)) / len(words1.union(words2))
            
            if overlap > 0.6 and abs(kw1['current_position'] - kw2['current_position']) > 5:
                similar_keywords += 1
    
    if similar_keywords > 3:
        return 'High'
    elif similar_keywords > 1:
        return 'Medium'
    else:
        return 'Low'

def get_airtable_multi_tables():
    """Initialize connections to all Airtable tables."""
    try:
        api_key = os.getenv('AIRTABLE_API_KEY')
        base_id = os.getenv('AIRTABLE_BASE_ID')
        
        if not all([api_key, base_id]):
            raise ValueError("Missing required Airtable configuration")
            
        airtable = Api(api_key)
        
        # Define all table connections
        tables = {
            'websites': airtable.table(base_id, 'Websites'),
            'core_metrics': airtable.table(base_id, 'Core_Metrics'),
            'performance_metrics': airtable.table(base_id, 'Performance_Metrics'),
            'index_technical': airtable.table(base_id, 'Index_Technical'),
            'sitemap_data': airtable.table(base_id, 'Sitemap_Data'),
            'mobile_usability': airtable.table(base_id, 'Mobile_Usability'),
            'keyword_analysis': airtable.table(base_id, 'Keyword_Analysis'),

        }
        
        # Test connection with main websites table
        websites_records = tables['websites'].all()
        print(f"Successfully connected to Airtable with {len(websites_records)} websites")
        
        # Test all table connections
        for table_name, table_obj in tables.items():
            try:
                table_records = table_obj.all()
                print(f"\t✓ {table_name}: {len(table_records)} records")
            except Exception as e:
                print(f"\t✗ {table_name}: Connection failed - {e}")
        
        return tables, websites_records
        
    except Exception as e:
        print(f"\nError connecting to Airtable multi-table setup: {str(e)}")
        raise

def update_airtable_organized(tables, url, combined_metrics):
    """Update organized Airtable tables with categorized data."""
    try:
        analysis_date = datetime.now().isoformat()
        
        # Find or create website record
        website_record = None
        websites_records = tables['websites'].all()
        print(f"\t\tLooking for {url} in {len(websites_records)} website records")
        
        for record in websites_records:
            record_url = record['fields'].get('url')
            print(f"\t\t  Checking: '{record_url}' vs '{url}'")
            if record_url == url:
                website_record = record
                print(f"\t\t  ✓ Found matching record: {record['id']}")
                break
        
        if not website_record:
            print(f"\t\t✗ Website {url} not found in main table - skipping organized update")
            print(f"\t\t  Available URLs in main table:")
            for record in websites_records:
                print(f"\t\t    - {record['fields'].get('url', 'NO URL FIELD')}")
            return False
        
        website_id = website_record['id']
        print(f"\t\tUsing website ID: {website_id}")
        
        # Prepare data for each table
        table_data = {
            'core_metrics': {
                'url': [website_id],
                'impressions': combined_metrics.get('impressions', 0),
                'clicks': combined_metrics.get('clicks', 0),
                'ctr': combined_metrics.get('ctr', 0),
                'average_position': combined_metrics.get('average_position', 0),
                'analysis_date': analysis_date
            },
            'performance_metrics': {
                'url': [website_id],
                'performance_score': combined_metrics.get('performance_score', 0),
                'first_contentful_paint': combined_metrics.get('first_contentful_paint', 0),
                'largest_contentful_paint': combined_metrics.get('largest_contentful_paint', 0),
                'speed_index': combined_metrics.get('speed_index', 0),
                'time_to_interactive': combined_metrics.get('time_to_interactive', 0),
                'total_blocking_time': combined_metrics.get('total_blocking_time', 0),
                'cumulative_layout_shift': combined_metrics.get('cumulative_layout_shift', 0),
                'analysis_date': analysis_date
            },
            'index_technical': {
                'url': [website_id],
                'index_verdict': combined_metrics.get('index_verdict', ''),
                'coverage_state': combined_metrics.get('coverage_state', ''),
                'robots_txt_state': combined_metrics.get('robots_txt_state', ''),
                'indexing_state': combined_metrics.get('indexing_state', ''),
                'last_crawl_time': combined_metrics.get('last_crawl_time', ''),
                'page_fetch_state': combined_metrics.get('page_fetch_state', ''),
                'analysis_date': analysis_date
            },
            'sitemap_data': {
                'url': [website_id],
                'sitemaps_submitted': combined_metrics.get('sitemaps_submitted', ''),
                'sitemap_count': combined_metrics.get('sitemap_count', 0),
                'sitemap_errors': combined_metrics.get('sitemap_errors', 0),
                'sitemap_warnings': combined_metrics.get('sitemap_warnings', 0),
                'last_submission': combined_metrics.get('last_submission', ''),
                'analysis_date': analysis_date
            },
            'mobile_usability': {
                'url': [website_id],
                'mobile_friendly_status': combined_metrics.get('mobile_friendly_status', ''),
                'mobile_friendly_issues_count': combined_metrics.get('mobile_friendly_issues_count', 0),
                'mobile_friendly_issues': combined_metrics.get('mobile_friendly_issues', ''),
                'mobile_test_loading_state': combined_metrics.get('mobile_test_loading_state', ''),
                'mobile_passed': combined_metrics.get('mobile_passed', ''),
                'analysis_date': analysis_date
            },
            'keyword_analysis': {
                'url': [website_id],
                'top_keywords': combined_metrics.get('top_keywords', ''),
                'total_keywords_tracked': combined_metrics.get('total_keywords_tracked', 0),
                'avg_keyword_position': combined_metrics.get('avg_keyword_position', 0),
                'high_opportunity_keywords': combined_metrics.get('high_opportunity_keywords', 0),
                'branded_keywords_count': combined_metrics.get('branded_keywords_count', 0),
                'keyword_cannibalization_risk': combined_metrics.get('keyword_cannibalization_risk', ''),
                'analysis_date': analysis_date
            },

        }
        
        # Update each table
        for table_name, data in table_data.items():
            try:
                print(f"\t\tAttempting to update {table_name} with data: {data}")
                result = tables[table_name].create(data)
                print(f"\t\t✓ Updated {table_name} - Record ID: {result['id']}")
            except Exception as e:
                print(f"\t\t✗ Failed to update {table_name}: {e}")
                print(f"\t\t   Data attempted: {data}")
                # Continue with other tables even if one fails
        
        # Update last analyzed timestamp in main websites table
        try:
            tables['websites'].update(website_id, {'last_analyzed': analysis_date})
            print(f"\t\t✓ Updated last_analyzed timestamp in main table")
        except Exception as e:
            print(f"\t\t✗ Failed to update last_analyzed timestamp: {e}")
        
        return True
        
    except Exception as e:
        print(f"\t\t✗ Error updating organized tables: {e}")
        return False

def get_url_inspection(service, url):
    """Get URL inspection data from Google Search Console."""
    print(f"\nFetching URL inspection data for {url}...")
    
    # Get site property (domain vs URL prefix)
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    url_prefix = f"https://{parsed.netloc}/"
    domain_property = f"sc-domain:{domain}"
    
    try:
        sites = service.sites().list().execute().get("siteEntry", [])
        original_is_domain = any(site.get("siteUrl") == domain_property for site in sites)
    except Exception:
        original_is_domain = False
    
    site_property = domain_property if original_is_domain else url_prefix
    
    try:
        print(f"\tChecking URL inspection for {url}...")
        
        # For URL inspection, we need to use the full URL
        inspection_url = url
        
        # Build URL inspection request
        request_body = {
            'inspectionUrl': inspection_url,
            'siteUrl': site_property,
            'languageCode': 'en'
        }
        
        # Call URL inspection API
        encoded_site_url = quote(site_property, safe=':/')
        response = service.urlInspection().index().inspect(body=request_body).execute()
        
        # Extract inspection results
        inspection_result = response.get('inspectionResult', {})
        index_status_result = inspection_result.get('indexStatusResult', {})
        
        # Get verdict
        verdict = index_status_result.get('verdict', 'UNKNOWN')
        
        # Get coverage state
        coverage_state = index_status_result.get('coverageState', 'UNKNOWN')
        
        # Get robots.txt state
        robots_txt_state = index_status_result.get('robotsTxtState', 'UNKNOWN')
        
        # Get indexing state
        indexing_state = index_status_result.get('indexingState', 'UNKNOWN')
        
        # Get last crawl time
        last_crawl_time = index_status_result.get('lastCrawlTime', '')
        
        # Get page fetch state
        page_fetch_result = inspection_result.get('pageFetchResult', {})
        page_fetch_state = page_fetch_result.get('fetchState', 'UNKNOWN')
        
        print(f"\t✓ URL inspection completed: {verdict}")
        
        # Clean up values for Airtable field types
        return {
            'index_verdict': str(verdict).replace('"', '').strip(),
            'coverage_state': str(coverage_state).replace('"', '').strip(),
            'robots_txt_state': str(robots_txt_state).replace('"', '').strip(),
            'indexing_state': str(indexing_state).replace('"', '').strip(),
            'last_crawl_time': str(last_crawl_time).strip(),
            'page_fetch_state': str(page_fetch_state).replace('"', '').strip()
        }
        
    except Exception as e:
        print(f"\t✗ Error fetching URL inspection for {url}: {e}")
        return {
            'index_verdict': 'ERROR',
            'coverage_state': 'ERROR',
            'robots_txt_state': 'ERROR', 
            'indexing_state': 'ERROR',
            'last_crawl_time': '',
            'page_fetch_state': 'ERROR'
        }

def main():
    # Check for required environment variables
    required_vars = [
        'AIRTABLE_API_KEY',
        'AIRTABLE_BASE_ID'
    ]
    
    # Check if using organized multi-table structure
    use_organized_tables = os.getenv('USE_ORGANIZED_TABLES', 'false').lower() == 'true'
    print(f"Organized tables mode: {use_organized_tables}")
    print(f"Environment variable USE_ORGANIZED_TABLES = '{os.getenv('USE_ORGANIZED_TABLES', 'NOT SET')}')")
    
    if not use_organized_tables:
        required_vars.append('AIRTABLE_TABLE_NAME')
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print("Missing required environment variables:")
        for var in missing_vars:
            print(f"- {var}")
        print("\nPlease create a .env file with these variables.")
        return

    try:
        # Get GSC credentials and create service
        print("Getting Google Search Console credentials...")
        credentials = get_gsc_credentials()
        service = build('searchconsole', 'v1', credentials=credentials)
        
        # Get records from Airtable
        print(f"\nFetching records from Airtable (organized mode: {use_organized_tables})...")
        
        if use_organized_tables:
            tables, records = get_airtable_multi_tables()
            print(f"Found {len(records)} websites")
        else:
            table, records = get_airtable_records()
            print(f"Found {len(records)} records")
        
        # Process each record
        print("\nVerifying URLs and fetching GSC metrics...")
        total_metrics = {'impressions': 0, 'clicks': 0, 'ctr': [], 'average_position': []}
        permission_errors = []
        
        for i, record in enumerate(records, 1):
            # Check if there is "url" column in Airtable
            if 'url' not in record['fields']:
                print(f"Skipping record {i}: No 'url' field found")
                continue
                
            url = record['fields']['url']
            print(f"\tProcessing {i}/{len(records)}: {url}")
            
            try:
                # First verify the URL exists in GSC
                site_url, is_domain_property, original_is_domain = get_site_info(service, url)
                if original_is_domain:
                    print(f"\tFound as domain property: {url}")
                else:
                    print(f"\tFound as URL prefix property: {url}")
                
                # Get metrics from GSC
                metrics = get_gsc_metrics(service, url)
                
                # Get PSI metrics
                print(f"\nFetching PageSpeed Insights metrics for {url}...")
                psi_metrics = get_psi_metrics(url)
                # Log the PSI metrics for debugging
                print(f"\tFetched PageSpeed Insights metrics for {url}: {psi_metrics}")
                
                # Get URL inspection data
                print(f"\nFetching URL inspection data for {url}...")
                url_inspection = get_url_inspection(service, url)
                print(f"\tFetched URL inspection for {url}: {url_inspection}")
                
                # Get sitemaps status
                print(f"\nFetching sitemap submission data for {url}...")
                sitemaps_status = get_sitemaps_status(service, url)
                print(f"\tFetched sitemaps status for {url}: {sitemaps_status}")
                
                # Get mobile usability from PSI
                mobile_test = get_mobile_usability_from_psi(url)
                print(f"\tFetched mobile usability results for {url}: {mobile_test}")
                
                # Get keyword performance
                print(f"\nFetching keyword performance for {url}...")
                keyword_performance = get_keyword_performance(service, url)
                print(f"\tFetched keyword performance for {url}: {keyword_performance}")
        
                
                # Combine metrics
                combined_metrics = {**metrics, **psi_metrics, **url_inspection, **sitemaps_status, **mobile_test, **keyword_performance}
                # Log combined metrics before updating Airtable
                print(f"\nCombined metrics to update Airtable for {url}: {combined_metrics}")
                
                # Update metrics in Airtable
                print(f"\nUpdating Airtable...")
                try:
                    if use_organized_tables:
                        success = update_airtable_organized(tables, url, combined_metrics)
                        if success:
                            print(f"\t✓ Successfully updated organized tables")
                        else:
                            print(f"\t✗ Failed to update organized tables")
                    else:
                        table.update(record['id'], combined_metrics)
                        print(f"\t✓ Successfully updated single table record")
                except Exception as airtable_error:
                    print(f"\t✗ Airtable update failed: {airtable_error}")
                    raise airtable_error
                
                # Accumulate metrics for summary
                if metrics['impressions'] > 0:  # Only include non-zero metrics
                    total_metrics['impressions'] += metrics['impressions']
                    total_metrics['clicks'] += metrics['clicks']
                    total_metrics['ctr'].append(metrics['ctr'])
                    total_metrics['average_position'].append(metrics['average_position'])
                
                print(f"\t✓ Updated metrics for {url}")
                
            except Exception as e:
                print(f"\tError processing {url}: {str(e)}")
                permission_errors.append(url)
        
        if permission_errors:
            print("\nSites with errors:")
            for url in permission_errors:
                print(f"\t- {url}")
            print("To fix errors:")
            print("1. Verify the sites are properly set up in GSC")
            print("2. Check if they are domain properties or URL prefix properties")
            print("3. Make sure you have proper access permissions")
        
        print("\nProcess completed!")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")










if __name__ == "__main__":
    main()
