#!/usr/bin/env python3
"""
Check for LW-001 signals on specific dates by paginating through BingX API
"""

import asyncio
import sys
sys.path.insert(0, "src")

from dotenv import load_dotenv
load_dotenv()

from src.exchange.bingx_fetcher import BingXFetcher
from src.strategy.lw001_canonical import check_lw001_signal
from datetime import UTC, datetime, timedelta


async def check_symbol_on_date(fetcher, symbol, target_date, start_ms, end_ms):
    """Check one symbol for signals on a specific date."""
    try:
        klines = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            limit=2000,
            start_time=start_ms,
            end_time=end_ms
        )
        
        if not klines or len(klines) < 21:
            return None
        
        signals = []
        for i in range(len(klines) - 1, 20, -1):
            ts = int(klines[i]['time'])
            candle_date = datetime.fromtimestamp(ts / 1000, tz=UTC).date()
            if candle_date != target_date.date():
                if candle_date < target_date.date():
                    break
                continue
            
            o = float(klines[i]['open'])
            h = float(klines[i]['high'])
            l = float(klines[i]['low'])
            c = float(klines[i]['close'])
            v = float(klines[i]['volume'])
            prev_20 = [float(klines[j]['volume']) for j in range(i - 20, i)]
            
            result = check_lw001_signal(o, h, l, c, v, prev_20)
            
            if result.qualified:
                event_time = datetime.fromtimestamp(ts / 1000, tz=UTC)
                return {
                    'symbol': symbol,
                    'time': event_time,
                    'metrics': result.metrics
                }
        return None
    except Exception as e:
        return None


async def main():
    from src.exchange.bingx_fetcher import BingXFetcher
    from src.strategy.lw001_canonical import check_lw001_signal
    from datetime import UTC, datetime, timedelta
    
    fetcher = BingXFetcher()
    
    # Symbols to check - a good mix of mid-tier coins
    symbols = [
        'AAVE-USDT', 'LINK-USDT', 'SOL-USDT', 'AVAX-USDT', 'DOT-USDT',
        'LTC-USDT', 'NEAR-USDT', 'UNI-USDT', 'ARB-USDT', 'OP-USDT',
        'ADA-USDT', 'XRP-USDT', 'DOGE-USDT', 'SHIB-USDT', 'MATIC-USDT',
        'ATOM-USDT', 'ETC-USDT', 'FIL-USDT', 'ICP-USDT', 'APT-USDT',
        'OP-USDT', 'ARB-USDT', 'INJ-USDT', 'SUI-USDT', 'SEI-USDT',
        'TIA-USDT', 'WLD-USDT', 'STRK-USDT', 'DYDX-USDT', 'BLUR-USDT',
        'ORDI-USDT', 'FET-USDT', 'RENDER-USDT', 'WLD-USDT'
    ]
    
    target_dates = [
        datetime(2026, 8, 30, tzinfo=UTC),
        datetime(2026, 8, 31, tzinfo=UTC),
        datetime(2026, 9, 1, tzinfo=UTC),
    ]
    
    fetcher = BingXFetcher()
    
    for target_date in [
        datetime(2026, 8, 30, tzinfo=UTC),
        datetime(2026, 8, 31, tzinfo=UTC),
        datetime(2026, 9, 1, tzinfo=UTC),
    ]:
        start_ms = int(target_date.replace(hour=0, minute=0, second=0).timestamp() * 1000)
        end_ms = int(target_date.replace(hour=23, minute=59, second=59).timestamp() * 1000)
        
        print(f"\n=== Checking {target_date.date()} ===")
        found_any = False
        
        for symbol in symbols:
            try:
                klines = await fetcher.get_klines(
                    symbol=symbol,
                    interval="15m",
                    limit=2000,
                    start_time=start_ms,
                    end_time=end_ms
                )
                
                if not klines or len(klines) < 21:
                    continue
                
                for i in range(len(klines) - 1, 20, -1):
                    ts = int(klines[i]['time'])
                    candle_date = datetime.fromtimestamp(ts / 1000, tz=UTC).date()
                    if candle_date != target_date.date():
                        if candle_date < target_date.date():
                            break
                        continue
                    
                    o = float(klines[i]['open'])
                    h = float(klines[i]['high'])
                    l = float(klines[i]['low'])
                    c = float(klines[i]['close'])
                    v = float(klines[i]['volume'])
                    prev_20 = [float(klines[j]['volume']) for j in range(i - 20, i)]
                    
                    result = check_lw001_signal(o, h, l, c, v, prev_20)
                    
                    if result.qualified:
                        event_time = datetime.fromtimestamp(ts / 1000, tz=UTC)
                        print(f"  SIGNAL: {symbol} at {event_time} LW/Body={result.metrics.lw_body_ratio:.2f}x VolRatio={result.metrics.volume_ratio:.2f}x")
                        break
            except Exception as e:
                continue
    
    print("\nDone checking all dates.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())