#!/bin/bash
set -e

echo "📦 Installing backend dependencies..."
cd backend
pip install -r requirements.txt

echo "⚛️  Building frontend..."
cd ../frontend
npm install
npm run build

echo "📁 Copying frontend build to backend/static..."
rm -rf ../backend/static
cp -r dist ../backend/static

echo "✅ Build complete"
