#!/usr/bin/env python3
"""
Re-run the signal finding to see what OHLC values are actually stored.

This will help us understand if the report data was from a different run or if there's a bug.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


def check_lw001_strict(open_price: float, high_price: float, low_price: float, close_price: float) -> tuple[bool, dict]:
    """Check LW-001 conditions."""
    is_red = close_price < open_price
    
    if not is_red:
        return False, {"reason": "Not a red candle"}
    
    if close_price == low_price:
        return False, {"reason": "Close == Low (no lower wick)"}
    
    body = open_price - close_price if is_red else 0.0
    
    if body <= 0:
        return False, {"reason": "Zero or negative body"}
    
    lower_wick = close_price - low_price
    upper_wick = high_price - open_price
    ratio = lower_wick / body
    qualified = ratio >= 2.0
    
    details = {
        "is_red": is_red,
        "body": body,
        "lower_wick": lower_wick,
        "upper_wick": upper_wick,
        "ratio": ratio,
        "qualified": qualified,
    }
    
    return qualified, details


def check_volume_filter(volume: float, previous_volumes: list[float]) -> tuple[bool, dict]:
    """Check volume filter."""
    if not previous_volumes:
        return False, {"reason": "No previous volumes"}
    
    max_previous = max(previous_volumes)
    
    if max_previous <= 0:
        return False, {"reason": "Max previous volume is zero"}
    
    ratio = volume / max_previous
    qualified = ratio >= 1.5
    
    details = {
        "volume": volume,
        "max_previous_volume": max_previous,
        "volume_ratio": ratio,
        "qualified": qualified,
    }
    
    return qualified, details


async def main():
    """Re-run signal finding for FLOW-USDT to see actual stored data."""
    print("=" * 80)
    print("RE-RUNNING SIGNAL FINDING FOR FLOW-USDT")
    print("=" * 80)
    
    fetcher = BingXFetcher()
    
    # The signal was at 10.08.2026 07:15 UTC
    target_time = datetime(2026, 8, 10, 7, 15, tzinfo=UTC)
    start_time = int((target_time - timedelta(hours=2)).timestamp() * 1000)
    end_time = int((target_time + timedelta(hours=2)).timestamp() * 1000)
    
    klines = await fetcher.get_klines(
        symbol="FLOW-USDT",
        interval="15m",
        limit=1000,
        start_time=start_time,
        end_time=end_time
    )
    
    print(f"Fetched {len(klines)} klines")
    
    # Show all klines to debug
    for i, kline in enumerate(klines):
        kline_time = int(kline['time'])
        kline_datetime = datetime.fromtimestamp(kline_time / 1000, tz=UTC)
        
        print(f"\nCandle {i} at {kline_datetime}:")
        print(f"  Open:  {float(kline['open']):.6f}")
        print(f"  High:  {float(kline['high']):.6f}")
        print(f"  Low:   {float(kline['low']):.6f}")
        print(f"  Close: {float(kline['close']):.6f}")
    
    # Find the candle at the exact timestamp
    for i in range(len(klines) - 1, 48, -1):
        kline_time = int(klines[i]['time'])
        kline_datetime = datetime.fromtimestamp(kline_time / 1000, tz=UTC)
        
        if kline_datetime == target_time:
            open_price = float(klines[i]['open'])
            high_price = float(klines[i]['high'])
            low_price = float(klines[i]['low'])
            close_price = float(klines[i]['close'])
            volume = float(klines[i]['volume'])
            timestamp = int(klines[i]['time'])
            
            print(f"\nFound candle at {kline_datetime}")
            print(f"RAW BINGX DATA:")
            print(f"  Open:  {open_price:.6f}")
            print(f"  High:  {high_price:.6f}")
            print(f"  Low:   {low_price:.6f}")
            print(f"  Close: {close_price:.6f}")
            print(f"  Volume: {volume:.0f}")
            
            # Run the same checks as the signal finder
            lw_qualified, lw_details = check_lw001_strict(open_price, high_price, low_price, close_price)
            
            previous_volumes = [float(klines[j]['volume']) for j in range(i - 48, i)]
            vol_qualified, vol_details = check_volume_filter(volume, previous_volumes)
            
            print(f"\nLW-001 CHECK:")
            print(f"  Qualified: {lw_qualified}")
            print(f"  Body: {lw_details['body']:.6f}")
            print(f"  Lower Wick: {lw_details['lower_wick']:.6f}")
            print(f"  Upper Wick: {lw_details['upper_wick']:.6f}")
            print(f"  Ratio: {lw_details['ratio']:.2f}x")
            
            print(f"\nVOLUME CHECK:")
            print(f"  Qualified: {vol_qualified}")
            print(f"  Current Volume: {vol_details['volume']:.0f}")
            print(f"  Max Previous 48: {vol_details['max_previous_volume']:.0f}")
            print(f"  Volume Ratio: {vol_details['volume_ratio']:.2f}x")
            
            print(f"\nSIGNAL DATA THAT WOULD BE STORED:")
            print(f"  open: {open_price:.6f}")
            print(f"  high: {high_price:.6f}")
            print(f"  low: {low_price:.6f}")
            print(f"  close: {close_price:.6f}")
            print(f"  body: {lw_details['body']:.6f}")
            print(f"  lower_wick: {lw_details['lower_wick']:.6f}")
            print(f"  upper_wick: {lw_details['upper_wick']:.6f}")
            print(f"  ratio: {lw_details['ratio']:.2f}")
            
            print(f"\nREPORT DATA (from previous report):")
            print(f"  open: 0.029750")
            print(f"  high: 0.029750")
            print(f"  low: 0.029720")
            print(f"  close: 0.029750")
            print(f"  body: 0.000000")
            print(f"  lower_wick: 0.000030")
            print(f"  upper_wick: 0.000000")
            print(f"  ratio: 3.00")
            
            print(f"\nCONCLUSION:")
            if abs(open_price - 0.029750) < 0.000001:
                print("The stored data matches the report data.")
                print("This means the report was accurate for the run that generated it.")
                print("But BingX now shows different values - possible data update on BingX?")
            else:
                print("The stored data DOES NOT match the report data.")
                print("The report showed wrong values.")
                print("The actual Telegram message would have sent the correct BingX values.")
            
            break


if __name__ == "__main__":
    asyncio.run(main())
