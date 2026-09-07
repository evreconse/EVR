#!/usr/bin/env python3
"""
Fetch Top-21 to Top-250 symbols from Coinglass API
"""

import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

COINGLASS_API_KEY = os.getenv("EVRECONSE_COINGLASS_API_KEY")


async def fetch_coinglass_rankings():
    """Fetch cryptocurrency rankings from Coinglass API."""
    if not COINGLASS_API_KEY:
        print("ERROR: COINGLASS_API_KEY not found in .env")
        return []
    
    # Try different endpoints
    urls = [
        "https://open-api-v4.coinglass.com/api/v2/ranking/derivatives",
        "https://api.coinglass.com/public/v2/ranking/derivatives",
        "https://open-api-v4.coinglass.com/api/futures/ranking",
    ]
    
    headers = {
        "CG-API-KEY": COINGLASS_API_KEY
    }
    
    params = {
        "size": 250  # Get top 250
    }
    
    for url in urls:
        try:
            print(f"Trying endpoint: {url}")
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as resp:
                    print(f"Status: {resp.status}")
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"Response keys: {data.keys()}")
                        return data.get("data", data)
                    else:
                        text = await resp.text()
                        print(f"Response: {text}")
        except Exception as e:
            print(f"ERROR with {url}: {e}")
    
    print("All endpoints failed")
    return []


async def main():
    print("="*100)
    print("FETCHING COINGLASS SYMBOLS (Top-21 to Top-250)")
    print("="*100)
    print()
    
    rankings = await fetch_coinglass_rankings()
    
    if not rankings:
        print("Failed to fetch rankings")
        return
    
    print(f"Total rankings fetched: {len(rankings)}")
    print()
    
    # Top-20 to exclude
    top_20_exclude = {
        "BTC", "ETH", "BNB", "SOL", "XRP",
        "DOGE", "ADA", "TRX", "TON", "AVAX",
        "SHIB", "DOT", "LINK", "MATIC", "PEPE",
        "LTC", "ATOM", "NEAR", "OP", "ARB"
    }
    
    # Extract symbols from rank 21-250
    mid_tier_symbols = []
    
    for item in rankings:
        rank = item.get("rank", 0)
        symbol = item.get("symbol", "")
        
        # Skip if not in range 21-250
        if rank < 21 or rank > 250:
            continue
        
        # Skip if in top-20
        if symbol in top_20_exclude:
            continue
        
        # Convert to BingX format (add -USDT)
        bingx_symbol = f"{symbol}-USDT"
        mid_tier_symbols.append(bingx_symbol)
    
    print(f"Mid-tier symbols (rank 21-250, excluding top-20): {len(mid_tier_symbols)}")
    print()
    
    # Output as Python list
    print("Python list for realtime_lw001_monitor.py:")
    print()
    print("MID_TIER_SYMBOLS = [")
    for i, symbol in enumerate(mid_tier_symbols, 1):
        if i % 10 == 1:
            print("    ", end="")
        print(f'"{symbol}"', end="")
        if i < len(mid_tier_symbols):
            print(", ", end="")
        else:
            print()
        if i % 10 == 0:
            print()
    print("]")
    print()
    
    # Save to file
    with open("coinglass_mid_tier_symbols.txt", "w") as f:
        for symbol in mid_tier_symbols:
            f.write(f"{symbol}\n")
    
    print(f"Saved to coinglass_mid_tier_symbols.txt")


if __name__ == "__main__":
    asyncio.run(main())
