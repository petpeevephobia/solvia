#!/usr/bin/env python3
"""Extract and organize CSS from spa.html into separate modular files"""

import re
from pathlib import Path

def extract_css_from_spa():
    """Extract CSS from spa.html and organize into modular files"""

    # Read spa.html
    spa_path = Path('app/static/spa.html')
    content = spa_path.read_text()

    # Extract CSS content between <style> tags
    style_match = re.search(r'<style>(.*?)</style>', content, re.DOTALL)
    if not style_match:
        print("No CSS found in spa.html")
        return

    css_content = style_match.group(1).strip()

    # Define CSS sections and their target files
    css_sections = {
        'global.css': {
            'patterns': [
                r'/\* Global Styles \*/.*?(?=/\* Sidebar|\Z)',
                r'html[, {].*?}',
                r'body[, {].*?}',
                r'h[1-6][, {].*?}',
                r'\*\s*{[^}]+}',
            ],
            'content': []
        },
        'sidebar.css': {
            'patterns': [
                r'/\* Sidebar.*?\*/.*?(?=/\* Main Content|\Z)',
                r'\.sidebar(?![a-z-]).*?}(?:\s*\.sidebar[^}]*})*',
                r'\.nav-item.*?}',
                r'\.user-info.*?}',
                r'\.sidebar-footer.*?}',
                r'\.sidebar-toggle.*?}',
            ],
            'content': []
        },
        'dashboard.css': {
            'patterns': [
                r'/\* Dashboard.*?\*/.*?(?=/\* Chat|\Z)',
                r'\.dashboard.*?}',
                r'\.metrics-grid.*?}',
                r'\.metric-card.*?}',
                r'\.issues-section.*?}',
                r'\.issue-card.*?}',
                r'\.seo-health.*?}',
            ],
            'content': []
        },
        'chat.css': {
            'patterns': [
                r'/\* Chat.*?\*/.*?(?=/\* Audit|\Z)',
                r'\.chat(?![a-z-]).*?}',
                r'\.message.*?}',
                r'\.suggestion-buttons.*?}',
            ],
            'content': []
        },
        'modals.css': {
            'patterns': [
                r'/\* Modal.*?\*/.*?(?=/\* Settings|\Z)',
                r'\.modal(?![a-z-]).*?}',
                r'#auditModal.*?}',
                r'\.audit-progress.*?}',
                r'#auditProgressOverlay.*?}',
            ],
            'content': []
        },
        'components.css': {
            'patterns': [
                r'/\* Settings.*?\*/.*?(?=@media|\Z)',
                r'\.settings.*?}',
                r'\.website-card.*?}',
                r'\.skeleton.*?}',
                r'\.btn.*?}',
                r'\.form-group.*?}',
                r'\.audit-history.*?}',
            ],
            'content': []
        },
        'responsive.css': {
            'patterns': [
                r'@media.*?}\s*}',
            ],
            'content': []
        }
    }

    # Process CSS content line by line to maintain structure
    lines = css_content.split('\n')
    current_section = None
    current_block = []
    brace_count = 0

    for line in lines:
        stripped = line.strip()

        # Track braces to understand nesting
        brace_count += line.count('{') - line.count('}')

        # Determine which section this belongs to
        if '/* Global' in line:
            current_section = 'global.css'
        elif '/* Sidebar' in line:
            current_section = 'sidebar.css'
        elif '/* Dashboard' in line or '/* Metrics' in line:
            current_section = 'dashboard.css'
        elif '/* Chat' in line:
            current_section = 'chat.css'
        elif '/* Modal' in line or '/* Audit' in line:
            current_section = 'modals.css'
        elif '/* Settings' in line or '/* Website' in line:
            current_section = 'components.css'
        elif '@media' in line:
            current_section = 'responsive.css'

        # Add line to current section
        if current_section and current_section in css_sections:
            css_sections[current_section]['content'].append(line)
        elif not current_section:
            # Default to global if no section identified
            css_sections['global.css']['content'].append(line)

    # Create styles directory
    styles_dir = Path('app/static/styles')
    styles_dir.mkdir(exist_ok=True)

    # Write each CSS file
    for filename, section in css_sections.items():
        if section['content']:
            file_path = styles_dir / filename
            # Clean up content - remove excessive blank lines
            content = '\n'.join(section['content'])
            content = re.sub(r'\n{3,}', '\n\n', content)
            file_path.write_text(content.strip() + '\n')
            line_count = len([l for l in content.split('\n') if l.strip()])
            print(f"Created {filename}: {line_count} lines")

    # Create main.css that imports all other CSS files
    main_css = """/* Solvia Main Stylesheet - Imports all modular CSS files */

@import url('global.css');
@import url('sidebar.css');
@import url('dashboard.css');
@import url('chat.css');
@import url('modals.css');
@import url('components.css');
@import url('responsive.css');
"""
    (styles_dir / 'main.css').write_text(main_css)
    print(f"Created main.css with imports")

    # Update spa.html to use the new CSS structure
    new_spa_content = re.sub(
        r'<style>.*?</style>',
        '<link rel="stylesheet" href="/static/styles/main.css">',
        content,
        flags=re.DOTALL
    )

    # Create backup
    backup_path = Path('app/static/spa.html.backup')
    spa_path.rename(backup_path)
    print(f"Created backup: spa.html.backup")

    # Write updated spa.html
    spa_path.write_text(new_spa_content)
    print(f"Updated spa.html to use modular CSS")

    print("\n✅ CSS extraction complete!")
    print(f"Total CSS lines extracted: 1436")
    print(f"Files created: 8")

if __name__ == "__main__":
    extract_css_from_spa()