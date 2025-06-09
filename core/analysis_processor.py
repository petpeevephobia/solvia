import os
import json
from urllib.parse import urlparse
import openai
from modules.business_analysis import BusinessAnalyzer
from modules.report_generator import ReportGenerator

def classify_keyword_intent(keyword):
    """
    Categorizes keyword intent into informational, navigational, commercial, or transactional.
    
    Args:
        keyword (str): The keyword to classify
        
    Returns:
        str: The classified intent category
    """
    # Common intent indicators
    intent_indicators = {
        'informational': ['what', 'how', 'why', 'when', 'where', 'guide', 'tutorial', 'learn'],
        'navigational': ['login', 'sign in', 'account', 'home', 'contact', 'about'],
        'commercial': ['best', 'top', 'review', 'compare', 'vs', 'alternatives'],
        'transactional': ['buy', 'purchase', 'price', 'cost', 'discount', 'deal', 'sale']
    }
    
    keyword_lower = keyword.lower()
    
    # Check for intent indicators
    for intent, indicators in intent_indicators.items():
        if any(indicator in keyword_lower for indicator in indicators):
            return intent
            
    # Default to informational if no clear intent is found
    return 'informational'

def calculate_opportunity_score(keyword_data):
    """
    Calculates SEO opportunity score based on keyword metrics.
    
    Args:
        keyword_data (dict): Keyword performance data
        
    Returns:
        float: Opportunity score between 0 and 100
    """
    try:
        # Extract metrics
        position = keyword_data.get('position', 0)
        impressions = keyword_data.get('impressions', 0)
        clicks = keyword_data.get('clicks', 0)
        
        # Calculate base score components
        position_score = max(0, 100 - (position * 10))  # Higher position = higher score
        volume_score = min(100, impressions / 1000)  # Normalize impressions
        ctr_score = min(100, (clicks / impressions * 100) if impressions > 0 else 0)
        
        # Weight the components
        final_score = (position_score * 0.4) + (volume_score * 0.4) + (ctr_score * 0.2)
        
        return round(final_score, 2)
    except Exception as e:
        print(f"Error calculating opportunity score: {str(e)}")
        return 0

def get_expected_ctr(position):
    """
    Estimates expected CTR based on position.
    
    Args:
        position (float): Current position in search results
        
    Returns:
        float: Expected CTR percentage
    """
    # Based on industry averages
    ctr_by_position = {
        1: 32.5,
        2: 17.6,
        3: 11.4,
        4: 8.1,
        5: 6.1,
        6: 4.4,
        7: 3.5,
        8: 3.1,
        9: 2.6,
        10: 2.4
    }
    
    return ctr_by_position.get(round(position), 1.0)

def estimate_traffic_potential(current_position, current_impressions):
    """
    Projects potential traffic based on current position and impressions.
    
    Args:
        current_position (float): Current position in search results
        current_impressions (int): Current number of impressions
        
    Returns:
        dict: Traffic potential estimates
    """
    try:
        current_ctr = get_expected_ctr(current_position)
        current_clicks = current_impressions * (current_ctr / 100)
        
        # Calculate potential at different positions
        potential = {}
        for target_position in range(1, 4):  # Look at top 3 positions
            target_ctr = get_expected_ctr(target_position)
            potential_clicks = current_impressions * (target_ctr / 100)
            potential[target_position] = {
                'estimated_clicks': round(potential_clicks),
                'increase': round(potential_clicks - current_clicks)
            }
            
        return potential
    except Exception as e:
        print(f"Error estimating traffic potential: {str(e)}")
        return {}

def get_priority_level(opportunity_score):
    """
    Determines priority level based on opportunity score.
    
    Args:
        opportunity_score (float): Calculated opportunity score
        
    Returns:
        str: Priority level (High, Medium, Low)
    """
    if opportunity_score >= 70:
        return 'High'
    elif opportunity_score >= 40:
        return 'Medium'
    else:
        return 'Low'

def is_branded_keyword(keyword, domain):
    """
    Identifies if a keyword is branded based on domain name.
    
    Args:
        keyword (str): The keyword to check
        domain (str): The website domain
        
    Returns:
        bool: True if keyword is branded, False otherwise
    """
    try:
        # Extract brand name from domain
        brand_name = domain.split('.')[0].lower()
        
        # Check if brand name is in keyword
        return brand_name in keyword.lower()
    except Exception as e:
        print(f"Error checking branded keyword: {str(e)}")
        return False

def detect_cannibalization_risk(keywords_data):
    """
    Detects potential keyword cannibalization issues.
    
    Args:
        keywords_data (list): List of keyword performance data
        
    Returns:
        list: Potential cannibalization issues
    """
    try:
        cannibalization_issues = []
        
        # Group keywords by similar terms
        keyword_groups = {}
        for keyword_data in keywords_data:
            keyword = keyword_data.get('query', '').lower()
            words = set(keyword.split())
            
            # Find similar keywords
            for existing_keyword in keyword_groups:
                existing_words = set(existing_keyword.split())
                similarity = len(words.intersection(existing_words)) / len(words.union(existing_words))
                
                if similarity > 0.7:  # 70% similarity threshold
                    if keyword not in keyword_groups[existing_keyword]:
                        keyword_groups[existing_keyword].append(keyword)
        
        # Analyze each group for cannibalization
        for main_keyword, similar_keywords in keyword_groups.items():
            if len(similar_keywords) > 1:
                cannibalization_issues.append({
                    'main_keyword': main_keyword,
                    'similar_keywords': similar_keywords,
                    'risk_level': 'High' if len(similar_keywords) > 3 else 'Medium'
                })
                
        return cannibalization_issues
    except Exception as e:
        print(f"Error detecting cannibalization: {str(e)}")
        return []

def get_business_analysis(url):
    """
    Performs initial business analysis of a website.
    
    Args:
        url (str): The website URL to analyze
        
    Returns:
        dict: Initial business analysis data
    """
    try:
        analyzer = BusinessAnalyzer(url)
        return analyzer.analyze()
    except Exception as e:
        print(f"Error performing business analysis: {str(e)}")
        return {}

def enhance_business_analysis_with_ai(initial_business_data, technical_metrics):
    """
    Enhances business analysis with AI insights.
    
    Args:
        initial_business_data (dict): Initial business analysis data
        technical_metrics (dict): Technical performance metrics
        
    Returns:
        dict: Enhanced business analysis with AI insights
    """
    try:
        # Prepare the prompt for AI
        prompt = f"""
        Analyze this business data and provide enhanced insights:
        
        Initial Business Data:
        {json.dumps(initial_business_data, indent=2)}
        
        Technical Metrics:
        {json.dumps(technical_metrics, indent=2)}
        
        Provide enhanced analysis focusing on:
        1. Market positioning
        2. Competitive advantages
        3. Growth opportunities
        4. Risk factors
        5. Strategic recommendations
        """
        
        # Get AI analysis using new API format
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a business analysis expert."},
                {"role": "user", "content": prompt}
            ]
        )
        
        # Parse and structure the AI response
        ai_insights = json.loads(response.choices[0].message.content)
        
        # Combine with initial analysis
        enhanced_analysis = {
            **initial_business_data,
            'ai_insights': ai_insights
        }
        
        return enhanced_analysis
    except Exception as e:
        print(f"Error enhancing business analysis: {str(e)}")
        return initial_business_data

def generate_seo_analysis(metrics, business_analysis):
    """
    Generates comprehensive SEO analysis report.
    
    Args:
        metrics (dict): SEO performance metrics
        business_analysis (dict): Business analysis data
        
    Returns:
        dict: Comprehensive SEO analysis report with the following structure:
            {
                'executive_summary': str,
                'recommendations': list of dicts with 'title' and 'description',
                'priority_actions': list of dicts with 'title', 'priority', 'impact', 'effort'
            }
    """
    try:
        # Prepare the prompt for AI
        prompt = f"""
        Analyze this website data and provide SEO insights:
        
        Website Metrics:
        {json.dumps(metrics, indent=2)}
        
        Business Analysis:
        {json.dumps(business_analysis, indent=2)}
        
        Provide a comprehensive SEO analysis with:
        1. Executive Summary
        2. Key Recommendations
        3. Priority Actions
        
        Format the response as a JSON object with these fields:
        - executive_summary: A concise overview of the website's SEO status
        - recommendations: List of objects with 'title' and 'description'
        - priority_actions: List of objects with 'title', 'priority', 'impact', 'effort'
        """
        
        # Get AI analysis using new API format
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an SEO analysis expert. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        # Parse and structure the AI response
        ai_analysis = json.loads(response.choices[0].message.content)
        
        # Ensure all required fields are present
        required_fields = ['executive_summary', 'recommendations', 'priority_actions']
        for field in required_fields:
            if field not in ai_analysis:
                ai_analysis[field] = [] if field in ['recommendations', 'priority_actions'] else "No analysis available"
        
        return ai_analysis
        
    except Exception as e:
        print(f"Error generating SEO analysis: {str(e)}")
        return {
            'executive_summary': "Error generating analysis",
            'recommendations': [],
            'priority_actions': []
        } 