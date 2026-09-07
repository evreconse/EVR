#!/usr/bin/env python3
"""
Unit tests for LW-001 qualification logic.

Tests the exact qualification formula:
qualified = (Close < Open) AND ((Close - Low) / (Open - Close) >= 2.0)
"""

import sys
from pathlib import Path
from datetime import UTC, datetime
from dataclasses import dataclass, replace

sys.path.insert(0, str(Path(__file__).parent / "src"))

from models.enums import Exchange, Timeframe
from models.market_event import MarketEvent, MarketData, StrategyData
from strategy.lw_001 import LW001Strategy
from strategy.context import StrategyConfig, StrategyContext


@dataclass
class TestCase:
    """Test case for LW-001 qualification."""
    name: str
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    expected_qualified: bool
    description: str


def create_strategy_context(open_price, high_price, low_price, close_price):
    """Create a strategy context for testing."""
    # Create market event using the correct factory method
    market_event = MarketEvent.new(
        symbol="TEST-USDT",
        exchange=Exchange.BINGX,
        timeframe=Timeframe.M15,
        event_time=datetime.now(UTC),
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
        volume=1000.0,
    )
    
    # Update strategy_data to mark candle as confirmed/closed
    market_event = replace(
        market_event,
        strategy_data=StrategyData(
            strategy_id="LW-001",
            lower_wick=0.0,
            body=0.0,
            wick_body_ratio=0.0,
            lower_wick_pct=0.0,
            body_pct=0.0,
            confirm=True,  # Candle is closed
        )
    )
    
    # Create strategy config
    config = StrategyConfig(
        strategy_id="LW-001",
        parameters={
            "lower_wick_ratio": 2.0,
            "scoring": {
                "lower_wick_weight": 70,
                "confirmation_weight": 30,
            }
        }
    )
    
    # Create strategy context
    context = StrategyContext(
        market_event=market_event,
        config=config,
    )
    
    return context


def calculate_manual_qualification(open_price, high_price, low_price, close_price):
    """Manually calculate qualification using the exact formula."""
    is_red = close_price < open_price
    
    if is_red:
        body = open_price - close_price
        lower_wick = close_price - low_price
    else:
        body = close_price - open_price
        lower_wick = open_price - low_price
    
    if body > 0:
        ratio = lower_wick / body
    else:
        ratio = 0.0
    
    qualified = is_red and ratio >= 2.0
    
    return {
        "is_red": is_red,
        "body": body,
        "lower_wick": lower_wick,
        "upper_wick": high_price - max(open_price, close_price),
        "ratio": ratio,
        "qualified": qualified
    }


def run_test(test_case: TestCase, strategy: LW001Strategy):
    """Run a single test case."""
    print(f"\n{'='*80}")
    print(f"TEST: {test_case.name}")
    print(f"Description: {test_case.description}")
    print(f"{'='*80}")
    
    # Manual calculation
    manual = calculate_manual_qualification(
        test_case.open_price,
        test_case.high_price,
        test_case.low_price,
        test_case.close_price
    )
    
    print(f"\nManual Calculation:")
    print(f"  Open: {test_case.open_price}")
    print(f"  High: {test_case.high_price}")
    print(f"  Low: {test_case.low_price}")
    print(f"  Close: {test_case.close_price}")
    print(f"  Red Candle (Close < Open): {manual['is_red']}")
    print(f"  Body: {manual['body']}")
    print(f"  Lower Wick: {manual['lower_wick']}")
    print(f"  Upper Wick: {manual['upper_wick']}")
    print(f"  Lower Wick / Body: {manual['ratio']:.2f}x")
    print(f"  Expected Qualified: {test_case.expected_qualified}")
    print(f"  Manual Qualified: {manual['qualified']}")
    
    # Strategy evaluation
    context = create_strategy_context(
        test_case.open_price,
        test_case.high_price,
        test_case.low_price,
        test_case.close_price
    )
    
    result = strategy.evaluate(context)
    
    print(f"\nStrategy Evaluation:")
    print(f"  Strategy Qualified: {result.qualified}")
    print(f"  Strategy Score: {result.final_score}")
    print(f"  Explanation: {result.explanation}")
    
    # Verify
    test_passed = (result.qualified == test_case.expected_qualified)
    manual_passed = (manual['qualified'] == test_case.expected_qualified)
    
    print(f"\nTest Result:")
    print(f"  Manual matches expected: {manual_passed}")
    print(f"  Strategy matches expected: {test_passed}")
    print(f"  Overall: {'PASS' if test_passed else 'FAIL'}")
    
    return test_passed


async def main():
    """Run all unit tests."""
    print("="*80)
    print("LW-001 QUALIFICATION UNIT TESTS")
    print("="*80)
    print("\nTesting formula: qualified = (Close < Open) AND ((Close - Low) / (Open - Close) >= 2.0)")
    
    # Initialize strategy
    strategy = LW001Strategy()
    config = StrategyConfig(
        strategy_id="LW-001",
        parameters={
            "lower_wick_ratio": 2.0,
            "scoring": {
                "lower_wick_weight": 70,
                "confirmation_weight": 30,
            }
        }
    )
    strategy.initialize(config)
    
    # Test cases
    test_cases = [
        TestCase(
            name="Test 1 - Should PASS (basic hammer)",
            open_price=100.0,
            high_price=101.0,
            low_price=97.0,
            close_price=99.0,
            expected_qualified=True,
            description="Red candle with lower wick exactly 2x body"
        ),
        TestCase(
            name="Test 2 - Should FAIL (insufficient lower wick)",
            open_price=100.0,
            high_price=101.0,
            low_price=98.0,
            close_price=99.0,
            expected_qualified=False,
            description="Red candle with lower wick only 1x body"
        ),
        TestCase(
            name="Test 3 - Should PASS (huge upper wick ignored)",
            open_price=100.0,
            high_price=150.0,
            low_price=97.0,
            close_price=99.0,
            expected_qualified=True,
            description="Red candle with huge upper wick - should PASS because upper wick is ignored"
        ),
        TestCase(
            name="Test 4 - Should FAIL (green candle)",
            open_price=99.0,
            high_price=101.0,
            low_price=97.0,
            close_price=100.0,
            expected_qualified=False,
            description="Green candle - should FAIL regardless of lower wick"
        ),
        TestCase(
            name="Test 5 - Should PASS (strong hammer)",
            open_price=100.0,
            high_price=102.0,
            low_price=95.0,
            close_price=98.0,
            expected_qualified=True,
            description="Red candle with lower wick 3x body"
        ),
        TestCase(
            name="Test 6 - Should FAIL (doji - no body)",
            open_price=100.0,
            high_price=101.0,
            low_price=99.0,
            close_price=100.0,
            expected_qualified=False,
            description="Doji with no body - should FAIL"
        ),
    ]
    
    results = []
    for test_case in test_cases:
        passed = run_test(test_case, strategy)
        results.append((test_case.name, passed))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED")
    else:
        print(f"\n❌ {total - passed} TEST(S) FAILED")
    
    await strategy.shutdown()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
