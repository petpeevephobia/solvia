# Python to Go V2 - 1:1 Parity Checklist

> **Purpose**: Critical values and logic that MUST match between Python and Go
> **Source**: Extracted from reading 6,648 lines of Python backend code
> **Last Updated**: 2025-12-08

---

## 1. SEO SCORING ENGINE

### Component Weights (MUST MATCH)
| Component | Weight | Python File | Go File |
|-----------|--------|-------------|---------|
| Traffic | 30% (0.30) | `app/core/seo_scoring.py:47` | `internal/shared/scoring/seo_score.go` |
| Position | 25% (0.25) | `app/core/seo_scoring.py:48` | `internal/shared/scoring/seo_score.go` |
| CTR | 25% (0.25) | `app/core/seo_scoring.py:49` | `internal/shared/scoring/seo_score.go` |
| Trends | 20% (0.20) | `app/core/seo_scoring.py:50` | `internal/shared/scoring/seo_score.go` |

### CTR Benchmarks by Position (MUST MATCH)
```
Position 1:  28.5% (0.285)
Position 2:  15.7% (0.157)
Position 3:   9.4% (0.094)
Position 4:   6.2% (0.062)
Position 5:   5.0% (0.050)
Position 6:   3.8% (0.038)
Position 7:   3.0% (0.030)
Position 8:   2.4% (0.024)
Position 9:   2.0% (0.020)
Position 10:  2.5% (0.025)
```
**Source**: `app/core/seo_scoring.py:33-44`

### Grade Thresholds (MUST MATCH)
| Score Range | Grade | Description |
|-------------|-------|-------------|
| >= 80 | Excellent | Outstanding SEO performance |
| >= 60 | Good | Performing well with room for improvement |
| >= 40 | Fair | Needs attention in several areas |
| >= 20 | Poor | Significant problems |
| < 20 | Critical | Minimal or no search visibility |

**Source**: `app/core/seo_scoring.py:337-366`

### Base Score
- **Value**: 25.0
- **When**: No data available (impressions=0, clicks=0, position=0)
- **Source**: `app/core/seo_scoring.py:79`

### SEO Stages (by impressions)
| Stage | Impressions | Description |
|-------|-------------|-------------|
| hidden | < 50 | Minimal search visibility |
| emerging | 50-299 | Starting to appear in results |
| discoverable | 300-1999 | Good search presence |
| trusted | >= 2000 | Strong search authority |

**Source**: `app/core/seo_scoring.py:395-420`

### Scoring Formulas

**Traffic Score** (Lines 176-184):
```python
if clicks <= 0:
    return 0
score = log10(clicks + 1) * 20
return min(100, score)
```

**Position Score** (Lines 187-200):
```python
if position <= 1:
    return 100
elif position <= 10:
    return max(0, 110 - (position * 10))
elif position <= 20:
    return max(0, 20 - position)
else:
    return 0
```

**CTR Score** (Lines 203-221):
```python
expected_ctr = get_expected_ctr(position)
if expected_ctr > 0:
    relative_performance = ctr / expected_ctr
    score = min(100, relative_performance * 50)
else:
    score = min(100, ctr * 1000)
return score
```

**Penalties** (Lines 301-324):
```python
# No visibility penalty
if impressions == 0:
    score *= 0.3  # 70% penalty

# Zero CTR with impressions penalty
elif clicks == 0 and impressions > 100:
    score *= 0.5  # 50% penalty

# Very low CTR penalty
elif impressions > 1000 and ctr < 0.001:
    score *= 0.7  # 30% penalty
```

---

## 2. GSC INTEGRATION

### Cache Timeouts
| Cache | Timeout | Source |
|-------|---------|--------|
| Credentials | 300s (5 min) | `app/auth/google_oauth.py:40` |
| Device Trust | 2,592,000s (30 days) | `app/auth/google_oauth.py:45` |

### API Request Limits
| Parameter | Value | Source |
|-----------|-------|--------|
| Row Limit | 25,000 | `app/auth/google_oauth.py:619` |
| Date Range | 30 days | Multiple locations |
| GSC Data Delay | 1 day | `app/auth/google_oauth.py:580` |

### OAuth Scopes (MUST MATCH)
```python
scopes = [
    "https://www.googleapis.com/auth/webmasters",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"
]
```
**Source**: `app/auth/google_oauth.py:32-37`

### Metrics Calculation
**CTR**: `total_clicks / total_impressions` (NOT average of individual CTRs)
**Position**: `sum(position * impressions) / total_impressions` (weighted average)

**Source**: `app/auth/google_oauth.py:751-758`

---

## 3. PDF GENERATION

### Brand Colors (MUST MATCH)
| Name | Hex | Usage |
|------|-----|-------|
| SOLVIA_ORANGE | #EC6019 | Primary brand color |
| SOLVIA_DARK | #1F2937 | Headers, dark text |
| SOLVIA_GRAY | #6B7280 | Body text |
| SOLVIA_LIGHT_GRAY | #F3F4F6 | Borders |
| SOLVIA_LIGHT_GRAY_BG | #EEEEEE | Quote box background |
| SOLVIA_GREEN | #16A34A | Positive changes |
| SOLVIA_RED | #EF4444 | Negative changes |
| SOLVIA_YELLOW | #F59E0B | Warning/medium score |

**Source**: `app/agent/pdf_generator.py:21-28`

### Font Sizes (MUST MATCH)
| Style | Size | Usage |
|-------|------|-------|
| SolviaTitle | 32pt Bold | Report title |
| SolviaHeading1 | 21pt Bold | Section headings (Summary, Health Score) |
| SolviaHeading2 | 12pt Bold | Sub-sections (Your Next Steps) |
| SolviaBody | 11pt Regular | Body text |
| SolviaQuote | 11pt Regular | Motivational quotes |
| Score Number | 36pt Bold | Score display |
| Score Suffix | 14pt Regular | "/100" suffix |
| Footer | 9pt Regular | Page footer |

**Source**: `app/agent/pdf_generator.py:302-370`

### Page Layout (MUST MATCH)
| Element | Value |
|---------|-------|
| Page Size | Letter (612 x 792 pt) |
| Margins | 50pt all sides |
| Content Width | 512pt (612 - 50 - 50) |
| Progress Bar | 512pt x 36pt |
| Score Circle | 109pt diameter |
| Quote Box | 472pt width (512 - 32 icon - 8 gap) |

**Source**: `app/agent/pdf_generator.py:403-411`

### Score Color Thresholds
| Score | Color |
|-------|-------|
| >= 80 | Green (#16A34A) |
| >= 60 | Yellow (#F59E0B) |
| >= 40 | Orange (#EC6019) |
| < 40 | Red (#EF4444) |

**Source**: `app/agent/pdf_generator.py:261-269`

---

## 4. API ENDPOINTS

### Auth Endpoints
| Method | Path | Function |
|--------|------|----------|
| POST | /auth/login | Email login |
| POST | /auth/register | User registration |
| POST | /auth/refresh | Token refresh |
| POST | /auth/logout | Logout |
| GET | /auth/me | Get current user |
| GET | /auth/google/authorize | Start OAuth flow |
| GET | /auth/google/callback | OAuth callback |

### GSC Endpoints
| Method | Path | Function |
|--------|------|----------|
| GET | /gsc/properties | Get user's GSC properties |
| POST | /gsc/select-property | Select a property |
| GET | /gsc/selected | Get selected property |
| GET | /gsc/metrics | Get metrics with caching |
| POST | /gsc/filter | Apply filters to metrics |
| GET | /gsc/daily | Get daily time series |
| POST | /gsc/refresh | Force refresh metrics |
| POST | /gsc/clear-credentials | Clear GSC credentials |

### Audit Endpoints
| Method | Path | Function |
|--------|------|----------|
| POST | /audit | Create new audit |
| GET | /audit | Get audit history |
| GET | /audit/latest | Get latest audit |
| GET | /audit/:id | Get audit by ID |
| GET | /audit/:id/issues | Get audit with issues |
| GET | /audit/:id/status | Check audit status |
| GET | /audit/:id/progress | Get audit progress |
| GET | /audit/:id/progress/stream | SSE progress stream |
| GET | /audit/:id/pdf | Download PDF |

### Chat Endpoints
| Method | Path | Function |
|--------|------|----------|
| POST | /chat | Send chat message |
| GET | /chat/conversations | Get conversations |
| GET | /chat/conversations/:id | Get conversation |
| DELETE | /chat/conversations/:id | Delete conversation |
| PATCH | /chat/conversations/:id/title | Update title |

### Benchmark Endpoints
| Method | Path | Function |
|--------|------|----------|
| GET | /benchmark/insights | Get benchmark insights |

### Dashboard Endpoints
| Method | Path | Function |
|--------|------|----------|
| GET | /dashboard/cache | Get cached data |
| POST | /dashboard/cache | Save cache |

---

## 5. DATA STRUCTURES

### AuditResult
```go
type AuditResult struct {
    ID              int       // audit_id
    UserEmail       string
    WebsiteURL      string
    SEOScore        float64
    CriticalIssues  int
    HighIssues      int
    MediumIssues    int
    LowIssues       int
    TotalIssues     int
    Status          string    // pending, running, completed, failed
    PDFGenerated    bool
    PDFPath         string
    CreatedAt       time.Time
}
```

### GSCMetrics
```go
type GSCMetrics struct {
    TotalClicks       int
    TotalImpressions  int
    AverageCTR        float64  // Decimal (0.05 = 5%)
    AveragePosition   float64
    ClicksChange      int
    ImpressionsChange int
    CTRChange         float64
    PositionChange    float64
}
```

---

## 6. VERIFICATION CHECKLIST

### Scoring Parity
- [ ] Weights sum to 1.0 (0.30 + 0.25 + 0.25 + 0.20)
- [ ] CTR benchmarks match for positions 1-10
- [ ] Grade thresholds: 80/60/40/20
- [ ] Base score is 25.0 for no data
- [ ] SEO stages: hidden(<50), emerging(50-299), discoverable(300-1999), trusted(>=2000)
- [ ] Traffic score uses log10(clicks+1)*20
- [ ] Position score uses 110-(position*10) formula
- [ ] Penalties applied correctly

### GSC Parity
- [ ] Row limit is 25,000
- [ ] Date range is 30 days
- [ ] CTR calculation: total_clicks/total_impressions
- [ ] Position calculation: weighted average
- [ ] Credentials cache timeout: 5 minutes
- [ ] Device trust timeout: 30 days

### PDF Parity
- [ ] Brand colors match hex values
- [ ] Font sizes match specifications
- [ ] Page layout matches dimensions
- [ ] Score colors at correct thresholds
- [ ] Progress bar has 4 stages
- [ ] Quote box has rounded corners

### API Parity
- [ ] All endpoints implemented
- [ ] Request/response formats match
- [ ] Error codes consistent
- [ ] Authentication flow identical

---

## 7. PDF DATA PROCESSOR (28-Day Changes)

### V1 vs V2 Change Calculation Method
The 28-day changes use "V1 vs V2" method - comparing FIRST day (V1) with LAST day (V2):

```python
# Impressions/Clicks: Percentage change
if v1_value > 0:
    change = ((v2_value - v1_value) / v1_value) * 100
elif v2_value > 0:
    change = 100.0  # From 0 to positive
else:
    change = 0.0

# CTR: Absolute difference in percentage points
ctr_change = v2_ctr - v1_ctr  # e.g., 4.55 percentage points

# Position: Absolute difference (negative = improved)
position_change = v2_position - v1_position  # e.g., -5.9 means improved
```

**Source**: `app/agent/pdf_data_processor.py:119-248`

### SEO Stage Thresholds (MUST MATCH)
```python
SEO_STAGES = {
    'hidden': {
        'threshold_min': 0,
        'threshold_max': 49,
        'threshold_display': '1 impression',
    },
    'emerging': {
        'threshold_min': 50,
        'threshold_max': 299,
        'threshold_display': '50 impressions',
    },
    'discoverable': {
        'threshold_min': 300,
        'threshold_max': 1999,
        'threshold_display': '300 impressions',
    },
    'trusted': {
        'threshold_min': 2000,
        'threshold_max': float('inf'),
        'threshold_display': '2000+ impressions',
    }
}
```

**Source**: `app/agent/pdf_data_processor.py:43-76`

### Max Next Steps
- **Value**: 8
- **Source**: `app/agent/pdf_data_processor.py:504`

### CTR Display Format
- **ALWAYS multiply by 100** to show as percentage
- Example: 0.0909 → "9.09%"
- **Source**: `app/agent/pdf_data_processor.py:572-593`

---

## 8. PDF TEXT CONSTANTS (Rule-Based Text)

### Stage Descriptions
```python
STAGE_DESCRIPTIONS = {
    'hidden': "Your site is still hidden from most search results...",
    'emerging': "Your site is starting to gain visibility...",
    'discoverable': "Your site is becoming more discoverable...",
    'trusted': "Your site has strong search visibility..."
}
```

### Motivational Quotes Page 1
```python
MOTIVATIONAL_QUOTES_PAGE1 = {
    'hidden': "It's okay to be early! Every great site starts in the shadows before it shines...",
    'emerging': "Visibility is growing. Each impression is a step toward discovery.",
    'discoverable': "You're building momentum. Consistency will accelerate your growth.",
    'trusted': "You've established authority. Now focus on expanding your reach."
}
```

### Motivational Quotes Page 2
```python
MOTIVATIONAL_QUOTES_PAGE2 = {
    'hidden': "Your next step is clarity. Make Google's job easier...",
    'emerging': "Focus on content quality and consistency...",
    'discoverable': "Optimize your top performers...",
    'trusted': "Maintain your momentum while exploring new opportunities..."
}
```

### Next Steps - Always Shown
```python
NEXT_STEPS_ALWAYS = [
    "Add internal links between your existing pages",
    "Generate another report after 14 days of these changes being made to track progress"
]
```

### Next Steps - Conditional Triggers
| Condition | Next Step |
|-----------|-----------|
| sitemap not submitted | "Submit sitemap to Google Search Console" |
| ctr < 5 OR avg_position > 10 | "Optimize meta titles with emotional, relevant keywords" |
| total_impressions < 300 | "Write one blog post per week for the next month" |
| unindexed_count > 0 | "Fix indexing issues for X page(s)" |
| total_clicks < 5 | "Focus on content quality and keyword research" |
| avg_position > 20 | "Improve on-page SEO for better rankings" |

### Summary Statement Rules

**Impressions Statement Endings:**
| Impressions | Ending |
|-------------|--------|
| 0 | "Google hasn't discovered your site yet. Submit your sitemap..." |
| 1-49 | "Google recognizes your presence." |
| >= 50 | "Google recognizes your presence and you're building visibility." |

**CTR Statement Endings:**
| CTR | Ending |
|-----|--------|
| < 2% | "That's below average — focus on improving your titles..." |
| 2-5% | "That's a good early signal that your content is relevant..." |
| >= 5% | "That's excellent! Your titles and descriptions are resonating..." |

**Position Statement Endings:**
| Position | Ending |
|----------|--------|
| <= 3 | "Excellent work! Keep maintaining quality to stay at the top." |
| 3-10 | "Getting to the top 3 will take consistency..." |
| 10-20 | "Focus on improving on-page SEO..." |
| > 20 | "Prioritize technical SEO fixes and content optimization..." |

**Source**: `app/agent/pdf_text_constants.py`

---

## 9. ANOMALY DETECTION THRESHOLDS

### Z-Score Thresholds
```python
z_score_thresholds = {
    'warning': 2.0,   # 95% confidence
    'critical': 3.0   # 99.7% confidence
}
```

### Traffic Change Thresholds
| Severity | Threshold |
|----------|-----------|
| critical | -50% (> 50% traffic loss) |
| high | -20% (20-50% traffic loss) |
| medium | -10% (10-20% traffic loss) |

### Position Change Thresholds
| Severity | Threshold |
|----------|-----------|
| critical | +5 positions (dropped 5+) |
| high | +3 positions (dropped 3-5) |
| medium | +2 positions (dropped 2-3) |

### CTR Change Thresholds
| Severity | Threshold |
|----------|-----------|
| critical | -50% CTR drop |
| high | -30% CTR drop |
| medium | -15% CTR drop |

### Impressions Change Thresholds
| Severity | Threshold |
|----------|-----------|
| critical | -60% impression loss |
| high | -30% impression loss |
| medium | -15% impression loss |

**Source**: `app/audit/analyzers/anomaly.py:24-53`

---

## 10. TREND ANALYSIS THRESHOLDS

```python
trend_thresholds = {
    'significant_change': 15,  # 15% change is significant
    'critical_change': 30,     # 30% change is critical
    'trend_reversal': 20,      # 20% opposite direction is reversal
}

min_data_points = 7  # Minimum data points for trend analysis
```

**Source**: `app/audit/analyzers/trends.py:24-31`

---

## 11. RAG AGENT CONFIGURATION

### Default RAGConfig
```python
model = "gpt-4o-mini"
embedding_model = "text-embedding-3-small"
max_context_length = 8000
min_relevance_score = 0.3
max_results = 10
temperature = 0.3
collections_to_search = ['gsc_data', 'audit_results', 'seo_knowledge', 'user_interactions']
```

**Source**: `app/agent/supabase_rag_agent.py:24-34`

### Embedding Dimensions
- **Model**: text-embedding-3-small
- **Dimensions**: 1536

### Document ID Generation
```python
# SHA256 hash, first 16 chars
id_string = f"{user_email}|{collection}|{content[:200]}"
return hashlib.sha256(id_string.encode()).hexdigest()[:16]
```

---

## 12. EMAIL SERVICE

### SMTP Configuration
- **Provider**: Zoho (smtp.zoho.com)
- **Port**: 587
- **TLS**: STARTTLS (start_tls=True, use_tls=False)

### Email Templates
- Brand color: #EC6019 (Solvia Orange)
- Score display: "{score}/100"
- Template includes: Score breakdown, Key metrics, Critical issues, Recommendations

**Source**: `app/agent/email_service.py`

---

## 13. CONVERSATION MEMORY

### Smart Title Keywords
| Keyword | Generated Title |
|---------|----------------|
| 'audit' | "SEO Audit Discussion" |
| 'traffic' | "Traffic Analysis" |
| 'ranking' OR 'position' | "Ranking Insights" |
| 'issue' OR 'problem' | "Issue Troubleshooting" |
| 'improve' OR 'optimize' | "Optimization Strategy" |
| (default) | First 50 chars of message |

### Default Limit
- **Get Conversations**: limit = 20

**Source**: `app/core/conversation_memory.py:229-272`

---

## 14. GSC DATA PIPELINE (detailed_fetcher.py)

### Critical Constants
```python
max_retries = 3           # API retry attempts
retry_delay = 2           # seconds between retries
batch_size = 1000         # Process in batches
row_limit = 25000         # Max GSC API allows per request
```

### Date Range Calculation
```python
# GSC data available within 1-2 days
end_date = datetime.now().date() - timedelta(days=1)

# Full refresh: 16 months (GSC limit)
full_refresh_days = 480

# Default for new users: 90 days
default_days = 90
```

### Data Normalization Rules
```python
# Query text: max 500 chars
query_text = str(row['keys'][0])[:500]

# Page URL: max 2000 chars
page_url = str(row['keys'][0])[:2000]

# CTR: must be 0-1 range
ctr = max(0, min(1, float(row.get('ctr', 0))))

# Position: must be > 0
position = max(0.1, float(row.get('position', 0)))
```

### Metrics Calculation (CRITICAL - Must Match Python)
```python
# CTR = total clicks / total impressions (NOT average of daily CTRs)
avg_ctr = total_clicks / total_impressions if total_impressions > 0 else 0

# Position = weighted average by impressions
weighted_position_sum = sum(row['avg_position'] * row['total_impressions'] for row in data)
avg_position = weighted_position_sum / total_impressions if total_impressions > 0 else 0
```

**Source**: `app/data_pipeline/detailed_fetcher.py:534-543`

---

## 15. DATA PIPELINE SCHEDULER (scheduler.py)

### Rate Limiting Thresholds
```python
# Global limit (1200 requests per minute, with buffer)
global_requests_limit = 1000  # Leave buffer

# Per-user limit (100 requests per 100 seconds per user)
per_user_requests_limit = 80  # Leave buffer

# Check windows
minute_window = 60       # seconds
hundred_second_window = 100  # seconds
```

### Scheduler Configuration
```python
max_concurrent_jobs = 3   # Parallel processing workers
data_retention_days = 365 # Days to keep old data

# Worker delay between jobs
job_delay = 2  # seconds

# Rate limit wait time
rate_limit_wait = 60  # seconds
```

### Job States
| State | Description |
|-------|-------------|
| queued | Added to processing queue |
| processing | Worker picked up the job |
| completed | Successfully processed |
| failed | Error during processing |
| rate_limited | Hit API rate limits |

**Source**: `app/data_pipeline/scheduler.py`

---

## 16. WEBSITE CRAWLER (website_crawler.py)

### Crawler Configuration
```python
timeout = 10              # seconds per page
max_pages = 5             # default max pages to crawl
content_limit = 500       # words for content summary
```

### Business Type Detection Indicators

**Personal Portfolio Indicators:**
```python
personal_indicators = [
    'portfolio', 'resume', 'cv', 'about me', 'my projects',
    'personal', 'freelancer', 'developer', 'designer',
    'software engineer', 'web developer', 'full-stack',
    'years of experience', 'skills', 'github', 'linkedin'
]
# threshold: score > 3 and score > business_score
```

**Business Indicators:**
```python
business_indicators = [
    'services', 'solutions', 'products', 'pricing',
    'contact us', 'our team', 'company', 'corporation',
    'ltd', 'llc', 'inc', 'pte', 'about us'
]
```

### Industry Detection Keywords
| Industry | Keywords |
|----------|----------|
| technology | software, technology, it services, development, programming, coding, api, cloud |
| construction | construction, building, contractor, renovation, architecture, engineering |
| healthcare | health, medical, clinic, hospital, doctor, patient, treatment |
| education | education, learning, school, university, course, training, student |
| ecommerce | shop, store, buy, cart, product, price, checkout, shipping |
| consulting | consulting, advisory, strategy, management, business solutions |
| finance | finance, investment, banking, insurance, loan, credit |
| marketing | marketing, advertising, seo, digital, social media, branding |

### Business Type Outputs
- `personal_portfolio_developer`
- `personal_portfolio_designer`
- `personal_portfolio`
- `{industry}_business` (e.g., `technology_business`)
- `general_business`

**Source**: `app/core/website_crawler.py:182-238`

---

## 17. KNOWLEDGE MANAGER (knowledge_manager.py)

### Knowledge Sources
```
knowledge/
├── business_detection/
│   └── domain_patterns.yaml
├── industries/
│   └── *.yaml
└── seo_categories/
    └── *.yaml
```

### Business Profile Detection
```python
# Confidence calculation
overall_confidence = (industry_confidence + location_confidence) / 2

# Confidence sources:
# - keyword_match: 0.5-0.7
# - tld_match: 0.3-0.5
# - domain_match: 0.5
```

### Industry-Specific Performance Thresholds
```python
# Default thresholds
traffic_thresholds = {'low': 10, 'medium': 50}
position_thresholds = {'page_1': 10}
ctr_thresholds = {'low': 2.0}  # 2% CTR
```

### Issue Severity Mapping
| Metric | Threshold | Severity |
|--------|-----------|----------|
| clicks < 5 | Very low traffic | critical |
| clicks < traffic_low | Low traffic | high |
| avg_position > 10 | Poor rankings | high |
| ctr < 2.0 | Low CTR | medium |

**Source**: `app/core/knowledge_manager.py`

---

## 18. AUDIT PROGRESS TRACKING (audit_progress.py)

### Audit Stages (MUST MATCH)
```python
class AuditStage(str, Enum):
    INITIALIZING = "initializing"               # 0-10%
    FETCHING_GSC_DATA = "fetching_gsc_data"     # 10-30%
    ANALYZING_METRICS = "analyzing_metrics"     # 30-50%
    DETECTING_ISSUES = "detecting_issues"       # 50-70%
    GENERATING_RECOMMENDATIONS = "generating_recommendations"  # 70-85%
    CREATING_REPORT = "creating_report"         # 85-95%
    FINALIZING = "finalizing"                   # 95-100%
    COMPLETED = "completed"                     # 100%
    ERROR = "error"
```

### Progress Percentages (MUST MATCH)
| Stage | Progress | Message |
|-------|----------|---------|
| initializing | 10% | "Starting SEO audit for your website..." |
| fetching_gsc_data | 20% | "Connecting to Google Search Console..." |
| fetching_gsc_data | 30% | "Retrieved search performance data" |
| analyzing_metrics | 40% | "Analyzing SEO metrics and trends..." |
| analyzing_metrics | 50% | "Metrics analysis complete" |
| detecting_issues | 60% | "Scanning for SEO issues..." |
| detecting_issues | 70% | "Identified critical issues" |
| generating_recommendations | 80% | "Creating personalized recommendations..." |
| generating_recommendations | 85% | "Recommendations ready" |
| creating_report | 90% | "Generating PDF report..." |
| creating_report | 95% | "Report generated successfully" |
| finalizing | 98% | "Saving audit results..." |
| completed | 100% | "Audit completed successfully!" |

### SSE Configuration
```python
# Heartbeat timeout
heartbeat_timeout = 30.0  # seconds

# SSE Headers
headers = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no"  # Disable Nginx buffering
}
```

### Database Table
```sql
-- audit_progress table
audit_id VARCHAR
user_email VARCHAR
stage VARCHAR
progress INT
message TEXT
details JSONB
created_at TIMESTAMP
```

**Source**: `app/agent/audit_progress.py`

---

## READING PROGRESS SUMMARY

### Files Read (21 files, ~13,215 lines) - 100% COMPLETE:
| Priority | File | Lines | Status |
|----------|------|-------|--------|
| 1 | app/auth/routes.py | 2,361 | [x] READ |
| 2 | app/agent/routes.py | 1,439 | [x] READ |
| 3 | app/auth/google_oauth.py | 1,422 | [x] READ |
| 4 | app/core/seo_scoring.py | 438 | [x] READ |
| 5 | app/agent/pdf_generator.py | 988 | [x] READ |
| 6 | app/agent/pdf_data_processor.py | 812 | [x] READ |
| 7 | app/agent/pdf_text_constants.py | 431 | [x] READ |
| 8 | app/agent/supabase_rag_agent.py | 643 | [x] READ |
| 9 | app/agent/chat_integration_supabase.py | 302 | [x] READ |
| 10 | app/core/conversation_memory.py | 351 | [x] READ |
| 11 | app/audit/analyzers/anomaly.py | 408 | [x] READ |
| 12 | app/audit/analyzers/trends.py | 358 | [x] READ |
| 13 | app/agent/email_service.py | 267 | [x] READ |
| 14 | app/audit/routes.py | 380 | [x] READ |
| 15 | app/auth/benchmark_analyzer.py | 372 | [x] READ |
| 16 | app/data_pipeline/detailed_fetcher.py | 644 | [x] READ |
| 17 | app/data_pipeline/scheduler.py | 356 | [x] READ |
| 18 | app/core/website_crawler.py | 453 | [x] READ |
| 19 | app/core/knowledge_manager.py | 403 | [x] READ |
| 20 | app/agent/audit_progress.py | 389 | [x] READ |
| 21 | app/database/supabase_client.py | 2 | [x] READ |

---

**Last Verified**: 2025-12-08
**Progress**: 100% of critical backend code read (21/21 files)
