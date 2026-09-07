#!/usr/bin/env python3
"""
Debug API response: Check what the BingX API actually returns
"""

import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

import asyncio
from datetime import datetime, UTC, timedelta


async def debug_api_response(symbol: str = "SAND-USDT"):
    """Debug actual API response."""
    from src.exchange.bingx_fetcher import BingXFetcher
    fetcher = BingXFetcher()
    
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=60)
    
    print("="*100)
    print(f"DEBUG: API Response for {symbol}")
    print("="*100)
    print()
    print(f"Request parameters:")
    print(f"  symbol: {symbol}")
    print(f"  interval: 15m")
    print(f"  startTime: {int(start_time.timestamp() * 1000)}")
    print(f"  endTime: {int(end_time.timestamp() * 1000)}")
    print(f"  limit: 1000")
    print()
    
    # Make a single request to see what the API returns
    params = {
        "symbol": symbol,
        "interval": "15m",
        "limit": 1000,
        "startTime": int(start_time.timestamp() * 1000),
        "endTime": int(end_time.timestamp() * 1000)
    }
    
    try:
        data = await fetcher._request("/openApi/swap/v3/quote/klines", "GET", params)
        
        print(f"API Response:")
        print(f"  Data type: {type(data)}")
        
        if isinstance(data, list):
            print(f"  Number of candles returned: {len(data)}")
            
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
                
                print(f"  First candle timestamp: {first_time} ({first_dt.strftime('%Y-%m-%d %H:%M:%S UTC')})")
                print(f"  Last candle timestamp: {last_time} ({last_dt.strftime('%Y-%m-%d %H:%M:%S UTC')})")
                
                # Check if data is in reverse order
                print(f"  Data order: {'Reverse (newest first)' if first_time > last_time else 'Chronological (oldest first)'}")
        else:
            print(f"  Unexpected response: {data}")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


async def main():
    await debug_api_response("SAND-USDT")


if __name__ == "__main__":
    asyncio.run(main())
