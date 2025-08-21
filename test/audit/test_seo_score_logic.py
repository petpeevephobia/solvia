#!/usr/bin/env python3
"""
Test the SEO score calculation logic to ensure 0% missing
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
import json

def test_seo_score_calculation():
    """Test the SEO score calculation formula"""
    
    print("=" * 60)
    print("TESTING SEO SCORE CALCULATION LOGIC")
    print("=" * 60)
    
    # Test Case 1: Zero data (what jeko.my.id has)
    print("\n1. ZERO DATA TEST (jeko.my.id scenario):")
    print("-" * 40)
    
    clicks = 0
    impressions = 0
    ctr = 0
    position = 0
    
    # Original formula from google_oauth.py
    score = 50.0  # Base score
    
    # Traffic factor (up to 25 points)
    if clicks > 0:
        traffic_factor = min(clicks / 100, 25)
        score += traffic_factor
    
    # CTR factor (up to 15 points)
    ctr_percentage = ctr * 100
    if ctr_percentage > 0:
        ctr_factor = min(ctr_percentage / 2, 15)
        score += ctr_factor
    
    # Position factor (up to 10 points)
    if position > 0:
        position_factor = max(0, (10 - position) * 2)
        score += position_factor
    
    final_score = min(score, 100)
    
    print(f"  Clicks: {clicks}")
    print(f"  Impressions: {impressions}")
    print(f"  CTR: {ctr}%")
    print(f"  Position: {position}")
    print(f"  Base Score: 50.0")
    print(f"  Traffic Factor: 0 (no clicks)")
    print(f"  CTR Factor: 0 (no CTR)")
    print(f"  Position Factor: 0 (position = 0)")
    print(f"  FINAL SCORE: {final_score}")
    print(f"  ✅ This matches your observed score: 50.0")
    
    # Test Case 2: The _get_empty_metrics() inconsistency
    print("\n2. EMPTY METRICS INCONSISTENCY:")
    print("-" * 40)
    print("  _get_empty_metrics() returns seo_score: 0")
    print("  But calculation with zero data gives: 50.0")
    print("  ❌ INCONSISTENCY FOUND!")
    
    # Test Case 3: Audit Engine formula (different!)
    print("\n3. AUDIT ENGINE FORMULA CHECK:")
    print("-" * 40)
    
    # From audit/engine.py
    audit_clicks = 0
    audit_position = 0
    
    # Audit engine formula: (clicks * 10) + (50 - position) * 2
    audit_score = min(100, max(0, (audit_clicks * 10) + (50 - audit_position) * 2))
    
    print(f"  Audit Formula: (clicks * 10) + (50 - position) * 2")
    print(f"  With clicks=0, position=0:")
    print(f"  Score = (0 * 10) + (50 - 0) * 2 = 100")
    print(f"  After min/max capping: {audit_score}")
    print(f"  ❌ ANOTHER INCONSISTENCY! Audit gives 100, GSC gives 50")
    
    # Summary of issues
    print("\n" + "=" * 60)
    print("ISSUES FOUND:")
    print("=" * 60)
    print("1. _get_empty_metrics() returns seo_score: 0")
    print("   But actual calculation gives: 50.0")
    print("")
    print("2. GSC calculation (google_oauth.py) gives: 50.0 for zero data")
    print("   Audit calculation (audit/engine.py) gives: 100.0 for zero data")
    print("")
    print("3. Two different SEO score formulas exist:")
    print("   - GSC: Base 50 + traffic/CTR/position factors")
    print("   - Audit: (clicks * 10) + (50 - position) * 2")
    print("")
    print("RECOMMENDATIONS:")
    print("1. Fix _get_empty_metrics() to return seo_score: 50.0")
    print("2. Standardize SEO score formula across the codebase")
    print("3. Document the official scoring algorithm")
    
    return final_score

if __name__ == "__main__":
    test_seo_score_calculation()