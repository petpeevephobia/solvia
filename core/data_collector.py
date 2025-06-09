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
        list: List of records from Airtable
    """
    try:
        api = Api(os.getenv('AIRTABLE_API_KEY'))
        table = api.table(os.getenv('AIRTABLE_BASE_ID'), os.getenv('AIRTABLE_TABLE_NAME'))
        return table.all()
    except Exception as e:
        print(f"Error fetching Airtable records: {str(e)}")
        return []

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
        dict: Data from multiple Airtable tables
    """
    try:
        api = Api(os.getenv('AIRTABLE_API_KEY'))
        tables = {}
        base_id = os.getenv('AIRTABLE_BASE_ID')
        
        # Add your table names here
        table_names = ['Business_Analysis', 'SEO_Metrics', 'Technical_Audit']
        
        for table_name in table_names:
            table = api.table(base_id, table_name)
            tables[table_name] = table.all()
            
        return tables
    except Exception as e:
        print(f"Error getting Airtable tables: {str(e)}")
        return {} 