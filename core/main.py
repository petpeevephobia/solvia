import os
import sys
import json
import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

import pickle
from urllib.parse import urlparse, quote
import requests
from core.analysis_processor import generate_seo_analysis
import openai
from core.auth_setup import get_gsc_credentials, check_gsc_access, get_gsc_service

# Load environment variables
load_dotenv()

# If modifying these scopes, delete the token.pickle file.
SCOPES = [
    'https://www.googleapis.com/auth/webmasters.readonly',
    'https://www.googleapis.com/auth/webmasters'
]

model = "gpt-4o-mini"







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
                break
            elif site_url.startswith('http') and domain in site_url:
                break
        
        # For verification, always return URL prefix version first
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
            response = service.searchanalytics().query(
                siteUrl=encoded_site_url,
                body=request
            ).execute()
            
            # If original was domain property, switch back for actual data fetch
            if original_is_domain:
                domain = parsed.netloc.replace('www.', '')
                site_url = f"sc-domain:{domain}"
                encoded_site_url = quote(site_url, safe=':/')
                page_url = url  # Use full URL for domain property
                
                # Update request with full URL for domain property
                request['dimensionFilterGroups'][0]['filters'][0]['expression'] = page_url
                
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
        return metrics
        
    except Exception as e:
        error_message = str(e)
        return {
            'impressions': 0,
            'clicks': 0,
            'ctr': 0,
            'average_position': 0
        }





def get_psi_metrics(url, strategy="mobile"):
    """Fetch PageSpeed Insights metrics for a given URL."""
    api_key = os.getenv("PSI_API_KEY")
    if not api_key:
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
        resp = service.sitemaps().list(siteUrl=site_property).execute()
        entries = resp.get("sitemap", [])
        
        if not entries:
            return {
                "sitemaps_submitted": "No sitemaps found",
                "sitemap_count": 0,
                "sitemap_errors": 0,
                "sitemap_warnings": 0,
                "last_submission": None
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
            "last_submission": latest_submission if latest_submission else None
        }
        
    except Exception as e:
        print(f"\tError fetching sitemaps for {url}: {e}")
        return {
            "sitemaps_submitted": "Error fetching data",
            "sitemap_count": 0,
            "sitemap_errors": -1,
            "sitemap_warnings": -1, 
            "last_submission": None
        }





def get_mobile_usability_from_psi(url):
    """Extract mobile usability data from PageSpeed Insights API."""
    api_key = os.getenv("PSI_API_KEY")
    if not api_key:
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
        
        return {
            "mobile_friendly_status": mobile_status,
            "mobile_friendly_issues_count": len(mobile_issues),
            "mobile_friendly_issues": "; ".join(mobile_issues),
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

def get_url_inspection(service, url):
    """Get URL inspection data from Google Search Console."""
    
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
        
        # Get page fetch state with better handling
        page_fetch_result = inspection_result.get('pageFetchResult', {})
        fetch_state = page_fetch_result.get('fetchState', '')
        
        # Map fetch states to more meaningful values
        fetch_state_mapping = {
            'SUCCESSFUL': 'Successfully Fetched',
            'PARTIAL': 'Partially Fetched',
            'FAILED': 'Failed to Fetch',
            'NOT_FETCHED': 'Not Yet Fetched',
            '': 'Not Available',
            'UNKNOWN': 'Not Available'
        }
        
        page_fetch_state = fetch_state_mapping.get(fetch_state, 'Not Available')
        
        return {
            'index_verdict': str(verdict).replace('"', '').strip(),
            'coverage_state': str(coverage_state).replace('"', '').strip(),
            'robots_txt_state': str(robots_txt_state).replace('"', '').strip(),
            'indexing_state': str(indexing_state).replace('"', '').strip(),
            'last_crawl_time': str(last_crawl_time).strip() if last_crawl_time else None,
            'page_fetch_state': page_fetch_state
        }
        
    except Exception as e:
        print(f"\t✗ Error fetching URL inspection for {url}: {e}")
        return {
            'index_verdict': 'Error',
            'coverage_state': 'Error',
            'robots_txt_state': 'Error', 
            'indexing_state': 'Error',
            'last_crawl_time': None,
            'page_fetch_state': 'Error Fetching Data'
        }

def main():
    # Check for required environment variables
    required_vars = [
        'AIRTABLE_API_KEY',
        'AIRTABLE_BASE_ID',
        'OPENAI_API_KEY'  # Add OpenAI API key requirement
    ]
    
    # Check if using organized multi-table structure
    use_organized_tables = os.getenv('USE_ORGANIZED_TABLES', 'false').lower() == 'true'
    print(f"Organized tables mode: {use_organized_tables}")
    
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
        # Initialize OpenAI with new client format
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
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
        for record in records:
            url = record['fields'].get('url')
            if not url:
                print("Skipping record with no URL")
                continue
                
            print(f"\nProcessing: {url}")
            
            # Collect all metrics
            gsc_metrics = get_gsc_metrics(service, url)
            psi_metrics = get_psi_metrics(url)
            sitemaps_status = get_sitemaps_status(service, url)
            mobile_test = get_mobile_usability_from_psi(url)
            keyword_performance = get_keyword_performance(service, url)
            
            # Combine all metrics into a flat structure (using enhanced business analysis)
            combined_metrics = {
                'url': url,
                # Core metrics from GSC
                'impressions': gsc_metrics.get('impressions', 0),
                'clicks': gsc_metrics.get('clicks', 0),
                'ctr': gsc_metrics.get('ctr', 0),
                'average_position': gsc_metrics.get('average_position', 0),
                
                # Performance metrics from PSI
                'performance_score': psi_metrics.get('performance_score', 0),
                'first_contentful_paint': psi_metrics.get('first_contentful_paint', 0),
                'largest_contentful_paint': psi_metrics.get('largest_contentful_paint', 0),
                'speed_index': psi_metrics.get('speed_index', 0),
                'time_to_interactive': psi_metrics.get('time_to_interactive', 0),
                'total_blocking_time': psi_metrics.get('total_blocking_time', 0),
                'cumulative_layout_shift': psi_metrics.get('cumulative_layout_shift', 0),
                
                # Keyword metrics
                'top_keywords': keyword_performance.get('top_keywords', ''),
                'total_keywords_tracked': keyword_performance.get('total_keywords_tracked', 0),
                'avg_keyword_position': keyword_performance.get('avg_keyword_position', 0),
                'high_opportunity_keywords': keyword_performance.get('high_opportunity_keywords', 0),
                'branded_keywords_count': keyword_performance.get('branded_keywords_count', 0),
                'keyword_cannibalization_risk': keyword_performance.get('keyword_cannibalization_risk', ''),
                
                # Mobile usability
                'mobile_friendly_status': mobile_test.get('mobile_friendly_status', ''),
                'mobile_friendly_issues_count': mobile_test.get('mobile_friendly_issues_count', 0),
                'mobile_friendly_issues': mobile_test.get('mobile_friendly_issues', ''),
                'mobile_test_loading_state': mobile_test.get('mobile_test_loading_state', ''),
                'mobile_passed': mobile_test.get('mobile_passed', ''),
                
                # Sitemap data
                'sitemaps_submitted': sitemaps_status.get('sitemaps_submitted', ''),
                'sitemap_count': sitemaps_status.get('sitemap_count', 0),
                'sitemap_errors': sitemaps_status.get('sitemap_errors', 0),
                'sitemap_warnings': sitemaps_status.get('sitemap_warnings', 0),
                'last_submission': sitemaps_status.get('last_submission', ''),
                
                # Index technical
                'index_verdict': get_url_inspection(service, url).get('index_verdict', ''),
                'coverage_state': get_url_inspection(service, url).get('coverage_state', ''),
                'robots_txt_state': get_url_inspection(service, url).get('robots_txt_state', ''),
                'indexing_state': get_url_inspection(service, url).get('indexing_state', ''),
                'last_crawl_time': get_url_inspection(service, url).get('last_crawl_time', ''),
                'page_fetch_state': get_url_inspection(service, url).get('page_fetch_state', ''),
            }
            
            # Generate OpenAI analysis (using enhanced business data)
            openai_analysis = generate_seo_analysis(combined_metrics, {})
            
            # Map data to SEO_Reports format and update table
            seo_report_data = map_to_seo_reports(combined_metrics, openai_analysis, {}, tables)
            if seo_report_data:  # Only update if we got valid data
                update_seo_reports_table(tables, seo_report_data)
            
            # Update Airtable with organized data
            if os.getenv('AIRTABLE_API_KEY') and os.getenv('AIRTABLE_BASE_ID'):
                try:
                    print("\n📊 Updating Airtable with organized data...")
                    update_airtable_organized(tables, url, combined_metrics)
                    print("✅ Airtable update completed")
                except Exception as e:
                    print(f"❌ Error updating Airtable: {str(e)}")
            else:
                print("⚠️ Skipping Airtable update - API key or base ID not configured")
                print("   Please set AIRTABLE_API_KEY and AIRTABLE_BASE_ID in your .env file")
        
    except Exception as e:
        print(f"Error in main process: {str(e)}")
        raise

if __name__ == "__main__":
    main()
