#!/usr/bin/env python3
"""
Airtable Connection Diagnostic Tool
Tests your Airtable setup and identifies potential issues
"""

import os
from dotenv import load_dotenv
from pyairtable import Api

# Load environment variables
load_dotenv()

def test_airtable_setup():
    """Test Airtable connection and table setup."""
    print("🔍 AIRTABLE DIAGNOSTIC TEST")
    print("=" * 50)
    
    # Check environment variables
    print("\n1. Checking environment variables...")
    api_key = os.getenv('AIRTABLE_API_KEY')
    base_id = os.getenv('AIRTABLE_BASE_ID')
    use_organized = os.getenv('USE_ORGANIZED_TABLES', 'false').lower() == 'true'
    
    print(f"   AIRTABLE_API_KEY: {'✅ Set' if api_key else '❌ Missing'}")
    print(f"   AIRTABLE_BASE_ID: {'✅ Set' if base_id else '❌ Missing'}")
    print(f"   USE_ORGANIZED_TABLES: {use_organized}")
    
    if not api_key or not base_id:
        print("\n❌ Missing required environment variables!")
        return False
    
    # Test connection
    print("\n2. Testing Airtable connection...")
    try:
        airtable = Api(api_key)
        print("   ✅ API connection successful")
    except Exception as e:
        print(f"   ❌ API connection failed: {e}")
        return False
    
    # Test table connections
    print("\n3. Testing table connections...")
    required_tables = [
        'Websites',
        'Core_Metrics',
        'Performance_Metrics', 
        'Index_Technical',
        'Sitemap_Data',
        'Mobile_Usability',
        'Keyword_Analysis',
        'Business_Analysis'
    ]
    
    table_status = {}
    for table_name in required_tables:
        try:
            table = airtable.table(base_id, table_name)
            records = table.all()
            table_status[table_name] = {
                'status': 'success',
                'count': len(records),
                'error': None
            }
            print(f"   ✅ {table_name}: {len(records)} records")
        except Exception as e:
            table_status[table_name] = {
                'status': 'error',
                'count': 0,
                'error': str(e)
            }
            print(f"   ❌ {table_name}: {e}")
    
    # Check Websites table content
    print("\n4. Checking Websites table content...")
    if table_status['Websites']['status'] == 'success':
        try:
            websites_table = airtable.table(base_id, 'Websites')
            websites_records = websites_table.all()
            
            if len(websites_records) == 0:
                print("   ⚠️  Websites table is EMPTY!")
                print("      You need to add websites to analyze first.")
            else:
                print(f"   ✅ Found {len(websites_records)} websites:")
                for i, record in enumerate(websites_records[:5], 1):
                    url = record['fields'].get('url', 'NO URL FIELD')
                    print(f"      {i}. {url}")
                if len(websites_records) > 5:
                    print(f"      ... and {len(websites_records) - 5} more")
        except Exception as e:
            print(f"   ❌ Error reading Websites table: {e}")
    
    # Test field types for Business_Analysis (if it exists)
    print("\n5. Testing Business_Analysis table field types...")
    if table_status['Business_Analysis']['status'] == 'success':
        try:
            business_table = airtable.table(base_id, 'Business_Analysis')
            websites_table = airtable.table(base_id, 'Websites')
            websites = websites_table.all()
            
            if not websites:
                print("   ⚠️  Cannot test URL field - Websites table is empty!")
                print("      Add some websites to the Websites table first.")
            else:
                # Try to create a test record with URL relationship
                test_website_id = websites[0]['id']
                test_data = {
                    'url': [test_website_id],  # This should be a relationship field
                    'business_model': 'E-commerce',  # Use valid select option
                    'target_market': 'B2C',
                    'industry_sector': 'Technology',
                    'company_size': 'Small',
                    'has_ecommerce': True,  # This should be a boolean
                    'has_local_presence': False,
                    'business_complexity_score': 5,
                    'primary_age_group': 'General',
                    'income_level': 'Mid-Range',
                    'audience_sophistication': 'General',
                    'geographic_scope': 'National',
                    'business_maturity': 'Growing',
                    'platform_detected': 'Unknown',
                    'tech_sophistication': 'Medium',
                    'content_maturity': 'Basic',
                    'preferred_contact_method': 'Email',
                    'competitive_positioning': 'Follower',
                    'positioning_strength': 'Medium',
                    'brand_strength': 'Medium',
                    'analysis_date': '2024-06-06T12:00:00.000000'
                }
                
                print("   Testing field types with sample data...")
                print(f"   Using website ID: {test_website_id}")
                print("   (This will create a test record - you can delete it)")
                
                result = business_table.create(test_data)
                print(f"   ✅ Field types are correctly configured!")
                print(f"   ✅ URL field accepts relationship data correctly!")
                print(f"   Test record created with ID: {result['id']}")
                
                # Try to delete the test record
                try:
                    business_table.delete(result['id'])
                    print("   ✅ Test record deleted successfully")
                except:
                    print("   ⚠️  Could not delete test record - please delete manually")
                
        except Exception as e:
            print(f"   ❌ Field type error: {e}")
            error_str = str(e)
            if 'INVALID_VALUE_FOR_COLUMN' in error_str:
                if 'url' in error_str.lower():
                    print("      💡 URL field error - this means your 'url' field is not set as 'Link to another record'!")
                    print("      Follow the fix_business_analysis_url.md guide to fix the URL field.")
                else:
                    print("      💡 This means your boolean fields are not set as 'Checkbox' type!")
                    print("      Follow the Business_Analysis_Setup.md guide to fix field types.")
            elif 'INVALID_MULTIPLE_CHOICE_OPTIONS' in error_str:
                print("      💡 Single select field error - your select fields don't have the required options!")
                print("      Follow the Business_Analysis_Setup.md guide to configure select field options.")
                print("      Or enable 'Allow users to add new options' in your select field settings.")
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 DIAGNOSTIC SUMMARY")
    
    success_count = sum(1 for table in table_status.values() if table['status'] == 'success')
    total_count = len(table_status)
    
    if success_count == total_count:
        print(f"✅ All {total_count} tables are working correctly!")
        print("   Your Airtable setup appears to be ready.")
    else:
        print(f"⚠️  {success_count}/{total_count} tables are working")
        print("   Issues found:")
        for table_name, status in table_status.items():
            if status['status'] == 'error':
                print(f"   - {table_name}: {status['error']}")
        print("\n   Please fix these issues before running the main script.")
    
    return success_count == total_count

if __name__ == "__main__":
    test_airtable_setup() 