package handler

import (
	"fmt"
	"net/http"
	"net/url"

	"github.com/gin-gonic/gin"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/auth/domain"
	"github.com/petpeevephobia/solvia-v2/api/internal/modules/auth/service"
	"github.com/petpeevephobia/solvia-v2/api/internal/shared/response"
)

// AuthHandler handles authentication HTTP requests
type AuthHandler struct {
	authService *service.AuthService
	frontendURL string
}

// NewAuthHandler creates a new auth handler
func NewAuthHandler(authService *service.AuthService, frontendURL string) *AuthHandler {
	return &AuthHandler{
		authService: authService,
		frontendURL: frontendURL,
	}
}

// GetAuthURL returns the Google OAuth URL
func (h *AuthHandler) GetAuthURL(c *gin.Context) {
	state := c.Query("state")
	if state == "" {
		state = "default"
	}

	url := h.authService.GetAuthURL(state)

	response.Success(c, http.StatusOK, gin.H{
		"auth_url": url,
	})
}

// CallbackRequest represents the OAuth callback request
type CallbackRequest struct {
	Code  string `json:"code" binding:"required"`
	State string `json:"state"`
}

// Callback handles the OAuth callback with automatic device trust management (1:1 with Python)
func (h *AuthHandler) Callback(c *gin.Context) {
	var req CallbackRequest

	// Try JSON body first, then query params
	if err := c.ShouldBindJSON(&req); err != nil {
		req.Code = c.Query("code")
		req.State = c.Query("state")
	}

	if req.Code == "" {
		// Redirect to frontend with error
		redirectURL := fmt.Sprintf("%s/auth/callback?error=%s", h.frontendURL, url.QueryEscape("Authorization code is required"))
		c.Redirect(http.StatusTemporaryRedirect, redirectURL)
		return
	}

	result, err := h.authService.HandleCallback(c.Request.Context(), req.Code)
	if err != nil {
		// Redirect to frontend with error
		redirectURL := fmt.Sprintf("%s/auth/callback?error=%s", h.frontendURL, url.QueryEscape(err.Error()))
		c.Redirect(http.StatusTemporaryRedirect, redirectURL)
		return
	}

	// Auto-mark device as trusted for better UX (1:1 with Python)
	// Python: "Always mark device as trusted for better UX"
	if result.User != nil && result.User.Email != "" {
		deviceRequest := h.extractDeviceTrustRequest(c)
		if err := h.authService.MarkDeviceTrusted(c.Request.Context(), result.User.Email, deviceRequest); err != nil {
			// Non-fatal error - log but don't fail the callback
			fmt.Printf("[DEVICE TRUST] Warning: Could not mark device as trusted: %v\n", err)
		} else {
			fingerprint := deviceRequest.GenerateFingerprint()
			fmt.Printf("[DEVICE TRUST] Device %s... marked as trusted for %s\n", fingerprint[:8], result.User.Email)
		}
	}

	// Redirect to frontend with token
	redirectURL := fmt.Sprintf("%s/auth/callback?token=%s&expires_in=%d",
		h.frontendURL,
		url.QueryEscape(result.AccessToken),
		result.ExpiresIn,
	)
	c.Redirect(http.StatusTemporaryRedirect, redirectURL)
}

// GetCurrentUser returns the current authenticated user
func (h *AuthHandler) GetCurrentUser(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	user, err := h.authService.GetUser(c.Request.Context(), userEmail)
	if err != nil {
		response.Error(c, http.StatusNotFound, "NOT_FOUND", "User not found")
		return
	}

	response.Success(c, http.StatusOK, gin.H{
		"user": user,
	})
}

// RefreshToken refreshes the access token
func (h *AuthHandler) RefreshToken(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	result, err := h.authService.RefreshToken(c.Request.Context(), userEmail)
	if err != nil {
		response.Error(c, http.StatusUnauthorized, "REFRESH_FAILED", err.Error())
		return
	}

	response.Success(c, http.StatusOK, result)
}

// Logout logs out the user
func (h *AuthHandler) Logout(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	if err := h.authService.Logout(c.Request.Context(), userEmail); err != nil {
		response.Error(c, http.StatusInternalServerError, "LOGOUT_FAILED", err.Error())
		return
	}

	response.Success(c, http.StatusOK, gin.H{
		"message": "Logged out successfully",
	})
}

// ============================================================
// Device Trust Handlers (1:1 with Python implementation)
// ============================================================

// extractDeviceTrustRequest extracts device fingerprint data from request headers
func (h *AuthHandler) extractDeviceTrustRequest(c *gin.Context) *domain.DeviceTrustRequest {
	return &domain.DeviceTrustRequest{
		UserAgent:      c.GetHeader("User-Agent"),
		AcceptLanguage: c.GetHeader("Accept-Language"),
		AcceptEncoding: c.GetHeader("Accept-Encoding"),
		IPAddress:      c.ClientIP(),
	}
}

// GetAuthURLWithDeviceTrust returns the Google OAuth URL considering device trust
func (h *AuthHandler) GetAuthURLWithDeviceTrust(c *gin.Context) {
	state := c.Query("state")
	if state == "" {
		state = "default"
	}

	// Check if user is already known (from cookie or header)
	userEmail := c.Query("email")

	// Extract device fingerprint from request
	deviceRequest := h.extractDeviceTrustRequest(c)

	url := h.authService.GetAuthURLWithDeviceTrust(c.Request.Context(), state, deviceRequest, userEmail)

	response.Success(c, http.StatusOK, gin.H{
		"auth_url": url,
	})
}

// CheckDeviceTrust checks if the current device is trusted for the user
func (h *AuthHandler) CheckDeviceTrust(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	deviceRequest := h.extractDeviceTrustRequest(c)
	isTrusted := h.authService.IsDeviceTrusted(c.Request.Context(), userEmail, deviceRequest)

	response.Success(c, http.StatusOK, gin.H{
		"trusted":     isTrusted,
		"fingerprint": deviceRequest.GenerateFingerprint(),
	})
}

// TrustDeviceRequest represents the request to trust a device
type TrustDeviceRequest struct {
	RememberDevice bool `json:"remember_device"`
}

// MarkDeviceTrusted marks the current device as trusted for 30 days
func (h *AuthHandler) MarkDeviceTrusted(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	var req TrustDeviceRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		// Default to trusting the device if no body provided
		req.RememberDevice = true
	}

	if !req.RememberDevice {
		response.Success(c, http.StatusOK, gin.H{
			"message": "Device not marked as trusted",
			"trusted": false,
		})
		return
	}

	deviceRequest := h.extractDeviceTrustRequest(c)
	if err := h.authService.MarkDeviceTrusted(c.Request.Context(), userEmail, deviceRequest); err != nil {
		response.Error(c, http.StatusInternalServerError, "TRUST_FAILED", err.Error())
		return
	}

	response.Success(c, http.StatusOK, gin.H{
		"message":     "Device marked as trusted for 30 days",
		"trusted":     true,
		"fingerprint": deviceRequest.GenerateFingerprint(),
	})
}

// ============================================================
// Email Verification & Password Reset Handlers (1:1 with Python)
// Note: These match Python's stub implementation for API parity
// ============================================================

// EmailVerificationRequest represents email verification request
type EmailVerificationRequest struct {
	Token string `json:"token" binding:"required"`
}

// VerifyEmail handles email verification (1:1 with Python - stub implementation)
func (h *AuthHandler) VerifyEmail(c *gin.Context) {
	var req EmailVerificationRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.Error(c, http.StatusBadRequest, "INVALID_REQUEST", "Token is required")
		return
	}

	// Match Python's stub response
	response.Success(c, http.StatusOK, gin.H{
		"message": "Email verification feature not available",
	})
}

// PasswordResetRequest represents password reset request
type PasswordResetRequest struct {
	Email string `json:"email" binding:"required,email"`
}

// ForgotPassword initiates password reset (1:1 with Python)
func (h *AuthHandler) ForgotPassword(c *gin.Context) {
	var req PasswordResetRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.Error(c, http.StatusBadRequest, "INVALID_REQUEST", "Valid email is required")
		return
	}

	// Match Python's behavior: always return success message for security
	// (don't reveal if email exists or not)
	response.Success(c, http.StatusOK, gin.H{
		"message": "If the email exists, a reset link has been sent",
	})
}

// PasswordResetConfirmRequest represents password reset confirmation
type PasswordResetConfirmRequest struct {
	Token       string `json:"token" binding:"required"`
	NewPassword string `json:"new_password" binding:"required,min=8"`
}

// ResetPassword handles password reset confirmation (1:1 with Python - stub implementation)
func (h *AuthHandler) ResetPassword(c *gin.Context) {
	var req PasswordResetConfirmRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.Error(c, http.StatusBadRequest, "INVALID_REQUEST", "Token and new password are required")
		return
	}

	// Validate password strength (matching Python's is_strong_password)
	if !isStrongPassword(req.NewPassword) {
		response.Error(c, http.StatusBadRequest, "WEAK_PASSWORD",
			"Password must be at least 8 characters long and contain uppercase, lowercase, and digit")
		return
	}

	// Match Python's stub response
	response.Success(c, http.StatusOK, gin.H{
		"message": "Password reset functionality not implemented in current version",
	})
}

// isStrongPassword checks if password meets strength requirements
// Matches Python's is_strong_password function
func isStrongPassword(password string) bool {
	if len(password) < 8 {
		return false
	}

	hasUpper := false
	hasLower := false
	hasDigit := false

	for _, c := range password {
		switch {
		case c >= 'A' && c <= 'Z':
			hasUpper = true
		case c >= 'a' && c <= 'z':
			hasLower = true
		case c >= '0' && c <= '9':
			hasDigit = true
		}
	}

	return hasUpper && hasLower && hasDigit
}
