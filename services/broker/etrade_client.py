import os, time, urllib.parse, logging
from typing import Optional
import requests
from requests_oauthlib import OAuth1
from pydantic import BaseModel
from .base import BrokerInterface, OrderRequest, OrderResponse

log = logging.getLogger(__name__)

ETRADE_SANDBOX = "https://apisb.etrade.com"
ETRADE_LIVE    = "https://api.etrade.com"

class ETradeConfig(BaseModel):
    consumer_key: str
    consumer_secret: str
    access_token: str
    access_token_secret: str
    account_id_key: str
    sandbox: bool = True

class ETradeClient(BrokerInterface):
    def __init__(self, cfg: ETradeConfig):
        self.cfg = cfg
        base = ETRADE_SANDBOX if cfg.sandbox else ETRADE_LIVE
        self.base = base
        self.oauth = OAuth1(
            client_key=cfg.consumer_key,
            client_secret=cfg.consumer_secret,
            resource_owner_key=cfg.access_token,
            resource_owner_secret=cfg.access_token_secret,
            signature_type="auth_header",
        )

    # --- Helpers
    def _url(self, path: str) -> str:
        return f"{self.base}{path}"

    def _get(self, path: str, params: dict | None = None):
        r = requests.get(self._url(path), params=params or {}, auth=self.oauth, timeout=15)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, json: dict):
        r = requests.post(self._url(path), json=json, auth=self.oauth, timeout=15)
        r.raise_for_status()
        return r.json()

    # --- BrokerInterface
    def account(self) -> dict:
        # Accounts list
        data = self._get("/v1/accounts/list.json")
        return data

    def positions(self) -> list[dict]:
        # Positions for the configured account
        aid = urllib.parse.quote(self.cfg.account_id_key)
        data = self._get(f"/v1/accounts/{aid}/portfolio.json", params={"count": 200})
        # normalize a bit
        out = []
        for acct in data.get("PortfolioResponse", {}).get("AccountPortfolio", []):
            for pos in acct.get("Position", []):
                out.append({
                    "symbol": pos.get("symbolDescription") or pos.get("Product", {}).get("symbol"),
                    "qty": pos.get("quantity"),
                    "price": pos.get("pricePaid"),
                    "market_value": pos.get("marketValue"),
                })
        return out

    def place(self, req: OrderRequest) -> OrderResponse:
        aid = urllib.parse.quote(self.cfg.account_id_key)
        order = {
            "PlaceEquityOrder": {
                "orderType": "EQ",
                "clientOrderId": f"cs-{int(time.time()*1000)}",
                "Order": [{
                    "allOrNone": False,
                    "priceType": "MARKET" if req.type.lower()=="market" else "LIMIT",
                    "limitPrice": req.limit_price if req.type.lower()=="limit" else None,
                    "orderTerm": req.tif.upper(),   # DAY/GTC
                    "marketSession": "REG",
                    "stopPrice": None,
                    "instrument": [{
                        "symbolDescription": req.ticker,
                        "orderAction": "BUY" if req.side.upper()=="BUY" else "SELL",
                        "quantityType": "QUANTITY",
                        "quantity": req.qty,
                        "Product": { "securityType": "EQ", "symbol": req.ticker }
                    }]
                }]
            }
        }
        # E*TRADE expects null fields sometimes removed:
        if order["PlaceEquityOrder"]["Order"][0]["limitPrice"] is None:
            order["PlaceEquityOrder"]["Order"][0].pop("limitPrice")

        resp = self._post(f"/v1/accounts/{aid}/orders/place.json", order)
        pr = resp.get("PlaceOrderResponse", {})
        status = pr.get("orderStatus", "ACCEPTED")
        oid = pr.get("orderId")
        avg_px = None  # follow-up call needed to get fills; keep None for now
        return OrderResponse(status=status, broker_order_id=str(oid) if oid else None, avg_px=avg_px, message=str(pr))

    def cancel(self, broker_order_id: str) -> OrderResponse:
        aid = urllib.parse.quote(self.cfg.account_id_key)
        resp = self._post(f"/v1/accounts/{aid}/orders/cancel.json", {
            "CancelOrderRequest": { "orderId": int(broker_order_id) }
        })
        status = resp.get("CancelOrderResponse", {}).get("orderStatus", "CANCELED")
        return OrderResponse(status=status, broker_order_id=broker_order_id, message=str(resp))

