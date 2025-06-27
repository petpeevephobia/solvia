import os
import json
from urllib.parse import urlparse
import openai
from core.modules.business_analysis import BusinessAnalyzer
from core.modules.report_generator import ReportGenerator
from core.modules.prompt_loader import load_prompt
from .recommendation_aggregator import RecommendationAggregator

model = "gpt-4o-mini"

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
    Detects potential keyword cannibalization issues and returns a risk level.
    
    Args:
        keywords_data (list): List of keyword performance data
        
    Returns:
        str: Risk level ('High', 'Medium', or 'Low')
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
        
        # Count high-risk groups
        high_risk_groups = 0
        medium_risk_groups = 0
        
        # Analyze each group for cannibalization
        for main_keyword, similar_keywords in keyword_groups.items():
            if len(similar_keywords) > 1:
                if len(similar_keywords) > 3:
                    high_risk_groups += 1
                else:
                    medium_risk_groups += 1
        
        # Determine overall risk level
        if high_risk_groups > 0:
            return 'High'
        elif medium_risk_groups > 0:
            return 'Medium'
        else:
            return 'Low'
            
    except Exception as e:
        print(f"Error detecting cannibalization: {str(e)}")
        return 'Low'  # Default to Low risk if there's an error

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
        try:
            print("Making API request...")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an SEO strategist and SaaS product assistant for early-stage founders. You MUST respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "json_object" }
            )
            print("API request completed")
            
            # Extract and parse the analysis
            print("Processing API response...")
            print(f"Response object type: {type(response)}")
            print(f"Response object: {response}")
            print(f"Choices available: {response.choices}")
            
            if not response.choices:
                print("No choices in response")
                return {}
                
            analysis_text = response.choices[0].message.content
            print(f"\tRaw OpenAI Response: {analysis_text}")
            
            if not analysis_text:
                print("Empty response content")
                return {}
                
            try:
                analysis = json.loads(analysis_text)
                print(f"\tParsed JSON: {json.dumps(analysis, indent=2)}")
                # Validate required fields
                if not isinstance(analysis, dict):
                    print("Analysis is not a dictionary")
                    raise ValueError("Analysis must be a dictionary")
                if "executive_summary" not in analysis:
                    print("Missing executive_summary in response")
                    raise ValueError("Missing required field: executive_summary")
                if "recommendations" not in analysis:
                    print("Missing recommendations in response")
                    raise ValueError("Missing required field: recommendations")
                if not isinstance(analysis["recommendations"], list):
                    print("Recommendations is not a list")
                    raise ValueError("Recommendations must be a list")
                print("Analysis validation successful")
                return analysis
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON response: {str(e)}")
                print(f"Raw response: {analysis_text}")
                return {}
            except ValueError as e:
                print(f"Error validating response format: {str(e)}")
                return {}
        except Exception as api_error:
            print(f"OpenAI API Error: {str(api_error)}")
            print(f"Error type: {type(api_error)}")
            print(f"Error details: {api_error.__dict__}")
            return {}
    except Exception as e:
        print(f"Error enhancing business analysis: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Error details: {e.__dict__}")
        return {}

def generate_seo_analysis(website_data, business_context):
    """
    Generate comprehensive SEO analysis with prioritized recommendations.
    
    Args:
        website_data (dict): Website performance and technical data
        business_context (dict): Business analysis context for personalization
        
    Returns:
        dict: Enhanced analysis with prioritized recommendations
    """
    
    # Load the SEO analysis prompt
    current_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(current_dir, 'prompts', 'seo_analysis_json.txt')
    
    try:
        with open(prompt_path, 'r', encoding='utf-8') as file:
            prompt_template = file.read()
    except FileNotFoundError:
        print(f"Prompt file not found at {prompt_path}")
        return {}

    # Prepare analysis data with all available context
    print("Preparing analysis data...")
    analysis_data = {
        'url': website_data.get('url', ''),
        'impressions': website_data.get('impressions', 0),
        'clicks': website_data.get('clicks', 0),
        'ctr': website_data.get('ctr', 0),
        'average_position': website_data.get('average_position', 0),
        'performance_score': website_data.get('performance_score', 0),
        'first_contentful_paint': website_data.get('first_contentful_paint', 0),
        'largest_contentful_paint': website_data.get('largest_contentful_paint', 0),
        'cumulative_layout_shift': website_data.get('cumulative_layout_shift', 0),
        'business_model': business_context.get('business_model', ''),
        'target_market': business_context.get('target_market', ''),
        'industry_sector': business_context.get('industry_sector', ''),
        'company_size': business_context.get('company_size', ''),
        'has_ecommerce': business_context.get('has_ecommerce', False),
        'has_local_presence': business_context.get('has_local_presence', False),
        'business_complexity_score': business_context.get('business_complexity_score', 0),
        'primary_age_group': business_context.get('primary_age_group', ''),
        'income_level': business_context.get('income_level', ''),
        'audience_sophistication': business_context.get('audience_sophistication', ''),
        'services_offered': business_context.get('services_offered', ''),
        'has_public_pricing': business_context.get('has_public_pricing', False),
        'service_count': business_context.get('service_count', 0),
        'geographic_scope': business_context.get('geographic_scope', ''),
        'target_locations': business_context.get('target_locations', ''),
        'is_location_based': business_context.get('is_location_based', False),
        'business_maturity': business_context.get('business_maturity', ''),
        'establishment_year': business_context.get('establishment_year', ''),
        'experience_indicators': business_context.get('experience_indicators', False),
        'platform_detected': business_context.get('platform_detected', ''),
        'has_advanced_features': business_context.get('has_advanced_features', False),
        'social_media_integration': business_context.get('social_media_integration', False),
        'tech_sophistication': business_context.get('tech_sophistication', ''),
        'has_content_marketing': business_context.get('has_content_marketing', False),
        'has_lead_generation': business_context.get('has_lead_generation', False),
        'has_social_proof': business_context.get('has_social_proof', False),
        'content_maturity': business_context.get('content_maturity', ''),
        'phone_prominence': business_context.get('phone_prominence', False),
        'has_contact_forms': business_context.get('has_contact_forms', False),
        'has_live_chat': business_context.get('has_live_chat', False),
        'preferred_contact_method': business_context.get('preferred_contact_method', ''),
        'competitive_positioning': business_context.get('competitive_positioning', ''),
        'positioning_strength': business_context.get('positioning_strength', ''),
        'value_proposition': business_context.get('value_proposition', ''),
        'brand_strength': business_context.get('brand_strength', ''),
        'trust_indicators': business_context.get('trust_indicators', ''),
        'business_insights': business_context.get('business_insights', ''),
        'seo_strategy_recommendations': business_context.get('seo_strategy_recommendations', '')
    }
    print("Analysis data prepared successfully")
    
    # Format the prompt with the analysis data
    print("Formatting prompt...")
    prompt = prompt_template.format(**analysis_data)

    # Get AI analysis using new API format
    print("Calling OpenAI API...")
    client = openai.OpenAI()
    print("Making API request...")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert SEO analyst. Provide detailed, actionable SEO recommendations in valid JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        analysis_text = response.choices[0].message.content.strip()
        print(f"Received response: {len(analysis_text)} characters")
        
        # Clean the response to ensure it's valid JSON
        if analysis_text.startswith('```json'):
            analysis_text = analysis_text[7:]
        if analysis_text.endswith('```'):
            analysis_text = analysis_text[:-3]
        analysis_text = analysis_text.strip()
        
        try:
            analysis = json.loads(analysis_text)
            print(f"\tParsed JSON: {json.dumps(analysis, indent=2)}")
            # Validate required fields
            if not isinstance(analysis, dict):
                print("Analysis is not a dictionary")
                raise ValueError("Analysis must be a dictionary")
            if "executive_summary" not in analysis:
                print("Missing executive_summary in response")
                raise ValueError("Missing required field: executive_summary")
            if "recommendations" not in analysis:
                print("Missing recommendations in response")
                raise ValueError("Missing required field: recommendations")
            if not isinstance(analysis["recommendations"], list):
                print("Recommendations is not a list")
                raise ValueError("Recommendations must be a list")
            
            print("Analysis validation successful")
            
            # 🎯 NEW: Process recommendations through the aggregator
            print("🎯 Processing recommendations through priority aggregator...")
            aggregator = RecommendationAggregator()
            aggregator.set_business_context(business_context)
            aggregator.add_technical_seo_recommendations(analysis)
            
            # Get prioritized recommendations
            prioritized_recs = aggregator.get_prioritized_recommendations()
            quick_wins = aggregator.get_quick_wins()
            action_plan_summary = aggregator.generate_action_plan_summary()
            
            # Enhance the original analysis with prioritized data
            analysis['prioritized_recommendations'] = prioritized_recs
            analysis['quick_wins'] = quick_wins
            analysis['action_plan_summary'] = action_plan_summary
            analysis['recommendation_aggregator_data'] = aggregator.export_recommendations_json()
            
            print(f"\t\t✓ Enhanced analysis with {len(prioritized_recs)} prioritized recommendations")
            print(f"\t\t✓ Identified {len(quick_wins)} quick wins")
            
            return analysis
            
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {str(e)}")
            print(f"Raw response: {analysis_text}")
            return {}
        except ValueError as e:
            print(f"Error validating response format: {str(e)}")
            return {}
    except Exception as api_error:
        print(f"OpenAI API Error: {str(api_error)}")
        print(f"Error type: {type(api_error)}")
        print(f"Error details: {api_error.__dict__}")
        return {}
