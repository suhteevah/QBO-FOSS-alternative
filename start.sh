#!/usr/bin/env bash
# OpenLedger — Quick Start (dev mode)
# Starts both backend and frontend in the background

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate venv
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

echo "Starting OpenLedger..."
echo ""

# Start backend
echo "[1/2] Starting API server on port 8000..."
uvicorn openledger.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

# Start frontend
echo "[2/2] Starting frontend on port 3000..."
cd frontend && npm run dev &
FE_PID=$!
cd "$SCRIPT_DIR"

echo ""
echo "OpenLedger is running!"
echo "  Frontend:  http://localhost:3000"
echo "  API Docs:  http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

# Cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $API_PID 2>/dev/null || true
    kill $FE_PID 2>/dev/null || true
    wait 2>/dev/null || true
    echo "Stopped."
}
trap cleanup EXIT INT TERM

wait
