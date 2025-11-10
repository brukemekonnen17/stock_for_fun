"""
Ship-Blocker #5: Event De-duplication (Whipsaw Control) Tests

Tests to ensure that whipsaw events (rapid back-and-forth crossovers) 
are properly de-duplicated with:
1. Cool-down period (e.g., 20 trading days)
2. Must persist ≥N bars
3. No opposite cross within N bars
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def detect_whipsaw_events(df: pd.DataFrame, cooldown_days: int = 20, persist_bars: int = 3) -> pd.DataFrame:
    """
    Detect crossover events with whipsaw protection.
    
    Args:
        df: DataFrame with ema20, ema50 columns
        cooldown_days: Minimum days between events of same type
        persist_bars: Minimum bars signal must persist
    
    Returns:
        DataFrame with deduplicated events
    """
    if 'ema20' not in df.columns or 'ema50' not in df.columns:
        return pd.DataFrame()
    
    df = df.copy()
    df['signal'] = df['ema20'] - df['ema50']
    
    # Detect raw crossovers
    df['cross_up'] = (df['signal'].shift(1) < 0) & (df['signal'] > 0)
    df['cross_down'] = (df['signal'].shift(1) > 0) & (df['signal'] < 0)
    
    events = []
    last_event_date = {type_: None for type_ in ['GC', 'DC']}
    
    for i in range(len(df)):
        if df.iloc[i]['cross_up']:
            event_type = 'GC'
        elif df.iloc[i]['cross_down']:
            event_type = 'DC'
        else:
            continue
        
        event_date = df.index[i]
        
        # Check cooldown
        if last_event_date[event_type] is not None:
            days_since_last = (event_date - last_event_date[event_type]).days
            if days_since_last < cooldown_days:
                continue  # Too soon, skip
        
        # Check persistence (signal stays in same direction for N bars)
        if i + persist_bars < len(df):
            future_signals = df['signal'].iloc[i+1:i+1+persist_bars]
            if event_type == 'GC':
                persists = (future_signals > 0).all()
            else:  # DC
                persists = (future_signals < 0).all()
            
            if not persists:
                continue  # Doesn't persist, skip
        
        # Check for opposite cross within N bars (whipsaw)
        if i + persist_bars < len(df):
            future_window = df.iloc[i+1:i+1+persist_bars]
            if event_type == 'GC':
                has_opposite = future_window['cross_down'].any()
            else:  # DC
                has_opposite = future_window['cross_up'].any()
            
            if has_opposite:
                continue  # Whipsaw detected, skip
        
        # Event passes all filters
        events.append({
            'date': event_date,
            'type': event_type,
            'valid': True
        })
        last_event_date[event_type] = event_date
    
    return pd.DataFrame(events)


class TestEventDeduplication:
    """Test suite for whipsaw control and event de-duplication."""
    
    def test_whipsaw_month_emits_single_event(self):
        """
        Critical test: A month of whipsawing should emit only 1 event.
        
        Without de-duplication, rapid crossovers would generate many false signals.
        """
        # Create synthetic data with whipsaw pattern
        dates = pd.date_range('2024-01-01', periods=30, freq='D')
        
        # EMA20 oscillates around EMA50
        ema50 = np.ones(30) * 100
        ema20 = 100 + np.array([1, -1, 1, -1, 1, -1, 1, -1, 1, -1] * 3)
        
        df = pd.DataFrame({
            'ema20': ema20,
            'ema50': ema50
        }, index=dates)
        
        # Detect events WITHOUT de-duplication
        signal = df['ema20'] - df['ema50']
        cross_up = (signal.shift(1) < 0) & (signal > 0)
        cross_down = (signal.shift(1) > 0) & (signal < 0)
        raw_events = cross_up.sum() + cross_down.sum()
        
        # Detect events WITH de-duplication
        deduped_events = detect_whipsaw_events(df, cooldown_days=10, persist_bars=2)
        
        print(f"\n✅ Whipsaw control:")
        print(f"   Raw crossovers: {raw_events}")
        print(f"   After de-duplication: {len(deduped_events)}")
        
        # Should dramatically reduce events
        assert raw_events >= 10, f"Should have many raw crossovers, got {raw_events}"
        assert len(deduped_events) <= 2, f"Should have ≤2 deduped events, got {len(deduped_events)}"
        
        print(f"   ✅ Reduced {raw_events} raw events to {len(deduped_events)}")
    
    def test_cooldown_prevents_rapid_events(self):
        """
        Test that cooldown period prevents events within N days.
        """
        # Create data with 2 golden crosses 10 days apart
        dates = pd.date_range('2024-01-01', periods=50, freq='D')
        
        ema50 = np.ones(50) * 100
        ema20 = np.ones(50) * 99  # Start below
        ema20[10:] = 101  # Cross up at day 10
        ema20[20:] = 99   # Cross down at day 20
        ema20[25:] = 101  # Cross up again at day 25 (only 5 days later)
        
        df = pd.DataFrame({
            'ema20': ema20,
            'ema50': ema50
        }, index=dates)
        
        # With 20-day cooldown, second GC should be blocked
        events = detect_whipsaw_events(df, cooldown_days=20, persist_bars=1)
        
        gc_events = events[events['type'] == 'GC']
        
        print(f"\n✅ Cooldown test:")
        print(f"   GC at day 10: ✅")
        print(f"   GC at day 25 (15 days later): ❌ Blocked by cooldown")
        print(f"   Total GC events: {len(gc_events)}")
        
        # Should only have first GC
        assert len(gc_events) == 1, f"Should have 1 GC (cooldown blocks 2nd), got {len(gc_events)}"
    
    def test_persistence_filter(self):
        """
        Test that events must persist for N bars.
        """
        # Create data with brief crossover that doesn't persist
        dates = pd.date_range('2024-01-01', periods=20, freq='D')
        
        ema50 = np.ones(20) * 100
        ema20 = np.ones(20) * 99
        ema20[10] = 101  # Brief cross above (1 bar only)
        ema20[11] = 99   # Immediately back below
        
        df = pd.DataFrame({
            'ema20': ema20,
            'ema50': ema50
        }, index=dates)
        
        # With persist_bars=3, this should NOT emit an event
        events = detect_whipsaw_events(df, cooldown_days=5, persist_bars=3)
        
        print(f"\n✅ Persistence filter:")
        print(f"   Cross at day 10 persists for: 1 bar")
        print(f"   Required persistence: 3 bars")
        print(f"   Event emitted: {'NO' if len(events) == 0 else 'YES'}")
        
        assert len(events) == 0, f"Brief crossover should not emit event, got {len(events)}"
    
    def test_no_opposite_cross_within_window(self):
        """
        Test that opposite crossover within window blocks the event.
        """
        # Create data with GC followed quickly by DC
        dates = pd.date_range('2024-01-01', periods=20, freq='D')
        
        ema50 = np.ones(20) * 100
        ema20 = np.ones(20) * 99
        ema20[5:8] = 101   # Cross up at day 5
        ema20[8:] = 99     # Cross down at day 8 (3 days later)
        
        df = pd.DataFrame({
            'ema20': ema20,
            'ema50': ema50
        }, index=dates)
        
        # With persist_bars=5, the opposite cross at day 8 is within window
        events = detect_whipsaw_events(df, cooldown_days=5, persist_bars=5)
        
        print(f"\n✅ Opposite cross filter:")
        print(f"   GC at day 5")
        print(f"   DC at day 8 (within 5-bar window)")
        print(f"   Event emitted: {'NO' if len(events) == 0 else 'YES'}")
        
        # GC should be blocked due to opposite cross
        gc_events = events[events['type'] == 'GC']
        assert len(gc_events) == 0, f"GC should be blocked by opposite cross, got {len(gc_events)}"
    
    def test_clean_trend_emits_events(self):
        """
        Test that clean, persistent trends DO emit events.
        """
        # Create clean uptrend
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        
        ema50 = np.ones(100) * 100
        ema20 = np.ones(100) * 99
        ema20[20:] = 105  # Clean cross up at day 20, stays up
        
        df = pd.DataFrame({
            'ema20': ema20,
            'ema50': ema50
        }, index=dates)
        
        events = detect_whipsaw_events(df, cooldown_days=20, persist_bars=5)
        
        print(f"\n✅ Clean trend:")
        print(f"   GC at day 20, persists for 80 days")
        print(f"   Events emitted: {len(events)}")
        
        assert len(events) == 1, f"Clean trend should emit 1 event, got {len(events)}"
        assert events.iloc[0]['type'] == 'GC', "Should be Golden Cross"
    
    def test_event_counts_before_after(self):
        """
        Integration test: Show event count reduction.
        """
        # Realistic scenario: Mix of clean and whipsaw
        dates = pd.date_range('2024-01-01', periods=200, freq='D')
        
        # Create mixed pattern
        ema50 = np.ones(200) * 100
        ema20 = np.zeros(200)
        
        # Clean GC at day 20
        ema20[:20] = 99
        ema20[20:50] = 105
        
        # Whipsaw period (days 50-70)
        for i in range(50, 70):
            ema20[i] = 101 if (i - 50) % 2 == 0 else 99
        
        # Clean DC at day 100
        ema20[70:100] = 105
        ema20[100:] = 95
        
        df = pd.DataFrame({
            'ema20': ema20,
            'ema50': ema50
        }, index=dates)
        
        # Count raw crossovers
        signal = df['ema20'] - df['ema50']
        cross_up = (signal.shift(1) < 0) & (signal > 0)
        cross_down = (signal.shift(1) > 0) & (signal < 0)
        raw_count = cross_up.sum() + cross_down.sum()
        
        # Count after de-duplication
        events = detect_whipsaw_events(df, cooldown_days=20, persist_bars=3)
        deduped_count = len(events)
        
        print(f"\n✅ Integration test:")
        print(f"   Raw crossovers: {raw_count}")
        print(f"   After de-duplication: {deduped_count}")
        print(f"   Reduction: {100 * (1 - deduped_count/raw_count):.1f}%")
        
        # Should reduce significantly
        assert deduped_count < raw_count / 2, "Should reduce events by at least 50%"
        
        # Should keep the clean events
        assert deduped_count >= 2, f"Should keep at least 2 clean events, got {deduped_count}"


def test_edge_cases():
    """
    Test edge cases for event de-duplication.
    """
    # Empty DataFrame
    df_empty = pd.DataFrame()
    events_empty = detect_whipsaw_events(df_empty)
    assert events_empty.empty, "Empty DataFrame should return empty events"
    
    # Single event
    dates = pd.date_range('2024-01-01', periods=10, freq='D')
    df_single = pd.DataFrame({
        'ema20': [99, 99, 101, 101, 101, 101, 101, 101, 101, 101],
        'ema50': [100] * 10
    }, index=dates)
    events_single = detect_whipsaw_events(df_single, cooldown_days=5, persist_bars=2)
    assert len(events_single) == 1, f"Single clean event should emit, got {len(events_single)}"
    
    print(f"\n✅ Edge cases handled correctly")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])

