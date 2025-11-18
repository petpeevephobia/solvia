"""
PDF Data Processor for Gamified SEO Audit Reports
=================================================

This module handles all data processing for the gamified 2-page PDF audit reports:
- 28-day change calculations (V1 vs V2 method)
- SEO stage determination (Hidden/Emerging/Discoverable/Trusted)
- Rule-based notes generation for each metric
- Next steps generation (conditional 3-5 items)
- Motivational quote selection by SEO stage

Author: Solvia Team
Date: 2025-11-13
Version: 1.0.0
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import random


# ============================================================================
# SEO STAGE DEFINITIONS
# ============================================================================

SEO_STAGES = {
    'hidden': {
        'name': 'Hidden',
        'threshold_min': 0,
        'threshold_max': 49,
        'threshold_display': '1 impression',
        'description': "Your site is still hidden from most search results. Let's work on visibility by improving content and indexing.",
        'next_stage': 'emerging'
    },
    'emerging': {
        'name': 'Emerging',
        'threshold_min': 50,
        'threshold_max': 299,
        'threshold_display': '50 impressions',
        'description': "Your site is beginning to appear in search results. Keep building content and optimizing for targeted keywords.",
        'next_stage': 'discoverable'
    },
    'discoverable': {
        'name': 'Discoverable',
        'threshold_min': 300,
        'threshold_max': 1999,
        'threshold_display': '300 impressions',
        'description': "Your site is gaining visibility! Focus on improving CTR and moving up in search rankings.",
        'next_stage': 'trusted'
    },
    'trusted': {
        'name': 'Trusted',
        'threshold_min': 2000,
        'threshold_max': float('inf'),
        'threshold_display': '2000+ impressions',
        'description': "Excellent visibility! Your site is trusted by search engines. Maintain quality and explore new opportunities.",
        'next_stage': None  # No next stage
    }
}


# ============================================================================
# MOTIVATIONAL QUOTES DATABASE
# ============================================================================

MOTIVATIONAL_QUOTES = {
    'hidden': [
        "It's okay to be early! Every great site starts in the shadows before it shines. This is where your foundation is built.",
        "Small beginnings lead to great outcomes. Your journey to visibility starts here.",
        "Building visibility takes time. Every page you optimize brings you closer to discovery.",
        "Rome wasn't built in a day, and neither is SEO success. You're laying the groundwork.",
        "The fact that you're measuring means you're already ahead of most. Keep going!"
    ],
    'emerging': [
        "You're on the right path! Consistency is key—keep publishing quality content.",
        "Great progress! Your site is starting to get noticed by search engines.",
        "You're building momentum. Stay focused on your SEO strategy.",
        "Every impression counts. You're moving in the right direction!",
        "Your efforts are paying off. Keep optimizing and watch your visibility grow."
    ],
    'discoverable': [
        "Impressive growth! Your efforts are paying off. Keep optimizing.",
        "You're in a great position. Focus on improving CTR to capture more clicks.",
        "Your visibility is strong. Time to refine and scale your content strategy.",
        "You've hit a sweet spot! Now focus on converting that visibility into clicks.",
        "Solid progress! You're competing on the first page—aim for the top 5."
    ],
    'trusted': [
        "Outstanding performance! You've built real authority in search.",
        "You've achieved excellent visibility. Now focus on maintaining quality.",
        "Your site is a trusted resource. Explore new keyword opportunities to grow further.",
        "Exceptional work! You're at the top. Keep innovating and stay ahead.",
        "You've mastered SEO basics. Time to explore advanced strategies and scale."
    ]
}


# ============================================================================
# 28-DAY CHANGE CALCULATION (V1 vs V2 METHOD)
# ============================================================================

def calculate_28day_changes(time_series_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate 28-day changes using V1 (first day) vs V2 (last day) method.

    This method compares the FIRST day's metrics (V1) with the LAST day's metrics (V2)
    within the date range, rather than comparing to a previous period.

    Args:
        time_series_data: List of daily metrics from GSC API, e.g.:
            [
                {'date': '2025-09-30', 'clicks': 0, 'impressions': 5, 'ctr': 0.00, 'position': 10.0},
                {'date': '2025-10-01', 'clicks': 1, 'impressions': 8, 'ctr': 0.125, 'position': 8.5},
                ...
                {'date': '2025-10-14', 'clicks': 2, 'impressions': 22, 'ctr': 0.0909, 'position': 4.1}
            ]

    Returns:
        Dictionary with calculated changes:
            {
                'impressions_change': 340.0,      # Percentage change
                'clicks_change': 100.0,           # Percentage change
                'ctr_change': 9.09,               # Absolute difference in percentage points
                'position_change': -5.9,          # Absolute difference (negative = improved)
                'indexed_pages_change': 'N/A',    # If not available
                'has_sufficient_data': True,      # At least 2 data points
                'v1_date': '2025-09-30',          # First day
                'v2_date': '2025-10-14'           # Last day
            }

    Edge Cases:
        - Single day data: Returns 'N/A' for all changes
        - Zero V1 values: Returns 100% if V2 > 0, else 0%
        - Missing data: Returns 'N/A' for that metric
    """

    # Validate input
    if not time_series_data or len(time_series_data) == 0:
        return {
            'impressions_change': 'N/A',
            'clicks_change': 'N/A',
            'ctr_change': 'N/A',
            'position_change': 'N/A',
            'indexed_pages_change': 'N/A',
            'has_sufficient_data': False,
            'v1_date': None,
            'v2_date': None
        }

    # Sort by date to ensure correct V1/V2 order
    sorted_data = sorted(time_series_data, key=lambda x: x.get('date', ''))

    # Check if we have at least 2 data points
    if len(sorted_data) < 2:
        return {
            'impressions_change': 'N/A',
            'clicks_change': 'N/A',
            'ctr_change': 'N/A',
            'position_change': 'N/A',
            'indexed_pages_change': 'N/A',
            'has_sufficient_data': False,
            'v1_date': sorted_data[0].get('date'),
            'v2_date': sorted_data[0].get('date')
        }

    # Get V1 (first day) and V2 (last day)
    V1 = sorted_data[0]
    V2 = sorted_data[-1]

    changes = {
        'has_sufficient_data': True,
        'v1_date': V1.get('date'),
        'v2_date': V2.get('date')
    }

    # Calculate Impressions Change (percentage)
    v1_impressions = V1.get('impressions', 0)
    v2_impressions = V2.get('impressions', 0)

    if v1_impressions > 0:
        changes['impressions_change'] = round(((v2_impressions - v1_impressions) / v1_impressions) * 100, 1)
    elif v2_impressions > 0:
        changes['impressions_change'] = 100.0  # Special case: went from 0 to positive
    else:
        changes['impressions_change'] = 0.0  # Both are 0

    # Calculate Clicks Change (percentage)
    v1_clicks = V1.get('clicks', 0)
    v2_clicks = V2.get('clicks', 0)

    if v1_clicks > 0:
        changes['clicks_change'] = round(((v2_clicks - v1_clicks) / v1_clicks) * 100, 1)
    elif v2_clicks > 0:
        changes['clicks_change'] = 100.0  # Special case: went from 0 to positive
    else:
        changes['clicks_change'] = 0.0  # Both are 0

    # Calculate CTR Change (absolute difference in percentage points)
    # Example: V1 CTR = 4.55%, V2 CTR = 9.09% → Change = +4.54 percentage points
    if v1_impressions > 0:
        v1_ctr = (v1_clicks / v1_impressions) * 100
    else:
        v1_ctr = 0.0

    if v2_impressions > 0:
        v2_ctr = (v2_clicks / v2_impressions) * 100
    else:
        v2_ctr = 0.0

    changes['ctr_change'] = round(v2_ctr - v1_ctr, 2)  # Absolute difference

    # Calculate Position Change (absolute difference, negative = improved)
    # Example: V1 position = 10.0, V2 position = 4.1 → Change = -5.9 (improved by 5.9 positions)
    v1_position = V1.get('position', 0)
    v2_position = V2.get('position', 0)

    if v1_position > 0 and v2_position > 0:
        changes['position_change'] = round(v2_position - v1_position, 1)
    else:
        changes['position_change'] = 'N/A'

    # Calculate Indexed Pages Change (absolute difference)
    v1_indexed = V1.get('indexed_pages')
    v2_indexed = V2.get('indexed_pages')

    if v1_indexed is not None and v2_indexed is not None:
        changes['indexed_pages_change'] = v2_indexed - v1_indexed
    else:
        changes['indexed_pages_change'] = 'N/A'

    return changes


# ============================================================================
# SEO STAGE DETERMINATION
# ============================================================================

def determine_seo_stage(impressions: int) -> str:
    """
    Determine SEO stage based on impression count.

    Thresholds:
        - Hidden: < 50 impressions
        - Emerging: 50-299 impressions
        - Discoverable: 300-1999 impressions
        - Trusted: 2000+ impressions

    Args:
        impressions: Total impressions in the period

    Returns:
        SEO stage key: 'hidden', 'emerging', 'discoverable', or 'trusted'
    """

    if impressions < 50:
        return 'hidden'
    elif impressions < 300:
        return 'emerging'
    elif impressions < 2000:
        return 'discoverable'
    else:
        return 'trusted'


def get_seo_stage_info(stage_key: str) -> Dict[str, Any]:
    """
    Get complete information about an SEO stage.

    Args:
        stage_key: SEO stage ('hidden', 'emerging', 'discoverable', 'trusted')

    Returns:
        Dictionary with stage details:
            {
                'name': 'Hidden',
                'threshold_min': 0,
                'threshold_max': 49,
                'threshold_display': '1 impression',
                'description': '...',
                'next_stage': 'emerging'
            }
    """

    return SEO_STAGES.get(stage_key, SEO_STAGES['hidden'])


# ============================================================================
# RULE-BASED NOTES GENERATION
# ============================================================================

def generate_metric_notes(
    metric_name: str,
    current_value: float,
    change: float,
    stage: str
) -> str:
    """
    Generate rule-based conditional notes for each metric.

    Uses a priority-based rule system to determine the most relevant note.
    Priorities: declining > poor > fair > good > excellent > unavailable

    Args:
        metric_name: 'impressions', 'clicks', 'ctr', 'position', or 'indexed_pages'
        current_value: Current metric value
        change: 28-day change value (can be 'N/A')
        stage: Current SEO stage ('hidden', 'emerging', etc.)

    Returns:
        Single-line note (max 150 characters) with actionable advice
    """

    # Handle unavailable data
    if current_value == 'N/A' or change == 'N/A':
        return "Data unavailable. Check Google Search Console for this metric."

    # Convert change to numeric if it's not already
    try:
        change_numeric = float(change) if change != 'N/A' else 0
    except (ValueError, TypeError):
        change_numeric = 0

    # Metric-specific rules
    if metric_name.lower() == 'impressions':
        if change_numeric < -10:
            return "Visibility declining. Review recent changes and check for algorithm updates."
        elif current_value < 50:
            return "Low visibility. Check indexing status and submit sitemap to GSC."
        elif current_value < 300:
            return "Emerging visibility. Optimize meta tags and expand content coverage."
        elif current_value < 2000:
            return "Good growth! Focus on expanding keyword coverage and content quality."
        else:
            return "Strong visibility! Keep publishing quality content regularly."

    elif metric_name.lower() == 'clicks':
        if change_numeric < -10:
            return "Traffic declining. Investigate ranking drops and title tag effectiveness."
        elif current_value < 2:
            return "Very low traffic. Focus on improving rankings and title tag relevance."
        elif current_value < 10:
            return "Early traffic. Improve CTR with more compelling titles and descriptions."
        elif current_value < 100:
            return "Solid traffic growth. Keep optimizing titles and meta descriptions."
        else:
            return "Excellent traffic! Your content resonates with users. Scale what works."

    elif metric_name.lower() == 'ctr':
        if change_numeric < -1:
            return "CTR declining. Test new title variations and review search intent alignment."
        elif current_value < 2:
            return "Low CTR. Rewrite titles to better match search intent and add power words."
        elif current_value < 5:
            return "Average CTR. A/B test meta descriptions and add emotional triggers."
        elif current_value < 8:
            return "Good CTR. Consider testing new title formats to push even higher."
        else:
            return "Outstanding CTR! Your titles are highly relevant. Maintain this quality."

    elif metric_name.lower() == 'position':
        if change_numeric > 2:  # Positive change = worse position
            return "Position dropping. Check for algorithm updates and competitor changes."
        elif current_value > 20:
            return "Low ranking. Focus on keyword optimization, content quality, and backlinks."
        elif current_value > 10:
            return "Second page ranking. Build high-quality backlinks to reach first page."
        elif current_value > 3:
            return "First page ranking! Aim for top 3 positions with content improvements."
        else:
            return "Top 3 position! Maintain quality, freshness, and monitor competitors."

    elif metric_name.lower() == 'indexed_pages' or metric_name.lower() == 'indexed pages':
        if change_numeric < -5:
            return "Losing indexed pages. Check for crawl errors and robots.txt issues."
        elif current_value == 'N/A':
            return "Data unavailable. Check Google Search Console coverage report."
        elif current_value < 10:
            return "Few indexed pages. Submit sitemap and ensure proper internal linking."
        elif current_value < 50:
            return "Growing index. Strengthen internal linking and publish regularly."
        else:
            return "Healthy page growth. Keep publishing quality content consistently."

    # Default fallback
    return "Monitor this metric closely for changes and trends."


# ============================================================================
# NEXT STEPS GENERATION
# ============================================================================

def generate_next_steps(
    metrics: Dict[str, Any],
    stage: str,
    issues: Optional[List[Dict[str, Any]]] = None
) -> List[str]:
    """
    Generate 3-5 actionable next steps based on current performance.

    Priority system:
        1. Critical issues (position > 20, impressions < 10)
        2. High-impact opportunities (CTR < 2%, position 11-20)
        3. Growth optimization (CTR 2-5%, position 4-10)
        4. Maintenance (all metrics good)

    Args:
        metrics: Dictionary with current metrics:
            {
                'impressions': 22,
                'clicks': 2,
                'ctr': 9.09,  # As percentage
                'position': 4.1,
                'impressions_change': 340.0,
                'clicks_change': 100.0,
                'ctr_change': 9.09,
                'position_change': -5.9
            }
        stage: Current SEO stage ('hidden', 'emerging', etc.)
        issues: Optional list of detected issues from audit engine

    Returns:
        List of 3-5 actionable next steps (strings)
    """

    next_steps = []
    impressions = metrics.get('impressions', 0)
    clicks = metrics.get('clicks', 0)
    ctr = metrics.get('ctr', 0)
    position = metrics.get('position', 0)
    impressions_change = metrics.get('impressions_change', 0)

    # Convert change to numeric if needed
    try:
        impressions_change_numeric = float(impressions_change) if impressions_change != 'N/A' else 0
    except (ValueError, TypeError):
        impressions_change_numeric = 0

    # Priority 1: Critical Issues
    if impressions < 10:
        next_steps.append("Check indexing status in Google Search Console and submit sitemap immediately.")

    if position > 20:
        next_steps.append("Improve on-page SEO: optimize title tags, meta descriptions, and heading structure.")

    if clicks == 0 and impressions > 100:
        next_steps.append("Rewrite title tags to better match search intent and improve click-through rate.")

    # Priority 2: High-Impact Opportunities
    if ctr < 2 and impressions >= 100:
        next_steps.append("A/B test title tags and meta descriptions with power words to increase CTR.")

    if 11 <= position <= 20:
        next_steps.append("Build 5-10 high-quality backlinks from relevant sites to reach first page.")

    if impressions_change_numeric < -10:
        next_steps.append("Investigate ranking drops: check Search Console for manual actions or algorithm updates.")

    # Priority 3: Growth Optimization
    if 2 <= ctr < 5 and not any('CTR' in step for step in next_steps):
        next_steps.append("Test new title formats: add numbers, questions, or emotional triggers.")

    if 4 <= position <= 10:
        next_steps.append("Target featured snippet opportunities with structured content (lists, tables, FAQs).")

    if stage in ['emerging', 'discoverable'] and len(next_steps) < 4:
        next_steps.append("Expand keyword coverage by targeting related long-tail keywords with lower competition.")

    # Priority 4: Maintenance
    if stage == 'trusted' and position <= 3 and len(next_steps) < 3:
        next_steps.append("Maintain content freshness with monthly updates and explore new keyword opportunities.")

    # Stage-specific recommendations
    if stage == 'hidden' and len(next_steps) < 4:
        next_steps.append("Create a content calendar with 2-4 posts per month targeting specific keywords.")

    if stage == 'emerging' and len(next_steps) < 4:
        next_steps.append("Strengthen internal linking: link from high-authority pages to new content.")

    # Generic fallback if we don't have enough steps
    if len(next_steps) < 3:
        next_steps.append("Monitor Google Search Console weekly for new issues and opportunities.")

    if len(next_steps) < 3:
        next_steps.append("Set up Google Analytics goals to track conversions from organic search.")

    # Limit to maximum 5 steps
    return next_steps[:5]


# ============================================================================
# MOTIVATIONAL QUOTE SELECTION
# ============================================================================

def select_motivational_quote(stage: str) -> str:
    """
    Select a random motivational quote based on SEO stage.

    Args:
        stage: Current SEO stage ('hidden', 'emerging', 'discoverable', 'trusted')

    Returns:
        Random motivational quote string appropriate for the stage
    """

    quotes = MOTIVATIONAL_QUOTES.get(stage, MOTIVATIONAL_QUOTES['hidden'])
    return random.choice(quotes)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def format_change_display(change: Any, metric_type: str = 'percentage') -> str:
    """
    Format change value for display in PDF.

    Args:
        change: Change value (can be float, int, or 'N/A')
        metric_type: 'percentage', 'absolute', or 'position'

    Returns:
        Formatted string with sign and unit:
            - percentage: "+340.0%", "-10.5%", "0.0%"
            - absolute: "+4.54", "-2.3", "0.0"
            - position: "-5.9" (improved), "+2.1" (declined)
    """

    if change == 'N/A' or change is None:
        return 'N/A'

    try:
        change_numeric = float(change)
    except (ValueError, TypeError):
        return 'N/A'

    # Add sign
    if change_numeric > 0:
        sign = '+'
    elif change_numeric < 0:
        sign = ''  # Negative sign already included
    else:
        sign = ''

    # Format based on metric type
    if metric_type == 'percentage':
        return f"{sign}{change_numeric:.1f}%"
    elif metric_type == 'absolute':
        return f"{sign}{change_numeric:.2f}"
    elif metric_type == 'position':
        return f"{sign}{change_numeric:.1f}"
    else:
        return f"{sign}{change_numeric:.1f}"


def format_ctr_display(ctr_decimal: float) -> str:
    """
    Format CTR for display (ALWAYS multiply by 100 to show as percentage).

    This is a critical utility to prevent the CTR display bug.

    Args:
        ctr_decimal: CTR as decimal (e.g., 0.0909)

    Returns:
        Formatted percentage string (e.g., "9.09%")
    """

    if ctr_decimal is None or ctr_decimal == 'N/A':
        return 'N/A'

    try:
        ctr_numeric = float(ctr_decimal)
        ctr_percentage = ctr_numeric * 100
        return f"{ctr_percentage:.2f}%"
    except (ValueError, TypeError):
        return 'N/A'


# ============================================================================
# MODULE TEST (for development/debugging)
# ============================================================================

if __name__ == "__main__":
    # Test 28-day calculation with sample data
    sample_time_series = [
        {'date': '2025-09-30', 'clicks': 0, 'impressions': 5, 'ctr': 0.00, 'position': 10.0},
        {'date': '2025-10-01', 'clicks': 1, 'impressions': 8, 'ctr': 0.125, 'position': 8.5},
        {'date': '2025-10-14', 'clicks': 2, 'impressions': 22, 'ctr': 0.0909, 'position': 4.1}
    ]

    print("=== Testing 28-Day Calculation ===")
    changes = calculate_28day_changes(sample_time_series)
    print(f"Impressions change: {changes['impressions_change']}")
    print(f"Clicks change: {changes['clicks_change']}")
    print(f"CTR change: {changes['ctr_change']}")
    print(f"Position change: {changes['position_change']}")
    print()

    print("=== Testing SEO Stage Determination ===")
    test_impressions = [22, 75, 500, 3000]
    for imp in test_impressions:
        stage = determine_seo_stage(imp)
        info = get_seo_stage_info(stage)
        print(f"{imp} impressions → {info['name']} stage")
    print()

    print("=== Testing Notes Generation ===")
    print(generate_metric_notes('impressions', 22, 340.0, 'hidden'))
    print(generate_metric_notes('ctr', 9.09, 9.09, 'hidden'))
    print()

    print("=== Testing Motivational Quotes ===")
    for stage_key in ['hidden', 'emerging', 'discoverable', 'trusted']:
        quote = select_motivational_quote(stage_key)
        print(f"{stage_key}: {quote[:50]}...")
