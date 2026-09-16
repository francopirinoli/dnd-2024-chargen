#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "=== Installing Python dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Building React SPA frontend ==="
cd frontend
npm install
npm run build
cd ..

echo "=== Build finished successfully ==="
