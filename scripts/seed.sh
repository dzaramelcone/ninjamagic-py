#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEEDS_DIR="$SCRIPT_DIR/../seeds"

# Source env file if it exists
ENV_FILE="$SCRIPT_DIR/../ninjamagic.env"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

# Detect how to run psql: native or docker
if command -v psql &>/dev/null; then
  DB_URL="${pg:-}"
  DB_URL="${DB_URL/postgresql+psycopg/postgresql}"
  if [[ -z "$DB_URL" ]]; then
    echo "Error: No database URL (set 'pg' in ninjamagic.env)"
    exit 1
  fi
  run_sql() { psql "$DB_URL" -f "$1"; }
elif docker ps --format '{{.Names}}' | grep -q '^db$'; then
  run_sql() { cat "$1" | docker exec -i db psql -U postgres; }
else
  echo "Error: No psql available (install psql or start docker db)"
  exit 1
fi

for f in "$SEEDS_DIR"/*.sql; do
  name=$(basename "$f")
  echo "[seed] applying $name"
  run_sql "$f"
done

echo "[seed] done"
