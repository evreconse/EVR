’"""
Verify coin list on Bybit Futures.
"""
import asyncio
import aiohttp

BYBIT_FUTURES_URL = "https://api.bybit.com/v5/market/tickers?category=linear"

SYMBOLS = [
    "INJUSDT", "SEIUSDT", "TIAUSDT", "SUIUSDT", "WIFUSDT",
    "BONKUSDT", "PEPEUSDT", "FLOKIUSDT", "TURBOUSDT", "BRETTUSDT",
    "JASMYUSDT", "ARKMUSDT", "APTUSDT", "NOTUSDT", "WUSDT",
    "PYTHUSDT", "JTOUSDT", "DYDXUSDT", "OPUSDT", "ARBUSDT"
]

async def verify_coins():
    """Verify each symbol exists on Bybit Futures."""
    async with aiohttp.ClientSession() as session:
        async with session.get(BYBIT_FUTURES_URL) as resp:
            text = await resp.text()
            print(f"Response status: {resp.status}")
            print(f"Response content (first 500 chars): {text[:500]}")
            
            try:
                import json
                data = json.loads(text)
            except Exception as e:
                print(f"JSON decode error: {e}")
                return
            
            if data.get("retCode") != 0:
                print(f"API Error: {data.get('retMsg')}")
                return
            
            available_symbols = set()
            for ticker in data.get("result", {}).get("list", []):
                symbol = ticker.get("symbol")
                if symbol:
                    available_symbols.add(symbol)
            
            print(f"Total symbols on Bybit Futures: {len(available_symbols)}")
            print()
            
            results = []
            for symbol in SYMBOLS:
                exists = symbol in available_symbols
                status = "[OK]" if exists else "[MISSING]"
                results.append((symbol, exists))
                print(f"{status} {symbol}")
            
            print()
            missing = [s for s, e in results if not e]
            if missing:
                print(f"MISSING SYMBOLS ({len(missing)}): {', '.join(missing)}")
            else:
                print("All symbols exist on Bybit Futures!")

if __name__ == "__main__":
    asyncio.run(verify_coins())
è *cascade08èë*cascade08ëù *cascade08ù±*cascade08±µ *cascade08µ×*cascade08×Ø *cascade08ØÜ*cascade08ÜÝ *cascade08ÝÈ*cascade08È’ *cascade082Kfile:///C:/Users/user/Documents/Default%20Project/EVRECONSE/verify_coins.py