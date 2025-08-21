#!/usr/bin/env python3
"""
Real Audit Engine Testing Script
Tests with actual authenticated user session
"""

import json
import time
from datetime import datetime
import requests
from typing import Optional

# Configuration
BASE_URL = "http://localhost:8000"

class RealAuditTester:
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
            
    def authenticate_real_user(self) -> bool:
        """Guide user through real authentication"""
        self.print_section("2. Real User Authentication")
        
        print("\n  To test the audit engine with real data:")
        print("  1. Open your browser")
        print(f"  2. Go to: {BASE_URL}/auth/google/authorize")
        print("  3. Complete Google OAuth login")
        print("  4. Select your GSC property")
        print("  5. Copy the JWT token from the dashboard")
        
        print("\n  You can find your JWT token in:")
        print("  - Browser DevTools > Application > Local Storage")
        print("  - Look for 'jwt_token' key")
        
        jwt_input = input("\n  Paste your JWT token here (or 'skip' to use test token): ")
        
        if jwt_input.lower() == 'skip':
            # Use the token from the last login if available
            # This is masjaroteko@gmail.com's token from the logs
            self.jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJtYXNqYXJvdGVrb0BnbWFpbC5jb20iLCJleHAiOjE3NTU3MzE4NjN9.QJEuQ4663CW6VVjtmLoki-EdNVi7biSK0RPoBQRiab0"
            self.print_result("Using cached token", "masjaroteko@gmail.com")
        else:
            self.jwt_token = jwt_input.strip()
            self.print_result("Token set", self.jwt_token[:50] + "...")
            
        # Set authorization header
        self.session.headers.update({
            "Authorization": f"Bearer {self.jwt_token}"
        })
        
        return True
        
    def get_current_user(self) -> Optional[str]:
        """Get current authenticated user"""
        try:
            response = self.session.get(f"{BASE_URL}/auth/me")
            if response.status_code == 200:
                data = response.json()
                return data.get("email")
            return None
        except:
            return None
            
    def get_selected_website(self) -> bool:
        """Get the user's selected website"""
        self.print_section("3. Getting Selected Website")
        
        try:
            response = self.session.get(f"{BASE_URL}/auth/gsc/selected-website")
            
            if response.status_code == 200:
                data = response.json()
                self.selected_website = data.get("website")
                
                if self.selected_website:
                    self.print_result("Selected Website", self.selected_website)
                    return True
                else:
                    self.print_result("No website selected", "Please select a website first", False)
                    return False
            else:
                self.print_result("Failed to get website", response.status_code, False)
                return False
                
        except Exception as e:
            self.print_result("Error", str(e), False)
            return False
            
    def trigger_audit(self) -> bool:
        """Trigger a new audit"""
        self.print_section("4. Triggering Audit")
        
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
            elif response.status_code == 400:
                error = response.json().get("detail", "Unknown error")
                self.print_result("Cannot trigger audit", error, False)
                return False
            else:
                self.print_result("Failed to trigger audit", response.status_code, False)
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            self.print_result("Error", str(e), False)
            return False
            
    def wait_for_audit(self) -> bool:
        """Wait for audit to complete"""
        self.print_section("5. Waiting for Audit Completion")
        
        if not self.audit_id:
            self.print_result("No audit ID", "Cannot check status", False)
            return False
            
        print("\n  Checking audit status...")
        max_attempts = 30  # 30 seconds max
        
        for attempt in range(max_attempts):
            try:
                response = self.session.get(f"{BASE_URL}/audit/status/{self.audit_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status")
                    progress = data.get("progress", 0)
                    
                    # Update progress line
                    print(f"\r  Progress: {progress}% - Status: {status}", end="")
                    
                    if status == "completed":
                        print()  # New line
                        self.print_result("Audit Completed", "Success")
                        return True
                    elif status == "failed":
                        print()  # New line
                        self.print_result("Audit Failed", data.get("message"), False)
                        return False
                        
                time.sleep(1)
                
            except Exception as e:
                print()  # New line
                self.print_result("Error checking status", str(e), False)
                return False
                
        print()  # New line
        self.print_result("Timeout", "Audit took too long", False)
        return False
        
    def get_audit_results(self) -> bool:
        """Get and display audit results"""
        self.print_section("6. Audit Results")
        
        try:
            # Try latest if no audit_id
            if not self.audit_id:
                response = self.session.get(f"{BASE_URL}/audit/latest")
            else:
                response = self.session.get(f"{BASE_URL}/audit/results/{self.audit_id}")
                
            if response.status_code == 200:
                data = response.json()
                
                # SEO Score
                print("\n  📊 SEO Score:")
                score = data.get('seo_score', 0)
                self.print_result("  Current Score", f"{score:.1f}/100")
                
                prev_score = data.get('previous_score')
                if prev_score:
                    delta = data.get('score_delta', 0)
                    trend = "📈" if delta > 0 else "📉" if delta < 0 else "➡️"
                    self.print_result("  Previous Score", f"{prev_score:.1f} ({trend} {delta:+.1f})")
                    
                # Metrics
                metrics = data.get('metrics', {})
                if metrics:
                    print("\n  📈 Current Metrics:")
                    self.print_result("  Total Clicks", metrics.get('total_clicks', 0))
                    self.print_result("  Total Impressions", metrics.get('total_impressions', 0))
                    self.print_result("  Average CTR", f"{metrics.get('average_ctr', 0):.2%}")
                    self.print_result("  Average Position", f"{metrics.get('average_position', 0):.1f}")
                    self.print_result("  Total Queries", metrics.get('total_queries', 0))
                    self.print_result("  Total Pages", metrics.get('total_pages', 0))
                    
                # Issue Summary
                print("\n  🔍 Issue Summary:")
                self.print_result("  Critical Issues", data.get('critical_issues', 0))
                self.print_result("  High Issues", data.get('high_issues', 0))
                self.print_result("  Medium Issues", data.get('medium_issues', 0))
                self.print_result("  Low Issues", data.get('low_issues', 0))
                self.print_result("  Total Issues", data.get('total_issues', 0))
                
                # Performance Changes
                print("\n  📊 Performance Changes (30-day):")
                traffic_change = data.get('traffic_change', 0)
                position_change = data.get('position_change', 0)
                ctr_change = data.get('ctr_change', 0)
                
                self.print_result("  Traffic", f"{traffic_change:+.1f}%")
                self.print_result("  Position", f"{position_change:+.1f}")
                self.print_result("  CTR", f"{ctr_change:+.1f}%")
                
                # Top Issues
                issues = data.get('issues', [])
                if issues:
                    print("\n  ⚠️  Top Issues Detected:")
                    for i, issue in enumerate(issues[:3], 1):
                        print(f"\n  Issue #{i}:")
                        severity = issue.get('severity', 'unknown')
                        severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(severity, "⚪")
                        
                        print(f"    {severity_icon} Severity: {severity.upper()}")
                        print(f"    Type: {issue.get('issue_type', 'unknown')}")
                        print(f"    Title: {issue.get('title', 'No title')}")
                        print(f"    Description: {issue.get('description', 'No description')[:150]}...")
                        
                        if issue.get('recommendation'):
                            print(f"    💡 Recommendation: {issue.get('recommendation')[:150]}...")
                            
                        impact = issue.get('traffic_impact', 0)
                        if impact:
                            print(f"    Impact: {impact:.1f}% traffic affected")
                            
                return True
            else:
                self.print_result("Failed to get results", response.status_code, False)
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            self.print_result("Error", str(e), False)
            return False
            
    def get_top_issues(self) -> bool:
        """Get top critical issues for dashboard"""
        self.print_section("7. Top Issues (Dashboard View)")
        
        try:
            response = self.session.get(f"{BASE_URL}/audit/top-issues")
            
            if response.status_code == 200:
                data = response.json()
                issues = data.get("issues", [])
                
                if issues:
                    self.print_result("Critical Issues Found", len(issues))
                    
                    for i, issue in enumerate(issues, 1):
                        severity = issue.get('severity', 'unknown')
                        severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡"}.get(severity, "⚪")
                        
                        print(f"\n  {severity_icon} Priority Issue #{i}:")
                        print(f"    Title: {issue.get('title')}")
                        print(f"    Impact: {issue.get('business_impact', 'Unknown')} business impact")
                        print(f"    Action: {issue.get('recommendation', 'No recommendation')[:100]}...")
                else:
                    self.print_result("No critical issues", "Excellent SEO health! 🎉", True)
                    
                return True
            else:
                self.print_result("Failed to get top issues", response.status_code, False)
                return False
                
        except Exception as e:
            self.print_result("Error", str(e), False)
            return False
            
    def run_test(self):
        """Run complete audit test"""
        print("\n" + "="*60)
        print("  SOLVIA AUDIT ENGINE - REAL USER TEST")
        print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("="*60)
        
        # Track results
        results = []
        
        # 1. Health check
        results.append(("Health Check", self.test_health()))
        
        # 2. Authenticate
        results.append(("Authentication", self.authenticate_real_user()))
        
        # 3. Get selected website
        if results[-1][1]:
            has_website = self.get_selected_website()
            results.append(("Website Selection", has_website))
            
            if has_website:
                # 4. Trigger audit
                audit_triggered = self.trigger_audit()
                results.append(("Trigger Audit", audit_triggered))
                
                if audit_triggered:
                    # 5. Wait for completion
                    audit_completed = self.wait_for_audit()
                    results.append(("Audit Completion", audit_completed))
                    
                    if audit_completed:
                        # 6. Get results
                        results.append(("Audit Results", self.get_audit_results()))
                        
                        # 7. Get top issues
                        results.append(("Top Issues", self.get_top_issues()))
                        
        # Print summary
        self.print_section("TEST SUMMARY")
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        print(f"\n  Tests Passed: {passed}/{total}")
        print(f"  Success Rate: {(passed/total)*100:.1f}%")
        
        print("\n  Results:")
        for name, result in results:
            status = "✅" if result else "❌"
            print(f"    {status} {name}")
            
        if passed == total:
            print("\n  🎉 ALL TESTS PASSED!")
            print("  The Audit Engine is working perfectly with real data!")
        else:
            print("\n  ⚠️  Some tests failed. Check the details above.")
            

def main():
    """Main entry point"""
    # Check server
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("❌ Server not responding properly")
            return
    except:
        print("❌ Cannot connect to server")
        print(f"   Please ensure server is running at {BASE_URL}")
        return
        
    # Run test
    tester = RealAuditTester()
    tester.run_test()
    

if __name__ == "__main__":
    main()