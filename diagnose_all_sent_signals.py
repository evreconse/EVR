#!/usr/bin/env python3
"""
Check all 10 signals from the previous batch to verify their actual BingX data.

From the report, the 10 signals were:
1. SUSHI-USDT at 05.08.2026 11:15 UTC
2. COMP-USDT at 07.08.2026 04:45 UTC
3. DASH-USDT at 11.08.2026 10:15 UTC
4. FLOW-USDT at 10.08.2026 07:15 UTC
5. RUNE-USDT at 06.08.2026 07:30 UTC
6. ROSE-USDT at 06.08.2026 02:15 UTC
7. WOO-USDT at 11.08.2026 04:45 UTC
8. CRO-USDT at 09.08.2026 04:45 UTC
9. ACH-USDT at 08.08.2026 13:00 UTC
10. TLM-USDT at 11.08.2026 18:30 UTC
"""

import asyncio
from datetime import UTC, datetime, timedelta
import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


async def check_candle(symbol: str, target_time: datetime, report_data: dict, fetcher: BingXFetcher):
    """Check a single candle against BingX data."""
    target_timestamp_ms = int(target_time.timestamp() * 1000)
    
    # Fetch klines around that time
    start_time = int((target_time - timedelta(hours=2)).timestamp() * 1000)
    end_time = int((target_time + timedelta(hours=2)).timestamp() * 1000)
    
    klines = await fetcher.get_klines(
        symbol=symbol,
        interval="15m",
        limit=1000,
        start_time=start_time,
        end_time=end_time
    )
    
    # Find the candle at the exact timestamp
    for kline in klines:
        kline_time = int(kline['time'])
        
        if kline_time == target_timestamp_ms:
            open_price = float(kline['open'])
            high_price = float(kline['high'])
            low_price = float(kline['low'])
            close_price = float(kline['close'])
            
            # Calculate LW-001
            is_red = close_price < open_price
            body = open_price - close_price if is_red else 0.0
            lower_wick = close_price - low_price
            upper_wick = high_price - open_price
            
            if body > 0:
                ratio = lower_wick / body
                qualified = is_red and body > 0 and lower_wick > 0 and lower_wick >= 2 * body
            else:
                ratio = 0.0
                qualified = False
            
            # Check for data mismatch
            open_mismatch = abs(open_price - report_data['open'])
            high_mismatch = abs(high_price - report_data['high'])
            low_mismatch = abs(low_price - report_data['low'])
            close_mismatch = abs(close_price - report_data['close'])
            
            has_mismatch = open_mismatch > 0.000001 or high_mismatch > 0.000001 or low_mismatch > 0.000001 or close_mismatch > 0.000001
            
            return {
                'symbol': symbol,
                'time': target_time,
                'bingx_open': open_price,
                'bingx_high': high_price,
                'bingx_low': low_price,
                'bingx_close': close_price,
                'report_open': report_data['open'],
                'report_high': report_data['high'],
                'report_low': report_data['low'],
                'report_close': report_data['close'],
                'has_mismatch': has_mismatch,
                'is_red': is_red,
                'body': body,
                'lower_wick': lower_wick,
                'upper_wick': upper_wick,
                'ratio': ratio,
                'qualified': qualified,
            }
    
    return None


async def main():
    """Check all 10 signals."""
    print("=" * 80)
    print("CHECKING ALL 10 SENT SIGNALS AGAINST BINGX DATA")
    print("=" * 80)
    
    fetcher = BingXFetcher()
    
    # Signal data from the report
    signals = [
        {
            'symbol': 'SUSHI-USDT',
            'time': datetime(2026, 8, 5, 11, 15, tzinfo=UTC),
            'report': {'open': 0.155500, 'high': 0.155500, 'low': 0.154700, 'close': 0.155500}
        },
        {
            'symbol': 'COMP-USDT',
            'time': datetime(2026, 8, 7, 4, 45, tzinfo=UTC),
            'report': {'open': 16.190000, 'high': 16.190000, 'low': 16.110000, 'close': 16.190000}
        },
        {
            'symbol': 'DASH-USDT',
            'time': datetime(2026, 8, 11, 10, 15, tzinfo=UTC),
            'report': {'open': 30.470000, 'high': 30.480000, 'low': 30.380000, 'close': 30.440000}
        },
        {
            'symbol': 'FLOW-USDT',
            'time': datetime(2026, 8, 10, 7, 15, tzinfo=UTC),
            'report': {'open': 0.029750, 'high': 0.029750, 'low': 0.029720, 'close': 0.029750}
        },
        {
            'symbol': 'RUNE-USDT',
            'time': datetime(2026, 8, 6, 7, 30, tzinfo=UTC),
            'report': {'open': 0.447300, 'high': 0.447560, 'low': 0.446000, 'close': 0.447300}
        },
        {
            'symbol': 'ROSE-USDT',
            'time': datetime(2026, 8, 6, 2, 15, tzinfo=UTC),
            'report': {'open': 0.005484, 'high': 0.005494, 'low': 0.005462, 'close': 0.005477}
        },
        {
            'symbol': 'WOO-USDT',
            'time': datetime(2026, 8, 11, 4, 45, tzinfo=UTC),
            'report': {'open': 0.011090, 'high': 0.011090, 'low': 0.010990, 'close': 0.011080}
        },
        {
            'symbol': 'CRO-USDT',
            'time': datetime(2026, 8, 9, 4, 45, tzinfo=UTC),
            'report': {'open': 0.049450, 'high': 0.049450, 'low': 0.049110, 'close': 0.049380}
        },
        {
            'symbol': 'ACH-USDT',
            'time': datetime(2026, 8, 8, 13, 0, tzinfo=UTC),
            'report': {'open': 0.004232, 'high': 0.004251, 'low': 0.004222, 'close': 0.004229}
        },
        {
            'symbol': 'TLM-USDT',
            'time': datetime(2026, 8, 11, 18, 30, tzinfo=UTC),
            'report': {'open': 0.001564, 'high': 0.001567, 'low': 0.001551, 'close': 0.001563}
        },
    ]
    
    results = []
    mismatch_count = 0
    
    for signal in signals:
        try:
            result = await check_candle(signal['symbol'], signal['time'], signal['report'], fetcher)
            if result:
                results.append(result)
                if result['has_mismatch']:
                    mismatch_count += 1
        except Exception as e:
            print(f"Error checking {signal['symbol']}: {e}")
    
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"\nTotal signals checked: {len(results)}")
    print(f"Signals with data mismatch: {mismatch_count}")
    
    print("\n" + "=" * 80)
    print("DETAILED RESULTS")
    print("=" * 80)
    
    for result in results:
        print(f"\n{result['symbol']} at {result['time']}")
        if result['has_mismatch']:
            print("  !!! DATA MISMATCH DETECTED !!!")
            print(f"  BingX:  O={result['bingx_open']:.6f} H={result['bingx_high']:.6f} L={result['bingx_low']:.6f} C={result['bingx_close']:.6f}")
            print(f"  Report: O={result['report_open']:.6f} H={result['report_high']:.6f} L={result['report_low']:.6f} C={result['report_close']:.6f}")
        else:
            print("  Data matches BingX")
        
        print(f"  Red: {result['is_red']}, Body: {result['body']:.6f}, Lower Wick: {result['lower_wick']:.6f}, Ratio: {result['ratio']:.2f}x")
        print(f"  Qualified: {result['qualified']}")
    
    if mismatch_count > 0:
        print("\n" + "=" * 80)
        print("!!! CRITICAL FINDING !!!")
        print("=" * 80)
        print(f"{mismatch_count} out of {len(results)} signals have data mismatches.")
        print("The report showed incorrect OHLC values.")
        print("This means the user was looking at wrong data in the report.")
        print("The actual candles in BingX may be correct.")


if __name__ == "__main__":
    asyncio.run(main())
