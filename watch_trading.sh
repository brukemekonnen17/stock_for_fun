#!/bin/bash
# Watch paper trading in action

cd /Users/brukemekonnen/stock_investment
source .venv/bin/activate

echo "🎯 Starting Paper Trading - Watch Your AI Learn!"
echo "================================================"
echo ""
echo "The trading loop will:"
echo "  1. Propose a trade (bandit selects strategy)"
echo "  2. Validate against risk rules"
echo "  3. Simulate execution"
echo "  4. Calculate reward"
echo "  5. Update bandit learning"
echo ""
echo "Cycles every 30 seconds. Press Ctrl+C to stop."
echo ""
echo "================================================"
echo ""

python paper_trading.py --interval 30

