"""
Unified SEO Scoring System for Solvia
=====================================

This module provides a single, consistent SEO scoring algorithm
to be used across the entire application.

Author: Solvia Team
Date: 2025-08-20
Version: 1.0.0
"""

from typing import Dict, Optional
import numpy as np
from math import log10


class SEOScoringEngine:
    """
    Centralized SEO scoring engine ensuring consistency across the application.
    
    The scoring algorithm uses a weighted multi-factor approach:
    - Traffic Impact: 30% (business value)
    - Position Performance: 25% (visibility potential)
    - CTR Effectiveness: 25% (content relevance)
    - Growth Trends: 20% (momentum indicator)
    
    Score Range: 0-100
    Base Score: 25 (when no data available)
    """
    
    # Industry standard CTR benchmarks by position
    CTR_BENCHMARKS = {
        1: 0.285,   # Position 1: 28.5% CTR
        2: 0.157,   # Position 2: 15.7% CTR
        3: 0.094,   # Position 3: 9.4% CTR
        4: 0.062,   # Position 4: 6.2% CTR
        5: 0.050,   # Position 5: 5.0% CTR
        6: 0.038,   # Position 6: 3.8% CTR
        7: 0.030,   # Position 7: 3.0% CTR
        8: 0.024,   # Position 8: 2.4% CTR
        9: 0.020,   # Position 9: 2.0% CTR
        10: 0.025,  # Position 10: 2.5% CTR
    }
    
    # Component weights (must sum to 1.0)
    WEIGHTS = {
        'traffic': 0.30,
        'position': 0.25,
        'ctr': 0.25,
        'trends': 0.20
    }
    
    @classmethod
    def calculate_score(
        cls,
        clicks: int = 0,
        impressions: int = 0,
        ctr: float = 0,
        position: float = 0,
        historical_data: Optional[Dict] = None
    ) -> float:
        """
        Calculate SEO score using unified algorithm.

        Args:
            clicks: Total clicks in period
            impressions: Total impressions in period
            ctr: Click-through rate (0-1)
            position: Average position (1-100+)
            historical_data: Previous period data for trend analysis

        Returns:
            SEO score between 0-100
        """

        # Handle completely empty data case
        if impressions == 0 and clicks == 0 and position == 0:
            return 25.0  # Base score for no data

        score_components = {}

        # 1. Traffic Score (30%)
        score_components['traffic'] = cls._calculate_traffic_score(clicks)

        # 2. Position Score (25%)
        score_components['position'] = cls._calculate_position_score(position)

        # 3. CTR Score (25%)
        score_components['ctr'] = cls._calculate_ctr_score(ctr, position)

        # 4. Trend Score (20%)
        score_components['trends'] = cls._calculate_trend_score(
            clicks, position, ctr, historical_data
        )

        # Calculate weighted final score
        final_score = sum(
            score * cls.WEIGHTS[component]
            for component, score in score_components.items()
        )

        # Apply penalties for critical issues
        final_score = cls._apply_penalties(final_score, clicks, impressions, ctr)

        # Ensure score is within valid range
        return round(max(0, min(100, final_score)), 2)

    @classmethod
    def calculate_score_with_breakdown(
        cls,
        clicks: int = 0,
        impressions: int = 0,
        ctr: float = 0,
        position: float = 0,
        historical_data: Optional[Dict] = None
    ) -> Dict:
        """
        Calculate SEO score with component breakdown for detailed reporting.

        Args:
            clicks: Total clicks in period
            impressions: Total impressions in period
            ctr: Click-through rate (0-1)
            position: Average position (1-100+)
            historical_data: Previous period data for trend analysis

        Returns:
            Dict containing:
                - seo_score: Final SEO score (0-100)
                - traffic_score: Traffic component score (0-100)
                - position_score: Position component score (0-100)
                - ctr_score: CTR component score (0-100)
                - trend_score: Trend component score (0-100)
        """

        # Handle completely empty data case
        if impressions == 0 and clicks == 0 and position == 0:
            return {
                'seo_score': 25.0,
                'traffic_score': 0.0,
                'position_score': 0.0,
                'ctr_score': 0.0,
                'trend_score': 0.0
            }

        # Calculate component scores
        traffic_score = cls._calculate_traffic_score(clicks)
        position_score = cls._calculate_position_score(position)
        ctr_score = cls._calculate_ctr_score(ctr, position)
        trend_score = cls._calculate_trend_score(clicks, position, ctr, historical_data)

        # Calculate weighted final score
        final_score = (
            traffic_score * cls.WEIGHTS['traffic'] +
            position_score * cls.WEIGHTS['position'] +
            ctr_score * cls.WEIGHTS['ctr'] +
            trend_score * cls.WEIGHTS['trends']
        )

        # Apply penalties for critical issues
        final_score = cls._apply_penalties(final_score, clicks, impressions, ctr)

        # Ensure score is within valid range
        final_score = round(max(0, min(100, final_score)), 2)

        return {
            'seo_score': final_score,
            'traffic_score': round(traffic_score, 1),
            'position_score': round(position_score, 1),
            'ctr_score': round(ctr_score, 1),
            'trend_score': round(trend_score, 1)
        }
    
    @classmethod
    def _calculate_traffic_score(cls, clicks: int) -> float:
        """Calculate traffic component score (0-100)"""
        if clicks <= 0:
            return 0
        
        # Logarithmic scale to handle wide range of traffic volumes
        # 10 clicks = 20, 100 clicks = 40, 1000 clicks = 60, 10000 clicks = 80
        score = log10(clicks + 1) * 20
        return min(100, score)
    
    @classmethod
    def _calculate_position_score(cls, position: float) -> float:
        """Calculate position component score (0-100)"""
        if position <= 0:
            return 0
        
        # Position 1 = 100, Position 10 = 10, Position 20+ = 0
        if position <= 1:
            return 100
        elif position <= 10:
            return max(0, 110 - (position * 10))
        elif position <= 20:
            return max(0, 20 - position)
        else:
            return 0
    
    @classmethod
    def _calculate_ctr_score(cls, ctr: float, position: float) -> float:
        """Calculate CTR component score relative to benchmarks (0-100)"""
        if ctr <= 0:
            return 0
        
        # Get expected CTR for position
        expected_ctr = cls._get_expected_ctr(position)
        
        if expected_ctr > 0:
            # Score based on performance vs benchmark
            # 100% of benchmark = 50 score, 200% = 100 score
            relative_performance = ctr / expected_ctr
            score = min(100, relative_performance * 50)
        else:
            # No benchmark available, use absolute CTR
            # 5% CTR = 50 score, 10% CTR = 100 score
            score = min(100, ctr * 1000)
        
        return score
    
    @classmethod
    def _get_expected_ctr(cls, position: float) -> float:
        """Get expected CTR for a given position"""
        if position <= 0:
            return 0
        
        # Exact match
        if position in cls.CTR_BENCHMARKS:
            return cls.CTR_BENCHMARKS[position]
        
        # Interpolate between known values
        if position < 1:
            return cls.CTR_BENCHMARKS[1]
        elif position > 10:
            # Exponential decay after position 10
            return cls.CTR_BENCHMARKS[10] * (0.9 ** (position - 10))
        else:
            # Linear interpolation between known points
            lower = int(position)
            upper = lower + 1
            
            if lower in cls.CTR_BENCHMARKS and upper in cls.CTR_BENCHMARKS:
                weight = position - lower
                return (cls.CTR_BENCHMARKS[lower] * (1 - weight) + 
                       cls.CTR_BENCHMARKS[upper] * weight)
            elif lower in cls.CTR_BENCHMARKS:
                return cls.CTR_BENCHMARKS[lower]
            else:
                # Estimate based on position 10
                return cls.CTR_BENCHMARKS[10]
    
    @classmethod
    def _calculate_trend_score(
        cls,
        clicks: int,
        position: float,
        ctr: float,
        historical_data: Optional[Dict]
    ) -> float:
        """Calculate trend component score (0-100)"""
        
        # Start with neutral score
        score = 50
        
        if not historical_data:
            return score
        
        # Traffic trend (±25 points)
        if 'clicks' in historical_data:
            prev_clicks = historical_data['clicks']
            if prev_clicks > 0:
                change_pct = ((clicks - prev_clicks) / prev_clicks) * 100
                if change_pct > 20:
                    score += 25
                elif change_pct > 0:
                    score += 12
                elif change_pct < -20:
                    score -= 25
                elif change_pct < 0:
                    score -= 12
        
        # Position trend (±25 points, inverse - lower is better)
        if 'position' in historical_data and position > 0:
            prev_position = historical_data['position']
            if prev_position > 0:
                position_change = prev_position - position  # Positive = improvement
                if position_change > 2:
                    score += 25
                elif position_change > 0:
                    score += 12
                elif position_change < -2:
                    score -= 25
                elif position_change < 0:
                    score -= 12
        
        return max(0, min(100, score))
    
    @classmethod
    def _apply_penalties(
        cls,
        base_score: float,
        clicks: int,
        impressions: int,
        ctr: float
    ) -> float:
        """Apply penalties for critical SEO issues"""
        
        score = base_score
        
        # No visibility penalty
        if impressions == 0:
            score *= 0.3  # 70% penalty
        
        # Zero CTR with impressions penalty
        elif clicks == 0 and impressions > 100:
            score *= 0.5  # 50% penalty
        
        # Very low CTR penalty
        elif impressions > 1000 and ctr < 0.001:
            score *= 0.7  # 30% penalty
        
        return score
    
    @classmethod
    def get_score_interpretation(cls, score: float) -> Dict:
        """
        Get human-readable interpretation of SEO score.
        
        Returns dict with:
        - rating: Excellent/Good/Fair/Poor/Critical
        - description: Explanation of score
        - recommendation: Next action to take
        """
        
        if score >= 80:
            return {
                'rating': 'Excellent',
                'description': 'Your SEO performance is outstanding',
                'recommendation': 'Maintain current strategy and explore new opportunities'
            }
        elif score >= 60:
            return {
                'rating': 'Good',
                'description': 'Your SEO is performing well with room for improvement',
                'recommendation': 'Focus on optimizing underperforming pages'
            }
        elif score >= 40:
            return {
                'rating': 'Fair',
                'description': 'Your SEO needs attention in several areas',
                'recommendation': 'Review and fix critical issues first'
            }
        elif score >= 20:
            return {
                'rating': 'Poor',
                'description': 'Your SEO has significant problems',
                'recommendation': 'Urgent action needed on visibility and content'
            }
        else:
            return {
                'rating': 'Critical',
                'description': 'Your site has minimal or no search visibility',
                'recommendation': 'Check indexing, robots.txt, and submit sitemap'
            }


# Convenience function for backward compatibility
def calculate_seo_score(
    clicks: int = 0,
    impressions: int = 0,
    ctr: float = 0,
    position: float = 0,
    historical_data: Optional[Dict] = None
) -> float:
    """
    Calculate SEO score using the unified scoring engine.
    
    This is a convenience function that delegates to SEOScoringEngine.
    """
    return SEOScoringEngine.calculate_score(
        clicks=clicks,
        impressions=impressions,
        ctr=ctr,
        position=position,
        historical_data=historical_data
    )