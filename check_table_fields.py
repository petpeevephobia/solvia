#!/usr/bin/env python3
"""
Check what fields actually exist in each Airtable table
"""

import os
from dotenv import load_dotenv
from pyairtable import Api

# Load environment variables
load_dotenv()

def check_table_fields():
    """Check what fields exist in each table."""
    
    print("🔍 Checking Table Fields...")
    print("=" * 50)
    
    api_key = os.getenv('AIRTABLE_API_KEY')
    base_id = os.getenv('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        print("❌ Missing environment variables!")
        return
    
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
        
        for table_name in table_names:
            print(f"\n📊 {table_name}")
            print("-" * 30)
            
            try:
                table = airtable.table(base_id, table_name)
                records = table.all()
                
                if records:
                    # Get field names from first record
                    fields = records[0]['fields'].keys()
                    print(f"✓ {len(records)} records found")
                    print(f"Fields: {', '.join(fields)}")
                    
                    # Show sample data for first record
                    print("Sample data:")
                    for field, value in records[0]['fields'].items():
                        print(f"  {field}: {value}")
                        
                else:
                    print("✓ Table exists but no records found")
                    print("Cannot determine field structure from empty table")
                
            except Exception as e:
                print(f"✗ ERROR: {e}")
    
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    check_table_fields() 