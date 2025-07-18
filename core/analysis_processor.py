import os
import json
from urllib.parse import urlparse
import openai
from core.modules.prompt_loader import load_prompt

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


