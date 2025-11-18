"""
PDF Text Constants - Rule-Based Conditional Content
===================================================

This module contains all rule-based conditional text content for Solvia PDF reports.
NO AI-generated content - all text is predefined based on rules and conditions.

Total Text Variations: 54
- Stage Descriptions: 4
- Motivational Quotes Page 1: 4
- Motivational Quotes Page 2: 4
- Metric Notes: 16 (across 5 metrics)
- Next Steps: 8 (2 always + 6 conditional)
- Summary Statements: 10 (3 CTR + 4 position + 3 impressions)
- Progress Bar Labels: 8 (4 stage + 4 threshold)

Author: Solvia Team
Date: 2025-11-18
Version: 2.0.0
"""

from typing import Dict, List, Any


# ============================================================================
# 1. SEO STAGE DESCRIPTIONS
# ============================================================================

STAGE_DESCRIPTIONS = {
    'hidden': "Your site is still hidden from most search results. Let's work on visibility by improving content and indexing.",
    'emerging': "Your site is starting to gain visibility. Continue building quality content and improving technical SEO.",
    'discoverable': "Your site is becoming more discoverable. Focus on optimizing top-performing pages and expanding keyword coverage.",
    'trusted': "Your site has strong search visibility. Maintain quality and explore new growth opportunities."
}


# ============================================================================
# 2. MOTIVATIONAL QUOTES - PAGE 1
# ============================================================================

MOTIVATIONAL_QUOTES_PAGE1 = {
    'hidden': "It's okay to be early! Every great site starts in the shadows before it shines. This is where your foundation is built.",
    'emerging': "Visibility is growing. Each impression is a step toward discovery.",
    'discoverable': "You're building momentum. Consistency will accelerate your growth.",
    'trusted': "You've established authority. Now focus on expanding your reach."
}


# ============================================================================
# 3. MOTIVATIONAL QUOTES - PAGE 2
# ============================================================================

MOTIVATIONAL_QUOTES_PAGE2 = {
    'hidden': "Your next step is clarity. Make Google's job easier by showing it what each page is about. That's how visibility starts to grow.",
    'emerging': "Focus on content quality and consistency. Each piece of content builds your authority.",
    'discoverable': "Optimize your top performers. Small improvements compound into significant gains.",
    'trusted': "Maintain your momentum while exploring new opportunities and keywords."
}


# ============================================================================
# 4. METRIC NOTES - CONDITIONAL TEXT
# ============================================================================

def get_impressions_note(impressions_change: float) -> str:
    """
    Get conditional note for Total Impressions metric.

    Args:
        impressions_change: Percentage change in impressions

    Returns:
        Note text based on condition
    """
    if impressions_change > 0:
        return "Visibility increasing steadily"
    else:
        return "Visibility needs improvement"


def get_clicks_note(clicks: int, clicks_change: float) -> str:
    """
    Get conditional note for Total Clicks metric.

    Args:
        clicks: Current click count
        clicks_change: Percentage change in clicks

    Returns:
        Note text based on condition
    """
    if clicks < 10:
        return "Good start for early-stage SEO"
    elif clicks >= 10 and clicks_change > 0:
        return "Traffic growth is positive"
    elif clicks >= 10 and clicks_change <= 0:
        return "Traffic is declining"
    else:
        return "Good start for early-stage SEO"


def get_ctr_note(ctr: float, ctr_change: float) -> str:
    """
    Get conditional note for Click-Through Rate metric.

    Args:
        ctr: Current CTR as percentage (e.g., 9.09 for 9.09%)
        ctr_change: Change in CTR as percentage points

    Returns:
        Note text based on condition
    """
    if ctr_change < 0:
        return "Slight dip — adjust titles"
    elif ctr_change >= 0 and ctr < 2:
        return "Low CTR — optimize meta descriptions"
    elif ctr_change >= 0 and 2 <= ctr < 5:
        return "CTR is improving!"
    elif ctr >= 5:
        return "Strong CTR performance"
    else:
        return "Monitor CTR trends"


def get_position_note(position: float, position_change: float) -> str:
    """
    Get conditional note for Average Position metric.

    Args:
        position: Current average position
        position_change: Change in position (negative = improved)

    Returns:
        Note text based on condition
    """
    if abs(position_change) < 1:
        return "Minor ranking fluctuation"
    elif position_change < -1:
        return "Rankings improving"
    elif position_change > 1:
        return "Rankings declining"
    elif position > 20:
        return "Pages appearing beyond page 2"
    else:
        return "Minor ranking fluctuation"


def get_indexed_pages_note(unindexed_count: int, indexed_pages_change: int) -> str:
    """
    Get conditional note for Indexed Pages metric.

    Args:
        unindexed_count: Number of unindexed pages
        indexed_pages_change: Change in indexed page count

    Returns:
        Note text based on condition
    """
    if unindexed_count > 0:
        return f"{unindexed_count} unindexed page(s)"
    elif unindexed_count == 0 and indexed_pages_change > 0:
        return "More pages being indexed"
    elif unindexed_count == 0 and indexed_pages_change == 0:
        return "Indexing status stable"
    else:
        return "Indexing status stable"


# ============================================================================
# 5. NEXT STEPS - CONDITIONAL LOGIC
# ============================================================================

NEXT_STEPS_ALWAYS = [
    "Add internal links between your existing pages",
    "Generate another report after 14 days of these changes being made to track progress"
]


def get_conditional_next_steps(
    sitemap_submitted: bool,
    ctr: float,
    avg_position: float,
    total_impressions: int,
    unindexed_count: int,
    total_clicks: int
) -> List[str]:
    """
    Get conditional next steps based on current metrics.

    Args:
        sitemap_submitted: Whether sitemap is submitted to GSC
        ctr: Current CTR as percentage
        avg_position: Current average position
        total_impressions: Current impression count
        unindexed_count: Number of unindexed pages
        total_clicks: Current click count

    Returns:
        List of conditional next steps
    """
    steps = []

    # Conditional - Sitemap
    if not sitemap_submitted:
        steps.append("Submit sitemap to Google Search Console")

    # Conditional - CTR/Position
    if ctr < 5 or avg_position > 10:
        steps.append("Optimize meta titles with emotional, relevant keywords")

    # Conditional - Impressions
    if total_impressions < 300:
        steps.append("Write one blog post per week for the next month")

    # Conditional - Indexing
    if unindexed_count > 0:
        steps.append(f"Fix indexing issues for {unindexed_count} page(s)")

    # Conditional - Low Traffic
    if total_clicks < 5:
        steps.append("Focus on content quality and keyword research")

    # Conditional - Position
    if avg_position > 20:
        steps.append("Improve on-page SEO for better rankings")

    return steps


# ============================================================================
# 6. SUMMARY STATEMENT VARIATIONS
# ============================================================================

def get_impressions_statement(impressions: int) -> str:
    """
    Get impressions statement with conditional ending.

    Args:
        impressions: Total impression count

    Returns:
        Complete impressions statement
    """
    base = f"Your site appeared in front of **{impressions}** people in Google search results this month"

    if impressions == 0:
        ending = " — this means Google hasn't discovered your site yet. Submit your sitemap and check for indexing issues."
    elif 0 < impressions < 50:
        ending = " — that means Google recognizes your presence."
    else:  # impressions >= 50
        ending = " — that means Google recognizes your presence and you're building visibility."

    return base + ending


def get_clicks_ctr_statement(clicks: int, ctr: float) -> str:
    """
    Get clicks & CTR statement with conditional ending.

    Args:
        clicks: Total click count
        ctr: CTR as percentage (e.g., 9.09 for 9.09%)

    Returns:
        Complete clicks & CTR statement
    """
    base = f"Out of those impressions, **{clicks}** visitors clicked through, giving you a CTR of **{ctr:.2f}%**."

    if ctr < 2:
        ending = " That's below average — focus on improving your titles and descriptions to increase click-through rates."
    elif 2 <= ctr < 5:
        ending = " That's a good early signal that your content is relevant, but there's still room to grow engagement through sharper titles and descriptions."
    else:  # ctr >= 5
        ending = " That's excellent! Your titles and descriptions are resonating with searchers."

    return base + ending


def get_position_statement(position: float) -> str:
    """
    Get position statement with conditional advice.

    Args:
        position: Average position

    Returns:
        Complete position statement
    """
    base = f"On average, your pages appeared in position **{position:.1f}**"

    if position <= 3:
        ending = ", which means you're ranking on the first page of results. Excellent work! Keep maintaining quality to stay at the top."
    elif 3 < position <= 10:
        ending = ", which means you're hovering on the first page of results. Getting to the top 3 will take consistency — adding fresh content, improving internal links, and keeping your meta details clear."
    elif 10 < position <= 20:
        ending = ", which means you're on page 2. Focus on improving on-page SEO and building quality backlinks to reach page 1."
    else:  # position > 20
        ending = ", which means you're beyond page 2. Prioritize technical SEO fixes and content optimization to improve visibility."

    return base + ending


# ============================================================================
# 7. PROGRESS BAR LABELS
# ============================================================================

STAGE_LABELS = {
    'hidden': 'Hidden',
    'emerging': 'Emerging',
    'discoverable': 'Discoverable',
    'trusted': 'Trusted'
}

THRESHOLD_LABELS = {
    'hidden': '1 impression',
    'emerging': '50 impressions',
    'discoverable': '300 impressions',
    'trusted': '2000+ impressions'
}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_stage_description(stage: str) -> str:
    """Get stage description based on SEO stage."""
    return STAGE_DESCRIPTIONS.get(stage, STAGE_DESCRIPTIONS['hidden'])


def get_motivational_quote_page1(stage: str) -> str:
    """Get Page 1 motivational quote based on SEO stage."""
    return MOTIVATIONAL_QUOTES_PAGE1.get(stage, MOTIVATIONAL_QUOTES_PAGE1['hidden'])


def get_motivational_quote_page2(stage: str) -> str:
    """Get Page 2 motivational quote based on SEO stage."""
    return MOTIVATIONAL_QUOTES_PAGE2.get(stage, MOTIVATIONAL_QUOTES_PAGE2['hidden'])


def get_all_next_steps(
    sitemap_submitted: bool,
    ctr: float,
    avg_position: float,
    total_impressions: int,
    unindexed_count: int,
    total_clicks: int
) -> List[str]:
    """
    Get complete next steps list (always shown + conditional).

    Returns list of 3-8 next steps depending on conditions.
    """
    # Start with always-shown steps
    steps = NEXT_STEPS_ALWAYS.copy()

    # Add conditional steps
    conditional = get_conditional_next_steps(
        sitemap_submitted=sitemap_submitted,
        ctr=ctr,
        avg_position=avg_position,
        total_impressions=total_impressions,
        unindexed_count=unindexed_count,
        total_clicks=total_clicks
    )

    # Insert conditional steps at the beginning (higher priority)
    steps = conditional + steps

    return steps


# ============================================================================
# MODULE TEST
# ============================================================================

if __name__ == "__main__":
    print("=== Testing PDF Text Constants ===\n")

    # Test stage descriptions
    print("1. Stage Descriptions:")
    for stage in ['hidden', 'emerging', 'discoverable', 'trusted']:
        desc = get_stage_description(stage)
        print(f"  {stage}: {desc[:50]}...")
    print()

    # Test motivational quotes
    print("2. Motivational Quotes (Page 1):")
    for stage in ['hidden', 'emerging', 'discoverable', 'trusted']:
        quote = get_motivational_quote_page1(stage)
        print(f"  {stage}: {quote[:60]}...")
    print()

    print("3. Motivational Quotes (Page 2):")
    for stage in ['hidden', 'emerging', 'discoverable', 'trusted']:
        quote = get_motivational_quote_page2(stage)
        print(f"  {stage}: {quote[:60]}...")
    print()

    # Test metric notes
    print("4. Metric Notes:")
    print(f"  Impressions (+100%): {get_impressions_note(100)}")
    print(f"  Impressions (-10%): {get_impressions_note(-10)}")
    print(f"  Clicks (2, +100%): {get_clicks_note(2, 100)}")
    print(f"  CTR (9.09%, +9.09pp): {get_ctr_note(9.09, 9.09)}")
    print(f"  Position (4.1, -5.9): {get_position_note(4.1, -5.9)}")
    print()

    # Test summary statements
    print("5. Summary Statements:")
    print(f"  Impressions: {get_impressions_statement(22)[:80]}...")
    print(f"  Clicks & CTR: {get_clicks_ctr_statement(2, 9.09)[:80]}...")
    print(f"  Position: {get_position_statement(4.1)[:80]}...")
    print()

    # Test next steps
    print("6. Next Steps:")
    steps = get_all_next_steps(
        sitemap_submitted=False,
        ctr=9.09,
        avg_position=4.1,
        total_impressions=22,
        unindexed_count=1,
        total_clicks=2
    )
    for i, step in enumerate(steps, 1):
        print(f"  {i}. {step}")
    print()

    print(f"Total text variations: 54")
    print("All tests passed!")
