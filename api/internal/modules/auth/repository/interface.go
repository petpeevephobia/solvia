package repository

import (
	"context"
	"time"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/auth/domain"
)

// AuthRepository defines the interface for auth data operations
type AuthRepository interface {
	// User operations
	CreateUser(ctx context.Context, user *domain.User) error
	GetUserByEmail(ctx context.Context, email string) (*domain.User, error)
	UpdateUser(ctx context.Context, user *domain.User) error

	// Token operations
	SaveTokens(ctx context.Context, email, accessToken, refreshToken string, expiry time.Time) error
	GetTokens(ctx context.Context, email string) (accessToken, refreshToken string, err error)
	DeleteTokens(ctx context.Context, email string) error

	// Device trust operations (1:1 with Python)
	GetTrustedDevice(ctx context.Context, email, fingerprint string) (*domain.TrustedDevice, error)
	SaveTrustedDevice(ctx context.Context, device *domain.TrustedDevice) error
	DeleteTrustedDevice(ctx context.Context, id int64) error
	DeleteExpiredDevices(ctx context.Context) error
}
