"""
Fetch all USDT Perpetual symbols from Bybit excluding TOP-20.

This script:
1. Fetches all USDT Perpetual trading pairs from Bybit
2. Sorts by 24h volume to identify TOP-20
3. Excludes TOP-20
4. Returns the remaining symbols for strategy use
"""
import asyncio
import aiohttp
import json
from typing import List, Set

BYBIT_TICKERS_URL = "https://api.bybit.com/v5/market/tickers?category=linear"

TOP_20_EXCLUDE = {
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "LINKUSDT",
    "MATICUSDT", "DOTUSDT", "LTCUSDT", "SHIBUSDT", "PEPEUSDT",
    "BCHUSDT", "NEARUSDT", "UNIUSDT", "XLMUSDT", "ATOMUSDT"
}

async def fetch_usdt_perpetual_symbols() -> List[str]:
    """
    Fetch all USDT Perpetual symbols from Bybit excluding TOP-20.
    
    Returns:
        List of symbol names (e.g., ["INJUSDT", "SEIUSDT", ...])
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(BYBIT_TICKERS_URL) as resp:
            text = await resp.text()
            
            if resp.status != 200:
                print(f"HTTP {resp.status}: {text[:200]}")
                return []
            
            try:
                data = json.loads(text)
            except Exception as e:
                print(f"JSON decode error: {e}")
                print(f"Response (first 200 chars): {text[:200]}")
                return []
            
            if data.get("retCode") != 0:
                print(f"API Error: {data.get('retMsg')}")
                return []
            
            # Extract all USDT Perpetual symbols
            all_symbols = []
            for ticker in data.get("result", {}).get("list", []):
                symbol = ticker.get("symbol")
                if symbol and symbol.endswith("USDT"):
                    all_symbols.append(symbol)
            
            print(f"Total USDT Perpetual symbols found: {len(all_symbols)}")
            
            # Remove TOP-20 (manually defined to avoid API issues)
            filtered_symbols = [s for s in all_symbols if s not in TOP_20_EXCLUDE]
            
            print(f"After excluding TOP-20: {len(filtered_symbols)}")
            
            return filtered_symbols

async def main():
    """Main function to fetch and save symbols."""
    print("=" * 80)
    print("Fetching USDT Perpetual Symbols (excluding TOP-20)")
    print("=" * 80)
    print()
    
    symbols = await fetch_usdt_perpetual_symbols()
    
    if symbols:
        # Sort alphabetically
        symbols.sort()
        
        # Save to file
        with open("usdt_perpetual_symbols.txt", "w") as f:
            for symbol in symbols:
                f.write(f"{symbol}\n")
        
        # Also save as Python list for easy import
        with open("usdt_perpetual_symbols.py", "w") as f:
            f.write("# Auto-generated USDT Perpetual symbols (excluding TOP-20)\n")
            f.write("SYMBOLS = [\n")
            for i, symbol in enumerate(symbols):
                if i == len(symbols) - 1:
                    f.write(f'    "{symbol}"\n')
                else:
                    f.write(f'    "{symbol}",\n')
            f.write("]\n")
        
        print()
        print(f"Saved {len(symbols)} symbols to:")
        print("  - usdt_perpetual_symbols.txt")
        print("  - usdt_perpetual_symbols.py")
        print()
        print("First 20 symbols:")
        for symbol in symbols[:20]:
            print(f"  {symbol}")
        print()
        print("Last 20 symbols:")
        for symbol in symbols[-20:]:
            print(f"  {symbol}")
    else:
        print("No symbols found.")

if __name__ == "__main__":
    asyncio.run(main())
