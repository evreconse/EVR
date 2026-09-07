#!/usr/bin/env python3
"""
Check LW-001 signals on specific dates - fast version
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
    from datetime import UTC, datetime
    
    fetcher = BingXFetcher()
    
    # Get full universe: top 21-250
    symbols = await fetcher.get_usdt_perpetual_symbols()
    TOP_20 = [
        'BTC-USDT', 'ETH-USDT', 'BNB-USDT', 'SOL-USDT', 'XRP-USDT',
        'ADA-USDT', 'DOGE-USDT', 'AVAX-USDT', 'TRX-USDT', 'DOT-USDT',
        'LINK-USDT', 'MATIC-USDT', 'SHIB-USDT', 'LTC-USDT', 'BCH-USDT',
        'PEPE-USDT', 'NEAR-USDT', 'UNI-USDT', 'APT-USDT', 'XLM-USDT'
    ]
    universe = [s for s in symbols if s not in TOP_20][:230]  # Top 21-250
    
    print(f"Universe size: {len(universe)} symbols")
    
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
        
        for i, symbol in enumerate(universe):
            if i % 20 == 0:
                print(f"  Progress: {i}/{len(universe)}")
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
                pass
    
    print("\nDone checking all dates.")
    await fetcher.close()


if __name__ == "__main__":
    import asyncio
    from src.exchange.bingx_fetcher import BingXFetcher
    from src.strategy.lw001_canonical import check_lw001_signal
    from datetime import UTC, datetime
    
    asyncio.run(main())