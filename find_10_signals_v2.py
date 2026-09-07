#!/usr/bin/env python3
"""
Find 10 historical LW-001 signals with CORRECTED formula.

User's specification:
- Body = abs(Open - Close)
- Lower Wick = min(Open, Close) - Low
- Qualified = (Close < Open) AND (Lower Wick >= 2 * Body)
"""

import asyncio
import os
from datetime import UTC, datetime, timedelta
from dotenv import load_dotenv

import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher
from src.notification.telegram_service import TelegramService, TelegramConfig


TOP_20_COINS = [
    "BTC-USDT", "ETH-USDT", "BNB-USDT", "SOL-USDT", "XRP-USDT",
    "ADA-USDT", "DOGE-USDT", "AVAX-USDT", "TRX-USDT", "DOT-USDT",
    "LINK-USDT", "MATIC-USDT", "SHIB-USDT", "LTC-USDT", "BCH-USDT",
    "PEPE-USDT", "NEAR-USDT", "UNI-USDT", "APT-USDT", "XLM-USDT"
]


async def get_universe(fetcher: BingXFetcher) -> list[str]:
    """Get universe of 250 USDT perpetual coins excluding TOP-20."""
    print("Fetching USDT perpetual symbols...")
    symbols = await fetcher.get_usdt_perpetual_symbols()
    print(f"Total USDT Perpetual symbols: {len(symbols)}")
    
    # Filter out TOP-20
    remaining = [s for s in symbols if s not in TOP_20_COINS]
    print(f"Excluded TOP-20: {len(TOP_20_COINS)} coins")
    print(f"Remaining: {len(remaining)} coins")
    
    # Select first 250 from remaining
    universe = remaining[:250]
    print(f"Selected universe: {len(universe)} coins")
    
    return universe


def check_lw001_corrected(open_price: float, high_price: float, low_price: float, close_price: float) -> tuple[bool, dict]:
    """
    Check if candle meets LW-001 conditions using USER'S SPECIFIED FORMULA.
    
    User's specification:
    - Body = abs(Open - Close)
    - Lower Wick = min(Open, Close) - Low
    - Qualified = (Close < Open) AND (Lower Wick >= 2 * Body)
    """
    # Condition 1: Red candle (Close < Open)
    is_red = close_price < open_price
    
    if not is_red:
        return False, {"reason": "Not a red candle"}
    
    # Calculate body (absolute value)
    body = abs(open_price - close_price)
    
    if body == 0:
        return False, {"reason": "Zero body"}
    
    # Calculate lower wick (min(Open, Close) - Low)
    lower_wick = min(open_price, close_price) - low_price
    
    # Calculate upper wick (informational only)
    upper_wick = high_price - max(open_price, close_price)
    
    # Calculate ratio
    ratio = lower_wick / body
    
    # Condition 2: Lower Wick >= 2 * Body (i.e., ratio >= 2.0)
    qualified = ratio >= 2.0
    
    details = {
        "is_red": is_red,
        "body": body,
        "lower_wick": lower_wick,
        "upper_wick": upper_wick,
        "ratio": ratio,
        "qualified": qualified,
    }
    
    return qualified, details


async def find_signals(fetcher: BingXFetcher, universe: list[str], limit: int = 10) -> list[dict]:
    """
    Find exactly `limit` qualified signals on different coins.
    
    Search historical M15 candles from the last 7 days.
    """
    print(f"\nSearching for {limit} signals on {len(universe)} coins...")
    
    # Search period: last 7 days
    end_time = int(datetime.now(UTC).timestamp() * 1000)
    start_time = int((datetime.now(UTC) - timedelta(days=7)).timestamp() * 1000)
    
    signals = []
    seen_coins = set()
    
    for symbol in universe:
        if len(signals) >= limit:
            break
        
        if symbol in seen_coins:
            continue
        
        try:
            # Fetch M15 candles
            klines = await fetcher.get_klines(
                symbol=symbol,
                interval="15m",
                limit=500,  # Max candles per request
                start_time=start_time,
                end_time=end_time
            )
            
            if not klines:
                continue
            
            # Check each candle (newest first)
            for kline in reversed(klines):
                if len(signals) >= limit:
                    break
                
                # Parse kline data
                open_price = float(kline['open'])
                high_price = float(kline['high'])
                low_price = float(kline['low'])
                close_price = float(kline['close'])
                volume = float(kline['volume'])
                timestamp = int(kline['time'])
                event_time = datetime.fromtimestamp(timestamp / 1000, tz=UTC)
                
                # Check LW-001 conditions with CORRECTED formula
                qualified, details = check_lw001_corrected(open_price, high_price, low_price, close_price)
                
                if qualified:
                    signals.append({
                        "symbol": symbol,
                        "event_time": event_time,
                        "open": open_price,
                        "high": high_price,
                        "low": low_price,
                        "close": close_price,
                        "volume": volume,
                        "body": details["body"],
                        "lower_wick": details["lower_wick"],
                        "upper_wick": details["upper_wick"],
                        "ratio": details["ratio"],
                    })
                    seen_coins.add(symbol)
                    print(f"Signal {len(signals)}/{limit}: {symbol} at {event_time} (ratio={details['ratio']:.2f}x)")
                    break  # Only take one signal per coin
            
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            continue
    
    print(f"\nFound {len(signals)} signals")
    return signals


def format_msk_time(utc_time: datetime) -> str:
    """Format UTC time as MSK (UTC+3)."""
    msk_time = utc_time.replace(hour=(utc_time.hour + 3) % 24)
    return msk_time.strftime("%Y-%m-%d %H:%M:%S MSK")


def verify_signals(signals: list[dict]) -> list[dict]:
    """
    Verify each signal meets LW-001 conditions.
    """
    print("\n=== VERIFICATION TABLE ===")
    print(f"{'#':<3} {'Symbol':<12} {'Time MSK':<20} {'Red':<4} {'Body':<10} {'Lower Wick':<12} {'Ratio':<8} {'Qualified':<10}")
    print("-" * 90)
    
    verified = []
    for i, signal in enumerate(signals, 1):
        open_price = signal["open"]
        high_price = signal["high"]
        low_price = signal["low"]
        close_price = signal["close"]
        
        # Re-calculate with CORRECTED formula
        is_red = close_price < open_price
        body = abs(open_price - close_price)
        lower_wick = min(open_price, close_price) - low_price
        ratio = lower_wick / body if body > 0 else 0.0
        qualified = is_red and ratio >= 2.0
        
        time_msk = format_msk_time(signal["event_time"])
        
        print(f"{i:<3} {signal['symbol']:<12} {time_msk:<20} {'YES' if is_red else 'NO':<4} {body:<10.4f} {lower_wick:<12.4f} {ratio:<8.2f} {'YES' if qualified else 'NO':<10}")
        
        if qualified:
            verified.append(signal)
        else:
            print(f"  WARNING: Signal {i} FAILED verification")
    
    print("-" * 90)
    print(f"Verified: {len(verified)}/{len(signals)} signals")
    
    return verified


async def main():
    """Main execution."""
    # Load .env file to ensure environment variables are set
    from dotenv import load_dotenv
    load_dotenv()
    
    # Initialize BingX fetcher
    print("Initializing BingX fetcher...")
    fetcher = BingXFetcher()
    
    # Get universe
    universe = await get_universe(fetcher)
    
    # Find signals with CORRECTED formula
    signals = await find_signals(fetcher, universe, limit=10)
    
    if len(signals) < 10:
        print(f"\nERROR: Only found {len(signals)} signals, need 10")
        return
    
    # Verify signals
    verified = verify_signals(signals)
    
    if len(verified) < 10:
        print(f"\nERROR: Only {len(verified)} signals verified, need 10")
        return
    
    print("\n=== COMPLETED ===")
    print(f"Found and verified {len(verified)} signals on 10 different coins")
    print("\nNOTE: Telegram sending disabled for diagnostic phase.")
    print("Please verify the signals above before proceeding to Telegram delivery.")


if __name__ == "__main__":
    asyncio.run(main())
