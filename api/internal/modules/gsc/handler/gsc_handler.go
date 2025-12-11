package handler

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/gsc/domain"
	"github.com/petpeevephobia/solvia-v2/api/internal/modules/gsc/service"
	apperrors "github.com/petpeevephobia/solvia-v2/api/internal/shared/errors"
	"github.com/petpeevephobia/solvia-v2/api/internal/shared/response"
)

// GSCHandler handles GSC HTTP requests
type GSCHandler struct {
	gscService *service.GSCService
}

// NewGSCHandler creates a new GSC handler
func NewGSCHandler(gscService *service.GSCService) *GSCHandler {
	return &GSCHandler{gscService: gscService}
}

// GetWebsites returns all connected websites
func (h *GSCHandler) GetWebsites(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	websites, err := h.gscService.GetWebsites(c.Request.Context(), userEmail)
	if err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, gin.H{
		"websites": websites,
	})
}

// GetSelectedWebsite returns the user's selected website (1:1 parity with original Python)
func (h *GSCHandler) GetSelectedWebsite(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	websiteURL, err := h.gscService.GetSelectedWebsite(c.Request.Context(), userEmail)
	if err != nil {
		handleError(c, err)
		return
	}

	if websiteURL != "" {
		response.Success(c, http.StatusOK, gin.H{
			"success":          true,
			"selected_website": websiteURL,
		})
	} else {
		response.Success(c, http.StatusOK, gin.H{
			"success":          false,
			"selected_website": nil,
		})
	}
}

// SelectProperty sets the user's selected website (1:1 parity with original Python)
func (h *GSCHandler) SelectProperty(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	var req struct {
		PropertyURL string `json:"property_url" binding:"required"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		response.Error(c, http.StatusBadRequest, "BAD_REQUEST", "Property URL is required")
		return
	}

	if err := h.gscService.SetSelectedWebsite(c.Request.Context(), userEmail, req.PropertyURL); err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, gin.H{
		"success": true,
		"message": "Property " + req.PropertyURL + " selected successfully",
	})
}

// SyncWebsites syncs websites from GSC
func (h *GSCHandler) SyncWebsites(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	websites, err := h.gscService.SyncWebsites(c.Request.Context(), userEmail)
	if err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, gin.H{
		"websites": websites,
		"synced":   true,
	})
}

// GetMetrics returns metrics for selected website
func (h *GSCHandler) GetMetrics(c *gin.Context) {
	userEmail := c.GetString("user_email")
	websiteURL := c.Query("website")

	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	if websiteURL == "" {
		response.Error(c, http.StatusBadRequest, "BAD_REQUEST", "Website URL is required")
		return
	}

	filter := parseFilter(c)

	metrics, err := h.gscService.GetMetrics(c.Request.Context(), userEmail, websiteURL, filter)
	if err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, metrics)
}

// GetQueries returns top queries
func (h *GSCHandler) GetQueries(c *gin.Context) {
	userEmail := c.GetString("user_email")
	websiteURL := c.Query("website")

	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	if websiteURL == "" {
		response.Error(c, http.StatusBadRequest, "BAD_REQUEST", "Website URL is required")
		return
	}

	filter := parseFilter(c)

	queries, err := h.gscService.GetQueries(c.Request.Context(), userEmail, websiteURL, filter)
	if err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, gin.H{
		"queries": queries,
	})
}

// GetPages returns top pages
func (h *GSCHandler) GetPages(c *gin.Context) {
	userEmail := c.GetString("user_email")
	websiteURL := c.Query("website")

	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	if websiteURL == "" {
		response.Error(c, http.StatusBadRequest, "BAD_REQUEST", "Website URL is required")
		return
	}

	filter := parseFilter(c)

	pages, err := h.gscService.GetPages(c.Request.Context(), userEmail, websiteURL, filter)
	if err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, gin.H{
		"pages": pages,
	})
}

// GetDailyMetrics returns daily metrics for charts
func (h *GSCHandler) GetDailyMetrics(c *gin.Context) {
	userEmail := c.GetString("user_email")
	websiteURL := c.Query("website")

	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	if websiteURL == "" {
		response.Error(c, http.StatusBadRequest, "BAD_REQUEST", "Website URL is required")
		return
	}

	filter := parseFilter(c)

	metrics, err := h.gscService.GetDailyMetrics(c.Request.Context(), userEmail, websiteURL, filter)
	if err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, gin.H{
		"daily_metrics": metrics,
	})
}

// parseFilter extracts filter parameters from request
func parseFilter(c *gin.Context) domain.MetricsFilter {
	filter := domain.DefaultFilter()

	if startDate := c.Query("start_date"); startDate != "" {
		if t, err := time.Parse("2006-01-02", startDate); err == nil {
			filter.StartDate = t
		}
	}

	if endDate := c.Query("end_date"); endDate != "" {
		if t, err := time.Parse("2006-01-02", endDate); err == nil {
			filter.EndDate = t
		}
	}

	return filter
}

// handleError converts AppError to HTTP response
func handleError(c *gin.Context, err error) {
	if appErr := apperrors.GetAppError(err); appErr != nil {
		response.Error(c, appErr.StatusCode, appErr.Code, appErr.Message)
		return
	}
	response.Error(c, http.StatusInternalServerError, "INTERNAL_ERROR", "An unexpected error occurred")
}

// ============================================================================
// GSC FILTER HANDLERS (1:1 with Python implementation)
// ============================================================================

// ApplyFilter handles POST /gsc/filter - applies filters to GSC data
func (h *GSCHandler) ApplyFilter(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	var req domain.GSCFilterRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.Error(c, http.StatusBadRequest, "BAD_REQUEST", "Invalid filter request: "+err.Error())
		return
	}

	// Set defaults if not provided
	if req.SearchType == "" {
		req.SearchType = "web"
	}
	if len(req.Dimensions) == 0 {
		req.Dimensions = []string{"date"}
	}
	if req.AggregationType == "" {
		req.AggregationType = "auto"
	}
	if req.RowLimit == 0 {
		req.RowLimit = 1000
	}
	if req.DataState == "" {
		req.DataState = "final"
	}

	metrics, websiteURL, err := h.gscService.ApplyFilter(c.Request.Context(), userEmail, &req)
	if err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, gin.H{
		"success": true,
		"metrics": metrics,
		"website": websiteURL,
	})
}

// GetFilterPreset handles GET /gsc/filter/preset/:preset_name - returns preset configuration
func (h *GSCHandler) GetFilterPreset(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	presetName := c.Param("preset_name")
	if presetName == "" {
		response.Error(c, http.StatusBadRequest, "BAD_REQUEST", "Preset name is required")
		return
	}

	preset, err := h.gscService.GetDatePreset(presetName)
	if err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, gin.H{
		"success": true,
		"preset":  preset,
	})
}

// ============================================================================
// ADDITIONAL 1:1 PARITY HANDLERS
// ============================================================================

// GetKeywords handles GET /gsc/keywords - returns keywords for selected property (1:1 with Python)
func (h *GSCHandler) GetKeywords(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	keywords, err := h.gscService.GetKeywords(c.Request.Context(), userEmail)
	if err != nil {
		handleError(c, err)
		return
	}

	// Return empty array if no keywords found (don't treat as error)
	if keywords == nil {
		keywords = []domain.Query{}
	}

	response.Success(c, http.StatusOK, gin.H{
		"keywords": keywords,
	})
}

// RefreshMetrics handles POST /gsc/refresh - refreshes SEO metrics (1:1 with Python)
func (h *GSCHandler) RefreshMetrics(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	metrics, websiteURL, err := h.gscService.RefreshMetrics(c.Request.Context(), userEmail)
	if err != nil {
		handleError(c, err)
		return
	}

	if metrics == nil {
		response.Error(c, http.StatusBadRequest, "BAD_REQUEST", "Failed to refresh SEO metrics")
		return
	}

	response.Success(c, http.StatusOK, gin.H{
		"success": true,
		"message": "SEO metrics refreshed successfully!",
		"metrics": metrics,
		"website": websiteURL,
	})
}

// GetProperties handles GET /gsc/properties - returns GSC properties (1:1 with Python)
func (h *GSCHandler) GetProperties(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	properties, err := h.gscService.GetProperties(c.Request.Context(), userEmail)
	if err != nil {
		handleError(c, err)
		return
	}

	if properties == nil {
		properties = []domain.Website{}
	}

	// Format response to match Python exactly
	var formattedProperties []gin.H
	for _, p := range properties {
		formattedProperties = append(formattedProperties, gin.H{
			"siteUrl":         p.SiteURL,
			"permissionLevel": p.PermissionLevel,
			"isVerified":      p.IsVerified, // 1:1 with Python
		})
	}

	if formattedProperties == nil {
		response.Success(c, http.StatusOK, gin.H{
			"properties": []gin.H{},
			"message":    "No properties found in Google Search Console",
		})
		return
	}

	response.Success(c, http.StatusOK, gin.H{
		"properties": formattedProperties,
		"message":    "Properties retrieved successfully",
	})
}

// ============================================================================
// ADDITIONAL ENDPOINTS FOR 1:1 PYTHON PARITY
// ============================================================================

// GetSelected handles GET /gsc/selected - alias for GetSelectedWebsite (1:1 with Python)
// Python has both /gsc/selected-website and /gsc/selected endpoints
func (h *GSCHandler) GetSelected(c *gin.Context) {
	// Simply delegate to GetSelectedWebsite for consistent behavior
	h.GetSelectedWebsite(c)
}

// ClearCredentials handles POST /gsc/clear-credentials - clears user's GSC OAuth credentials (1:1 with Python)
// This allows users to disconnect their GSC account and re-authenticate
func (h *GSCHandler) ClearCredentials(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	if err := h.gscService.ClearCredentials(c.Request.Context(), userEmail); err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, gin.H{
		"success": true,
		"message": "GSC credentials cleared successfully. Please re-authenticate with Google.",
	})
}
