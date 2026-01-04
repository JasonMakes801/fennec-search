#!/bin/bash
# Fresh start: stops containers, wipes database, rebuilds and starts fresh

set -e

cd "$(dirname "$0")/.."

echo "Stopping containers..."
docker compose down

echo "Removing database volume..."
docker volume rm fennec-search_fennec_data 2>/dev/null || docker volume rm fennec_data 2>/dev/null || true

echo "Building containers (using cache)..."
docker compose build

echo "Starting containers..."
docker compose up -d

echo "Done. Database is empty. Containers running."
echo "  UI: http://localhost:8080"
echo "  API: http://localhost:8000"
echo ""
echo "Tailing ingest logs (Ctrl+C to stop)..."
docker compose logs -f ingest
