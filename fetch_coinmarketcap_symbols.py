#!/usr/bin/env python3
"""
Fetch Top-21 to Top-250 symbols from CoinMarketCap API
"""

import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()

COINMARKETCAP_API_KEY = "1d94e9d6928a4abebbf04fae9cc7f417"


async def fetch_coinmarketcap_rankings():
    """Fetch cryptocurrency rankings from CoinMarketCap API."""
    if not COINMARKETCAP_API_KEY:
        print("ERROR: COINMARKETCAP_API_KEY not provided")
        return []
    
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
    
    headers = {
        "X-CMC_PRO_API_KEY": COINMARKETCAP_API_KEY,
        "Accept": "application/json"
    }
    
    params = {
        "start": 1,
        "limit": 250,
        "convert": "USD"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", [])
                else:
                    print(f"ERROR: API returned status {resp.status}")
                    text = await resp.text()
                    print(f"Response: {text}")
                    return []
    except Exception as e:
        print(f"ERROR: {e}")
        return []


async def main():
    print("="*100)
    print("FETCHING COINMARKETCAP SYMBOLS (Top-21 to Top-250)")
    print("="*100)
    print()
    
    rankings = await fetch_coinmarketcap_rankings()
    
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
        rank = item.get("cmc_rank", 0)
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
    
    # Save to file
    with open("coinmarketcap_mid_tier_symbols.txt", "w", encoding="utf-8") as f:
        for symbol in mid_tier_symbols:
            f.write(f"{symbol}\n")
    
    print(f"Saved to coinmarketcap_mid_tier_symbols.txt")
    print(f"Total symbols: {len(mid_tier_symbols)}")
    
    # Show first 30 symbols
    print()
    print("First 30 symbols:")
    for i, symbol in enumerate(mid_tier_symbols[:30], 1):
        try:
            print(f"  {i}. {symbol}")
        except:
            print(f"  {i}. [encoding error]")


if __name__ == "__main__":
    asyncio.run(main())
