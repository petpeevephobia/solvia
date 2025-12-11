package handler

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/onpage/domain"
	"github.com/petpeevephobia/solvia-v2/api/internal/modules/onpage/service"
	apperrors "github.com/petpeevephobia/solvia-v2/api/internal/shared/errors"
	"github.com/petpeevephobia/solvia-v2/api/internal/shared/response"
)

// OnPageHandler handles on-page SEO HTTP requests
type OnPageHandler struct {
	onpageService *service.OnPageService
}

// NewOnPageHandler creates a new on-page handler
func NewOnPageHandler(onpageService *service.OnPageService) *OnPageHandler {
	return &OnPageHandler{onpageService: onpageService}
}

// AnalyzePage starts a page analysis
func (h *OnPageHandler) AnalyzePage(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	var req domain.AnalysisRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.Error(c, http.StatusBadRequest, "BAD_REQUEST", "URL is required")
		return
	}

	analysis, err := h.onpageService.AnalyzePage(c.Request.Context(), userEmail, req.URL)
	if err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusAccepted, gin.H{
		"analysis": analysis,
		"message":  "Analysis started. Check status for completion.",
	})
}

// GetAnalysis retrieves an analysis by ID
func (h *OnPageHandler) GetAnalysis(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	idStr := c.Param("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		response.Error(c, http.StatusBadRequest, "BAD_REQUEST", "Invalid analysis ID")
		return
	}

	result, err := h.onpageService.GetAnalysis(c.Request.Context(), id, userEmail)
	if err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, result)
}

// GetAnalysisHistory retrieves analysis history
func (h *OnPageHandler) GetAnalysisHistory(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	limitStr := c.DefaultQuery("limit", "20")
	limit, _ := strconv.Atoi(limitStr)

	analyses, err := h.onpageService.GetAnalysisHistory(c.Request.Context(), userEmail, limit)
	if err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, gin.H{
		"analyses": analyses,
	})
}

// CheckAnalysisStatus checks the status of an analysis
func (h *OnPageHandler) CheckAnalysisStatus(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	idStr := c.Param("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		response.Error(c, http.StatusBadRequest, "BAD_REQUEST", "Invalid analysis ID")
		return
	}

	result, err := h.onpageService.GetAnalysis(c.Request.Context(), id, userEmail)
	if err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, gin.H{
		"id":           result.Analysis.ID,
		"status":       result.Analysis.Status,
		"score":        result.Analysis.Score,
		"completed_at": result.Analysis.CompletedAt,
		"error":        result.Analysis.Error,
	})
}

// MapSiteRequest represents a site map request
type MapSiteRequest struct {
	URL   string `json:"url" binding:"required"`
	Limit int    `json:"limit,omitempty"`
}

// MapSite maps all URLs on a site
func (h *OnPageHandler) MapSite(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	var req MapSiteRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.Error(c, http.StatusBadRequest, "BAD_REQUEST", "URL is required")
		return
	}

	if req.Limit <= 0 {
		req.Limit = 50
	}

	result, err := h.onpageService.MapSite(c.Request.Context(), userEmail, req.URL, req.Limit)
	if err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, result)
}

// CrawlWebsiteRequest represents a website crawl request
type CrawlWebsiteRequest struct {
	URL string `json:"url" binding:"required"`
}

// CrawlWebsite performs comprehensive website analysis (1:1 with Python website_crawler.py)
// Returns business type, keywords, services, and content analysis
func (h *OnPageHandler) CrawlWebsite(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	var req CrawlWebsiteRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.Error(c, http.StatusBadRequest, "BAD_REQUEST", "URL is required")
		return
	}

	analysis, err := h.onpageService.CrawlWebsite(c.Request.Context(), req.URL)
	if err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, analysis)
}

// handleError converts AppError to HTTP response
func handleError(c *gin.Context, err error) {
	if appErr := apperrors.GetAppError(err); appErr != nil {
		response.Error(c, appErr.StatusCode, appErr.Code, appErr.Message)
		return
	}
	response.Error(c, http.StatusInternalServerError, "INTERNAL_ERROR", "An unexpected error occurred")
}
