"""
Fetch all USDT Perpetual symbols from BingX excluding TOP-20.

Uses BingX API to get all perpetual contracts and excludes TOP-20 by market cap.
"""
import asyncio
import sys
import os
from typing import List

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from exchange.bingx_fetcher import BingXFetcher

# TOP-20 cryptocurrencies by market cap (to exclude)
TOP_20_EXCLUDE = {
    "BTC-USDT", "ETH-USDT", "BNB-USDT", "SOL-USDT", "XRP-USDT",
    "DOGE-USDT", "ADA-USDT", "AVAX-USDT", "TRX-USDT", "LINK-USDT",
    "MATIC-USDT", "DOT-USDT", "LTC-USDT", "SHIB-USDT", "PEPE-USDT",
    "BCH-USDT", "NEAR-USDT", "UNI-USDT", "XLM-USDT", "ATOM-USDT"
}

async def fetch_symbols() -> List[str]:
    """
    Fetch all USDT Perpetual symbols from BingX excluding TOP-20 and numeric prefixes.
    
    Returns:
        List of symbol names (e.g., ["INJ-USDT", "SEI-USDT", ...])
    """
    print("=" * 80)
    print("Fetching USDT Perpetual Symbols from BingX (excluding TOP-20 and numeric prefixes)")
    print("=" * 80)
    print()
    
    try:
        # Direct API keys for testing
        api_key = "LY4rJlgmbxIhuniKUTibI16IhHnu937kDdPLOBfbo7BnfjHR3g6e3dUXTWBOj4NT4ZV7l4BRUed9ryYOnFFQ"
        api_secret = "q9DmZfQGGFjqN2yC8VGXVVEw5Ecws2mSmYOHGEEXTKWKIjgcafyrvcQrhKg4YAlBrj8rWaUUVxLiaOjA"
        fetcher = BingXFetcher(api_key=api_key, api_secret=api_secret)
        all_symbols = await fetcher.get_usdt_perpetual_symbols()
        
        print(f"Total USDT Perpetual symbols found: {len(all_symbols)}")
        
        # Exclude TOP-20
        filtered_symbols = [s for s in all_symbols if s not in TOP_20_EXCLUDE]
        
        print(f"After excluding TOP-20: {len(filtered_symbols)}")
        
        # Exclude symbols with numeric prefixes (e.g., 1000PEPE-USDT, 1000000BABYDOGE-USDT)
        # These are micro-tokens with very small prices
        clean_symbols = [s for s in filtered_symbols if not s[0].isdigit()]
        
        print(f"After excluding numeric prefixes: {len(clean_symbols)}")
        
        # Convert to Bybit format (USDT suffix instead of -USDT)
        bybit_format = [s.replace("-USDT", "USDT") for s in clean_symbols]
        
        return bybit_format
        
    except Exception as e:
        print(f"Error fetching symbols: {e}")
        return []

async def main():
    """Main function to fetch and save symbols."""
    try:
        symbols = await fetch_symbols()
        
        if symbols:
            # Sort alphabetically
            symbols.sort()
            
            # Save to file
            with open("usdt_perpetual_symbols.txt", "w") as f:
                for symbol in symbols:
                    f.write(f"{symbol}\n")
            
            # Save as Python list
            with open("usdt_perpetual_symbols.py", "w") as f:
                f.write("# Auto-generated USDT Perpetual symbols from BingX (excluding TOP-20)\n")
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
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
