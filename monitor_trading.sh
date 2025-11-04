#!/bin/bash
# Real-time monitoring of paper trading
# Shows live stats as trading happens

echo "📊 Live Trading Monitor"
echo "================================"
echo ""

# Check if database exists
if [ ! -f catalyst.db ]; then
    echo "⚠️  No database found yet. Start paper trading first:"
    echo "   python paper_trading.py --interval 30"
    exit 1
fi

# Function to get stats
get_stats() {
    echo "📈 Trading Statistics (Last update: $(date '+%H:%M:%S'))"
    echo "================================"
    
    # Total decisions
    TOTAL=$(sqlite3 catalyst.db "SELECT COUNT(*) FROM bandit_logs;" 2>/dev/null || echo "0")
    echo "Total Decisions: $TOTAL"
    echo ""
    
    if [ "$TOTAL" -gt 0 ]; then
        # Performance by arm
        echo "Performance by Strategy Arm:"
        sqlite3 -header -column catalyst.db "
        SELECT 
          arm_name as 'Arm',
          COUNT(*) as 'Times Selected',
          printf('%.4f', AVG(reward)) as 'Avg Reward',
          printf('%.4f', MIN(reward)) as 'Worst',
          printf('%.4f', MAX(reward)) as 'Best'
        FROM bandit_logs
        GROUP BY arm_name
        ORDER BY AVG(reward) DESC;
        " 2>/dev/null
        
        echo ""
        echo "Recent Decisions:"
        sqlite3 -header -column catalyst.db "
        SELECT 
          strftime('%H:%M:%S', ts) as 'Time',
          arm_name as 'Arm',
          printf('%.4f', reward) as 'Reward'
        FROM bandit_logs
        ORDER BY ts DESC
        LIMIT 5;
        " 2>/dev/null
    else
        echo "Waiting for first trade..."
    fi
    
    echo ""
    echo "================================"
}

# Watch mode - updates every 10 seconds
if [ "$1" == "--watch" ] || [ "$1" == "-w" ]; then
    echo "📡 Live monitoring mode (Ctrl+C to stop)"
    echo ""
    while true; do
        clear
        get_stats
        echo ""
        echo "Updates every 10 seconds..."
        sleep 10
    done
else
    # Single shot
    get_stats
    echo ""
    echo "Run with --watch for live updates:"
    echo "  ./monitor_trading.sh --watch"
fi

