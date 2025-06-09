#!/usr/bin/env python3
"""
Organized Tables Debug Tool
Diagnoses issues with the organized multi-table structure and website matching
"""

import os
from dotenv import load_dotenv
from pyairtable import Api
from datetime import datetime

# Load environment variables
load_dotenv()

def debug_organized_tables():
    """Debug the organized tables setup and identify issues."""
    print("🔍 ORGANIZED TABLES DEBUG TOOL")
    print("=" * 60)
     
    # Check environment
    api_key = os.getenv('AIRTABLE_API_KEY')
    base_id = os.getenv('AIRTABLE_BASE_ID')
    use_organized = os.getenv('USE_ORGANIZED_TABLES', 'false').lower() == 'true'
    
    print(f"\n1. Environment Check:")
    print(f"   USE_ORGANIZED_TABLES: {use_organized}")
    
    if not use_organized:
        print("   ⚠️  WARNING: USE_ORGANIZED_TABLES is not set to 'true'!")
        print("      Your script will use single table mode instead of organized tables.")
        print("      Set USE_ORGANIZED_TABLES=true in your .env file")
        return False
    
    if not api_key or not base_id:
        print("   ❌ Missing API key or Base ID")
        return False
    
    try:
        airtable = Api(api_key)
        
        # Test all organized tables
        print(f"\n2. Testing Organized Table Connections:")
        tables = {}
        table_names = [
            'Websites',
            'Core_Metrics', 
            'Performance_Metrics',
            'Index_Technical',
            'Sitemap_Data',
            'Mobile_Usability', 
            'Keyword_Analysis',
            'Business_Analysis'
        ]
        
        for table_name in table_names:
            try:
                table = airtable.table(base_id, table_name)
                records = table.all()
                tables[table_name] = table
                print(f"   ✅ {table_name}: {len(records)} records")
            except Exception as e:
                print(f"   ❌ {table_name}: {e}")
                return False
        
        # Analyze Websites table
        print(f"\n3. Websites Table Analysis:")
        websites_table = tables['Websites']
        websites_records = websites_table.all()
        
        if len(websites_records) == 0:
            print("   ❌ CRITICAL: Websites table is EMPTY!")
            print("      This is why no organized table updates are working.")
            print("      Add websites to the Websites table first!")
            return False
        
        print(f"   ✅ Found {len(websites_records)} websites:")
        for i, record in enumerate(websites_records, 1):
            url = record['fields'].get('url', 'NO URL FIELD')
            record_id = record['id']
            print(f"      {i}. {url} (ID: {record_id})")
        
        # Test URL matching logic
        print(f"\n4. Testing URL Matching Logic:")
        test_urls = [
            "https://example.com",
            "https://www.example.com", 
            "https://example.com/",
            "http://example.com"
        ]
        
        for test_url in test_urls:
            print(f"\n   Testing URL: {test_url}")
            match_found = False
            
            for record in websites_records:
                record_url = record['fields'].get('url')
                
                # Exact match
                if record_url == test_url:
                    print(f"      ✅ EXACT match with: {record_url}")
                    match_found = True
                    break
                    
                # Flexible matching
                if record_url and test_url:
                    clean_record = record_url.rstrip('/')
                    clean_test = test_url.rstrip('/')
                    
                    if clean_record == clean_test:
                        print(f"      ✅ FLEXIBLE match (no slash): {record_url}")
                        match_found = True
                        break
                        
                    if clean_record.replace('www.', '') == clean_test.replace('www.', ''):
                        print(f"      ✅ FLEXIBLE match (no www): {record_url}")
                        match_found = True
                        break
            
            if not match_found:
                print(f"      ❌ NO MATCH found for {test_url}")
        
        # Test relationship field types
        print(f"\n5. Testing Relationship Field Types:")
        
        # Test Core_Metrics table
        try:
            test_website_id = websites_records[0]['id']
            test_data = {
                'url': [test_website_id],  # Should be array for relationship
                'impressions': 100,
                'clicks': 10, 
                'ctr': 0.1,
                'average_position': 15.5,
                'analysis_date': datetime.now().isoformat()
            }
            
            print(f"   Testing Core_Metrics with website ID: {test_website_id}")
            core_table = tables['Core_Metrics']
            result = core_table.create(test_data)
            print(f"   ✅ Core_Metrics accepts relationship data correctly!")
            
            # Clean up
            try:
                core_table.delete(result['id'])
                print(f"   ✅ Test record deleted")
            except:
                print(f"   ⚠️  Could not delete test record: {result['id']}")
                
        except Exception as e:
            print(f"   ❌ Core_Metrics relationship test failed: {e}")
            if 'INVALID_VALUE_FOR_COLUMN' in str(e) and 'url' in str(e).lower():
                print("      💡 The 'url' field in Core_Metrics is not set as 'Link to another record'!")
            
        # Check field types in data tables
        print(f"\n6. Field Type Analysis:")
        
        data_tables = ['Core_Metrics', 'Performance_Metrics', 'Index_Technical', 
                      'Sitemap_Data', 'Mobile_Usability', 'Keyword_Analysis']
        
        for table_name in data_tables:
            if table_name in tables:
                try:
                    records = tables[table_name].all()
                    if records:
                        sample_fields = list(records[0]['fields'].keys())
                        has_url_field = 'url' in sample_fields
                        print(f"   {table_name}: {len(records)} records, has url field: {has_url_field}")
                        if has_url_field and records[0]['fields'].get('url'):
                            url_value = records[0]['fields']['url']
                            print(f"      Sample url value: {url_value} (type: {type(url_value)})")
                    else:
                        print(f"   {table_name}: 0 records (empty table)")
                except Exception as e:
                    print(f"   {table_name}: Error reading - {e}")
        
        print(f"\n" + "=" * 60)
        print("🎯 RECOMMENDATIONS:")
        
        if len(websites_records) == 0:
            print("1. ❌ Add websites to your Websites table first!")
        else:
            print("1. ✅ Websites table has data")
            
        print("2. Ensure all data table 'url' fields are 'Link to another record' type")
        print("3. Run your main script and check the detailed debugging output")
        print("4. If issues persist, check the exact URL format in your Websites table")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

if __name__ == "__main__":
    debug_organized_tables() 