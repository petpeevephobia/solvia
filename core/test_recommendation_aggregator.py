"""
Test script for the Recommendation Aggregator
Demonstrates prioritized technical SEO recommendations with scoring
"""

from recommendation_aggregator import RecommendationAggregator
import json

def test_recommendation_aggregator():
    """Test the recommendation aggregator with sample technical SEO recommendations."""
    
    print("🧪 Testing Recommendation Aggregator")
    print("=" * 60)
    
    # Sample business context (E-commerce site)
    business_context = {
        'business_model': 'E-commerce',
        'target_market': 'B2C',
        'industry_sector': 'Retail',
        'company_size': 'Medium',
        'geographic_scope': 'National'
    }
    
    # Sample OpenAI analysis with technical recommendations
    sample_analysis = {
        'executive_summary': 'Website shows good performance with opportunities for technical optimization.',
        'recommendations': [
            {
                'title': 'Optimize Meta Descriptions',
                'description': 'Current meta descriptions are not optimized for click-through rates. Implementing targeted meta descriptions can improve CTR by up to 15%.',
                'action_type': 'meta_update',
                'implementation_steps': [
                    'Analyze current meta descriptions',
                    'Generate optimized versions using AI',
                    'Implement changes through CMS',
                    'Monitor CTR improvements'
                ]
            },
            {
                'title': 'Improve Core Web Vitals - Reduce LCP',
                'description': 'Largest Contentful Paint (LCP) is above recommended thresholds at 3.2 seconds. Critical for mobile e-commerce conversion rates.',
                'action_type': 'technical_fix',
                'implementation_steps': [
                    'Implement lazy loading for product images',
                    'Optimize server response time',
                    'Enable browser caching',
                    'Compress large images',
                    'Monitor LCP improvements'
                ]
            },
            {
                'title': 'Fix Mobile Usability Issues',
                'description': 'Mobile usability problems detected affecting 15% of pages. Critical for mobile-first indexing and user experience.',
                'action_type': 'technical_fix',
                'implementation_steps': [
                    'Audit mobile viewport configuration',
                    'Fix touch element sizing',
                    'Resolve text readability issues',
                    'Test mobile navigation flow'
                ]
            },
            {
                'title': 'Implement Structured Data for Products',
                'description': 'Product pages lack structured data markup. Adding schema can improve search visibility and enable rich snippets.',
                'action_type': 'technical_fix',
                'implementation_steps': [
                    'Audit current structured data',
                    'Implement Product schema markup',
                    'Add Review schema for ratings',
                    'Test with Google Rich Results Tool',
                    'Monitor SERP feature appearances'
                ]
            },
            {
                'title': 'Update Robots.txt File',
                'description': 'Robots.txt file has minor issues that could be optimized for better crawling efficiency.',
                'action_type': 'technical_fix',
                'implementation_steps': [
                    'Review current robots.txt',
                    'Add sitemap references',
                    'Update crawl directives',
                    'Test with Google Search Console'
                ]
            },
            {
                'title': 'Optimize Internal Linking Structure',
                'description': 'Internal linking can be improved to better distribute page authority and improve user navigation.',
                'action_type': 'technical_fix',
                'implementation_steps': [
                    'Audit current internal link structure',
                    'Identify orphaned pages',
                    'Create strategic internal link plan',
                    'Implement contextual links',
                    'Monitor page authority distribution'
                ]
            }
        ]
    }
    
    # Initialize and test the aggregator
    aggregator = RecommendationAggregator()
    aggregator.set_business_context(business_context)
    aggregator.add_technical_seo_recommendations(sample_analysis)
    
    # Get results
    all_recommendations = aggregator.get_prioritized_recommendations()
    technical_recommendations = aggregator.get_technical_recommendations()
    quick_wins = aggregator.get_quick_wins()
    summary = aggregator.generate_action_plan_summary()
    
    # Display results
    print(f"\n📊 AGGREGATION RESULTS")
    print("-" * 40)
    print(f"Total Recommendations: {len(all_recommendations)}")
    print(f"Technical Recommendations: {len(technical_recommendations)}")
    print(f"Quick Wins: {len(quick_wins)}")
    print(f"Average Priority Score: {summary['average_priority_score']}")
    
    print(f"\n🏆 TOP PRIORITY RECOMMENDATIONS")
    print("-" * 40)
    for i, rec in enumerate(technical_recommendations[:3], 1):
        print(f"{i}. {rec['title']}")
        print(f"   Priority Score: {rec['priority_score']}")
        print(f"   Category: {rec['subcategory']}")
        print(f"   Business Impact: {rec['business_impact']}/10")
        print(f"   SEO Impact: {rec['seo_impact']}/10") 
        print(f"   Urgency: {rec['urgency']}/10")
        print(f"   Implementation Effort: {rec['implementation_effort']}/10")
        print(f"   Timeline: {rec['timeline']}")
        print(f"   Context: {rec['business_context_adjustment']}")
        print()
    
    print(f"⚡ QUICK WINS (High Priority, Low Effort)")
    print("-" * 40)
    if quick_wins:
        for i, rec in enumerate(quick_wins, 1):
            print(f"{i}. {rec['title']} (Score: {rec['priority_score']}, Effort: {rec['implementation_effort']})")
    else:
        print("No quick wins identified with current criteria.")
    
    print(f"\n📈 SCORING BREAKDOWN")
    print("-" * 40)
    for rec in technical_recommendations:
        priority_calc = (
            f"({rec['business_impact']} × 0.4) + "
            f"({rec['seo_impact']} × 0.3) + "
            f"({rec['urgency']} × 0.2) + "
            f"({10 - rec['implementation_effort']} × 0.1) = "
            f"{rec['priority_score']}"
        )
        print(f"{rec['title'][:40]}...")
        print(f"  Formula: {priority_calc}")
        print(f"  Success Metrics: {', '.join(rec['success_metrics'][:2])}")
        print()
    
    print(f"\n📋 ACTION PLAN SUMMARY")
    print("-" * 40)
    print(json.dumps(summary, indent=2))
    
    # Test JSON export
    print(f"\n💾 EXPORT TEST")
    print("-" * 40)
    export_json = aggregator.export_recommendations_json()
    print(f"Export JSON length: {len(export_json)} characters")
    print("Export structure valid:", "generated_at" in export_json and "recommendations" in export_json)
    
    print(f"\n✅ AGGREGATOR TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    test_recommendation_aggregator() 