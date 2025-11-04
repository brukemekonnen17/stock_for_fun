#!/bin/bash
# Start the FastAPI backend server

echo "Starting Catalyst Scanner API..."
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

