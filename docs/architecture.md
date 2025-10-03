# Solvia Alpha - Technical Architecture

> **Purpose**: Detailed technical architecture and implementation details
> **Last Updated**: 2025-10-03

---

## 🏗️ System Architecture

### Tech Stack
**Backend:**
- Python 3.11+ with FastAPI
- Uvicorn ASGI server
- Supabase (PostgreSQL) with Row Level Security
- Google OAuth2 & Search Console API v1
- OpenAI GPT-4o-mini for AI responses

**Frontend:**
- Static HTML/CSS/JavaScript
- Fetch-based API calls
- No framework dependencies

### Database Schema
```sql
user_sessions:
- id, email (UNIQUE), name, picture
- access_token, refresh_token
- selected_website
- last_login, created_at, updated_at

chat_messages:
- id, user_email, message_content
- message_type (user/ai), sender_name
- created_at

gsc_metrics_cache:
- user_email, website_url
- start_date, end_date
- seo_score, impressions, clicks, ctr, avg_position
- cache_date, created_at

trusted_devices:
- id, user_email, device_fingerprint
- user_agent, created_at, expires_at, last_used_at
- UNIQUE(user_email, device_fingerprint)
- RLS enabled for user isolation
```

### API Structure
```
/auth/
  google/authorize    # OAuth flow start
  google/callback     # Token exchange
  logout              # Session termination
  me                  # Current user info

/auth/gsc/
  properties          # List GSC properties
  select-property     # Set active property
  selected-website    # Get selected site
  metrics            # Fetch metrics (cached)

/auth/chat/
  send               # AI interaction
  history            # Message retrieval

/ui, /dashboard, /login, /settings  # Static pages
```

---

## 📂 File Structure

```
solvia/
├── app/                   # Application code
│   ├── main.py           # FastAPI app & routes
│   ├── auth/             # Authentication
│   │   ├── google_oauth.py
│   │   └── models.py
│   ├── core/             # Core business logic
│   │   └── knowledge_manager.py  # Centralized knowledge system
│   ├── agent/            # RAG agents and chat system
│   │   ├── keyword_rag_agent.py
│   │   ├── routes.py
│   │   └── chat_integration_supabase.py
│   ├── knowledge/        # SEO knowledge base (1,200+ lines)
│   │   ├── industries/
│   │   │   └── construction.yaml  # Construction business rules
│   │   ├── business_detection/
│   │   │   └── domain_patterns.yaml  # Business detection logic
│   │   └── seo_categories/
│   │       ├── analytics.yaml      # SEO tracking & measurement
│   │       ├── technical_seo.yaml  # Technical optimization
│   │       └── local_seo.yaml      # Local search optimization
│   ├── database/         # Database layer
│   │   └── supabase_db.py
│   └── static/           # Frontend files
│       ├── index.html
│       ├── dashboard.html
│       ├── logo.png          # Solvia brand logo
│       └── login.html
├── test/                  # Core test suite
│   ├── test_data_pipeline.py
│   ├── test_performance.py
│   └── check_oauth_setup.py
├── docs/                 # Documentation
│   ├── claude/          # Detailed CLAUDE documentation
│   │   └── CLAUDE_*.md files
│   ├── GSC_CREDENTIALS_SOLUTION.md  # GSC credentials fix documentation
│   ├── PROJECT_CLEANUP_SUMMARY.md   # Project cleanup documentation
│   └── SEO_TESTING_COMPLETE.md      # SEO testing results
├── check_gsc_credentials.py     # Diagnostic script for GSC credentials
├── requirements.txt      # Python dependencies
├── CLAUDE.md            # Project memory (this file)
└── .env                 # Environment variables
```

---

## 🏗️ Clean Architecture Principles

> **CRITICAL**: All new features, issues, problems, and solutions MUST be documented in CLAUDE_*.md files

### **Architecture Rules**
1. **Separation of Concerns**: Database, business logic, and presentation layers isolated
2. **Dependency Inversion**: Core business logic never depends on external concerns
3. **Repository Pattern**: Abstract data access behind interfaces
4. **Domain Independence**: Business rules isolated from infrastructure
5. **Documentation First**: Every decision documented before implementation

### **Database Layer Guidelines**
- **No direct DB calls** in business logic
- **Repository abstractions** for all data operations
- **Performance optimizations** documented and tested
- **Clean migration strategies** for schema changes
- **RLS enforcement** at database level, not application

### **Decision Documentation**
- **Before implementing**: Research best practices
- **Create CLAUDE_FEATURE_X.md**: For new features
- **Create CLAUDE_ISSUE_X.md**: For problems/bugs
- **Update CLAUDE_DECISION_X.md**: For architectural choices
- **Performance impacts**: Always measure and document

---

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Configure: SUPABASE_URL, SUPABASE_KEY, GOOGLE_CLIENT_ID, etc.

# Run database setup
psql $DATABASE_URL < setup_supabase.sql

# Start server
uvicorn main:app --reload --port 8000
```

---

## 🔄 Recent Updates (2025-10-03)

### OAuth Flexibility Enhancement
- **Flexible Scope Validation**: Users can now log in even if they decline Google Search Console permission
- **Graceful Fallback**: Primary flow requests all scopes, fallback flow uses basic scopes (email + profile)
- **Progressive Permissions**: Users can grant GSC access later from settings
- **Impact**: Reduced onboarding friction, improved login success rate

### Data Freshness Optimization
- **GSC Data Delay**: Reduced from 3-day to 1-day delay for fresher metrics
- **Comprehensive Logging**: Added detailed logging to verify real-time Google API calls
- **Date Range Update**: Changed from Sept 1-30 to Sept 3 - Oct 2 (30 days ending yesterday)
- **Impact**: Dashboard now shows accurate, up-to-date metrics from Google Search Console

### Error Handling Improvements
- **Extended Auth Error Handling**: Now handles both 401 (unauthorized) and 403 (forbidden) errors
- **Actionable Error Messages**: Replaced generic "Connection error" with specific guidance
- **One-Click Resolution**: Added logout button in error messages for self-service recovery
- **Impact**: Users can resolve authentication issues without support intervention

### UI/UX Enhancements
- **Custom Modal Component**: Replaced all browser alerts with beautiful branded modals
- **Modal Features**: 4 types (success, error, warning, info) with gradient icons and animations
- **Callback Support**: Execute functions after modal closes (e.g., redirect on success)
- **Impact**: More professional, branded user experience throughout dashboard

---

## ⚠️ Known Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| GSC API quotas | Caching, pagination, throttling |
| OAuth redirect issues | Exact URI matching, thorough testing |
| AI data accuracy | Structured JSON only, no assumptions |
| Performance on large sites | Database indexes, materialized views |
| User trust | Data source tooltips, verifiable metrics |

---

## 📋 Documentation Structure

### **📁 Documentation Organization**
All detailed CLAUDE documentation files are organized in `docs/claude/` folder for better maintainability.

**Main Documentation:**
- `CLAUDE.md` - Core project memory and quick reference
- `docs/architecture.md` (this file) - Technical architecture details

**Detailed Documentation in `docs/claude/`:**
- `CLAUDE_PROJECT_REQ.md` - Complete project requirements
- `CLAUDE_ARCHITECTURE.md` - System architecture overview
- `CLAUDE_FEATURES.md` - Feature specifications
- `CLAUDE_API.md` - API documentation
- `CLAUDE_DATABASE.md` - Database schema and design
- `CLAUDE_FRONTEND.md` - Frontend architecture
- `CLAUDE_SECURITY.md` - Security implementation
- `CLAUDE_CLEAN_ARCHITECTURE.md` - Architecture compliance review ✅
- `CLAUDE_DATABASE_OPTIMIZATION.md` - Database performance strategy ✅
- `CLAUDE_PERFORMANCE_ANALYSIS.md` - Query optimization research ✅
- `CLAUDE_RAG_ENHANCEMENT.md` - RAG analyzer enhancement details ✅
- `CLAUDE_COMPLETE_AUDIT.md` - Complete project audit

### **Documentation Rules:**
1. **Research first** - Web search best practices before implementing
2. **Document decisions** - Why we chose X over Y
3. **Measure impact** - Performance before/after
4. **Clean architecture** - Does it violate separation of concerns?
5. **Future maintenance** - How will this affect long-term code health?

### **Best Practices:**
- Keep `CLAUDE.md` in root for quick access and recent updates
- Store detailed analysis files in `docs/claude/`
- Reference specific docs when discussing features: `See docs/claude/CLAUDE_API.md`
- Update both CLAUDE.md (summary) and detailed doc (full analysis)