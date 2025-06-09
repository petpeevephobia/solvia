import os
import sys
import json
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
from datetime import datetime, timedelta
from modules.business_analysis import BusinessAnalyzer
from modules.report_generator import ReportGenerator
import openai

# Load environment variables
load_dotenv()

# If modifying these scopes, delete the token.pickle file.
SCOPES = [
    'https://www.googleapis.com/auth/webmasters.readonly',
    'https://www.googleapis.com/auth/webmasters'
]

def map_ai_values_to_airtable_options(enhanced_data):
    """
    Intelligently map AI-generated values to valid Airtable select options using semantic analysis.
    No fallbacks - the AI should make smart decisions about its own output.
    
    Args:
        enhanced_data (dict): Enhanced business analysis data from AI
        
    Returns:
        dict: Data with values mapped to valid Airtable options
    """
    
    # Define valid Airtable select options for each field
    airtable_mappings = {
        'business_model': {
            'valid_options': ['E-commerce', 'SaaS', 'Professional Services', 'Local Services', 'Information/Content', 'Non-profit', 'Marketplace', 'Subscription'],
            'mappings': {
                'Service-Based Agency': 'Professional Services',
                'Agency': 'Professional Services',
                'Consulting': 'Professional Services',
                'Digital Agency': 'Professional Services',
                'Marketing Agency': 'Professional Services',
                'Service-Based Information Agency': 'Information/Content',
                'Information Agency': 'Information/Content',
                'Content Agency': 'Information/Content',
                'Software': 'SaaS',
                'Technology': 'SaaS',
                'Platform': 'SaaS',
                'Online Store': 'E-commerce',
                'Retail': 'E-commerce',
                'Shop': 'E-commerce',
                'Blog': 'Information/Content',
                'News': 'Information/Content',
                'Media': 'Information/Content',
                'Local Business': 'Local Services',
                'Service Business': 'Local Services'
            }
        },
        'target_market': {
            'valid_options': ['B2B', 'B2C'],
            'mappings': {
                'Business-to-Business': 'B2B',
                'Business to Business': 'B2B',
                'Enterprise': 'B2B',
                'Corporate': 'B2B',
                'Consumer': 'B2C',
                'Business-to-Consumer': 'B2C',
                'Business to Consumer': 'B2C',
                'Individual': 'B2C',
                'Personal': 'B2C',
                'B2B with potential B2C elements': 'B2B',
                'B2B/B2C': 'B2B',
                'Mixed': 'B2B',
                'Both': 'B2B',
                'Hybrid': 'B2B'
            }
        },
        'company_size': {
            'valid_options': ['Startup', 'Small', 'Medium', 'Large', 'Enterprise'],
            'mappings': {
                'Solo': 'Startup',
                'Individual': 'Startup',
                'Micro': 'Startup',
                'Small Business': 'Small',
                'SMB': 'Small',
                'SME': 'Medium',
                'Mid-size': 'Medium',
                'Mid-sized': 'Medium',
                'Growing': 'Medium',
                'Corporation': 'Large',
                'Big': 'Large',
                'Fortune 500': 'Enterprise',
                'Global': 'Enterprise',
                'Multinational': 'Enterprise'
            }
        },
        'geographic_scope': {
            'valid_options': ['Local', 'Regional', 'National', 'Global'],
            'mappings': {
                'City': 'Local',
                'Local Area': 'Local',
                'Metropolitan': 'Regional',
                'State': 'Regional',
                'Multi-state': 'Regional',
                'Country': 'National',
                'Nationwide': 'National',
                'Singapore': 'National',
                'USA': 'Global',
                'International': 'Global',
                'Worldwide': 'Global',
                'Multi-country': 'Global'
            }
        },
        'business_maturity': {
            'valid_options': ['Startup', 'Growing', 'Established', 'Mature'],
            'mappings': {
                'New': 'Startup',
                'Early-stage': 'Startup',
                'Young': 'Startup',
                'Developing': 'Growing',
                'Expanding': 'Growing',
                'Scaling': 'Growing',
                'Stable': 'Established',
                'Well-established': 'Established',
                'Experienced': 'Established',
                'Legacy': 'Mature',
                'Industry Leader': 'Mature',
                'Veteran': 'Mature'
            }
        },
        'tech_sophistication': {
            'valid_options': ['Basic', 'Medium', 'High', 'Advanced'],
            'mappings': {
                'Low': 'Basic',
                'Simple': 'Basic',
                'Minimal': 'Basic',
                'Standard': 'Medium',
                'Average': 'Medium',
                'Moderate': 'Medium',
                'Strong': 'High',
                'Good': 'High',
                'Sophisticated': 'Advanced',
                'Expert': 'Advanced',
                'Cutting-edge': 'Advanced'
            }
        },
        'content_maturity': {
            'valid_options': ['Basic', 'Developing', 'Mature', 'Advanced'],
            'mappings': {
                'Low': 'Basic',
                'Simple': 'Basic',
                'Minimal': 'Basic',
                'Growing': 'Developing',
                'Improving': 'Developing',
                'Established': 'Mature',
                'Strong': 'Mature',
                'Sophisticated': 'Advanced',
                'Expert': 'Advanced',
                'Professional': 'Advanced'
            }
        },
        'competitive_positioning': {
            'valid_options': ['Leader', 'Challenger', 'Follower', 'Niche'],
            'mappings': {
                'Market Leader': 'Leader',
                'Industry Leader': 'Leader',
                'Top Player': 'Leader',
                'Competitor': 'Challenger',
                'Alternative': 'Challenger',
                'Contender': 'Challenger',
                'Me-too': 'Follower',
                'Copycat': 'Follower',
                'Standard': 'Follower',
                'Specialized': 'Niche',
                'Boutique': 'Niche',
                'Specialist': 'Niche'
            }
        },
        'positioning_strength': {
            'valid_options': ['Weak', 'Medium', 'Strong', 'Dominant'],
            'mappings': {
                'Low': 'Weak',
                'Poor': 'Weak',
                'Unclear': 'Weak',
                'Average': 'Medium',
                'Moderate': 'Medium',
                'Good': 'Medium',
                'High': 'Strong',
                'Powerful': 'Strong',
                'Clear': 'Strong',
                'Market Leader': 'Dominant',
                'Unbeatable': 'Dominant',
                'Monopolistic': 'Dominant'
            }
        },
        'brand_strength': {
            'valid_options': ['Weak', 'Medium', 'Strong', 'Very Strong'],
            'mappings': {
                'Low': 'Weak',
                'Poor': 'Weak',
                'Unknown': 'Weak',
                'Average': 'Medium',
                'Moderate': 'Medium',
                'Good': 'Medium',
                'High': 'Strong',
                'Powerful': 'Strong',
                'Excellent': 'Very Strong',
                'Outstanding': 'Very Strong',
                'World-class': 'Very Strong'
            }
        },
        'income_level': {
            'valid_options': ['Budget', 'Mid-Range', 'Premium', 'Luxury'],
            'mappings': {
                'Low': 'Budget',
                'Affordable': 'Budget',
                'Cheap': 'Budget',
                'Economy': 'Budget',
                'Standard': 'Mid-Range',
                'Average': 'Mid-Range',
                'Middle': 'Mid-Range',
                'High': 'Premium',
                'Expensive': 'Premium',
                'Upscale': 'Premium',
                'Elite': 'Luxury',
                'High-end': 'Luxury',
                'Exclusive': 'Luxury'
            }
        },
        'audience_sophistication': {
            'valid_options': ['Basic', 'General', 'Advanced', 'Expert'],
            'mappings': {
                'Low': 'Basic',
                'Simple': 'Basic',
                'Beginner': 'Basic',
                'Standard': 'General',
                'Average': 'General',
                'Mainstream': 'General',
                'High': 'Advanced',
                'Professional': 'Advanced',
                'Technical': 'Advanced',
                'Specialist': 'Expert',
                'Expert-level': 'Expert',
                'Highly Technical': 'Expert'
            }
        },
        'preferred_contact_method': {
            'valid_options': ['Phone', 'Email', 'Form', 'Chat', 'Social'],
            'mappings': {
                'Telephone': 'Phone',
                'Call': 'Phone',
                'Contact Form': 'Form',
                'Web Form': 'Form',
                'Online Form': 'Form',
                'Live Chat': 'Chat',
                'Chat Widget': 'Chat',
                'Messaging': 'Chat',
                'Social Media': 'Social',
                'Facebook': 'Social',
                'Twitter': 'Social'
            }
        },
        'industry_sector': {
            'valid_options': ['Technology', 'Healthcare', 'Finance', 'Education', 'Retail', 'Real Estate', 'Marketing', 'Manufacturing', 'Professional Services', 'Government', 'Non-profit', 'General'],
            'mappings': {
                'Tech': 'Technology',
                'IT': 'Technology',
                'Software': 'Technology',
                'Digital': 'Technology',
                'Medical': 'Healthcare',
                'Health': 'Healthcare',
                'Banking': 'Finance',
                'Financial Services': 'Finance',
                'Insurance': 'Finance',
                'School': 'Education',
                'University': 'Education',
                'Learning': 'Education',
                'E-commerce': 'Retail',
                'Shopping': 'Retail',
                'Store': 'Retail',
                'Property': 'Real Estate',
                'Construction': 'Real Estate',
                'Advertising': 'Marketing',
                'Digital Marketing': 'Marketing',
                'Agency': 'Marketing',
                'Consulting': 'Professional Services',
                'Legal': 'Professional Services',
                'Accounting': 'Professional Services',
                'Business Services': 'Professional Services',
                'Public Sector': 'Government',
                'Municipal': 'Government',
                'Charity': 'Non-profit',
                'Foundation': 'Non-profit'
            }
        },
        'primary_age_group': {
            'valid_options': ['Young Adults', 'Middle Age', 'Seniors', 'General'],
            'mappings': {
                '18-25': 'Young Adults',
                '18-35': 'Young Adults',
                '20-30': 'Young Adults',
                '25-35': 'Young Adults',
                '25-45': 'Middle Age',
                '30-45': 'Middle Age',
                '35-50': 'Middle Age',
                '40-55': 'Middle Age',
                '45-65': 'Middle Age',
                '50+': 'Seniors',
                '55+': 'Seniors',
                '60+': 'Seniors',
                '65+': 'Seniors',
                'Adults': 'General',
                'All Ages': 'General',
                'Mixed': 'General',
                'Broad': 'General',
                'Millennials': 'Young Adults',
                'Gen Z': 'Young Adults',
                'Gen X': 'Middle Age',
                'Baby Boomers': 'Seniors'
            }
        }
    }
    
    def find_best_semantic_match(ai_value, valid_options, field_name):
        """
        Find the best semantic match for an AI-generated value using intelligent analysis.
        """
        ai_value_lower = ai_value.lower().strip()
        
        # For business model, use semantic reasoning
        if field_name == 'business_model':
            if any(word in ai_value_lower for word in ['service', 'agency', 'consulting', 'professional']):
                return 'Professional Services'
            elif any(word in ai_value_lower for word in ['information', 'content', 'news', 'media', 'blog']):
                return 'Information/Content'
            elif any(word in ai_value_lower for word in ['software', 'saas', 'platform', 'tech']):
                return 'SaaS'
            elif any(word in ai_value_lower for word in ['store', 'shop', 'retail', 'ecommerce', 'e-commerce']):
                return 'E-commerce'
            elif any(word in ai_value_lower for word in ['local', 'neighborhood']):
                return 'Local Services'
            elif any(word in ai_value_lower for word in ['subscription', 'recurring']):
                return 'Subscription'
            elif any(word in ai_value_lower for word in ['marketplace', 'platform']):
                return 'Marketplace'
            elif any(word in ai_value_lower for word in ['non-profit', 'nonprofit', 'charity']):
                return 'Non-profit'
        
        # For target market, use context clues
        elif field_name == 'target_market':
            if any(phrase in ai_value_lower for phrase in ['b2c', 'consumer', 'individual', 'personal']):
                return 'B2C'
            else:
                # Default to B2B for mixed/hybrid cases or when B2B indicators are present
                return 'B2B'
        
        # For company size, analyze scale indicators
        elif field_name == 'company_size':
            if any(word in ai_value_lower for word in ['startup', 'new', 'early', 'solo', 'individual']):
                return 'Startup'
            elif any(word in ai_value_lower for word in ['small', 'smb', 'local']):
                return 'Small'
            elif any(word in ai_value_lower for word in ['medium', 'mid', 'growing', 'sme']):
                return 'Medium'
            elif any(word in ai_value_lower for word in ['large', 'big', 'corporation']):
                return 'Large'
            elif any(word in ai_value_lower for word in ['enterprise', 'global', 'multinational', 'fortune']):
                return 'Enterprise'
        
        # For geographic scope, analyze reach indicators
        elif field_name == 'geographic_scope':
            if any(word in ai_value_lower for word in ['local', 'city', 'neighborhood']):
                return 'Local'
            elif any(word in ai_value_lower for word in ['regional', 'state', 'metro']):
                return 'Regional'
            elif any(word in ai_value_lower for word in ['national', 'country', 'singapore']):
                return 'National'
            elif any(word in ai_value_lower for word in ['global', 'international', 'worldwide', 'usa']):
                return 'Global'
        
        # For maturity levels, analyze stage indicators
        elif field_name in ['business_maturity', 'content_maturity']:
            if any(word in ai_value_lower for word in ['startup', 'new', 'early', 'young']):
                return 'Startup' if field_name == 'business_maturity' else 'Basic'
            elif any(word in ai_value_lower for word in ['growing', 'developing', 'improving', 'expanding']):
                return 'Growing' if field_name == 'business_maturity' else 'Developing'
            elif any(word in ai_value_lower for word in ['established', 'stable', 'mature', 'strong']):
                return 'Established' if field_name == 'business_maturity' else 'Mature'
            elif any(word in ai_value_lower for word in ['mature', 'legacy', 'veteran', 'advanced', 'sophisticated']):
                return 'Mature' if field_name == 'business_maturity' else 'Advanced'
        
        # For sophistication levels, analyze complexity indicators  
        elif field_name in ['tech_sophistication', 'audience_sophistication']:
            if any(word in ai_value_lower for word in ['basic', 'low', 'simple', 'minimal', 'beginner']):
                return 'Basic'
            elif any(word in ai_value_lower for word in ['medium', 'standard', 'average', 'moderate', 'general']):
                return 'Medium' if field_name == 'tech_sophistication' else 'General'
            elif any(word in ai_value_lower for word in ['high', 'strong', 'good', 'professional', 'advanced']):
                return 'High' if field_name == 'tech_sophistication' else 'Advanced'
            elif any(word in ai_value_lower for word in ['advanced', 'expert', 'sophisticated', 'cutting']):
                return 'Advanced' if field_name == 'tech_sophistication' else 'Expert'
        
        # For strength/positioning fields, analyze power indicators
        elif field_name in ['positioning_strength', 'brand_strength']:
            if any(word in ai_value_lower for word in ['weak', 'low', 'poor', 'unclear', 'unknown']):
                return 'Weak'
            elif any(word in ai_value_lower for word in ['medium', 'average', 'moderate', 'good']):
                return 'Medium'
            elif any(word in ai_value_lower for word in ['strong', 'high', 'powerful', 'clear']):
                return 'Strong'
            elif any(word in ai_value_lower for word in ['dominant', 'leader', 'unbeatable', 'excellent', 'outstanding']):
                return 'Dominant' if field_name == 'positioning_strength' else 'Very Strong'
        
        # For competitive positioning, analyze market position
        elif field_name == 'competitive_positioning':
            if any(word in ai_value_lower for word in ['leader', 'top', 'market leader', 'industry leader']):
                return 'Leader'
            elif any(word in ai_value_lower for word in ['challenger', 'competitor', 'alternative', 'contender']):
                return 'Challenger'
            elif any(word in ai_value_lower for word in ['niche', 'specialized', 'boutique', 'specialist']):
                return 'Niche'
            elif any(word in ai_value_lower for word in ['follower', 'standard', 'copycat']):
                return 'Follower'
        
        # For income level, analyze price indicators
        elif field_name == 'income_level':
            if any(word in ai_value_lower for word in ['budget', 'low', 'affordable', 'cheap', 'economy']):
                return 'Budget'
            elif any(word in ai_value_lower for word in ['mid', 'standard', 'average', 'middle']):
                return 'Mid-Range'
            elif any(word in ai_value_lower for word in ['premium', 'high', 'expensive', 'upscale']):
                return 'Premium'
            elif any(word in ai_value_lower for word in ['luxury', 'elite', 'exclusive']):
                return 'Luxury'
        
        # For contact method, analyze communication preferences  
        elif field_name == 'preferred_contact_method':
            if any(word in ai_value_lower for word in ['phone', 'call', 'telephone']):
                return 'Phone'
            elif any(word in ai_value_lower for word in ['email', 'mail']):
                return 'Email'
            elif any(word in ai_value_lower for word in ['form', 'contact form', 'web form']):
                return 'Form'
            elif any(word in ai_value_lower for word in ['chat', 'messaging', 'live chat']):
                return 'Chat'
            elif any(word in ai_value_lower for word in ['social', 'facebook', 'twitter']):
                return 'Social'
        
        # For industry sector, analyze business domain
        elif field_name == 'industry_sector':
            if any(word in ai_value_lower for word in ['technology', 'tech', 'software', 'digital', 'it', 'computing']):
                return 'Technology'
            elif any(word in ai_value_lower for word in ['healthcare', 'health', 'medical', 'wellness', 'fitness']):
                return 'Healthcare'
            elif any(word in ai_value_lower for word in ['finance', 'financial', 'banking', 'insurance', 'investment']):
                return 'Finance'
            elif any(word in ai_value_lower for word in ['education', 'school', 'university', 'learning', 'training']):
                return 'Education'
            elif any(word in ai_value_lower for word in ['retail', 'shopping', 'store', 'ecommerce', 'e-commerce']):
                return 'Retail'
            elif any(word in ai_value_lower for word in ['real estate', 'property', 'construction', 'housing']):
                return 'Real Estate'
            elif any(word in ai_value_lower for word in ['marketing', 'advertising', 'agency', 'promotion']):
                return 'Marketing'
            elif any(word in ai_value_lower for word in ['manufacturing', 'production', 'industrial', 'factory']):
                return 'Manufacturing'
            elif any(word in ai_value_lower for word in ['consulting', 'professional services', 'legal', 'accounting']):
                return 'Professional Services'
            elif any(word in ai_value_lower for word in ['government', 'public', 'municipal', 'civic']):
                return 'Government'
            elif any(word in ai_value_lower for word in ['non-profit', 'nonprofit', 'charity', 'foundation']):
                return 'Non-profit'
        
        # For primary age group, analyze age indicators
        elif field_name == 'primary_age_group':
            # Check for specific age ranges
            if any(age_range in ai_value_lower for age_range in ['18-25', '18-35', '20-30', '25-35']) or any(word in ai_value_lower for word in ['young', 'millennials', 'gen z']):
                return 'Young Adults'
            elif any(age_range in ai_value_lower for age_range in ['25-45', '30-45', '35-50', '40-55', '45-65']) or any(word in ai_value_lower for word in ['middle', 'gen x', 'working']):
                return 'Middle Age'
            elif any(age_range in ai_value_lower for age_range in ['50+', '55+', '60+', '65+']) or any(word in ai_value_lower for word in ['senior', 'elderly', 'retired', 'baby boomers']):
                return 'Seniors'
            elif any(word in ai_value_lower for word in ['general', 'all ages', 'broad', 'mixed', 'adults']):
                return 'General'
        
        # If no semantic match found, return the most general/neutral option
        if len(valid_options) >= 2:
            return valid_options[1]  # Usually the second option is more neutral
        return valid_options[0]  # Fallback to first option
    
    mapped_data = enhanced_data.copy()
    
    # Apply intelligent mappings for each field
    for field_name, config in airtable_mappings.items():
        if field_name in mapped_data:
            current_value = str(mapped_data[field_name]).strip()
            
            # First check if it's already a valid option
            if current_value in config['valid_options']:
                continue
                
            # Try to find a predefined mapping
            mapped_value = config['mappings'].get(current_value)
            if mapped_value:
                mapped_data[field_name] = mapped_value
                print(f"    🔄 Mapped '{current_value}' -> '{mapped_value}' for {field_name}")
            else:
                # Use intelligent semantic matching
                smart_match = find_best_semantic_match(current_value, config['valid_options'], field_name)
                mapped_data[field_name] = smart_match
                print(f"    🧠 Smart match '{current_value}' -> '{smart_match}' for {field_name}")
    
    return mapped_data

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
            print(f"\t⚠️  No GSC data found for URL: {url}")
            print(f"\t   Possible reasons:")
            print(f"\t   - Website is new (no search traffic yet)")
            print(f"\t   - URL not properly verified in GSC")
            print(f"\t   - Different property type needed (domain vs URL prefix)")
            print(f"\t   - No search traffic in the selected time period ({days} days)")
            print(f"\t   - Website not indexed by Google yet")
            print(f"\t   ✅ Continuing with other metrics...")
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
            'business_analysis': airtable.table(base_id, 'Business_Analysis'),
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
        print(f"\t\tStarting Airtable update process for {url}")
        print(f"\t\tAnalysis date: {analysis_date}")
        
        # Find or create website record
        website_record = None
        websites_records = tables['websites'].all()
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
        
        # Update Core Metrics
        try:
            print(f"\n\t\t--- Updating CORE_METRICS ---")
            result = tables['core_metrics'].create(core_metrics_data)
            print(f"\t\t✓ SUCCESS: Updated Core Metrics - Record ID: {result['id']}")
            successful_updates += 1
        except Exception as e:
            print(f"\t\t✗ FAILED to update Core Metrics: {e}")
            failed_updates += 1
        
        # Update Performance Metrics
        try:
            print(f"\n\t\t--- Updating PERFORMANCE_METRICS ---")
            result = tables['performance_metrics'].create(performance_data)
            print(f"\t\t✓ SUCCESS: Updated Performance Metrics - Record ID: {result['id']}")
            successful_updates += 1
        except Exception as e:
            print(f"\t\t✗ FAILED to update Performance Metrics: {e}")
            failed_updates += 1
        
        # Update Keyword Analysis
        try:
            print(f"\n\t\t--- Updating KEYWORD_ANALYSIS ---")
            result = tables['keyword_analysis'].create(keyword_data)
            print(f"\t\t✓ SUCCESS: Updated Keyword Analysis - Record ID: {result['id']}")
            successful_updates += 1
        except Exception as e:
            print(f"\t\t✗ FAILED to update Keyword Analysis: {e}")
            failed_updates += 1

        # Update Mobile Usability
        try:
            print(f"\n\t\t--- Updating MOBILE_USABILITY ---")
            result = tables['mobile_usability'].create(mobile_data)
            print(f"\t\t✓ SUCCESS: Updated Mobile Usability - Record ID: {result['id']}")
            successful_updates += 1
        except Exception as e:
            print(f"\t\t✗ FAILED to update Mobile Usability: {e}")
            failed_updates += 1

        # Update Sitemap Data
        try:
            print(f"\n\t\t--- Updating SITEMAP_DATA ---")
            result = tables['sitemap_data'].create(sitemap_data)
            print(f"\t\t✓ SUCCESS: Updated Sitemap Data - Record ID: {result['id']}")
            successful_updates += 1
        except Exception as e:
            print(f"\t\t✗ FAILED to update Sitemap Data: {e}")
            failed_updates += 1

        # Update Index Technical
        try:
            print(f"\n\t\t--- Updating INDEX_TECHNICAL ---")
            result = tables['index_technical'].create(index_data)
            print(f"\t\t✓ SUCCESS: Updated Index Technical - Record ID: {result['id']}")
            successful_updates += 1
        except Exception as e:
            print(f"\t\t✗ FAILED to update Index Technical: {e}")
            failed_updates += 1

        # Update Business Analysis
        try:
            print(f"\n\t\t--- Updating BUSINESS_ANALYSIS ---")
            result = tables['business_analysis'].create(business_data)
            print(f"\t\t✓ SUCCESS: Updated Business Analysis - Record ID: {result['id']}")
            successful_updates += 1
        except Exception as e:
            print(f"\t\t✗ FAILED to update Business Analysis: {e}")
            failed_updates += 1
        
        print(f"\n\t\tUpdate Summary: {successful_updates} successful, {failed_updates} failed")
        
        # Update last analyzed timestamp in main websites table
        try:
            tables['websites'].update(website_id, {'last_analyzed': analysis_date})
            print(f"\t\t✓ Updated last_analyzed timestamp in main table")
        except Exception as e:
            print(f"\t\t✗ Failed to update last_analyzed timestamp: {e}")
        
        # Return success only if at least some tables were updated
        success = successful_updates > 0
        if success:
            print(f"\t\t🎉 OVERALL SUCCESS: {successful_updates} tables updated!")
        else:
            print(f"\t\t💥 OVERALL FAILURE: No tables were updated!")
        
        return success
        
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
            'last_crawl_time': str(last_crawl_time).strip() if last_crawl_time else None,
            'page_fetch_state': str(page_fetch_state).replace('"', '').strip()
        }
        
    except Exception as e:
        print(f"\t✗ Error fetching URL inspection for {url}: {e}")
        return {
            'index_verdict': 'ERROR',
            'coverage_state': 'ERROR',
            'robots_txt_state': 'ERROR', 
            'indexing_state': 'ERROR',
            'last_crawl_time': None,
            'page_fetch_state': 'ERROR'
        }

def get_business_analysis(url):
    """
    Analyze a website's business context using the BusinessAnalyzer class.
    
    Args:
        url (str): The URL of the website to analyze
        
    Returns:
        dict: Business analysis data including model, target market, and recommendations
    """
    try:
        analyzer = BusinessAnalyzer()
        business_data = analyzer.analyze_business(url)
        return business_data
    except Exception as e:
        print(f"Error analyzing business context: {str(e)}")
        return analyzer._get_default_business_data()

def enhance_business_analysis_with_ai(initial_business_data, technical_metrics):
    """
    Enhance business analysis using GPT-4o-mini to make intelligent assumptions
    and improve data quality for Airtable storage.
    
    Args:
        initial_business_data (dict): Initial business analysis from BusinessAnalyzer
        technical_metrics (dict): Technical performance and feature data
        
    Returns:
        dict: Enhanced business analysis with AI improvements
    """
    try:
        print(f"\n🤖 Enhancing business analysis with AI...")
        
        # Load enhancement prompt template
        prompt_file_path = os.path.join(os.path.dirname(__file__), 'prompts', 'business_analysis_enhancement.txt')
        
        with open(prompt_file_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
        
        # Format the prompt with available data
        prompt = prompt_template.format(
            url=technical_metrics.get('url', 'N/A'),
            
            # Initial business analysis
            business_model=initial_business_data.get('business_model', 'Unknown'),
            target_market=initial_business_data.get('target_market', 'Unknown'),
            industry_sector=initial_business_data.get('industry_sector', 'Unknown'),
            company_size=initial_business_data.get('company_size', 'Unknown'),
            geographic_scope=initial_business_data.get('geographic_scope', 'Unknown'),
            business_maturity=initial_business_data.get('business_maturity', 'Unknown'),
            platform_detected=initial_business_data.get('platform_detected', 'Unknown'),
            tech_sophistication=initial_business_data.get('tech_sophistication', 'Unknown'),
            content_maturity=initial_business_data.get('content_maturity', 'Unknown'),
            competitive_positioning=initial_business_data.get('competitive_positioning', 'Unknown'),
            services_offered=initial_business_data.get('services_offered', 'Not specified'),
            
            # Technical context
            performance_score=technical_metrics.get('performance_score', 'N/A'),
            mobile_friendly_status=technical_metrics.get('mobile_friendly_status', 'N/A'),
            has_ecommerce=initial_business_data.get('has_ecommerce', False),
            has_local_presence=initial_business_data.get('has_local_presence', False),
            has_content_marketing=initial_business_data.get('has_content_marketing', False),
            has_lead_generation=initial_business_data.get('has_lead_generation', False),
            has_social_proof=initial_business_data.get('has_social_proof', False),
            social_media_integration=initial_business_data.get('social_media_integration', False),
            has_advanced_features=initial_business_data.get('has_advanced_features', False)
        )
        
        # Call OpenAI API
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a business intelligence analyst. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent analysis
            max_tokens=2500
        )
        
        # Parse JSON response
        ai_analysis = response.choices[0].message.content
        
        # Clean up the response to ensure it's valid JSON
        if ai_analysis.startswith('```json'):
            ai_analysis = ai_analysis.replace('```json', '').replace('```', '').strip()
        
        try:
            enhanced_data = json.loads(ai_analysis)
            print(f"✓ AI enhancement completed successfully")
            
            # Merge enhanced data back into the original structure
            enhanced_business_data = initial_business_data.copy()
            
            # Update with AI enhancements (remove reasoning fields for storage)
            for key, value in enhanced_data.items():
                if not key.endswith('_reasoning'):
                    enhanced_business_data[key] = value
            
            # Add special AI insights
            if 'business_insights' in enhanced_data:
                enhanced_business_data['business_insights'] = enhanced_data['business_insights']
            if 'seo_strategy_recommendations' in enhanced_data:
                enhanced_business_data['seo_strategy_recommendations'] = enhanced_data['seo_strategy_recommendations']
            
            return enhanced_business_data
            
        except json.JSONDecodeError as e:
            print(f"⚠️ Failed to parse AI response as JSON: {e}")
            print(f"Raw response: {ai_analysis[:200]}...")
            return initial_business_data
            
    except FileNotFoundError:
        print(f"Error: Enhancement prompt file not found at {prompt_file_path}")
        return initial_business_data
    except Exception as e:
        print(f"❌ Error enhancing business analysis: {str(e)}")
        return initial_business_data

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
        # Initialize OpenAI
        openai.api_key = os.getenv('OPENAI_API_KEY')
        
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
        
        # Initialize report generator
        report_generator = ReportGenerator()
        
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
            business_analysis = get_business_analysis(url)
            
            # Enhance business analysis with AI
            technical_context = {
                'url': url,
                'performance_score': psi_metrics.get('performance_score', 0),
                'mobile_friendly_status': mobile_test.get('mobile_friendly_status', 'Unknown')
            }
            enhanced_business_analysis = enhance_business_analysis_with_ai(business_analysis, technical_context)
            
            # Map AI values to valid Airtable options to prevent 422 errors
            print(f"  🔧 Mapping enhanced business analysis to Airtable options...")
            enhanced_business_analysis = map_ai_values_to_airtable_options(enhanced_business_analysis)
            
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
                
                # Enhanced business analysis (AI-improved)
                'business_model': enhanced_business_analysis.get('business_model', ''),
                'target_market': enhanced_business_analysis.get('target_market', ''),
                'industry_sector': enhanced_business_analysis.get('industry_sector', ''),
                'company_size': enhanced_business_analysis.get('company_size', ''),
                'has_ecommerce': enhanced_business_analysis.get('has_ecommerce', False),
                'has_local_presence': enhanced_business_analysis.get('has_local_presence', False),
                'business_complexity_score': enhanced_business_analysis.get('business_complexity_score', 0),
                'primary_age_group': enhanced_business_analysis.get('primary_age_group', ''),
                'income_level': enhanced_business_analysis.get('income_level', ''),
                'audience_sophistication': enhanced_business_analysis.get('audience_sophistication', ''),
                'services_offered': enhanced_business_analysis.get('services_offered', ''),
                'has_public_pricing': enhanced_business_analysis.get('has_public_pricing', False),
                'service_count': enhanced_business_analysis.get('service_count', 0),
                'geographic_scope': enhanced_business_analysis.get('geographic_scope', ''),
                'target_locations': enhanced_business_analysis.get('target_locations', ''),
                'is_location_based': enhanced_business_analysis.get('is_location_based', False),
                'business_maturity': enhanced_business_analysis.get('business_maturity', ''),
                'establishment_year': enhanced_business_analysis.get('establishment_year', 0) if enhanced_business_analysis.get('establishment_year') else None,
                'experience_indicators': enhanced_business_analysis.get('experience_indicators', False),
                'platform_detected': enhanced_business_analysis.get('platform_detected', ''),
                'has_advanced_features': enhanced_business_analysis.get('has_advanced_features', False),
                'social_media_integration': enhanced_business_analysis.get('social_media_integration', False),
                'tech_sophistication': enhanced_business_analysis.get('tech_sophistication', ''),
                'has_content_marketing': enhanced_business_analysis.get('has_content_marketing', False),
                'has_lead_generation': enhanced_business_analysis.get('has_lead_generation', False),
                'has_social_proof': enhanced_business_analysis.get('has_social_proof', False),
                'content_maturity': enhanced_business_analysis.get('content_maturity', ''),
                'phone_prominence': enhanced_business_analysis.get('phone_prominence', False),
                'has_contact_forms': enhanced_business_analysis.get('has_contact_forms', False),
                'has_live_chat': enhanced_business_analysis.get('has_live_chat', False),
                'preferred_contact_method': enhanced_business_analysis.get('preferred_contact_method', ''),
                'competitive_positioning': enhanced_business_analysis.get('competitive_positioning', ''),
                'positioning_strength': enhanced_business_analysis.get('positioning_strength', ''),
                'value_proposition': enhanced_business_analysis.get('value_proposition', ''),
                'brand_strength': enhanced_business_analysis.get('brand_strength', ''),
                'trust_indicators': enhanced_business_analysis.get('trust_indicators', ''),
                'business_insights': enhanced_business_analysis.get('business_insights', 'No specific insights available'),
                'seo_strategy_recommendations': enhanced_business_analysis.get('seo_strategy_recommendations', 'No existing recommendations'),
            }
            
            # Generate OpenAI analysis (using enhanced business data)
            try:
                openai_analysis = generate_seo_analysis(combined_metrics, enhanced_business_analysis)
                
                # Generate and send report
                recipient_email = record['fields'].get('contact_email')
                recipient_name = record['fields'].get('contact_name', 'Valued Client')
                
                if recipient_email:
                    print(f"\nGenerating and sending report to {recipient_email}...")
                    report_generator.generate_and_send_report(
                        website_data=combined_metrics,
                        openai_analysis=openai_analysis,
                        recipient_email=recipient_email,
                        recipient_name=recipient_name
                    )
                    print("✅ Report sent successfully!")
                else:
                    print("⚠️  No contact email found for report delivery")
        
            except Exception as e:
                print(f"❌ Error generating report: {str(e)}")
            
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

def generate_seo_analysis(metrics, business_analysis):
    """Generate SEO analysis using OpenAI."""
    try:
        # Load prompt template from file
        prompt_file_path = os.path.join(os.path.dirname(__file__), 'prompts', 'seo_analysis_prompt.txt')
        
        with open(prompt_file_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
        
        # Format the prompt with actual data
        prompt = prompt_template.format(
            # Website Overview
            url=metrics['url'],
            
            # Core SEO Metrics
            impressions=metrics.get('impressions', 'N/A'),
            clicks=metrics.get('clicks', 'N/A'),
            ctr=metrics.get('ctr', 'N/A'),
            average_position=metrics.get('average_position', 'N/A'),
            
            # Technical Performance
            performance_score=metrics.get('performance_score', 'N/A'),
            first_contentful_paint=metrics.get('first_contentful_paint', 'N/A'),
            largest_contentful_paint=metrics.get('largest_contentful_paint', 'N/A'),
            speed_index=metrics.get('speed_index', 'N/A'),
            time_to_interactive=metrics.get('time_to_interactive', 'N/A'),
            total_blocking_time=metrics.get('total_blocking_time', 'N/A'),
            cumulative_layout_shift=metrics.get('cumulative_layout_shift', 'N/A'),
            
            # Mobile Usability
            mobile_friendly_status=metrics.get('mobile_friendly_status', 'N/A'),
            mobile_friendly_issues_count=metrics.get('mobile_friendly_issues_count', 'N/A'),
            mobile_friendly_issues=metrics.get('mobile_friendly_issues', 'N/A'),
            mobile_test_loading_state=metrics.get('mobile_test_loading_state', 'N/A'),
            mobile_passed=metrics.get('mobile_passed', 'N/A'),
            
            # Keyword Analysis
            top_keywords=metrics.get('top_keywords', 'N/A'),
            total_keywords_tracked=metrics.get('total_keywords_tracked', 'N/A'),
            avg_keyword_position=metrics.get('avg_keyword_position', 'N/A'),
            high_opportunity_keywords=metrics.get('high_opportunity_keywords', 'N/A'),
            branded_keywords_count=metrics.get('branded_keywords_count', 'N/A'),
            keyword_cannibalization_risk=metrics.get('keyword_cannibalization_risk', 'N/A'),
            
            # Sitemap & Indexing
            sitemaps_submitted=metrics.get('sitemaps_submitted', 'N/A'),
            sitemap_count=metrics.get('sitemap_count', 'N/A'),
            sitemap_errors=metrics.get('sitemap_errors', 'N/A'),
            sitemap_warnings=metrics.get('sitemap_warnings', 'N/A'),
            last_submission=metrics.get('last_submission', 'N/A'),
            index_verdict=metrics.get('index_verdict', 'N/A'),
            coverage_state=metrics.get('coverage_state', 'N/A'),
            robots_txt_state=metrics.get('robots_txt_state', 'N/A'),
            indexing_state=metrics.get('indexing_state', 'N/A'),
            last_crawl_time=metrics.get('last_crawl_time', 'N/A'),
            page_fetch_state=metrics.get('page_fetch_state', 'N/A'),
            
            # Business Intelligence
            business_model=metrics.get('business_model', 'Unknown'),
            target_market=metrics.get('target_market', 'Unknown'),
            industry_sector=metrics.get('industry_sector', 'Unknown'),
            company_size=metrics.get('company_size', 'Unknown'),
            geographic_scope=metrics.get('geographic_scope', 'Unknown'),
            target_locations=metrics.get('target_locations', 'Unknown'),
            has_ecommerce=metrics.get('has_ecommerce', 'Unknown'),
            has_local_presence=metrics.get('has_local_presence', 'Unknown'),
            is_location_based=metrics.get('is_location_based', 'Unknown'),
            business_complexity_score=metrics.get('business_complexity_score', 'Unknown'),
            primary_age_group=metrics.get('primary_age_group', 'Unknown'),
            income_level=metrics.get('income_level', 'Unknown'),
            audience_sophistication=metrics.get('audience_sophistication', 'Unknown'),
            services_offered=metrics.get('services_offered', 'Not specified'),
            service_count=metrics.get('service_count', 'Unknown'),
            has_public_pricing=metrics.get('has_public_pricing', 'Unknown'),
            business_maturity=metrics.get('business_maturity', 'Unknown'),
            establishment_year=metrics.get('establishment_year', 'Unknown'),
            experience_indicators=metrics.get('experience_indicators', 'Unknown'),
            platform_detected=metrics.get('platform_detected', 'Unknown'),
            has_advanced_features=metrics.get('has_advanced_features', 'Unknown'),
            social_media_integration=metrics.get('social_media_integration', 'Unknown'),
            tech_sophistication=metrics.get('tech_sophistication', 'Unknown'),
            has_content_marketing=metrics.get('has_content_marketing', 'Unknown'),
            has_lead_generation=metrics.get('has_lead_generation', 'Unknown'),
            has_social_proof=metrics.get('has_social_proof', 'Unknown'),
            content_maturity=metrics.get('content_maturity', 'Unknown'),
            phone_prominence=metrics.get('phone_prominence', 'Unknown'),
            has_contact_forms=metrics.get('has_contact_forms', 'Unknown'),
            has_live_chat=metrics.get('has_live_chat', 'Unknown'),
            preferred_contact_method=metrics.get('preferred_contact_method', 'Unknown'),
            competitive_positioning=metrics.get('competitive_positioning', 'Unknown'),
            positioning_strength=metrics.get('positioning_strength', 'Unknown'),
            value_proposition=metrics.get('value_proposition', 'Unknown'),
            brand_strength=metrics.get('brand_strength', 'Unknown'),
            trust_indicators=metrics.get('trust_indicators', 'Unknown'),
            business_insights=metrics.get('business_insights', 'No specific insights available'),
            seo_strategy_recommendations=metrics.get('seo_strategy_recommendations', 'No existing recommendations')
        )
        
        # Call OpenAI API
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a business intelligence analyst. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent analysis
            max_tokens=2500
        )
        
        # Parse JSON response
        ai_analysis = response.choices[0].message.content
        
        # Clean up the response to ensure it's valid JSON
        if ai_analysis.startswith('```json'):
            ai_analysis = ai_analysis.replace('```json', '').replace('```', '').strip()
        
        try:
            seo_analysis = json.loads(ai_analysis)
            print(f"✓ SEO analysis generated successfully")
            return seo_analysis
            
        except json.JSONDecodeError as e:
            print(f"⚠️ Failed to parse AI response as JSON: {e}")
            print(f"Raw response: {ai_analysis[:200]}...")
            return {"error": "Failed to parse AI analysis"}
            
    except FileNotFoundError:
        print(f"Error: SEO analysis prompt file not found at {prompt_file_path}")
        return {"error": "Prompt file not found"}
    except Exception as e:
        print(f"❌ Error generating SEO analysis: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    main()
