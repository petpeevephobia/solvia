import os

def load_prompt(filename):
    """
    Load a prompt template from the app/auth/prompts directory.
    
    Args:
        filename (str): Name of the prompt file
        
    Returns:
        str: The prompt template content
    """
    prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app', 'auth', 'prompts', filename)
    with open(prompt_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # If the content contains a JSON template, clean it up
    if 'REQUIRED OUTPUT FORMAT (JSON):' in content:
        # Split the content at the JSON format marker
        parts = content.split('REQUIRED OUTPUT FORMAT (JSON):')
        if len(parts) > 1:
            # Clean up the JSON template part
            json_template = parts[1].strip()
            # Remove any markdown code block markers
            json_template = json_template.replace('```json', '').replace('```', '').strip()
            # Remove newlines and extra spaces from the JSON
            json_template = ' '.join(json_template.split())
            # Reconstruct the content
            content = parts[0] + 'REQUIRED OUTPUT FORMAT (JSON):\n' + json_template
            
    return content 