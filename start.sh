#!/bin/bash
echo "🚀 Starting AI Email SaaS..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 10000
