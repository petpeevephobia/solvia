#!/usr/bin/env python3
"""
Test the unified SEO scoring system
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.seo_scoring import SEOScoringEngine

def test_unified_scoring():
    """Test unified SEO scoring across different scenarios"""
    
    print("=" * 60)
    print("TESTING UNIFIED SEO SCORING SYSTEM")
    print("=" * 60)
    
    # Test Case 1: Zero data (jeko.my.id)
    print("\n1. ZERO DATA TEST (jeko.my.id):")
    print("-" * 40)
    score = SEOScoringEngine.calculate_score(
        clicks=0,
        impressions=0,
        ctr=0,
        position=0
    )
    print(f"  Clicks: 0, Impressions: 0, CTR: 0%, Position: 0")
    print(f"  SEO Score: {score}")
    print(f"  Expected: 25.0 (base score)")
    print(f"  ✅ PASS" if score == 25.0 else f"  ❌ FAIL")
    
    # Test Case 2: Some impressions but no clicks
    print("\n2. IMPRESSIONS WITHOUT CLICKS:")
    print("-" * 40)
    score = SEOScoringEngine.calculate_score(
        clicks=0,
        impressions=1000,
        ctr=0,
        position=15
    )
    print(f"  Clicks: 0, Impressions: 1000, CTR: 0%, Position: 15")
    print(f"  SEO Score: {score}")
    print(f"  Should be penalized (50% penalty)")
    
    # Test Case 3: Good performance
    print("\n3. GOOD PERFORMANCE:")
    print("-" * 40)
    score = SEOScoringEngine.calculate_score(
        clicks=100,
        impressions=2000,
        ctr=0.05,  # 5% CTR
        position=5
    )
    print(f"  Clicks: 100, Impressions: 2000, CTR: 5%, Position: 5")
    print(f"  SEO Score: {score}")
    print(f"  Should be 60-80 range")
    
    # Test Case 4: Excellent performance
    print("\n4. EXCELLENT PERFORMANCE:")
    print("-" * 40)
    score = SEOScoringEngine.calculate_score(
        clicks=1000,
        impressions=5000,
        ctr=0.20,  # 20% CTR
        position=2
    )
    print(f"  Clicks: 1000, Impressions: 5000, CTR: 20%, Position: 2")
    print(f"  SEO Score: {score}")
    print(f"  Should be 80+ range")
    
    # Test Case 5: With historical data (improving)
    print("\n5. WITH POSITIVE TRENDS:")
    print("-" * 40)
    score = SEOScoringEngine.calculate_score(
        clicks=150,
        impressions=2500,
        ctr=0.06,
        position=4,
        historical_data={
            'clicks': 100,  # Was 100, now 150 (+50%)
            'position': 6,   # Was 6, now 4 (improved)
            'ctr': 0.04      # Was 4%, now 6%
        }
    )
    print(f"  Current: Clicks: 150, Position: 4, CTR: 6%")
    print(f"  Previous: Clicks: 100, Position: 6, CTR: 4%")
    print(f"  SEO Score: {score}")
    print(f"  Should be boosted by positive trends")
    
    # Test Case 6: With historical data (declining)
    print("\n6. WITH NEGATIVE TRENDS:")
    print("-" * 40)
    score = SEOScoringEngine.calculate_score(
        clicks=50,
        impressions=2000,
        ctr=0.025,
        position=8,
        historical_data={
            'clicks': 100,  # Was 100, now 50 (-50%)
            'position': 5,   # Was 5, now 8 (worse)
            'ctr': 0.05      # Was 5%, now 2.5%
        }
    )
    print(f"  Current: Clicks: 50, Position: 8, CTR: 2.5%")
    print(f"  Previous: Clicks: 100, Position: 5, CTR: 5%")
    print(f"  SEO Score: {score}")
    print(f"  Should be reduced by negative trends")
    
    # Test interpretations
    print("\n" + "=" * 60)
    print("SCORE INTERPRETATIONS:")
    print("=" * 60)
    
    test_scores = [5, 25, 45, 65, 85]
    for test_score in test_scores:
        interpretation = SEOScoringEngine.get_score_interpretation(test_score)
        print(f"\nScore {test_score}: {interpretation['rating']}")
        print(f"  {interpretation['description']}")
        print(f"  → {interpretation['recommendation']}")

if __name__ == "__main__":
    test_unified_scoring()