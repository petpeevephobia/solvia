#!/usr/bin/env python3
"""
Complete Audit Engine Testing Script
Tests the full workflow from authentication to audit results
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
import requests
from typing import Dict, Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BASE_URL = "http://localhost:8000"
TEST_EMAIL = "test@example.com"  # Replace with your test email

class AuditTester:
    def __init__(self):
        self.session = requests.Session()
        self.jwt_token = None
        self.selected_website = None
        self.audit_id = None
        
    def print_section(self, title: str):
        """Print formatted section header"""
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
        
    def print_result(self, label: str, value: any, success: bool = True):
        """Print formatted result"""
        status = "✅" if success else "❌"
        print(f"{status} {label}: {value}")
        
    def test_health(self) -> bool:
        """Test audit health endpoint"""
        self.print_section("1. Testing Audit Health Endpoint")
        
        try:
            response = self.session.get(f"{BASE_URL}/audit/health")
            if response.status_code == 200:
                data = response.json()
                self.print_result("Status", data.get("status"))
                self.print_result("Engine", data.get("engine"))
                self.print_result("Analyzers", ", ".join(data.get("analyzers", [])))
                return True
            else:
                self.print_result("Health check failed", response.status_code, False)
                return False
        except Exception as e:
            self.print_result("Error", str(e), False)
            return False
            
    def authenticate(self) -> bool:
        """Simulate authentication and get JWT token"""
        self.print_section("2. Simulating Authentication")
        
        # For testing, we'll create a mock JWT token
        # In production, this would come from Google OAuth flow
        
        try:
            # Check if we have a user session in the database
            # For now, we'll simulate this
            import jwt
            import uuid
            
            # Create a test JWT token
            secret_key = os.getenv("JWT_SECRET", "test-secret-key")
            payload = {
                "email": TEST_EMAIL,
                "sub": str(uuid.uuid4()),
                "exp": datetime.utcnow() + timedelta(hours=24)
            }
            
            self.jwt_token = jwt.encode(payload, secret_key, algorithm="HS256")
            self.session.headers.update({
                "Authorization": f"Bearer {self.jwt_token}"
            })
            
            self.print_result("JWT Token Generated", self.jwt_token[:50] + "...")
            self.print_result("Test Email", TEST_EMAIL)
            return True
            
        except Exception as e:
            self.print_result("Authentication failed", str(e), False)
            return False
            
    def get_gsc_properties(self) -> bool:
        """Get GSC properties for the user"""
        self.print_section("3. Getting GSC Properties")
        
        try:
            response = self.session.get(f"{BASE_URL}/auth/gsc/properties")
            
            if response.status_code == 200:
                data = response.json()
                properties = data.get("properties", [])
                
                if properties:
                    self.print_result("Properties Found", len(properties))
                    for prop in properties[:3]:  # Show first 3
                        print(f"  - {prop}")
                    return True
                else:
                    self.print_result("No properties found", "User needs to connect GSC", False)
                    return False
            else:
                self.print_result("Failed to get properties", response.status_code, False)
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            self.print_result("Error", str(e), False)
            return False
            
    def select_website(self, website_url: Optional[str] = None) -> bool:
        """Select a website for auditing"""
        self.print_section("4. Selecting Website")
        
        # Use provided URL or a test URL
        if not website_url:
            website_url = "https://example.com"  # Default test website
            
        try:
            response = self.session.post(
                f"{BASE_URL}/auth/gsc/select-property",
                json={"website_url": website_url}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.selected_website = website_url
                self.print_result("Website Selected", website_url)
                return True
            else:
                self.print_result("Failed to select website", response.status_code, False)
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            self.print_result("Error", str(e), False)
            return False
            
    def trigger_audit(self) -> bool:
        """Trigger a new audit"""
        self.print_section("5. Triggering Audit")
        
        try:
            response = self.session.post(
                f"{BASE_URL}/audit/trigger",
                json={
                    "date_range_days": 30,
                    "force_refresh": False,
                    "include_recommendations": True
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.audit_id = data.get("audit_id")
                self.print_result("Audit ID", self.audit_id)
                self.print_result("Status", data.get("status"))
                self.print_result("Progress", f"{data.get('progress')}%")
                self.print_result("Message", data.get("message"))
                return True
            else:
                self.print_result("Failed to trigger audit", response.status_code, False)
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            self.print_result("Error", str(e), False)
            return False
            
    def check_audit_status(self) -> bool:
        """Check audit status"""
        self.print_section("6. Checking Audit Status")
        
        if not self.audit_id:
            self.print_result("No audit ID", "Skipping status check", False)
            return False
            
        try:
            max_attempts = 10
            for attempt in range(max_attempts):
                response = self.session.get(f"{BASE_URL}/audit/status/{self.audit_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status")
                    progress = data.get("progress", 0)
                    
                    print(f"  Attempt {attempt + 1}/{max_attempts}: Status={status}, Progress={progress}%")
                    
                    if status == "completed":
                        self.print_result("Audit Completed", "Success")
                        return True
                    elif status == "failed":
                        self.print_result("Audit Failed", data.get("message"), False)
                        return False
                    
                    # Wait before next check
                    time.sleep(2)
                else:
                    self.print_result("Failed to check status", response.status_code, False)
                    return False
                    
            self.print_result("Timeout", "Audit took too long", False)
            return False
            
        except Exception as e:
            self.print_result("Error", str(e), False)
            return False
            
    def get_audit_results(self) -> bool:
        """Get audit results"""
        self.print_section("7. Getting Audit Results")
        
        if not self.audit_id:
            # Try to get latest audit instead
            try:
                response = self.session.get(f"{BASE_URL}/audit/latest")
            except:
                self.print_result("No audit to retrieve", "Skipping", False)
                return False
        else:
            try:
                response = self.session.get(f"{BASE_URL}/audit/results/{self.audit_id}")
            except:
                self.print_result("Failed to get results", "Error", False)
                return False
                
        if response.status_code == 200:
            data = response.json()
            
            # Display key metrics
            self.print_result("SEO Score", f"{data.get('seo_score', 0):.2f}/100")
            self.print_result("Previous Score", data.get('previous_score', 'N/A'))
            self.print_result("Score Delta", data.get('score_delta', 'N/A'))
            
            # Display issue counts
            print("\n  Issue Summary:")
            self.print_result("  Critical", data.get('critical_issues', 0))
            self.print_result("  High", data.get('high_issues', 0))
            self.print_result("  Medium", data.get('medium_issues', 0))
            self.print_result("  Low", data.get('low_issues', 0))
            self.print_result("  Total", data.get('total_issues', 0))
            
            # Display performance changes
            print("\n  Performance Changes (30-day):")
            self.print_result("  Traffic", f"{data.get('traffic_change', 0):.2f}%")
            self.print_result("  Position", f"{data.get('position_change', 0):.2f}")
            self.print_result("  CTR", f"{data.get('ctr_change', 0):.2f}%")
            
            # Display top issues
            issues = data.get('issues', [])
            if issues:
                print("\n  Top Issues Detected:")
                for i, issue in enumerate(issues[:3], 1):
                    print(f"\n  Issue #{i}:")
                    print(f"    Type: {issue.get('issue_type')}")
                    print(f"    Severity: {issue.get('severity')}")
                    print(f"    Title: {issue.get('title')}")
                    print(f"    Impact: {issue.get('traffic_impact', 0):.2f}%")
                    
            return True
        else:
            self.print_result("Failed to get results", response.status_code, False)
            print(f"Response: {response.text}")
            return False
            
    def get_top_issues(self) -> bool:
        """Get top critical issues"""
        self.print_section("8. Getting Top Issues")
        
        try:
            response = self.session.get(f"{BASE_URL}/audit/top-issues")
            
            if response.status_code == 200:
                data = response.json()
                issues = data.get("issues", [])
                
                if issues:
                    self.print_result("Top Issues Found", len(issues))
                    
                    for i, issue in enumerate(issues, 1):
                        print(f"\n  Priority Issue #{i}:")
                        print(f"    Severity: {issue.get('severity')}")
                        print(f"    Title: {issue.get('title')}")
                        print(f"    Description: {issue.get('description')[:100]}...")
                        print(f"    Recommendation: {issue.get('recommendation', 'N/A')[:100]}...")
                        print(f"    Business Impact: {issue.get('business_impact')}")
                        
                    return True
                else:
                    self.print_result("No issues found", "Great SEO health!", True)
                    return True
            else:
                self.print_result("Failed to get top issues", response.status_code, False)
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            self.print_result("Error", str(e), False)
            return False
            
    def get_audit_history(self) -> bool:
        """Get audit history"""
        self.print_section("9. Getting Audit History")
        
        try:
            response = self.session.get(
                f"{BASE_URL}/audit/history",
                params={"limit": 5}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data:
                    self.print_result("History Records", len(data))
                    
                    for audit in data:
                        print(f"\n  Audit: {audit.get('audit_id')}")
                        print(f"    Date: {audit.get('audit_date')}")
                        print(f"    Score: {audit.get('seo_score'):.2f}")
                        print(f"    Trend: {audit.get('trend')}")
                        print(f"    Issues: {audit.get('total_issues')}")
                        
                    return True
                else:
                    self.print_result("No history found", "This is the first audit", True)
                    return True
            else:
                self.print_result("Failed to get history", response.status_code, False)
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            self.print_result("Error", str(e), False)
            return False
            
    def run_complete_test(self):
        """Run complete audit test workflow"""
        print("\n" + "="*60)
        print("  SOLVIA AUDIT ENGINE - COMPLETE TEST")
        print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("="*60)
        
        # Track test results
        results = []
        
        # 1. Test health endpoint
        results.append(("Health Check", self.test_health()))
        
        # 2. Authenticate
        results.append(("Authentication", self.authenticate()))
        
        # 3. Get GSC properties (may fail if no GSC connection)
        self.get_gsc_properties()  # Optional, don't track result
        
        # 4. Select website
        results.append(("Website Selection", self.select_website()))
        
        # 5. Trigger audit
        if results[-1][1]:  # Only if website selection succeeded
            results.append(("Trigger Audit", self.trigger_audit()))
            
            # 6. Check status (wait for completion)
            if results[-1][1]:  # Only if audit triggered
                results.append(("Audit Status", self.check_audit_status()))
                
                # 7. Get results
                results.append(("Audit Results", self.get_audit_results()))
        
        # 8. Get top issues
        results.append(("Top Issues", self.get_top_issues()))
        
        # 9. Get history
        results.append(("Audit History", self.get_audit_history()))
        
        # Print summary
        self.print_section("TEST SUMMARY")
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        print(f"\n  Tests Passed: {passed}/{total}")
        print(f"  Success Rate: {(passed/total)*100:.1f}%")
        
        print("\n  Detailed Results:")
        for name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"    {name}: {status}")
            
        if passed == total:
            print("\n  🎉 ALL TESTS PASSED! Audit Engine is fully operational!")
        else:
            print("\n  ⚠️  Some tests failed. Check the output above for details.")
            
        return passed == total


def main():
    """Main test runner"""
    # First check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("❌ Server is not running! Please start with:")
            print("   uvicorn app.main:app --reload --port 8000")
            return
    except:
        print("❌ Cannot connect to server at", BASE_URL)
        print("   Please start the server with:")
        print("   uvicorn app.main:app --reload --port 8000")
        return
        
    # Run tests
    tester = AuditTester()
    success = tester.run_complete_test()
    
    # Exit with appropriate code
    exit(0 if success else 1)


if __name__ == "__main__":
    main()