package google

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"golang.org/x/oauth2"
	"golang.org/x/oauth2/google"
)

// OAuthClient handles Google OAuth operations
type OAuthClient struct {
	config *oauth2.Config
}

// UserInfo represents Google user profile
type UserInfo struct {
	ID            string `json:"id"`
	Email         string `json:"email"`
	VerifiedEmail bool   `json:"verified_email"`
	Name          string `json:"name"`
	GivenName     string `json:"given_name"`
	FamilyName    string `json:"family_name"`
	Picture       string `json:"picture"`
}

// TokenResponse contains OAuth tokens
type TokenResponse struct {
	AccessToken  string
	RefreshToken string
	TokenType    string
	ExpiresAt    time.Time
}

// NewOAuthClient creates a new Google OAuth client
func NewOAuthClient(clientID, clientSecret, redirectURI string) *OAuthClient {
	return &OAuthClient{
		config: &oauth2.Config{
			ClientID:     clientID,
			ClientSecret: clientSecret,
			RedirectURL:  redirectURI,
			Scopes: []string{
				"openid",
				"email",
				"profile",
				"https://www.googleapis.com/auth/webmasters", // GSC read-write access (1:1 with Python)
			},
			Endpoint: google.Endpoint,
		},
	}
}

// GetAuthURL generates the Google OAuth authorization URL
func (c *OAuthClient) GetAuthURL(state string) string {
	return c.config.AuthCodeURL(state,
		oauth2.AccessTypeOffline,   // Request refresh token
		oauth2.ApprovalForce,       // Force consent screen for refresh token
		oauth2.SetAuthURLParam("prompt", "consent"),
	)
}

// GetAuthURLWithPrompt generates OAuth URL with device trust support (1:1 with Python)
// For returning users with trusted devices: prompt='none' (skip consent)
// For new devices or forced re-auth: prompt='consent' to ensure refresh tokens
func (c *OAuthClient) GetAuthURLWithPrompt(state string, rememberDevice bool) string {
	promptValue := "consent"
	if rememberDevice {
		promptValue = "none"
	}

	return c.config.AuthCodeURL(state,
		oauth2.AccessTypeOffline,
		oauth2.SetAuthURLParam("prompt", promptValue),
		oauth2.SetAuthURLParam("include_granted_scopes", "true"), // Enable incremental authorization
	)
}

// ExchangeCode exchanges authorization code for tokens
func (c *OAuthClient) ExchangeCode(ctx context.Context, code string) (*TokenResponse, error) {
	token, err := c.config.Exchange(ctx, code)
	if err != nil {
		return nil, fmt.Errorf("failed to exchange code: %w", err)
	}

	return &TokenResponse{
		AccessToken:  token.AccessToken,
		RefreshToken: token.RefreshToken,
		TokenType:    token.TokenType,
		ExpiresAt:    token.Expiry,
	}, nil
}

// RefreshToken refreshes an expired access token
func (c *OAuthClient) RefreshToken(ctx context.Context, refreshToken string) (*TokenResponse, error) {
	token := &oauth2.Token{
		RefreshToken: refreshToken,
	}

	tokenSource := c.config.TokenSource(ctx, token)
	newToken, err := tokenSource.Token()
	if err != nil {
		return nil, fmt.Errorf("failed to refresh token: %w", err)
	}

	return &TokenResponse{
		AccessToken:  newToken.AccessToken,
		RefreshToken: newToken.RefreshToken,
		TokenType:    newToken.TokenType,
		ExpiresAt:    newToken.Expiry,
	}, nil
}

// GetUserInfo fetches user profile from Google
func (c *OAuthClient) GetUserInfo(ctx context.Context, accessToken string) (*UserInfo, error) {
	client := c.config.Client(ctx, &oauth2.Token{AccessToken: accessToken})

	resp, err := client.Get("https://www.googleapis.com/oauth2/v2/userinfo")
	if err != nil {
		return nil, fmt.Errorf("failed to get user info: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("user info request failed with status: %d", resp.StatusCode)
	}

	var userInfo UserInfo
	if err := json.NewDecoder(resp.Body).Decode(&userInfo); err != nil {
		return nil, fmt.Errorf("failed to decode user info: %w", err)
	}

	return &userInfo, nil
}

// GetHTTPClient returns an authenticated HTTP client for API calls
func (c *OAuthClient) GetHTTPClient(ctx context.Context, accessToken, refreshToken string) *http.Client {
	token := &oauth2.Token{
		AccessToken:  accessToken,
		RefreshToken: refreshToken,
		TokenType:    "Bearer",
	}

	return c.config.Client(ctx, token)
}
