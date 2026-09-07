¶"""
Check actual BingX symbols to see format
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from exchange.bingx_fetcher import BingXFetcher

async def main():
    api_key = "LY4rJlgmbxIhuniKUTibI16IhHnu937kDdPLOBfbo7BnfjHR3g6e3dUXTWBOj4NT4ZV7l4BRUed9ryYOnFFQ"
    api_secret = "q9DmZfQGGFjqN2yC8VGXVVEw5Ecws2mSmYOHGEEXTKWKIjgcafyrvcQrhKg4YAlBrj8rWaUUVxLiaOjA"
    fetcher = BingXFetcher(api_key=api_key, api_secret=api_secret)
    
    contracts = await fetcher.get_contracts()
    print(f"Total contracts: {len(contracts)}")
    print()
    
    # Show first 30 contracts
    print("First 30 contracts from BingX API:")
    for i, contract in enumerate(contracts[:30]):
        symbol = contract.get("symbol", "")
        print(f"  {i+1}. {symbol}")
    
    print()
    print("Contracts starting with numbers:")
    for contract in contracts:
        symbol = contract.get("symbol", "")
        if symbol and symbol[0].isdigit():
            print(f"  {symbol}")

if __name__ == "__main__":
    asyncio.run(main())
¶*cascade082Rfile:///C:/Users/user/Documents/Default%20Project/EVRECONSE/check_bingx_symbols.py