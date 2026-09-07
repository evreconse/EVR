#!/usr/bin/env python3
"""
Deep diagnostic for previous 10 signals.

This script will:
1. Fetch raw BingX API response for each signal
2. Verify timestamp conversion (UTC/MSK)
3. Verify symbol mapping (USDT Perpetual)
4. Build candlestick chart from exact OHLC data
5. Perform verification for all 10 previous signals
"""

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent / "src"))

from exchange.bingx_fetcher import BingXFetcher


def format_msk_time(utc_dt):
    """Convert UTC datetime to MSK (UTC+3)."""
    msk_offset = timedelta(hours=3)
    msk_dt = utc_dt + msk_offset
    return msk_dt.strftime("%Y-%m-%d %H:%M:%S MSK")


async def deep_diagnostic_one_signal(fetcher, symbol, target_time_str):
    """Perform deep diagnostic on one signal."""
    print("\n" + "="*100)
    print(f"DEEP DIAGNOSTIC: {symbol}")
    print("="*100)
    
    target_time = datetime.fromisoformat(target_time_str.replace("Z", "+00:00"))
    target_timestamp_ms = int(target_time.timestamp() * 1000)
    
    print(f"\n1. TARGET INFORMATION")
    print(f"   Symbol: {symbol}")
    print(f"   Target Time (UTC): {target_time_str}")
    print(f"   Target Timestamp (ms): {target_timestamp_ms}")
    print(f"   Target Time (MSK): {format_msk_time(target_time)}")
    
    # Calculate candle interval
    target_minute = target_time.minute
    candle_start_minute = (target_minute // 15) * 15
    candle_start_time = target_time.replace(minute=candle_start_minute, second=0, microsecond=0)
    candle_end_time = candle_start_time + timedelta(minutes=15)
    
    print(f"\n2. CANDLE INTERVAL (M15)")
    print(f"   Candle Start (UTC): {candle_start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"   Candle End (UTC): {candle_end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"   Candle Start (MSK): {format_msk_time(candle_start_time)}")
    print(f"   Candle End (MSK): {format_msk_time(candle_end_time)}")
    
    # Fetch klines with raw API response
    print(f"\n3. BINGX API REQUEST")
    start_time = target_timestamp_ms - (100 * 15 * 60 * 1000)
    end_time = target_timestamp_ms + (100 * 15 * 60 * 1000)
    
    print(f"   Interval: 15m")
    print(f"   Limit: 200")
    print(f"   Start Time (ms): {start_time}")
    print(f"   End Time (ms): {end_time}")
    
    try:
        klines = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            limit=200,
            start_time=start_time,
            end_time=end_time
        )
        
        print(f"   Klines received: {len(klines)}")
        
        # Find the exact candle
        target_candle = None
        min_diff = float('inf')
        
        for kline in klines:
            kline_time = int(kline['time'])
            diff = abs(kline_time - target_timestamp_ms)
            if diff < min_diff:
                min_diff = diff
                target_candle = kline
        
        if target_candle:
            print(f"\n4. RAW BINGX API RESPONSE FOR TARGET CANDLE")
            print(f"   Raw JSON:")
            print(f"   {json.dumps(target_candle, indent=2)}")
            
            open_price = float(target_candle['open'])
            high_price = float(target_candle['high'])
            low_price = float(target_candle['low'])
            close_price = float(target_candle['close'])
            volume = float(target_candle['volume'])
            candle_time = int(target_candle['time'])
            candle_time_utc = datetime.fromtimestamp(candle_time / 1000, tz=UTC)
            
            print(f"\n5. PARSED OHLC DATA")
            print(f"   Time (UTC): {candle_time_utc}")
            print(f"   Time (MSK): {format_msk_time(candle_time_utc)}")
            print(f"   Open: {open_price}")
            print(f"   High: {high_price}")
            print(f"   Low: {low_price}")
            print(f"   Close: {close_price}")
            print(f"   Volume: {volume}")
            
            # Calculate metrics
            is_red = close_price < open_price
            body = open_price - close_price if is_red else close_price - open_price
            lower_wick = close_price - low_price if is_red else open_price - low_price
            upper_wick = high_price - max(open_price, close_price)
            total_range = high_price - low_price
            
            if body > 0:
                ratio = lower_wick / body
            else:
                ratio = 0.0
            
            if total_range > 0:
                body_range_ratio = body / total_range
                close_position = (close_price - low_price) / total_range
            else:
                body_range_ratio = 0.0
                close_position = 0.0
            
            qualified = is_red and ratio >= 2.0
            
            print(f"\n6. LW-001 CALCULATION")
            print(f"   Red Candle (Close < Open): {is_red}")
            print(f"   Body (Open - Close): {body:.6f}")
            print(f"   Lower Wick (Close - Low): {lower_wick:.6f}")
            print(f"   Upper Wick: {upper_wick:.6f}")
            print(f"   Total Range: {total_range:.6f}")
            print(f"   Lower Wick / Body: {ratio:.2f}x")
            print(f"   Body / Range: {body_range_ratio:.1%}")
            print(f"   Close Position: {close_position:.1%}")
            print(f"   Qualified (red AND ratio >= 2.0): {qualified}")
            
            # Get previous candle for volume comparison
            candle_index = -1
            for i, kline in enumerate(klines):
                if int(kline['time']) == candle_time:
                    candle_index = i
                    break
            
            previous_volume = 0.0
            volume_ratio = 0.0
            if candle_index > 0:
                previous_candle = klines[candle_index - 1]
                previous_volume = float(previous_candle['volume'])
                if previous_volume > 0:
                    volume_ratio = volume / previous_volume
            
            print(f"\n7. VOLUME ANALYSIS")
            print(f"   Signal Volume: {volume:,.0f}")
            print(f"   Previous Candle Volume: {previous_volume:,.0f}")
            print(f"   Volume Ratio: {volume_ratio:.2f}x")
            
            # Collect surrounding candles for chart
            chart_candles = []
            start_idx = max(0, candle_index - 5)
            end_idx = min(len(klines), candle_index + 6)
            
            for i in range(start_idx, end_idx):
                k = klines[i]
                chart_candles.append({
                    'time': datetime.fromtimestamp(int(k['time']) / 1000, tz=UTC),
                    'open': float(k['open']),
                    'high': float(k['high']),
                    'low': float(k['low']),
                    'close': float(k['close']),
                    'volume': float(k['volume']),
                    'is_target': i == candle_index
                })
            
            print(f"\n8. SURROUNDING CANDLES FOR CHART")
            print(f"   Total candles: {len(chart_candles)}")
            for i, c in enumerate(chart_candles):
                marker = " <-- TARGET" if c['is_target'] else ""
                print(f"   {i}: {c['time'].strftime('%Y-%m-%d %H:%M')} O={c['open']:.4f} H={c['high']:.4f} L={c['low']:.4f} C={c['close']:.4f}{marker}")
            
            return {
                'symbol': symbol,
                'target_time_utc': target_time_str,
                'target_time_msk': format_msk_time(target_time),
                'actual_time_utc': candle_time_utc.strftime('%Y-%m-%d %H:%M:%S UTC'),
                'actual_time_msk': format_msk_time(candle_time_utc),
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'body': body,
                'lower_wick': lower_wick,
                'upper_wick': upper_wick,
                'ratio': ratio,
                'is_red': is_red,
                'qualified': qualified,
                'volume': volume,
                'previous_volume': previous_volume,
                'volume_ratio': volume_ratio,
                'chart_candles': chart_candles,
                'raw_api_response': target_candle
            }
        else:
            print(f"\nERROR: Could not find candle near target time")
            return None
            
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Main diagnostic execution."""
    from dotenv import load_dotenv
    load_dotenv()
    
    print("="*100)
    print("DEEP DIAGNOSTIC: Previous 10 Signals")
    print("="*100)
    
    fetcher = BingXFetcher()
    
    previous_signals = [
        {"symbol": "BCH-USDT", "time": "2026-08-10T14:15:00Z"},
        {"symbol": "THETA-USDT", "time": "2026-08-10T16:00:00Z"},
        {"symbol": "ALGO-USDT", "time": "2026-08-10T16:00:00Z"},
        {"symbol": "AXS-USDT", "time": "2026-08-10T15:00:00Z"},
        {"symbol": "DYDX-USDT", "time": "2026-08-10T13:30:00Z"},
        {"symbol": "ICP-USDT", "time": "2026-08-09T21:00:00Z"},
        {"symbol": "SAND-USDT", "time": "2026-08-10T13:30:00Z"},
        {"symbol": "KSM-USDT", "time": "2026-08-10T15:15:00Z"},
        {"symbol": "VET-USDT", "time": "2026-08-10T16:00:00Z"},
        {"symbol": "SUSHI-USDT", "time": "2026-08-10T16:00:00Z"},
    ]
    
    results = []
    
    for signal_info in previous_signals:
        result = await deep_diagnostic_one_signal(
            fetcher,
            signal_info["symbol"],
            signal_info["time"]
        )
        if result:
            results.append(result)
    
    # Summary table
    print("\n" + "="*100)
    print("SUMMARY TABLE")
    print("="*100)
    print(f"{'#':<3} {'Symbol':<12} {'UTC':<20} {'MSK':<20} {'Open':<10} {'Close':<10} {'Body':<10} {'Lower Wick':<12} {'Ratio':<8} {'Program':<8}")
    print("-"*100)
    
    for i, r in enumerate(results, 1):
        print(f"{i:<3} {r['symbol']:<12} {r['actual_time_utc']:<20} {r['actual_time_msk']:<20} {r['open']:<10.4f} {r['close']:<10.4f} {r['body']:<10.6f} {r['lower_wick']:<12.6f} {r['ratio']:<8.2f} {'PASS' if r['qualified'] else 'FAIL':<8}")
    
    # Save results to JSON for chart generation
    with open('diagnostic_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print("\n" + "="*100)
    print("DIAGNOSTIC COMPLETE")
    print("Results saved to: diagnostic_results.json")
    print("="*100)


if __name__ == "__main__":
    asyncio.run(main())
