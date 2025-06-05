import os
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
    
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
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
        
        with open('token.pickle', 'wb') as token:
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
                print(f"Found original domain property: {domain_property}")
                break
            elif site_url.startswith('http') and domain in site_url:
                print(f"Found original URL prefix property: {site_url}")
                break
        
        # For verification, always return URL prefix version first
        print(f"Checking URL prefix version: {url_prefix}")
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
        print(f"Verifying access using URL prefix: {site_url}")
        
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
            print(f"Verifying access to: {site_url}")
            response = service.searchanalytics().query(
                siteUrl=encoded_site_url,
                body=request
            ).execute()
            print("Successfully verified URL access")
            
            # If original was domain property, switch back for actual data fetch
            if original_is_domain:
                print("Switching back to domain property for data fetch...")
                domain = parsed.netloc.replace('www.', '')
                site_url = f"sc-domain:{domain}"
                encoded_site_url = quote(site_url, safe=':/')
                page_url = url  # Use full URL for domain property
                
                # Update request with full URL for domain property
                request['dimensionFilterGroups'][0]['filters'][0]['expression'] = page_url
                
                print(f"Fetching data using domain property: {site_url}")
                response = service.searchanalytics().query(
                    siteUrl=encoded_site_url,
                    body=request
                ).execute()
            
        except Exception as e:
            # print(f"Error during verification: {str(e)}")
            if original_is_domain:
                print("Falling back to domain property due to insufficient permissions on URL prefix property")
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
            print(f"No data found for URL: {url}")
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
        print(f"Retrieved metrics for {url}: {metrics}")
        return metrics
        
    except Exception as e:
        error_message = str(e)
        print(f"Error querying GSC for {url}: {error_message}")
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





def main():
    # Check for required environment variables
    required_vars = [
        'AIRTABLE_API_KEY',
        'AIRTABLE_BASE_ID',
        'AIRTABLE_TABLE_NAME'
    ]
    
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
        print("\nFetching records from Airtable...")
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
            print(f"\nProcessing {i}/{len(records)}: {url}")
            
            try:
                # First verify the URL exists in GSC
                site_url, is_domain_property, original_is_domain = get_site_info(service, url)
                if original_is_domain:
                    print(f"Found as domain property: {url}")
                else:
                    print(f"Found as URL prefix property: {url}")
                
                # Get metrics from GSC
                metrics = get_gsc_metrics(service, url)
                
                # Get PSI metrics
                psi_metrics = get_psi_metrics(url)
                # Log the PSI metrics for debugging
                print(f"Fetched PSI metrics for {url}: {psi_metrics}")
                
                # Combine metrics
                combined_metrics = {**metrics, **psi_metrics}
                # Log combined metrics before updating Airtable
                print(f"Combined metrics to update Airtable for {url}: {combined_metrics}")
                
                # Update PSI metrics in Airtable
                table.update(record['id'], combined_metrics)
                
                # Accumulate metrics for summary
                if metrics['impressions'] > 0:  # Only include non-zero metrics
                    total_metrics['impressions'] += metrics['impressions']
                    total_metrics['clicks'] += metrics['clicks']
                    total_metrics['ctr'].append(metrics['ctr'])
                    total_metrics['average_position'].append(metrics['average_position'])
                
                print(f"✓ Updated metrics for {url}")
                
            except Exception as e:
                print(f"Error processing {url}: {str(e)}")
                permission_errors.append(url)
        
        # Display summary
        print("\nMetrics Summary:")
        print(f"Total Impressions: {total_metrics['impressions']:,}")
        print(f"Total Clicks: {total_metrics['clicks']:,}")
        if total_metrics['ctr']:
            print(f"Average CTR: {sum(total_metrics['ctr']) / len(total_metrics['ctr']):.2f}%")
            print(f"Average Position: {sum(total_metrics['average_position']) / len(total_metrics['average_position']):.2f}")
        
        if permission_errors:
            print("\nSites with errors:")
            for url in permission_errors:
                print(f"- {url}")
            print("\nTo fix errors:")
            print("1. Verify the sites are properly set up in GSC")
            print("2. Check if they are domain properties or URL prefix properties")
            print("3. Make sure you have proper access permissions")
        
        print("\nProcess completed!")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")










if __name__ == "__main__":
    main()
