package middleware

import (
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/auth/service"
	"github.com/petpeevephobia/solvia-v2/api/internal/shared/response"
)

// AuthMiddleware creates authentication middleware
func AuthMiddleware(authService *service.AuthService) gin.HandlerFunc {
	return func(c *gin.Context) {
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "Authorization header required")
			c.Abort()
			return
		}

		// Extract Bearer token
		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || strings.ToLower(parts[0]) != "bearer" {
			response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "Invalid authorization format")
			c.Abort()
			return
		}

		tokenString := parts[1]

		// Validate token
		email, err := authService.ValidateToken(tokenString)
		if err != nil {
			response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "Invalid or expired token")
			c.Abort()
			return
		}

		// Set user email in context
		c.Set("user_email", email)
		c.Next()
	}
}

// OptionalAuthMiddleware allows requests without auth but sets user if present
func OptionalAuthMiddleware(authService *service.AuthService) gin.HandlerFunc {
	return func(c *gin.Context) {
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			c.Next()
			return
		}

		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || strings.ToLower(parts[0]) != "bearer" {
			c.Next()
			return
		}

		tokenString := parts[1]
		email, err := authService.ValidateToken(tokenString)
		if err == nil {
			c.Set("user_email", email)
		}

		c.Next()
	}
}
