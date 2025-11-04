# Testing Guide

## Quick Smoke Tests

Run the automated smoke test suite:

```bash
./smoke_tests.sh
```

This tests all core endpoints and validates:
- Health check
- Scan endpoint
- Propose with bandit selection
- Validation with policy rules
- Reward logging
- Kill-switch rejection
- Spread validation

## Unit Tests

Run the full test suite:

```bash
# Install test dependencies first
pip install pytest pytest-asyncio

# Run all tests
pytest

# Run specific test file
pytest tests/test_validators.py -v

# Run with coverage
pytest --cov=apps --cov=services --cov=libs
```

### Test Structure

```
tests/
├── test_validators.py    # Policy validation rules
├── test_bandit.py         # Contextual Thompson Sampling
└── test_api.py            # FastAPI endpoints
```

## Manual API Tests

### 1. Propose Trade

```bash
curl -X POST http://localhost:8000/propose \
  -H "Content-Type: application/json" \
  -d '{
    "ticker":"AAPL",
    "price":192.50,
    "event_type":"EARNINGS",
    "days_to_event":7,
    "rank_components":{"immediacy":0.6,"materiality":0.6,"liq":1.0},
    "expected_move":0.04,
    "backtest_kpis":{"hit_rate":0.54,"avg_win":0.012},
    "liquidity":5000000000,
    "spread":0.01,
    "news_summary":"Test",
    "context":[0.6,0.6,1.0,0.4,0.5,0.04,7]
  }' | jq .
```

Expected response:
```json
{
  "selected_arm": "POST_EVENT_MOMO",
  "plan": {
    "ticker": "AAPL",
    "entry_type": "limit",
    "entry_price": 191.50,
    ...
  },
  "decision_id": "1699..."
}
```

### 2. Validate Trade

```bash
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d '{
    "plan":{
      "ticker":"AAPL",
      "entry_type":"limit",
      "entry_price":192.00,
      "stop_rule":"ATR14 * 1.0 below entry",
      "stop_price":189.00,
      "target_rule":"1.5 x stop",
      "target_price":196.50,
      "timeout_days":5,
      "confidence":0.72,
      "reason":"Test"
    },
    "market":{"price":192.30,"spread":0.01,"avg_dollar_vol":5000000000},
    "context":{"open_positions":1,"realized_pnl_today":-10.0},
    "decision_id":"1699..."
  }' | jq .
```

Expected response:
```json
{
  "verdict": "APPROVED",
  "reason": "All checks passed",
  "adjusted_size": 3
}
```

### 3. Log Reward

```bash
curl -X POST http://localhost:8000/bandit/reward \
  -H "Content-Type: application/json" \
  -d '{
    "arm_name":"POST_EVENT_MOMO",
    "context":[0.6,0.6,1.0,0.4,0.5,0.04,7],
    "reward":0.35,
    "decision_id":"1699...",
    "meta":{"ticker":"AAPL","entry_px":192.0}
  }'
```

Expected response:
```json
{"status": "ok"}
```

## Correctness Checks

### Kill-Switch Test

```bash
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d '{
    "plan":{"ticker":"AAPL","entry_type":"limit","entry_price":192.0,"stop_rule":"test","stop_price":189.0,"target_rule":"test","target_price":196.5,"timeout_days":5,"confidence":0.72,"reason":"test"},
    "market":{"price":192.3,"spread":0.01,"avg_dollar_vol":5000000000},
    "context":{"open_positions":1,"realized_pnl_today":-100.0}
  }' | jq .
```

Should return `"verdict": "REJECTED"` with reason containing "kill-switch".

### Spread Validation

```bash
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d '{
    "plan":{"ticker":"AAPL","entry_type":"limit","entry_price":192.0,"stop_rule":"test","stop_price":189.0,"target_rule":"test","target_price":196.5,"timeout_days":5,"confidence":0.72,"reason":"test"},
    "market":{"price":192.3,"spread":0.10,"avg_dollar_vol":5000000000},
    "context":{"open_positions":0,"realized_pnl_today":0.0}
  }' | jq .
```

Should return `"verdict": "REJECTED"` with reason containing "spread".

## Paper Trading Tests

### Single Cycle Test

```bash
python run_paper_trading.py
```

Expected output shows all 4 steps:
1. Propose → Selected arm
2. Validate → Approved/Rejected
3. Fill → Price + slippage
4. Reward → R-multiple calculated

### Continuous Loop

```bash
python paper_trading.py --interval 10
```

Watch logs for:
- Decision IDs in brackets `[1699...]`
- Bandit arm selection
- Validation verdicts
- R-multiple rewards (clipped to [-1.0, 1.0])

## Database Checks

Check bandit logs:

```bash
sqlite3 catalyst.db "SELECT * FROM bandit_logs ORDER BY ts DESC LIMIT 10;"
```

Check for arm name, context vector, and reward columns.

## Bandit State Persistence

After running a few cycles, check:

```bash
ls -la bandit_state/
cat bandit_state/d7.json  # If you ran with 7-dim context
```

State is automatically saved on shutdown (atexit hook).

## Performance Benchmarks

Expected latencies (local):
- `/health`: < 5ms
- `/scan`: < 10ms
- `/propose` (without LLM): < 50ms
- `/propose` (with LLM): 500-2000ms
- `/validate`: < 10ms
- `/bandit/reward`: < 20ms

## Troubleshooting

### Tests fail with import errors

```bash
# Make sure you're in project root
cd /Users/brukemekonnen/stock_investment

# Ensure PYTHONPATH includes current directory
export PYTHONPATH=.
pytest
```

### LLM tests timeout

LLM client has retry logic and falls back to mock plans. If tests consistently timeout, check `DEEPSEEK_API_URL` in .env or increase timeout in `services/llm/client.py`.

### Database locked errors

If running multiple instances, SQLite may lock. Use PostgreSQL for production:

```bash
export DB_URL="postgresql://user:pass@localhost/catalyst"
```

