#!/bin/bash
# Run both backend and frontend dev servers

trap 'kill 0' EXIT

echo "🚀 Starting Mas Shevach 360..."

# Backend
echo "📦 Backend (FastAPI) → http://localhost:8000"
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000 &

# Frontend
echo "⚛️  Frontend (Vite)   → http://localhost:3000"
cd frontend && npm run dev &

wait
