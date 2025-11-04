#!/bin/bash
# Quick Start - Opens 4 terminals and starts everything
# Run with: ./quick_start.sh

echo "🚀 Starting Complete Trading System..."
echo ""

# Check if we're on macOS (has 'open' command)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS - use Terminal.app
    
    # Terminal 1: API
    osascript -e 'tell application "Terminal"
        do script "cd /Users/brukemekonnen/stock_investment && source .venv/bin/activate && echo \"Starting API...\" && uvicorn apps.api.main:app --reload"
    end tell'
    
    sleep 2
    
    # Terminal 2: Frontend
    osascript -e 'tell application "Terminal"
        do script "cd /Users/brukemekonnen/stock_investment && echo \"Starting Frontend...\" && npm run dev"
    end tell'
    
    sleep 3
    
    # Terminal 3: Test
    osascript -e 'tell application "Terminal"
        do script "cd /Users/brukemekonnen/stock_investment && sleep 5 && echo \"Testing connections...\" && ./test_live_integration.sh && echo \"\" && echo \"Press ENTER to start paper trading...\" && read && source .venv/bin/activate && python paper_trading.py --interval 30"
    end tell'
    
    sleep 2
    
    # Open browser
    sleep 3
    open http://localhost:3000
    open http://localhost:8000/docs
    
    echo "✅ All terminals opened!"
    echo ""
    echo "Check your Terminal windows:"
    echo "  1. API running on :8000"
    echo "  2. Frontend on :3000"
    echo "  3. Tests + Paper Trading"
    echo ""
    echo "Dashboard: http://localhost:3000"
    echo "API Docs: http://localhost:8000/docs"
    
else
    # Linux or other - manual instructions
    echo "Please open 4 terminals manually:"
    echo ""
    echo "Terminal 1 (API):"
    echo "  cd /Users/brukemekonnen/stock_investment"
    echo "  source .venv/bin/activate"
    echo "  uvicorn apps.api.main:app --reload"
    echo ""
    echo "Terminal 2 (Frontend):"
    echo "  cd /Users/brukemekonnen/stock_investment"
    echo "  npm run dev"
    echo ""
    echo "Terminal 3 (Test):"
    echo "  cd /Users/brukemekonnen/stock_investment"
    echo "  ./test_live_integration.sh"
    echo ""
    echo "Terminal 4 (Paper Trading):"
    echo "  cd /Users/brukemekonnen/stock_investment"
    echo "  source .venv/bin/activate"
    echo "  python paper_trading.py --interval 30"
fi

