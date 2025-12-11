package database

import (
	"context"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/rs/zerolog/log"
)

// PostgresDB wraps pgxpool for database operations
type PostgresDB struct {
	Pool *pgxpool.Pool
}

// NewPostgresDB creates a new PostgreSQL connection pool
func NewPostgresDB(databaseURL string) (*PostgresDB, error) {
	config, err := pgxpool.ParseConfig(databaseURL)
	if err != nil {
		return nil, err
	}

	// Connection pool settings
	config.MaxConns = 25
	config.MinConns = 5
	config.MaxConnLifetime = time.Hour
	config.MaxConnIdleTime = 30 * time.Minute
	config.HealthCheckPeriod = time.Minute

	// Create connection pool
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	pool, err := pgxpool.NewWithConfig(ctx, config)
	if err != nil {
		return nil, err
	}

	// Test connection
	if err := pool.Ping(ctx); err != nil {
		return nil, err
	}

	log.Info().
		Int32("max_conns", config.MaxConns).
		Int32("min_conns", config.MinConns).
		Msg("PostgreSQL connection pool initialized")

	return &PostgresDB{Pool: pool}, nil
}

// Close closes the database connection pool
func (db *PostgresDB) Close() {
	db.Pool.Close()
	log.Info().Msg("Database connection pool closed")
}

// Health checks if the database is healthy
func (db *PostgresDB) Health(ctx context.Context) error {
	return db.Pool.Ping(ctx)
}
