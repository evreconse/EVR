#!/usr/bin/env python3
"""
Find 50-100 experimental candidates for large-sample research.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import json
import sys
sys.path.insert(0, "src")
sys.path.insert(0, ".")

from src.exchange.bingx_fetcher import BingXFetcher
from LW001_METRIC_SPEC import calculate_all_metrics


def format_msk_time(dt: datetime) -> str:
    """Format datetime to MSK string (UTC + 3 hours)."""
    msk_time = dt + timedelta(hours=3)
    return msk_time.strftime("%d.%m.%Y %H:%M MSK")


def format_utc_time(dt: datetime) -> str:
    """Format datetime to UTC string."""
    return dt.strftime("%d.%m.%Y %H:%M UTC")


def analyze_candle_geometry(open_price: float, high_price: float, low_price: float, close_price: float) -> dict:
    """Analyze candle geometry using canonical metrics."""
    is_red = close_price < open_price
    is_green = close_price > open_price
    
    # Use canonical metric calculation
    canonical_metrics = calculate_all_metrics(
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
        volume=1.0,  # Not used in this analysis
        reference_average_volume=1.0  # Not used in this analysis
    )
    
    # Calculate additional metrics for geometry analysis
    if is_red:
        body = open_price - close_price
        lower_wick = close_price - low_price
        upper_wick = high_price - open_price
    else:
        body = close_price - open_price
        lower_wick = open_price - low_price
        upper_wick = high_price - close_price
    
    total_range = high_price - low_price
    
    # Use canonical metrics for key calculations
    lower_wick_body_ratio = canonical_metrics.lower_wick_body_ratio
    lower_wick_range_ratio = canonical_metrics.lower_wick_range_pct / 100  # Convert % to ratio
    
    return {
        "is_red": is_red,
        "is_green": is_green,
        "body": body,
        "upper_wick": upper_wick,
        "lower_wick": lower_wick,
        "total_range": total_range,
        "lower_wick_body_ratio": lower_wick_body_ratio,
        "lower_wick_range_ratio": lower_wick_range_ratio,
        "body_percent": canonical_metrics.body_pct,
        "range_percent": canonical_metrics.range_pct,
        "open_to_low_percent": canonical_metrics.open_to_low_pct,
    }


def check_base_filter(open_price, high_price, low_price, close_price, volume, previous_volume):
    """Check base filter conditions (Formula 3)."""
    geo = analyze_candle_geometry(open_price, high_price, low_price, close_price)
    
    open_to_low_percent = geo["open_to_low_percent"]  # Use canonical
    vol_ratio = volume / previous_volume if previous_volume > 0 else 0
    lw_range_ratio = geo["lower_wick_range_ratio"]
    lw_body_ratio = geo["lower_wick_body_ratio"]
    range_percent = geo["range_percent"]  # Use canonical
    body_percent = geo["body_percent"]  # Use canonical
    
    return (
        geo["is_red"] and
        open_to_low_percent <= -2.5 and
        vol_ratio >= 0.75 and
        lw_range_ratio >= 0.40 and
        lw_body_ratio >= 0.75 and
        range_percent >= 2.5 and
        body_percent >= 0.30
    ), {
        "body_percent": body_percent,
        "range_percent": range_percent,
        "lower_wick_body_ratio": lw_body_ratio,
        "lower_wick_range_ratio": lw_range_ratio,
        "open_to_low_percent": open_to_low_percent,
        "volume_ratio": vol_ratio
    }


async def find_large_sample_candidates(limit=100):
    """Find large sample of experimental candidates."""
    print("=" * 100)
    print("FINDING LARGE SAMPLE OF EXPERIMENTAL CANDIDATES")
    print("=" * 100)
    
    fetcher = BingXFetcher()
    
    # Use the same universe
    universe = [
        "WLD-USDT", "ONDO-USDT", "TAO-USDT", "ENA-USDT", "WLFI-USDT",
        "INJ-USDT", "XPL-USDT", "FARTCOIN-USDT", "ICP-USDT", "SIREN-USDT",
        "ARB-USDT", "APT-USDT", "ZRO-USDT", "KITE-USDT", "CRV-USDT",
        "WIF-USDT", "PENGU-USDT", "VIRTUAL-USDT", "SEI-USDT", "HOME-USDT",
        "RENDER-USDT", "PENDLE-USDT", "POL-USDT", "OP-USDT", "SUI-USDT",
        "ORDI-USDT", "TIA-USDT", "JTO-USDT", "ALT-USDT", "MEW-USDT",
        "ONE-USDT", "LUNC-USDT", "10000SATS-USDT", "1000BONK-USDT",
        "ARPA-USDT", "BLUR-USDT", "CAKE-USDT", "CELO-USDT",
        "COMP-USDT", "DASH-USDT", "ENS-USDT", "FET-USDT", "FIL-USDT",
        "GALA-USDT", "GLM-USDT", "GRT-USDT", "IMX-USDT",
        "IOTA-USDT", "KAVA-USDT", "LDO-USDT", "MANA-USDT",
        "MASK-USDT", "MINA-USDT", "NMR-USDT",
        "PEOPLE-USDT", "QNT-USDT", "ROSE-USDT", "RUNE-USDT",
        "SAND-USDT", "SNX-USDT", "STG-USDT", "STORJ-USDT", "SUSHI-USDT",
        "THETA-USDT", "TLM-USDT", "WOO-USDT", "YFI-USDT",
        "ZEC-USDT", "ZEN-USDT",
    ]
    
    print(f"Universe size: {len(universe)} coins")
    
    # Search last 30 days for more data
    end_time = int(datetime.now(UTC).timestamp() * 1000)
    start_time = int((datetime.now(UTC) - timedelta(days=30)).timestamp() * 1000)
    
    candidates = []
    
    for symbol in universe:
        if len(candidates) >= limit:
            break
        
        try:
            klines = await fetcher.get_klines(
                symbol=symbol,
                interval="15m",
                limit=3000,
                start_time=start_time,
                end_time=end_time
            )
            
            if not klines or len(klines) < 2:
                continue
            
            # Check each candle (newest first)
            for i in range(len(klines) - 1, 0, -1):
                if len(candidates) >= limit:
                    break
                
                open_price = float(klines[i]['open'])
                high_price = float(klines[i]['high'])
                low_price = float(klines[i]['low'])
                close_price = float(klines[i]['close'])
                volume = float(klines[i]['volume'])
                timestamp = int(klines[i]['time'])
                event_time = datetime.fromtimestamp(timestamp / 1000, tz=UTC)
                
                previous_volume = float(klines[i - 1]['volume'])
                
                qualified, details = check_base_filter(
                    open_price, high_price, low_price, close_price,
                    volume, previous_volume
                )
                
                if qualified:
                    geo = analyze_candle_geometry(open_price, high_price, low_price, close_price)
                    
                    candidates.append({
                        "symbol": symbol,
                        "event_time": format_utc_time(event_time),
                        "event_time_msk": format_msk_time(event_time),
                        "timestamp_ms": timestamp,
                        "open": open_price,
                        "high": high_price,
                        "low": low_price,
                        "close": close_price,
                        "volume": volume,
                        "volume_ratio": details["volume_ratio"],
                        "lower_wick_body_ratio": geo["lower_wick_body_ratio"],
                        "lower_wick_range_ratio": geo["lower_wick_range_ratio"],
                        "formula_details": details
                    })
            
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            continue
    
    print(f"\nFound {len(candidates)} candidates")
    
    # Save results
    with open("large_sample_candidates.json", "w") as f:
        json.dump(candidates, f, indent=2, default=str)
    
    print(f"Saved to large_sample_candidates.json")
    
    return candidates


async def main():
    """Main function."""
    candidates = await find_large_sample_candidates(limit=100)
    
    print(f"\n{'=' * 100}")
    print("SAMPLE SUMMARY")
    print(f"{'=' * 100}")
    print(f"Total candidates: {len(candidates)}")
    
    if candidates:
        symbols = set(c["symbol"] for c in candidates)
        print(f"Unique symbols: {len(symbols)}")
        print(f"Symbols: {', '.join(sorted(symbols))}")


if __name__ == "__main__":
    asyncio.run(main())
