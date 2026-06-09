#!/bin/bash
# Review Service - Quick Start Script

set -e

echo "🚀 Review Service - Quick Start"
echo "========================================"

# Check Python
echo "✓ Checking Python..."
python --version

# Install dependencies
echo "✓ Installing dependencies..."
python -m pip install -q -r requirements.txt

# Create .env if missing
if [ ! -f .env ]; then
    echo "✓ Creating .env file..."
    cp .env.example .env
fi

# Run tests (optional)
if [ -f tests/test_main.py ]; then
    echo "✓ Running tests..."
    python -m pytest tests/ -v --tb=short || true
fi

# Start service
echo ""
echo "========================================"
echo "🎯 Starting Review Service"
echo "📍 http://localhost:8006"
echo "📚 Docs: http://localhost:8006/docs"
echo "========================================"
echo ""

python main.py
