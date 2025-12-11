package domain

import (
	"sync"
	"time"
)

// AuditStage represents a stage in the audit process (1:1 with Python)
// 8 stages: initializing, fetching_gsc_data, analyzing_metrics, detecting_issues,
// generating_recommendations, creating_report, finalizing, completed/error
type AuditStage string

const (
	StageInitializing               AuditStage = "initializing"
	StageFetchingGSCData            AuditStage = "fetching_gsc_data"
	StageAnalyzingMetrics           AuditStage = "analyzing_metrics"
	StageDetectingIssues            AuditStage = "detecting_issues"
	StageGeneratingRecommendations  AuditStage = "generating_recommendations"
	StageCreatingReport             AuditStage = "creating_report"
	StageFinalizing                 AuditStage = "finalizing"
	StageCompleted                  AuditStage = "completed"
	StageError                      AuditStage = "error"
)

// StageInfo contains metadata for each stage
type StageInfo struct {
	Stage       AuditStage `json:"stage"`
	Name        string     `json:"name"`
	Description string     `json:"description"`
	MinProgress int        `json:"min_progress"` // 0-100
	MaxProgress int        `json:"max_progress"` // 0-100
}

// AuditStages defines all stages with their progress ranges (1:1 with Python)
var AuditStages = map[AuditStage]StageInfo{
	StageInitializing: {
		Stage:       StageInitializing,
		Name:        "Initializing",
		Description: "Setting up audit environment",
		MinProgress: 0,
		MaxProgress: 10,
	},
	StageFetchingGSCData: {
		Stage:       StageFetchingGSCData,
		Name:        "Fetching GSC Data",
		Description: "Retrieving data from Google Search Console",
		MinProgress: 10,
		MaxProgress: 30,
	},
	StageAnalyzingMetrics: {
		Stage:       StageAnalyzingMetrics,
		Name:        "Analyzing Metrics",
		Description: "Processing and analyzing SEO metrics",
		MinProgress: 30,
		MaxProgress: 50,
	},
	StageDetectingIssues: {
		Stage:       StageDetectingIssues,
		Name:        "Detecting Issues",
		Description: "Identifying SEO issues and anomalies",
		MinProgress: 50,
		MaxProgress: 70,
	},
	StageGeneratingRecommendations: {
		Stage:       StageGeneratingRecommendations,
		Name:        "Generating Recommendations",
		Description: "Creating actionable recommendations",
		MinProgress: 70,
		MaxProgress: 85,
	},
	StageCreatingReport: {
		Stage:       StageCreatingReport,
		Name:        "Creating Report",
		Description: "Generating PDF audit report",
		MinProgress: 85,
		MaxProgress: 95,
	},
	StageFinalizing: {
		Stage:       StageFinalizing,
		Name:        "Finalizing",
		Description: "Saving results and cleaning up",
		MinProgress: 95,
		MaxProgress: 100,
	},
	StageCompleted: {
		Stage:       StageCompleted,
		Name:        "Completed",
		Description: "Audit completed successfully",
		MinProgress: 100,
		MaxProgress: 100,
	},
	StageError: {
		Stage:       StageError,
		Name:        "Error",
		Description: "Audit failed with error",
		MinProgress: 0,
		MaxProgress: 100,
	},
}

// AuditProgress represents the current progress of an audit
type AuditProgress struct {
	AuditID     int64      `json:"audit_id"`
	Stage       AuditStage `json:"stage"`
	Progress    int        `json:"progress"`       // 0-100
	Message     string     `json:"message"`
	SubMessage  string     `json:"sub_message,omitempty"`
	Error       string     `json:"error,omitempty"`
	StartedAt   time.Time  `json:"started_at"`
	UpdatedAt   time.Time  `json:"updated_at"`
	ElapsedMs   int64      `json:"elapsed_ms"`
}

// AuditProgressTracker tracks progress for multiple audits
type AuditProgressTracker struct {
	mu          sync.RWMutex
	progress    map[int64]*AuditProgress
	listeners   map[int64]map[int64]chan AuditProgress // auditID -> subscriptionID -> channel
	nextSubID   int64
}

// NewAuditProgressTracker creates a new progress tracker
func NewAuditProgressTracker() *AuditProgressTracker {
	return &AuditProgressTracker{
		progress:  make(map[int64]*AuditProgress),
		listeners: make(map[int64]map[int64]chan AuditProgress),
		nextSubID: 1,
	}
}

// StartTracking begins tracking progress for an audit
func (t *AuditProgressTracker) StartTracking(auditID int64) {
	t.mu.Lock()
	defer t.mu.Unlock()

	t.progress[auditID] = &AuditProgress{
		AuditID:   auditID,
		Stage:     StageInitializing,
		Progress:  0,
		Message:   "Starting audit...",
		StartedAt: time.Now(),
		UpdatedAt: time.Now(),
	}

	t.notifyListeners(auditID)
}

// UpdateProgress updates the progress for an audit
func (t *AuditProgressTracker) UpdateProgress(auditID int64, stage AuditStage, progress int, message string) {
	t.mu.Lock()
	defer t.mu.Unlock()

	p, exists := t.progress[auditID]
	if !exists {
		p = &AuditProgress{
			AuditID:   auditID,
			StartedAt: time.Now(),
		}
		t.progress[auditID] = p
	}

	p.Stage = stage
	p.Progress = progress
	p.Message = message
	p.UpdatedAt = time.Now()
	p.ElapsedMs = time.Since(p.StartedAt).Milliseconds()

	// Set sub-message based on stage
	if info, ok := AuditStages[stage]; ok {
		p.SubMessage = info.Description
	}

	t.notifyListeners(auditID)
}

// SetStage sets the stage and auto-calculates progress
func (t *AuditProgressTracker) SetStage(auditID int64, stage AuditStage, message string) {
	info, ok := AuditStages[stage]
	if !ok {
		info = StageInfo{MinProgress: 0, MaxProgress: 100}
	}

	// Use the minimum progress for the stage
	t.UpdateProgress(auditID, stage, info.MinProgress, message)
}

// SetError sets an error state for the audit
func (t *AuditProgressTracker) SetError(auditID int64, err string) {
	t.mu.Lock()
	defer t.mu.Unlock()

	p, exists := t.progress[auditID]
	if !exists {
		p = &AuditProgress{
			AuditID:   auditID,
			StartedAt: time.Now(),
		}
		t.progress[auditID] = p
	}

	p.Stage = StageError
	p.Error = err
	p.Message = "Audit failed"
	p.UpdatedAt = time.Now()
	p.ElapsedMs = time.Since(p.StartedAt).Milliseconds()

	t.notifyListeners(auditID)
}

// Complete marks the audit as completed
func (t *AuditProgressTracker) Complete(auditID int64) {
	t.UpdateProgress(auditID, StageCompleted, 100, "Audit completed successfully")
}

// GetProgress returns the current progress for an audit
func (t *AuditProgressTracker) GetProgress(auditID int64) *AuditProgress {
	t.mu.RLock()
	defer t.mu.RUnlock()

	if p, exists := t.progress[auditID]; exists {
		return p
	}
	return nil
}

// Subscription represents a subscription to audit progress updates
type Subscription struct {
	Ch      <-chan AuditProgress
	SubID   int64
	AuditID int64
}

// Subscribe creates a channel to receive progress updates
func (t *AuditProgressTracker) Subscribe(auditID int64) *Subscription {
	t.mu.Lock()
	defer t.mu.Unlock()

	ch := make(chan AuditProgress, 10)
	subID := t.nextSubID
	t.nextSubID++

	// Initialize listener map for this audit if needed
	if t.listeners[auditID] == nil {
		t.listeners[auditID] = make(map[int64]chan AuditProgress)
	}
	t.listeners[auditID][subID] = ch

	// Send current progress immediately if available
	if p, exists := t.progress[auditID]; exists {
		select {
		case ch <- *p:
		default:
		}
	}

	return &Subscription{
		Ch:      ch,
		SubID:   subID,
		AuditID: auditID,
	}
}

// Unsubscribe removes a listener channel
func (t *AuditProgressTracker) Unsubscribe(sub *Subscription) {
	if sub == nil {
		return
	}

	t.mu.Lock()
	defer t.mu.Unlock()

	if listeners, exists := t.listeners[sub.AuditID]; exists {
		if ch, ok := listeners[sub.SubID]; ok {
			close(ch)
			delete(listeners, sub.SubID)
		}
	}
}

// CleanupAudit removes progress tracking for an audit
func (t *AuditProgressTracker) CleanupAudit(auditID int64) {
	t.mu.Lock()
	defer t.mu.Unlock()

	// Close all listener channels
	for _, ch := range t.listeners[auditID] {
		close(ch)
	}

	delete(t.progress, auditID)
	delete(t.listeners, auditID)
}

// notifyListeners sends progress update to all listeners
func (t *AuditProgressTracker) notifyListeners(auditID int64) {
	p := t.progress[auditID]
	if p == nil {
		return
	}

	for _, ch := range t.listeners[auditID] {
		select {
		case ch <- *p:
		default:
			// Channel full, skip
		}
	}
}

// GlobalProgressTracker is the singleton progress tracker
var GlobalProgressTracker = NewAuditProgressTracker()
