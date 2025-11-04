# 🚀 Quick Setup: IEX Cloud (Paid Market Data)

Yahoo Finance doesn't have a paid version - it's free but heavily rate-limited. **IEX Cloud** is the best alternative with reliable paid data.

## ⚡ Quick Setup (5 minutes)

### Step 1: Sign Up for IEX Cloud

1. Go to: **https://iexcloud.io/cloud-login#/register**
2. Sign up (free tier available - no credit card required)
3. Log in to your dashboard

### Step 2: Get Your API Key

1. In the dashboard, find **"Publishable API Token"**
2. It starts with `pk_...` (e.g., `pk_0123456789abcdef...`)
3. Copy the entire token

### Step 3: Add to Your `.env` File

Create or edit `.env` in your project root:

```bash
# Market Data - IEX Cloud (reliable, no rate limits)
IEX_CLOUD_API_KEY=pk_your_actual_api_key_here
```

**Example:**
```bash
IEX_CLOUD_API_KEY=pk_0123456789abcdef0123456789abcdef
```

### Step 4: Restart the API

The system will **automatically detect** the key and use IEX Cloud instead of Yahoo Finance.

```bash
# Stop current API (Ctrl+C)
# Then restart:
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

You should see in the logs:
```
INFO: Using IEX Cloud for market data (IEX_CLOUD_API_KEY found)
```

### Step 5: Test It!

```bash
curl http://127.0.0.1:8000/analyze/NVDA
```

Should work immediately! ✅

---

## 💰 Pricing

### Free Tier (Starter)
- **50,000 messages/month** (free forever)
- Perfect for testing and light usage
- No credit card required

### Paid Tiers
- **Launch**: $9/month - 1M messages/month
- **Grow**: $49/month - 5M messages/month
- **Scale**: Custom pricing

**For most users**: Free tier is plenty for testing!

---

## ✅ What This Fixes

- ✅ **No more rate limits** - IEX Cloud is reliable
- ✅ **Real-time data** - No delays
- ✅ **Better error handling** - Clear error messages
- ✅ **Automatic switching** - System detects key and switches automatically

---

## 🔍 Verify It's Working

After restarting, check the logs:
```
INFO: Using IEX Cloud for market data (IEX_CLOUD_API_KEY found)
```

Then test:
```bash
curl http://127.0.0.1:8000/analyze/AAPL
curl http://127.0.0.1:8000/analyze/NVDA
```

Both should work immediately! ✅

---

**Status**: Ready to use once you add the API key! 🚀

