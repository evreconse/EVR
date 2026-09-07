#!/usr/bin/env python3
"""
Deep diagnostic for FLOW-USDT signal.

Shows the complete data chain from BingX API to qualification.
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta
import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


def check_lw001_strict(open_price: float, high_price: float, low_price: float, close_price: float) -> dict:
    """Check LW-001 conditions - exact formula."""
    is_red = close_price < open_price
    
    if not is_red:
        return {
            "qualified": False,
            "reason": "Not a red candle",
            "is_red": is_red,
            "body": None,
            "lower_wick": None,
            "upper_wick": None,
            "ratio": None,
        }
    
    if close_price == low_price:
        return {
            "qualified": False,
            "reason": "Close == Low (no lower wick)",
            "is_red": is_red,
            "body": None,
            "lower_wick": None,
            "upper_wick": None,
            "ratio": None,
        }
    
    body = open_price - close_price if is_red else 0.0
    
    if body <= 0:
        return {
            "qualified": False,
            "reason": "Zero or negative body",
            "is_red": is_red,
            "body": body,
            "lower_wick": None,
            "upper_wick": None,
            "ratio": None,
        }
    
    lower_wick = close_price - low_price
    upper_wick = high_price - open_price
    ratio = lower_wick / body
    qualified = ratio >= 2.0
    
    return {
        "qualified": qualified,
        "reason": "Qualified" if qualified else "Lower Wick < 2 * Body",
        "is_red": is_red,
        "body": body,
        "lower_wick": lower_wick,
        "upper_wick": upper_wick,
        "ratio": ratio,
    }


def check_volume_filter(volume: float, previous_volumes: list[float]) -> dict:
    """Check volume filter."""
    if not previous_volumes:
        return {
            "qualified": False,
            "reason": "No previous volumes",
            "volume": volume,
            "max_previous_volume": None,
            "volume_ratio": None,
        }
    
    max_previous = max(previous_volumes)
    
    if max_previous <= 0:
        return {
            "qualified": False,
            "reason": "Max previous volume is zero",
            "volume": volume,
            "max_previous_volume": max_previous,
            "volume_ratio": None,
        }
    
    ratio = volume / max_previous
    qualified = ratio >= 1.5
    
    return {
        "qualified": qualified,
        "reason": "Qualified" if qualified else "Volume < 1.5x max previous",
        "volume": volume,
        "max_previous_volume": max_previous,
        "volume_ratio": ratio,
    }


async def main():
    """Deep diagnostic of FLOW-USDT signal."""
    print("=" * 80)
    print("DEEP DIAGNOSTIC: FLOW-USDT SIGNAL")
    print("=" * 80)
    
    fetcher = BingXFetcher()
    
    # The signal was at 10.08.2026 07:15 UTC
    target_time = datetime(2026, 8, 10, 7, 15, tzinfo=UTC)
    target_timestamp_ms = int(target_time.timestamp() * 1000)
    
    print(f"\nTARGET TIME:")
    print(f"  UTC: {target_time}")
    print(f"  MSK: {target_time.replace(hour=(target_time.hour + 3) % 24)}")
    print(f"  Timestamp (ms): {target_timestamp_ms}")
    
    # Fetch klines around that time
    start_time = int((target_time - timedelta(hours=4)).timestamp() * 1000)
    end_time = int((target_time + timedelta(hours=4)).timestamp() * 1000)
    
    print(f"\nFETCHING FROM BINGX:")
    print(f"  Start: {datetime.fromtimestamp(start_time/1000, tz=UTC)}")
    print(f"  End: {datetime.fromtimestamp(end_time/1000, tz=UTC)}")
    
    klines = await fetcher.get_klines(
        symbol="FLOW-USDT",
        interval="15m",
        limit=1000,
        start_time=start_time,
        end_time=end_time
    )
    
    print(f"  Fetched {len(klines)} klines")
    
    # Find the target candle and show neighbors
    target_index = -1
    for i, kline in enumerate(klines):
        kline_time = int(kline['time'])
        if kline_time == target_timestamp_ms:
            target_index = i
            break
    
    if target_index == -1:
        print("\n!!! TARGET CANDLE NOT FOUND !!!")
        return
    
    print(f"\nTARGET CANDLE INDEX: {target_index}")
    
    # Show 5 candles before and after
    start_idx = max(0, target_index - 5)
    end_idx = min(len(klines), target_index + 6)
    
    print("\n" + "=" * 80)
    print("NEIGHBORING CANDLES (RAW BINGX DATA)")
    print("=" * 80)
    
    for i in range(start_idx, end_idx):
        kline = klines[i]
        kline_time = int(kline['time'])
        kline_datetime = datetime.fromtimestamp(kline_time / 1000, tz=UTC)
        
        is_target = (i == target_index)
        marker = ">>> TARGET <<<" if is_target else ""
        
        print(f"\n[{i}] {kline_datetime} {marker}")
        print(f"  RAW BINGX RESPONSE:")
        for key, value in kline.items():
            print(f"    {key}: {value}")
        
        if is_target:
            print(f"\n  FULL RAW JSON:")
            print(f"    {json.dumps(kline, indent=4)}")
    
    # Now analyze the target candle in detail
    print("\n" + "=" * 80)
    print("TARGET CANDLE DETAILED ANALYSIS")
    print("=" * 80)
    
    kline = klines[target_index]
    
    print(f"\nRAW BINGX DATA (as received from API):")
    print(f"  time: {kline['time']}")
    print(f"  open: {kline['open']}")
    print(f"  high: {kline['high']}")
    print(f"  low: {kline['low']}")
    print(f"  close: {kline['close']}")
    print(f"  volume: {kline['volume']}")
    
    # Parse to float
    open_price = float(kline['open'])
    high_price = float(kline['high'])
    low_price = float(kline['low'])
    close_price = float(kline['close'])
    volume = float(kline['volume'])
    
    print(f"\nPARSED VALUES:")
    print(f"  Open:  {open_price:.6f}")
    print(f"  High:  {high_price:.6f}")
    print(f"  Low:   {low_price:.6f}")
    print(f"  Close: {close_price:.6f}")
    print(f"  Volume: {volume:.0f}")
    
    # Manual calculation
    print(f"\nMANUAL CALCULATION:")
    print(f"  RED CANDLE:")
    print(f"    Close < Open = {close_price:.6f} < {open_price:.6f} = {close_price < open_price}")
    
    is_red = close_price < open_price
    body = open_price - close_price if is_red else 0.0
    lower_wick = close_price - low_price
    upper_wick = high_price - open_price
    
    print(f"\n  BODY:")
    print(f"    Open - Close = {open_price:.6f} - {close_price:.6f} = {body:.6f}")
    
    print(f"\n  LOWER WICK:")
    print(f"    Close - Low = {close_price:.6f} - {low_price:.6f} = {lower_wick:.6f}")
    
    print(f"\n  UPPER WICK:")
    print(f"    High - Open = {high_price:.6f} - {open_price:.6f} = {upper_wick:.6f}")
    
    if body > 0:
        ratio = lower_wick / body
        print(f"\n  LOWER WICK / BODY:")
        print(f"    {lower_wick:.6f} / {body:.6f} = {ratio:.2f}x")
    else:
        ratio = 0.0
        print(f"\n  LOWER WICK / BODY:")
        print(f"    Cannot calculate - body is {body:.6f}")
    
    # LW-001 check
    print(f"\nLW-001 QUALIFICATION CHECK:")
    lw_result = check_lw001_strict(open_price, high_price, low_price, close_price)
    
    print(f"  Red Candle: {lw_result['is_red']}")
    print(f"  Body > 0: {lw_result['body'] is not None and lw_result['body'] > 0}")
    print(f"  Lower Wick > 0: {lw_result['lower_wick'] is not None and lw_result['lower_wick'] > 0}")
    if lw_result['ratio'] is not None:
        print(f"  Lower Wick >= 2 * Body: {lw_result['lower_wick']:.6f} >= 2 * {lw_result['body']:.6f} = {lw_result['lower_wick'] >= 2 * lw_result['body']}")
    print(f"  Qualified: {lw_result['qualified']}")
    print(f"  Reason: {lw_result['reason']}")
    
    # Volume check
    print(f"\nVOLUME FILTER CHECK:")
    previous_volumes = [float(klines[j]['volume']) for j in range(target_index - 48, target_index)]
    vol_result = check_volume_filter(volume, previous_volumes)
    
    print(f"  Current Volume: {vol_result['volume']:.0f}")
    print(f"  Max Previous 48: {vol_result['max_previous_volume']:.0f}")
    if vol_result['volume_ratio'] is not None:
        print(f"  Volume Ratio: {vol_result['volume_ratio']:.2f}x")
    print(f"  Qualified: {vol_result['qualified']}")
    print(f"  Reason: {vol_result['reason']}")
    
    # Final qualification
    print(f"\nFINAL QUALIFICATION:")
    final_qualified = lw_result['qualified'] and vol_result['qualified']
    print(f"  LW-001: {lw_result['qualified']}")
    print(f"  Volume: {vol_result['qualified']}")
    print(f"  FINAL: {final_qualified}")
    
    # Data that would be sent to Telegram
    print(f"\nDATA THAT WOULD BE SENT TO TELEGRAM:")
    print(f"  symbol: FLOW-USDT")
    print(f"  event_time: {datetime.fromtimestamp(int(kline['time']) / 1000, tz=UTC)}")
    print(f"  timestamp_ms: {int(kline['time'])}")
    print(f"  open: {open_price:.6f}")
    print(f"  high: {high_price:.6f}")
    print(f"  low: {low_price:.6f}")
    print(f"  close: {close_price:.6f}")
    print(f"  body: {lw_result['body']:.6f}")
    print(f"  lower_wick: {lw_result['lower_wick']:.6f}")
    print(f"  upper_wick: {lw_result['upper_wick']:.6f}")
    print(f"  ratio: {lw_result['ratio']:.2f}")
    print(f"  volume: {vol_result['volume']:.0f}")
    print(f"  max_previous_volume: {vol_result['max_previous_volume']:.0f}")
    print(f"  volume_ratio: {vol_result['volume_ratio']:.2f}")


if __name__ == "__main__":
    asyncio.run(main())
