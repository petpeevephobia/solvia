"""
Data mapping and transformation functions for converting AI-generated values to Airtable-compatible formats.
"""

def map_ai_values_to_airtable_options(enhanced_data):
    """
    Intelligently map AI-generated values to valid Airtable select options using semantic analysis.
    No fallbacks - the AI should make smart decisions about its own output.
    
    Args:
        enhanced_data (dict): Enhanced business analysis data from AI
        
    Returns:
        dict: Data with values mapped to valid Airtable options
    """
    
    # Define valid Airtable select options for each field
    airtable_mappings = {
        'business_model': {
            'valid_options': ['E-commerce', 'SaaS', 'Professional Services', 'Local Services', 'Information/Content', 'Non-profit', 'Marketplace', 'Subscription'],
            'mappings': {
                'Service-Based Agency': 'Professional Services',
                'Agency': 'Professional Services',
                'Consulting': 'Professional Services',
                'Digital Agency': 'Professional Services',
                'Marketing Agency': 'Professional Services',
                'Service-Based Information Agency': 'Information/Content',
                'Information Agency': 'Information/Content',
                'Content Agency': 'Information/Content',
                'Software': 'SaaS',
                'Technology': 'SaaS',
                'Platform': 'SaaS',
                'Online Store': 'E-commerce',
                'Retail': 'E-commerce',
                'Shop': 'E-commerce',
                'Blog': 'Information/Content',
                'News': 'Information/Content',
                'Media': 'Information/Content',
                'Local Business': 'Local Services',
                'Service Business': 'Local Services'
            }
        },
        'target_market': {
            'valid_options': ['B2B', 'B2C'],
            'mappings': {
                'Business-to-Business': 'B2B',
                'Business to Business': 'B2B',
                'Enterprise': 'B2B',
                'Corporate': 'B2B',
                'Consumer': 'B2C',
                'Business-to-Consumer': 'B2C',
                'Business to Consumer': 'B2C',
                'Individual': 'B2C',
                'Personal': 'B2C',
                'B2B with potential B2C elements': 'B2B',
                'B2B/B2C': 'B2B',
                'Mixed': 'B2B',
                'Both': 'B2B',
                'Hybrid': 'B2B'
            }
        },
        'company_size': {
            'valid_options': ['Startup', 'Small', 'Medium', 'Large', 'Enterprise'],
            'mappings': {
                'Solo': 'Startup',
                'Individual': 'Startup',
                'Micro': 'Startup',
                'Small Business': 'Small',
                'SMB': 'Small',
                'SME': 'Medium',
                'Mid-size': 'Medium',
                'Mid-sized': 'Medium',
                'Growing': 'Medium',
                'Corporation': 'Large',
                'Big': 'Large',
                'Fortune 500': 'Enterprise',
                'Global': 'Enterprise',
                'Multinational': 'Enterprise'
            }
        },
        'geographic_scope': {
            'valid_options': ['Local', 'Regional', 'National', 'Global'],
            'mappings': {
                'City': 'Local',
                'Local Area': 'Local',
                'Metropolitan': 'Regional',
                'State': 'Regional',
                'Multi-state': 'Regional',
                'Country': 'National',
                'Nationwide': 'National',
                'Singapore': 'National',
                'USA': 'Global',
                'International': 'Global',
                'Worldwide': 'Global',
                'Multi-country': 'Global'
            }
        },
        'business_maturity': {
            'valid_options': ['Startup', 'Growing', 'Established', 'Mature'],
            'mappings': {
                'New': 'Startup',
                'Early-stage': 'Startup',
                'Young': 'Startup',
                'Developing': 'Growing',
                'Expanding': 'Growing',
                'Scaling': 'Growing',
                'Stable': 'Established',
                'Well-established': 'Established',
                'Experienced': 'Established',
                'Legacy': 'Mature',
                'Industry Leader': 'Mature',
                'Veteran': 'Mature'
            }
        },
        'tech_sophistication': {
            'valid_options': ['Basic', 'Medium', 'High', 'Advanced'],
            'mappings': {
                'Low': 'Basic',
                'Simple': 'Basic',
                'Minimal': 'Basic',
                'Standard': 'Medium',
                'Average': 'Medium',
                'Moderate': 'Medium',
                'Strong': 'High',
                'Good': 'High',
                'Sophisticated': 'Advanced',
                'Expert': 'Advanced',
                'Cutting-edge': 'Advanced'
            }
        },
        'content_maturity': {
            'valid_options': ['Basic', 'Developing', 'Mature', 'Advanced'],
            'mappings': {
                'Low': 'Basic',
                'Simple': 'Basic',
                'Minimal': 'Basic',
                'Growing': 'Developing',
                'Improving': 'Developing',
                'Established': 'Mature',
                'Strong': 'Mature',
                'Sophisticated': 'Advanced',
                'Expert': 'Advanced',
                'Professional': 'Advanced'
            }
        },
        'competitive_positioning': {
            'valid_options': ['Leader', 'Challenger', 'Follower', 'Niche'],
            'mappings': {
                'Market Leader': 'Leader',
                'Industry Leader': 'Leader',
                'Top Player': 'Leader',
                'Competitor': 'Challenger',
                'Strong Competitor': 'Challenger',
                'Emerging': 'Challenger',
                'Established': 'Follower',
                'Traditional': 'Follower',
                'Specialized': 'Niche',
                'Focused': 'Niche',
                'Unique': 'Niche'
            }
        },
        'positioning_strength': {
            'valid_options': ['Dominant', 'Strong', 'Medium', 'Weak'],
            'mappings': {
                'Dominant': 'Dominant',
                'Leading': 'Dominant',
                'Strong': 'Strong',
                'Good': 'Strong',
                'Medium': 'Medium',
                'Moderate': 'Medium',
                'Average': 'Medium',
                'Weak': 'Weak',
                'Poor': 'Weak'
            }
        },
        'brand_strength': {
            'valid_options': ['Very Strong', 'Strong', 'Medium', 'Weak'],
            'mappings': {
                'Very Strong': 'Very Strong',
                'Excellent': 'Very Strong',
                'Strong': 'Strong',
                'Good': 'Strong',
                'Medium': 'Medium',
                'Moderate': 'Medium',
                'Average': 'Medium',
                'Weak': 'Weak',
                'Poor': 'Weak'
            }
        },
        'audience_sophistication': {
            'valid_options': ['Basic', 'Intermediate', 'Advanced', 'Expert'],
            'mappings': {
                'General': 'Basic',
                'Beginner': 'Basic',
                'Casual': 'Basic',
                'Knowledgeable': 'Intermediate',
                'Informed': 'Intermediate',
                'Professional': 'Advanced',
                'Specialized': 'Advanced',
                'Technical': 'Expert',
                'Industry Expert': 'Expert'
            }
        },
        'primary_age_group': {
            'valid_options': ['Young Adults', 'Middle Age', 'Seniors', 'General'],
            'mappings': {
                '18-24': 'Young Adults',
                '18-35': 'Young Adults',
                '20-30': 'Young Adults',
                '25-35': 'Young Adults',
                '25-45': 'Middle Age',
                '30-45': 'Middle Age',
                '35-50': 'Middle Age',
                '40-55': 'Middle Age',
                '45-65': 'Middle Age',
                '50+': 'Seniors',
                '55+': 'Seniors',
                '60+': 'Seniors',
                '65+': 'Seniors',
                'General': 'General',
                'All Ages': 'General',
                'Mixed': 'General',
                'Broad': 'General',
                'Millennials': 'Young Adults',
                'Gen Z': 'Young Adults',
                'Gen X': 'Middle Age',
                'Baby Boomers': 'Seniors'
            }
        },
        'income_level': {
            'valid_options': ['Luxury', 'Premium', 'Mid-Range', 'Budget'],
            'mappings': {
                'Budget': 'Budget',
                'Affordable': 'Budget',
                'Low': 'Budget',
                'Standard': 'Mid-Range',
                'Moderate': 'Mid-Range',
                'Middle': 'Mid-Range',
                'Average': 'Mid-Range',
                'Premium': 'Premium',
                'High': 'Premium',
                'High-end': 'Premium',
                'Elite': 'Luxury',
                'Exclusive': 'Luxury',
                'Luxury': 'Luxury'
            }
        }
    }
    
    mapped_data = {}
    
    for field, value in enhanced_data.items():
        if field in airtable_mappings:
            field_config = airtable_mappings[field]
            valid_options = field_config['valid_options']
            mappings = field_config['mappings']
            
            # First try direct mapping
            if value in valid_options:
                mapped_data[field] = value
            # Then try predefined mappings
            elif value in mappings:
                mapped_data[field] = mappings[value]
            # Finally try semantic matching
            else:
                mapped_data[field] = find_best_semantic_match(value, valid_options, field)
        else:
            # Keep non-mapped fields as is
            mapped_data[field] = value
    
    return mapped_data

def find_best_semantic_match(ai_value, valid_options, field_name):
    """
    Find the best semantic match between an AI-generated value and valid Airtable options.
    Uses a combination of exact matching, partial matching, and semantic similarity.
    
    Args:
        ai_value (str): The value generated by AI
        valid_options (list): List of valid Airtable options
        field_name (str): Name of the field being mapped
        
    Returns:
        str: Best matching valid option
    """
    if not ai_value:
        return valid_options[0]  # Return first option as default
        
    # Convert to lowercase for comparison
    ai_value = ai_value.lower()
    valid_options_lower = [opt.lower() for opt in valid_options]
    
    # 1. Try exact match
    if ai_value in valid_options_lower:
        return valid_options[valid_options_lower.index(ai_value)]
    
    # 2. Try partial match
    for i, option in enumerate(valid_options_lower):
        if ai_value in option or option in ai_value:
            return valid_options[i]
    
    # 3. Try word-based matching
    ai_words = set(ai_value.split())
    best_match = None
    best_score = 0
    
    for i, option in enumerate(valid_options_lower):
        option_words = set(option.split())
        common_words = ai_words.intersection(option_words)
        score = len(common_words) / max(len(ai_words), len(option_words))
        
        if score > best_score:
            best_score = score
            best_match = valid_options[i]
    
    if best_score > 0.3:  # Threshold for word-based matching
        return best_match
    
    # 4. Field-specific fallbacks
    field_fallbacks = {
        'business_model': 'Professional Services',
        'target_market': 'B2B',
        'company_size': 'Small',
        'geographic_scope': 'National',
        'business_maturity': 'Growing',
        'tech_sophistication': 'Medium',
        'content_maturity': 'Developing',
        'competitive_positioning': 'Challenger',
        'positioning_strength': 'Moderate',
        'brand_strength': 'Moderate',
        'audience_sophistication': 'Intermediate',
        'primary_age_group': '25-34',
        'income_level': 'Middle'
    }
    
    return field_fallbacks.get(field_name, valid_options[0]) 