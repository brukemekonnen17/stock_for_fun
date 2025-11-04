# E*TRADE Integration Plan

## Prerequisites

### 1. E*TRADE Developer Account
- Sign up at https://developer.etrade.com/
- Create an application
- Get OAuth credentials:
  - **Consumer Key**
  - **Consumer Secret**

### 2. Account Access
- E*TRADE brokerage account
- Trading enabled
- API access enabled (contact E*TRADE if not)

## Architecture

```
Paper Trading Loop
       ↓
   /propose (Bandit + LLM)
       ↓
   /validate (Policy Check)
       ↓
   E*TRADE Client ← [NEW COMPONENT]
       ↓
   Order Submitted
       ↓
   Fill Received
       ↓
   /bandit/reward
```

## Implementation Steps

### Step 1: Install Dependencies

```bash
pip install requests-oauthlib
```

Update `requirements.txt`:
```txt
requests-oauthlib==1.3.1
```

### Step 2: Create E*TRADE Client

**File:** `services/broker/etrade_client.py`

```python
import os
import json
import logging
from requests_oauthlib import OAuth1Session
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ETradeClient:
    """E*TRADE API client for order execution and market data"""
    
    BASE_URL = "https://api.etrade.com"
    SANDBOX_URL = "https://apisb.etrade.com"  # For testing
    
    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        sandbox: bool = True
    ):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.base_url = self.SANDBOX_URL if sandbox else self.BASE_URL
        self.session: Optional[OAuth1Session] = None
        self.account_id_key: Optional[str] = None
    
    def authenticate(self):
        """
        OAuth authentication flow.
        Returns authorization URL for user to visit.
        """
        # Step 1: Get request token
        request_token_url = f"{self.base_url}/oauth/request_token"
        oauth = OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
            callback_uri='oob'
        )
        
        try:
            fetch_response = oauth.fetch_request_token(request_token_url)
            resource_owner_key = fetch_response.get('oauth_token')
            resource_owner_secret = fetch_response.get('oauth_token_secret')
            
            # Step 2: User authorization
            authorize_url = f"{self.base_url}/oauth/authorize"
            authorization_url = oauth.authorization_url(authorize_url)
            
            logger.info(f"Visit this URL to authorize: {authorization_url}")
            print(f"\n🔐 Authorization Required:")
            print(f"Visit: {authorization_url}")
            print(f"Enter the verification code: ", end='')
            
            verifier = input().strip()
            
            # Step 3: Get access token
            access_token_url = f"{self.base_url}/oauth/access_token"
            oauth = OAuth1Session(
                self.consumer_key,
                client_secret=self.consumer_secret,
                resource_owner_key=resource_owner_key,
                resource_owner_secret=resource_owner_secret,
                verifier=verifier
            )
            
            oauth_tokens = oauth.fetch_access_token(access_token_url)
            
            self.session = OAuth1Session(
                self.consumer_key,
                client_secret=self.consumer_secret,
                resource_owner_key=oauth_tokens.get('oauth_token'),
                resource_owner_secret=oauth_tokens.get('oauth_token_secret')
            )
            
            logger.info("✅ Authentication successful")
            return True
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def list_accounts(self) -> list:
        """Get list of accounts"""
        url = f"{self.base_url}/v1/accounts/list"
        response = self.session.get(url, headers={'Accept': 'application/json'})
        response.raise_for_status()
        
        data = response.json()
        accounts = data.get('AccountListResponse', {}).get('Accounts', {}).get('Account', [])
        
        if accounts and not self.account_id_key:
            # Store first account as default
            self.account_id_key = accounts[0]['accountIdKey']
        
        return accounts
    
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get real-time quote"""
        url = f"{self.base_url}/v1/market/quote/{symbol}"
        response = self.session.get(url, headers={'Accept': 'application/json'})
        response.raise_for_status()
        
        data = response.json()
        quote = data.get('QuoteResponse', {}).get('QuoteData', [{}])[0]
        
        return {
            'symbol': symbol,
            'last': quote.get('All', {}).get('lastTrade', 0),
            'bid': quote.get('All', {}).get('bid', 0),
            'ask': quote.get('All', {}).get('ask', 0),
            'spread': quote.get('All', {}).get('ask', 0) - quote.get('All', {}).get('bid', 0),
            'volume': quote.get('All', {}).get('totalVolume', 0)
        }
    
    def place_order(
        self,
        symbol: str,
        quantity: int,
        side: str,  # 'buy' or 'sell'
        order_type: str = 'limit',
        limit_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Place an order.
        Returns order details with order_id.
        """
        if not self.account_id_key:
            raise ValueError("No account selected. Call list_accounts() first.")
        
        # Build order payload
        order_action = "BUY" if side.lower() == "buy" else "SELL"
        price_type = "LIMIT" if order_type == "limit" else "MARKET"
        
        order = {
            "PlaceOrderRequest": {
                "orderType": "EQ",
                "clientOrderId": f"{int(datetime.utcnow().timestamp())}",
                "Order": {
                    "allOrNone": "false",
                    "priceType": price_type,
                    "orderTerm": "GOOD_FOR_DAY",
                    "marketSession": "REGULAR",
                    "Instrument": {
                        "Product": {
                            "securityType": "EQ",
                            "symbol": symbol
                        },
                        "orderAction": order_action,
                        "quantityType": "QUANTITY",
                        "quantity": quantity
                    }
                }
            }
        }
        
        if price_type == "LIMIT" and limit_price:
            order["PlaceOrderRequest"]["Order"]["limitPrice"] = limit_price
        
        # Preview order first (required by E*TRADE)
        preview_url = f"{self.base_url}/v1/accounts/{self.account_id_key}/orders/preview"
        preview_response = self.session.post(
            preview_url,
            json=order,
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
        )
        preview_response.raise_for_status()
        
        preview_data = preview_response.json()
        preview_id = preview_data.get('PreviewOrderResponse', {}).get('PreviewIds', [{}])[0].get('previewId')
        
        # Place order
        place_url = f"{self.base_url}/v1/accounts/{self.account_id_key}/orders/place"
        order["PlaceOrderRequest"]["PreviewIds"] = [{"previewId": preview_id}]
        
        place_response = self.session.post(
            place_url,
            json=order,
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
        )
        place_response.raise_for_status()
        
        place_data = place_response.json()
        order_id = place_data.get('PlaceOrderResponse', {}).get('OrderIds', [{}])[0].get('orderId')
        
        logger.info(f"Order placed: {order_id} - {side} {quantity} {symbol} @ {limit_price}")
        
        return {
            'order_id': order_id,
            'symbol': symbol,
            'quantity': quantity,
            'side': side,
            'order_type': order_type,
            'limit_price': limit_price,
            'status': 'OPEN'
        }
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Check order status"""
        url = f"{self.base_url}/v1/accounts/{self.account_id_key}/orders/{order_id}"
        response = self.session.get(url, headers={'Accept': 'application/json'})
        response.raise_for_status()
        
        data = response.json()
        order_details = data.get('OrdersResponse', {}).get('Order', [{}])[0]
        
        return {
            'order_id': order_id,
            'status': order_details.get('orderStatus'),
            'filled_quantity': order_details.get('filledQuantity', 0),
            'average_execution_price': order_details.get('averageExecutionPrice', 0)
        }
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order"""
        url = f"{self.base_url}/v1/accounts/{self.account_id_key}/orders/cancel"
        payload = {
            "CancelOrderRequest": {
                "orderId": order_id
            }
        }
        
        response = self.session.put(
            url,
            json=payload,
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
        )
        response.raise_for_status()
        
        logger.info(f"Order cancelled: {order_id}")
        return True
```

### Step 3: Configuration

Add to `.env`:
```env
# E*TRADE
ETRADE_CONSUMER_KEY=your_consumer_key_here
ETRADE_CONSUMER_SECRET=your_consumer_secret_here
ETRADE_SANDBOX=true  # Set to false for production
```

### Step 4: Create Live Trading Loop

**File:** `live_trading.py`

```python
"""
Live trading loop using E*TRADE
"""
import asyncio
import logging
from paper_trading import PaperTradingLoop
from services.broker.etrade_client import ETradeClient
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LiveTradingLoop(PaperTradingLoop):
    """Trading loop with real E*TRADE execution"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialize E*TRADE client
        self.broker = ETradeClient(
            consumer_key=os.getenv("ETRADE_CONSUMER_KEY"),
            consumer_secret=os.getenv("ETRADE_CONSUMER_SECRET"),
            sandbox=os.getenv("ETRADE_SANDBOX", "true").lower() == "true"
        )
        
        # Authenticate
        if not self.broker.authenticate():
            raise RuntimeError("E*TRADE authentication failed")
        
        # List accounts
        accounts = self.broker.list_accounts()
        logger.info(f"Connected to {len(accounts)} E*TRADE account(s)")
    
    async def simulate_fill(self, plan: dict):
        """Override to use real E*TRADE order execution"""
        symbol = plan.get("ticker")
        entry_price = plan.get("entry_price")
        side = "buy"  # Assuming long-only for now
        
        # Get real quote
        quote = self.broker.get_quote(symbol)
        logger.info(f"Real quote for {symbol}: bid={quote['bid']}, ask={quote['ask']}")
        
        # Calculate position size (from validators or default to 1 share for safety)
        quantity = 1  # Start with 1 share for testing
        
        # Place order
        order = self.broker.place_order(
            symbol=symbol,
            quantity=quantity,
            side=side,
            order_type="limit",
            limit_price=entry_price
        )
        
        # Wait for fill (poll every 2 seconds, max 60 seconds)
        for _ in range(30):
            await asyncio.sleep(2)
            status = self.broker.get_order_status(order['order_id'])
            
            if status['status'] == 'EXECUTED':
                fill = {
                    "symbol": symbol,
                    "quantity": status['filled_quantity'],
                    "side": side,
                    "proposed_price": entry_price,
                    "filled_price": status['average_execution_price'],
                    "filled_at": datetime.utcnow().isoformat(),
                    "slippage": (status['average_execution_price'] - entry_price) / entry_price,
                    "order_id": order['order_id']
                }
                logger.info(f"Order filled: {fill}")
                return fill
            
            elif status['status'] in ['CANCELLED', 'REJECTED']:
                logger.warning(f"Order {status['status']}: {order['order_id']}")
                return None
        
        # Timeout - cancel order
        logger.warning(f"Order timeout, cancelling: {order['order_id']}")
        self.broker.cancel_order(order['order_id'])
        return None


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Live Trading Loop with E*TRADE")
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--interval", type=int, default=300)  # 5 minutes default
    
    args = parser.parse_args()
    
    loop = LiveTradingLoop(
        api_base_url=args.api_url,
        interval_seconds=args.interval
    )
    
    try:
        await loop.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await loop.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

## Testing Sequence

### 1. Test Authentication
```bash
python -c "
from services.broker.etrade_client import ETradeClient
import os

client = ETradeClient(
    consumer_key=os.getenv('ETRADE_CONSUMER_KEY'),
    consumer_secret=os.getenv('ETRADE_CONSUMER_SECRET'),
    sandbox=True
)

if client.authenticate():
    accounts = client.list_accounts()
    print(f'✅ Connected to {len(accounts)} account(s)')
    for acc in accounts:
        print(f"  - {acc['accountDesc']}: {acc['accountIdKey']}")
"
```

### 2. Test Quote Retrieval
```bash
python -c "
from services.broker.etrade_client import ETradeClient
import os

client = ETradeClient(os.getenv('ETRADE_CONSUMER_KEY'), os.getenv('ETRADE_CONSUMER_SECRET'), True)
client.authenticate()
client.list_accounts()

quote = client.get_quote('AAPL')
print(f'AAPL: bid={quote[\"bid\"]}, ask={quote[\"ask\"]}, spread={quote[\"spread\"]:.2f}')
"
```

### 3. Test Order Placement (Sandbox)
```bash
python -c "
from services.broker.etrade_client import ETradeClient
import os

client = ETradeClient(os.getenv('ETRADE_CONSUMER_KEY'), os.getenv('ETRADE_CONSUMER_SECRET'), True)
client.authenticate()
client.list_accounts()

# Place a 1-share limit order (in sandbox, won't execute)
order = client.place_order('AAPL', 1, 'buy', 'limit', 150.00)
print(f'Order placed: {order[\"order_id\"]}')

status = client.get_order_status(order['order_id'])
print(f'Status: {status[\"status\"]}')
"
```

### 4. Run Live Trading Loop
```bash
# Make sure E*TRADE credentials are in .env
python live_trading.py --interval 300
```

## Safety Checklist

Before running with real money:

- [ ] Test extensively in E*TRADE sandbox
- [ ] Start with 1 share per trade
- [ ] Set MAX_TICKET to very low value ($50)
- [ ] Set MAX_PER_TRADE_LOSS to very low ($5)
- [ ] Run for 1 week in sandbox
- [ ] Verify all orders are placed/cancelled correctly
- [ ] Test kill-switch manually (set realized_pnl_today < -75)
- [ ] Monitor for 24 hours before increasing size

## Cost Considerations

- E*TRADE commission: ~$0 for stocks (check your account)
- Market data fees: May apply
- API rate limits: Check E*TRADE docs

## Next Steps

1. Get E*TRADE developer credentials
2. Test authentication
3. Run in sandbox for 1 week
4. Gradually transition to production

Want me to create the E*TRADE client files for you?

