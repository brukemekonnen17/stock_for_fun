from pydantic import BaseModel
from typing import Optional

class OrderRequest(BaseModel):
    ticker: str
    side: str            # "BUY" | "SELL"
    qty: int
    type: str            # "market" | "limit"
    limit_price: Optional[float] = None
    tif: str = "DAY"     # "DAY" | "GTC"

class OrderResponse(BaseModel):
    status: str          # "ACCEPTED" | "FILLED" | "REJECTED" | "CANCELED"
    broker_order_id: str | None = None
    avg_px: float | None = None
    message: str = ""

class BrokerInterface:
    def place(self, req: OrderRequest) -> OrderResponse:
        raise NotImplementedError

    def cancel(self, broker_order_id: str) -> OrderResponse:
        raise NotImplementedError

    def positions(self) -> list[dict]:
        raise NotImplementedError

    def account(self) -> dict:
        raise NotImplementedError

