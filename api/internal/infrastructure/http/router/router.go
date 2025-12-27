package router

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"github.com/petpeevephobia/solvia-v2/api/internal/infrastructure/database"
	"github.com/petpeevephobia/solvia-v2/api/internal/shared/config"
	"github.com/petpeevephobia/solvia-v2/api/internal/shared/middleware"
	"github.com/petpeevephobia/solvia-v2/api/internal/shared/response"
)

// NewRouter creates and configures the main router
func NewRouter(cfg *config.Config, db *database.PostgresDB) *gin.Engine {
	r := gin.New()

	// Global middleware
	r.Use(gin.Recovery())
	r.Use(middleware.Logger())
	r.Use(middleware.CORS(cfg.AllowedOrigins))
	r.Use(middleware.RequestID())

	// Health check endpoint
	r.GET("/health", healthHandler(db))

	// API v1 routes
	v1 := r.Group("/api/v1")
	{
		// Public routes
		v1.GET("/status", statusHandler)

		// Auth routes
		auth := v1.Group("/auth")
		{
			auth.GET("/google", placeholderHandler("Google OAuth"))
			auth.GET("/callback", placeholderHandler("OAuth Callback"))
			auth.POST("/logout", placeholderHandler("Logout"))
		}

		// Protected routes (require authentication)
		protected := v1.Group("")
		protected.Use(middleware.Auth(cfg.JWTSecret))
		{
			// User
			protected.GET("/me", placeholderHandler("Current User"))
			protected.PUT("/me/website", placeholderHandler("Update Website"))

			// Dashboard
			protected.GET("/dashboard", placeholderHandler("Dashboard"))

			// GSC (Google Search Console)
			gsc := protected.Group("/gsc")
			{
				gsc.GET("/websites", placeholderHandler("List Websites"))
				gsc.GET("/metrics", placeholderHandler("Get Metrics"))
				gsc.GET("/queries", placeholderHandler("Get Queries"))
				gsc.GET("/pages", placeholderHandler("Get Pages"))
			}

			// Audit
			audit := protected.Group("/audit")
			{
				audit.POST("/run", placeholderHandler("Run Audit"))
				audit.GET("/history", placeholderHandler("Audit History"))
				audit.GET("/:id", placeholderHandler("Get Audit"))
				audit.GET("/:id/pdf", placeholderHandler("Download PDF"))
			}

			// Chat (AI Assistant)
			chat := protected.Group("/chat")
			{
				chat.POST("/message", placeholderHandler("Send Message"))
				chat.GET("/history", placeholderHandler("Chat History"))
			}

			// On-Page SEO Analysis (Firecrawl)
			onpage := protected.Group("/onpage")
			{
				onpage.POST("/analyze", placeholderHandler("Analyze URL"))
				onpage.GET("/report/:id", placeholderHandler("Get Report"))
			}
		}
	}

	// Serve React SPA static files
	r.Static("/assets", "./web/dist/assets")
	r.NoRoute(spaHandler())

	return r
}

// healthHandler returns database and service health
func healthHandler(db *database.PostgresDB) gin.HandlerFunc {
	return func(c *gin.Context) {
		ctx := c.Request.Context()

		status := "healthy"
		dbStatus := "connected"

		if err := db.Health(ctx); err != nil {
			status = "degraded"
			dbStatus = "disconnected"
		}

		response.Success(c, http.StatusOK, gin.H{
			"status":   status,
			"database": dbStatus,
			"version":  "2.0.0",
			"stack":    "golang",
		})
	}
}

// statusHandler returns API status
func statusHandler(c *gin.Context) {
	response.Success(c, http.StatusOK, gin.H{
		"api":     "Solvia API",
		"version": "2.0.0",
		"status":  "operational",
	})
}

// placeholderHandler creates a placeholder for routes under development
func placeholderHandler(name string) gin.HandlerFunc {
	return func(c *gin.Context) {
		response.Success(c, http.StatusOK, gin.H{
			"message": name + " endpoint - coming soon",
			"status":  "placeholder",
		})
	}
}

// spaHandler serves the React SPA
func spaHandler() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.File("./web/dist/index.html")
	}
}
