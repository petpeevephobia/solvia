package middleware

import (
	"time"

	"github.com/gin-gonic/gin"
	"github.com/rs/zerolog/log"
)

// Logger returns a gin middleware for logging requests
func Logger() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		path := c.Request.URL.Path
		query := c.Request.URL.RawQuery

		// Process request
		c.Next()

		// Calculate latency
		latency := time.Since(start)
		status := c.Writer.Status()

		// Get request ID if available
		requestID := c.GetString("request_id")

		// Build log entry
		event := log.Info()
		if status >= 400 && status < 500 {
			event = log.Warn()
		} else if status >= 500 {
			event = log.Error()
		}

		event.
			Str("request_id", requestID).
			Str("method", c.Request.Method).
			Str("path", path).
			Str("query", query).
			Int("status", status).
			Dur("latency", latency).
			Str("client_ip", c.ClientIP()).
			Str("user_agent", c.Request.UserAgent()).
			Msg("Request")
	}
}
