#!/usr/bin/env python3
"""
Check all symbols from top 21 to top 250 for LW-001 signals on specific dates
"""

import asyncio
import sys
sys.path.insert(0, "src")

from dotenv import load_dotenv
load_dotenv()

from src.exchange.bingx_fetcher import BingXFetcher
from src.strategy.lw001_canonical import check_lw001_signal
from datetime import UTC, datetime


async def main():
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
    
    dates = [
        datetime(2026, 8, 30, tzinfo=UTC),
        datetime(2026, 8, 31, tzinfo=UTC),
        datetime(2026, 9, 1, tzinfo=UTC),
    ]
    
    fetcher = BingXFetcher()
    
    for target in dates:
        start_ms = int(target.replace(hour=0, minute=0, second=0).timestamp() * 1000)
        end_ms = int(target.replace(hour=23, minute=59, second=59).timestamp() * 1000)
        print(f"\n=== {target.date()} ===")
        
        signals_found = 0
        for i, symbol in enumerate(universe):
            if i % 20 == 0:
                print(f"  Progress: {i}/{len(universe)}")
            try:
                klines = await fetcher.get_klines(
                    symbol=symbol, 
                    interval='15m', 
                    limit=2000, 
                    start_time=start_ms, 
                    end_time=end_ms
                )
                if not klines or len(klines) < 21:
                    continue
                for i in range(len(klines)-1, 20, -1):
                    ts = int(klines[i]['time'])
                    candle_date = datetime.fromtimestamp(ts/1000, tz=UTC).date()
                    if candle_date != target.date():
                        if candle_date < target.date():
                            break
                        continue
                    o = float(klines[i]['open'])
                    h = float(klines[i]['high'])
                    l = float(klines[i]['low'])
                    c = float(klines[i]['close'])
                    v = float(klines[i]['volume'])
                    prev_20 = [float(klines[j]['volume']) for j in range(i-20, i)]
                    result = check_lw001_signal(o, h, l, c, v, prev_20)
                    if result.qualified:
                        print(f'SIGNAL: {symbol} at {datetime.fromtimestamp(ts/1000, tz=UTC)} LW/Body={result.metrics.lw_body_ratio:.2f}x VolRatio={result.metrics.volume_ratio:.2f}x')
                        break
            except Exception as e:
                pass
    
    print('\nDone checking all symbols.')
    await fetcher.close()


if __name__ == "__main__":
    import asyncio
    from datetime import UTC, datetime
    from src.exchange.bingx_fetcher import BingXFetcher
    from src.strategy.lw001_canonical import check_lw001_signal
    from datetime import UTC, datetime
    
    asyncio.run(main())