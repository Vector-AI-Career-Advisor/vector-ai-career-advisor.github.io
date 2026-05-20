#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."

cleanup() {
  echo ""
  echo "Shutting down..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  echo "Done."
}
trap cleanup SIGINT SIGTERM

echo "Starting server..."
cd "$ROOT/server"
"$ROOT/.venv/bin/uvicorn" main:app --reload --port 8000 &
BACKEND_PID=$!

echo "Starting client..."
cd "$ROOT/client"
npm install --silent
npm run dev &
FRONTEND_PID=$!

echo ""
echo "Server:  http://localhost:8000"
echo "Client: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop."

wait "$BACKEND_PID" "$FRONTEND_PID"
