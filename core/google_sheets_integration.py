"""
Google Sheets Integration for SEO Analysis and Report Generation
Bridges the Google Sheets user database with the SEO analysis pipeline
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import GoogleSheetsDB
from typing import List, Dict, Any, Optional
from core.analysis_processor import generate_seo_analysis
from core.modules.business_analysis import BusinessAnalyzer
from googleapiclient.discovery import build
import openai

class GoogleSheetsReportGenerator:
    """Generates and sends SEO reports using Google Sheets user data."""
    
    def __init__(self):
        self.db = GoogleSheetsDB()
        self.business_analyzer = BusinessAnalyzer()
        
    def get_users_with_websites(self) -> List[Dict[str, str]]:
        """Get all users who have websites configured for analysis."""
        users_with_sites = []
        
        if self.db.demo_mode:
            # Demo mode - return demo users
            demo_users = [
                {
                    'email': 'solviapteltd@gmail.com',
                    'website_url': 'https://thenadraagency.com'  # Use your actual domain
                }
            ]
            return demo_users
        
        try:
            # Get all users from the Google Sheet
            all_users = self.db.users_sheet.get_all_records()
            
            for user in all_users:
                email = user.get('email')
                website_url = user.get('website_url')
                
                if email and website_url:
                    users_with_sites.append({
                        'email': email,
                        'website_url': website_url
                    })
                    
            print(f"Found {len(users_with_sites)} users with configured websites")
            return users_with_sites
            
        except Exception as e:
            print(f"Error getting users with websites: {e}")
            return []
    
    def analyze_and_send_reports(self, gsc_service=None):
        """
        Main function to analyze websites and send reports to users.
        
        Args:
            gsc_service: Google Search Console service object (optional)
        """
        print("\n🎯 Starting Google Sheets SEO Analysis & Report Generation")
        print("=" * 70)
        
        users_with_sites = self.get_users_with_websites()
        
        if not users_with_sites:
            print("⚠️  No users with configured websites found.")
            print("   Users need to add their website URL through the dashboard.")
            return
        
        for user_data in users_with_sites:
            email = user_data['email']
            website_url = self._clean_website_url(user_data['website_url'])
            
            print(f"\nProcessing: {website_url} for {email}")
            
            try:
                # Get business analysis
                print("  📊 Conducting business analysis...")
                business_analysis = self.business_analyzer.analyze_business(website_url)
                
                # Create sample metrics for demo (you can replace this with actual GSC/PSI data)
                sample_metrics = self._get_sample_metrics(website_url)
                
                # Generate AI analysis with recommendations
                print("  🤖 Generating AI analysis with prioritized recommendations...")
                openai_analysis = generate_seo_analysis(sample_metrics, business_analysis)
                
                if not openai_analysis:
                    print("  ❌ Failed to generate AI analysis, skipping...")
                    continue
                
                # Generate and send report
                print(f"  📄 Generating and sending report to {email}...")
                
                # Create user data in the format expected by report generator
                user_name = email.split('@')[0].title()  # Use email prefix as name
                
                try:
                    pdf_path = self.report_generator.generate_and_send_report(
                        website_data=sample_metrics,
                        openai_analysis=openai_analysis,
                        recipient_email=email,
                        recipient_name=user_name
                    )
                    print(f"  ✅ Report sent successfully to {email}!")
                    print(f"     PDF saved: {pdf_path}")
                    
                except Exception as email_error:
                    print(f"  ⚠️  Email sending failed: {email_error}")
                    print("     PDF report was still generated locally.")
                
            except Exception as e:
                print(f"  ❌ Error processing {website_url}: {e}")
                continue
        
        print(f"\n✅ Completed processing {len(users_with_sites)} websites")
        print("=" * 70)
    
    def _clean_website_url(self, raw_url: str) -> str:
        """
        Clean and normalize website URL from Google Sheets.
        Handles Search Console property formats like 'sc-domain:example.com'
        """
        if raw_url.startswith('sc-domain:'):
            # Convert Search Console domain property to HTTPS URL
            domain = raw_url.replace('sc-domain:', '')
            return f'https://{domain}'
        elif not raw_url.startswith(('http://', 'https://')):
            # Add https if no protocol specified
            return f'https://{raw_url}'
        else:
            # Already a proper URL
            return raw_url
    
    def _get_sample_metrics(self, website_url: str) -> Dict[str, Any]:
        """
        Generate sample metrics for demonstration.
        Replace this with actual GSC/PSI data collection.
        """
        return {
            'url': website_url,
            'impressions': 15000,
            'clicks': 750,
            'ctr': 5.0,
            'average_position': 3.5,
            'performance_score': 85,
            'first_contentful_paint': 1.2,
            'largest_contentful_paint': 2.5,
            'cumulative_layout_shift': 0.1,
            'speed_index': 2.1,
            'time_to_interactive': 3.4,
            'total_blocking_time': 150
        }
    
    def generate_single_report(self, email: str) -> bool:
        """
        Generate a report for a single user by email.
        
        Args:
            email: User's email address
            
        Returns:
            bool: Success status
        """
        print(f"\n🎯 Generating report for: {email}")
        
        try:
            # Get user's website
            user_website = self.db.get_user_website(email)
            if not user_website or not user_website.get('website_url'):
                print(f"  ❌ No website configured for {email}")
                return False
            
            website_url = self._clean_website_url(user_website['website_url'])
            print(f"  🌐 Analyzing website: {website_url}")
            print(f"  🔗 Cleaned URL: {user_website['website_url']} → {website_url}")
            
            # Get business analysis
            business_analysis = self.business_analyzer.analyze_business(website_url)
            
            # Get sample metrics
            sample_metrics = self._get_sample_metrics(website_url)
            
            # Generate AI analysis
            openai_analysis = generate_seo_analysis(sample_metrics, business_analysis)
            
            if not openai_analysis:
                print(f"  ❌ Failed to generate analysis for {website_url}")
                return False
            
            # Generate report
            user_name = email.split('@')[0].title()
            pdf_path = self.report_generator.generate_and_send_report(
                website_data=sample_metrics,
                openai_analysis=openai_analysis,
                recipient_email=email,
                recipient_name=user_name
            )
            
            print(f"  ✅ Report generated and sent successfully!")
            print(f"     PDF: {pdf_path}")
            return True
            
        except Exception as e:
            print(f"  ❌ Error generating report for {email}: {e}")
            return False


def test_google_sheets_reports():
    """Test function to generate reports for Google Sheets users."""
    
    print("🧪 Testing Google Sheets Report Generation")
    print("=" * 50)
    
    # Initialize the report generator
    gs_reports = GoogleSheetsReportGenerator()
    
    # Test getting users with websites
    users = gs_reports.get_users_with_websites()
    print(f"Found {len(users)} users with websites:")
    for user in users:
        print(f"  - {user['email']}: {user['website_url']}")
    
    if users:
        print(f"\n🎯 Generating test report for first user...")
        first_user = users[0]
        success = gs_reports.generate_single_report(first_user['email'])
        if success:
            print("✅ Test report generation successful!")
        else:
            print("❌ Test report generation failed!")
    else:
        print("⚠️  No users found for testing.")


if __name__ == "__main__":
    test_google_sheets_reports() 