package handler

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/benchmark/service"
	apperrors "github.com/petpeevephobia/solvia-v2/api/internal/shared/errors"
	"github.com/petpeevephobia/solvia-v2/api/internal/shared/response"
)

// BenchmarkHandler handles benchmark HTTP requests
type BenchmarkHandler struct {
	benchmarkService *service.BenchmarkService
}

// NewBenchmarkHandler creates a new benchmark handler
func NewBenchmarkHandler(benchmarkService *service.BenchmarkService) *BenchmarkHandler {
	return &BenchmarkHandler{benchmarkService: benchmarkService}
}

// GetBenchmarkInsights handles GET /benchmark/insights (1:1 with Python)
// Supports explicit_ai query param or X-Explicit-AI-Request header for explicit generation
func (h *BenchmarkHandler) GetBenchmarkInsights(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	// Check for explicit AI request (query param or header)
	explicitAI := c.Query("explicit_ai")
	explicitHeader := c.GetHeader("X-Explicit-AI-Request")
	explicit := explicitAI == "true" || explicitHeader == "true"

	insights, err := h.benchmarkService.GetBenchmarkInsights(c.Request.Context(), userEmail, explicit)
	if err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, insights)
}

// handleError converts AppError to HTTP response
func handleError(c *gin.Context, err error) {
	if appErr := apperrors.GetAppError(err); appErr != nil {
		response.Error(c, appErr.StatusCode, appErr.Code, appErr.Message)
		return
	}
	response.Error(c, http.StatusInternalServerError, "INTERNAL_ERROR", "An unexpected error occurred")
}
