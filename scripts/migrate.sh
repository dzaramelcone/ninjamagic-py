#!/usr/bin/env bash
set -euo pipefail

# Source env file if it exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../ninjamagic.env"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

# Convert SQLAlchemy URL to psql format (strip +psycopg)
DB_URL="${pg:-}"
DB_URL="${DB_URL/postgresql+psycopg/postgresql}"

if [[ -z "$DB_URL" ]]; then
  echo "Error: No database URL (set 'pg' in ninjamagic.env)"
  exit 1
fi

MIGRATIONS_DIR="$SCRIPT_DIR/../migrations"

# Always run bootstrap first (idempotent)
psql "$DB_URL" -f "$MIGRATIONS_DIR/000_bootstrap.sql" 2>/dev/null || true

# Run unapplied migrations in order
for f in "$MIGRATIONS_DIR"/*.sql; do
  name=$(basename "$f")
  [[ "$name" == "000_bootstrap.sql" ]] && continue

  applied=$(psql "$DB_URL" -tAc "SELECT 1 FROM _migrations WHERE name='$name'" 2>/dev/null || echo "")
  if [[ -z "$applied" ]]; then
    echo "[migrate] applying $name"
    psql "$DB_URL" -f "$f"
    psql "$DB_URL" -c "INSERT INTO _migrations(name) VALUES('$name')"
  else
    echo "[migrate] skip $name (already applied)"
  fi
done

echo "[migrate] done"
