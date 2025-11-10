#!/bin/bash
# Clean restart of API server with proper .env loading

cd /Users/brukemekonnen/stock_investment

echo "🛑 Stopping any existing API servers..."
pkill -9 -f "uvicorn.*main:app" 2>/dev/null
lsof -ti:8000 | xargs kill -9 2>/dev/null
sleep 2

echo "✅ Starting API server with .env loaded..."
# Use the anaconda environment that has all dependencies
/Users/brukemekonnen/anaconda3/bin/uvicorn apps.api.main:app \
    --reload \
    --host 0.0.0.0 \
    --port 8000 \
    > api.log 2>&1 &

SERVER_PID=$!
echo "📡 Server starting (PID: $SERVER_PID)"
echo "📋 Logs: tail -f api.log"

# Wait for server to be ready
echo "⏳ Waiting for server to be ready..."
for i in {1..10}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Server is ready!"
        echo ""
        echo "🧪 Testing /summarize endpoint..."
        curl -X POST http://localhost:8000/summarize \
            -H "Content-Type: application/json" \
            -d '{"file_path": "artifacts/analysis_contract.json"}' \
            -s | head -20
        echo ""
        echo "🌐 Open in browser: http://localhost:8000/"
        exit 0
    fi
    sleep 1
    echo -n "."
done

echo ""
echo "⚠️  Server may still be starting. Check logs: tail -f api.log"
echo "🌐 Once ready, open: http://localhost:8000/"

