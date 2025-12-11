# Solvia V2 - Project Memory & Architecture Guide

> **Purpose**: SEO audit tool migrated from Python to Go with React frontend
> **Status**: In Development - Achieving 1:1 parity with Python version
> **Last Updated**: 2025-12-03

---

## 🎯 Project Overview

**Solvia V2** is a complete rewrite of the Solvia SEO audit tool:
- **Backend**: Go (Gin) with Clean Architecture
- **Frontend**: React (TypeScript) with Vite + TailwindCSS
- **Database**: PostgreSQL (Supabase)
- **Goal**: 100% feature and logic parity with Python version

### Reference Repository
- **Python Original**: `/Users/jarotekosaputra/Documents/SOLVIA/App/solvia`
- **Go V2**: `/Users/jarotekosaputra/Documents/SOLVIA/App/solvia-v2`

---

## 🏗️ Clean Architecture Principles

### Layer Structure (Dependency Rule: Inward Only)
```
┌─────────────────────────────────────────────────────────┐
│                    EXTERNAL LAYER                        │
│  (Frameworks, Drivers, UI, DB, External Services)       │
├─────────────────────────────────────────────────────────┤
│                   INTERFACE LAYER                        │
│  (Controllers/Handlers, Gateways, Presenters)           │
├─────────────────────────────────────────────────────────┤
│                  APPLICATION LAYER                       │
│  (Use Cases, Application Services, DTOs)                │
├─────────────────────────────────────────────────────────┤
│                    DOMAIN LAYER                          │
│  (Entities, Value Objects, Domain Services, Interfaces) │
└─────────────────────────────────────────────────────────┘
```

### Directory Structure
```
api/
├── cmd/
│   └── api/
│       └── main.go              # Entry point, DI wiring
├── internal/
│   ├── modules/                 # Feature modules (vertical slices)
│   │   ├── auth/
│   │   │   ├── domain/          # Entities, Value Objects
│   │   │   ├── repository/      # Data access interfaces + implementations
│   │   │   ├── service/         # Business logic (use cases)
│   │   │   └── handler/         # HTTP handlers (controllers)
│   │   ├── audit/
│   │   │   ├── domain/
│   │   │   ├── repository/
│   │   │   ├── service/
│   │   │   ├── handler/
│   │   │   ├── analyzers/       # Audit analysis logic
│   │   │   └── pdf/             # PDF generation
│   │   ├── gsc/                 # Google Search Console
│   │   ├── benchmark/           # Benchmark analysis
│   │   ├── chat/                # AI chat
│   │   ├── dashboard/           # Dashboard cache
│   │   ├── website/             # Website content
│   │   └── onpage/              # OnPage analysis
│   ├── infrastructure/          # External services
│   │   ├── database/            # PostgreSQL connection
│   │   ├── google/              # Google OAuth, GSC client
│   │   ├── openai/              # OpenAI client
│   │   ├── firecrawl/           # Firecrawl client
│   │   ├── pdf/                 # PDF generator
│   │   └── email/               # Email service (NEW)
│   ├── shared/                  # Cross-cutting concerns
│   │   ├── config/              # Configuration
│   │   ├── errors/              # Custom errors
│   │   ├── middleware/          # HTTP middleware
│   │   ├── response/            # Response formatting
│   │   ├── scoring/             # SEO scoring engine
│   │   └── adapters/            # Service adapters
│   └── router/                  # HTTP routing
└── reports/                     # Generated PDF reports
```

---

## 📐 Clean Code Standards

### 0. File Size Limits (CRITICAL)

**Maximum Lines of Code per file:**
- **Hard limit**: 1000 LOC (absolute max)
- **Target**: 500 LOC or less
- **Ideal**: 300 LOC

**When file exceeds limit - MUST split:**
```
// ❌ BAD: dashboard_service.go (1200 LOC)
type DashboardService struct { ... }
func (s *DashboardService) GetMetrics() { ... }        // 400 LOC
func (s *DashboardService) GenerateReport() { ... }    // 400 LOC
func (s *DashboardService) ProcessAnalytics() { ... }  // 400 LOC

// ✅ GOOD: Split by responsibility
dashboard/
├── service.go              // Main service, orchestration (200 LOC)
├── metrics_calculator.go   // GetMetrics logic (300 LOC)
├── report_generator.go     // Report generation (300 LOC)
└── analytics_processor.go  // Analytics logic (300 LOC)
```

**Refactoring triggers:**
- File > 500 LOC: Consider splitting
- File > 800 LOC: Plan to split soon
- File > 1000 LOC: **MUST refactor immediately**

**Current files needing refactor:**
- None - All files are under 1000 LOC

### 1. SOLID Principles

#### Single Responsibility (SRP)
```go
// ✅ GOOD: Each struct has one responsibility
type AuditService struct { ... }      // Business logic only
type AuditRepository struct { ... }   // Data access only
type AuditHandler struct { ... }      // HTTP handling only

// ❌ BAD: Mixed responsibilities
type AuditManager struct {
    db *sql.DB           // Data access
    httpClient *http.Client  // External calls
    // Methods that do everything
}
```

#### Open/Closed (OCP)
```go
// ✅ GOOD: Open for extension via interfaces
type Analyzer interface {
    Analyze(ctx context.Context, data *AuditData) ([]Issue, error)
}

type PerformanceAnalyzer struct{}
type TrendAnalyzer struct{}
type OpportunityAnalyzer struct{}
// Add new analyzers without modifying existing code
```

#### Liskov Substitution (LSP)
```go
// ✅ GOOD: Implementations are interchangeable
type TokenGetter interface {
    GetUserTokens(ctx context.Context, email string) (access, refresh string, err error)
}

// Any implementation can be used wherever TokenGetter is expected
type PostgresTokenGetter struct{}
type RedisTokenGetter struct{}
```

#### Interface Segregation (ISP)
```go
// ✅ GOOD: Small, focused interfaces
type DashboardCacheGetter interface {
    GetCache(ctx context.Context, userEmail, websiteURL string) (map[string]interface{}, error)
}

type DashboardCacheSaver interface {
    SaveCache(ctx context.Context, userEmail, websiteURL string, data map[string]interface{}) error
}

// ❌ BAD: Fat interface
type DashboardCacheManager interface {
    GetCache(...) (...)
    SaveCache(...) error
    DeleteCache(...) error
    ClearAllCache(...) error
    GetCacheStats(...) (...)
    // etc.
}
```

#### Dependency Inversion (DIP)
```go
// ✅ GOOD: Depend on abstractions
type BenchmarkService struct {
    tokenGetter    TokenGetter        // Interface
    websiteGetter  WebsiteGetter      // Interface
    dashboardCache DashboardCacheGetter // Interface
}

// ❌ BAD: Depend on concretions
type BenchmarkService struct {
    db *pgxpool.Pool        // Concrete type
    httpClient *http.Client // Concrete type
}
```

### 2. Naming Conventions

```go
// Packages: lowercase, single word
package audit
package gsc
package scoring

// Interfaces: verb or capability suffix
type Reader interface { Read() }
type TokenGetter interface { GetUserTokens() }
type Analyzer interface { Analyze() }

// Structs: nouns
type AuditService struct {}
type BenchmarkInsights struct {}

// Functions: verb + noun
func CalculateGSCScore() {}
func GetSEOStage() {}
func ProcessPDFData() {}

// Constants: descriptive
const WeightTraffic = 0.30
const BaseScore = 25.0
```

### 3. Error Handling

```go
// ✅ GOOD: Wrap errors with context
if err != nil {
    return nil, fmt.Errorf("failed to fetch GSC metrics: %w", err)
}

// ✅ GOOD: Use custom error types
return nil, apperrors.New(apperrors.CodeNotFound, "No cached AI analysis available", 404)

// ❌ BAD: Generic errors
return nil, errors.New("error")
```

### 4. Comments (1:1 with Python notation)

```go
// Use "1:1 with Python" comments for parity verification
// CalculateGSCScore calculates SEO score from GSC metrics (1:1 with Python)
func CalculateGSCScore(metrics *GSCMetrics) *SEOScore { ... }

// GetAggregatedMetrics fetches and calculates metrics (1:1 with Python)
// CTR = total_clicks / total_impressions (NOT average of CTRs)
// Position = sum(position * impressions) / total_impressions (weighted)
func (c *SearchConsoleClient) GetAggregatedMetrics(...) (*AggregatedMetrics, error) { ... }
```

---

## 🔄 1:1 Parity Checklist with Python

### Business Logic Parity ✅

| Component | Python File | Go File | Status |
|-----------|-------------|---------|--------|
| SEO Scoring | `app/core/seo_scoring.py` | `internal/shared/scoring/seo_score.go` | ✅ |
| GSC Metrics | `app/auth/google_oauth.py` | `internal/infrastructure/google/searchconsole.go` | ✅ |
| PDF Data Processor | `app/agent/pdf_data_processor.py` | `internal/modules/audit/pdf/data_processor.go` | ✅ |
| PDF Text Constants | `app/agent/pdf_text_constants.py` | `internal/modules/audit/pdf/text_constants.go` | ✅ |
| PDF Generator | `app/agent/pdf_generator.py` | `internal/infrastructure/pdf/generator.go` | ✅ |
| PDF Colors | `app/agent/pdf_generator.py` | `internal/infrastructure/pdf/colors.go` | ✅ |
| PDF Styles | `app/agent/pdf_generator.py` | `internal/infrastructure/pdf/styles.go` | ✅ |
| Email Service | `app/agent/email_service.py` | `internal/infrastructure/email/service.go` | ✅ |

### Critical Values (Must Match Python Exactly)

```go
// SEO Scoring Weights
WeightTraffic  = 0.30  // 30%
WeightPosition = 0.25  // 25%
WeightCTR      = 0.25  // 25%
WeightTrends   = 0.20  // 20%
BaseScore      = 25.0  // No data score

// Grade Thresholds
>= 80: "Excellent"
>= 60: "Good"
>= 40: "Fair"
>= 20: "Poor"
<  20: "Critical"

// SEO Stages (by impressions)
< 50:    "hidden"
50-299:  "emerging"
300-1999: "discoverable"
>= 2000: "trusted"

// Date Range
30 days (NOT 28)
GSC data delay: 1 day

// CTR Benchmarks (position 1-10)
{1: 0.285, 2: 0.157, 3: 0.094, 4: 0.062, 5: 0.050,
 6: 0.038, 7: 0.030, 8: 0.024, 9: 0.020, 10: 0.025}
```

### PDF Layout Parity (Must Match Python)

```go
// Page Settings
PageSize: Letter (612 x 792 pt)
Margins: 50pt all sides
ContentWidth: 512pt

// Brand Colors
SOLVIA_ORANGE = "#EC6019"
SOLVIA_DARK = "#1F2937"
SOLVIA_GRAY = "#6B7280"
SOLVIA_LIGHT_GRAY = "#F3F4F6"
SOLVIA_LIGHT_GRAY_BG = "#EEEEEE"
SOLVIA_GREEN = "#16A34A"
SOLVIA_RED = "#EF4444"
SOLVIA_YELLOW = "#F59E0B"

// Font Sizes
Title: 32pt Bold
Heading1: 21pt Bold
Heading2: 12pt Bold
Body: 11pt Regular
Quote: 11pt Regular
Footer: 9pt Regular
ScoreNumber: 36pt Bold
```

---

## 🛠️ Development Rules

### Truth of Data Principle (CRITICAL)

**ALL data shown to users MUST come from real sources, NEVER assumptions or AI-generated numbers.**

```
┌─────────────────────────────────────────────────────────┐
│                    DATA SOURCES                          │
├─────────────────────────────────────────────────────────┤
│ GSC Metrics → Google Search Console API (REAL DATA)     │
│ Page Data   → Firecrawl API (REAL CRAWL)                │
│ SEO Score   → Calculated from GSC data (DETERMINISTIC)  │
│ Chat Data   → GSC + Page data injected into AI context  │
└─────────────────────────────────────────────────────────┘

✅ CORRECT: "You have 23 impressions" (from GSC API)
❌ WRONG:   "You have about 1000 impressions" (AI assumption)

✅ CORRECT: "CTR is 60.87%" (calculated: clicks/impressions)
❌ WRONG:   "CTR is typically around 3%" (example/assumption)
```

**Chat module MUST:**
1. Always send `include_metrics: true` to inject real GSC data
2. AI responds using **injected data context**, not trained knowledge
3. Numbers in responses = numbers from GSC API (truth)

**Verification**: If AI says "12,450 impressions" or "3.1% CTR" - these are example numbers from prompt template, NOT real data. Real data will match what GSC API returns.

### Pre-Task Protocol
1. Read this CLAUDE.md
2. Check Python implementation for reference
3. Verify 1:1 parity requirements
4. Update todo list if needed

### Code Quality Gates
- [ ] Follows Clean Architecture layers
- [ ] Uses interfaces for dependencies
- [ ] Has "1:1 with Python" comments where applicable
- [ ] Error handling with context
- [ ] No hardcoded values (use constants)
- [ ] Tested or verified manually

### Git Commit Rules
- NEVER mention "Claude" in commits
- Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`
- Reference parity: `fix: Update grade thresholds to match Python`

---

## 📊 Current Focus: PDF & Email Implementation

### PDF Generator Requirements
1. **Page Size**: Letter (612 x 792 pt)
2. **Layout**: 2 pages matching Python exactly
3. **Components**:
   - Progress bar with 4 SEO stages
   - Rounded quote boxes with icon
   - Score circle with color coding
   - Metrics table with notes
   - Next steps bullet list
4. **Integration**: Use existing `data_processor.go` and `text_constants.go`

### Email Service Requirements
1. **SMTP**: Zoho (smtp.zoho.com:587)
2. **Template**: HTML matching Python
3. **Attachment**: PDF report
4. **Logging**: Store in email_logs table

---

## 📁 Key File References

### Go V2
- Entry point: `api/cmd/api/main.go`
- Scoring: `api/internal/shared/scoring/seo_score.go`
- GSC Client: `api/internal/infrastructure/google/searchconsole.go`
- PDF Generator: `api/internal/infrastructure/pdf/generator.go`
- PDF Data: `api/internal/modules/audit/pdf/data_processor.go`

### Python (Reference)
- PDF Generator: `app/agent/pdf_generator.py`
- PDF Data: `app/agent/pdf_data_processor.py`
- Email Service: `app/agent/email_service.py`
- Scoring: `app/core/seo_scoring.py`

---

## 🔄 Recent Updates

| Date | Update | Files |
|------|--------|-------|
| 2025-12-10 | **Dashboard Refactor**: Split 1098 LOC into 7 files (460 LOC main + components) | `DashboardPage.tsx`, `components/*` |
| 2025-12-10 | **Code Standards**: Added 1000 LOC limit, Truth of Data principle | `CLAUDE.md` |
| 2025-12-10 | **Chat Fix**: Fixed include_metrics to use real GSC data, not examples | `chat.ts`, `ChatPage.tsx` |
| 2025-12-03 | **PDF Generator**: Complete rewrite with exact Python layout parity | `colors.go`, `styles.go`, `generator.go` |
| 2025-12-03 | **Email Service**: Implemented SMTP with Zoho, HTML templates, logging | `email/service.go` |
| 2025-12-03 | **Config**: Added email configuration fields | `config.go` |
| 2025-12-03 | Fixed Grade thresholds (Excellent/Good/Fair/Poor/Critical) | `seo_score.go` |
| 2025-12-03 | Fixed Date range (28→30 days) | Multiple files |
| 2025-12-03 | Fixed Benchmark caching logic | `benchmark_service.go` |
| 2025-12-03 | Added header/footer to website content | `website_service.go` |
| 2025-12-03 | Created CLAUDE.md with clean architecture principles | This file |

---

**Version**: 2.0.0-alpha | **Target**: 1:1 Parity with Python | **Status**: PDF & Email Complete
