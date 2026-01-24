#!/usr/bin/env bash
set -euo pipefail

# Get the directory containing this script, then find project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Postgres connection for creating temp database
PG_HOST="${PG_HOST:-localhost}"
PG_USER="${PG_USER:-postgres}"
PG_PASSWORD="${PG_PASSWORD:-postgres}"

TEMP_DB="migration_$$"
TEMP_DIR=$(mktemp -d)

cleanup() {
    rm -rf "$TEMP_DIR"
    PGPASSWORD="$PG_PASSWORD" dropdb -h "$PG_HOST" -U "$PG_USER" --if-exists "$TEMP_DB" 2>/dev/null || true
}
trap cleanup EXIT

cd "$PROJECT_ROOT"

# Create temp database
PGPASSWORD="$PG_PASSWORD" createdb -h "$PG_HOST" -U "$PG_USER" "$TEMP_DB"

# Extract schema from origin/main (the "from" state)
FROM_DIR="$TEMP_DIR/from"
TO_DIR="$TEMP_DIR/to"
mkdir "$FROM_DIR" "$TO_DIR"

git show origin/main:ninjamagic/sqlc/schema.sql > "$FROM_DIR/schema.sql"
cp ./ninjamagic/sqlc/schema.sql "$TO_DIR/schema.sql"

# Generate migration diff
pg-schema-diff plan \
    --temp-db-dsn "postgres://$PG_USER:$PG_PASSWORD@$PG_HOST/$TEMP_DB" \
    --from-dir "$FROM_DIR" \
    --to-dir "$TO_DIR"
