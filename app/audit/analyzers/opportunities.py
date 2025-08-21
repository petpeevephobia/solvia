"""
Opportunity Analyzer
Identifies growth opportunities and missed potential
"""

from typing import Dict, List, Optional

from app.audit.models import (
    AuditIssue, SEOMetrics,
    IssueSeverity, IssueCategory, IssueType
)


class OpportunityAnalyzer:
    """
    Identifies SEO opportunities and untapped potential
    """
    
    def __init__(self):
        """Initialize opportunity analyzer with thresholds"""
        
        # Opportunity identification thresholds
        self.opportunity_thresholds = {
            'high_impressions_low_ctr': {
                'impressions': 1000,  # Min impressions to consider
                'ctr': 0.01           # CTR below 1% is opportunity
            },
            'near_first_page': {
                'position_min': 11,    # Position 11-20
                'position_max': 20,
                'traffic_potential': 50  # 50% traffic increase potential
            },
            'striking_distance': {
                'position_min': 4,     # Position 4-10
                'position_max': 10,
                'improvement_potential': 3  # Can improve by 3 positions
            },
            'featured_snippet': {
                'position_max': 5,     # Top 5 positions
                'ctr_below': 0.15     # CTR below 15% might indicate snippet opportunity
            }
        }
        
        # Traffic potential by position (estimated CTR improvement)
        self.traffic_potential = {
            1: 1.0,    # Baseline
            2: 0.55,   # 55% of position 1 traffic
            3: 0.33,   # 33% of position 1 traffic
            4: 0.22,   # 22% of position 1 traffic
            5: 0.18,   # 18% of position 1 traffic
            10: 0.09,  # 9% of position 1 traffic
            15: 0.04,  # 4% of position 1 traffic
            20: 0.02   # 2% of position 1 traffic
        }
    
    async def find_opportunities(
        self,
        current_data: Dict,
        historical_data: Dict,
        metrics: SEOMetrics
    ) -> List[AuditIssue]:
        """
        Find SEO opportunities and untapped potential
        
        Args:
            current_data: Current period metrics
            historical_data: Historical comparison data
            metrics: Current SEO metrics
            
        Returns:
            List of opportunity-related issues
        """
        
        opportunities = []
        
        # 1. High impressions but low CTR opportunity
        low_ctr_opp = self._find_low_ctr_opportunities(metrics)
        if low_ctr_opp:
            opportunities.append(low_ctr_opp)
        
        # 2. Near first page opportunity
        near_first_page = self._find_near_first_page_opportunities(metrics)
        if near_first_page:
            opportunities.append(near_first_page)
        
        # 3. Striking distance opportunities
        striking_distance = self._find_striking_distance_opportunities(metrics)
        if striking_distance:
            opportunities.append(striking_distance)
        
        # 4. Featured snippet opportunities
        snippet_opp = self._find_featured_snippet_opportunities(metrics)
        if snippet_opp:
            opportunities.append(snippet_opp)
        
        # 5. Content gap opportunities
        content_gaps = self._find_content_gap_opportunities(current_data, historical_data)
        opportunities.extend(content_gaps)
        
        # 6. Quick win opportunities
        quick_wins = self._find_quick_win_opportunities(metrics, current_data)
        opportunities.extend(quick_wins)
        
        return opportunities
    
    def _find_low_ctr_opportunities(self, metrics: SEOMetrics) -> Optional[AuditIssue]:
        """Find opportunities where high impressions but low CTR"""
        
        thresholds = self.opportunity_thresholds['high_impressions_low_ctr']
        
        if (metrics.total_impressions >= thresholds['impressions'] and
            metrics.average_ctr < thresholds['ctr']):
            
            # Calculate potential traffic gain
            potential_ctr = 0.03  # Target 3% CTR
            potential_clicks = metrics.total_impressions * potential_ctr
            traffic_gain = potential_clicks - metrics.total_clicks
            
            issue = AuditIssue(
                issue_type=IssueType.OPPORTUNITY_MISSED,
                severity=IssueSeverity.MEDIUM,
                category=IssueCategory.OPPORTUNITY,
                title="High Visibility, Low Engagement Opportunity",
                description=f"You have {metrics.total_impressions:,} impressions but only {metrics.average_ctr:.2f}% CTR. "
                           f"This represents a significant opportunity to increase traffic without improving rankings.",
                recommendation="Focus on improving title tags and meta descriptions to increase click-through rates. "
                              f"Potential to gain {traffic_gain:.0f} additional clicks per month.",
                traffic_impact=traffic_gain,
                business_impact="medium",
                evidence={
                    'total_impressions': metrics.total_impressions,
                    'current_ctr': metrics.average_ctr,
                    'target_ctr': potential_ctr,
                    'potential_clicks': potential_clicks,
                    'traffic_gain': traffic_gain
                }
            )
            
            return issue
        
        return None
    
    def _find_near_first_page_opportunities(self, metrics: SEOMetrics) -> Optional[AuditIssue]:
        """Find opportunities for keywords near first page"""
        
        thresholds = self.opportunity_thresholds['near_first_page']
        
        if (thresholds['position_min'] <= metrics.average_position <= thresholds['position_max'] and
            metrics.total_impressions > 100):
            
            # Calculate traffic potential if moved to first page
            current_traffic_ratio = self._estimate_traffic_ratio(metrics.average_position)
            first_page_ratio = self._estimate_traffic_ratio(8)  # Target position 8
            traffic_multiplier = first_page_ratio / current_traffic_ratio if current_traffic_ratio > 0 else 10
            
            potential_traffic = metrics.total_clicks * traffic_multiplier
            
            issue = AuditIssue(
                issue_type=IssueType.OPPORTUNITY_MISSED,
                severity=IssueSeverity.MEDIUM,
                category=IssueCategory.OPPORTUNITY,
                title="Near First Page - High Impact Opportunity",
                description=f"Your average position ({metrics.average_position:.1f}) is just outside the first page. "
                           f"Moving to the first page could increase traffic by {(traffic_multiplier-1)*100:.0f}%.",
                recommendation="Focus effort on these near-first-page keywords. Small improvements in content quality, "
                              "internal linking, and page optimization can push them to page one.",
                traffic_impact=(traffic_multiplier - 1) * 100,
                business_impact="high",
                evidence={
                    'current_position': metrics.average_position,
                    'target_position': 8,
                    'traffic_multiplier': traffic_multiplier,
                    'potential_traffic': potential_traffic,
                    'current_traffic': metrics.total_clicks
                }
            )
            
            return issue
        
        return None
    
    def _find_striking_distance_opportunities(self, metrics: SEOMetrics) -> Optional[AuditIssue]:
        """Find opportunities for keywords in striking distance of top 3"""
        
        thresholds = self.opportunity_thresholds['striking_distance']
        
        if (thresholds['position_min'] <= metrics.average_position <= thresholds['position_max'] and
            metrics.total_impressions > 500):
            
            # Calculate traffic potential if moved to top 3
            current_ratio = self._estimate_traffic_ratio(metrics.average_position)
            target_ratio = self._estimate_traffic_ratio(3)  # Target position 3
            traffic_multiplier = target_ratio / current_ratio if current_ratio > 0 else 3
            
            potential_traffic = metrics.total_clicks * traffic_multiplier
            
            issue = AuditIssue(
                issue_type=IssueType.OPPORTUNITY_MISSED,
                severity=IssueSeverity.LOW,
                category=IssueCategory.OPPORTUNITY,
                title="Striking Distance - Top 3 Opportunity",
                description=f"Your content ranks in position {metrics.average_position:.1f}, within striking distance of top 3. "
                           f"Reaching top 3 could increase traffic by {(traffic_multiplier-1)*100:.0f}%.",
                recommendation="These are your easiest wins. Focus on content improvements, "
                              "add more comprehensive information, and build a few quality backlinks.",
                traffic_impact=(traffic_multiplier - 1) * 100,
                business_impact="medium",
                evidence={
                    'current_position': metrics.average_position,
                    'target_position': 3,
                    'positions_to_gain': metrics.average_position - 3,
                    'traffic_multiplier': traffic_multiplier,
                    'potential_traffic': potential_traffic
                }
            )
            
            return issue
        
        return None
    
    def _find_featured_snippet_opportunities(self, metrics: SEOMetrics) -> Optional[AuditIssue]:
        """Find featured snippet opportunities"""
        
        thresholds = self.opportunity_thresholds['featured_snippet']
        
        if (metrics.average_position <= thresholds['position_max'] and
            metrics.average_ctr < thresholds['ctr_below'] and
            metrics.total_impressions > 1000):
            
            # Low CTR despite high ranking might indicate competitor has featured snippet
            
            issue = AuditIssue(
                issue_type=IssueType.OPPORTUNITY_MISSED,
                severity=IssueSeverity.LOW,
                category=IssueCategory.OPPORTUNITY,
                title="Featured Snippet Opportunity",
                description=f"You rank in position {metrics.average_position:.1f} but have low CTR ({metrics.average_ctr:.2f}%). "
                           f"This pattern suggests a competitor may have the featured snippet.",
                recommendation="Optimize content for featured snippets: Add clear definitions, "
                              "use structured lists, include tables, and answer questions directly.",
                traffic_impact=50,  # Featured snippets can increase CTR by 50%+
                business_impact="medium",
                evidence={
                    'position': metrics.average_position,
                    'current_ctr': metrics.average_ctr,
                    'expected_ctr': 0.20,  # Expected ~20% CTR for top 5
                    'snippet_potential': True
                }
            )
            
            return issue
        
        return None
    
    def _find_content_gap_opportunities(
        self,
        current_data: Dict,
        historical_data: Dict
    ) -> List[AuditIssue]:
        """Find content gap opportunities"""
        
        opportunities = []
        
        # Check for low page count
        if current_data.get('total_pages', 0) < 10:
            issue = AuditIssue(
                issue_type=IssueType.CONTENT_GAP,
                severity=IssueSeverity.MEDIUM,
                category=IssueCategory.OPPORTUNITY,
                title="Limited Content Coverage",
                description=f"Only {current_data.get('total_pages', 0)} pages are ranking in search. "
                           f"This indicates significant content gaps and expansion opportunities.",
                recommendation="Conduct keyword research to identify content gaps. "
                              "Create comprehensive content covering your industry topics.",
                traffic_impact=100,  # Could double traffic with more content
                business_impact="high",
                evidence={
                    'ranking_pages': current_data.get('total_pages', 0),
                    'total_queries': current_data.get('total_queries', 0)
                }
            )
            opportunities.append(issue)
        
        return opportunities
    
    def _find_quick_win_opportunities(
        self,
        metrics: SEOMetrics,
        current_data: Dict
    ) -> List[AuditIssue]:
        """Find quick win optimization opportunities"""
        
        opportunities = []
        
        # Check for very low CTR with decent position
        if (metrics.average_position <= 10 and 
            metrics.average_ctr < 0.02 and 
            metrics.total_impressions > 500):
            
            issue = AuditIssue(
                issue_type=IssueType.OPPORTUNITY_MISSED,
                severity=IssueSeverity.HIGH,
                category=IssueCategory.OPPORTUNITY,
                title="Quick Win - CTR Optimization",
                description=f"Despite ranking on page 1 (position {metrics.average_position:.1f}), "
                           f"your CTR is extremely low ({metrics.average_ctr:.2f}%).",
                recommendation="This is a quick win. Update title tags and meta descriptions immediately. "
                              "Even a small CTR improvement will significantly increase traffic.",
                traffic_impact=100,  # Could double traffic with better CTR
                business_impact="high",
                evidence={
                    'position': metrics.average_position,
                    'current_ctr': metrics.average_ctr,
                    'impressions': metrics.total_impressions,
                    'wasted_impressions': metrics.total_impressions * 0.98  # 98% not clicking
                }
            )
            opportunities.append(issue)
        
        return opportunities
    
    def _estimate_traffic_ratio(self, position: float) -> float:
        """Estimate relative traffic potential for a position"""
        
        if position <= 0:
            return 0
        
        # Find closest known ratio
        positions = sorted(self.traffic_potential.keys())
        
        if position <= positions[0]:
            return self.traffic_potential[positions[0]]
        
        if position >= positions[-1]:
            # Extrapolate for positions beyond 20
            return self.traffic_potential[positions[-1]] * (20 / position)
        
        # Interpolate between known values
        for i in range(len(positions) - 1):
            if positions[i] <= position <= positions[i + 1]:
                lower_pos = positions[i]
                upper_pos = positions[i + 1]
                lower_ratio = self.traffic_potential[lower_pos]
                upper_ratio = self.traffic_potential[upper_pos]
                
                # Linear interpolation
                weight = (position - lower_pos) / (upper_pos - lower_pos)
                ratio = lower_ratio + (upper_ratio - lower_ratio) * weight
                return ratio
        
        return 0.01  # Default 1% for unknown positions