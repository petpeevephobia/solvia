package handler

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/dashboard/domain"
	"github.com/petpeevephobia/solvia-v2/api/internal/modules/dashboard/service"
	apperrors "github.com/petpeevephobia/solvia-v2/api/internal/shared/errors"
	"github.com/petpeevephobia/solvia-v2/api/internal/shared/response"
)

// DashboardHandler handles dashboard HTTP requests
type DashboardHandler struct {
	dashboardService *service.DashboardService
}

// NewDashboardHandler creates a new dashboard handler
func NewDashboardHandler(dashboardService *service.DashboardService) *DashboardHandler {
	return &DashboardHandler{dashboardService: dashboardService}
}

// GetCache handles GET /dashboard/cache - retrieves cached dashboard data (1:1 with Python)
func (h *DashboardHandler) GetCache(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	cache, websiteURL, err := h.dashboardService.GetCache(c.Request.Context(), userEmail)
	if err != nil {
		handleError(c, err)
		return
	}

	// No website selected
	if websiteURL == "" {
		response.Success(c, http.StatusOK, gin.H{
			"success":   false,
			"has_cache": false,
			"data":      nil,
			"message":   "No website property selected for user.",
		})
		return
	}

	// No cache found
	if cache == nil {
		response.Success(c, http.StatusOK, gin.H{
			"success":   true,
			"has_cache": false,
			"data":      nil,
			"message":   "No cached dashboard data found.",
		})
		return
	}

	// Cache found
	response.Success(c, http.StatusOK, gin.H{
		"success":   true,
		"has_cache": true,
		"data":      cache.Data,
		"message":   "Loaded latest cached dashboard data.",
	})
}

// SaveCache handles POST /dashboard/cache - saves dashboard cache (1:1 with Python)
func (h *DashboardHandler) SaveCache(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	var req domain.CacheDashboardRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.Success(c, http.StatusOK, gin.H{
			"success": false,
			"message": "Failed to parse request: " + err.Error(),
		})
		return
	}

	if err := h.dashboardService.SaveCache(c.Request.Context(), userEmail, &req); err != nil {
		// Return success:false instead of error for parity with Python
		response.Success(c, http.StatusOK, gin.H{
			"success": false,
			"message": err.Error(),
		})
		return
	}

	response.Success(c, http.StatusOK, gin.H{
		"success": true,
		"message": "Dashboard data cached successfully!",
	})
}

// handleError converts AppError to HTTP response
func handleError(c *gin.Context, err error) {
	if appErr := apperrors.GetAppError(err); appErr != nil {
		response.Error(c, appErr.StatusCode, appErr.Code, appErr.Message)
		return
	}
	response.Error(c, http.StatusInternalServerError, "INTERNAL_ERROR", "An unexpected error occurred")
}
