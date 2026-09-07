#!/usr/bin/env python3
"""Add CoinGlass API key to .env file."""

with open(".env", "a") as f:
    f.write("\nEVRECONSE_COINGLASS_API_KEY=eddcf24e1c8f492298d7ad7d2f8a0702\n")

print("CoinGlass API key added to .env")
