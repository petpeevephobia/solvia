#!/usr/bin/env python3
"""
Run SEO Reports for Google Sheets Users
Generates prioritized SEO reports with the new Recommendation Aggregator system
"""

import os
import sys

# Add the core and app directories to the Python path
sys.path.append('core')
sys.path.append('app')

from core.google_sheets_integration import GoogleSheetsReportGenerator

def main():
    """Main function to generate and send SEO reports."""
    
    print("🚀 Solvia SEO Report Generator - Google Sheets Edition")
    print("=" * 60)
    print("🎯 Features: Prioritized recommendations with business context")
    print("📊 New: Quick wins identification and scoring breakdown")
    print("=" * 60)
    
    # Check if required environment variables are set
    required_env_vars = [
        'OPENAI_API_KEY',
        'SMTP_SERVER', 'EMAIL_USERNAME', 'EMAIL_PASSWORD', 'EMAIL_FROM'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("⚠️  Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these in your .env file:")
        print("   - OPENAI_API_KEY: For AI-powered analysis")
        print("   - SMTP_SERVER, EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_FROM: For sending reports")
        print("\nReports will still be generated locally as PDFs.")
        print("\nContinuing in 3 seconds...")
        import time
        time.sleep(3)
    
    try:
        # Initialize the Google Sheets report generator
        print("\n🔗 Connecting to Google Sheets...")
        gs_reports = GoogleSheetsReportGenerator()
        
        # Option 1: Generate reports for all users
        print("\n📋 Choose an option:")
        print("1. Generate reports for ALL users with websites")
        print("2. Generate report for a SPECIFIC user email")
        print("3. TEST with demo data")
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == "1":
            # Generate for all users
            gs_reports.analyze_and_send_reports()
            
        elif choice == "2":
            # Generate for specific user
            email = input("Enter user email: ").strip()
            if email:
                success = gs_reports.generate_single_report(email)
                if not success:
                    print("\n💡 Make sure the user has:")
                    print("   - Added their website URL in the dashboard")
                    print("   - Verified their email address")
            else:
                print("❌ No email provided.")
                
        elif choice == "3":
            # Test mode
            print("\n🧪 Running in test mode...")
            from core.google_sheets_integration import test_google_sheets_reports
            test_google_sheets_reports()
            
        else:
            print("❌ Invalid choice.")
            return
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Operation cancelled by user.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Check your Google Sheets credentials")
        print("   2. Verify OpenAI API key is set")
        print("   3. Ensure email configuration is correct")
        print("   4. Make sure users have website URLs configured")

def test_recommendation_aggregator():
    """Quick test of the recommendation aggregator system."""
    
    print("\n🧪 Testing Recommendation Aggregator...")
    
    try:
        from core.test_recommendation_aggregator import test_recommendation_aggregator
        test_recommendation_aggregator()
    except ImportError as e:
        print(f"❌ Could not import test: {e}")
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    main()
    
    # Ask if user wants to see the aggregator test
    print("\n" + "=" * 60)
    test_choice = input("🧪 Would you like to see the Recommendation Aggregator test? (y/n): ").strip().lower()
    if test_choice in ['y', 'yes']:
        test_recommendation_aggregator() 