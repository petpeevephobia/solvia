# Multi-stage build for Solvia V2 (Go API + React Frontend)

# ============================================
# Stage 1: Build React Frontend
# ============================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/web

# Copy package files
COPY web/package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY web/ ./

# Build for production
RUN npm run build

# ============================================
# Stage 2: Build Go API
# ============================================
FROM golang:1.23-alpine AS api-builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache git ca-certificates tzdata

# Copy go mod files
COPY api/go.mod api/go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY api/ ./

# Build the binary
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-w -s" -o /solvia-api ./cmd/api

# ============================================
# Stage 3: Final Runtime Image
# ============================================
FROM alpine:3.19

WORKDIR /app

# Install runtime dependencies
RUN apk add --no-cache ca-certificates tzdata curl

# Copy binary from builder
COPY --from=api-builder /solvia-api /app/solvia-api

# Copy React build from frontend builder
COPY --from=frontend-builder /app/web/dist /app/web/dist

# Create reports directory
RUN mkdir -p /app/reports

# Set timezone
ENV TZ=Asia/Singapore

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Run the application
CMD ["/app/solvia-api"]
