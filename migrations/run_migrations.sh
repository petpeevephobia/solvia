#!/bin/bash

# Solvia v2 Database Migrations
# Usage: ./run_migrations.sh [database_url]

set -e

# Default database URL
DB_URL="${1:-postgresql://$(whoami)@localhost:5432/solvia_v2}"

echo "🚀 Running Solvia v2 Migrations..."
echo "Database: $DB_URL"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run migrations in order
for migration in "$SCRIPT_DIR"/00*.sql; do
    if [ -f "$migration" ]; then
        echo "📦 Running: $(basename "$migration")"
        psql "$DB_URL" -f "$migration"
        echo "   ✅ Done"
        echo ""
    fi
done

echo "✨ All migrations completed successfully!"
echo ""

# Show table counts
echo "📊 Database Summary:"
psql "$DB_URL" -c "SELECT schemaname, tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;"
