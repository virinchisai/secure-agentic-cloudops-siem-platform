#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Secure Agentic CloudOps SIEM Platform ==="
echo ""

echo "[1/4] Starting Docker infrastructure..."
docker compose up -d --build
echo "  Infrastructure started."

echo ""
echo "[2/4] Waiting for services to become healthy..."
for svc in postgres redpanda ingest-service detection-service; do
  printf "  Waiting for %-20s" "$svc..."
  attempts=0
  until docker compose ps "$svc" 2>/dev/null | grep -q "healthy"; do
    sleep 2
    attempts=$((attempts + 1))
    if [ "$attempts" -ge 30 ]; then
      echo " TIMEOUT"
      echo "ERROR: $svc did not become healthy within 60 seconds."
      docker compose logs "$svc" --tail 20
      exit 1
    fi
  done
  echo " ready"
done

echo ""
echo "[3/4] Seeding sample events..."
python scripts/seed_sample_events.py

echo ""
echo "[4/4] Verification"
echo "  Ingest service : $(curl -s http://127.0.0.1:8001/health)"
echo "  Detection svc  : $(curl -s http://127.0.0.1:8002/health)"
echo ""

ALERT_COUNT=$(docker exec "$(docker compose ps -q postgres)" \
  psql -U app -d cloudops -t -c "SELECT COUNT(*) FROM alerts;" 2>/dev/null | tr -d ' ' || echo "?")
EVENT_COUNT=$(docker exec "$(docker compose ps -q postgres)" \
  psql -U app -d cloudops -t -c "SELECT COUNT(*) FROM events;" 2>/dev/null | tr -d ' ' || echo "?")

echo "  Events in DB   : $EVENT_COUNT"
echo "  Alerts in DB   : $ALERT_COUNT"
echo ""
echo "=== Platform is running ==="
echo ""
echo "Endpoints:"
echo "  Ingest API       : http://127.0.0.1:8001/docs"
echo "  Detection API    : http://127.0.0.1:8002/docs"
echo "  Redpanda Console : http://127.0.0.1:8080"
echo "  MLflow UI        : http://127.0.0.1:5001"
