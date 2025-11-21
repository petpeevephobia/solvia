"""Quick test script to preview PDF changes
Run this script to generate a test PDF and see your layout changes instantly.
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.agent.pdf_generator import PDFReportGenerator

# Sample audit data matching real structure
sample_audit_data = {
    'seo_score': 72.5,
    'summary': {
        'total_issues': 8,
        'critical_issues': 2
    },
    'scores': {
        'traffic_score': 75.0,
        'position_score': 68.0,
        'ctr_score': 70.0,
        'trend_score': 77.0
    },
    'metrics': {
        'impressions': 191,  # Changed to match image example
        'total_impressions': 191,
        'impressions_change': 12.5,
        'clicks': 9,
        'total_clicks': 9,
        'clicks_change': 8.3,
        'ctr': 0.0471,  # 4.71% as decimal
        'average_ctr': 0.0471,
        'ctr_change': -2.1,
        'avg_position': 8.1,
        'average_position': 8.1,
        'position_change': -1.2,
        'total_queries': 245,
        'total_pages': 87,
        'indexed_pages': 5,
        'avg_time_on_site': '2m 34s',
        'bounce_rate': '42%'
    },
    # ADD THIS: gamified_pdf_data structure
    'gamified_pdf_data': {
        'date_range': {
            'start_display': 'October 19, 2025',
            'end_display': 'November 18, 2025',
            'start': '2025-10-19',
            'end': '2025-11-18',
            'days': 30
        },
        'summary_paragraphs': {
            'impressions_para': 'Your site appeared in front of **191** people in Google search results this month — that means Google recognizes your presence and you\'re building visibility.',
            'clicks_ctr_para': 'Out of those impressions, **9** visitors clicked through, giving you a CTR of **4.71%**. That\'s a good early signal that your content is relevant, but there\'s still room to grow engagement through sharper titles and descriptions.',
            'position_para': 'On average, your pages appeared in position **8.1**, which means you\'re hovering on the first page of results. Getting to the top 3 will take consistency — adding fresh content, improving internal links, and keeping your meta details clear.'
        },
        'seo_stage': 'emerging',  # Based on 191 impressions (between 50 and 300)
        'seo_stage_info': {
            'description': 'Your site is beginning to appear in search results. Keep building content and optimizing for targeted keywords.'
        },
        'motivational_quote_page1': 'Visibility is growing. Each impression is a step toward discovery.',
        'motivational_quote_page2': 'Your next step is clarity. Make Google\'s job easier by showing it what each page is about. That\'s how visibility starts to grow.',
        'changes_28day': {
            'impressions_change': 12.5,
            'clicks_change': 8.3,
            'ctr_change': -2.1,
            'position_change': -1.2,
            'indexed_pages_change': 0
        },
        'next_steps': [
            'Focus on creating content that answers your audience\'s questions',
            'Optimize your meta descriptions to improve click-through rates',
            'Build internal links between related pages',
            'Submit your sitemap to Google Search Console',
            'Monitor your search performance weekly'
        ]
    },
    'issues': [
        {
            'title': 'Low Search Visibility',
            'description': 'Your website has very limited search visibility with only 15,420 impressions. This significantly impacts your ability to attract organic traffic and potential customers.',
            'severity': 'critical',
            'business_impact': 'Reduced organic traffic and potential revenue loss',
            'recommendation': 'Focus on content optimization and keyword targeting to improve search visibility'
        },
        {
            'title': 'Below Average Click-Through Rate',
            'description': 'Click-through rate of 5.78% is below industry standards of 6-8%. This suggests your search result snippets may not be compelling enough.',
            'severity': 'critical',
            'business_impact': 'Missing potential clicks from search results',
            'recommendation': 'Improve meta descriptions and title tags to increase click-through rates'
        },
        {
            'title': 'Limited Keyword Coverage',
            'description': 'Only 245 keywords are ranking, below the recommended 500+ for competitive industries.',
            'severity': 'high',
            'business_impact': 'Limited search opportunities and market reach',
            'recommendation': 'Expand content strategy to target more keywords in your niche'
        },
        {
            'title': 'Average Position Needs Improvement',
            'description': 'Average position of 8.5 means most pages appear on page 2 of search results, reducing visibility.',
            'severity': 'high',
            'business_impact': 'Lower click-through rates and reduced organic traffic',
            'recommendation': 'Optimize on-page SEO factors and build quality backlinks'
        },
        {
            'title': 'Insufficient Indexed Pages',
            'description': 'Only 87 pages are indexed, which may limit your content reach.',
            'severity': 'medium',
            'business_impact': 'Potential content not being discovered by search engines',
            'recommendation': 'Submit updated sitemap and check for crawl errors'
        }
    ],
    'recommendations': [
        {
            'title': 'Improve Meta Descriptions',
            'description': 'Create compelling meta descriptions that encourage clicks while accurately describing page content. Include target keywords naturally and add a clear call-to-action.',
            'priority': 'high'
        },
        {
            'title': 'Expand Content Strategy',
            'description': 'Create more content targeting long-tail keywords in your industry. Focus on answering user questions and providing valuable information.',
            'priority': 'high'
        },
        {
            'title': 'Optimize Title Tags',
            'description': 'Ensure all pages have unique, keyword-rich title tags under 60 characters. Include primary keywords near the beginning.',
            'priority': 'medium'
        },
        {
            'title': 'Build Quality Backlinks',
            'description': 'Develop a backlink strategy focusing on high-authority sites in your industry. Create shareable content that naturally attracts links.',
            'priority': 'medium'
        },
        {
            'title': 'Improve Page Load Speed',
            'description': 'Optimize images, minify CSS/JS, and leverage browser caching to improve page load times, which is a ranking factor.',
            'priority': 'low'
        }
    ]
}

if __name__ == '__main__':
    generator = PDFReportGenerator()
    output_path = 'test_report_preview.pdf'
    
    print("=" * 60)
    print("📄 PDF Preview Generator")
    print("=" * 60)
    print(f"\nGenerating test PDF: {output_path}")
    print("Using sample audit data with:")
    print(f"  - SEO Score: {sample_audit_data['seo_score']}/100")
    print(f"  - Total Issues: {sample_audit_data['summary']['total_issues']}")
    print(f"  - Critical Issues: {sample_audit_data['summary']['critical_issues']}")
    print(f"  - Metrics: {sample_audit_data['metrics']['impressions']:,} impressions")
    print()
    
    try:
        generator.generate_report(
            sample_audit_data,
            output_path,
            'example.com',
            'test-audit-123'
        )
        
        print("✅ PDF generated successfully!")
        print(f"📂 Location: {os.path.abspath(output_path)}")
        print("\n💡 Tips:")
        print("  - Open the PDF in your viewer")
        print("  - Make changes to pdf_generator.py")
        print("  - Run this script again: python test_pdf_preview.py")
        print("  - Refresh the PDF viewer to see changes")
        print()
        
    except Exception as e:
        print(f"❌ Error generating PDF: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

