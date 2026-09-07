#!/usr/bin/env python3
"""
Find large diverse sample for deep context research.

Research: Collect 100-150+ signals from 50+ diverse coins.

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


async def find_large_diverse_sample(coins_per_symbol=3, max_symbols=100):
    """Find large diverse sample from 100+ coins."""
    print("=" * 100)
    print("FINDING LARGE DIVERSE SAMPLE (100+ COINS)")
    print("=" * 100)
    
    fetcher = BingXFetcher()
    
    # Expanded universe - more coins to get 50+ working
    universe = [
        # From previous successful samples
        "1000BONK-USDT", "GALA-USDT", "HOME-USDT", "JTO-USDT", "KITE-USDT",
        "ONE-USDT", "PEOPLE-USDT", "SIREN-USDT", "STG-USDT", "STORJ-USDT",
        "SUSHI-USDT", "WLD-USDT",
        
        # Layer 1 / L2
        "ARB-USDT", "OP-USDT", "SUI-USDT", "APT-USDT", "SEI-USDT",
        "INJ-USDT", "NEAR-USDT", "ATOM-USDT", "FET-USDT",
        
        # AI / DePIN
        "TAO-USDT", "RNDR-USDT", "WLD-USDT",
        
        # DeFi
        "UNI-USDT", "AAVE-USDT", "MKR-USDT", "CRV-USDT", "COMP-USDT",
        "PENDLE-USDT", "1INCH-USDT", "SNX-USDT", "YFI-USDT",
        
        # Gaming / Metaverse
        "SAND-USDT", "MANA-USDT", "AXS-USDT", "IMX-USDT", "ENJ-USDT",
        "GALA-USDT",
        
        # Meme / Community
        "PEPE-USDT", "SHIB-USDT", "DOGE-USDT", "FLOKI-USDT",
        "WIF-USDT", "MEME-USDT",
        
        # Storage
        "FIL-USDT", "AR-USDT", "STORJ-USDT",
        
        # Privacy
        "XMR-USDT", "ZEC-USDT", "DASH-USDT",
        
        # Oracle / Infrastructure
        "LINK-USDT",
        
        # Cross-chain
        "ZRO-USDT", "WOO-USDT", "XLM-USDT",
        
        # Others
        "ICP-USDT", "ALGO-USDT", "HBAR-USDT", "QNT-USDT",
        "ONT-USDT", "ZIL-USDT", "ROSE-USDT",
        "CELO-USDT", "GLM-USDT", "GRT-USDT", "LPT-USDT", "MASK-USDT",
        "BAT-USDT", "NMR-USDT", "RPL-USDT", "LDO-USDT",
        "TIA-USDT", "MANTA-USDT", "ALT-USDT", "ENA-USDT",
        "XPL-USDT", "FARTCOIN-USDT", "CRV-USDT", "WIF-USDT", "PENGU-USDT",
        "VIRTUAL-USDT", "POL-USDT", "ORDI-USDT", "MEW-USDT", "DASH-USDT",
        "ENS-USDT", "MOVR-USDT", "IOST-USDT", "JASMY-USDT", "KAVA-USDT",
        "RSR-USDT", "STX-USDT", "SUPER-USDT",
        "SXP-USDT", "UMA-USDT", "YFI-USDT", "ZEC-USDT", "ZEN-USDT",
        "AXL-USDT", "DUSK-USDT", "MIR-USDT",
        "TOMO-USDT", "UNFI-USDT", "XVG-USDT", "ZRX-USDT",
        
        # Additional mid-cap coins
        "BLUR-USDT", "GMX-USDT", "FXS-USDT", "CVX-USDT", "LDO-USDT",
        "JTO-USDT", "TIA-USDT", "STRK-USDT", "MANTA-USDT", "ALT-USDT",
        "BEAMX-USDT", "GLM-USDT", "GRT-USDT", "LPT-USDT", "MASK-USDT",
        "NMR-USDT", "RPL-USDT", "FXS-USDT", "CVX-USDT", "LDO-USDT",
        "JTO-USDT", "TIA-USDT", "MANTA-USDT", "ALT-USDT", "ENA-USDT",
        "WLFI-USDT", "XPL-USDT", "FARTCOIN-USDT", "CRV-USDT", "WIF-USDT",
        "PENGU-USDT", "VIRTUAL-USDT", "POL-USDT", "ORDI-USDT", "MEW-USDT",
        "DASH-USDT", "ENS-USDT", "MOVR-USDT", "IOST-USDT", "JASMY-USDT",
        "KAVA-USDT", "RSR-USDT", "STX-USDT", "SUPER-USDT", "SXP-USDT",
        "UMA-USDT", "YFI-USDT", "ZEC-USDT", "ZEN-USDT", "AXL-USDT",
        "DUSK-USDT", "MIR-USDT", "TOMO-USDT", "UNFI-USDT", "XVG-USDT",
        "ZRX-USDT",
    ]
    
    # Remove TOP-20
    top_20 = ["BTC-USDT", "ETH-USDT", "BNB-USDT", "SOL-USDT", "XRP-USDT",
              "DOGE-USDT", "ADA-USDT", "TRX-USDT", "TON-USDT", "AVAX-USDT",
              "SHIB-USDT", "DOT-USDT", "LINK-USDT", "NEAR-USDT", "MATIC-USDT",
              "PEPE-USDT", "UNI-USDT", "LTC-USDT", "KAS-USDT", "XLM-USDT"]
    universe = [s for s in universe if s not in top_20]
    
    # Remove duplicates
    universe = list(set(universe))
    
    print(f"Universe size: {len(universe)} coins")
    
    # Search last 60 days
    end_time = int(datetime.now(UTC).timestamp() * 1000)
    start_time = int((datetime.now(UTC) - timedelta(days=60)).timestamp() * 1000)
    
    candidates = []
    symbols_used = {}
    failed_symbols = []
    
    for symbol in universe[:max_symbols]:
        if len(symbols_used) >= max_symbols:
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
                failed_symbols.append(symbol)
                continue
            
            # Find up to 3 signals per symbol
            symbol_signals = []
            
            # Check all candles from newest to oldest
            for i in range(len(klines) - 1, 0, -1):
                if len(symbol_signals) >= coins_per_symbol:
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
                    
                    signal = {
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
                        "body_percent": geo["body_percent"],
                        "range_percent": geo["range_percent"],
                        "open_to_low_percent": geo["open_to_low_percent"],
                        "formula_details": details
                    }
                    symbol_signals.append(signal)
            
            if symbol_signals:
                candidates.extend(symbol_signals)
                symbols_used[symbol] = len(symbol_signals)
                print(f"  {symbol}: {len(symbol_signals)} signals")
            else:
                failed_symbols.append(symbol)
            
        except Exception as e:
            error_msg = str(e).encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
            print(f"Error processing {symbol}: {error_msg}")
            failed_symbols.append(symbol)
            continue
    
    print(f"\n{'=' * 100}")
    print("LARGE DIVERSE SAMPLE SUMMARY")
    print(f"{'=' * 100}")
    print(f"Total candidates: {len(candidates)}")
    print(f"Unique symbols: {len(symbols_used)}")
    print(f"Failed symbols: {len(failed_symbols)}")
    
    if symbols_used:
        print(f"\nSignals per symbol:")
        for symbol, count in sorted(symbols_used.items(), key=lambda x: x[1], reverse=True):
            print(f"  {symbol}: {count}")
    
    # Save results
    with open("large_diverse_sample.json", "w") as f:
        json.dump({
            "candidates": candidates,
            "symbols_used": symbols_used,
            "failed_symbols": failed_symbols,
            "summary": {
                "total_candidates": len(candidates),
                "unique_symbols": len(symbols_used),
                "failed_symbols": len(failed_symbols)
            }
        }, f, indent=2, default=str)
    
    print(f"\nSaved to large_diverse_sample.json")
    
    return candidates


async def main():
    """Main function."""
    candidates = await find_large_diverse_sample(coins_per_symbol=3, max_symbols=100)


if __name__ == "__main__":
    asyncio.run(main())
