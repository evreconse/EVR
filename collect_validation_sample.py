#!/usr/bin/env python3
"""
Collect large independent sample for mean-reversion hypothesis validation.

Research: Collect 50+ diverse coins with 2-3 signals each (100-150+ total signals).

DO NOT modify LW-001, production, backtest, PASS_CHECK, or Telegram.
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


def check_base_filter(kline):
    """Check if kline passes base filter conditions using canonical formulas."""
    open_price = float(kline['open'])
    close_price = float(kline['close'])
    high_price = float(kline['high'])
    low_price = float(kline['low'])
    volume = float(kline['volume'])
    
    # Use canonical calculation (avg_volume not needed for this filter)
    metrics = calculate_all_metrics(open_price, high_price, low_price, close_price, volume, 1.0)
    
    # Base filter conditions (from LW-001)
    conditions = {
        "body_percent": metrics.body_pct >= 0.5,
        "range_percent": metrics.range_pct >= 1.5,
        "lower_wick_body_ratio": metrics.lower_wick_body_ratio >= 0.5,
        "lower_wick_range_ratio": metrics.lower_wick_range_pct / 100 >= 0.3,
        "open_to_low_percent": metrics.open_to_low_pct <= -1.5,
    }
    
    passes = all(conditions.values())
    
    return passes, {
        "body_percent": metrics.body_pct,
        "range_percent": metrics.range_pct,
        "lower_wick_body_ratio": metrics.lower_wick_body_ratio,
        "lower_wick_range_ratio": metrics.lower_wick_range_pct / 100,
        "open_to_low_percent": metrics.open_to_low_pct,
        "conditions": conditions
    }


async def find_signals_for_symbol(fetcher, symbol, max_signals=3):
    """Find up to max_signals for a single symbol."""
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=60)
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    try:
        klines = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            limit=500,
            start_time=start_ms,
            end_time=end_ms
        )
        
        if not klines:
            return [], "No klines data"
        
        signals = []
        for kline in klines:
            passes, details = check_base_filter(kline)
            if passes:
                signals.append({
                    "symbol": symbol,
                    "event_time": datetime.fromtimestamp(int(kline['time']) / 1000, tz=UTC).strftime("%d.%m.%Y %H:%M UTC"),
                    "event_time_msk": datetime.fromtimestamp(int(kline['time']) / 1000, tz=UTC).strftime("%d.%m.%Y %H:%M MSK"),
                    "timestamp_ms": int(kline['time']),
                    "open": float(kline['open']),
                    "high": float(kline['high']),
                    "low": float(kline['low']),
                    "close": float(kline['close']),
                    "volume": float(kline['volume']),
                    "volume_ratio": None,  # Will calculate later
                    "lower_wick_body_ratio": details["lower_wick_body_ratio"],
                    "lower_wick_range_ratio": details["lower_wick_range_ratio"],
                    "body_percent": details["body_percent"],
                    "range_percent": details["range_percent"],
                    "open_to_low_percent": details["open_to_low_percent"],
                    "formula_details": details
                })
                
                if len(signals) >= max_signals:
                    break
        
        return signals, "OK"
        
    except Exception as e:
        return [], f"Error: {str(e)}"


async def collect_validation_sample(max_signals_per_symbol=3, max_symbols=100):
    """Collect large independent sample from diverse coins."""
    print("=" * 100)
    print("COLLECTING VALIDATION SAMPLE FOR MEAN-REVERSION HYPOTHESIS")
    print("=" * 100)
    print("\nDO NOT modify LW-001, production, backtest, PASS_CHECK, or Telegram.")
    
    fetcher = BingXFetcher()
    
    # List of symbols to try (focus on small cap altcoins with higher volatility)
    # These are more likely to pass the base filter than major coins
    symbols = [
        # Small cap altcoins (from previous successful sample)
        "SIREN-USDT", "HOME-USDT", "KITE-USDT", "1000BONK-USDT",
        
        # High volatility small caps
        "PEPE-USDT", "FLOKI-USDT", "BONK-USDT", "WIF-USDT", "BOME-USDT",
        "ORCA-USDT", "RAY-USDT", "JUP-USDT", "BONK-USDT", "WEN-USDT",
        
        # Gaming/Metaverse (often volatile)
        "GALA-USDT", "SAND-USDT", "MANA-USDT", "AXS-USDT", "ENJ-USDT",
        "IMX-USDT", "ILV-USDT", "YGG-USDT", "ALICE-USDT", "RPL-USDT",
        
        # DeFi small caps
        "SUSHI-USDT", "1INCH-USDT", "BAL-USDT", "SNX-USDT", "CRV-USDT",
        "LOOKS-USDT", "BLUR-USDT", "X2Y2-USDT",
        
        # AI coins (often volatile)
        "FET-USDT", "RNDR-USDT", "AGIX-USDT", "OCEAN-USDT", "NMR-USDT",
        "GLM-USDT", "TAO-USDT", "NMR-USDT",
        
        # Layer 2 altcoins
        "OP-USDT", "ARB-USDT", "SEI-USDT", "SUI-USDT", "APT-USDT",
        "TIA-USDT", "INJ-USDT", "KAVA-USDT",
        
        # Meme coins (high volatility)
        "DOGE-USDT", "SHIB-USDT", "PEPE-USDT", "FLOKI-USDT",
        
        # Other small caps
        "STG-USDT", "JTO-USDT", "STORJ-USDT", "WLD-USDT", "ONE-USDT",
        "ROSE-USDT", "CELO-USDT", "ALGO-USDT", "VET-USDT", "HBAR-USDT",
        "ICP-USDT", "EGLD-USDT", "QNT-USDT", "ZEC-USDT", "DASH-USDT",
        "MINA-USDT", "MASK-USDT", "AXL-USDT", "BAND-USDT", "UMA-USDT",
        "THETA-USDT", "TFUEL-USDT", "XLM-USDT", "HOT-USDT", "IOTA-USDT",
        "XEM-USDT", "XTZ-USDT", "EOS-USDT", "TRX-USDT", "XMR-USDT",
        "ETC-USDT", "BCH-USDT",
        
        # Mid-cap coins
        "ADA-USDT", "AVAX-USDT", "DOT-USDT", "LINK-USDT", "MATIC-USDT",
        "ATOM-USDT", "NEAR-USDT", "GRT-USDT", "AAVE-USDT", "MKR-USDT",
        "COMP-USDT", "YFI-USDT",
        
        # Major coins (less likely to pass, but included)
        "BTC-USDT", "ETH-USDT", "BNB-USDT", "SOL-USDT", "XRP-USDT",
        "DOGE-USDT", "UNI-USDT", "LTC-USDT",
    ]
    
    print(f"\nAttempting to collect from {len(symbols)} symbols...")
    print(f"Target: {max_signals_per_symbol} signals per symbol")
    print(f"Expected total: {max_symbols * max_signals_per_symbol} signals")
    
    all_candidates = []
    successful_symbols = []
    failed_symbols = []
    
    for i, symbol in enumerate(symbols, 1):
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(symbols)} symbols checked")
        
        signals, status = await find_signals_for_symbol(fetcher, symbol, max_signals_per_symbol)
        
        if signals:
            all_candidates.extend(signals)
            successful_symbols.append(symbol)
            print(f"  {symbol}: {len(signals)} signals ({status})")
        else:
            failed_symbols.append((symbol, status))
            if i % 20 == 0:
                print(f"  {symbol}: {status}")
    
    print(f"\n{'=' * 100}")
    print("COLLECTION COMPLETE")
    print(f"{'=' * 100}")
    print(f"Successful symbols: {len(successful_symbols)}")
    print(f"Failed symbols: {len(failed_symbols)}")
    print(f"Total signals collected: {len(all_candidates)}")
    
    if len(successful_symbols) < 50:
        print(f"\nWARNING: Only {len(successful_symbols)} symbols available (target was 50)")
        print(f"Sample size: {len(all_candidates)} signals (target was 100-150)")
    
    # Save results
    results = {
        "candidates": all_candidates,
        "summary": {
            "total_signals": len(all_candidates),
            "successful_symbols": successful_symbols,
            "failed_symbols": failed_symbols,
            "target_symbols": max_symbols,
            "target_signals": max_symbols * max_signals_per_symbol
        }
    }
    
    with open("validation_sample.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to validation_sample.json")
    print(f"{'=' * 100}")
    
    return results


async def main():
    """Main function."""
    await collect_validation_sample(max_signals_per_symbol=3, max_symbols=100)


if __name__ == "__main__":
    asyncio.run(main())
