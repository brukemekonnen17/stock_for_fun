"""
Paper Trading Loop
Cron-style loop that cycles: propose → validate → simulate fills → log reward for the bandit
"""
import asyncio
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import httpx
from contextlib import asynccontextmanager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PaperTradingLoop:
    """Paper trading loop that simulates trading cycles for bandit learning."""
    
    def __init__(
        self,
        api_base_url: str = "http://localhost:8000",
        interval_seconds: int = 60,
        fill_delay_seconds: int = 5
    ):
        self.api_base_url = api_base_url
        self.interval_seconds = interval_seconds
        self.fill_delay_seconds = fill_delay_seconds
        self.running = False
        self.client = httpx.AsyncClient(timeout=30.0)
    
    def _generate_mock_proposal_data(self, context: Optional[list] = None) -> Dict[str, Any]:
        """Generate mock data for ProposePayload."""
        import random
        
        if context is None:
            context = [random.random() for _ in range(10)]
        
        return {
            "ticker": "AAPL",
            "price": 150.0 + random.uniform(-5, 5),
            "event_type": random.choice(["EARNINGS", "FDA", "ECONOMIC", "NEWS"]),
            "days_to_event": random.uniform(1, 7),
            "rank_components": {
                "timing": 0.8,
                "catalyst_strength": 0.7,
                "liquidity": 0.9
            },
            "expected_move": random.uniform(0.02, 0.08),
            "backtest_kpis": {
                "win_rate": 0.65,
                "avg_return": 0.04,
                "sharpe": 1.2
            },
            "liquidity": 5_000_000_000,
            "spread": 0.01,
            "news_summary": "Strong earnings expected",
            "context": context
        }
    
    async def propose_trade(self, context: Optional[list] = None) -> Optional[Dict[str, Any]]:
        """Propose a trade using the bandit's recommendation.
        
        Args:
            context: Feature vector (list of numbers). If None, generates a sample context.
        
        Returns:
            Response with selected_arm and plan, or None if error.
        """
        try:
            payload = self._generate_mock_proposal_data(context)
            response = await self.client.post(
                f"{self.api_base_url}/propose",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            # Store context for later use
            result["_context"] = payload["context"]
            
            logger.info(f"Proposed trade - Arm: {result.get('selected_arm')}, Ticker: {payload['ticker']}")
            return result
        except Exception as e:
            logger.error(f"Error proposing trade: {e}")
            return None
    
    async def validate_trade(self, plan: Dict[str, Any]) -> tuple[bool, Dict[str, Any]]:
        """Validate the proposed trade.
        
        Args:
            plan: The trade plan from /propose (TradePlan schema)
        
        Returns:
            Tuple of (is_valid, verdict_details)
        """
        try:
            # Generate market snapshot
            market = {
                "price": plan.get("entry_price", 150.0),
                "spread": 0.01,
                "avg_dollar_vol": 5_000_000
            }
            
            # Generate policy context
            context = {
                "open_positions": 0,
                "realized_pnl_today": 0.0
            }
            
            payload = {
                "plan": plan,
                "market": market,
                "context": context
            }
            
            response = await self.client.post(
                f"{self.api_base_url}/validate",
                json=payload
            )
            response.raise_for_status()
            verdict = response.json()
            
            is_valid = verdict.get("verdict") == "APPROVED"
            logger.info(f"Trade validation: {verdict.get('verdict')} - {verdict.get('reason')}")
            
            return is_valid, verdict
        except Exception as e:
            logger.error(f"Error validating trade: {e}")
            return False, {"verdict": "ERROR", "reason": str(e)}
    
    async def simulate_fill(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate trade fill with realistic delay.
        
        Args:
            plan: The trade plan from /propose
            
        Returns:
            Fill details including price, slippage, etc.
        """
        await asyncio.sleep(self.fill_delay_seconds)
        
        # Extract trade details from plan
        symbol = plan.get("symbol", "")
        quantity = plan.get("quantity", 0)
        side = plan.get("side", "buy")
        proposed_price = plan.get("price", 0)
        
        # Simulate small slippage (0.1% random)
        import random
        slippage_factor = 1 + (random.random() - 0.5) * 0.002
        filled_price = proposed_price * slippage_factor if proposed_price > 0 else 0
        
        fill = {
            "symbol": symbol,
            "quantity": quantity,
            "side": side,
            "proposed_price": proposed_price,
            "filled_price": filled_price,
            "filled_at": datetime.utcnow().isoformat(),
            "slippage": (filled_price - proposed_price) / proposed_price if proposed_price > 0 else 0
        }
        
        logger.info(f"Simulated fill: {symbol} {side} {quantity} @ {filled_price:.2f} (slippage: {fill['slippage']*100:.2f}%)")
        return fill
    
    def _calculate_reward(self, plan: Dict[str, Any], fill: Dict[str, Any]) -> float:
        """Calculate reward in R-multiples (risk units).
        
        Formula:
        - Risk unit (RU) = entry_price - stop_price (for longs)
        - If RU <= 0, return -1.0 (invalid trade setup)
        - Simulate exit after fill and compute P&L in R units
        - Clip to [-1.0, 1.0]
        
        Args:
            plan: Trade plan with entry_price, stop_price, target_price
            fill: Fill details with filled_price
            
        Returns:
            Reward clipped to [-1.0, 1.0]
        """
        entry_price = fill.get("filled_price", plan.get("entry_price", 0))
        stop_price = plan.get("stop_price", 0)
        target_price = plan.get("target_price", entry_price * 1.05)
        side = plan.get("side", "buy")
        
        # Calculate risk unit
        if side == "buy":
            risk_unit = entry_price - stop_price
        else:
            risk_unit = stop_price - entry_price
        
        if risk_unit <= 0:
            logger.warning(f"Invalid risk unit: {risk_unit} (entry={entry_price}, stop={stop_price})")
            return -1.0
        
        # Simulate exit (in paper trading, we'll use a simple heuristic)
        # In production, you'd track actual exit price after timeout or target/stop hit
        # For now, simulate a random outcome biased toward target
        import random
        
        # Simple probability model: 60% chance of reaching target, 40% stop
        hit_target = random.random() < 0.6
        
        if hit_target:
            exit_price = target_price
        else:
            # Simulate partial loss (not always full stop)
            loss_pct = random.uniform(0.5, 1.0)  # 50-100% of stop loss
            if side == "buy":
                exit_price = entry_price - (risk_unit * loss_pct)
            else:
                exit_price = entry_price + (risk_unit * loss_pct)
        
        # Calculate P&L in R-multiples
        if side == "buy":
            pnl = exit_price - entry_price
        else:
            pnl = entry_price - exit_price
        
        r_multiple = pnl / risk_unit
        
        # Clip to [-1.0, 1.0]
        reward = max(-1.0, min(1.0, r_multiple))
        
        logger.debug(f"Reward calc: entry={entry_price:.2f}, stop={stop_price:.2f}, "
                    f"exit={exit_price:.2f}, RU={risk_unit:.2f}, R={r_multiple:.2f}, "
                    f"reward={reward:.2f}")
        
        return reward
    
    async def log_reward(
        self, 
        selected_arm: str, 
        context: list, 
        plan: Dict[str, Any],
        fill: Dict[str, Any],
        reward: Optional[float] = None
    ) -> bool:
        """Log reward for the bandit based on fill performance.
        
        Args:
            selected_arm: The arm name (e.g., "POST_EVENT_MOMO")
            context: The context vector used for proposal
            plan: The trade plan (needed for risk calculation)
            fill: Fill details from simulate_fill
            reward: Pre-calculated reward (if None, will compute R-multiple reward)
        """
        try:
            # Calculate reward based on R-multiples if not provided
            if reward is None:
                reward = self._calculate_reward(plan, fill)
            
            reward_data = {
                "arm_name": selected_arm,
                "context": context,
                "reward": reward
            }
            
            response = await self.client.post(
                f"{self.api_base_url}/bandit/reward",
                json=reward_data
            )
            response.raise_for_status()
            logger.info(f"Logged reward for arm {selected_arm}: {reward:.4f}")
            return True
        except Exception as e:
            logger.error(f"Error logging reward: {e}")
            return False
    
    async def run_cycle(self, context: Optional[list] = None):
        """Run a single trading cycle: propose → validate → simulate → log.
        
        Args:
            context: Optional context vector. If None, will be generated.
        """
        logger.info("=" * 50)
        logger.info("Starting trading cycle")
        logger.info("=" * 50)
        
        # Generate context if not provided
        if context is None:
            import random
            context = [random.random() for _ in range(10)]
        
        # Step 1: Propose
        proposal = await self.propose_trade(context)
        if not proposal:
            logger.warning("No trade proposed, skipping cycle")
            return
        
        selected_arm = proposal.get("selected_arm")
        plan = proposal.get("plan", {})
        context = proposal.get("_context", context)  # Use stored context
        
        if not selected_arm or not plan:
            logger.warning(f"Invalid proposal response: {proposal}")
            return
        
        # Step 2: Validate
        is_valid, verdict = await self.validate_trade(plan)
        if not is_valid:
            logger.warning(f"Trade validation failed for arm {selected_arm}: {verdict.get('reason')}")
            return
        
        # Step 3: Simulate fill
        fill = await self.simulate_fill(plan)
        
        # Step 4: Log reward
        await self.log_reward(selected_arm, context, plan, fill)
        
        logger.info("Trading cycle completed")
    
    async def start(self):
        """Start the paper trading loop."""
        self.running = True
        logger.info(f"Starting paper trading loop (interval: {self.interval_seconds}s)")
        
        while self.running:
            try:
                await self.run_cycle()
            except Exception as e:
                logger.error(f"Error in trading cycle: {e}", exc_info=True)
            
            # Wait for next cycle
            await asyncio.sleep(self.interval_seconds)
    
    async def stop(self):
        """Stop the paper trading loop."""
        logger.info("Stopping paper trading loop")
        self.running = False
        await self.client.aclose()
    
    @asynccontextmanager
    async def run(self):
        """Context manager for running the loop."""
        try:
            await self.start()
            yield
        finally:
            await self.stop()


async def main():
    """Main entry point for the paper trading loop."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Paper Trading Loop")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Base URL for the API"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Interval between cycles in seconds"
    )
    parser.add_argument(
        "--fill-delay",
        type=int,
        default=5,
        help="Delay for simulating fills in seconds"
    )
    
    args = parser.parse_args()
    
    loop = PaperTradingLoop(
        api_base_url=args.api_url,
        interval_seconds=args.interval,
        fill_delay_seconds=args.fill_delay
    )
    
    try:
        await loop.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await loop.stop()


if __name__ == "__main__":
    asyncio.run(main())

