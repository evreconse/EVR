#!/usr/bin/env python3
"""
Find 10 new historical candidates using experimental formulas.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import sys
sys.path.insert(0, "src")

from src.exchange.bingx_fetcher import BingXFetcher


def format_msk_time(dt: datetime) -> str:
    """Format datetime to MSK string (UTC + 3 hours)."""
    msk_time = dt + timedelta(hours=3)
    return msk_time.strftime("%d.%m.%Y %H:%M MSK")


def format_utc_time(dt: datetime) -> str:
    """Format datetime to UTC string."""
    return dt.strftime("%d.%m.%Y %H:%M UTC")


def analyze_candle_geometry(open_price: float, high_price: float, low_price: float, close_price: float) -> dict:
    """Analyze candle geometry."""
    is_red = close_price < open_price
    is_green = close_price > open_price
    
    if is_red:
        body = open_price - close_price
        lower_wick = close_price - low_price
        upper_wick = high_price - open_price
    else:
        body = close_price - open_price
        lower_wick = open_price - low_price
        upper_wick = high_price - close_price
    
    total_range = high_price - low_price
    
    lower_wick_body_ratio = lower_wick / body if body > 0 else 0
    lower_wick_range_ratio = lower_wick / total_range if total_range > 0 else 0
    
    return {
        "is_red": is_red,
        "is_green": is_green,
        "body": body,
        "lower_wick": lower_wick,
        "upper_wick": upper_wick,
        "total_range": total_range,
        "lower_wick_body_ratio": lower_wick_body_ratio,
        "lower_wick_range_ratio": lower_wick_range_ratio,
    }


# EXPERIMENTAL FORMULA 1: Red + LW/Range >= 30% + Volume >= 1.5x
def check_experimental_formula_1(open_price: float, high_price: float, low_price: float, close_price: float, 
                                  current_volume: float, previous_volume: float) -> tuple[bool, dict]:
    """
    Experimental Formula 1:
    - Red candle
    - Lower Wick / Range >= 30%
    - Volume >= 1.5x previous candle
    """
    geo = analyze_candle_geometry(open_price, high_price, low_price, close_price)
    
    is_red = geo["is_red"]
    lw_range_ratio = geo["lower_wick_range_ratio"]
    vol_ratio = current_volume / previous_volume if previous_volume > 0 else 0
    
    qualified = is_red and lw_range_ratio >= 0.3 and vol_ratio >= 1.5
    
    details = {
        "is_red": is_red,
        "lw_range_ratio": lw_range_ratio,
        "vol_ratio": vol_ratio,
        "qualified": qualified,
    }
    
    return qualified, details


# EXPERIMENTAL FORMULA 2: Red + LW/Body >= 1.0 + Volume >= 1.5x
def check_experimental_formula_2(open_price: float, high_price: float, low_price: float, close_price: float,
                                  current_volume: float, previous_volume: float) -> tuple[bool, dict]:
    """
    Experimental Formula 2:
    - Red candle
    - Lower Wick / Body >= 1.0
    - Volume >= 1.5x previous candle
    """
    geo = analyze_candle_geometry(open_price, high_price, low_price, close_price)
    
    is_red = geo["is_red"]
    lw_body_ratio = geo["lower_wick_body_ratio"]
    vol_ratio = current_volume / previous_volume if previous_volume > 0 else 0
    
    qualified = is_red and lw_body_ratio >= 1.0 and vol_ratio >= 1.5
    
    details = {
        "is_red": is_red,
        "lw_body_ratio": lw_body_ratio,
        "vol_ratio": vol_ratio,
        "qualified": qualified,
    }
    
    return qualified, details


# EXPERIMENTAL FORMULA 3: New comprehensive filter
def check_experimental_formula_3(open_price: float, high_price: float, low_price: float, close_price: float,
                                  current_volume: float, previous_volume: float) -> tuple[bool, dict]:
    """
    Experimental Formula 3:
    - Red candle
    - Open -> Low <= -2.5%
    - Volume Ratio >= 0.75
    - LW/Range >= 40%
    - LW/Body >= 0.75
    - Range% >= 2.5%
    - Body% >= 0.30%
    """
    geo = analyze_candle_geometry(open_price, high_price, low_price, close_price)
    
    is_red = geo["is_red"]
    
    # Open -> Low %
    open_to_low_percent = (low_price - open_price) / open_price * 100
    
    # Volume Ratio
    vol_ratio = current_volume / previous_volume if previous_volume > 0 else 0
    
    # LW/Range
    lw_range_ratio = geo["lower_wick_range_ratio"]
    
    # LW/Body
    lw_body_ratio = geo["lower_wick_body_ratio"]
    
    # Range%
    range_percent = geo["total_range"] / open_price * 100
    
    # Body%
    body_percent = geo["body"] / open_price * 100
    
    qualified = (
        is_red and
        open_to_low_percent <= -2.5 and
        vol_ratio >= 0.75 and
        lw_range_ratio >= 0.40 and
        lw_body_ratio >= 0.75 and
        range_percent >= 2.5 and
        body_percent >= 0.30
    )
    
    details = {
        "is_red": is_red,
        "open_to_low_percent": open_to_low_percent,
        "vol_ratio": vol_ratio,
        "lw_range_ratio": lw_range_ratio,
        "lw_body_ratio": lw_body_ratio,
        "range_percent": range_percent,
        "body_percent": body_percent,
        "qualified": qualified,
    }
    
    return qualified, details


async def find_experimental_candidates(formula_name: str, formula_func, limit: int = 10) -> list[dict]:
    """Find experimental candidates using specified formula."""
    print(f"\n{'=' * 100}")
    print(f"FINDING EXPERIMENTAL CANDIDATES - {formula_name}")
    print(f"{'=' * 100}")
    
    fetcher = BingXFetcher()
    
    # Use a predefined universe of popular coins (excluding TOP-20)
    # This is a sample universe - in production this would be fetched dynamically
    universe = [
        "WLD-USDT", "ONDO-USDT", "TAO-USDT", "ENA-USDT", "WLFI-USDT",
        "INJ-USDT", "CRLC-USDT", "XPL-USDT", "FARTCOIN-USDT", "FF-USDT",
        "TRUMP-USDT", "ICP-USDT", "DRAM-USDT", "SIREN-USDT", "ARB-USDT",
        "APT-USDT", "ZRO-USDT", "KITE-USDT", "MON-USDT", "CRV-USDT",
        "WIF-USDT", "PENGU-USDT", "VIRTUAL-USDT", "SEI-USDT", "HOME-USDT",
        "RENDER-USDT", "PENDLE-USDT", "POL-USDT", "OP-USDT", "SUI-USDT",
        "ORDI-USDT", "TIA-USDT", "JTO-USDT", "ALT-USDT", "MEW-USDT",
        "ONE-USDT", "LUNC-USDT", "10000SATS-USDT", "1000BONK-USDT",
        "ARPA-USDT", "BAND-USDT", "BLUR-USDT", "CAKE-USDT", "CELO-USDT",
        "COMP-USDT", "DASH-USDT", "ENS-USDT", "FET-USDT", "FIL-USDT",
        "GALA-USDT", "GLM-USDT", "GRT-USDT", "HOT-USDT", "IMX-USDT",
        "IOTA-USDT", "KAVA-USDT", "KLAY-USDT", "LDO-USDT", "MANA-USDT",
        "MASK-USDT", "MINA-USDT", "NMR-USDT", "OCEAN-USDT", "OMG-USDT",
        "PEOPLE-USDT", "QNT-USDT", "RNDR-USDT", "ROSE-USDT", "RUNE-USDT",
        "SAND-USDT", "SNX-USDT", "STG-USDT", "STORJ-USDT", "SUSHI-USDT",
        "THETA-USDT", "TLM-USDT", "WOO-USDT", "XEM-USDT", "YFI-USDT",
        "ZEC-USDT", "ZEN-USDT",
    ]
    
    # Remove TOP-20 by market cap (approximate list)
    top_20 = {
        "BTC-USDT", "ETH-USDT", "BNB-USDT", "SOL-USDT", "XRP-USDT",
        "DOGE-USDT", "ADA-USDT", "TRX-USDT", "TON-USDT", "AVAX-USDT",
        "SHIB-USDT", "LINK-USDT", "DOT-USDT", "MATIC-USDT", "NEAR-USDT",
        "UNI-USDT", "LTC-USDT", "ATOM-USDT", "XLM-USDT", "PEPE-USDT",
    }
    
    universe = [s for s in universe if s not in top_20]
    
    print(f"Universe size: {len(universe)} coins (excluding TOP-20)")
    
    # Search last 7 days
    end_time = int(datetime.now(UTC).timestamp() * 1000)
    start_time = int((datetime.now(UTC) - timedelta(days=7)).timestamp() * 1000)
    
    candidates = []
    seen_coins = set()
    
    for symbol in universe:
        if len(candidates) >= limit:
            break
        
        if symbol in seen_coins:
            continue
        
        try:
            klines = await fetcher.get_klines(
                symbol=symbol,
                interval="15m",
                limit=1000,
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
                
                qualified, details = formula_func(
                    open_price, high_price, low_price, close_price,
                    volume, previous_volume
                )
                
                if qualified:
                    geo = analyze_candle_geometry(open_price, high_price, low_price, close_price)
                    
                    candidates.append({
                        "symbol": symbol,
                        "event_time": event_time,
                        "timestamp_ms": timestamp,
                        "open": open_price,
                        "high": high_price,
                        "low": low_price,
                        "close": close_price,
                        "volume": volume,
                        "body": geo["body"],
                        "lower_wick": geo["lower_wick"],
                        "upper_wick": geo["upper_wick"],
                        "lower_wick_body_ratio": geo["lower_wick_body_ratio"],
                        "lower_wick_range_ratio": geo["lower_wick_range_ratio"],
                        "previous_volume": previous_volume,
                        "volume_ratio": details["vol_ratio"],
                        "formula_details": details,
                    })
                    seen_coins.add(symbol)
                    print(f"Candidate {len(candidates)}/{limit}: {symbol} at {event_time}")
                    print(f"  LW/Body: {geo['lower_wick_body_ratio']:.2f}x, LW/Range: {geo['lower_wick_range_ratio']:.2f}, Vol Ratio: {details['vol_ratio']:.2f}x")
                    break
        
        except Exception as e:
            continue
    
    print(f"\nFound {len(candidates)} candidates")
    return candidates


async def main():
    """Main function to find experimental candidates."""
    print("=" * 100)
    print("EXPERIMENTAL CANDIDATE SEARCH - RESEARCH TASK")
    print("=" * 100)
    print("\nDO NOT modify existing LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    # Find candidates using Formula 3 (new comprehensive filter)
    candidates_3 = await find_experimental_candidates(
        "Formula 3: Red + Open->Low <= -2.5% + Vol >= 0.75 + LW/Range >= 40% + LW/Body >= 0.75 + Range% >= 2.5% + Body% >= 0.30%",
        check_experimental_formula_3,
        limit=10
    )
    
    # Print results with all required metrics
    print("\n" + "=" * 100)
    print("EXPERIMENTAL CANDIDATES - FORMULA 3")
    print("=" * 100)
    print(f"{'Symbol':<15} {'MSK':<20} {'UTC':<20}")
    print("-" * 100)
    
    for cand in candidates_3:
        print(f"{cand['symbol']:<15} {format_msk_time(cand['event_time']):<20} {format_utc_time(cand['event_time']):<20}")
        print(f"  O={cand['open']:.6f} H={cand['high']:.6f} L={cand['low']:.6f} C={cand['close']:.6f}")
        print(f"  Body%={cand['formula_details']['body_percent']:.4f}% Range%={cand['formula_details']['range_percent']:.4f}%")
        print(f"  LW/Body={cand['lower_wick_body_ratio']:.2f}x LW/Range={cand['lower_wick_range_ratio']*100:.1f}%")
        print(f"  Vol Ratio={cand['volume_ratio']:.2f}x Open->Low%={cand['formula_details']['open_to_low_percent']:.4f}%")
        print()
    
    # Save to JSON
    import json
    
    serializable_candidates = []
    for cand in candidates_3:
        cand_copy = cand.copy()
        cand_copy["event_time"] = format_utc_time(cand["event_time"])
        cand_copy["event_time_msk"] = format_msk_time(cand["event_time"])
        serializable_candidates.append(cand_copy)
    
    with open("experimental_candidates_formula3.json", "w") as f:
        json.dump(serializable_candidates, f, indent=2)
    
    print(f"\nResults saved to experimental_candidates_formula3.json")
    print("\n" + "=" * 100)
    print("SEARCH COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    asyncio.run(main())
