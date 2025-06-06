#!/usr/bin/env python3
"""
Test script to verify Airtable connection and table setup for organized tables mode
"""

import os
from dotenv import load_dotenv
from pyairtable import Api

# Load environment variables
load_dotenv()

def test_airtable_connection():
    """Test the Airtable connection and table setup."""
    
    print("🔍 Testing Airtable Connection...")
    print("=" * 50)
    
    # Check environment variables
    api_key = os.getenv('AIRTABLE_API_KEY')
    base_id = os.getenv('AIRTABLE_BASE_ID')
    use_organized = os.getenv('USE_ORGANIZED_TABLES', 'false').lower() == 'true'
    
    print(f"API Key: {'✓ Set' if api_key else '✗ Missing'}")
    print(f"Base ID: {'✓ Set' if base_id else '✗ Missing'}")
    print(f"USE_ORGANIZED_TABLES: {os.getenv('USE_ORGANIZED_TABLES', 'NOT SET')} -> {use_organized}")
    print()
    
    if not api_key or not base_id:
        print("❌ Missing required environment variables!")
        return False
    
    try:
        airtable = Api(api_key)
        
        # Define table names
        table_names = [
            'Websites',
            'Core_Metrics',
            'Performance_Metrics', 
            'Index_Technical',
            'Sitemap_Data',
            'Mobile_Usability',
            'Keyword_Analysis'
        ]
        
        print("📊 Testing Table Connections...")
        print("-" * 30)
        
        tables = {}
        for table_name in table_names:
            try:
                table = airtable.table(base_id, table_name)
                records = table.all()
                tables[table_name] = table
                print(f"✓ {table_name}: {len(records)} records")
                
                # Show some field info for debugging
                if records:
                    sample_fields = list(records[0]['fields'].keys())
                    print(f"  Fields: {', '.join(sample_fields)}")
                
            except Exception as e:
                print(f"✗ {table_name}: ERROR - {e}")
        
        print()
        print("🔗 Testing Relationships...")
        print("-" * 25)
        
        # Test the main websites table
        if 'Websites' in tables:
            websites = tables['Websites'].all()
            print(f"Websites table has {len(websites)} records:")
            for i, record in enumerate(websites[:3]):  # Show first 3
                url = record['fields'].get('url', 'NO URL FIELD')
                print(f"  {i+1}. {url} (ID: {record['id']})")
            if len(websites) > 3:
                print(f"  ... and {len(websites) - 3} more")
        
        print()
        print("✅ Connection test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_sample_insert():
    """Test inserting sample data into organized tables."""
    
    print("\n" + "="*50)
    print("🧪 Testing Sample Data Insert...")
    print("="*50)
    
    api_key = os.getenv('AIRTABLE_API_KEY')
    base_id = os.getenv('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        print("❌ Missing environment variables for test insert")
        return False
    
    try:
        airtable = Api(api_key)
        
        # Get websites table
        websites_table = airtable.table(base_id, 'Websites')
        websites = websites_table.all()
        
        if not websites:
            print("❌ No websites found in main table. Add some URLs first!")
            return False
        
        # Use first website for test
        test_website = websites[0]
        website_id = test_website['id']
        test_url = test_website['fields'].get('url', 'unknown')
        
        print(f"Testing with: {test_url} (ID: {website_id})")
        
        # Test inserting into Core_Metrics
        core_metrics_table = airtable.table(base_id, 'Core_Metrics')
        test_data = {
            'url': [website_id],
            'impressions': 999,
            'clicks': 99,
            'ctr': 0.099,
            'average_position': 9.9,
            'analysis_date': '2024-01-15T12:00:00Z'
        }
        
        print(f"Inserting test data: {test_data}")
        result = core_metrics_table.create(test_data)
        print(f"✅ Success! Created record ID: {result['id']}")
        
        # Clean up - delete the test record
        core_metrics_table.delete(result['id'])
        print(f"🧹 Cleaned up test record")
        
        return True
        
    except Exception as e:
        print(f"❌ Test insert failed: {e}")
        return False

if __name__ == "__main__":
    success = test_airtable_connection()
    
    if success:
        test_sample_insert()
    
    print("\n" + "="*50)
    print("Test completed!") 