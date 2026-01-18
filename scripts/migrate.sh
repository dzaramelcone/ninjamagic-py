#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATIONS_DIR="$SCRIPT_DIR/../migrations"

# Source env file if it exists
ENV_FILE="$SCRIPT_DIR/../ninjamagic.env"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

# Detect how to run psql: native or docker
if command -v psql &>/dev/null; then
  # Server: native psql with connection URL
  DB_URL="${pg:-}"
  DB_URL="${DB_URL/postgresql+psycopg/postgresql}"
  if [[ -z "$DB_URL" ]]; then
    echo "Error: No database URL (set 'pg' in ninjamagic.env)"
    exit 1
  fi
  run_sql() { psql "$DB_URL" -f "$1"; }
  run_cmd() { psql "$DB_URL" -tAc "$1"; }
elif docker ps --format '{{.Names}}' | grep -q '^db$'; then
  # Local: docker exec, pipe file content
  run_sql() { cat "$1" | docker exec -i db psql -U postgres; }
  run_cmd() { echo "$1" | docker exec -i db psql -U postgres -tA; }
else
  echo "Error: No psql available (install psql or start docker db)"
  exit 1
fi

# Always run bootstrap first (idempotent)
run_sql "$MIGRATIONS_DIR/000_bootstrap.sql" 2>/dev/null || true

# Run unapplied migrations in order
for f in "$MIGRATIONS_DIR"/*.sql; do
  name=$(basename "$f")
  [[ "$name" == "000_bootstrap.sql" ]] && continue

  applied=$(run_cmd "SELECT 1 FROM _migrations WHERE name='$name'" 2>/dev/null || echo "")
  if [[ -z "$applied" ]]; then
    echo "[migrate] applying $name"
    run_sql "$f"
    run_cmd "INSERT INTO _migrations(name) VALUES('$name')"
  else
    echo "[migrate] skip $name (already applied)"
  fi
done

echo "[migrate] done"
