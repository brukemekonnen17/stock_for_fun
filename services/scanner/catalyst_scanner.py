from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Union
from services.marketdata.yf_adapter import YFMarketData
from services.marketdata.service import MarketDataProviderService
from services.analysis.events import get_event_details

@dataclass
class ScanItem:
    ticker: str
    event_type: str
    event_time: datetime
    rank: float
    expected_move: float
    liquidity: float
    spread: float

class CatalystScanner:
    """
    Catalyst scanner that uses market data provider service with fallback chain.
    Accepts either MarketDataProviderService (new) or YFMarketData (legacy).
    """
    def __init__(self, md: Union[MarketDataProviderService, YFMarketData, None] = None):
        # Use provided market data, or create new service (preferred)
        if md is None:
            self.md = MarketDataProviderService()
        else:
            self.md = md

    def scan(self, universe: List[str]) -> List[ScanItem]:
        out: List[ScanItem] = []
        for t in universe:
            try:
                quote = self.md.last_quote(t)
                price = quote["price"]
                spread = self.md.spread_proxy(t)
                # naive liquidity proxy: $vol from 60-day avg volume * price
                hist = self.md.daily_ohlc(t, lookback=60)
                if not hist:
                    continue
                avg_vol = sum([h["volume"] for h in hist[-20:]]) / max(1, len(hist[-20:]))
                dollar_vol = avg_vol * price

                # fake expected move proxy from 5-day close-to-close pct move abs mean
                closes = [h["close"] for h in hist][-10:]
                em = 0.03
                if len(closes) >= 6:
                    rets = [abs((closes[i] - closes[i-5]) / closes[i-5]) for i in range(5, len(closes))]
                    em = sum(rets) / len(rets)

                # Get REAL event details (not hardcoded!)
                event_type, days_to_event = get_event_details(t, self.md)
                event_time = datetime.utcnow() + timedelta(days=days_to_event)

                # naive rank (you'll replace with your CatalystRank)
                rank = max(0.0, min(100.0, 50 + (0.5 - spread / max(0.01, price)) * 100))

                out.append(ScanItem(
                    ticker=t,
                    event_type=event_type,  # Real event type from calendar
                    event_time=event_time,   # Real event time (not hardcoded 7 days!)
                    rank=round(rank, 2),
                    expected_move=round(em, 4),
                    liquidity=float(dollar_vol),
                    spread=float(spread),
                ))
            except Exception as e:
                # Skip tickers that fail (e.g., delisted, bad data)
                import logging
                logging.warning(f"Failed to scan {t}: {e}")
                continue
                
        # Top N by rank
        return sorted(out, key=lambda x: x.rank, reverse=True)[:10]

