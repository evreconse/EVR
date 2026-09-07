"""
Test LW-001 logic after migration to D: drive
Tests the 4 critical cases specified in requirements
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from datetime import UTC, datetime
from strategy.lw_001 import LW001Strategy
from strategy.context import StrategyContext, StrategyConfig, StrategyResult
from models.market_event import MarketEvent

async def test_case(name, open_p, close_p, low_p, high_p, expected_qualified, expected_ratio=None):
    """Test a single candle case."""
    print("=" * 80)
    print(f"TEST CASE: {name}")
    print("=" * 80)
    print(f"Open:  {open_p}")
    print(f"Close: {close_p}")
    print(f"Low:   {low_p}")
    print(f"High:  {high_p}")
    print()
    
    # Check if red
    is_red = close_p < open_p
    print(f"RED: {'YES' if is_red else 'NO'}")
    print()
    
    # Calculate body
    body = abs(close_p - open_p)
    print(f"Body: {body}")
    
    # Calculate lower wick (for red candles: Close - Low)
    lower_wick = close_p - low_p
    print(f"Lower Wick: {lower_wick}")
    
    # Calculate upper wick
    upper_wick = high_p - max(open_p, close_p)
    print(f"Upper Wick: {upper_wick}")
    print()
    
    # Calculate ratio
    if body > 0:
        ratio = lower_wick / body
        print(f"Lower Wick / Body: {ratio:.2f}x")
    else:
        ratio = 0.0
        print(f"Lower Wick / Body: N/A (body = 0)")
    print()
    
    # Expected result
    print(f"Expected Qualified: {'YES' if expected_qualified else 'NO'}")
    if expected_ratio is not None:
        print(f"Expected Ratio: {expected_ratio:.2f}x")
    print()
    
    # Test with actual strategy
    try:
        # Create strategy
        strategy = LW001Strategy()
        
        # Create config
        config = StrategyConfig(
            strategy_id="lw_001",
            parameters={
                "lower_wick_ratio": 2.0,
                "scoring": {
                    "lower_wick_weight": 70,
                    "confirmation_weight": 30,
                    "wick_tier_3x": 70,
                    "wick_tier_2_5x": 60,
                    "wick_tier_2x": 50,
                    "wick_tier_1_5x": 35,
                    "wick_tier_1x": 20,
                    "wick_tier_doji": 25,
                    "confirm_tier_bull_0_6": 30,
                    "confirm_tier_bear_0_4": 30,
                    "confirm_tier_neutral": 15,
                }
            }
        )
        
        # Create context
        context = StrategyContext(config=config)
        
        # Create market event with OHLC data
        market_event = MarketEvent.new(
            symbol="TESTUSDT",
            exchange=Exchange.BINGX,
            timeframe=Timeframe.M15,
            timestamp=datetime.now(UTC),
            open=open_p,
            high=high_p,
            low=low_p,
            close=close_p,
            volume=1000.0
        )
        
        # Evaluate
        result = await strategy.evaluate(market_event, context)
        
        print(f"Actual Qualified: {'YES' if result.qualified else 'NO'}")
        print(f"Actual Score: {result.final_score}")
        print()
        
        # Check result
        if result.qualified == expected_qualified:
            print("[+] TEST PASSED")
        else:
            print(f"[-] TEST FAILED: Expected {expected_qualified}, got {result.qualified}")
        
        if expected_ratio is not None:
            if abs(ratio - expected_ratio) < 0.01:
                print("[+] RATIO CORRECT")
            else:
                print(f"[-] RATIO INCORRECT: Expected {expected_ratio:.2f}x, got {ratio:.2f}x")
        
        print()
        
    except Exception as e:
        print(f"[ERROR] Strategy evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        print()
    
    print("=" * 80)
    print()

async def main():
    print("=" * 80)
    print("Testing LW-001 Logic from new location D:\\EVRECONSE_PROJECT")
    print("=" * 80)
    print()
    
    print(f"Python executable: {sys.executable}")
    print()
    
    # Case A: Red candle with lower wick >= 2x body - should PASS
    await test_case(
        name="Case A - Red candle, Lower Wick >= 2x Body",
        open_p=110,
        close_p=100,
        low_p=75,
        high_p=115,
        expected_qualified=True,
        expected_ratio=2.5
    )
    
    # Case B: Red candle with lower wick < 2x body - should FAIL
    await test_case(
        name="Case B - Red candle, Lower Wick < 2x Body",
        open_p=110,
        close_p=100,
        low_p=85,
        high_p=115,
        expected_qualified=False,
        expected_ratio=1.5
    )
    
    # Case C: Green candle - should FAIL regardless of wick size
    await test_case(
        name="Case C - Green candle (should FAIL)",
        open_p=100,
        close_p=110,
        low_p=75,
        high_p=115,
        expected_qualified=False,
        expected_ratio=None  # Not applicable for green candles
    )
    
    # Case D1: Red candle with small upper wick
    await test_case(
        name="Case D1 - Red candle, Small Upper Wick",
        open_p=110,
        close_p=100,
        low_p=75,
        high_p=112,
        expected_qualified=True,
        expected_ratio=2.5
    )
    
    # Case D2: Red candle with large upper wick (same Open, Close, Low)
    await test_case(
        name="Case D2 - Red candle, Large Upper Wick (same O/C/L)",
        open_p=110,
        close_p=100,
        low_p=75,
        high_p=150,
        expected_qualified=True,
        expected_ratio=2.5
    )
    
    print("=" * 80)
    print("LW-001 LOGIC TEST COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
