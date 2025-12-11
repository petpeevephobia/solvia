package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"
)

// Config holds all application configuration
type Config struct {
	// Server
	Environment string
	Port        string
	BaseURL     string
	FrontendURL string

	// Database
	DatabaseURL string

	// Redis (caching + job queue)
	RedisURL      string
	RedisEnabled  bool
	RedisCacheTTL int // Default cache TTL in seconds

	// Google OAuth
	GoogleClientID     string
	GoogleClientSecret string
	GoogleRedirectURI  string

	// AI Provider (Gemini - replaces OpenAI)
	GeminiAPIKey string
	OpenAIAPIKey string // DEPRECATED: Kept for backward compatibility

	// Firecrawl (for on-page SEO)
	FirecrawlAPIKey string

	// JWT
	JWTSecret string

	// CORS
	AllowedOrigins []string

	// Email (SMTP via Zoho)
	EmailEnabled  bool
	EmailHost     string
	EmailPort     int
	EmailUsername string
	EmailPassword string
	EmailFrom     string

	// Audit Queue Settings
	AuditMaxWorkers   int // Max concurrent audit workers
	AuditQueueTimeout int // Queue timeout in seconds
}

// Load reads configuration from environment variables
func Load() (*Config, error) {
	// Parse email port
	emailPort := 587
	if portStr := os.Getenv("EMAIL_PORT"); portStr != "" {
		if p, err := strconv.Atoi(portStr); err == nil {
			emailPort = p
		}
	}

	// Parse Redis cache TTL (default 1 hour)
	redisCacheTTL := 3600
	if ttlStr := os.Getenv("REDIS_CACHE_TTL"); ttlStr != "" {
		if t, err := strconv.Atoi(ttlStr); err == nil {
			redisCacheTTL = t
		}
	}

	// Parse audit queue settings
	auditMaxWorkers := 5
	if workersStr := os.Getenv("AUDIT_MAX_WORKERS"); workersStr != "" {
		if w, err := strconv.Atoi(workersStr); err == nil {
			auditMaxWorkers = w
		}
	}

	auditQueueTimeout := 1800 // 30 minutes default
	if timeoutStr := os.Getenv("AUDIT_QUEUE_TIMEOUT"); timeoutStr != "" {
		if t, err := strconv.Atoi(timeoutStr); err == nil {
			auditQueueTimeout = t
		}
	}

	cfg := &Config{
		Environment: getEnv("ENVIRONMENT", "development"),
		Port:        getEnv("PORT", "8080"),
		BaseURL:     getEnv("BASE_URL", "http://localhost:8080"),
		FrontendURL: getEnv("FRONTEND_URL", "http://localhost:3000"),

		DatabaseURL: os.Getenv("DATABASE_URL"),

		// Redis config - defaults to localhost:6379 for development
		RedisURL:      getEnv("REDIS_URL", "redis://localhost:6379/0"),
		RedisEnabled:  getEnv("REDIS_ENABLED", "true") == "true",
		RedisCacheTTL: redisCacheTTL,

		GoogleClientID:     os.Getenv("GOOGLE_CLIENT_ID"),
		GoogleClientSecret: os.Getenv("GOOGLE_CLIENT_SECRET"),
		GoogleRedirectURI:  getEnv("GOOGLE_REDIRECT_URI", "http://localhost:8080/api/v1/auth/callback"),

		// Gemini AI (primary) - replaces OpenAI
		GeminiAPIKey:    os.Getenv("GEMINI_API_KEY"),
		OpenAIAPIKey:    os.Getenv("OPENAI_API_KEY"), // DEPRECATED
		FirecrawlAPIKey: os.Getenv("FIRECRAWL_API_KEY"),

		JWTSecret: os.Getenv("JWT_SECRET"),

		AllowedOrigins: parseOrigins(getEnv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080,https://solvia.app")),

		// Email config (1:1 with Python)
		EmailEnabled:  getEnv("EMAIL_ENABLED", "false") == "true",
		EmailHost:     getEnv("EMAIL_HOST", "smtp.zoho.com"),
		EmailPort:     emailPort,
		EmailUsername: os.Getenv("EMAIL_USERNAME"),
		EmailPassword: os.Getenv("EMAIL_PASSWORD"),
		EmailFrom:     getEnv("EMAIL_FROM", "info@solvia.app"), // 1:1 with Python config.py:49

		// Audit queue config
		AuditMaxWorkers:   auditMaxWorkers,
		AuditQueueTimeout: auditQueueTimeout,
	}

	// Validate required fields
	if cfg.DatabaseURL == "" {
		return nil, fmt.Errorf("DATABASE_URL is required")
	}

	if cfg.GoogleClientID == "" || cfg.GoogleClientSecret == "" {
		return nil, fmt.Errorf("Google OAuth credentials are required")
	}

	if cfg.JWTSecret == "" {
		return nil, fmt.Errorf("JWT_SECRET is required")
	}

	// Gemini API key required for AI features (chat, benchmark, RAG)
	if cfg.GeminiAPIKey == "" {
		return nil, fmt.Errorf("GEMINI_API_KEY is required for AI features")
	}

	return cfg, nil
}

// getEnv returns environment variable or default value
func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

// parseOrigins splits comma-separated origins
func parseOrigins(origins string) []string {
	parts := strings.Split(origins, ",")
	result := make([]string, 0, len(parts))
	for _, p := range parts {
		if trimmed := strings.TrimSpace(p); trimmed != "" {
			result = append(result, trimmed)
		}
	}
	return result
}
