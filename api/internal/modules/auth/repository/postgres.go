package repository

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/auth/domain"
)

// ============================================================================
// CREDENTIAL CACHE (1:1 with Python _credentials_cache)
// ============================================================================

const (
	// CredentialCacheTimeout is the cache timeout for credentials (5 minutes, 1:1 with Python)
	CredentialCacheTimeout = 5 * time.Minute
)

// cachedCredentials stores cached token data with timestamp
type cachedCredentials struct {
	accessToken  string
	refreshToken string
	timestamp    time.Time
}

// credentialsCache provides thread-safe credential caching (1:1 with Python _credentials_cache)
type credentialsCache struct {
	mu    sync.RWMutex
	cache map[string]*cachedCredentials
}

// newCredentialsCache creates a new credentials cache
func newCredentialsCache() *credentialsCache {
	return &credentialsCache{
		cache: make(map[string]*cachedCredentials),
	}
}

// get retrieves credentials from cache if not expired
func (c *credentialsCache) get(email string) (accessToken, refreshToken string, found bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	key := fmt.Sprintf("creds_%s", email)
	cached, ok := c.cache[key]
	if !ok {
		return "", "", false
	}

	// Check if cache has expired
	if time.Since(cached.timestamp) > CredentialCacheTimeout {
		// Cache expired - will be cleaned up on next set or explicit clear
		return "", "", false
	}

	return cached.accessToken, cached.refreshToken, true
}

// set stores credentials in cache
func (c *credentialsCache) set(email, accessToken, refreshToken string) {
	c.mu.Lock()
	defer c.mu.Unlock()

	key := fmt.Sprintf("creds_%s", email)
	c.cache[key] = &cachedCredentials{
		accessToken:  accessToken,
		refreshToken: refreshToken,
		timestamp:    time.Now(),
	}
}

// clear removes credentials from cache for a specific user
func (c *credentialsCache) clear(email string) {
	c.mu.Lock()
	defer c.mu.Unlock()

	key := fmt.Sprintf("creds_%s", email)
	delete(c.cache, key)
}

// clearAll clears all cached credentials
func (c *credentialsCache) clearAll() {
	c.mu.Lock()
	defer c.mu.Unlock()

	c.cache = make(map[string]*cachedCredentials)
}

// Global credentials cache instance (1:1 with Python)
var globalCredentialsCache = newCredentialsCache()

// PostgresAuthRepository implements AuthRepository with PostgreSQL
type PostgresAuthRepository struct {
	pool *pgxpool.Pool
}

// NewPostgresAuthRepository creates a new PostgreSQL auth repository
func NewPostgresAuthRepository(pool *pgxpool.Pool) *PostgresAuthRepository {
	return &PostgresAuthRepository{pool: pool}
}

// CreateUser creates a new user
func (r *PostgresAuthRepository) CreateUser(ctx context.Context, user *domain.User) error {
	query := `
		INSERT INTO users (email, name, picture, created_at, last_login)
		VALUES ($1, $2, $3, $4, $5)
		RETURNING id
	`

	return r.pool.QueryRow(ctx, query,
		user.Email,
		user.Name,
		user.Picture,
		user.CreatedAt,
		user.LastLogin,
	).Scan(&user.ID)
}

// GetUserByEmail retrieves a user by email
func (r *PostgresAuthRepository) GetUserByEmail(ctx context.Context, email string) (*domain.User, error) {
	query := `
		SELECT id, email, name, picture, created_at, last_login
		FROM users
		WHERE email = $1
	`

	var user domain.User
	err := r.pool.QueryRow(ctx, query, email).Scan(
		&user.ID,
		&user.Email,
		&user.Name,
		&user.Picture,
		&user.CreatedAt,
		&user.LastLogin,
	)

	if errors.Is(err, pgx.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}

	return &user, nil
}

// UpdateUser updates a user
func (r *PostgresAuthRepository) UpdateUser(ctx context.Context, user *domain.User) error {
	query := `
		UPDATE users
		SET name = $2, picture = $3, last_login = $4
		WHERE email = $1
	`

	_, err := r.pool.Exec(ctx, query,
		user.Email,
		user.Name,
		user.Picture,
		user.LastLogin,
	)
	return err
}

// SaveTokens saves OAuth tokens (1:1 with Python - clears cache after save)
func (r *PostgresAuthRepository) SaveTokens(ctx context.Context, email, accessToken, refreshToken string, expiry time.Time) error {
	query := `
		INSERT INTO oauth_tokens (user_email, access_token, refresh_token, expiry, updated_at)
		VALUES ($1, $2, $3, $4, NOW())
		ON CONFLICT (user_email)
		DO UPDATE SET access_token = $2, refresh_token = $3, expiry = $4, updated_at = NOW()
	`

	_, err := r.pool.Exec(ctx, query, email, accessToken, refreshToken, expiry)
	if err != nil {
		return err
	}

	// Clear cache after save so fresh credentials are fetched from DB (1:1 with Python)
	globalCredentialsCache.clear(email)

	return nil
}

// GetTokens retrieves OAuth tokens (1:1 with Python get_credentials with caching)
func (r *PostgresAuthRepository) GetTokens(ctx context.Context, email string) (accessToken, refreshToken string, err error) {
	// Check cache first (1:1 with Python)
	if cachedAccess, cachedRefresh, found := globalCredentialsCache.get(email); found {
		// Cache hit
		return cachedAccess, cachedRefresh, nil
	}

	// Cache miss - query database
	query := `
		SELECT access_token, refresh_token
		FROM oauth_tokens
		WHERE user_email = $1
	`

	err = r.pool.QueryRow(ctx, query, email).Scan(&accessToken, &refreshToken)
	if errors.Is(err, pgx.ErrNoRows) {
		return "", "", fmt.Errorf("tokens not found")
	}
	if err != nil {
		return "", "", err
	}

	// Store in cache for future requests (1:1 with Python)
	globalCredentialsCache.set(email, accessToken, refreshToken)

	return accessToken, refreshToken, nil
}

// DeleteTokens deletes OAuth tokens (1:1 with Python - clears cache)
func (r *PostgresAuthRepository) DeleteTokens(ctx context.Context, email string) error {
	query := `DELETE FROM oauth_tokens WHERE user_email = $1`
	_, err := r.pool.Exec(ctx, query, email)
	if err != nil {
		return err
	}

	// Clear cache after delete (1:1 with Python)
	globalCredentialsCache.clear(email)

	return nil
}

// ClearCredentialsCache clears the credentials cache for a user (1:1 with Python clear_credentials_cache)
func (r *PostgresAuthRepository) ClearCredentialsCache(email string) {
	globalCredentialsCache.clear(email)
}

// ============================================================
// Device Trust Operations (1:1 with Python implementation)
// ============================================================

// GetTrustedDevice retrieves a trusted device record by email and fingerprint
func (r *PostgresAuthRepository) GetTrustedDevice(ctx context.Context, email, fingerprint string) (*domain.TrustedDevice, error) {
	query := `
		SELECT id, user_email, device_fingerprint, user_agent, created_at, expires_at
		FROM trusted_devices
		WHERE user_email = $1 AND device_fingerprint = $2
	`

	var device domain.TrustedDevice
	err := r.pool.QueryRow(ctx, query, email, fingerprint).Scan(
		&device.ID,
		&device.UserEmail,
		&device.DeviceFingerprint,
		&device.UserAgent,
		&device.CreatedAt,
		&device.ExpiresAt,
	)

	if errors.Is(err, pgx.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("failed to get trusted device: %w", err)
	}

	return &device, nil
}

// SaveTrustedDevice saves or updates a trusted device record (upsert on user_email, device_fingerprint)
func (r *PostgresAuthRepository) SaveTrustedDevice(ctx context.Context, device *domain.TrustedDevice) error {
	query := `
		INSERT INTO trusted_devices (user_email, device_fingerprint, user_agent, created_at, expires_at)
		VALUES ($1, $2, $3, $4, $5)
		ON CONFLICT (user_email, device_fingerprint)
		DO UPDATE SET user_agent = $3, created_at = $4, expires_at = $5
		RETURNING id
	`

	return r.pool.QueryRow(ctx, query,
		device.UserEmail,
		device.DeviceFingerprint,
		device.UserAgent,
		device.CreatedAt,
		device.ExpiresAt,
	).Scan(&device.ID)
}

// DeleteTrustedDevice deletes a trusted device by ID
func (r *PostgresAuthRepository) DeleteTrustedDevice(ctx context.Context, id int64) error {
	query := `DELETE FROM trusted_devices WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id)
	return err
}

// DeleteExpiredDevices removes all expired trusted device records
func (r *PostgresAuthRepository) DeleteExpiredDevices(ctx context.Context) error {
	query := `DELETE FROM trusted_devices WHERE expires_at < NOW()`
	_, err := r.pool.Exec(ctx, query)
	return err
}
