package domain

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"sync"
	"time"
)

// DeviceTrustTimeout is 30 days in seconds (1:1 with Python)
const DeviceTrustTimeout = 30 * 24 * 60 * 60 // 2592000 seconds

// TrustedDevice represents a trusted device record
type TrustedDevice struct {
	ID                int64     `json:"id"`
	UserEmail         string    `json:"user_email"`
	DeviceFingerprint string    `json:"device_fingerprint"`
	UserAgent         string    `json:"user_agent"`
	CreatedAt         time.Time `json:"created_at"`
	ExpiresAt         time.Time `json:"expires_at"`
}

// DeviceTrustCache provides in-memory caching for device trust lookups
type DeviceTrustCache struct {
	mu      sync.RWMutex
	cache   map[string]*deviceTrustEntry
	timeout time.Duration
}

type deviceTrustEntry struct {
	Timestamp time.Time
	Trusted   bool
}

// NewDeviceTrustCache creates a new device trust cache
func NewDeviceTrustCache() *DeviceTrustCache {
	return &DeviceTrustCache{
		cache:   make(map[string]*deviceTrustEntry),
		timeout: time.Duration(DeviceTrustTimeout) * time.Second,
	}
}

// Get retrieves a cached trust entry
func (c *DeviceTrustCache) Get(userEmail, deviceFingerprint string) (trusted bool, found bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	key := c.cacheKey(userEmail, deviceFingerprint)
	entry, exists := c.cache[key]
	if !exists {
		return false, false
	}

	// Check if entry has expired
	if time.Since(entry.Timestamp) > c.timeout {
		return false, false
	}

	return entry.Trusted, true
}

// Set stores a trust entry in cache
func (c *DeviceTrustCache) Set(userEmail, deviceFingerprint string, trusted bool) {
	c.mu.Lock()
	defer c.mu.Unlock()

	key := c.cacheKey(userEmail, deviceFingerprint)
	c.cache[key] = &deviceTrustEntry{
		Timestamp: time.Now(),
		Trusted:   trusted,
	}
}

// Delete removes an entry from cache
func (c *DeviceTrustCache) Delete(userEmail, deviceFingerprint string) {
	c.mu.Lock()
	defer c.mu.Unlock()

	key := c.cacheKey(userEmail, deviceFingerprint)
	delete(c.cache, key)
}

// Clear removes all expired entries
func (c *DeviceTrustCache) Clear() {
	c.mu.Lock()
	defer c.mu.Unlock()

	now := time.Now()
	for key, entry := range c.cache {
		if now.Sub(entry.Timestamp) > c.timeout {
			delete(c.cache, key)
		}
	}
}

func (c *DeviceTrustCache) cacheKey(userEmail, deviceFingerprint string) string {
	return fmt.Sprintf("trust_%s_%s", userEmail, deviceFingerprint)
}

// GenerateDeviceFingerprint generates a unique device fingerprint (1:1 with Python)
// Uses SHA-256 hash of browser characteristics
func GenerateDeviceFingerprint(userAgent, acceptLanguage, acceptEncoding, ipAddress string) string {
	if ipAddress == "" {
		ipAddress = "unknown"
	}

	// Create fingerprint from stable browser characteristics (1:1 with Python)
	fingerprintData := fmt.Sprintf("%s|%s|%s|%s", userAgent, acceptLanguage, acceptEncoding, ipAddress)

	// Generate SHA-256 hash and take first 32 chars
	hash := sha256.Sum256([]byte(fingerprintData))
	return hex.EncodeToString(hash[:])[:32]
}

// DeviceTrustRequest contains headers for fingerprint generation
type DeviceTrustRequest struct {
	UserAgent      string
	AcceptLanguage string
	AcceptEncoding string
	IPAddress      string
}

// GenerateFingerprint creates a fingerprint from the request
func (r *DeviceTrustRequest) GenerateFingerprint() string {
	return GenerateDeviceFingerprint(
		r.UserAgent,
		r.AcceptLanguage,
		r.AcceptEncoding,
		r.IPAddress,
	)
}

// IsDeviceExpired checks if a trusted device has expired
func (d *TrustedDevice) IsDeviceExpired() bool {
	if d == nil {
		return true
	}
	return time.Now().After(d.ExpiresAt)
}

// GlobalDeviceTrustCache is the singleton cache instance
var GlobalDeviceTrustCache = NewDeviceTrustCache()
