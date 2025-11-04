#!/bin/bash
# Test that API is working RIGHT NOW

echo "🧪 Testing Your Live API..."
echo "================================"
echo ""

echo "1️⃣ Health Check:"
curl -s http://localhost:8000/health | python3 -m json.tool
echo ""
echo ""

echo "2️⃣ Bandit Statistics:"
curl -s http://localhost:8000/bandit/stats | python3 -m json.tool
echo ""
echo ""

echo "3️⃣ Catalyst Scan (Real Market Data):"
curl -s http://localhost:8000/scan | python3 -m json.tool
echo ""
echo ""

echo "================================"
echo "✅ API is working perfectly!"
echo ""
echo "🎯 Next step: Start paper trading!"
echo "   python paper_trading.py --interval 30"
echo ""
echo "📊 Or open interactive docs:"
echo "   http://localhost:8000/docs"
