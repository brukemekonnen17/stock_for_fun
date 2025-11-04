#!/bin/bash
# Start Everything - API + Frontend + Paper Trading

echo "🚀 Starting Complete Trading System..."
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if API is already running
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  API already running on port 8000${NC}"
else
    echo -e "${BLUE}📡 Starting Backend API...${NC}"
    source .venv/bin/activate
    uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000 > api.log 2>&1 &
    API_PID=$!
    echo -e "${GREEN}✅ API started (PID: $API_PID)${NC}"
    echo "   Logs: tail -f api.log"
fi

echo ""
sleep 3

# Check if Frontend is already running
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Frontend already running on port 3000${NC}"
else
    echo -e "${BLUE}🎨 Starting Frontend Dashboard...${NC}"
    npm run dev > frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo -e "${GREEN}✅ Frontend started (PID: $FRONTEND_PID)${NC}"
    echo "   Logs: tail -f frontend.log"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}🎉 System is starting up!${NC}"
echo ""
echo "📊 Dashboards (will be ready in ~10 seconds):"
echo "   • Catalyst Radar:      http://localhost:3000"
echo "   • Trading Dashboard:   http://localhost:3000/trading"
echo "   • API Docs:            http://localhost:8000/docs"
echo ""
echo "⏳ Waiting for services to be ready..."

# Wait for API
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ API is ready!${NC}"
        break
    fi
    sleep 1
    echo -n "."
done
echo ""

# Wait for Frontend
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Frontend is ready!${NC}"
        break
    fi
    sleep 1
    echo -n "."
done
echo ""

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}🚀 SYSTEM IS LIVE!${NC}"
echo ""
echo "🌐 Open these URLs:"
echo -e "   ${BLUE}http://localhost:3000${NC}          (Catalyst Radar)"
echo -e "   ${BLUE}http://localhost:3000/trading${NC}  (Trading Metrics)"
echo ""
echo "📝 To start paper trading, run in a new terminal:"
echo -e "   ${YELLOW}cd $(pwd)${NC}"
echo -e "   ${YELLOW}source .venv/bin/activate${NC}"
echo -e "   ${YELLOW}python paper_trading.py --interval 30${NC}"
echo ""
echo "📊 To monitor live stats:"
echo -e "   ${YELLOW}./monitor_trading.sh --watch${NC}"
echo ""
echo "🛑 To stop everything:"
echo -e "   ${YELLOW}pkill -f uvicorn && pkill -f 'next dev'${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Open browser (macOS only)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo ""
    echo "🌐 Opening dashboards in browser..."
    sleep 2
    open http://localhost:3000
    sleep 1
    open http://localhost:3000/trading
fi

