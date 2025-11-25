#!/bin/bash
# Quick launcher for JobHunter Web Dashboard
# Usage: ./start_dashboard.sh

echo ""
echo "============================================================"
echo "🚀 Starting JobHunter Web Dashboard..."
echo "============================================================"
echo ""

# Kill any existing process on port 5002
lsof -ti:5002 | xargs kill -9 2>/dev/null

# Start the dashboard
python3 web_app.py
