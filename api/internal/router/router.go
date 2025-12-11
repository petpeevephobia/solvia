package router

import (
	"context"
	"net/http"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"

	redisClient "github.com/petpeevephobia/solvia-v2/api/internal/infrastructure/redis"
	auditHandler "github.com/petpeevephobia/solvia-v2/api/internal/modules/audit/handler"
	authHandler "github.com/petpeevephobia/solvia-v2/api/internal/modules/auth/handler"
	authService "github.com/petpeevephobia/solvia-v2/api/internal/modules/auth/service"
	benchmarkHandler "github.com/petpeevephobia/solvia-v2/api/internal/modules/benchmark/handler"
	chatHandler "github.com/petpeevephobia/solvia-v2/api/internal/modules/chat/handler"
	dashboardHandler "github.com/petpeevephobia/solvia-v2/api/internal/modules/dashboard/handler"
	gscHandler "github.com/petpeevephobia/solvia-v2/api/internal/modules/gsc/handler"
	onpageHandler "github.com/petpeevephobia/solvia-v2/api/internal/modules/onpage/handler"
	websiteHandler "github.com/petpeevephobia/solvia-v2/api/internal/modules/website/handler"

	"github.com/petpeevephobia/solvia-v2/api/internal/middleware"
)

// Handlers holds all HTTP handlers
type Handlers struct {
	Auth      *authHandler.AuthHandler
	GSC       *gscHandler.GSCHandler
	Audit     *auditHandler.AuditHandler
	Chat      *chatHandler.ChatHandler
	OnPage    *onpageHandler.OnPageHandler
	Benchmark *benchmarkHandler.BenchmarkHandler   // Benchmark insights (1:1 with Python)
	Dashboard *dashboardHandler.DashboardHandler   // Dashboard cache (1:1 with Python)
	Website   *websiteHandler.WebsiteHandler       // Website content (1:1 with Python)
}

// Config holds router configuration
type Config struct {
	AllowedOrigins []string
	AuthService    *authService.AuthService
	Redis          *redisClient.Client // Redis client for caching
}

// New creates a new router with all routes registered
func New(handlers *Handlers, config *Config) *gin.Engine {
	r := gin.Default()

	// CORS configuration
	corsConfig := cors.DefaultConfig()
	if len(config.AllowedOrigins) > 0 {
		corsConfig.AllowOrigins = config.AllowedOrigins
	} else {
		corsConfig.AllowAllOrigins = true
	}
	corsConfig.AllowHeaders = []string{
		"Origin",
		"Content-Type",
		"Accept",
		"Authorization",
		"X-Requested-With",
	}
	corsConfig.AllowMethods = []string{"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}
	corsConfig.AllowCredentials = true
	r.Use(cors.New(corsConfig))

	// Health check
	r.GET("/health", func(c *gin.Context) {
		health := gin.H{
			"status":  "healthy",
			"service": "solvia-api",
		}

		// Add Redis status
		if config.Redis != nil && config.Redis.IsEnabled() {
			ctx, cancel := context.WithTimeout(c.Request.Context(), 2*time.Second)
			defer cancel()
			if err := config.Redis.Ping(ctx); err != nil {
				health["redis"] = gin.H{"status": "unhealthy", "error": err.Error()}
			} else {
				stats := config.Redis.Stats()
				health["redis"] = gin.H{
					"status":      "healthy",
					"total_conns": stats.TotalConns,
					"idle_conns":  stats.IdleConns,
				}
			}
		} else {
			health["redis"] = gin.H{"status": "disabled"}
		}

		c.JSON(http.StatusOK, health)
	})

	// API v1 routes
	v1 := r.Group("/api/v1")
	{
		// Public routes (no auth required)
		auth := v1.Group("/auth")
		{
			auth.GET("/url", handlers.Auth.GetAuthURL)
			auth.GET("/url/device-trust", handlers.Auth.GetAuthURLWithDeviceTrust) // Device trust support (1:1 with Python)
			auth.POST("/callback", handlers.Auth.Callback)
			auth.GET("/callback", handlers.Auth.Callback) // Support GET callback
			// Email verification & password reset (1:1 with Python - public routes)
			auth.POST("/verify-email", handlers.Auth.VerifyEmail)
			auth.POST("/forgot-password", handlers.Auth.ForgotPassword)
			auth.POST("/reset-password", handlers.Auth.ResetPassword)
		}

		// Protected routes
		protected := v1.Group("")
		protected.Use(middleware.AuthMiddleware(config.AuthService))
		{
			// Auth routes
			protected.GET("/auth/me", handlers.Auth.GetCurrentUser)
			protected.POST("/auth/refresh", handlers.Auth.RefreshToken)
			protected.POST("/auth/logout", handlers.Auth.Logout)
			// Device trust routes (1:1 with Python)
			protected.GET("/auth/device-trust", handlers.Auth.CheckDeviceTrust)
			protected.POST("/auth/device-trust", handlers.Auth.MarkDeviceTrusted)

			// GSC routes
			gsc := protected.Group("/gsc")
			{
				gsc.GET("/websites", handlers.GSC.GetWebsites)
				gsc.POST("/websites/sync", handlers.GSC.SyncWebsites)
				gsc.GET("/selected-website", handlers.GSC.GetSelectedWebsite)   // 1:1 parity with original
				gsc.POST("/select-property", handlers.GSC.SelectProperty)       // 1:1 parity with original
				gsc.GET("/metrics", handlers.GSC.GetMetrics)
				gsc.GET("/queries", handlers.GSC.GetQueries)
				gsc.GET("/pages", handlers.GSC.GetPages)
				gsc.GET("/daily", handlers.GSC.GetDailyMetrics)
				// GSC Filter System (1:1 with Python)
				gsc.POST("/filter", handlers.GSC.ApplyFilter)                        // Apply filters to GSC data
				gsc.GET("/filter/preset/:preset_name", handlers.GSC.GetFilterPreset) // Get date range presets (24h, 7d, 28d, 3mo)
				// Additional 1:1 parity endpoints
				gsc.GET("/keywords", handlers.GSC.GetKeywords)              // 1:1 with Python /gsc/keywords
				gsc.POST("/refresh", handlers.GSC.RefreshMetrics)           // 1:1 with Python /gsc/refresh
				gsc.GET("/properties", handlers.GSC.GetProperties)          // 1:1 with Python /gsc/properties
				gsc.GET("/selected", handlers.GSC.GetSelected)              // 1:1 with Python /gsc/selected (alias)
				gsc.POST("/clear-credentials", handlers.GSC.ClearCredentials) // 1:1 with Python /gsc/clear-credentials
			}

			// Audit routes
			audit := protected.Group("/audit")
			{
				audit.POST("", handlers.Audit.CreateAudit)
				audit.GET("", handlers.Audit.GetAuditHistory)
				audit.GET("/latest", handlers.Audit.GetLatestAudit)
				audit.GET("/current-issues", handlers.Audit.GetCurrentIssues)
				audit.GET("/health", handlers.Audit.Health)           // 1:1 with Python /audit/health
				audit.GET("/:id", handlers.Audit.GetAudit)
				audit.GET("/:id/issues", handlers.Audit.GetAuditWithIssues)
				audit.GET("/:id/status", handlers.Audit.CheckAuditStatus)
				audit.GET("/:id/progress", handlers.Audit.GetAuditProgress)        // Non-streaming progress
				audit.GET("/:id/progress/stream", handlers.Audit.StreamAuditProgress) // SSE streaming (1:1 with Python)
				audit.GET("/:id/pdf", handlers.Audit.DownloadPDF)
				audit.POST("/:id/export", handlers.Audit.ExportAudit) // 1:1 with Python /audit/export/{audit_id}
			}

			// Chat routes
			chat := protected.Group("/chat")
			{
				chat.POST("", handlers.Chat.Chat)
				chat.GET("/conversations", handlers.Chat.GetConversations)
				chat.GET("/conversations/:id", handlers.Chat.GetConversation)
				chat.DELETE("/conversations/:id", handlers.Chat.DeleteConversation)
				chat.PATCH("/conversations/:id/title", handlers.Chat.UpdateConversationTitle)
			}

			// OnPage routes
			onpage := protected.Group("/onpage")
			{
				onpage.POST("/analyze", handlers.OnPage.AnalyzePage)
				onpage.GET("/analyses", handlers.OnPage.GetAnalysisHistory)
				onpage.GET("/analyses/:id", handlers.OnPage.GetAnalysis)
				onpage.GET("/analyses/:id/status", handlers.OnPage.CheckAnalysisStatus)
				onpage.POST("/map", handlers.OnPage.MapSite)
				onpage.POST("/crawl", handlers.OnPage.CrawlWebsite) // 1:1 with Python website_crawler.py
			}

			// Benchmark routes (1:1 with Python)
			benchmark := protected.Group("/benchmark")
			{
				benchmark.GET("/insights", handlers.Benchmark.GetBenchmarkInsights)
			}

			// Dashboard routes (1:1 with Python)
			dashboard := protected.Group("/dashboard")
			{
				dashboard.GET("/cache", handlers.Dashboard.GetCache)
				dashboard.POST("/cache", handlers.Dashboard.SaveCache)
			}

			// Website content routes (1:1 with Python)
			website := protected.Group("/website")
			{
				website.POST("/content/fetch", handlers.Website.FetchContent)
				website.GET("/content", handlers.Website.GetContent)
			}
		}
	}

	return r
}
