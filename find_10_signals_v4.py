#!/usr/bin/env python3
"""
Find 10 historical LW-001 signals with CORRECTED formulas and VOLUME FILTER >= 1.5x.

User's specification:
- Body = Open - Close (for red candles)
- Lower Wick = Close - Low (for red candles)
- Wick/Body = (Close - Low) / (Open - Close)
- Qualified = (Close < Open) AND (Wick/Body >= 2.0)
- Volume Filter: Current Volume >= 1.5x max(previous 15 volumes)
"""

import asyncio
import os
from datetime import UTC, datetime, timedelta
from dotenv import load_dotenv

import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


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
    
    remaining = [s for s in symbols if s not in TOP_20_COINS]
    print(f"Excluded TOP-20: {len(TOP_20_COINS)} coins")
    print(f"Remaining: {len(remaining)} coins")
    
    universe = remaining[:250]
    print(f"Selected universe: {len(universe)} coins")
    
    return universe


def check_lw001_corrected(open_price: float, high_price: float, low_price: float, close_price: float) -> tuple[bool, dict]:
    """
    Check if candle meets LW-001 conditions using USER'S SPECIFIED FORMULA.
    
    User's specification:
    - Body = Open - Close (for red candles)
    - Lower Wick = Close - Low (for red candles)
    - Wick/Body = (Close - Low) / (Open - Close)
    - Qualified = (Close < Open) AND (Wick/Body >= 2.0)
    """
    # Condition 1: Red candle (Close < Open)
    is_red = close_price < open_price
    
    if not is_red:
        return False, {"reason": "Not a red candle"}
    
    # Calculate body (Open - Close for red candles)
    body = open_price - close_price
    
    if body <= 0:
        return False, {"reason": "Zero or negative body"}
    
    # Calculate lower wick (Close - Low for red candles)
    lower_wick = close_price - low_price
    
    # Calculate upper wick (informational only)
    upper_wick = high_price - open_price  # For red candles, Open is max(Open, Close)
    
    # Calculate ratio
    ratio = lower_wick / body
    
    # Condition 2: Wick/Body >= 2.0
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


def check_volume_filter(current_volume: float, previous_volumes: list[float]) -> tuple[bool, dict]:
    """
    Check if current volume is >= 1.5x max of previous 15 volumes.
    
    User's specification:
    - Current Volume >= 1.5x max(volume of previous 15 closed M15 candles)
    """
    if len(previous_volumes) < 15:
        return False, {"reason": "Not enough previous candles (need 15)"}
    
    max_previous_volume = max(previous_volumes)
    volume_ratio = current_volume / max_previous_volume if max_previous_volume > 0 else 0.0
    volume_qualified = volume_ratio >= 1.5
    
    details = {
        "current_volume": current_volume,
        "max_previous_volume": max_previous_volume,
        "volume_ratio": volume_ratio,
        "volume_qualified": volume_qualified,
    }
    
    return volume_qualified, details


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
            # Fetch M15 candles (need more for volume filter)
            klines = await fetcher.get_klines(
                symbol=symbol,
                interval="15m",
                limit=1000,  # More candles for volume filter
                start_time=start_time,
                end_time=end_time
            )
            
            if not klines or len(klines) < 16:  # Need at least 16 candles (current + 15 previous)
                continue
            
            # Check each candle (newest first, skip first 15 to ensure we have previous candles)
            for i in range(len(klines) - 1, 15, -1):  # Start from end, need at least 15 previous
                if len(signals) >= limit:
                    break
                
                # Parse kline data
                open_price = float(klines[i]['open'])
                high_price = float(klines[i]['high'])
                low_price = float(klines[i]['low'])
                close_price = float(klines[i]['close'])
                volume = float(klines[i]['volume'])
                timestamp = int(klines[i]['time'])
                event_time = datetime.fromtimestamp(timestamp / 1000, tz=UTC)
                
                # Get previous 15 volumes
                previous_volumes = [float(klines[j]['volume']) for j in range(i - 15, i)]
                
                # Check LW-001 conditions with CORRECTED formula
                lw_qualified, lw_details = check_lw001_corrected(open_price, high_price, low_price, close_price)
                
                if lw_qualified:
                    # Check volume filter with >= 1.5x threshold
                    vol_qualified, vol_details = check_volume_filter(volume, previous_volumes)
                    
                    if vol_qualified:
                        signals.append({
                            "symbol": symbol,
                            "event_time": event_time,
                            "timestamp_ms": timestamp,
                            "open": open_price,
                            "high": high_price,
                            "low": low_price,
                            "close": close_price,
                            "volume": volume,
                            "body": lw_details["body"],
                            "lower_wick": lw_details["lower_wick"],
                            "upper_wick": lw_details["upper_wick"],
                            "ratio": lw_details["ratio"],
                            "max_previous_volume": vol_details["max_previous_volume"],
                            "volume_ratio": vol_details["volume_ratio"],
                        })
                        seen_coins.add(symbol)
                        print(f"Signal {len(signals)}/{limit}: {symbol} at {event_time} (ratio={lw_details['ratio']:.2f}x, vol_ratio={vol_details['volume_ratio']:.2f}x)")
                        break  # Only take one signal per coin
            
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            continue
    
    print(f"\nFound {len(signals)} signals")
    return signals


def format_msk_time(utc_time: datetime) -> str:
    """Format UTC time as MSK (UTC+3)."""
    msk_time = utc_time.replace(hour=(utc_time.hour + 3) % 24)
    return msk_time.strftime("%d.%m.%Y %H:%M MSK")


def verify_signals(signals: list[dict]) -> list[dict]:
    """
    Verify each signal meets LW-001 conditions and volume filter.
    """
    print("\n=== VERIFICATION TABLE ===")
    print(f"{'#':<3} {'Symbol':<12} {'Time MSK':<20} {'Red':<4} {'Wick/Body':<10} {'VolRatio':<10} {'Qualified':<10}")
    print("-" * 90)
    
    verified = []
    for i, signal in enumerate(signals, 1):
        open_price = signal["open"]
        high_price = signal["high"]
        low_price = signal["low"]
        close_price = signal["close"]
        volume = signal["volume"]
        max_prev_vol = signal["max_previous_volume"]
        
        # Re-calculate with CORRECTED formula
        is_red = close_price < open_price
        body = open_price - close_price
        lower_wick = close_price - low_price
        ratio = lower_wick / body if body > 0 else 0.0
        lw_qualified = is_red and ratio >= 2.0
        
        # Re-calculate volume filter with >= 1.5x threshold
        vol_ratio = volume / max_prev_vol if max_prev_vol > 0 else 0.0
        vol_qualified = vol_ratio >= 1.5
        
        qualified = lw_qualified and vol_qualified
        
        time_msk = format_msk_time(signal["event_time"])
        
        print(f"{i:<3} {signal['symbol']:<12} {time_msk:<20} {'YES' if is_red else 'NO':<4} {ratio:<10.2f} {vol_ratio:<10.2f} {'YES' if qualified else 'NO':<10}")
        
        if qualified:
            verified.append(signal)
        else:
            print(f"  WARNING: Signal {i} FAILED verification")
    
    print("-" * 90)
    print(f"Verified: {len(verified)}/{len(signals)} signals")
    
    return verified


async def main():
    """Main execution."""
    load_dotenv()
    
    print("Initializing BingX fetcher...")
    fetcher = BingXFetcher()
    
    universe = await get_universe(fetcher)
    
    # Find signals with CORRECTED formula + VOLUME FILTER >= 1.5x
    signals = await find_signals(fetcher, universe, limit=10)
    
    if len(signals) < 10:
        print(f"\nERROR: Only found {len(signals)} signals, need 10")
        print("This may be due to the volume filter being too restrictive.")
        print("Consider extending the search period.")
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
