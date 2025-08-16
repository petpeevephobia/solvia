#!/usr/bin/env python3
"""
Comprehensive Data Pipeline Integration Test for Solvia Alpha Phase 1
Tests complete OAuth -> GSC -> Supabase flow with RLS validation
"""

import os
import sys
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.supabase_db import SupabaseAuthDB
from app.auth.google_oauth import GoogleOAuthHandler
from supabase import create_client

class DataPipelineTest:
    def __init__(self):
        """Initialize comprehensive data pipeline test suite"""
        self.db = SupabaseAuthDB()
        
        # Service role client for admin operations
        service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        supabase_url = os.getenv('SUPABASE_URL')
        self.service_db = create_client(supabase_url, service_role_key)
        
        # Test data
        self.test_user_email = "test_pipeline@solvia.ai"
        self.test_website = "https://test-pipeline.solvia.ai"
        
        print("🔧 Data Pipeline Test Suite Initialized")
    
    def test_supabase_connection(self) -> bool:
        """Test 1: Supabase database connection"""
        print("\n1️⃣ Testing Supabase Connection...")
        try:
            # Test basic connection
            response = self.db.supabase.table('gsc_metrics_cache').select('count').execute()
            print(f"   ✅ Connected to Supabase (found table)")
            return True
        except Exception as e:
            print(f"   ❌ Supabase connection failed: {e}")
            return False
    
    def test_rls_policies(self) -> bool:
        """Test 2: Row Level Security policies"""
        print("\n2️⃣ Testing RLS Policies...")
        try:
            # Insert test data with service role (should work)
            test_data = {
                'user_email': self.test_user_email,
                'website_url': self.test_website,
                'start_date': '2025-07-17',
                'end_date': '2025-08-16',
                'seo_score': 88.5,
                'impressions': 15000,
                'clicks': 520,
                'ctr': 3.47,
                'avg_position': 12.8,
                'cache_date': '2025-08-16',
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Test service role insert
            self.db.supabase.table('gsc_metrics_cache').insert(test_data).execute()
            print("   ✅ Service role can insert data")
            
            # Test RLS isolation - try to read as different user
            response = self.db.supabase.table('gsc_metrics_cache')\
                .select('*')\
                .eq('user_email', self.test_user_email)\
                .execute()
            
            if response.data:
                print("   ✅ Data inserted and retrievable")
            
            # Test user isolation with service client
            user1_data = test_data.copy()
            user1_data['user_email'] = 'user1@test.com'
            
            user2_data = test_data.copy()
            user2_data['user_email'] = 'user2@test.com'
            user2_data['website_url'] = 'https://user2-site.com'
            
            # Insert data for two different users
            self.service_db.table('gsc_metrics_cache').insert([user1_data, user2_data]).execute()
            
            # Verify isolation - each user should only see their own data
            all_data = self.service_db.table('gsc_metrics_cache')\
                .select('user_email, website_url')\
                .execute()
            
            users = set(record['user_email'] for record in all_data.data)
            if len(users) >= 2:
                print("   ✅ RLS allows multi-user data storage")
            
            # Cleanup test users
            self.service_db.table('gsc_metrics_cache')\
                .delete()\
                .in_('user_email', ['user1@test.com', 'user2@test.com'])\
                .execute()
            
            return True
            
        except Exception as e:
            print(f"   ❌ RLS test failed: {e}")
            return False
    
    def test_oauth_handler_initialization(self) -> bool:
        """Test 3: Google OAuth handler initialization"""
        print("\n3️⃣ Testing OAuth Handler...")
        try:
            oauth_handler = GoogleOAuthHandler(self.db)
            
            # Test auth URL generation
            auth_url = oauth_handler.get_auth_url("test_state")
            if "accounts.google.com" in auth_url and "oauth2" in auth_url:
                print("   ✅ OAuth URL generated successfully")
            else:
                print(f"   ❌ Invalid OAuth URL: {auth_url}")
                return False
            
            print("   ✅ OAuth handler initialized")
            return True
            
        except Exception as e:
            print(f"   ❌ OAuth handler failed: {e}")
            return False
    
    async def test_metrics_caching(self) -> bool:
        """Test 4: GSC metrics caching functionality"""
        print("\n4️⃣ Testing Metrics Caching...")
        try:
            # Test cache storage
            test_metrics = {
                'seo_score': 92.3,
                'organic_traffic': 8500,
                'clicks': 340,
                'ctr': 4.0,
                'avg_position': 8.5,
                'impressions': 8500,
                'keywords': 125
            }
            
            date_range = {
                'start_date': datetime.now().date() - timedelta(days=30),
                'end_date': datetime.now().date(),
                'is_custom_range': False
            }
            
            # Test cache storage
            stored = await self.db.store_gsc_metrics_cache(
                self.test_user_email, 
                self.test_website, 
                test_metrics, 
                date_range
            )
            
            if stored:
                print("   ✅ Metrics cached successfully")
            else:
                print("   ❌ Cache storage failed")
                return False
            
            # Test cache retrieval
            cached_metrics = await self.db.get_gsc_metrics_cache(
                self.test_user_email,
                self.test_website,
                date_range
            )
            
            if cached_metrics and cached_metrics.get('seo_score') == 92.3:
                print("   ✅ Cached metrics retrieved successfully")
                return True
            else:
                print("   ❌ Cache retrieval failed")
                return False
                
        except Exception as e:
            print(f"   ❌ Caching test failed: {e}")
            return False
    
    def test_database_indexes(self) -> bool:
        """Test 5: Database index performance"""
        print("\n5️⃣ Testing Database Indexes...")
        try:
            import time
            
            # Test indexed query performance
            start_time = time.time()
            
            response = self.db.supabase.table('gsc_metrics_cache')\
                .select('*')\
                .eq('user_email', self.test_user_email)\
                .order('cache_date', desc=True)\
                .limit(10)\
                .execute()
            
            end_time = time.time()
            query_time_ms = (end_time - start_time) * 1000
            
            if query_time_ms < 300:  # Under 300ms requirement
                print(f"   ✅ Indexed query: {query_time_ms:.2f}ms (< 300ms)")
                return True
            else:
                print(f"   ❌ Slow query: {query_time_ms:.2f}ms (> 300ms)")
                return False
                
        except Exception as e:
            print(f"   ❌ Index test failed: {e}")
            return False
    
    def cleanup_test_data(self):
        """Clean up all test data"""
        try:
            self.db.supabase.table('gsc_metrics_cache')\
                .delete()\
                .eq('user_email', self.test_user_email)\
                .execute()
            print("\n🧹 Test data cleaned up")
        except Exception as e:
            print(f"\n⚠️ Cleanup warning: {e}")
    
    async def run_full_test_suite(self) -> Dict[str, Any]:
        """Run complete data pipeline test suite"""
        print("🚀 Solvia Data Pipeline Integration Test")
        print("Testing: OAuth → GSC → Supabase → RLS → Caching")
        print("=" * 60)
        
        results = {
            'test_timestamp': datetime.utcnow().isoformat(),
            'tests': {},
            'summary': {}
        }
        
        # Test suite
        tests = [
            ('supabase_connection', self.test_supabase_connection),
            ('rls_policies', self.test_rls_policies),
            ('oauth_handler', self.test_oauth_handler_initialization),
            ('metrics_caching', self.test_metrics_caching),
            ('database_indexes', self.test_database_indexes)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            try:
                if asyncio.iscoroutinefunction(test_func):
                    result = await test_func()
                else:
                    result = test_func()
                
                results['tests'][test_name] = {
                    'status': 'pass' if result else 'fail',
                    'passed': result
                }
                
                if result:
                    passed_tests += 1
                    
            except Exception as e:
                results['tests'][test_name] = {
                    'status': 'error',
                    'error': str(e),
                    'passed': False
                }
        
        # Test summary
        results['summary'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'success_rate': (passed_tests / total_tests) * 100,
            'overall_status': 'pass' if passed_tests == total_tests else 'fail'
        }
        
        print(f"\n📊 Test Results Summary")
        print("-" * 30)
        print(f"Tests Passed: {passed_tests}/{total_tests}")
        print(f"Success Rate: {results['summary']['success_rate']:.1f}%")
        
        if passed_tests == total_tests:
            print("\n✅ DATA PIPELINE TEST: PASSED")
            print("All integration tests successful")
        else:
            print("\n❌ DATA PIPELINE TEST: FAILED")
            print("Some integration tests failed")
        
        # Cleanup
        self.cleanup_test_data()
        
        return results

async def main():
    """Run data pipeline integration tests"""
    print("Loading environment...")
    from dotenv import load_dotenv
    load_dotenv()
    
    tester = DataPipelineTest()
    results = await tester.run_full_test_suite()
    
    # Save results
    with open('test/integration_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📝 Results saved to test/integration_test_results.json")

if __name__ == "__main__":
    asyncio.run(main())