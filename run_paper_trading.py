#!/usr/bin/env python3
"""
Minimal paper trading script that hits the API endpoints directly.
Run this to test the paper trading loop immediately.
"""
import asyncio
import httpx
import json
import random
from typing import Dict, Any


async def run_single_cycle(api_url: str = "http://localhost:8000"):
    """Run a single paper trading cycle."""
    client = httpx.AsyncClient(timeout=30.0)
    
    try:
        print("=" * 60)
        print("PAPER TRADING CYCLE")
        print("=" * 60)
        
        # Step 1: Generate context and propose
        print("\n[1/4] Proposing trade...")
        context = [random.random() for _ in range(10)]
        print(f"   Context vector (10 features): {[f'{x:.3f}' for x in context[:5]]}...")
        
        # Create full ProposePayload
        payload = {
            "ticker": "AAPL",
            "price": 150.0 + random.uniform(-5, 5),
            "event_type": "EARNINGS",
            "days_to_event": 3.5,
            "rank_components": {
                "timing": 0.8,
                "catalyst_strength": 0.7,
                "liquidity": 0.9
            },
            "expected_move": 0.04,
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
        
        response = await client.post(
            f"{api_url}/propose",
            json=payload
        )
        response.raise_for_status()
        proposal = response.json()
        
        selected_arm = proposal.get("selected_arm")
        plan = proposal.get("plan", {})
        print(f"   ✅ Selected arm: {selected_arm}")
        print(f"   ✅ Plan received: {len(plan)} keys")
        
        # Step 2: Validate
        print("\n[2/4] Validating trade...")
        
        # Build validation payload
        market_snapshot = {
            "price": plan.get("entry_price", 150.0),
            "spread": 0.01,
            "avg_dollar_vol": 5_000_000
        }
        
        policy_context = {
            "open_positions": 0,
            "realized_pnl_today": 0.0
        }
        
        response = await client.post(
            f"{api_url}/validate",
            json={
                "plan": plan,
                "market": market_snapshot,
                "context": policy_context
            }
        )
        response.raise_for_status()
        verdict = response.json()
        
        is_approved = verdict.get("verdict") == "APPROVED"
        if is_approved:
            print(f"   ✅ Trade approved: {verdict.get('reason')}")
            print(f"   ✅ Adjusted size: {verdict.get('adjusted_size')} shares")
        else:
            print(f"   ❌ Trade rejected: {verdict.get('reason')}")
            return
        
        # Step 3: Simulate fill (simplified - no actual delay)
        print("\n[3/4] Simulating fill...")
        symbol = plan.get("symbol", "UNKNOWN")
        price = plan.get("price", 0)
        
        # Simulate slippage
        slippage_factor = 1 + (random.random() - 0.5) * 0.002
        filled_price = price * slippage_factor
        slippage = (filled_price - price) / price if price > 0 else 0
        
        print(f"   ✅ Fill: {symbol} @ ${filled_price:.2f} (slippage: {slippage*100:.2f}%)")
        
        # Step 4: Log reward
        print("\n[4/4] Logging reward...")
        # Simple reward calculation based on slippage
        reward = -abs(slippage) * 10
        
        response = await client.post(
            f"{api_url}/bandit/reward",
            json={
                "arm_name": selected_arm,
                "context": context,
                "reward": reward
            }
        )
        response.raise_for_status()
        print(f"   ✅ Reward logged: {reward:.4f}")
        
        print("\n" + "=" * 60)
        print("CYCLE COMPLETED SUCCESSFULLY")
        print("=" * 60)
        
    except httpx.HTTPStatusError as e:
        print(f"\n❌ HTTP Error: {e.response.status_code}")
        print(f"   Response: {e.response.text}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.aclose()


async def main():
    """Run a single cycle."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run single paper trading cycle")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Base URL for the API"
    )
    
    args = parser.parse_args()
    await run_single_cycle(args.api_url)


if __name__ == "__main__":
    asyncio.run(main())


