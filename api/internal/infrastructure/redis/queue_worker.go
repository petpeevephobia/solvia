package redis

import (
	"context"
	"sync"
	"time"

	"github.com/rs/zerolog/log"
)

// AuditProcessor is the function type for processing audit jobs
type AuditProcessor func(ctx context.Context, job *AuditJob) error

// QueueWorker processes audit jobs from the Redis queue
type QueueWorker struct {
	client       *Client
	processor    AuditProcessor
	maxWorkers   int
	pollTimeout  time.Duration
	stopCh       chan struct{}
	wg           sync.WaitGroup
	running      bool
	mu           sync.Mutex
}

// QueueWorkerConfig holds queue worker configuration
type QueueWorkerConfig struct {
	MaxWorkers  int
	PollTimeout time.Duration
}

// NewQueueWorker creates a new queue worker
func NewQueueWorker(client *Client, processor AuditProcessor, cfg *QueueWorkerConfig) *QueueWorker {
	maxWorkers := 5
	pollTimeout := 30 * time.Second

	if cfg != nil {
		if cfg.MaxWorkers > 0 {
			maxWorkers = cfg.MaxWorkers
		}
		if cfg.PollTimeout > 0 {
			pollTimeout = cfg.PollTimeout
		}
	}

	return &QueueWorker{
		client:      client,
		processor:   processor,
		maxWorkers:  maxWorkers,
		pollTimeout: pollTimeout,
		stopCh:      make(chan struct{}),
	}
}

// Start begins processing jobs from the queue
func (w *QueueWorker) Start() {
	w.mu.Lock()
	if w.running {
		w.mu.Unlock()
		return
	}
	w.running = true
	w.mu.Unlock()

	if !w.client.IsEnabled() {
		log.Info().Msg("[AUDIT QUEUE] Redis disabled, queue worker not started")
		return
	}

	log.Info().Int("workers", w.maxWorkers).Msg("[AUDIT QUEUE] Starting queue workers")

	// Start worker goroutines
	for i := 0; i < w.maxWorkers; i++ {
		w.wg.Add(1)
		go w.worker(i)
	}
}

// Stop gracefully stops the queue worker
func (w *QueueWorker) Stop() {
	w.mu.Lock()
	if !w.running {
		w.mu.Unlock()
		return
	}
	w.running = false
	w.mu.Unlock()

	log.Info().Msg("[AUDIT QUEUE] Stopping queue workers...")
	close(w.stopCh)
	w.wg.Wait()
	log.Info().Msg("[AUDIT QUEUE] All workers stopped")
}

// worker processes jobs from the queue
func (w *QueueWorker) worker(id int) {
	defer w.wg.Done()

	log.Debug().Int("worker_id", id).Msg("[AUDIT QUEUE] Worker started")

	for {
		select {
		case <-w.stopCh:
			log.Debug().Int("worker_id", id).Msg("[AUDIT QUEUE] Worker stopping")
			return
		default:
			w.processNextJob(id)
		}
	}
}

// processNextJob attempts to get and process the next job
func (w *QueueWorker) processNextJob(workerID int) {
	ctx, cancel := context.WithTimeout(context.Background(), w.pollTimeout)
	defer cancel()

	// Blocking pop with timeout
	job, err := w.client.DequeueAudit(ctx, w.pollTimeout)
	if err != nil {
		// Timeout or empty queue is normal
		return
	}

	log.Info().
		Int("worker_id", workerID).
		Int64("audit_id", job.AuditID).
		Str("user", job.UserEmail).
		Str("website", job.WebsiteURL).
		Msg("[AUDIT QUEUE] Processing job")

	// Mark as processing
	_ = w.client.MarkAuditProcessing(ctx, job.AuditID)

	// Process the job with a longer timeout
	processCtx, processCancel := context.WithTimeout(context.Background(), 30*time.Minute)
	defer processCancel()

	startTime := time.Now()
	err = w.processor(processCtx, job)
	duration := time.Since(startTime)

	// Clear processing marker
	_ = w.client.ClearAuditProcessing(context.Background(), job.AuditID)

	if err != nil {
		log.Error().
			Err(err).
			Int("worker_id", workerID).
			Int64("audit_id", job.AuditID).
			Dur("duration", duration).
			Msg("[AUDIT QUEUE] Job failed")
	} else {
		log.Info().
			Int("worker_id", workerID).
			Int64("audit_id", job.AuditID).
			Dur("duration", duration).
			Msg("[AUDIT QUEUE] Job completed")
	}
}

// GetStats returns queue statistics
func (w *QueueWorker) GetStats(ctx context.Context) (*QueueStats, error) {
	queueLen, err := w.client.GetQueueLength(ctx)
	if err != nil {
		return nil, err
	}

	return &QueueStats{
		QueueLength: queueLen,
		MaxWorkers:  w.maxWorkers,
		Running:     w.running,
	}, nil
}

// QueueStats holds queue statistics
type QueueStats struct {
	QueueLength int64 `json:"queue_length"`
	MaxWorkers  int   `json:"max_workers"`
	Running     bool  `json:"running"`
}
