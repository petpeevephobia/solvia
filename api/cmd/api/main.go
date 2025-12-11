package main

import (
	"context"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"

	// Infrastructure
	"github.com/petpeevephobia/solvia-v2/api/internal/infrastructure/database"
	"github.com/petpeevephobia/solvia-v2/api/internal/infrastructure/email"
	"github.com/petpeevephobia/solvia-v2/api/internal/infrastructure/firecrawl"
	"github.com/petpeevephobia/solvia-v2/api/internal/infrastructure/gemini"
	"github.com/petpeevephobia/solvia-v2/api/internal/infrastructure/google"
	"github.com/petpeevephobia/solvia-v2/api/internal/infrastructure/pdf"
	"github.com/petpeevephobia/solvia-v2/api/internal/infrastructure/rag"
	redisClient "github.com/petpeevephobia/solvia-v2/api/internal/infrastructure/redis"

	// Modules - Handlers
	auditHandler "github.com/petpeevephobia/solvia-v2/api/internal/modules/audit/handler"
	authHandler "github.com/petpeevephobia/solvia-v2/api/internal/modules/auth/handler"
	benchmarkHandler "github.com/petpeevephobia/solvia-v2/api/internal/modules/benchmark/handler"
	chatHandler "github.com/petpeevephobia/solvia-v2/api/internal/modules/chat/handler"
	dashboardHandler "github.com/petpeevephobia/solvia-v2/api/internal/modules/dashboard/handler"
	gscHandler "github.com/petpeevephobia/solvia-v2/api/internal/modules/gsc/handler"
	onpageHandler "github.com/petpeevephobia/solvia-v2/api/internal/modules/onpage/handler"
	websiteHandler "github.com/petpeevephobia/solvia-v2/api/internal/modules/website/handler"

	// Modules - Services
	auditService "github.com/petpeevephobia/solvia-v2/api/internal/modules/audit/service"
	authService "github.com/petpeevephobia/solvia-v2/api/internal/modules/auth/service"
	benchmarkService "github.com/petpeevephobia/solvia-v2/api/internal/modules/benchmark/service"
	chatService "github.com/petpeevephobia/solvia-v2/api/internal/modules/chat/service"
	dashboardService "github.com/petpeevephobia/solvia-v2/api/internal/modules/dashboard/service"
	gscService "github.com/petpeevephobia/solvia-v2/api/internal/modules/gsc/service"
	onpageService "github.com/petpeevephobia/solvia-v2/api/internal/modules/onpage/service"
	websiteService "github.com/petpeevephobia/solvia-v2/api/internal/modules/website/service"

	// Modules - Repositories
	auditRepo "github.com/petpeevephobia/solvia-v2/api/internal/modules/audit/repository"
	authRepo "github.com/petpeevephobia/solvia-v2/api/internal/modules/auth/repository"
	chatRepo "github.com/petpeevephobia/solvia-v2/api/internal/modules/chat/repository"
	dashboardRepo "github.com/petpeevephobia/solvia-v2/api/internal/modules/dashboard/repository"
	gscRepo "github.com/petpeevephobia/solvia-v2/api/internal/modules/gsc/repository"
	onpageRepo "github.com/petpeevephobia/solvia-v2/api/internal/modules/onpage/repository"
	websiteRepo "github.com/petpeevephobia/solvia-v2/api/internal/modules/website/repository"

	// Router
	"github.com/petpeevephobia/solvia-v2/api/internal/router"
	"github.com/petpeevephobia/solvia-v2/api/internal/shared/adapters"
	"github.com/petpeevephobia/solvia-v2/api/internal/shared/config"
)

func main() {
	// Initialize zerolog
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnix
	log.Logger = log.Output(zerolog.ConsoleWriter{Out: os.Stderr})

	// Load environment variables
	if err := godotenv.Load("../../.env"); err != nil {
		if err := godotenv.Load(); err != nil {
			log.Warn().Msg("No .env file found, using environment variables")
		}
	}

	// Load configuration
	cfg, err := config.Load()
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to load configuration")
	}

	// Set Gin mode
	if cfg.Environment == "production" {
		gin.SetMode(gin.ReleaseMode)
	}

	// Initialize database connection
	db, err := database.NewPostgresDB(cfg.DatabaseURL)
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to connect to database")
	}
	defer db.Close()

	log.Info().Msg("Database connection established")

	// Initialize Redis client (caching + job queue)
	redisConfig := &redisClient.Config{
		URL:        cfg.RedisURL,
		Enabled:    cfg.RedisEnabled,
		DefaultTTL: time.Duration(cfg.RedisCacheTTL) * time.Second,
	}
	redis, err := redisClient.NewClient(redisConfig)
	if err != nil {
		log.Warn().Err(err).Msg("Failed to connect to Redis, caching disabled")
		// Create disabled client to continue without Redis
		disabledConfig := &redisClient.Config{Enabled: false}
		redis, _ = redisClient.NewClient(disabledConfig)
	} else if redis.IsEnabled() {
		defer redis.Close()
		log.Info().Msg("Redis connection established")
	}

	// Initialize infrastructure clients
	oauthClient := google.NewOAuthClient(cfg.GoogleClientID, cfg.GoogleClientSecret, cfg.GoogleRedirectURI)
	gscClient := google.NewSearchConsoleClient()
	firecrawlClient := firecrawl.NewClient(cfg.FirecrawlAPIKey)
	pdfGenerator := pdf.NewGenerator("./storage/pdfs")

	// Initialize Gemini AI client (replaces OpenAI)
	geminiClient, err := gemini.NewClient(context.Background(), cfg.GeminiAPIKey)
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to create Gemini client")
	}
	log.Info().Msg("Gemini AI client initialized")

	// Initialize Gemini Embeddings client
	geminiEmbeddings, err := gemini.NewEmbeddingsClient(context.Background(), cfg.GeminiAPIKey)
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to create Gemini embeddings client")
	}

	// Initialize email service (1:1 with Python)
	emailConfig := &email.Config{
		Enabled:     cfg.EmailEnabled,
		Host:        cfg.EmailHost,
		Port:        cfg.EmailPort,
		Username:    cfg.EmailUsername,
		Password:    cfg.EmailPassword,
		From:        cfg.EmailFrom,
		FrontendURL: cfg.FrontendURL,
	}
	emailService := email.NewService(emailConfig, db.Pool)

	// Initialize repositories
	authRepository := authRepo.NewPostgresAuthRepository(db.Pool)
	gscRepository := gscRepo.NewPostgresGSCRepository(db.Pool)
	auditRepository := auditRepo.NewPostgresAuditRepository(db.Pool)
	chatRepository := chatRepo.NewPostgresChatRepository(db.Pool)
	onpageRepository := onpageRepo.NewPostgresOnPageRepository(db.Pool)
	dashboardRepository := dashboardRepo.NewPostgresDashboardRepository(db.Pool)
	websiteRepository := websiteRepo.NewPostgresWebsiteRepository(db.Pool)

	// Initialize services
	authSvc := authService.NewAuthService(authRepository, oauthClient, cfg.JWTSecret)
	gscSvc := gscService.NewGSCService(gscRepository, gscClient, oauthClient, authSvc, authRepository)

	// Wire up token refresher for automatic 401 retry (1:1 with Python ULTRATHINK)
	gscService.SetTokenRefresher(authSvc)
	auditSvc := auditService.NewAuditService(auditRepository, gscClient, oauthClient, pdfGenerator, authSvc, emailService)
	benchmarkSvc := benchmarkService.NewBenchmarkService(gscClient, oauthClient, authSvc, gscSvc)

	// Wire up cache cleaner to audit service (1:1 with Python ULTRATHINK)
	cacheCleaner := adapters.NewCacheCleanerAdapter(gscRepository, dashboardRepository)
	auditSvc.SetCacheClearer(cacheCleaner)

	// Create adapters for chat service (clean architecture)
	gscAdapter := adapters.NewGSCServiceAdapter(gscSvc)
	auditAdapter := adapters.NewAuditServiceAdapter(auditSvc)

	// Wire up dashboard cache to benchmark service (1:1 with Python)
	dashboardCacheAdapter := adapters.NewDashboardCacheAdapter(dashboardRepository)
	benchmarkSvc.SetDashboardCache(dashboardCacheAdapter)

	// Wire up AI client to benchmark service (1:1 with Python)
	benchmarkAIAdapter := adapters.NewGeminiBenchmarkAdapter(geminiClient)
	benchmarkSvc.SetAIClient(benchmarkAIAdapter)

	// Initialize RAG system (1:1 with Python - CRITICAL for chat intelligence)
	// Uses Gemini embeddings (replaces OpenAI text-embedding-3-small)
	geminiEmbeddingsAdapter := adapters.NewGeminiEmbeddingsAdapter(geminiEmbeddings)
	ragAgent := rag.NewAgent(db.Pool, geminiEmbeddingsAdapter, nil)
	ragAdapter := adapters.NewRAGProviderAdapter(ragAgent)

	// Initialize chat service with context providers (1:1 with Python)
	// Uses Gemini AI client (replaces OpenAI gpt-4o-mini)
	geminiClientAdapter := adapters.NewGeminiClientAdapter(geminiClient)
	chatSvc := chatService.NewChatService(chatRepository, geminiClientAdapter, gscAdapter, auditAdapter)
	chatSvc.SetRAGProvider(ragAdapter) // Wire up RAG for knowledge-augmented responses
	onpageSvc := onpageService.NewOnPageService(onpageRepository, firecrawlClient)
	dashboardSvc := dashboardService.NewDashboardService(dashboardRepository, gscRepository)
	websiteSvc := websiteService.NewWebsiteService(websiteRepository, gscRepository)

	// Initialize handlers
	handlers := &router.Handlers{
		Auth:      authHandler.NewAuthHandler(authSvc, cfg.FrontendURL),
		GSC:       gscHandler.NewGSCHandler(gscSvc),
		Audit:     auditHandler.NewAuditHandler(auditSvc),
		Chat:      chatHandler.NewChatHandler(chatSvc),
		OnPage:    onpageHandler.NewOnPageHandler(onpageSvc),
		Benchmark: benchmarkHandler.NewBenchmarkHandler(benchmarkSvc),
		Dashboard: dashboardHandler.NewDashboardHandler(dashboardSvc),
		Website:   websiteHandler.NewWebsiteHandler(websiteSvc),
	}

	// Initialize router
	routerConfig := &router.Config{
		AllowedOrigins: cfg.AllowedOrigins,
		AuthService:    authSvc,
		Redis:          redis,
	}
	r := router.New(handlers, routerConfig)

	// Create HTTP server
	srv := &http.Server{
		Addr:         ":" + cfg.Port,
		Handler:      r,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 60 * time.Second, // Increased for PDF generation
		IdleTimeout:  60 * time.Second,
	}

	// Start server in goroutine
	go func() {
		log.Info().
			Str("port", cfg.Port).
			Str("env", cfg.Environment).
			Msg("Starting Solvia API v2")
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatal().Err(err).Msg("Failed to start server")
		}
	}()

	// Graceful shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Info().Msg("Shutting down server...")

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		log.Fatal().Err(err).Msg("Server forced to shutdown")
	}

	log.Info().Msg("Server exited gracefully")
}
