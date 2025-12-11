package handler

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/audit/domain"
	"github.com/petpeevephobia/solvia-v2/api/internal/modules/audit/service"
	apperrors "github.com/petpeevephobia/solvia-v2/api/internal/shared/errors"
	"github.com/petpeevephobia/solvia-v2/api/internal/shared/response"
)

// AuditHandler handles audit HTTP requests
type AuditHandler struct {
	auditService *service.AuditService
}

// NewAuditHandler creates a new audit handler
func NewAuditHandler(auditService *service.AuditService) *AuditHandler {
	return &AuditHandler{auditService: auditService}
}

// CreateAuditRequest represents the request to create an audit (1:1 with Python AuditRequest)
type CreateAuditRequest struct {
	WebsiteURL             string `json:"website_url" binding:"required"`
	DateRangeDays          int    `json:"date_range_days"`          // Days to analyze (default: 30)
	ReportFormat           string `json:"report_format"`            // pdf, json, or both (default: both)
	DeliveryMethod         string `json:"delivery_method"`          // email or download (default: email)
	ForceRefresh           bool   `json:"force_refresh"`            // Force fresh data fetch (default: false)
	IncludeRecommendations bool   `json:"include_recommendations"`  // Include AI recommendations (default: true)
}

// setDefaults sets default values for CreateAuditRequest (1:1 with Python)
func (r *CreateAuditRequest) setDefaults() {
	if r.DateRangeDays <= 0 {
		r.DateRangeDays = 30
	}
	if r.ReportFormat == "" {
		r.ReportFormat = "both"
	}
	if r.DeliveryMethod == "" {
		r.DeliveryMethod = "email"
	}
	// IncludeRecommendations defaults to true
	// Note: Go's zero value for bool is false, so we handle this in service layer
}

// CreateAudit starts a new audit
func (h *AuditHandler) CreateAudit(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	var req CreateAuditRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.Error(c, http.StatusBadRequest, "BAD_REQUEST", "Website URL is required")
		return
	}

	// Set defaults for optional fields (1:1 with Python)
	req.setDefaults()

	// Convert to service options (1:1 with Python AuditRequest)
	options := &service.AuditOptions{
		DateRangeDays:          req.DateRangeDays,
		ReportFormat:           req.ReportFormat,
		DeliveryMethod:         req.DeliveryMethod,
		ForceRefresh:           req.ForceRefresh,
		IncludeRecommendations: req.IncludeRecommendations,
	}

	audit, err := h.auditService.CreateAuditWithOptions(c.Request.Context(), userEmail, req.WebsiteURL, options)
	if err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusAccepted, gin.H{
		"audit":   audit,
		"message": "Audit started. Check status for completion.",
	})
}

// GetAudit retrieves an audit by ID
func (h *AuditHandler) GetAudit(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	idStr := c.Param("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		response.Error(c, http.StatusBadRequest, "BAD_REQUEST", "Invalid audit ID")
		return
	}

	audit, err := h.auditService.GetAudit(c.Request.Context(), id, userEmail)
	if err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, gin.H{
		"audit": audit,
	})
}

// GetAuditWithIssues retrieves an audit with its issues
func (h *AuditHandler) GetAuditWithIssues(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	idStr := c.Param("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		response.Error(c, http.StatusBadRequest, "BAD_REQUEST", "Invalid audit ID")
		return
	}

	data, err := h.auditService.GetAuditWithIssues(c.Request.Context(), id, userEmail)
	if err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, data)
}

// GetAuditHistory retrieves audit history
func (h *AuditHandler) GetAuditHistory(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	limitStr := c.DefaultQuery("limit", "20")
	limit, _ := strconv.Atoi(limitStr)

	audits, err := h.auditService.GetAuditHistory(c.Request.Context(), userEmail, limit)
	if err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, gin.H{
		"audits": audits,
	})
}

// GetLatestAudit retrieves the most recent audit for a website
func (h *AuditHandler) GetLatestAudit(c *gin.Context) {
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

	audit, err := h.auditService.GetLatestAudit(c.Request.Context(), userEmail, websiteURL)
	if err != nil {
		handleError(c, err)
		return
	}

	if audit == nil {
		response.Success(c, http.StatusOK, gin.H{
			"audit": nil,
		})
		return
	}

	response.Success(c, http.StatusOK, gin.H{
		"audit": audit,
	})
}

// DownloadPDF serves the PDF file
func (h *AuditHandler) DownloadPDF(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	idStr := c.Param("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		response.Error(c, http.StatusBadRequest, "BAD_REQUEST", "Invalid audit ID")
		return
	}

	audit, err := h.auditService.GetAudit(c.Request.Context(), id, userEmail)
	if err != nil {
		handleError(c, err)
		return
	}

	if audit.PDFPath == "" {
		response.Error(c, http.StatusNotFound, "NOT_FOUND", "PDF not available yet")
		return
	}

	// Check if file exists
	if _, err := os.Stat(audit.PDFPath); os.IsNotExist(err) {
		response.Error(c, http.StatusNotFound, "NOT_FOUND", "PDF file not found")
		return
	}

	filename := filepath.Base(audit.PDFPath)
	c.Header("Content-Disposition", "attachment; filename="+filename)
	c.Header("Content-Type", "application/pdf")
	c.File(audit.PDFPath)
}

// GetCurrentIssues retrieves issues from the latest audit
func (h *AuditHandler) GetCurrentIssues(c *gin.Context) {
	userEmail := c.GetString("user_email")
	websiteURL := c.Query("website")

	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	// Get latest audit with issues
	data, err := h.auditService.GetCurrentIssues(c.Request.Context(), userEmail, websiteURL)
	if err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, data)
}

// CheckAuditStatus checks the status of an audit (for polling)
func (h *AuditHandler) CheckAuditStatus(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	idStr := c.Param("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		response.Error(c, http.StatusBadRequest, "BAD_REQUEST", "Invalid audit ID")
		return
	}

	audit, err := h.auditService.GetAudit(c.Request.Context(), id, userEmail)
	if err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, gin.H{
		"id":           audit.ID,
		"status":       audit.Status,
		"seo_score":    audit.SEOScore,
		"seo_stage":    audit.SEOStage,
		"pdf_ready":    audit.PDFPath != "",
		"completed_at": audit.CompletedAt,
		"error":        audit.Error,
	})
}

// StreamAuditProgress streams audit progress via SSE (Server-Sent Events)
// This implements 1:1 parity with Python's SSE streaming for audit progress
func (h *AuditHandler) StreamAuditProgress(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "User not authenticated"})
		return
	}

	idStr := c.Param("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid audit ID"})
		return
	}

	// Verify ownership
	audit, err := h.auditService.GetAudit(c.Request.Context(), id, userEmail)
	if err != nil {
		handleError(c, err)
		return
	}

	// If audit is already completed, return immediately
	if audit.Status == domain.AuditStatusCompleted || audit.Status == domain.AuditStatusFailed {
		progress := &domain.AuditProgress{
			AuditID:  id,
			Stage:    domain.StageCompleted,
			Progress: 100,
			Message:  "Audit already completed",
		}
		if audit.Status == domain.AuditStatusFailed {
			progress.Stage = domain.StageError
			progress.Error = audit.Error
		}

		c.Header("Content-Type", "text/event-stream")
		c.Header("Cache-Control", "no-cache")
		c.Header("Connection", "keep-alive")
		c.Header("X-Accel-Buffering", "no")

		data, _ := json.Marshal(progress)
		c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(data)))
		c.Writer.Flush()
		return
	}

	// Set headers for SSE
	c.Header("Content-Type", "text/event-stream")
	c.Header("Cache-Control", "no-cache")
	c.Header("Connection", "keep-alive")
	c.Header("X-Accel-Buffering", "no")
	c.Header("Access-Control-Allow-Origin", "*")

	// Subscribe to progress updates
	subscription := domain.GlobalProgressTracker.Subscribe(id)
	defer domain.GlobalProgressTracker.Unsubscribe(subscription)

	// Client disconnect detection
	clientGone := c.Request.Context().Done()

	// Heartbeat ticker to keep connection alive
	heartbeat := time.NewTicker(15 * time.Second)
	defer heartbeat.Stop()

	// Timeout for the entire stream (5 minutes max)
	timeout := time.NewTimer(5 * time.Minute)
	defer timeout.Stop()

	c.Writer.Flush()

	for {
		select {
		case <-clientGone:
			// Client disconnected
			return

		case <-timeout.C:
			// Stream timeout - send final error
			errProgress := domain.AuditProgress{
				AuditID:  id,
				Stage:    domain.StageError,
				Progress: 0,
				Message:  "Audit timed out",
				Error:    "The audit took too long to complete",
			}
			data, _ := json.Marshal(errProgress)
			c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(data)))
			c.Writer.Flush()
			return

		case progress, ok := <-subscription.Ch:
			if !ok {
				// Channel closed
				return
			}

			// Send progress update
			data, err := json.Marshal(progress)
			if err != nil {
				continue
			}

			c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(data)))
			c.Writer.Flush()

			// If completed or error, close stream
			if progress.Stage == domain.StageCompleted || progress.Stage == domain.StageError {
				return
			}

		case <-heartbeat.C:
			// Send heartbeat to keep connection alive
			c.Writer.WriteString(": heartbeat\n\n")
			c.Writer.Flush()
		}
	}
}

// GetAuditProgress returns the current progress of an audit (non-streaming)
func (h *AuditHandler) GetAuditProgress(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	idStr := c.Param("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		response.Error(c, http.StatusBadRequest, "BAD_REQUEST", "Invalid audit ID")
		return
	}

	// Verify ownership
	_, err = h.auditService.GetAudit(c.Request.Context(), id, userEmail)
	if err != nil {
		handleError(c, err)
		return
	}

	// Get progress from tracker
	progress := domain.GlobalProgressTracker.GetProgress(id)
	if progress == nil {
		// If no progress tracked, check audit status
		audit, _ := h.auditService.GetAudit(c.Request.Context(), id, userEmail)
		if audit != nil {
			progress = &domain.AuditProgress{
				AuditID:  id,
				Progress: 0,
				Message:  "Audit status: " + string(audit.Status),
			}

			if audit.Status == domain.AuditStatusCompleted {
				progress.Stage = domain.StageCompleted
				progress.Progress = 100
				progress.Message = "Audit completed"
			} else if audit.Status == domain.AuditStatusFailed {
				progress.Stage = domain.StageError
				progress.Error = audit.Error
			} else if audit.Status == domain.AuditStatusProcessing {
				progress.Stage = domain.StageFetchingGSCData
				progress.Progress = 20
				progress.Message = "Processing audit..."
			}
		}
	}

	if progress == nil {
		response.Error(c, http.StatusNotFound, "NOT_FOUND", "No progress information available")
		return
	}

	response.Success(c, http.StatusOK, progress)
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
// ADDITIONAL 1:1 PARITY ENDPOINTS
// ============================================================================

// Health returns the audit engine health status (1:1 with Python /audit/health)
func (h *AuditHandler) Health(c *gin.Context) {
	// Match Python's response format exactly
	response.Success(c, http.StatusOK, gin.H{
		"status": "healthy",
		"engine": "audit_engine_v1",
		"analyzers": []string{
			"performance",
			"anomaly",
			"trends",
			"opportunities",
		},
	})
}

// ExportAudit exports audit results in JSON format (1:1 with Python /audit/export/{audit_id})
// Note: PDF export is handled separately via DownloadPDF
func (h *AuditHandler) ExportAudit(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	idStr := c.Param("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		response.Error(c, http.StatusBadRequest, "BAD_REQUEST", "Invalid audit ID")
		return
	}

	// Get format from query param (default: json)
	format := c.DefaultQuery("format", "json")

	// PDF export is handled by DownloadPDF endpoint
	if format == "pdf" {
		response.Error(c, http.StatusBadRequest, "BAD_REQUEST", "Use /audit/:id/pdf for PDF download")
		return
	}

	// Get audit with issues for complete export
	data, err := h.auditService.GetAuditWithIssues(c.Request.Context(), id, userEmail)
	if err != nil {
		handleError(c, err)
		return
	}

	// Set headers for JSON download (1:1 with Python)
	c.Header("Content-Disposition", fmt.Sprintf("attachment; filename=audit_%d.json", id))
	c.Header("Content-Type", "application/json")

	response.Success(c, http.StatusOK, data)
}
