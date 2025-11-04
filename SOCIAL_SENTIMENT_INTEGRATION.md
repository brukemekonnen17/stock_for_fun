# ✅ Social Sentiment Integration - Complete

## 🎯 Strategy Transformation

**CRITICAL UPGRADE:** The system now integrates **real-time social sentiment** from StockTwits to support high-risk, high-reward momentum trading in low-cap stocks.

This transforms the agent from a traditional catalyst-based system to a **social momentum trader** that identifies and capitalizes on retail-driven price surges.

## ✅ Components Implemented

### 1. StockTwits API Adapter
**File:** `services/social/stocktwits_adapter.py`
- Fetches real-time messages from StockTwits public API
- No API key required (public endpoints)
- Rate limit handling built-in
- Returns raw message data for processing

### 2. Sentiment Scanner
**File:** `services/social/sentiment_scanner.py`
- Processes StockTwits messages into actionable metrics
- Uses simple counting of user-labeled sentiment (Bullish/Bearish)
- Research-confirmed approach: least error-prone for rapid trading
- Returns:
  - `sentiment_score`: -1.0 to 1.0 (positive = bullish momentum)
  - `mention_count_total`: Total messages (key indicator for low-float mania)
  - `bullish_pct`: Percentage of bullish messages
  - `bearish_pct`: Percentage of bearish messages

### 3. LLM Integration
**Files Updated:**
- `services/llm/schema.py` - Updated system prompt for momentum trading
- `services/llm/client.py` - Added social sentiment to template
- `apps/api/main.py` - Integrated sentiment fetch into propose endpoint

**Key Changes:**
- LLM now instructed to prioritize social momentum over fundamentals
- Social sentiment data included in every trade proposal
- Agent focuses on high mention count + positive sentiment

### 4. Policy Guardrails Updated
**Mandatory Configuration Changes** (see `.env` updates below)

## 🔧 Configuration

### Critical: Update `.env` File

**MANDATORY** - Add these updated guardrails for low-cap volatility:

```env
# Risk Guardrails (ADJUSTED FOR LOW-CAP VOLATILITY)

# Increased capital to handle large share counts in low-priced stocks
MAX_TICKET=1500

# Increased for diversification across momentum plays
MAX_POSITIONS=5

# Increased absolute loss tolerance for volatile entries
MAX_PER_TRADE_LOSS=50

# Increased daily stop-loss to manage overall volatility
DAILY_KILL_SWITCH=-100

# TIGHTENED to 3 cents max spread (was 0.05) - CRITICAL ADJUSTMENT
# Low-cap stocks need tighter spreads to prevent slippage
SPREAD_CENTS_MAX=0.03

# Increased basis point tolerance for low-priced stocks
SPREAD_BPS_MAX=150

# Increased slippage tolerance for illiquid stocks
SLIPPAGE_BPS=30
```

**Why These Changes:**
- **MAX_TICKET=1500**: Low-cap stocks trade at lower prices, requiring larger share counts
- **SPREAD_CENTS_MAX=0.03**: Tighter spreads prevent excessive slippage in volatile stocks
- **SPREAD_BPS_MAX=150**: Allows wider percentage spreads for low-priced stocks (e.g., $0.50 stock with $0.03 spread = 6%)
- **SLIPPAGE_BPS=30**: Higher slippage tolerance for illiquid momentum plays

## 📊 How It Works

```
Trade Proposal Request
    ↓
1. Fetch Market Data (price, spread, liquidity)
    ↓
2. Fetch Social Sentiment (NEW!)
   - Get recent StockTwits messages
   - Count bullish/bearish tags
   - Calculate sentiment score
    ↓
3. Combine Data Sources
   - Market data
   - Calendar events
   - News sentiment
   - Social sentiment (NEW!)
    ↓
4. LLM Decision
   - Prioritizes high mention count (>20)
   - Prioritizes positive sentiment (>0.5)
   - Generates momentum-based trade plan
    ↓
5. Policy Validation
   - Checks updated guardrails
   - Approves/rejects based on new limits
```

## 🚀 Testing

### Test 1: Social Sentiment Fetch

```bash
# Start API
uvicorn apps.api.main:app --reload

# Test sentiment endpoint (if you add one, or check logs)
# Or test via analyze endpoint
curl http://localhost:8000/analyze/AAPL | jq '.analysis'

# Check logs for:
# Social sentiment: score=0.650, mentions=45
```

### Test 2: Momentum Trade Proposal

```bash
# Analyze a stock with high social activity
curl http://localhost:8000/analyze/TSLA | jq '.plan'

# LLM should consider:
# - High mention count (momentum indicator)
# - Positive sentiment score (directional bias)
# - Generate momentum-based trade plan
```

### Test 3: Policy Guardrails

```bash
# Test with updated spread limits
# Low-priced stock with $0.05 spread should now be rejected
# (if SPREAD_CENTS_MAX=0.03)

# Check validation logs for:
# "Spread too wide" rejections
```

## 📈 Strategy Logic

### Momentum Identification

The agent now identifies trades where:
1. **High Mention Volume** (`mention_count_total > 20`)
   - Indicates retail interest and potential momentum
   - Low-float stocks can move dramatically on social hype

2. **Positive Sentiment** (`sentiment_score > 0.5`)
   - Bullish bias from retail traders
   - Directional signal for entry

3. **Acceptable Spread** (`SPREAD_CENTS_MAX = 0.03`)
   - Tighter spreads prevent excessive slippage
   - Critical for low-cap stocks where spreads can be wide

### LLM Prompt Integration

The LLM is explicitly instructed:
```
CRITICAL INSTRUCTION FOR LOW-CAP TRADING:
The primary driver is retail momentum and social sentiment, NOT fundamental data.

Prioritize trades where:
1. Mention Count is high (e.g., above 20)
2. Sentiment Score is significantly positive (e.g., above 0.5)
3. Stock's Current Spread is within expanded limits
```

## ⚠️ Important Notes

1. **StockTwits Rate Limits:**
   - Public API: Lenient for simple queries
   - No API key required
   - Built-in error handling

2. **Sentiment Calculation:**
   - Uses explicit user labels (Bullish/Bearish)
   - Research confirms this is most reliable for trading
   - Neutral baseline if no tagged sentiment

3. **Policy Guardrails:**
   - **MUST** update `.env` before testing
   - Old limits will reject all low-cap trades
   - New limits designed for volatility

4. **Backward Compatibility:**
   - If sentiment fetch fails, defaults to neutral
   - System continues to work without StockTwits
   - Existing trades not affected

## ✅ Verification Checklist

- [x] StockTwits adapter created
- [x] Sentiment scanner implemented
- [x] LLM prompt updated for momentum trading
- [x] Social sentiment integrated into propose endpoint
- [x] LLM client updated to include sentiment
- [x] Policy guardrails documented
- [x] Error handling with neutral fallback
- [x] No linting errors

## 🎉 Result

**The system now prioritizes social momentum over fundamentals for low-cap trading!**

The agent is now a **social momentum trader** that:
- Identifies high-volume social activity
- Uses positive sentiment as directional signal
- Generates momentum-based trade plans
- Operates within updated volatility guardrails

---

## 📝 Next Steps (Optional Enhancements)

1. **Sentiment Aggregation:**
   - Add Twitter/X integration
   - Add Reddit (r/wallstreetbets) sentiment
   - Weight multiple sources

2. **Sentiment Scoring Improvements:**
   - Add natural language processing
   - Weight by user influence
   - Time-decay for recent messages

3. **Monitoring Dashboard:**
   - Real-time sentiment visualization
   - Mention volume charts
   - Sentiment trend analysis

4. **Advanced Filtering:**
   - Filter by user verification
   - Weight by follower count
   - Exclude bot activity

---

## 📚 Research Reference

This implementation uses the research-confirmed approach of counting user-labeled sentiment tags, which is the least error-prone method for rapid-fire trading models.

For more on using sentiment analysis for trading strategies:
- [Using StockTwits Social Sentiment for Trading Strategies](https://www.youtube.com/watch?v=q9lTerSyptI)

---

**Ready for momentum trading!** 🚀📈

