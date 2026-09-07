#!/usr/bin/env python3
"""
Quick check for LW-001 signals on Sept 1-5, 2026
"""

import asyncio
import sys
sys.path.insert(0, "src")

from dotenv import load_dotenv
load_dotenv()

from src.exchange.bingx_fetcher import BingXFetcher
from src.strategy.lw001_canonical import check_lw001_signal
from datetime import UTC, datetime


async def check_one_symbol(fetcher, symbol, target_date, start_ms, end_ms):
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
    except:
        return None


async def check_date(fetcher, symbols, target_date, start_ms, end_ms):
    """Check all symbols for one date - runs in parallel."""
    semaphore = asyncio.Semaphore(5)  # Limit concurrent requests
    
    async def check_one(symbol):
        async with asyncio.Semaphore(3):
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
                    
                    result = check_lw001_signal(
                        open_price=o, high_price=h, low_price=l, 
                        close_price=c, volume=v, previous_20_volumes=prev_20
                    )
                    
                    if result.qualified:
                        return {
                            'symbol': symbol,
                            'time': datetime.fromtimestamp(ts / 1000, tz=UTC),
                            'metrics': result.metrics
                        }
                return None
            except Exception as e:
                return None
    
    semaphore = asyncio.Semaphore(3)
    
    async def check_one(symbol):
        async with asyncio.Semaphore(3):
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
            except Exception as e:
                return None
    
    tasks = [check_one(s) for s in symbols]
    results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]


async def main():
    from src.exchange.bingx_fetcher import BingXFetcher
    from src.strategy.lw001_canonical import check_lw001_signal
    from datetime import UTC, datetime, timedelta
    
    fetcher = BingXFetcher()
    
    # Get universe: top 21-250
    symbols_all = await fetcher.get_usdt_perpetual_symbols()
    TOP_20 = [
        'BTC-USDT', 'ETH-USDT', 'BNB-USDT', 'SOL-USDT', 'XRP-USDT',
        'ADA-USDT', 'DOGE-USDT', 'AVAX-USDT', 'TRX-USDT', 'DOT-USDT',
        'LINK-USDT', 'MATIC-USDT', 'SHIB-USDT', 'LTC-USDT', 'BCH-USDT',
        'PEPE-USDT', 'NEAR-USDT', 'UNI-USDT', 'APT-USDT', 'XLM-USDT'
    ]
    universe = [s for s in symbols if s not in TOP_20][:30]  # First 30 for speed
    
    print(f"Universe size: {len(universe)} symbols")
    
    target_dates = [
        datetime(2026, 9, 1, tzinfo=UTC),
        datetime(2026, 9, 2, tzinfo=UTC),
        datetime(2026, 9, 3, tzinfo=UTC),
        datetime(2026, 9, 4, tzinfo=UTC),
        datetime(2026, 9, 5, tzinfo=UTC),
    ]
    
    fetcher = BingXFetcher()
    all_signals = []
    
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
        
        # Check first 10 symbols for speed
        symbols_to_check = ['AAVE-USDT', 'LINK-USDT', 'SOL-USDT', 'AVAX-USDT', 'DOT-USDT',
                            'LTC-USDT', 'NEAR-USDT', 'UNI-USDT', 'ARB-USDT', 'OP-USDT',
                            'ADA-USDT', 'XRP-USDT', 'DOGE-USDT', 'SHIB-USDT', 'MATIC-USDT',
                            'ATOM-USDT', 'ETC-USDT', 'FIL-USDT', 'ICP-USDT', 'APT-USDT',
                            'NEAR-USDT', 'UNI-USDT', 'ARB-USDT', 'OP-USDT', 'INJ-USDT',
                            'SUI-USDT', 'SEI-USDT', 'TIA-USDT', 'WLD-USDT', 'STRK-USDT',
                            'DYDX-USDT', 'BLUR-USDT', 'ORDI-USDT', 'FET-USDT', 'RENDER-USDT',
                            'WLD-USDT', 'STRK-USDT', 'DYDX-USDT', 'BLUR-USDT', 'ORDI-USDT',
                            'FET-USDT', 'RENDER-USDT', 'WLD-USDT']
        
        signals = []
        for symbol in symbols[:15]:  # First 15 for speed
            start_ms = int(target_date.replace(hour=0, minute=0, second=0).timestamp() * 1000)
            end_ms = int(target_date.replace(hour=23, minute=59, second=59).timestamp() * 1000)
            result = await check_symbol_on_date(fetcher, symbol, target_date, start_ms, end_ms)
            if result:
                m = result['metrics']
                print(f"  SIGNAL: {result['symbol']} at {result['time']} LW/Body={result['metrics'].lw_body_ratio:.2f}x VolRatio={result['metrics'].volume_ratio:.2f}x")
        
        print(f"  Done checking {target_date.date()}")
    
    print("\nDone checking all dates.")
    await fetcher.close()


if __name__ == "__main__":
    import asyncio
    from src.exchange.bingx_fetcher import BingXFetcher
    from src.strategy.lw001_canonical import check_lw001_signal
    from datetime import UTC, datetime, timedelta
    
    asyncio.run(main())