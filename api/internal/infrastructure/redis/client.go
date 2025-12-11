package redis

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/rs/zerolog/log"
)

// Client wraps the Redis client with convenience methods
type Client struct {
	rdb        *redis.Client
	defaultTTL time.Duration
	enabled    bool
}

// Config holds Redis configuration
type Config struct {
	URL        string
	Enabled    bool
	DefaultTTL time.Duration
}

// NewClient creates a new Redis client
func NewClient(cfg *Config) (*Client, error) {
	if !cfg.Enabled {
		log.Info().Msg("[REDIS] Redis disabled, using no-op client")
		return &Client{enabled: false}, nil
	}

	opts, err := redis.ParseURL(cfg.URL)
	if err != nil {
		return nil, fmt.Errorf("failed to parse Redis URL: %w", err)
	}

	rdb := redis.NewClient(opts)

	// Test connection
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := rdb.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("failed to connect to Redis: %w", err)
	}

	log.Info().Str("url", cfg.URL).Msg("[REDIS] Connected successfully")

	return &Client{
		rdb:        rdb,
		defaultTTL: cfg.DefaultTTL,
		enabled:    true,
	}, nil
}

// Close closes the Redis connection
func (c *Client) Close() error {
	if !c.enabled {
		return nil
	}
	return c.rdb.Close()
}

// IsEnabled returns whether Redis is enabled
func (c *Client) IsEnabled() bool {
	return c.enabled
}

// ============================================================================
// Basic Key-Value Operations
// ============================================================================

// Set stores a value with the default TTL
func (c *Client) Set(ctx context.Context, key string, value interface{}) error {
	return c.SetWithTTL(ctx, key, value, c.defaultTTL)
}

// SetWithTTL stores a value with a custom TTL
func (c *Client) SetWithTTL(ctx context.Context, key string, value interface{}, ttl time.Duration) error {
	if !c.enabled {
		return nil
	}

	data, err := json.Marshal(value)
	if err != nil {
		return fmt.Errorf("failed to marshal value: %w", err)
	}

	return c.rdb.Set(ctx, key, data, ttl).Err()
}

// Get retrieves a value and unmarshals it into dest
func (c *Client) Get(ctx context.Context, key string, dest interface{}) error {
	if !c.enabled {
		return redis.Nil
	}

	data, err := c.rdb.Get(ctx, key).Bytes()
	if err != nil {
		return err
	}

	return json.Unmarshal(data, dest)
}

// Delete removes a key
func (c *Client) Delete(ctx context.Context, keys ...string) error {
	if !c.enabled {
		return nil
	}
	return c.rdb.Del(ctx, keys...).Err()
}

// Exists checks if a key exists
func (c *Client) Exists(ctx context.Context, key string) (bool, error) {
	if !c.enabled {
		return false, nil
	}
	n, err := c.rdb.Exists(ctx, key).Result()
	return n > 0, err
}

// ============================================================================
// Token/Credential Caching
// ============================================================================

const (
	tokenKeyPrefix = "token:"
	tokenCacheTTL  = 5 * time.Minute // 1:1 with Python credential cache
)

// TokenCache represents cached Google OAuth tokens
type TokenCache struct {
	AccessToken  string    `json:"access_token"`
	RefreshToken string    `json:"refresh_token"`
	ExpiresAt    time.Time `json:"expires_at"`
}

// SetTokens caches user tokens
func (c *Client) SetTokens(ctx context.Context, userEmail string, tokens *TokenCache) error {
	key := tokenKeyPrefix + userEmail
	return c.SetWithTTL(ctx, key, tokens, tokenCacheTTL)
}

// GetTokens retrieves cached tokens
func (c *Client) GetTokens(ctx context.Context, userEmail string) (*TokenCache, error) {
	key := tokenKeyPrefix + userEmail
	var tokens TokenCache
	if err := c.Get(ctx, key, &tokens); err != nil {
		return nil, err
	}
	return &tokens, nil
}

// DeleteTokens removes cached tokens
func (c *Client) DeleteTokens(ctx context.Context, userEmail string) error {
	key := tokenKeyPrefix + userEmail
	return c.Delete(ctx, key)
}

// ============================================================================
// GSC Metrics Caching
// ============================================================================

const (
	metricsKeyPrefix = "metrics:"
	metricsCacheTTL  = 1 * time.Hour // Cache GSC metrics for 1 hour
)

// MetricsCache represents cached GSC metrics
type MetricsCache struct {
	SEOScore    float64   `json:"seo_score"`
	Impressions int       `json:"impressions"`
	Clicks      int       `json:"clicks"`
	CTR         float64   `json:"ctr"`
	Position    float64   `json:"position"`
	CachedAt    time.Time `json:"cached_at"`
}

// metricsKey generates a cache key for metrics
func metricsKey(userEmail, websiteURL, dateRange string) string {
	return fmt.Sprintf("%s%s:%s:%s", metricsKeyPrefix, userEmail, websiteURL, dateRange)
}

// SetMetrics caches GSC metrics
func (c *Client) SetMetrics(ctx context.Context, userEmail, websiteURL, dateRange string, metrics *MetricsCache) error {
	key := metricsKey(userEmail, websiteURL, dateRange)
	metrics.CachedAt = time.Now()
	return c.SetWithTTL(ctx, key, metrics, metricsCacheTTL)
}

// GetMetrics retrieves cached GSC metrics
func (c *Client) GetMetrics(ctx context.Context, userEmail, websiteURL, dateRange string) (*MetricsCache, error) {
	key := metricsKey(userEmail, websiteURL, dateRange)
	var metrics MetricsCache
	if err := c.Get(ctx, key, &metrics); err != nil {
		return nil, err
	}
	return &metrics, nil
}

// DeleteMetrics removes cached metrics for a user/website
func (c *Client) DeleteMetrics(ctx context.Context, userEmail, websiteURL string) error {
	if !c.enabled {
		return nil
	}

	// Delete all date range variants
	pattern := fmt.Sprintf("%s%s:%s:*", metricsKeyPrefix, userEmail, websiteURL)
	keys, err := c.rdb.Keys(ctx, pattern).Result()
	if err != nil {
		return err
	}

	if len(keys) > 0 {
		return c.rdb.Del(ctx, keys...).Err()
	}
	return nil
}

// ============================================================================
// Dashboard Cache
// ============================================================================

const (
	dashboardKeyPrefix = "dashboard:"
	dashboardCacheTTL  = 30 * time.Minute
)

// dashboardKey generates a cache key for dashboard data
func dashboardKey(userEmail, websiteURL string) string {
	return fmt.Sprintf("%s%s:%s", dashboardKeyPrefix, userEmail, websiteURL)
}

// SetDashboard caches dashboard data
func (c *Client) SetDashboard(ctx context.Context, userEmail, websiteURL string, data map[string]interface{}) error {
	key := dashboardKey(userEmail, websiteURL)
	return c.SetWithTTL(ctx, key, data, dashboardCacheTTL)
}

// GetDashboard retrieves cached dashboard data
func (c *Client) GetDashboard(ctx context.Context, userEmail, websiteURL string) (map[string]interface{}, error) {
	key := dashboardKey(userEmail, websiteURL)
	var data map[string]interface{}
	if err := c.Get(ctx, key, &data); err != nil {
		return nil, err
	}
	return data, nil
}

// DeleteDashboard removes cached dashboard data
func (c *Client) DeleteDashboard(ctx context.Context, userEmail, websiteURL string) error {
	key := dashboardKey(userEmail, websiteURL)
	return c.Delete(ctx, key)
}

// ============================================================================
// Audit Job Queue
// ============================================================================

const (
	auditQueueKey     = "audit:queue"
	auditProcessingKey = "audit:processing"
)

// AuditJob represents an audit job in the queue
type AuditJob struct {
	AuditID       int64     `json:"audit_id"`
	UserEmail     string    `json:"user_email"`
	WebsiteURL    string    `json:"website_url"`
	DateRangeDays int       `json:"date_range_days"`
	ReportFormat  string    `json:"report_format"`
	DeliveryMethod string   `json:"delivery_method"`
	ForceRefresh  bool      `json:"force_refresh"`
	QueuedAt      time.Time `json:"queued_at"`
}

// EnqueueAudit adds an audit job to the queue
func (c *Client) EnqueueAudit(ctx context.Context, job *AuditJob) error {
	if !c.enabled {
		return nil // Fall back to direct processing if Redis disabled
	}

	job.QueuedAt = time.Now()
	data, err := json.Marshal(job)
	if err != nil {
		return fmt.Errorf("failed to marshal audit job: %w", err)
	}

	return c.rdb.RPush(ctx, auditQueueKey, data).Err()
}

// DequeueAudit retrieves and removes an audit job from the queue
// Uses BLPOP for blocking wait with timeout
func (c *Client) DequeueAudit(ctx context.Context, timeout time.Duration) (*AuditJob, error) {
	if !c.enabled {
		return nil, redis.Nil
	}

	result, err := c.rdb.BLPop(ctx, timeout, auditQueueKey).Result()
	if err != nil {
		return nil, err
	}

	if len(result) < 2 {
		return nil, redis.Nil
	}

	var job AuditJob
	if err := json.Unmarshal([]byte(result[1]), &job); err != nil {
		return nil, fmt.Errorf("failed to unmarshal audit job: %w", err)
	}

	return &job, nil
}

// GetQueueLength returns the number of audits in the queue
func (c *Client) GetQueueLength(ctx context.Context) (int64, error) {
	if !c.enabled {
		return 0, nil
	}
	return c.rdb.LLen(ctx, auditQueueKey).Result()
}

// MarkAuditProcessing marks an audit as being processed (for tracking)
func (c *Client) MarkAuditProcessing(ctx context.Context, auditID int64) error {
	if !c.enabled {
		return nil
	}
	key := fmt.Sprintf("%s:%d", auditProcessingKey, auditID)
	return c.rdb.Set(ctx, key, time.Now().Unix(), 30*time.Minute).Err()
}

// ClearAuditProcessing removes the processing marker
func (c *Client) ClearAuditProcessing(ctx context.Context, auditID int64) error {
	if !c.enabled {
		return nil
	}
	key := fmt.Sprintf("%s:%d", auditProcessingKey, auditID)
	return c.rdb.Del(ctx, key).Err()
}

// IsAuditProcessing checks if an audit is currently being processed
func (c *Client) IsAuditProcessing(ctx context.Context, auditID int64) (bool, error) {
	if !c.enabled {
		return false, nil
	}
	key := fmt.Sprintf("%s:%d", auditProcessingKey, auditID)
	return c.Exists(ctx, key)
}

// ============================================================================
// Rate Limiting
// ============================================================================

const (
	rateLimitKeyPrefix = "ratelimit:"
)

// CheckRateLimit checks if an action is rate limited
// Returns true if allowed, false if rate limited
func (c *Client) CheckRateLimit(ctx context.Context, key string, limit int, window time.Duration) (bool, error) {
	if !c.enabled {
		return true, nil // Allow all if Redis disabled
	}

	fullKey := rateLimitKeyPrefix + key

	// Use a Lua script for atomic increment + expiry check
	script := redis.NewScript(`
		local current = redis.call("INCR", KEYS[1])
		if current == 1 then
			redis.call("EXPIRE", KEYS[1], ARGV[1])
		end
		return current
	`)

	count, err := script.Run(ctx, c.rdb, []string{fullKey}, int(window.Seconds())).Int()
	if err != nil {
		return true, err // Allow on error
	}

	return count <= limit, nil
}

// ============================================================================
// Health Check
// ============================================================================

// Ping checks if Redis is healthy
func (c *Client) Ping(ctx context.Context) error {
	if !c.enabled {
		return nil
	}
	return c.rdb.Ping(ctx).Err()
}

// Stats returns Redis connection stats
func (c *Client) Stats() *redis.PoolStats {
	if !c.enabled {
		return nil
	}
	return c.rdb.PoolStats()
}
