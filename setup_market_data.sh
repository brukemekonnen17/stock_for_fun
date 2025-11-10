#!/bin/bash

echo "🚀 Market Data API Key Setup"
echo "======================================"
echo ""
echo "Currently using: yfinance (free, rate-limited)"
echo "Recommendation: Set up IEX Cloud for reliable data"
echo ""
echo "Choose a provider:"
echo "  1. IEX Cloud (Recommended - Free tier: 50K calls/month)"
echo "  2. Tiingo (Free tier: 500 calls/day)"
echo "  3. Alpha Vantage (Free tier: 5 calls/min)"
echo "  4. Skip for now (continue with yfinance + rate limiting fixes)"
echo ""
read -p "Enter choice (1-4): " choice

case $choice in
    1)
        echo ""
        echo "📝 IEX Cloud Setup:"
        echo "  1. Go to: https://iexcloud.io"
        echo "  2. Sign up (free)"
        echo "  3. Copy your API key (starts with pk_)"
        echo ""
        read -p "Enter your IEX Cloud API key (or press Enter to skip): " api_key
        if [ ! -z "$api_key" ]; then
            echo "export IEX_CLOUD_API_KEY=$api_key" >> ~/.zshrc
            export IEX_CLOUD_API_KEY=$api_key
            echo "✅ IEX Cloud API key configured!"
            echo "   Restart your terminal or run: source ~/.zshrc"
        fi
        ;;
    2)
        echo ""
        echo "📝 Tiingo Setup:"
        echo "  1. Go to: https://api.tiingo.com"
        echo "  2. Sign up (free)"
        echo "  3. Copy your API token"
        echo ""
        read -p "Enter your Tiingo API token (or press Enter to skip): " api_key
        if [ ! -z "$api_key" ]; then
            echo "export TIINGO_API_KEY=$api_key" >> ~/.zshrc
            export TIINGO_API_KEY=$api_key
            echo "✅ Tiingo API key configured!"
            echo "   Restart your terminal or run: source ~/.zshrc"
        fi
        ;;
    3)
        echo ""
        echo "📝 Alpha Vantage Setup:"
        echo "  1. Go to: https://www.alphavantage.co/support/#api-key"
        echo "  2. Enter your email to get free API key"
        echo "  3. Copy the key from the email"
        echo ""
        read -p "Enter your Alpha Vantage API key (or press Enter to skip): " api_key
        if [ ! -z "$api_key" ]; then
            echo "export ALPHA_VANTAGE_API_KEY=$api_key" >> ~/.zshrc
            export ALPHA_VANTAGE_API_KEY=$api_key
            echo "✅ Alpha Vantage API key configured!"
            echo "   Restart your terminal or run: source ~/.zshrc"
        fi
        ;;
    4)
        echo ""
        echo "⚠️  Continuing with yfinance (rate-limited)"
        echo "   Rate limiting fixes have been applied to reduce errors."
        echo "   Consider setting up a paid provider later to avoid 429 errors."
        ;;
    *)
        echo "Invalid choice"
        ;;
esac

echo ""
echo "======================================"
echo "Current Configuration:"
echo "======================================"
[ ! -z "$IEX_CLOUD_API_KEY" ] && echo "✅ IEX Cloud: Configured" || echo "❌ IEX Cloud: Not configured"
[ ! -z "$TIINGO_API_KEY" ] && echo "✅ Tiingo: Configured" || echo "❌ Tiingo: Not configured"
[ ! -z "$ALPHA_VANTAGE_API_KEY" ] && echo "✅ Alpha Vantage: Configured" || echo "❌ Alpha Vantage: Not configured"
echo ""
echo "Fallback chain: Tiingo → Alpha Vantage → yfinance"
echo ""
echo "To apply changes, restart your API server:"
echo "  cd /Users/brukemekonnen/stock_investment"
echo "  ./start_api.sh"
echo ""

