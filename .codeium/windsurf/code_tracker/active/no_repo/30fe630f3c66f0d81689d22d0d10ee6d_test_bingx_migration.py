‚"""
Test BingX API after migration to D: drive
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from exchange.bingx_fetcher import BingXFetcher

async def main():
    print("=" * 80)
    print("Testing BingX API from new location D:\\EVRECONSE_PROJECT")
    print("=" * 80)
    print()
    
    # Check Python location
    print(f"Python executable: {sys.executable}")
    print()
    
    try:
        # Load from .env (explicitly load since we're testing)
        from dotenv import load_dotenv
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        load_dotenv(env_path)
        
        # Verify env vars are loaded
        api_key = os.environ.get('EVRECONSE_EXCHANGE_API_KEY')
        api_secret = os.environ.get('EVRECONSE_EXCHANGE_API_SECRET')
        
        if not api_key or not api_secret:
            print(f"[ERROR] Environment variables not loaded from {env_path}")
            print(f"  API_KEY: {api_key}")
            print(f"  API_SECRET: {'FOUND' if api_secret else 'NOT FOUND'}")
            print(f"  Trying direct initialization...")
            
            # Fallback: direct initialization with known values
            api_key = "LY4rJlgmbxIhuniKUTibI16IhHnu937kDdPLOBfbo7BnfjHR3g6e3dUXTWBOj4NT4ZV7l4BRUed9ryYOnFFQ"
            api_secret = "q9DmZfQGGFjqN2yC8VGXVVEw5Ecws2mSmYOHGEEXTKWKIjgcafyrvcQrhKg4YAlBrj8rWaUUVxLiaOjA"
            fetcher = BingXFetcher(api_key=api_key, api_secret=api_secret)
        else:
            fetcher = BingXFetcher()
        
        print("[+] BingXFetcher initialized successfully")
        print()
        
        # Test getting contracts
        print("[*] Testing get_contracts()...")
        contracts = await fetcher.get_contracts()
        print(f"[+] get_contracts() returned {len(contracts)} contracts")
        print()
        
        # Test getting USDT perpetual symbols
        print("[*] Testing get_usdt_perpetual_symbols()...")
        symbols = await fetcher.get_usdt_perpetual_symbols()
        print(f"[+] get_usdt_perpetual_symbols() returned {len(symbols)} symbols")
        print()
        
        # Show first 5 symbols
        print("First 5 USDT perpetual symbols:")
        for s in symbols[:5]:
            print(f"  {s}")
        print()
        
        # Test getting klines for a symbol
        print("[*] Testing get_klines() for BTC-USDT...")
        klines = await fetcher.get_klines("BTC-USDT", interval="15m", limit=10)
        print(f"[+] get_klines() returned {len(klines)} candles")
        print()
        
        if klines:
            print("First candle:")
            print(f"  Time: {klines[0].get('time')}")
            print(f"  Open: {klines[0].get('open')}")
            print(f"  High: {klines[0].get('high')}")
            print(f"  Low: {klines[0].get('low')}")
            print(f"  Close: {klines[0].get('close')}")
            print()
        
        print("=" * 80)
        print("BingX API TEST PASSED")
        print("=" * 80)
        
    except Exception as e:
        print(f"[ERROR] BingX API test failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        print("=" * 80)
        print("BingX API TEST FAILED")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
Þ *cascade08Þ´ *cascade08´Å *cascade08Åô*cascade08ô‚ *cascade0824file:///D:/EVRECONSE_PROJECT/test_bingx_migration.py