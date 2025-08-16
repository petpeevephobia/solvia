#!/usr/bin/env python3
"""
Performance testing for Solvia Data Pipeline - Alpha Phase 1
Tests query performance against < 300ms requirement
"""

import time
import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.supabase_db import SupabaseAuthDB
from supabase import create_client

# Test configuration
TEST_USER_EMAIL = "test_performance@solvia.ai"
TEST_WEBSITE = "https://test-performance.com"
TARGET_PERFORMANCE = 300  # milliseconds
NUM_ITERATIONS = 10

class PerformanceTest:
    def __init__(self):
        """Initialize performance test with Supabase connection"""
        self.db = SupabaseAuthDB()
        
        # Service role client for direct operations
        service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        supabase_url = os.getenv('SUPABASE_URL')
        self.supabase = create_client(supabase_url, service_role_key)
        
    def time_operation(self, operation_name: str, operation_func, *args, **kwargs):
        """Time an operation and return result with performance metrics"""
        start_time = time.time()
        try:
            result = operation_func(*args, **kwargs)
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            status = "✅ PASS" if duration_ms < TARGET_PERFORMANCE else "❌ FAIL"
            print(f"{operation_name}: {duration_ms:.2f}ms {status}")
            
            return {
                'operation': operation_name,
                'duration_ms': duration_ms,
                'status': 'pass' if duration_ms < TARGET_PERFORMANCE else 'fail',
                'result': result
            }
        except Exception as e:
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            print(f"{operation_name}: {duration_ms:.2f}ms ❌ ERROR - {e}")
            return {
                'operation': operation_name,
                'duration_ms': duration_ms,
                'status': 'error',
                'error': str(e)
            }
    
    def test_insert_performance(self):
        """Test GSC metrics cache INSERT performance"""
        test_data = {
            'user_email': TEST_USER_EMAIL,
            'website_url': TEST_WEBSITE,
            'start_date': '2025-07-17',
            'end_date': '2025-08-16',
            'seo_score': 85.5,
            'impressions': 12500,
            'clicks': 450,
            'ctr': 3.6,
            'avg_position': 15.2,
            'cache_date': '2025-08-16',
            'created_at': datetime.utcnow().isoformat()
        }
        
        def insert_operation():
            return self.supabase.table('gsc_metrics_cache').insert(test_data).execute()
        
        return self.time_operation("INSERT gsc_metrics_cache", insert_operation)
    
    def test_select_performance(self):
        """Test GSC metrics cache SELECT performance"""
        def select_operation():
            return self.supabase.table('gsc_metrics_cache')\
                .select('*')\
                .eq('user_email', TEST_USER_EMAIL)\
                .eq('website_url', TEST_WEBSITE)\
                .order('cache_date', desc=True)\
                .limit(1)\
                .execute()
        
        return self.time_operation("SELECT gsc_metrics_cache", select_operation)
    
    def test_update_performance(self):
        """Test GSC metrics cache UPDATE performance"""
        def update_operation():
            return self.supabase.table('gsc_metrics_cache')\
                .update({'seo_score': 87.2, 'impressions': 13000})\
                .eq('user_email', TEST_USER_EMAIL)\
                .eq('website_url', TEST_WEBSITE)\
                .execute()
        
        return self.time_operation("UPDATE gsc_metrics_cache", update_operation)
    
    def test_complex_query_performance(self):
        """Test complex multi-table query performance"""
        def complex_query():
            # Simulate dashboard query: get metrics + user sessions
            metrics = self.supabase.table('gsc_metrics_cache')\
                .select('*')\
                .eq('user_email', TEST_USER_EMAIL)\
                .gte('cache_date', '2025-07-01')\
                .order('cache_date', desc=True)\
                .execute()
            
            return metrics
        
        return self.time_operation("COMPLEX query with filters", complex_query)
    
    def cleanup_test_data(self):
        """Clean up test data after performance tests"""
        try:
            self.supabase.table('gsc_metrics_cache')\
                .delete()\
                .eq('user_email', TEST_USER_EMAIL)\
                .execute()
            print("🧹 Test data cleaned up")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
    
    def run_performance_suite(self):
        """Run complete performance test suite"""
        print("🚀 Solvia Data Pipeline Performance Test")
        print(f"Target: < {TARGET_PERFORMANCE}ms per query")
        print("=" * 50)
        
        results = []
        
        # Test suite
        test_operations = [
            self.test_insert_performance,
            self.test_select_performance,
            self.test_update_performance,
            self.test_complex_query_performance
        ]
        
        for operation in test_operations:
            result = operation()
            results.append(result)
            time.sleep(0.1)  # Brief pause between tests
        
        # Performance analysis
        print("\n📊 Performance Analysis")
        print("-" * 30)
        
        total_operations = len(results)
        passed_operations = len([r for r in results if r['status'] == 'pass'])
        average_time = sum(r['duration_ms'] for r in results if 'duration_ms' in r) / total_operations
        
        print(f"Operations Passed: {passed_operations}/{total_operations}")
        print(f"Average Query Time: {average_time:.2f}ms")
        print(f"Performance Headroom: {((TARGET_PERFORMANCE - average_time) / TARGET_PERFORMANCE * 100):.1f}%")
        
        # Overall verdict
        if passed_operations == total_operations and average_time < TARGET_PERFORMANCE:
            print("\n✅ PERFORMANCE TEST: PASSED")
            print(f"All queries under {TARGET_PERFORMANCE}ms requirement")
        else:
            print("\n❌ PERFORMANCE TEST: FAILED")
            print("Some queries exceed performance requirements")
        
        # Cleanup
        self.cleanup_test_data()
        
        return {
            'total_operations': total_operations,
            'passed_operations': passed_operations,
            'average_time_ms': average_time,
            'target_ms': TARGET_PERFORMANCE,
            'results': results
        }

def main():
    """Run performance tests"""
    print("Loading environment...")
    from dotenv import load_dotenv
    load_dotenv()
    
    tester = PerformanceTest()
    results = tester.run_performance_suite()
    
    # Save results
    import json
    with open('test/performance_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📝 Results saved to test/performance_results.json")

if __name__ == "__main__":
    main()