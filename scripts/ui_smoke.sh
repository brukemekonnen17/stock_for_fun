#!/usr/bin/env bash
set -euo pipefail

echo "=== UI Smoke Test ==="
echo ""

echo "1) /health"
curl -s http://127.0.0.1:8000/health 2>/dev/null | python -m json.tool 2>/dev/null || echo "Health check failed"
echo ""

echo "2) /stats/calibration"
curl -s http://127.0.0.1:8000/stats/calibration | python -m json.tool
echo ""

echo "3) /metrics/llm_phase1"
curl -s http://127.0.0.1:8000/metrics/llm_phase1 | python -m json.tool
echo ""

echo "4) /propose (AAPL) - checking llm_v2 confidence"
curl -s -X POST "http://127.0.0.1:8000/propose" \
 -H "Content-Type: application/json" \
 -d '{"ticker":"AAPL","price":190,"event_type":"EARNINGS","days_to_event":3,"context":[0.6,0.6,1,0.4,0.5,0.04,3],"rank_components":{},"backtest_kpis":{},"liquidity":10000000,"spread":0.002,"decision_id":"ui-smoke","volume_surge_ratio":1.5,"recent_high":195,"recent_low":185,"price_position":0.6,"rolling_volatility_10d":0.02,"breakout_flag":false,"adv_change":0.1}' \
 | python -c "import sys, json; d=json.load(sys.stdin); print(json.dumps({
    'verdict_i': d.get('analysis',{}).get('llm_v2',{}).get('verdict_intraday'),
    'verdict_s': d.get('analysis',{}).get('llm_v2',{}).get('verdict_swing_1to5d'),
    'conf': d.get('analysis',{}).get('llm_v2',{}).get('confidence'),
    'has_series': 'series' in d.get('analysis',{}),
    'alignment': d.get('analysis',{}).get('alignment'),
    'nba': d.get('analysis',{}).get('nba_score'),
    'has_drivers': 'drivers' in d.get('analysis',{})
}, indent=2))"
echo ""

echo "5) /evidence/event-study"
curl -s "http://127.0.0.1:8000/evidence/event-study?ticker=AAPL&event=EARNINGS&pre=5&post=5" | python -c "import sys, json; d=json.load(sys.stdin); print(f\"N_events: {d.get('N_events', 0)}, CAR length: {len(d.get('car', []))}\")"
echo ""

echo "6) /scan"
curl -s "http://127.0.0.1:8000/scan?min_rank=70&limit=10" | python -c "import sys, json; arr=json.load(sys.stdin); print(json.dumps(arr[0] if arr else {}, indent=2))" 2>/dev/null || echo "Scan returned empty or error"
echo ""

echo "=== Smoke Test Complete ==="

