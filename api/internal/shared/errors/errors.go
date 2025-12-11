package errors

import (
	"errors"
	"fmt"
	"net/http"
)

// Common error codes
const (
	CodeUnauthorized    = "UNAUTHORIZED"
	CodeForbidden       = "FORBIDDEN"
	CodeNotFound        = "NOT_FOUND"
	CodeBadRequest      = "BAD_REQUEST"
	CodeValidation      = "VALIDATION_ERROR"
	CodeInternal        = "INTERNAL_ERROR"
	CodeDatabase        = "DATABASE_ERROR"
	CodeExternalService = "EXTERNAL_SERVICE_ERROR"
	CodeRateLimited     = "RATE_LIMITED"
	CodeConflict        = "CONFLICT"
)

// AppError represents an application error
type AppError struct {
	Code       string
	Message    string
	StatusCode int
	Err        error
}

func (e *AppError) Error() string {
	if e.Err != nil {
		return fmt.Sprintf("%s: %v", e.Message, e.Err)
	}
	return e.Message
}

func (e *AppError) Unwrap() error {
	return e.Err
}

// New creates a new AppError
func New(code, message string, statusCode int) *AppError {
	return &AppError{
		Code:       code,
		Message:    message,
		StatusCode: statusCode,
	}
}

// Wrap wraps an existing error
func Wrap(err error, code, message string, statusCode int) *AppError {
	return &AppError{
		Code:       code,
		Message:    message,
		StatusCode: statusCode,
		Err:        err,
	}
}

// Common errors
var (
	ErrUnauthorized = New(CodeUnauthorized, "Authentication required", http.StatusUnauthorized)
	ErrForbidden    = New(CodeForbidden, "Access denied", http.StatusForbidden)
	ErrNotFound     = New(CodeNotFound, "Resource not found", http.StatusNotFound)
	ErrBadRequest   = New(CodeBadRequest, "Invalid request", http.StatusBadRequest)
	ErrInternal     = New(CodeInternal, "Internal server error", http.StatusInternalServerError)
	ErrRateLimited  = New(CodeRateLimited, "Too many requests", http.StatusTooManyRequests)
)

// Validation error helpers
func ValidationError(message string) *AppError {
	return New(CodeValidation, message, http.StatusBadRequest)
}

func NotFoundError(resource string, id ...string) *AppError {
	if len(id) > 0 {
		return New(CodeNotFound, fmt.Sprintf("%s %s not found", resource, id[0]), http.StatusNotFound)
	}
	return New(CodeNotFound, fmt.Sprintf("%s not found", resource), http.StatusNotFound)
}

func ForbiddenError(message string) *AppError {
	return New(CodeForbidden, message, http.StatusForbidden)
}

func DatabaseError(err error) *AppError {
	return Wrap(err, CodeDatabase, "Database operation failed", http.StatusInternalServerError)
}

func ExternalServiceError(service string, err error) *AppError {
	return Wrap(err, CodeExternalService, fmt.Sprintf("%s service error", service), http.StatusBadGateway)
}

// IsAppError checks if an error is an AppError
func IsAppError(err error) bool {
	var appErr *AppError
	return errors.As(err, &appErr)
}

// GetAppError extracts AppError from error chain
func GetAppError(err error) *AppError {
	var appErr *AppError
	if errors.As(err, &appErr) {
		return appErr
	}
	return nil
}
