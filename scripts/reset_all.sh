#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Stopping all services and removing volumes..."
docker compose down -v --remove-orphans
echo ""
echo "Pruning built images..."
docker compose down --rmi local 2>/dev/null || true
echo ""
echo "Reset complete. Run 'bash scripts/run_all.sh' to start fresh."
