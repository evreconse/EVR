#!/usr/bin/env python3
"""
Debug pagination: Check if the pagination logic is working correctly
"""

import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

import asyncio
from datetime import datetime, UTC, timedelta


async def debug_pagination(symbol: str = "SAND-USDT", days: int = 60):
    """Debug pagination by manually simulating the fetch logic."""
    from src.exchange.bingx_fetcher import BingXFetcher
    fetcher = BingXFetcher()
    
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=days)
    
    print("="*100)
    print(f"DEBUG: Pagination for {symbol}")
    print("="*100)
    print()
    print(f"Target range:")
    print(f"  Start: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')} (timestamp: {int(start_time.timestamp() * 1000)})")
    print(f"  End: {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')} (timestamp: {int(end_time.timestamp() * 1000)})")
    print()
    
    # Manually simulate pagination
    all_klines = []
    current_end = int(end_time.timestamp() * 1000)
    start_timestamp = int(start_time.timestamp() * 1000)
    max_per_request = 1000
    request_count = 0
    
    while True:
        request_count += 1
        print(f"Request #{request_count}:")
        print(f"  endTime: {current_end}")
        print(f"  startTime: {start_timestamp}")
        
        params = {
            "symbol": symbol,
            "interval": "15m",
            "limit": max_per_request,
            "startTime": start_timestamp,
            "endTime": current_end
        }
        
        try:
            data = await fetcher._request("/openApi/swap/v3/quote/klines", "GET", params)
            
            if isinstance(data, list) and data:
                print(f"  Returned: {len(data)} candles")
                
                if data:
                    first = data[0]
                    last = data[-1]
                    
                    if isinstance(first, dict):
                        first_time = int(first.get('time', 0))
                        last_time = int(last.get('time', 0))
                    else:
                        first_time = int(first[0])
                        last_time = int(last[0])
                    
                    from datetime import datetime as dt
                    first_dt = dt.fromtimestamp(first_time / 1000, UTC)
                    last_dt = dt.fromtimestamp(last_time / 1000, UTC)
                    
                    print(f"  First candle: {first_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    print(f"  Last candle: {last_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    
                    data_reversed = list(reversed(data))
                    all_klines.extend(data_reversed)
                    print(f"  Total collected so far: {len(all_klines)} candles")
                    
                    # Check if we got less than requested
                    if len(data) < max_per_request:
                        print(f"  Got less than max_per_request - stopping pagination")
                        break
                    
                    # Update end_time for next request
                    current_end = first_time - 1
                    print(f"  Next request endTime: {current_end}")
                    
                    # Check if we've reached start_time
                    if current_end <= start_timestamp:
                        print(f"  Reached start_time - stopping pagination")
                        break
                    
                    # Safety limit
                    if request_count >= 10:
                        print(f"  Safety limit reached - stopping pagination")
                        break
                else:
                    print(f"  Empty data - stopping pagination")
                    break
            else:
                print(f"  No data returned - stopping pagination")
                break
                
        except Exception as e:
            print(f"  ERROR: {e}")
            break
        
        print()
    
    print()
    print("="*100)
    print(f"Pagination Complete")
    print("="*100)
    print(f"Total requests made: {request_count}")
    print(f"Total candles collected: {len(all_klines)}")
    
    if all_klines:
        first = all_klines[0]
        last = all_klines[-1]
        
        if isinstance(first, dict):
            first_time = int(first.get('time', 0))
            last_time = int(last.get('time', 0))
        else:
            first_time = int(first[0])
            last_time = int(last[0])
        
        from datetime import datetime as dt
        first_dt = dt.fromtimestamp(first_time / 1000, UTC)
        last_dt = dt.fromtimestamp(last_time / 1000, UTC)
        
        print(f"First candle: {first_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Last candle: {last_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        actual_days = len(all_klines) / (24 * 4)
        print(f"Actual days covered: {actual_days:.2f} days")


async def main():
    await debug_pagination("SAND-USDT", days=60)


if __name__ == "__main__":
    asyncio.run(main())
