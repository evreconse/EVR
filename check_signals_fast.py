#!/usr/bin/env python3
"""
Quick check for LW-001 signals on Sept 1-5, 2026 - minimal symbols
"""

import asyncio
import sys
sys.path.insert(0, "src")

from dotenv import load_dotenv
load_dotenv()

from src.exchange.bingx_fetcher import BingXFetcher
from src.strategy.lw001_canonical import check_lw001_signal
from datetime import UTC, datetime


async def check_symbol_on_date(fetcher, symbol, target_date, start_ms, end_ms):
    """Check one symbol on one date."""
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
                return {
                    'symbol': symbol,
                    'time': datetime.fromtimestamp(ts / 1000, tz=UTC),
                    'metrics': result.metrics
                }
        return None
    except Exception:
        return None


async def main():
    from src.exchange.bingx_fetcher import BingXFetcher
    from src.strategy.lw001_canonical import check_lw001_signal
    from datetime import UTC, datetime
    
    fetcher = BingXFetcher()
    
    # Just check a few key symbols for speed
    symbols = ['AAVE-USDT', 'LINK-USDT', 'SOL-USDT', 'AVAX-USDT', 'DOT-USDT',
               'LTC-USDT', 'NEAR-USDT', 'UNI-USDT', 'ARB-USDT', 'OP-USDT']
    
    target_dates = [
        datetime(2026, 9, 1, tzinfo=UTC),
        datetime(2026, 9, 2, tzinfo=UTC),
        datetime(2026, 9, 3, tzinfo=UTC),
        datetime(2026, 9, 4, tzinfo=UTC),
        datetime(2026, 9, 5, tzinfo=UTC),
    ]
    
    fetcher = BingXFetcher()
    
    for target_date in [
        datetime(2026, 9, 1, tzinfo=UTC),
        datetime(2026, 9, 2, tzinfo=UTC),
        datetime(2026, 9, 3, tzinfo=UTC),
        datetime(2026, 9, 4, tzinfo=UTC),
        datetime(2026, 9, 5, tzinfo=UTC),
    ]:
        start_ms = int(target_date.replace(hour=0, minute=0, second=0).timestamp() * 1000)
        end_ms = int(target_date.replace(hour=23, minute=59, second=59).timestamp() * 1000)
        
        print(f"\n=== Checking {target_date.date()} ===")
        
        for symbol in ['AAVE-USDT', 'LINK-USDT', 'SOL-USDT', 'AVAX-USDT', 'DOT-USDT',
                       'LTC-USDT', 'NEAR-USDT', 'UNI-USDT', 'ARB-USDT', 'OP-USDT']:
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
            except Exception:
                pass
        
        print(f"  Done checking {target_date.date()}")
    
    print("\nDone checking all dates.")
    await fetcher.close()


if __name__ == "__main__":
    import asyncio
    from src.exchange.bingx_fetcher import BingXFetcher
    from src.strategy.lw001_canonical import check_lw001_signal
    from datetime import UTC, datetime
    
    asyncio.run(main())