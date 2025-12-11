package service

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/golang-jwt/jwt/v5"

	"github.com/petpeevephobia/solvia-v2/api/internal/infrastructure/google"
	"github.com/petpeevephobia/solvia-v2/api/internal/modules/auth/domain"
	"github.com/petpeevephobia/solvia-v2/api/internal/modules/auth/repository"
)

// AuthService handles authentication business logic
type AuthService struct {
	repo        repository.AuthRepository
	oauthClient *google.OAuthClient
	jwtSecret   []byte
}

// NewAuthService creates a new auth service
func NewAuthService(
	repo repository.AuthRepository,
	oauthClient *google.OAuthClient,
	jwtSecret string,
) *AuthService {
	return &AuthService{
		repo:        repo,
		oauthClient: oauthClient,
		jwtSecret:   []byte(jwtSecret),
	}
}

// GetAuthURL returns the Google OAuth URL
func (s *AuthService) GetAuthURL(state string) string {
	return s.oauthClient.GetAuthURL(state)
}

// HandleCallback handles the OAuth callback
func (s *AuthService) HandleCallback(ctx context.Context, code string) (*domain.AuthResult, error) {
	// Exchange code for tokens
	token, err := s.oauthClient.ExchangeCode(ctx, code)
	if err != nil {
		return nil, fmt.Errorf("failed to exchange code: %w", err)
	}

	// Get user info from Google
	userInfo, err := s.getUserInfo(ctx, token.AccessToken)
	if err != nil {
		return nil, fmt.Errorf("failed to get user info: %w", err)
	}

	// Save or update user
	user := &domain.User{
		Email:     userInfo.Email,
		Name:      userInfo.Name,
		Picture:   userInfo.Picture,
		LastLogin: time.Now(),
	}

	existingUser, _ := s.repo.GetUserByEmail(ctx, user.Email)
	if existingUser != nil {
		user.ID = existingUser.ID
		user.CreatedAt = existingUser.CreatedAt
		if err := s.repo.UpdateUser(ctx, user); err != nil {
			return nil, fmt.Errorf("failed to update user: %w", err)
		}
	} else {
		user.CreatedAt = time.Now()
		if err := s.repo.CreateUser(ctx, user); err != nil {
			return nil, fmt.Errorf("failed to create user: %w", err)
		}
	}

	// Save OAuth tokens
	if err := s.repo.SaveTokens(ctx, user.Email, token.AccessToken, token.RefreshToken, token.ExpiresAt); err != nil {
		return nil, fmt.Errorf("failed to save tokens: %w", err)
	}

	// Generate JWT
	jwtToken, expiresIn, err := s.generateJWT(user.Email)
	if err != nil {
		return nil, fmt.Errorf("failed to generate JWT: %w", err)
	}

	return &domain.AuthResult{
		User:        user,
		AccessToken: jwtToken,
		ExpiresIn:   expiresIn,
	}, nil
}

// GetUser retrieves a user by email
func (s *AuthService) GetUser(ctx context.Context, email string) (*domain.User, error) {
	return s.repo.GetUserByEmail(ctx, email)
}

// RefreshToken refreshes the access token
func (s *AuthService) RefreshToken(ctx context.Context, userEmail string) (*domain.AuthResult, error) {
	user, err := s.repo.GetUserByEmail(ctx, userEmail)
	if err != nil {
		return nil, fmt.Errorf("user not found: %w", err)
	}

	jwtToken, expiresIn, err := s.generateJWT(user.Email)
	if err != nil {
		return nil, fmt.Errorf("failed to generate JWT: %w", err)
	}

	return &domain.AuthResult{
		User:        user,
		AccessToken: jwtToken,
		ExpiresIn:   expiresIn,
	}, nil
}

// Logout logs out a user
func (s *AuthService) Logout(ctx context.Context, userEmail string) error {
	return s.repo.DeleteTokens(ctx, userEmail)
}

// GetUserTokens retrieves OAuth tokens for a user (implements UserTokenGetter)
func (s *AuthService) GetUserTokens(ctx context.Context, email string) (accessToken, refreshToken string, err error) {
	return s.repo.GetTokens(ctx, email)
}

// RefreshAndSaveTokens refreshes OAuth tokens and saves them (1:1 with Python verify_gsc_credentials)
// This is used by GSC service for automatic 401 retry
func (s *AuthService) RefreshAndSaveTokens(ctx context.Context, email, refreshToken string) (string, error) {
	if refreshToken == "" {
		return "", fmt.Errorf("no refresh token available")
	}

	// Refresh with Google
	newTokens, err := s.oauthClient.RefreshToken(ctx, refreshToken)
	if err != nil {
		return "", fmt.Errorf("failed to refresh token: %w", err)
	}

	// Save new tokens to database
	// Note: Refresh token might be rotated, so use the new one if provided
	newRefreshToken := refreshToken
	if newTokens.RefreshToken != "" {
		newRefreshToken = newTokens.RefreshToken
	}

	if err := s.repo.SaveTokens(ctx, email, newTokens.AccessToken, newRefreshToken, newTokens.ExpiresAt); err != nil {
		return "", fmt.Errorf("failed to save refreshed tokens: %w", err)
	}

	return newTokens.AccessToken, nil
}

// ValidateToken validates a JWT token
func (s *AuthService) ValidateToken(tokenString string) (string, error) {
	token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
		}
		return s.jwtSecret, nil
	})

	if err != nil {
		return "", err
	}

	if claims, ok := token.Claims.(jwt.MapClaims); ok && token.Valid {
		email, ok := claims["email"].(string)
		if !ok {
			return "", fmt.Errorf("invalid email claim")
		}
		return email, nil
	}

	return "", fmt.Errorf("invalid token")
}

// getUserInfo fetches user info from Google
func (s *AuthService) getUserInfo(ctx context.Context, accessToken string) (*domain.GoogleUserInfo, error) {
	req, err := http.NewRequestWithContext(ctx, "GET", "https://www.googleapis.com/oauth2/v2/userinfo", nil)
	if err != nil {
		return nil, err
	}

	req.Header.Set("Authorization", "Bearer "+accessToken)

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("failed to get user info: %s", string(body))
	}

	var userInfo domain.GoogleUserInfo
	if err := json.Unmarshal(body, &userInfo); err != nil {
		return nil, err
	}

	return &userInfo, nil
}

// generateJWT generates a JWT token (1:1 with Python - 30 minutes expiry)
func (s *AuthService) generateJWT(email string) (string, int64, error) {
	expiresIn := int64(30 * 60) // 30 minutes in seconds (1:1 with Python)
	expiresAt := time.Now().Add(30 * time.Minute)

	// 1:1 with Python auth/utils.py:40-44 - include both 'email' and 'sub' claims
	claims := jwt.MapClaims{
		"sub":   email, // 1:1 with Python - 'sub' claim for backwards compatibility
		"email": email, // 1:1 with Python - standard email claim
		"exp":   expiresAt.Unix(),
		"iat":   time.Now().Unix(),
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	tokenString, err := token.SignedString(s.jwtSecret)
	if err != nil {
		return "", 0, err
	}

	return tokenString, expiresIn, nil
}

// ============================================================
// Device Trust Operations (1:1 with Python implementation)
// ============================================================

// IsDeviceTrusted checks if a device is trusted for the user (1:1 with Python)
func (s *AuthService) IsDeviceTrusted(ctx context.Context, userEmail string, deviceRequest *domain.DeviceTrustRequest) bool {
	fingerprint := deviceRequest.GenerateFingerprint()

	// Check memory cache first (fast path)
	if trusted, found := domain.GlobalDeviceTrustCache.Get(userEmail, fingerprint); found {
		return trusted
	}

	// Check database for persistent trust
	device, err := s.repo.GetTrustedDevice(ctx, userEmail, fingerprint)
	if err != nil {
		return false
	}

	if device == nil {
		// Cache the negative result
		domain.GlobalDeviceTrustCache.Set(userEmail, fingerprint, false)
		return false
	}

	// Check if device trust has expired
	if device.IsDeviceExpired() {
		// Remove expired device
		_ = s.repo.DeleteTrustedDevice(ctx, device.ID)
		domain.GlobalDeviceTrustCache.Set(userEmail, fingerprint, false)
		return false
	}

	// Device is trusted and not expired - cache it
	domain.GlobalDeviceTrustCache.Set(userEmail, fingerprint, true)
	return true
}

// MarkDeviceTrusted marks a device as trusted for 30 days (1:1 with Python)
func (s *AuthService) MarkDeviceTrusted(ctx context.Context, userEmail string, deviceRequest *domain.DeviceTrustRequest) error {
	fingerprint := deviceRequest.GenerateFingerprint()

	// Create trusted device record
	device := &domain.TrustedDevice{
		UserEmail:         userEmail,
		DeviceFingerprint: fingerprint,
		UserAgent:         deviceRequest.UserAgent,
		CreatedAt:         time.Now(),
		ExpiresAt:         time.Now().Add(time.Duration(domain.DeviceTrustTimeout) * time.Second),
	}

	// Save to database
	if err := s.repo.SaveTrustedDevice(ctx, device); err != nil {
		return fmt.Errorf("failed to save trusted device: %w", err)
	}

	// Update memory cache
	domain.GlobalDeviceTrustCache.Set(userEmail, fingerprint, true)

	return nil
}

// GetAuthURLWithDeviceTrust returns the Google OAuth URL considering device trust (1:1 with Python)
func (s *AuthService) GetAuthURLWithDeviceTrust(ctx context.Context, state string, deviceRequest *domain.DeviceTrustRequest, userEmail string) string {
	// If we have a user email and device is trusted, use prompt='none' to skip consent
	rememberDevice := false
	if userEmail != "" {
		rememberDevice = s.IsDeviceTrusted(ctx, userEmail, deviceRequest)
	}

	return s.oauthClient.GetAuthURLWithPrompt(state, rememberDevice)
}

// CleanupExpiredDevices removes all expired trusted devices (maintenance task)
func (s *AuthService) CleanupExpiredDevices(ctx context.Context) error {
	// Clear expired entries from memory cache
	domain.GlobalDeviceTrustCache.Clear()

	// Clear from database
	return s.repo.DeleteExpiredDevices(ctx)
}
