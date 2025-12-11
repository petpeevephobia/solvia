package adapters

import (
	"context"
	"fmt"
	"time"

	chatDomain "github.com/petpeevephobia/solvia-v2/api/internal/modules/chat/domain"
	dashboardDomain "github.com/petpeevephobia/solvia-v2/api/internal/modules/dashboard/domain"
)

// GSCMetricsProvider defines the interface for GSC service to provide metrics
type GSCMetricsProvider interface {
	GetWebsiteMetricsForChat(ctx context.Context, userEmail, websiteURL string) (*chatDomain.WebsiteContext, error)
}

// AuditContextProvider defines the interface for Audit service to provide audit context
type AuditContextProvider interface {
	GetLatestAuditContext(ctx context.Context, userEmail, websiteURL string) (*chatDomain.AuditContext, error)
}

// GSCServiceAdapter adapts GSC service to MetricsProvider interface for chat
type GSCServiceAdapter struct {
	gscService GSCMetricsProvider
}

// NewGSCServiceAdapter creates a new GSC service adapter
func NewGSCServiceAdapter(gscService GSCMetricsProvider) *GSCServiceAdapter {
	return &GSCServiceAdapter{gscService: gscService}
}

// GetWebsiteContext implements chat.MetricsProvider interface
func (a *GSCServiceAdapter) GetWebsiteContext(ctx context.Context, userEmail, websiteURL string) (*chatDomain.WebsiteContext, error) {
	return a.gscService.GetWebsiteMetricsForChat(ctx, userEmail, websiteURL)
}

// AuditServiceAdapter adapts Audit service to AuditProvider interface for chat
type AuditServiceAdapter struct {
	auditService AuditContextProvider
}

// NewAuditServiceAdapter creates a new Audit service adapter
func NewAuditServiceAdapter(auditService AuditContextProvider) *AuditServiceAdapter {
	return &AuditServiceAdapter{auditService: auditService}
}

// GetLatestAuditContext implements chat.AuditProvider interface
func (a *AuditServiceAdapter) GetLatestAuditContext(ctx context.Context, userEmail, websiteURL string) (*chatDomain.AuditContext, error) {
	return a.auditService.GetLatestAuditContext(ctx, userEmail, websiteURL)
}

// DashboardCacheProvider defines the interface for dashboard cache operations
type DashboardCacheProvider interface {
	GetCache(ctx context.Context, userEmail, websiteURL string) (*dashboardDomain.DashboardCache, error)
	SaveCache(ctx context.Context, cache *dashboardDomain.DashboardCache) error
}

// DashboardCacheAdapter adapts dashboard repository to benchmark.DashboardCacheGetter interface
type DashboardCacheAdapter struct {
	repo DashboardCacheProvider
}

// NewDashboardCacheAdapter creates a new dashboard cache adapter
func NewDashboardCacheAdapter(repo DashboardCacheProvider) *DashboardCacheAdapter {
	return &DashboardCacheAdapter{repo: repo}
}

// GetCache implements benchmark.DashboardCacheGetter interface
func (a *DashboardCacheAdapter) GetCache(ctx context.Context, userEmail, websiteURL string) (map[string]interface{}, error) {
	cache, err := a.repo.GetCache(ctx, userEmail, websiteURL)
	if err != nil {
		return nil, err
	}
	if cache == nil {
		return nil, nil
	}
	return cache.Data, nil
}

// SaveCache implements benchmark.DashboardCacheGetter interface
func (a *DashboardCacheAdapter) SaveCache(ctx context.Context, userEmail, websiteURL string, data map[string]interface{}) error {
	cache := &dashboardDomain.DashboardCache{
		UserEmail:  userEmail,
		WebsiteURL: websiteURL,
		Data:       data,
		CachedAt:   time.Now(),
	}
	return a.repo.SaveCache(ctx, cache)
}

// ============================================================================
// CACHE CLEARING ADAPTERS (1:1 with Python cache clearing)
// ============================================================================

// GSCCacheClearer defines the interface for GSC cache clearing
type GSCCacheClearer interface {
	InvalidateMetricsCache(ctx context.Context, userEmail, websiteURL string) error
}

// DashboardCacheClearer defines the interface for dashboard cache clearing
type DashboardCacheClearer interface {
	ClearCache(ctx context.Context, userEmail, websiteURL string) error
}

// DateRangesToClear defines the common date ranges to clear (1:1 with Python)
var DateRangesToClear = []int{7, 14, 28, 30, 90}

// CacheCleanerAdapter combines GSC and Dashboard cache clearing (1:1 with Python)
type CacheCleanerAdapter struct {
	gscRepo       GSCCacheClearer
	dashboardRepo DashboardCacheClearer
}

// NewCacheCleanerAdapter creates a new cache cleaner adapter
func NewCacheCleanerAdapter(gscRepo GSCCacheClearer, dashboardRepo DashboardCacheClearer) *CacheCleanerAdapter {
	return &CacheCleanerAdapter{
		gscRepo:       gscRepo,
		dashboardRepo: dashboardRepo,
	}
}

// ClearAllCaches clears all caches before audit (1:1 with Python ULTRATHINK)
// This clears GSC metrics cache for all common date ranges [7, 14, 28, 30, 90]
func (a *CacheCleanerAdapter) ClearAllCaches(ctx context.Context, userEmail, websiteURL string) error {
	fmt.Printf("[AUDIT CACHE CLEAR] 🧹 Clearing all caches for fresh data...\n")

	// 1. Clear GSC metrics cache for all date ranges (1:1 with Python)
	// Python iterates through [7, 14, 28, 30, 90] days and clears each
	// Go's InvalidateMetricsCache clears ALL entries at once, which is more efficient
	// We log the date ranges for parity with Python's logging
	for _, days := range DateRangesToClear {
		endDate := time.Now().AddDate(0, 0, -1) // GSC data delayed by 1 day
		startDate := endDate.AddDate(0, 0, -(days - 1))
		fmt.Printf("[AUDIT CACHE CLEAR] Clearing cache for %d days: %s to %s\n",
			days, startDate.Format("2006-01-02"), endDate.Format("2006-01-02"))
	}

	// Clear all GSC metrics cache (Go clears all at once, more efficient)
	if err := a.gscRepo.InvalidateMetricsCache(ctx, userEmail, websiteURL); err != nil {
		fmt.Printf("[AUDIT CACHE CLEAR] ⚠️ Warning: Could not clear metrics cache: %v\n", err)
	} else {
		fmt.Printf("[AUDIT CACHE CLEAR] ✅ Cleared GSC metrics cache for %s\n", websiteURL)
	}

	// 2. Clear dashboard cache (1:1 with Python)
	if err := a.dashboardRepo.ClearCache(ctx, userEmail, websiteURL); err != nil {
		fmt.Printf("[AUDIT CACHE CLEAR] ⚠️ Warning: Could not clear dashboard cache: %v\n", err)
	} else {
		fmt.Printf("[AUDIT CACHE CLEAR] ✅ Cleared dashboard cache for %s\n", websiteURL)
	}

	fmt.Printf("[AUDIT CACHE CLEAR] 🎯 All caches cleared - audit will use fresh Google API data\n")
	return nil
}

// ============================================================================
// RAG ADAPTERS (1:1 with Python RAG integration)
// ============================================================================

// RAGAgent defines the interface for RAG operations
// Note: The second return value from GetRAGContext is ignored by the adapter
type RAGAgent interface {
	GetRAGContext(ctx context.Context, userEmail, query, websiteURL string) (string, interface{}, error)
	IndexDocument(ctx context.Context, userEmail, content, collectionName string, metadata map[string]interface{}, websiteURL string) error
}

// RAGProviderAdapter adapts RAG agent to chat service RAGProvider interface
type RAGProviderAdapter struct {
	ragAgent RAGAgent
}

// NewRAGProviderAdapter creates a new RAG provider adapter
func NewRAGProviderAdapter(ragAgent RAGAgent) *RAGProviderAdapter {
	return &RAGProviderAdapter{ragAgent: ragAgent}
}

// GetRAGContext retrieves relevant context for a query (1:1 with Python)
func (a *RAGProviderAdapter) GetRAGContext(ctx context.Context, userEmail, query, websiteURL string) (string, error) {
	if a.ragAgent == nil {
		return "", nil
	}
	context, _, err := a.ragAgent.GetRAGContext(ctx, userEmail, query, websiteURL)
	return context, err
}

// IndexInteraction indexes a chat interaction for future retrieval (1:1 with Python)
func (a *RAGProviderAdapter) IndexInteraction(ctx context.Context, userEmail, websiteURL, query, response string) error {
	if a.ragAgent == nil {
		return nil
	}

	// Create interaction content
	content := "Q: " + query + "\nA: " + response

	metadata := map[string]interface{}{
		"type":     "chat_interaction",
		"question": query,
	}

	return a.ragAgent.IndexDocument(ctx, userEmail, content, "user_interactions", metadata, websiteURL)
}
