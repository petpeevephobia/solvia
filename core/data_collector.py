import os
import json
import requests
from datetime import datetime, timedelta
import pandas as pd
from pyairtable import Api
from core.auth_setup import get_gsc_service

def get_airtable_records():
    """
    Fetch records from Airtable.
    
    Returns:
        tuple: (table, records) where:
            - table is the Airtable table object
            - records is a list of records from the table
    """
    try:
        api = Api(os.getenv('AIRTABLE_API_KEY'))
        table = api.table(os.getenv('AIRTABLE_BASE_ID'), os.getenv('AIRTABLE_TABLE_NAME'))
        records = table.all()
        return table, records
    except Exception as e:
        print(f"Error fetching Airtable records: {str(e)}")
        return None, []

def get_site_info(service, url):
    """
    Get basic site information from Google Search Console.
    
    Args:
        service: Google Search Console service object
        url (str): The website URL to analyze
        
    Returns:
        dict: Basic site information
    """
    try:
        site_info = service.sites().get(siteUrl=url).execute()
        return {
            'permission_level': site_info.get('permissionLevel'),
            'site_url': site_info.get('siteUrl')
        }
    except Exception as e:
        print(f"Error getting site info: {str(e)}")
        return {}

def get_gsc_metrics(service, url, days=30):
    """
    Get Google Search Console metrics for a website.
    
    Args:
        service: Google Search Console service object
        url (str): The website URL to analyze
        days (int): Number of days to analyze
        
    Returns:
        dict: GSC metrics data
    """
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        request = {
            'startDate': start_date.isoformat(),
            'endDate': end_date.isoformat(),
            'dimensions': ['query', 'page', 'device', 'country'],
            'rowLimit': 25000,
            'startRow': 0
        }
        
        response = service.searchanalytics().query(siteUrl=url, body=request).execute()
        return response
    except Exception as e:
        print(f"Error getting GSC metrics: {str(e)}")
        return {}

def get_psi_metrics(url, strategy="mobile"):
    """
    Get PageSpeed Insights metrics for a website.
    
    Args:
        url (str): The website URL to analyze
        strategy (str): Analysis strategy ('mobile' or 'desktop')
        
    Returns:
        dict: PageSpeed Insights metrics
    """
    try:
        api_key = os.getenv('GOOGLE_API_KEY')
        psi_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&strategy={strategy}&key={api_key}"
        response = requests.get(psi_url)
        return response.json()
    except Exception as e:
        print(f"Error getting PSI metrics: {str(e)}")
        return {}

def get_sitemaps_status(service, url):
    """
    Get sitemap status from Google Search Console.
    
    Args:
        service: Google Search Console service object
        url (str): The website URL to analyze
        
    Returns:
        dict: Sitemap status information
    """
    try:
        sitemaps = service.sitemaps().list(siteUrl=url).execute()
        return sitemaps
    except Exception as e:
        print(f"Error getting sitemap status: {str(e)}")
        return {}

def get_mobile_usability_from_psi(url):
    """
    Get mobile usability metrics from PageSpeed Insights.
    
    Args:
        url (str): The website URL to analyze
        
    Returns:
        dict: Mobile usability metrics
    """
    try:
        psi_data = get_psi_metrics(url, strategy="mobile")
        if 'lighthouseResult' in psi_data:
            return psi_data['lighthouseResult'].get('categories', {}).get('mobile-usability', {})
        return {}
    except Exception as e:
        print(f"Error getting mobile usability: {str(e)}")
        return {}

def get_keyword_performance(service, url, days=90):
    """
    Get keyword performance data from Google Search Console.
    
    Args:
        service: Google Search Console service object
        url (str): The website URL to analyze
        days (int): Number of days to analyze
        
    Returns:
        dict: Keyword performance data
    """
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        request = {
            'startDate': start_date.isoformat(),
            'endDate': end_date.isoformat(),
            'dimensions': ['query'],
            'rowLimit': 25000,
            'startRow': 0
        }
        
        response = service.searchanalytics().query(siteUrl=url, body=request).execute()
        return response
    except Exception as e:
        print(f"Error getting keyword performance: {str(e)}")
        return {}

def get_url_inspection(service, url):
    """
    Get URL inspection data from Google Search Console.
    
    Args:
        service: Google Search Console service object
        url (str): The website URL to analyze
        
    Returns:
        dict: URL inspection data
    """
    try:
        response = service.urlInspection().index().inspect(body={'inspectionUrl': url}).execute()
        return response
    except Exception as e:
        print(f"Error getting URL inspection: {str(e)}")
        return {}

def get_airtable_multi_tables():
    """
    Get data from multiple Airtable tables.
    
    Returns:
        tuple: (tables, records) where:
            - tables is a dict of table objects
            - records is a list of website records from the Websites table
    """
    try:
        api = Api(os.getenv('AIRTABLE_API_KEY'))
        tables = {}
        base_id = os.getenv('AIRTABLE_BASE_ID')
        
        # First get the Websites table and its records
        websites_table = api.table(base_id, 'Websites')
        records = websites_table.all()
        tables['Websites'] = websites_table
        
        # Add other required tables
        table_names = [
            'Core_Metrics',
            'Performance_Metrics',
            'Index_Technical',
            'Sitemap_Data',
            'Mobile_Usability',
            'Keyword_Analysis',
            'Business_Analysis'
        ]
        
        for table_name in table_names:
            table = api.table(base_id, table_name)
            tables[table_name] = table
            
        return tables, records
    except Exception as e:
        print(f"Error getting Airtable tables: {str(e)}")
        return {}, []

def update_airtable_organized(tables, url, combined_metrics):
    """
    Update organized Airtable tables with categorized data.
    
    Args:
        tables (dict): Dictionary of Airtable table objects
        url (str): Website URL
        combined_metrics (dict): Combined metrics data
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        analysis_date = datetime.now().isoformat()
        print(f"\t\tStarting Airtable update process for {url}")
        print(f"\t\tAnalysis date: {analysis_date}")
        
        # Find or create website record
        website_record = None
        websites_records = tables['Websites'].all()
        print(f"\t\tLooking for {url} in {len(websites_records)} website records")
        
        for record in websites_records:
            record_url = record['fields'].get('url')
            print(f"\t\t  Checking: '{record_url}' vs '{url}'")
            
            # Try different URL matching strategies
            if record_url == url:
                website_record = record
                print(f"\t\t  ✓ Found exact match: {record['id']}")
                break
            elif record_url and url:
                # Try without trailing slashes
                clean_record = record_url.rstrip('/')
                clean_url = url.rstrip('/')
                if clean_record == clean_url:
                    website_record = record
                    print(f"\t\t  ✓ Found match (no trailing slash): {record['id']}")
                    break
                # Try without www
                if clean_record.replace('www.', '') == clean_url.replace('www.', ''):
                    website_record = record
                    print(f"\t\t  ✓ Found match (no www): {record['id']}")
                    break
        
        if not website_record:
            print(f"\t\t✗ CRITICAL ERROR: Website {url} not found in main Websites table!")
            print(f"\t\t  This means the organized table update will be skipped entirely.")
            print(f"\t\t  Available URLs in main table ({len(websites_records)} records):")
            for i, record in enumerate(websites_records[:10], 1):  # Show first 10
                record_url = record['fields'].get('url', 'NO URL FIELD')
                print(f"\t\t    {i}. '{record_url}'")
            if len(websites_records) > 10:
                print(f"\t\t    ... and {len(websites_records) - 10} more records")
            print(f"\t\t  SOLUTION: Add '{url}' to your Websites table first!")
            return False
        
        website_id = website_record['id']
        print(f"\t\tUsing website ID: {website_id}")
        
        # Map AI values to Airtable options
        try:
            from core.data_mapper import map_ai_values_to_airtable_options
            combined_metrics = map_ai_values_to_airtable_options(combined_metrics)
            print("\t\t✓ Successfully mapped AI values to Airtable options")
        except Exception as e:
            print(f"\t\t⚠ Warning: Failed to map AI values: {e}")
            print("\t\t  Continuing with original values...")
        
        # Prepare data for each table
        print(f"\t\tPreparing data for {len(combined_metrics)} metrics across 7 organized tables...")
        
        # Core Metrics
        core_metrics_data = {
            'url': [website_id],  # Link to Websites table
            'impressions': int(combined_metrics.get('impressions', 0)),
            'clicks': int(combined_metrics.get('clicks', 0)),
            'ctr': float(combined_metrics.get('ctr', 0)),
            'average_position': float(combined_metrics.get('average_position', 0)),
            'analysis_date': analysis_date
        }
        
        # Performance Metrics
        performance_data = {
            'url': [website_id],
            'performance_score': float(combined_metrics.get('performance_score', 0)),
            'first_contentful_paint': float(combined_metrics.get('first_contentful_paint', 0)),
            'largest_contentful_paint': float(combined_metrics.get('largest_contentful_paint', 0)),
            'speed_index': float(combined_metrics.get('speed_index', 0)),
            'time_to_interactive': float(combined_metrics.get('time_to_interactive', 0)),
            'total_blocking_time': float(combined_metrics.get('total_blocking_time', 0)),
            'cumulative_layout_shift': float(combined_metrics.get('cumulative_layout_shift', 0)),
            'analysis_date': analysis_date
        }
        
        # Keyword Analysis
        keyword_data = {
            'url': [website_id],
            'top_keywords': str(combined_metrics.get('top_keywords', '')),
            'total_keywords_tracked': int(combined_metrics.get('total_keywords_tracked', 0)),
            'avg_keyword_position': float(combined_metrics.get('avg_keyword_position', 0)),
            'high_opportunity_keywords': int(combined_metrics.get('high_opportunity_keywords', 0)),
            'branded_keywords_count': int(combined_metrics.get('branded_keywords_count', 0)),
            'keyword_cannibalization_risk': str(combined_metrics.get('keyword_cannibalization_risk', '')),
            'analysis_date': analysis_date
        }

        # Mobile Usability
        mobile_data = {
            'url': [website_id],
            'mobile_friendly_status': str(combined_metrics.get('mobile_friendly_status', '')),
            'mobile_friendly_issues_count': int(combined_metrics.get('mobile_friendly_issues_count', 0)),
            'mobile_friendly_issues': str(combined_metrics.get('mobile_friendly_issues', '')),
            'mobile_test_loading_state': str(combined_metrics.get('mobile_test_loading_state', '')),
            'mobile_passed': str(combined_metrics.get('mobile_passed', '')),
            'analysis_date': analysis_date
        }

        # Sitemap Data
        sitemap_data = {
            'url': [website_id],
            'sitemaps_submitted': str(combined_metrics.get('sitemaps_submitted', '')),
            'sitemap_count': int(combined_metrics.get('sitemap_count', 0)),
            'sitemap_errors': int(combined_metrics.get('sitemap_errors', 0)),
            'sitemap_warnings': int(combined_metrics.get('sitemap_warnings', 0)),
            'last_submission': str(combined_metrics.get('last_submission', '')),
            'analysis_date': analysis_date
        }

        # Index Technical
        index_data = {
            'url': [website_id],
            'index_verdict': str(combined_metrics.get('index_verdict', '')),
            'coverage_state': str(combined_metrics.get('coverage_state', '')),
            'robots_txt_state': str(combined_metrics.get('robots_txt_state', '')),
            'indexing_state': str(combined_metrics.get('indexing_state', '')),
            'last_crawl_time': str(combined_metrics.get('last_crawl_time', '')),
            'page_fetch_state': str(combined_metrics.get('page_fetch_state', '')),
            'analysis_date': analysis_date
        }

        # Business Analysis
        business_data = {
            'url': [website_id],
            'business_model': str(combined_metrics.get('business_model', '')),
            'target_market': str(combined_metrics.get('target_market', '')),
            'industry_sector': str(combined_metrics.get('industry_sector', '')),
            'company_size': str(combined_metrics.get('company_size', '')),
            'has_ecommerce': bool(combined_metrics.get('has_ecommerce', False)),
            'has_local_presence': bool(combined_metrics.get('has_local_presence', False)),
            'business_complexity_score': float(combined_metrics.get('business_complexity_score', 0)),
            'primary_age_group': str(combined_metrics.get('primary_age_group', '')),
            'income_level': str(combined_metrics.get('income_level', '')),
            'audience_sophistication': str(combined_metrics.get('audience_sophistication', '')),
            'services_offered': str(combined_metrics.get('services_offered', '')),
            'has_public_pricing': bool(combined_metrics.get('has_public_pricing', False)),
            'service_count': int(combined_metrics.get('service_count', 0)),
            'geographic_scope': str(combined_metrics.get('geographic_scope', '')),
            'target_locations': str(combined_metrics.get('target_locations', '')),
            'is_location_based': bool(combined_metrics.get('is_location_based', False)),
            'business_maturity': str(combined_metrics.get('business_maturity', '')),
            'establishment_year': int(combined_metrics.get('establishment_year', 0)) if combined_metrics.get('establishment_year') else None,
            'experience_indicators': bool(combined_metrics.get('experience_indicators', False)),
            'platform_detected': str(combined_metrics.get('platform_detected', '')),
            'has_advanced_features': bool(combined_metrics.get('has_advanced_features', False)),
            'social_media_integration': bool(combined_metrics.get('social_media_integration', False)),
            'tech_sophistication': str(combined_metrics.get('tech_sophistication', '')),
            'has_content_marketing': bool(combined_metrics.get('has_content_marketing', False)),
            'has_lead_generation': bool(combined_metrics.get('has_lead_generation', False)),
            'has_social_proof': bool(combined_metrics.get('has_social_proof', False)),
            'content_maturity': str(combined_metrics.get('content_maturity', '')),
            'phone_prominence': bool(combined_metrics.get('phone_prominence', False)),
            'has_contact_forms': bool(combined_metrics.get('has_contact_forms', False)),
            'has_live_chat': bool(combined_metrics.get('has_live_chat', False)),
            'preferred_contact_method': str(combined_metrics.get('preferred_contact_method', '')),
            'competitive_positioning': str(combined_metrics.get('competitive_positioning', '')),
            'positioning_strength': str(combined_metrics.get('positioning_strength', '')),
            'value_proposition': str(combined_metrics.get('value_proposition', '')),
            'brand_strength': str(combined_metrics.get('brand_strength', '')),
            'trust_indicators': str(combined_metrics.get('trust_indicators', '')),
            'business_insights': str(combined_metrics.get('business_insights', '')),
            'seo_strategy_recommendations': str(combined_metrics.get('seo_strategy_recommendations', '')),
            'analysis_date': analysis_date
        }
        
        # Update each table
        successful_updates = 0
        failed_updates = 0
        update_results = {}
        
        # Helper function to safely update a table
        def safe_update_table(table_name, data):
            try:
                print(f"\n\t\t--- Updating {table_name} ---")
                result = tables[table_name].create(data)
                print(f"\t\t✓ SUCCESS: Updated {table_name} - Record ID: {result['id']}")
                return True, result['id']
            except Exception as e:
                print(f"\t\t✗ FAILED to update {table_name}: {e}")
                return False, str(e)
        
        # Update all tables
        tables_to_update = {
            'Core_Metrics': core_metrics_data,
            'Performance_Metrics': performance_data,
            'Keyword_Analysis': keyword_data,
            'Mobile_Usability': mobile_data,
            'Sitemap_Data': sitemap_data,
            'Index_Technical': index_data,
            'Business_Analysis': business_data
        }
        
        for table_name, data in tables_to_update.items():
            success, result = safe_update_table(table_name, data)
            if success:
                successful_updates += 1
            else:
                failed_updates += 1
            update_results[table_name] = {'success': success, 'result': result}
        
        print(f"\n\t\tUpdate Summary: {successful_updates} successful, {failed_updates} failed")
        
        # Update last analyzed timestamp in main websites table
        try:
            tables['Websites'].update(website_id, {'last_analyzed': analysis_date})
            print(f"\t\t✓ Updated last_analyzed timestamp in main table")
        except Exception as e:
            print(f"\t\t✗ Failed to update last_analyzed timestamp: {e}")
        
        # Return success only if at least some tables were updated
        success = successful_updates > 0
        if success:
            print(f"\t\t🎉 OVERALL SUCCESS: {successful_updates} tables updated!")
        else:
            print(f"\t\t💥 OVERALL FAILURE: No tables were updated!")
        
        return success, update_results
        
    except Exception as e:
        print(f"\t\t✗ Error updating organized tables: {e}")
        return False, {'error': str(e)} 