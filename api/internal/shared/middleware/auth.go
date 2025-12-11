package middleware

import (
	"fmt"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"

	"github.com/petpeevephobia/solvia-v2/api/internal/shared/response"
)

// Auth returns a middleware for JWT authentication (1:1 with Python auth/utils.py)
func Auth(jwtSecret string) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Get Authorization header
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "Authorization header required")
			c.Abort()
			return
		}

		// Check Bearer prefix
		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || parts[0] != "Bearer" {
			response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "Invalid authorization format")
			c.Abort()
			return
		}

		tokenString := parts[1]

		if tokenString == "" {
			response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "Invalid token")
			c.Abort()
			return
		}

		// Parse and validate JWT token (1:1 with Python auth/utils.py)
		token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
			// Validate signing method is HS256 (1:1 with Python ALGORITHM = "HS256")
			if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
				return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
			}
			return []byte(jwtSecret), nil
		})

		if err != nil {
			response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "Invalid or expired token")
			c.Abort()
			return
		}

		// Extract claims
		claims, ok := token.Claims.(jwt.MapClaims)
		if !ok || !token.Valid {
			response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "Invalid token claims")
			c.Abort()
			return
		}

		// Extract user email from claims (1:1 with Python - uses 'email' or 'sub' field)
		var userEmail string
		if email, exists := claims["email"]; exists {
			userEmail = fmt.Sprintf("%v", email)
		} else if sub, exists := claims["sub"]; exists {
			userEmail = fmt.Sprintf("%v", sub)
		}

		if userEmail == "" {
			response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "No user identifier in token")
			c.Abort()
			return
		}

		// Set user info in context for downstream handlers
		c.Set("user_email", userEmail)
		if name, exists := claims["name"]; exists {
			c.Set("user_name", fmt.Sprintf("%v", name))
		}
		if picture, exists := claims["picture"]; exists {
			c.Set("user_picture", fmt.Sprintf("%v", picture))
		}

		c.Next()
	}
}

// OptionalAuth allows requests without authentication but parses token if present
func OptionalAuth(jwtSecret string) gin.HandlerFunc {
	return func(c *gin.Context) {
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			c.Next()
			return
		}

		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || parts[0] != "Bearer" {
			c.Next()
			return
		}

		tokenString := parts[1]
		if tokenString == "" {
			c.Next()
			return
		}

		// Try to parse JWT - don't fail if invalid, just continue without user context
		token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
			if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
				return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
			}
			return []byte(jwtSecret), nil
		})

		if err == nil && token.Valid {
			if claims, ok := token.Claims.(jwt.MapClaims); ok {
				if email, exists := claims["email"]; exists {
					c.Set("user_email", fmt.Sprintf("%v", email))
				} else if sub, exists := claims["sub"]; exists {
					c.Set("user_email", fmt.Sprintf("%v", sub))
				}
				if name, exists := claims["name"]; exists {
					c.Set("user_name", fmt.Sprintf("%v", name))
				}
			}
		}

		c.Next()
	}
}
