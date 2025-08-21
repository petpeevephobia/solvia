#!/usr/bin/env python3
"""
Test Real User Flow with Unified Scoring
========================================
Simulates actual user interaction with the system
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.supabase_db import SupabaseAuthDB
from app.auth.google_oauth import GoogleOAuthHandler
from app.audit.engine import AuditEngine
from app.core.seo_scoring import SEOScoringEngine

def test_real_flow():
    """Test with real user flow simulation"""
    
    print("\n" + "=" * 60)
    print("  REAL USER FLOW TEST")
    print("=" * 60)
    
    # Initialize components
    db = SupabaseAuthDB()
    oauth = GoogleOAuthHandler(db)
    engine = AuditEngine(db)
    
    print("\n1. SIMULATING USER WITH NO GSC DATA (jeko.my.id):")
    print("-" * 50)
    
    # Simulate metrics for a site with no data
    no_data_metrics = oauth._get_empty_metrics()
    print(f"  Empty metrics SEO Score: {no_data_metrics['seo_score']}")
    print(f"  Expected: 25.0 (unified base score)")
    print(f"  ✅ PASS" if no_data_metrics['seo_score'] == 25.0 else f"  ❌ FAIL")
    
    # Calculate score directly
    score = oauth._calculate_seo_score(0, 0, 0, 0)
    print(f"\n  Direct calculation: {score}")
    print(f"  ✅ Consistent" if score == no_data_metrics['seo_score'] else f"  ❌ Inconsistent")
    
    print("\n2. SIMULATING USER WITH LOW PERFORMANCE:")
    print("-" * 50)
    
    low_perf_score = oauth._calculate_seo_score(
        clicks=10,
        impressions=500,
        ctr=0.02,
        position=15
    )
    print(f"  Low performance SEO Score: {low_perf_score}")
    print(f"  Expected range: 30-40")
    print(f"  ✅ PASS" if 30 <= low_perf_score <= 40 else f"  ❌ FAIL")
    
    print("\n3. SIMULATING USER WITH GOOD PERFORMANCE:")
    print("-" * 50)
    
    good_perf_score = oauth._calculate_seo_score(
        clicks=500,
        impressions=2000,
        ctr=0.25,
        position=3
    )
    print(f"  Good performance SEO Score: {good_perf_score}")
    print(f"  Expected range: 65-85")
    print(f"  ✅ PASS" if 65 <= good_perf_score <= 85 else f"  ❌ FAIL")
    
    print("\n4. SCORE INTERPRETATION TEST:")
    print("-" * 50)
    
    test_scores = [
        (no_data_metrics['seo_score'], "No data"),
        (low_perf_score, "Low performance"),
        (good_perf_score, "Good performance")
    ]
    
    for score, label in test_scores:
        interpretation = SEOScoringEngine.get_score_interpretation(score)
        print(f"\n  {label} ({score:.1f}):")
        print(f"    Rating: {interpretation['rating']}")
        print(f"    Action: {interpretation['recommendation']}")
    
    print("\n5. CONSISTENCY CHECK ACROSS ALL MODULES:")
    print("-" * 50)
    
    # Test data
    test_clicks = 100
    test_impressions = 2000
    test_ctr = 0.05
    test_position = 8
    
    # Core engine
    core_score = SEOScoringEngine.calculate_score(
        test_clicks, test_impressions, test_ctr, test_position
    )
    
    # OAuth module  
    oauth_score = oauth._calculate_seo_score(
        test_clicks, test_impressions, test_ctr, test_position
    )
    
    # Audit engine (using SEOMetrics)
    from app.audit.models import SEOMetrics
    metrics = SEOMetrics(
        total_clicks=test_clicks,
        total_impressions=test_impressions,
        average_ctr=test_ctr,
        average_position=test_position,
        total_queries=0,
        total_pages=0
    )
    audit_score = engine._calculate_enhanced_seo_score(metrics, {})
    
    print(f"  Core Engine Score: {core_score}")
    print(f"  OAuth Module Score: {oauth_score}")
    print(f"  Audit Engine Score: {audit_score}")
    
    if core_score == oauth_score == audit_score:
        print(f"  ✅ ALL CONSISTENT - Score: {core_score}")
    else:
        print(f"  ❌ INCONSISTENT SCORES!")
    
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    
    all_consistent = (core_score == oauth_score == audit_score)
    base_score_correct = (no_data_metrics['seo_score'] == 25.0)
    
    if all_consistent and base_score_correct:
        print("  ✅ UNIFIED SCORING SYSTEM - 100% WORKING!")
        print("  All components use the same scoring algorithm")
        print("  Base score for no data: 25.0")
        print("  Consistent scoring across all modules")
    else:
        print("  ❌ ISSUES DETECTED")
        if not base_score_correct:
            print("  - Base score mismatch")
        if not all_consistent:
            print("  - Scoring inconsistency between modules")
    
    print("=" * 60)

if __name__ == "__main__":
    test_real_flow()