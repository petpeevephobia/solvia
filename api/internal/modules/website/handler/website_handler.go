package handler

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/website/service"
	apperrors "github.com/petpeevephobia/solvia-v2/api/internal/shared/errors"
	"github.com/petpeevephobia/solvia-v2/api/internal/shared/response"
)

// WebsiteHandler handles website content HTTP requests
type WebsiteHandler struct {
	websiteService *service.WebsiteService
}

// NewWebsiteHandler creates a new website handler
func NewWebsiteHandler(websiteService *service.WebsiteService) *WebsiteHandler {
	return &WebsiteHandler{websiteService: websiteService}
}

// FetchContent handles POST /website/content/fetch - fetches and stores website content (1:1 with Python)
func (h *WebsiteHandler) FetchContent(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	content, err := h.websiteService.FetchContent(c.Request.Context(), userEmail)
	if err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, gin.H{
		"success": true,
		"message": "Website content fetched and stored successfully!",
		"content": gin.H{
			"title_tags":        content.TitleTags,
			"meta_descriptions": content.MetaDescriptions,
			"page_content":      content.PageContent,
		},
	})
}

// GetContent handles GET /website/content - gets stored website content (1:1 with Python)
func (h *WebsiteHandler) GetContent(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	content, websiteURL, err := h.websiteService.GetContent(c.Request.Context(), userEmail)
	if err != nil {
		handleError(c, err)
		return
	}

	if content == nil {
		response.Success(c, http.StatusOK, gin.H{
			"success":    false,
			"message":    "No website content found. Please fetch content first.",
			"content":    nil,
			"fetched_at": nil,
			"website":    websiteURL,
		})
		return
	}

	response.Success(c, http.StatusOK, gin.H{
		"success": true,
		"message": "Website content retrieved successfully!",
		"content": gin.H{
			"title_tags":        content.TitleTags,
			"meta_descriptions": content.MetaDescriptions,
			"page_content":      content.PageContent,
		},
		"fetched_at": content.FetchedAt,
		"website":    websiteURL,
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
