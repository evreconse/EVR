"""
Check BingX symbols without numeric prefixes
"""
import asyncio
import sys
import os
import re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from exchange.bingx_fetcher import BingXFetcher

async def main():
    api_key = "LY4rJlgmbxIhuniKUTibI16IhHnu937kDdPLOBfbo7BnfjHR3g6e3dUXTWBOj4NT4ZV7l4BRUed9ryYOnFFQ"
    api_secret = "q9DmZfQGGFjqN2yC8VGXVVEw5Ecws2mSmYOHGEEXTKWKIjgcafyrvcQrhKg4YAlBrj8rWaUUVxLiaOjA"
    fetcher = BingXFetcher(api_key=api_key, api_secret=api_secret)
    
    contracts = await fetcher.get_contracts()
    print(f"Total contracts: {len(contracts)}")
    print()
    
    # Filter for USDT perpetual
    usdt_symbols = [c.get("symbol", "") for c in contracts if c.get("symbol", "").endswith("-USDT")]
    print(f"Total USDT perpetual: {len(usdt_symbols)}")
    print()
    
    # Separate into normal and prefixed
    normal_symbols = []
    prefixed_symbols = []
    
    for symbol in usdt_symbols:
        # Remove -USDT suffix
        base = symbol.replace("-USDT", "")
        if base[0].isdigit():
            prefixed_symbols.append(symbol)
        else:
            normal_symbols.append(symbol)
    
    print(f"Normal symbols (no numeric prefix): {len(normal_symbols)}")
    print(f"Prefixed symbols (with numeric prefix): {len(prefixed_symbols)}")
    print()
    
    print("First 30 normal symbols:")
    for s in normal_symbols[:30]:
        print(f"  {s}")
    
    print()
    print("All prefixed symbols:")
    for s in prefixed_symbols:
        print(f"  {s}")
    
    print()
    print("Checking if base coins exist without prefix:")
    # Extract base names from prefixed symbols
    base_names = set()
    for s in prefixed_symbols:
        # Remove numeric prefix and -USDT
        base = re.sub(r'^[0-9]+', '', s.replace("-USDT", ""))
        base_names.add(base)
    
    print(f"Base names from prefixed symbols: {sorted(base_names)}")
    print()
    
    # Check if these base names exist as normal symbols
    for base in sorted(base_names):
        normal = f"{base}-USDT"
        if normal in normal_symbols:
            print(f"  {base}: EXISTS as {normal}")
        else:
            print(f"  {base}: NOT FOUND as normal symbol")

if __name__ == "__main__":
    asyncio.run(main())
