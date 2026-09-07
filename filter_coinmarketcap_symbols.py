#!/usr/bin/env python3
"""
Filter CoinMarketCap symbols to remove inappropriate ones
"""

import re

# Read CoinMarketCap symbols
with open("coinmarketcap_mid_tier_symbols.txt", "r", encoding="utf-8") as f:
    symbols = [line.strip() for line in f if line.strip()]

print(f"Total symbols from CoinMarketCap: {len(symbols)}")

# Stablecoins and USD-related tokens to exclude
stablecoin_patterns = [
    r'^USD',  # Starts with USD
    r'^USDe',  # USDe
    r'^USDD',  # USDD
    r'^USDG',  # USDG
    r'^USDY',  # USDY
    r'^USDAI', # USDAI
    r'^USX',   # USX
    r'^USAT',  # USAT
    r'^USDon', # USDon
    r'^RLUSD', # RLUSD
    r'^FDUSD', # FDUSD
    r'^TUSD',  # TUSD
    r'^EURC',  # EURC
    r'^EURCV', # EURCV
    r'^FRAX',  # FRAX
    r'^GUSD',  # GUSD
    r'^PAXG',  # PAXG (gold-backed)
    r'^XAUt',  # XAUt (gold token)
    r'^PYUSD', # PYUSD
    r'^US0',   # USD0
    r'^FRXUSD', # FRXUSD
]

# Filter symbols
filtered_symbols = []

for symbol in symbols:
    # Check for non-ASCII characters
    try:
        symbol.encode('ascii')
    except UnicodeEncodeError:
        try:
            print(f"Skipping (non-ASCII): {symbol}")
        except:
            print("Skipping (non-ASCII): [encoding error]")
        continue
    
    # Check for stablecoin patterns
    is_stablecoin = False
    for pattern in stablecoin_patterns:
        if re.match(pattern, symbol):
            is_stablecoin = True
            break
    
    if is_stablecoin:
        print(f"Skipping (stablecoin): {symbol}")
        continue
    
    # Check for obvious non-trading symbols
    if any(x in symbol for x in ['STABLE', 'NFT', 'DOG', 'CAT', 'MEME']):
        print(f"Skipping (non-trading): {symbol}")
        continue
    
    filtered_symbols.append(symbol)

print(f"\nAfter filtering: {len(filtered_symbols)} symbols")

# Save filtered symbols
with open("filtered_mid_tier_symbols.txt", "w", encoding="utf-8") as f:
    for symbol in filtered_symbols:
        f.write(f"{symbol}\n")

print(f"Saved to filtered_mid_tier_symbols.txt")

# Show first 30 symbols
print("\nFirst 30 filtered symbols:")
for i, symbol in enumerate(filtered_symbols[:30], 1):
    print(f"  {i}. {symbol}")

# Generate Python list
print("\nPython list for realtime_lw001_monitor.py:")
print("MID_TIER_SYMBOLS = [")
for i, symbol in enumerate(filtered_symbols):
    if i == len(filtered_symbols) - 1:
        print(f'    "{symbol}"')
    else:
        print(f'    "{symbol}",')
print("]")
