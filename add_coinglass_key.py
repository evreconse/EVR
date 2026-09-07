#!/usr/bin/env python3
"""Add CoinGlass API key to .env file."""

with open(".env", "a") as f:
    f.write("\nEVRECONSE_COINGLASS_API_KEY=***REMOVED***\n")

print("CoinGlass API key added to .env")
