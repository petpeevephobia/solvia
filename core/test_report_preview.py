import os
from modules.report_generator import ReportGenerator

def generate_test_report():
    # Create sample website data
    website_data = {
        'url': 'example.com',
        'impressions': 15000,
        'clicks': 750,
        'ctr': 5.0,
        'average_position': 3.5,
        'performance_score': 85,
        'first_contentful_paint': 1.2,
        'largest_contentful_paint': 2.5,
        'cumulative_layout_shift': 0.1
    }

    # Create sample OpenAI analysis
    openai_analysis = {
        'executive_summary': 'This website shows strong performance in search results with good engagement metrics. Technical optimization opportunities have been identified to further improve visibility and user experience.',
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
                'title': 'Improve Core Web Vitals',
                'description': 'Largest Contentful Paint (LCP) is above recommended thresholds. Optimizing image loading and server response times can improve user experience.',
                'action_type': 'technical_fix',
                'implementation_steps': [
                    'Implement lazy loading for images',
                    'Optimize server response time',
                    'Enable browser caching',
                    'Monitor LCP improvements'
                ]
            },
            {
                'title': 'Enhance Internal Linking Structure',
                'description': 'Current internal linking structure can be improved to better distribute page authority and improve crawl efficiency.',
                'action_type': 'content_optimization',
                'implementation_steps': [
                    'Analyze current internal linking',
                    'Identify key pages for linking',
                    'Implement strategic internal links',
                    'Monitor crawl efficiency'
                ]
            }
        ]
    }

    # Initialize report generator
    report_generator = ReportGenerator()

    # Generate report
    try:
        pdf_path = report_generator.generate_report(website_data, openai_analysis)
        print(f"\n✅ Test report generated successfully!")
        print(f"📄 Report location: {pdf_path}")
        print("\nTo view the report, open the PDF file at the location above.")
    except Exception as e:
        print(f"❌ Error generating test report: {str(e)}")

if __name__ == "__main__":
    generate_test_report() 