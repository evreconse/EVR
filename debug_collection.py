#!/usr/bin/env python3
"""
Debug collection script to test API response and filter.

Research: Debug why collection failed.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import json
import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


async def test_single_symbol():
    """Test collection for a single symbol."""
    print("=" * 100)
    print("DEBUGGING COLLECTION")
    print("=" * 100)
    
    fetcher = BingXFetcher()
    
    symbol = "BTC-USDT"
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=60)
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    print(f"\nTesting symbol: {symbol}")
    print(f"Time range: {start_time} to {end_time}")
    
    try:
        klines = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            limit=500,
            start_time=start_ms,
            end_time=end_ms
        )
        
        print(f"\nTotal klines received: {len(klines)}")
        
        if klines:
            print(f"\nFirst kline keys: {klines[0].keys()}")
            print(f"\nFirst kline sample: {json.dumps(klines[0], indent=2)}")
            
            # Check distribution of filter values
            body_percents = []
            range_percents = []
            lower_wick_body_ratios = []
            lower_wick_range_ratios = []
            open_to_low_percents = []
            
            for kline in klines:
                open_price = float(kline['open'])
                close_price = float(kline['close'])
                high_price = float(kline['high'])
                low_price = float(kline['low'])
                volume = float(kline['volume'])
                
                body = abs(close_price - open_price)
                lower_wick = min(open_price, close_price) - low_price
                upper_wick = high_price - max(open_price, close_price)
                candle_range = high_price - low_price
                
                if candle_range == 0:
                    continue
                
                body_percent = (body / close_price) * 100
                range_percent = (candle_range / close_price) * 100
                lower_wick_body_ratio = lower_wick / body if body > 0 else 0
                lower_wick_range_ratio = lower_wick / candle_range if candle_range > 0 else 0
                open_to_low_percent = ((low_price - open_price) / open_price) * 100
                
                body_percents.append(body_percent)
                range_percents.append(range_percent)
                lower_wick_body_ratios.append(lower_wick_body_ratio)
                lower_wick_range_ratios.append(lower_wick_range_ratio)
                open_to_low_percents.append(open_to_low_percent)
            
            print(f"\nFilter value distributions:")
            print(f"body_percent: min={min(body_percents):.2f}, max={max(body_percents):.2f}, median={sorted(body_percents)[len(body_percents)//2]:.2f}")
            print(f"range_percent: min={min(range_percents):.2f}, max={max(range_percents):.2f}, median={sorted(range_percents)[len(range_percents)//2]:.2f}")
            print(f"lower_wick_body_ratio: min={min(lower_wick_body_ratios):.2f}, max={max(lower_wick_body_ratios):.2f}, median={sorted(lower_wick_body_ratios)[len(lower_wick_body_ratios)//2]:.2f}")
            print(f"lower_wick_range_ratio: min={min(lower_wick_range_ratios):.2f}, max={max(lower_wick_range_ratios):.2f}, median={sorted(lower_wick_range_ratios)[len(lower_wick_range_ratios)//2]:.2f}")
            print(f"open_to_low_percent: min={min(open_to_low_percents):.2f}, max={max(open_to_low_percents):.2f}, median={sorted(open_to_low_percents)[len(open_to_low_percents)//2]:.2f}")
            
            # Check base filter
            passing_count = 0
            for kline in klines:
                open_price = float(kline['open'])
                close_price = float(kline['close'])
                high_price = float(kline['high'])
                low_price = float(kline['low'])
                volume = float(kline['volume'])
                
                body = abs(close_price - open_price)
                lower_wick = min(open_price, close_price) - low_price
                upper_wick = high_price - max(open_price, close_price)
                candle_range = high_price - low_price
                
                if candle_range == 0:
                    continue
                
                body_percent = (body / close_price) * 100
                range_percent = (candle_range / close_price) * 100
                lower_wick_body_ratio = lower_wick / body if body > 0 else 0
                lower_wick_range_ratio = lower_wick / candle_range if candle_range > 0 else 0
                open_to_low_percent = ((low_price - open_price) / open_price) * 100
                
                conditions = {
                    "body_percent": body_percent >= 0.5,
                    "range_percent": range_percent >= 1.5,
                    "lower_wick_body_ratio": lower_wick_body_ratio >= 0.5,
                    "lower_wick_range_ratio": lower_wick_range_ratio >= 0.3,
                    "open_to_low_percent": open_to_low_percent <= -1.5,
                }
                
                if all(conditions.values()):
                    passing_count += 1
            
            print(f"\nKlines passing base filter: {passing_count}/{len(klines)}")
            
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()


async def main():
    """Main function."""
    await test_single_symbol()


if __name__ == "__main__":
    asyncio.run(main())
