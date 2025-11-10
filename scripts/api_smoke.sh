#!/usr/bin/env bash
set -euo pipefail

echo "[/healthz]"
curl -s http://127.0.0.1:8000/healthz | python -m json.tool || echo "Failed"

echo ""
echo "[/features]"
curl -s http://127.0.0.1:8000/features | python -m json.tool || echo "Failed"

echo ""
echo "[/propose AAPL]"
curl -s -X POST http://127.0.0.1:8000/propose -H 'Content-Type: application/json' \
 -d '{"ticker":"AAPL","price":190,"event_type":"EARNINGS","days_to_event":5,
      "context":[0.6,0.6,1,0.4,0.5,0.04,5],
      "rank_components":{},"backtest_kpis":{},
      "liquidity":10000000,"spread":0.002,"decision_id":"preview"}' \
 | python -c "import sys, json; d=json.load(sys.stdin); print(json.dumps({
    'llm_version': d.get('analysis',{}).get('llm_version'),
    'drivers': (d.get('analysis',{}).get('drivers') is not None),
    'has_series': (d.get('analysis',{}).get('series') is not None)
}, indent=2))" || echo "Failed"

