#!/usr/bin/env python3
"""
Find 10 historical LW-001 signals with CANONICAL formulas and VOLUME FILTER >= 1.5x over AVG previous 20 candles.

Production LW-001 Specification:
- Red candle only (Close < Open)
- Range >= 4.5% ((High - Low) / Open * 100)
- Body >= 0.8% (abs(Close - Open) / Open * 100)
- LW/Body >= 1.3x (Lower_Wick / abs(Close - Open))
- LW/Range >= 55% (Lower_Wick / (High - Low) * 100)
- Open->Low <= -2.5% ((Low - Open) / Open * 100)
- Volume Ratio >= 1.5x (Current_Vol / Avg(Prev_20_Volumes))
- ALL conditions must pass (AND logic)
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


def check_lw001_canonical(
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
    current_volume: float,
    previous_20_volumes: list[float]
) -> tuple[bool, dict]:
    """
    Check if candle meets LW-001 conditions using CANONICAL SPECIFICATION.
    
    All 6 conditions must pass (AND logic):
    1. Red candle: Close < Open
    2. Range >= 4.5%: (High - Low) / Open * 100
    3. Body >= 0.8%: abs(Close - Open) / Open * 100
    4. LW/Body >= 1.3x: Lower_Wick / abs(Close - Open)
    5. LW/Range >= 55%: Lower_Wick / (High - Low) * 100
    6. Open->Low <= -2.5%: (Low - Open) / Open * 100
    7. Volume Ratio >= 1.5x: Current_Vol / Avg(Prev_20_Volumes)
    """
    from src.strategy.lw001_canonical import check_lw001_signal
    
    result = check_lw001_signal(
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
        current_volume=current_volume,
        previous_20_volumes=previous_20_volumes
    )
    
    return result.qualified, {
        "is_red": result.metrics.is_red,
        "body": abs(close_price - open_price),
        "lower_wick": min(open_price, close_price) - low_price,
        "upper_wick": high_price - max(open_price, close_price),
        "ratio": result.metrics.lw_body_ratio,
        "range_pct": result.metrics.range_pct,
        "body_pct": result.metrics.body_pct,
        "lw_range_pct": result.metrics.lw_range_pct,
        "open_to_low_pct": result.metrics.open_to_low_pct,
        "volume_ratio": result.metrics.volume_ratio,
        "qualified": result.qualified,
        "failed_conditions": result.failed_conditions
    }


def check_volume_filter(current_volume: float, previous_20_volumes: list[float]) -> tuple[bool, dict]:
    """
    Check if current volume is >= 1.5x average of previous 20 volumes.
    
    Production specification:
    - Volume Ratio = Current_Vol / Avg(Previous_20_Volumes)
    - Threshold: >= 1.5x
    """
    if len(previous_20_volumes) < 20:
        return False, {"reason": "Not enough previous candles (need 20)"}
    
    avg_previous_volume = sum(previous_20_volumes) / len(previous_20_volumes)
    volume_ratio = current_volume / avg_previous_volume if avg_previous_volume > 0 else 0.0
    volume_qualified = volume_ratio >= 1.5
    
    details = {
        "current_volume": current_volume,
        "avg_previous_volume": avg_previous_volume,
        "volume_ratio": volume_ratio,
        "volume_qualified": volume_qualified,
    }
    
    return volume_qualified, details


async def find_signals(fetcher: BingXFetcher, universe: list[str], limit: int = 10) -> list[dict]:
    """
    Find exactly `limit` qualified signals on different coins.
    
    Search historical M15 candles from the last 7 days.
    Uses CANONICAL LW-001 check with 6 conditions + Volume Ratio.
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
            # Fetch M15 candles (need more for volume filter - 20 previous)
            klines = await fetcher.get_klines(
                symbol=symbol,
                interval="15m",
                limit=1000,  # More candles for volume filter
                start_time=start_time,
                end_time=end_time
            )
            
            if not klines or len(klines) < 21:  # Need at least 21 candles (current + 20 previous)
                continue
            
            # Check each candle (newest first, skip first 20 to ensure we have previous candles)
            for i in range(len(klines) - 1, 20, -1):  # Start from end, need at least 20 previous
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
                
                # Get previous 20 volumes
                previous_20_volumes = [float(klines[j]['volume']) for j in range(i - 20, i)]
                
                # Check LW-001 conditions with CANONICAL check (all 6 conditions)
                lw_qualified, lw_details = check_lw001_canonical(
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=close_price,
                    current_volume=volume,
                    previous_20_volumes=[float(klines[j]['volume']) for j in range(i - 20, i)]
                )
                
                if lw_qualified:
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
                        "range_pct": lw_details["range_pct"],
                        "body_pct": lw_details["body_pct"],
                        "lw_range_pct": lw_details["lw_range_pct"],
                        "open_to_low_pct": lw_details["open_to_low_pct"],
                        "volume_ratio": lw_details["volume_ratio"],
                    })
                    seen_coins.add(symbol)
                    print(f"Signal {len(signals)}/{limit}: {symbol} at {event_time} (ratio={lw_details['ratio']:.2f}x, vol_ratio={lw_details['volume_ratio']:.2f}x)")
                    break  # Only take one signal per coin
            
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            continue
    
    print(f"\nFound {len(signals)} signals")
    return signals


def format_utc_time(utc_time: datetime) -> str:
    """Format UTC time for display."""
    return utc_time.strftime("%d.%m.%Y %H:%M UTC")


def verify_signals(signals: list[dict]) -> list[dict]:
    """
    Verify each signal meets LW-001 canonical conditions (all 6 + volume).
    """
    print("\n=== VERIFICATION TABLE ===")
    print(f"{'#':<3} {'Symbol':<12} {'Time UTC':<20} {'Red':<4} {'LW/Body':<8} {'LW/Range':<8} {'Range%':<7} {'Body%':<7} {'O->L%':<7} {'VolRatio':<8} {'OK':<4}")
    print("-" * 120)
    
    verified = []
    for i, signal in enumerate(signals, 1):
        open_price = signal["open"]
        high_price = signal["high"]
        low_price = signal["low"]
        close_price = signal["close"]
        volume = signal["volume"]
        
        # Re-calculate with CANONICAL formulas
        from src.strategy.lw001_canonical import check_lw001_signal
        result = check_lw001_signal(
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            current_volume=volume,
            previous_20_volumes=[volume] * 20  # Placeholder for verification
        )
        
        qualified = result.qualified
        m = result.metrics
        
        time_utc = format_utc_time(signal["event_time"])
        
        print(f"{i:<3} {signal['symbol']:<12} {time_utc:<20} {'YES' if m.is_red else 'NO':<4} {m.lw_body_ratio:<8.2f} {m.lw_range_pct:<8.1f} {m.range_pct:<7.1f} {m.body_pct:<7.1f} {m.open_to_low_pct:<7.1f} {m.volume_ratio:<8.2f} {'YES' if qualified else 'NO':<4}")
        
        if qualified:
            verified.append(signal)
        else:
            print(f"  WARNING: Signal {i} FAILED verification - {result.failed_conditions}")
    
    print("-" * 120)
    print(f"Verified: {len(verified)}/{len(signals)} signals")
    
    return verified


async def main():
    """Main execution."""
    load_dotenv()
    
    print("Initializing BingX fetcher...")
    fetcher = BingXFetcher()
    
    universe = await get_universe(fetcher)
    
    # Find signals with CANONICAL LW-001 check (all 6 conditions + volume)
    signals = await find_signals(fetcher, universe, limit=10)
    
    if len(signals) < 10:
        print(f"\nERROR: Only found {len(signals)} signals, need 10")
        print("This may be due to the volume filter being too restrictive.")
        print("Consider extending the search period.")
        return
    
    # Verify signals with canonical check
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
