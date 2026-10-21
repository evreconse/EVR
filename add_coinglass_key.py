#!/usr/bin/env python3
"""Add CoinGlass API key to .env file."""

with open(".env", "a") as f:
    f.write("\nEVRECONSE_COINGLASS_API_KEY=your_coinglass_api_key_here\n")

print("CoinGlass API key placeholder added to .env (replace with real key)")
