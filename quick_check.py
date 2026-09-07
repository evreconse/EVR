#!/usr/bin/env python3
"""
Quick check for LW-001 signals on recent data
"""

import asyncio
import sys
sys.path.insert(0, "src")

from dotenv import load_dotenv
load_dotenv()

from src.exchange.bingx_fetcher import BingXFetcher
from src.strategy.lw001_canonical import check_lw001_signal
from datetime import UTC, datetime, timedelta


async def quick_check():
    fetcher = BingXFetcher()
    symbols = await fetcher.get_usdt_perpetual_symbols()
    print(f'Total symbols: {len(symbols)}')

    # Test with top 20 symbols for speed
    universe = symbols[:20]
    print(f'Testing {len(universe)} symbols...')

    # Check last 2 days
    end_time = int(datetime.now(UTC).timestamp() * 1000)
    start_time = int((datetime.now(UTC) - timedelta(days=2)).timestamp() * 1000)

    signals = 0
    for symbol in universe:
        try:
            klines = await fetcher.get_klines(
                symbol=symbol,
                interval="15m",
                limit=50,
                start_time=int((datetime.now(UTC) - timedelta(days=2)).timestamp() * 1000),
                end_time=int(datetime.now(UTC).timestamp() * 1000)
            )

            if not klines or len(klines) < 21:
                continue

            # Check most recent closed candle
            for i in range(len(klines) - 1, 20, -1):
                o = float(klines[i]['open'])
                h = float(klines[i]['high'])
                l = float(klines[i]['low'])
                c = float(klines[i]['close'])
                v = float(klines[i]['volume'])
                ts = int(klines[i]['time'])
                prev_20 = [float(klines[j]['volume']) for j in range(i - 20, i)]

                result = check_lw001_signal(o, h, l, c, v, prev_20)

                if result.qualified:
                    event_time = datetime.fromtimestamp(ts / 1000, tz=UTC)
                    print(f"SIGNAL: {symbol} at {event_time} LW/Body={result.metrics.lw_body_ratio:.2f}x VolRatio={result.metrics.volume_ratio:.2f}x")
                    signals += 1
                    break

        except Exception as e:
            print(f"Error {symbol}: {e}")
            continue

    print(f"\nTotal signals found: {signals}")


async def main():
    from src.exchange.bingx_fetcher import BingXFetcher
    from src.strategy.lw001_canonical import check_lw001_signal
    from datetime import UTC, datetime, timedelta

    fetcher = BingXFetcher()
    symbols = await fetcher.get_usdt_perpetual_symbols()
    print(f'Total symbols: {len(symbols)}')

    # Test with top 20 symbols for speed
    universe = symbols[:20]
    print(f'Testing {len(universe)} symbols...')

    # Check last 2 days
    end_time = int(datetime.now(UTC).timestamp() * 1000)
    start_time = int((datetime.now(UTC) - timedelta(days=2)).timestamp() * 1000)

    signals = 0
    for symbol in universe:
        try:
            klines = await fetcher.get_klines(
                symbol=symbol,
                interval="15m",
                limit=50,
                start_time=int((datetime.now(UTC) - timedelta(days=2)).timestamp() * 1000),
                end_time=int(datetime.now(UTC).timestamp() * 1000)
            )

            if not klines or len(klines) < 21:
                continue

            # Check most recent closed candle
            for i in range(len(klines) - 1, 20, -1):
                o = float(klines[i]['open'])
                h = float(klines[i]['high'])
                l = float(klines[i]['low'])
                c = float(klines[i]['close'])
                v = float(klines[i]['volume'])
                ts = int(klines[i]['time'])
                prev_20 = [float(klines[j]['volume']) for j in range(i - 20, i)]

                result = check_lw001_signal(o, h, l, c, v, prev_20)

                if result.qualified:
                    event_time = datetime.fromtimestamp(ts / 1000, tz=UTC)
                    print(f"SIGNAL: {symbol} at {event_time} LW/Body={result.metrics.lw_body_ratio:.2f}x VolRatio={result.metrics.volume_ratio:.2f}x")
                    signals += 1
                    break

        except Exception as e:
            print(f"Error {symbol}: {e}")
            continue

    print(f"\nTotal signals found: {signals}")


if __name__ == "__main__":
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())