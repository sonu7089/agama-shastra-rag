#!/bin/bash
# Render startup script with debugging

echo "=== Startup Script Started ==="
echo "PORT environment variable: $PORT"

# Use PORT from environment, default to 8000 if not set
PORT=${PORT:-8000}

echo "Using port: $PORT"
echo "Starting Uvicorn..."

# Run uvicorn with explicit error output
uvicorn src.api:app --host 0.0.0.0 --port $PORT 2>&1 || {
    echo "ERROR: Uvicorn failed to start"
    echo "Exit code: $?"
    exit 1
}
