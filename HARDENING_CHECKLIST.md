# Hardening Checklist ✅

## Completed

### ✅ 1. Smoke Tests
- [x] Created `smoke_tests.sh` with all core endpoints
- [x] Health, scan, propose, validate, reward tests
- [x] Kill-switch validation test
- [x] Spread validation test
- [x] Automated pass/fail checks with colored output

### ✅ 2. Reward Calculation
- [x] Implemented R-multiple (risk unit) formula
- [x] Risk unit = entry_price - stop_price
- [x] P&L calculated in R units
- [x] Clipped to [-1.0, 1.0]
- [x] Invalid trades (RU <= 0) return -1.0
- [x] Simulated exit with 60/40 target/stop probability

### ✅ 3. LLM Robustness
- [x] Retry logic with exponential backoff (2 retries default)
- [x] Timeout handling (30s total, 5s connect)
- [x] JSON validation with required key checks
- [x] Fallback to mock plan on failure
- [x] Comprehensive error logging
- [x] Template formatting error handling

### ✅ 4. Idempotency
- [x] Added `decision_id` to ProposePayload (auto-generated)
- [x] Propagated through validate and reward endpoints
- [x] Logged with every API call for tracing
- [x] Optional metadata in reward payload

### ✅ 5. Unit Tests
- [x] `test_validators.py`: 7 test cases
  - Approve valid trades
  - Reject on kill-switch
  - Reject on max positions
  - Reject on low liquidity
  - Reject on wide spread
  - Reject on invalid stop
- [x] `test_bandit.py`: 6 test cases
  - Initialization
  - Select returns valid arm
  - Determinism with seed
  - Update modifies parameters
  - Evidence accumulation
  - Multi-arm independence
- [x] `test_api.py`: 7 integration tests
  - Health endpoint
  - Scan endpoint
  - Propose with context
  - Validate approved
  - Validate rejected (kill-switch)
  - Bandit reward
  - Missing context error
- [x] pytest.ini configuration
- [x] Added pytest dependencies

### ✅ 6. Comprehensive Logging
- [x] Decision ID in brackets `[decision_id]` format
- [x] Propose: ticker, event_type, context_dim, selected_arm
- [x] Validate: ticker, entry, stop, verdict, reason, size
- [x] Reward: arm, reward value, context preview, decision_id
- [x] Structured log format with timestamps
- [x] Info level for decisions, debug for calculations

### ✅ 7. Bandit State Persistence
- [x] `BanditStatePersistence` class in `libs/analytics/persistence.py`
- [x] Save/load A and b matrices with pickle
- [x] Export to JSON for inspection
- [x] Automatic save on shutdown (atexit hook)
- [x] Automatic load on first bandit access
- [x] Dimension validation on load
- [x] State directory: `./bandit_state/`

## Production-Ready Enhancements

### Configuration
- [x] All guardrails in environment variables
- [x] LLM retry count configurable
- [x] Timeouts configurable
- [x] Database URL configurable

### Observability
- [x] Structured logging with decision IDs
- [x] Feature vectors logged
- [x] Verdict reasons logged
- [x] Arm selections logged

### Testing
- [x] Smoke tests (executable script)
- [x] Unit tests (pytest)
- [x] Integration tests (FastAPI TestClient)
- [x] Table-driven test cases

## Future Enhancements

### Metrics (Not Yet Implemented)
- [ ] Prometheus counters for proposals, approvals, rejections
- [ ] Histogram for reward distribution by arm
- [ ] Gauge for current open positions
- [ ] Counter for bandit updates
- [ ] Latency histograms per endpoint

### Advanced Persistence
- [ ] Periodic snapshots (every N updates)
- [ ] Snapshot versioning
- [ ] State export to S3/cloud storage
- [ ] Disaster recovery procedures

### Advanced Idempotency
- [ ] Decision cache (Redis/Memcached)
- [ ] Duplicate detection within time window
- [ ] Replay protection

### Monitoring
- [ ] Health check with detailed status
- [ ] Readiness probe (DB + LLM connectivity)
- [ ] Alerting on high rejection rates
- [ ] Dashboard for arm performance

### Advanced Testing
- [ ] Load testing (Locust/k6)
- [ ] Chaos engineering (kill LLM, database)
- [ ] Property-based testing (Hypothesis)
- [ ] Mutation testing

## Validation Results

### Smoke Tests
```bash
./smoke_tests.sh
# All 7 tests should pass
```

### Unit Tests
```bash
pytest
# 20+ tests should pass
```

### Paper Trading
```bash
python run_paper_trading.py
# Should complete full cycle without errors
```

### Persistence
```bash
# Run paper trading, then check state saved
ls -la bandit_state/
# Should see d*.pkl and d*.json files
```

## Notes

- **LLM Fallback**: System gracefully handles LLM failures with mock plans
- **R-Multiple Rewards**: Aligns with per-trade loss cap philosophy
- **Decision Tracing**: Every decision tracked end-to-end with decision_id
- **State Survives Restarts**: Bandit learning persists across server restarts
- **Test Coverage**: Core logic tested (validators, bandit, API)
- **Logging**: Production-ready structured logging

