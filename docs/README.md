# Solvia v1.3 - Comprehensive SEO Audit Tool

## 🚀 Features

### Core SEO Metrics
- **Google Search Console**: Impressions, clicks, CTR, average position
- **PageSpeed Insights**: Performance scores, Core Web Vitals (FCP, LCP, TBT, CLS)
- **Index Status**: Coverage state, robots.txt status, last crawl time
- **Sitemap Analysis**: Submission status, errors, warnings
- **Mobile Usability**: Mobile-friendly status and issues

### Advanced Analysis
- **Keyword Performance**: Top keywords, opportunity scoring, intent classification
- **Business Intelligence**: Automated business model detection, target audience analysis
- **Competitive Positioning**: Market positioning and strategy recommendations

### Business Intelligence Features
- **Business Model Detection**: E-commerce, SaaS, Local Services, Professional Services
- **Target Market Analysis**: B2B vs B2C, age demographics, income level
- **Geographic Scope**: Local, National, Multi-Regional, Global
- **Technology Stack**: Platform detection, feature analysis
- **Content Strategy**: Blog presence, lead generation, social proof
- **Competitive Positioning**: Premium, Value, Innovation, Service focus

## 📁 Project Structure

```
Solvia_v1.3/
├── main.py                     # Main application script
├── config/                     # Configuration files
│   └── token.pickle           # Google OAuth credentials
├── data/                      # Data and logs
│   └── debug.log             # Application logs
├── modules/                   # Business logic modules
│ 
├── reports/                   # Generated reports (future)
├── requirements.txt           # Python dependencies
├── .env                      # Environment variables (create this)
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

## 🔧 Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Configuration
Create a `.env` file with:

```env
# Airtable Configuration
AIRTABLE_API_KEY=your_airtable_api_key
AIRTABLE_BASE_ID=your_base_id

# Choose your table structure:
# Option 1: Single table (original) - all 58 columns in one table
USE_ORGANIZED_TABLES=false
AIRTABLE_TABLE_NAME=your_table_name

# Option 2: Organized multi-tables (recommended) - 8 related tables
# USE_ORGANIZED_TABLES=true
# (no table name needed - uses predefined table names)

# Google APIs
PSI_API_KEY=your_pagespeed_insights_key

# Google Search Console (OAuth will handle this)
# No additional keys needed - OAuth flow will generate tokens
```

### 3. Google Search Console Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Search Console API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download `credentials.json` to project root

### 4. PageSpeed Insights API
1. In Google Cloud Console, enable PageSpeed Insights API
2. Create API key and add to `.env` file

### 5. Search Console API (for Mobile Testing)
1. In Google Cloud Console, enable Search Console API
2. Use the same API key as PageSpeed Insights
3. This enables mobile usability testing functionality

## 📊 Airtable Schema

### Required Columns (32 total)

#### Core Metrics
- **url** (URL) - Website URL
- **impressions** (Number) - Search impressions
- **clicks** (Number) - Search clicks  
- **ctr** (Percent) - Click-through rate
- **average_position** (Number) - Average ranking

#### Performance Metrics
- **performance_score** (Percent) - PSI performance score
- **first_contentful_paint** (Number) - FCP in seconds
- **largest_contentful_paint** (Number) - LCP in seconds
- **speed_index** (Number) - Speed index in seconds
- **time_to_interactive** (Number) - TTI in seconds
- **total_blocking_time** (Number) - TBT in milliseconds
- **cumulative_layout_shift** (Number) - CLS score

#### Index & Technical
- **index_verdict** (Single line text) - Index status
- **coverage_state** (Single line text) - Coverage status
- **robots_txt_state** (Single line text) - Robots.txt status
- **indexing_state** (Single line text) - Indexing status
- **last_crawl_time** (Date & time) - Last crawl date
- **page_fetch_state** (Single line text) - Fetch status

#### Sitemap Data
- **sitemaps_submitted** (Long text) - Sitemap list with status
- **sitemap_count** (Number) - Number of sitemaps
- **sitemap_errors** (Number) - Total errors
- **sitemap_warnings** (Number) - Total warnings
- **last_submission** (Date & time) - Last submission date

#### Mobile Usability
- **mobile_friendly_status** (Single line text) - Mobile status
- **mobile_friendly_issues_count** (Number) - Issue count
- **mobile_friendly_issues** (Long text) - Issue details
- **mobile_test_loading_state** (Single line text) - Test status
- **mobile_passed** (Single line text) - Pass/Fail

#### Keyword Analysis
- **top_keywords** (Long text) - Top performing keywords
- **total_keywords_tracked** (Number) - Total keywords found
- **avg_keyword_position** (Number) - Average ranking
- **high_opportunity_keywords** (Number) - High potential keywords
- **branded_keywords_count** (Number) - Branded keywords
- **keyword_cannibalization_risk** (Single line text) - Risk level

#### Business Intelligence
- **business_model** (Single line text) - Business type
- **target_market** (Single line text) - B2B/B2C
- **has_ecommerce** (Checkbox) - E-commerce presence
- **has_local_presence** (Checkbox) - Local business
- **business_complexity_score** (Number) - Complexity (1-10)
- **primary_age_group** (Single line text) - Target age
- **income_level** (Single line text) - Target income
- **audience_sophistication** (Single line text) - Audience level
- **services_offered** (Long text) - Main services
- **has_public_pricing** (Checkbox) - Pricing visibility
- **service_count** (Number) - Number of services
- **geographic_scope** (Single line text) - Geographic reach
- **target_locations** (Long text) - Target locations
- **is_location_based** (Checkbox) - Location relevance
- **business_maturity** (Single line text) - Business stage
- **establishment_year** (Number) - Founded year
- **experience_indicators** (Checkbox) - Experience mentioned
- **platform_detected** (Single line text) - Website platform
- **has_advanced_features** (Checkbox) - Advanced features
- **social_media_integration** (Checkbox) - Social presence
- **tech_sophistication** (Single line text) - Tech level
- **has_content_marketing** (Checkbox) - Content strategy
- **has_lead_generation** (Checkbox) - Lead magnets
- **has_social_proof** (Checkbox) - Testimonials/reviews
- **content_maturity** (Single line text) - Content level
- **phone_prominence** (Checkbox) - Phone visibility
- **has_contact_forms** (Checkbox) - Contact forms
- **has_live_chat** (Checkbox) - Live chat
- **preferred_contact_method** (Single line text) - Contact preference
- **competitive_positioning** (Single line text) - Market position
- **positioning_strength** (Single line text) - Position strength
- **business_insights** (Long text) - Key insights
- **seo_strategy_recommendations** (Long text) - SEO recommendations

## 🚀 Usage

### Run the Analysis
```bash
python main.py
```

### What It Does
1. **Authenticates** with Google Search Console
2. **Fetches URLs** from your Airtable
3. **Analyzes each website** for:
   - SEO performance metrics
   - Technical SEO status
   - Business intelligence
   - Keyword opportunities
4. **Updates Airtable** with comprehensive data
5. **Provides insights** for personalized SEO recommendations

## 📈 Business Intelligence Insights

### Automated Analysis
- **Business Model**: Automatically detects if site is e-commerce, SaaS, local service, etc.
- **Target Market**: Identifies B2B vs B2C focus
- **Geographic Scope**: Determines local, national, or global reach
- **Competitive Position**: Analyzes premium, value, or innovation positioning

### SEO Strategy Recommendations
Based on business analysis, the tool provides personalized recommendations:

**Local Services**: Focus on local SEO, Google My Business, "near me" keywords
**E-commerce**: Product schema, transactional keywords, shopping optimization  
**SaaS**: Problem-solving content, long-tail keywords, trial optimization
**B2B**: Industry expertise, lead generation, professional positioning

## 🔍 Sample Output

```
Processing 1/5: https://example.com
  ✓ Found as domain property
  ✓ Retrieved GSC metrics: 1,234 impressions, 89 clicks
  ✓ PageSpeed Insights: 78% performance score
  ✓ Sitemap analysis: 2 sitemaps, 0 errors
  ✓ Mobile usability: MOBILE_FRIENDLY
  ✓ Keyword analysis: 47 keywords tracked
  ✓ Business intelligence: SaaS, B2B, National scope
  ✓ Successfully updated Airtable record
```

## 🛠 Troubleshooting

### Common Issues
1. **OAuth Errors**: Delete `config/token.pickle` and re-authenticate
2. **Airtable Errors**: Verify column names match exactly
3. **PSI Timeouts**: Reduce batch size or add delays
4. **GSC Permission**: Ensure proper Search Console access

### Error Codes
- **403**: Insufficient permissions in Search Console  
- **422**: Airtable column mismatch
- **429**: API rate limit exceeded
- **500**: Server error (retry later)

## 📝 Version History

### v1.3 (Current)
- ✅ Business Intelligence Module
- ✅ Advanced Keyword Analysis  
- ✅ Organized Project Structure
- ✅ Comprehensive Error Handling
- ✅ 32-column Airtable Schema

### v1.2
- ✅ Mobile Usability Analysis
- ✅ Sitemap Status Checking
- ✅ Enhanced Error Handling

### v1.1  
- ✅ PageSpeed Insights Integration
- ✅ URL Inspection API
- ✅ Improved GSC Handling

### v1.0
- ✅ Basic GSC Metrics
- ✅ Airtable Integration
- ✅ Core Functionality

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Verify your `.env` configuration
3. Ensure all Airtable columns exist
4. Check API quotas and permissions

## 🔐 Security Notes

- Keep your `.env` file secure and never commit it
- `config/token.pickle` contains sensitive OAuth tokens
- Regularly review API access permissions
- Use environment variables for all secrets 