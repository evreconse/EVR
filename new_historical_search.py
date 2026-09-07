#!/usr/bin/env python3
"""
New historical LW-001 signal search with minimum thresholds.

Minimum thresholds (not target values):
- Range: ≥ 6%
- Body: ≥ 1.9%
- LW/Body: ≥ 2.5x
- LW/Range: ≥ 63%
- Open → Low: ≤ -5%
- Volume Ratio: ≥ 2.6x

Goal: Find ALL signals meeting minimum thresholds across Top 20-250 coins.

DO NOT modify LW-001, production, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import json
import sys
from statistics import mean
sys.path.insert(0, "src")
sys.path.insert(0, ".")

from src.exchange.bingx_fetcher import BingXFetcher
from LW001_METRIC_SPEC import calculate_all_metrics


def calculate_deviation(kline_metrics, target_metrics):
    """Calculate total deviation from target parameters."""
    deviations = []
    
    # Range deviation
    range_dev = abs(kline_metrics["range_percent"] - target_metrics["range_percent"])
    deviations.append(range_dev)
    
    # Body deviation
    body_dev = abs(kline_metrics["body_percent"] - target_metrics["body_percent"])
    deviations.append(body_dev)
    
    # LW/Body deviation
    lw_body_dev = abs(kline_metrics["lower_wick_body_ratio"] - target_metrics["lower_wick_body_ratio"])
    deviations.append(lw_body_dev)
    
    # LW/Range deviation
    lw_range_dev = abs(kline_metrics["lower_wick_range_ratio"] - target_metrics["lower_wick_range_ratio"])
    deviations.append(lw_range_dev)
    
    # Open to Low deviation
    open_low_dev = abs(kline_metrics["open_to_low_percent"] - target_metrics["open_to_low_percent"])
    deviations.append(open_low_dev)
    
    # Volume Ratio deviation (if available)
    if kline_metrics.get("volume_ratio") is not None and target_metrics.get("volume_ratio") is not None:
        vol_dev = abs(kline_metrics["volume_ratio"] - target_metrics["volume_ratio"])
        deviations.append(vol_dev)
    
    return sum(deviations)


def calculate_kline_metrics(kline, avg_volume_20):
    """Calculate kline metrics using canonical formulas."""
    open_price = float(kline['open'])
    close_price = float(kline['close'])
    high_price = float(kline['high'])
    low_price = float(kline['low'])
    volume = float(kline['volume'])
    
    # Use canonical calculation
    metrics = calculate_all_metrics(open_price, high_price, low_price, close_price, volume, avg_volume_20)
    
    return {
        "body_percent": metrics.body_pct,
        "range_percent": metrics.range_pct,
        "lower_wick_body_ratio": metrics.lower_wick_body_ratio,
        "lower_wick_range_ratio": metrics.lower_wick_range_pct / 100,  # Convert back to ratio for compatibility
        "open_to_low_percent": metrics.open_to_low_pct,
        "volume_ratio": metrics.volume_ratio
    }


async def search_symbol_for_signals(fetcher, symbol, target_metrics, lookback_days=60):
    """Search for ALL signals matching target parameters on a single symbol."""
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=lookback_days)
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    try:
        klines = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            limit=2000,
            start_time=start_ms,
            end_time=end_ms
        )
        
        if not klines or len(klines) < 50:
            return []
        
        # Calculate average volume for last 20 candles
        volumes = [float(k['volume']) for k in klines[:20]]
        avg_volume_20 = mean(volumes) if volumes else 0
        
        candidates = []
        
        # Skip last 20 candles to ensure historical signals
        for kline in klines[20:]:
            metrics = calculate_kline_metrics(kline, avg_volume_20)
            
            if metrics is None:
                continue
            
            # Calculate deviation from target
            deviation = calculate_deviation(metrics, target_metrics)
            
            # Accept signals with reasonable deviation (e.g., < 10)
            if deviation < 10:
                candidates.append({
                    "symbol": symbol,
                    "event_time": datetime.fromtimestamp(int(kline['time']) / 1000, tz=UTC).strftime("%d.%m.%Y %H:%M UTC"),
                    "event_time_msk": datetime.fromtimestamp(int(kline['time']) / 1000, tz=UTC).strftime("%d.%m.%Y %H:%M MSK"),
                    "timestamp_ms": int(kline['time']),
                    "open": float(kline['open']),
                    "high": float(kline['high']),
                    "low": float(kline['low']),
                    "close": float(kline['close']),
                    "volume": float(kline['volume']),
                    "metrics": metrics,
                    "deviation": deviation
                })
        
        return candidates
        
    except Exception as e:
        return []


async def calculate_signal_performance(fetcher, signal):
    """Calculate post-signal performance for a signal."""
    symbol = signal["symbol"]
    signal_time = datetime.fromtimestamp(signal["timestamp_ms"] / 1000, tz=UTC)
    signal_close = signal["close"]
    
    # Get klines after signal (up to 100 candles = 25 hours)
    start_time = int(signal_time.timestamp() * 1000)
    end_time = int((signal_time + timedelta(hours=25)).timestamp() * 1000)
    
    try:
        klines = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            limit=100,
            start_time=start_time,
            end_time=end_time
        )
        
        if not klines:
            return {
                "result": "ERROR",
                "time_to_result_candles": None,
                "max_adverse": None
            }
        
        tp_3pct = signal_close * 1.03
        sl_3pct = signal_close * 0.97
        
        hit_tp = False
        hit_sl = False
        time_to_result = None
        max_adverse = 0
        
        for i, kline in enumerate(klines, 1):
            high = float(kline['high'])
            low = float(kline['low'])
            
            # Track max adverse
            drawdown = (signal_close - low) / signal_close * 100
            max_adverse = max(max_adverse, drawdown)
            
            # Check TP
            if high >= tp_3pct:
                hit_tp = True
                time_to_result = i
                break
            
            # Check SL
            if low <= sl_3pct:
                hit_sl = True
                time_to_result = i
                break
        
        if hit_tp:
            result = "TP"
        elif hit_sl:
            result = "SL"
        else:
            result = "NO_REVERSAL"
        
        return {
            "result": result,
            "time_to_result_candles": time_to_result,
            "max_adverse": max_adverse
        }
        
    except Exception as e:
        return {
            "result": "ERROR",
            "time_to_result_candles": None,
            "max_adverse": None,
            "error": str(e)
        }


async def main():
    """Main function."""
    print("=" * 100)
    print("NEW HISTORICAL LW-001 SIGNAL SEARCH - MINIMUM THRESHOLDS")
    print("=" * 100)
    
    target_metrics = {
        "range_percent": 4.0,
        "body_percent": 1.8,
        "lower_wick_body_ratio": 2.0,
        "lower_wick_range_ratio": 0.6,
        "open_to_low_percent": -5.0,
        "volume_ratio": 2.0
    }
    
    print(f"\nTarget parameters (deviation-based search):")
    print(f"  Range: {target_metrics['range_percent']}%")
    print(f"  Body: {target_metrics['body_percent']}%")
    print(f"  LW/Body: {target_metrics['lower_wick_body_ratio']}x")
    print(f"  LW/Range: {target_metrics['lower_wick_range_ratio']*100}%")
    print(f"  Open to Low: {target_metrics['open_to_low_percent']}%")
    print(f"  Volume Ratio: {target_metrics['volume_ratio']}x")
    print(f"  Deviation threshold: < 10")
    
    fetcher = BingXFetcher()
    
    # Broad list of symbols (Top 20-250 range)
    symbols = [
        # Major coins (Top 20)
        "BTC-USDT", "ETH-USDT", "BNB-USDT", "SOL-USDT", "XRP-USDT",
        "ADA-USDT", "DOGE-USDT", "AVAX-USDT", "DOT-USDT", "LINK-USDT",
        "MATIC-USDT", "UNI-USDT", "LTC-USDT", "ATOM-USDT", "NEAR-USDT",
        "ETC-USDT", "XLM-USDT", "ALGO-USDT", "VET-USDT", "FIL-USDT",
        
        # Mid-cap coins (Top 20-100)
        "APT-USDT", "OP-USDT", "ARB-USDT", "INJ-USDT", "SUI-USDT",
        "SEI-USDT", "TIA-USDT", "FET-USDT", "RNDR-USDT", "GRT-USDT",
        "AAVE-USDT", "MKR-USDT", "COMP-USDT", "YFI-USDT", "CRV-USDT",
        "SNX-USDT", "BAL-USDT", "1INCH-USDT", "SUSHI-USDT", "IMX-USDT",
        "SAND-USDT", "MANA-USDT", "AXS-USDT", "ENJ-USDT", "GALA-USDT",
        "ILV-USDT", "YGG-USDT", "RPL-USDT", "ALICE-USDT", "PEPE-USDT",
        "SHIB-USDT", "FLOKI-USDT", "BONK-USDT", "WIF-USDT", "BOME-USDT",
        
        # Small-mid cap coins (Top 100-250)
        "ORCA-USDT", "RAY-USDT", "JUP-USDT", "WEN-USDT", "STG-USDT",
        "JTO-USDT", "STORJ-USDT", "WLD-USDT", "ONE-USDT", "ROSE-USDT",
        "CELO-USDT", "HBAR-USDT", "ICP-USDT", "EGLD-USDT", "QNT-USDT",
        "ZEC-USDT", "DASH-USDT", "KAVA-USDT", "MINA-USDT", "MASK-USDT",
        "AXL-USDT", "GLM-USDT", "BAND-USDT", "UMA-USDT", "THETA-USDT",
        "TFUEL-USDT", "HOT-USDT", "IOTA-USDT", "XEM-USDT", "XTZ-USDT",
        "EOS-USDT", "TRX-USDT", "XMR-USDT", "BCH-USDT", "LUNC-USDT",
        "SIREN-USDT", "HOME-USDT", "KITE-USDT", "1000BONK-USDT", "PEOPLE-USDT",
        "TAO-USDT", "NMR-USDT", "AGIX-USDT", "OCEAN-USDT", "LOOKS-USDT",
        "BLUR-USDT", "X2Y2-USDT", "GLM-USDT", "ARPA-USDT", "IDEX-USDT",
        "HARD-USDT", "KSM-USDT", "OXY-USDT", "RUNE-USDT", "SCRT-USDT",
        "STX-USDT", "AKRO-USDT", "ANKR-USDT", "BAND-USDT", "BNT-USDT",
        "CQT-USDT", "DIA-USDT", "DKA-USDT", "ELF-USDT", "FORTH-USDT",
        "GNO-USDT", "HIVE-USDT", "IOST-USDT", "JST-USDT", "KMD-USDT",
        "LDO-USDT", "LRC-USDT", "MCO2-USDT", "MOVR-USDT", "NEXO-USDT",
        "OAX-USDT", "PNT-USDT", "QKC-USDT", "RAMP-USDT", "RARI-USDT",
        "SNT-USDT", "SXP-USDT", "TCT-USDT", "TRB-USDT", "UOS-USDT",
        "VITE-USDT", "WAN-USDT", "XVS-USDT", "YFII-USDT", "ZEN-USDT",
    ]
    
    print(f"\nSearching across {len(symbols)} symbols...")
    print(f"Period: Last 2 months")
    print(f"Goal: Minimum 50 different coins with signals")
    
    all_candidates = []
    successful_symbols = []
    failed_symbols = []
    
    for i, symbol in enumerate(symbols, 1):
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(symbols)}")
        
        candidates = await search_symbol_for_signals(fetcher, symbol, target_metrics)
        
        if candidates:
            all_candidates.extend(candidates)
            successful_symbols.append(symbol)
        else:
            failed_symbols.append(symbol)
    
    print(f"\nSearch complete:")
    print(f"  Successful symbols: {len(successful_symbols)}")
    print(f"  Failed symbols: {len(failed_symbols)}")
    print(f"  Total signals found: {len(all_candidates)}")
    
    # Calculate performance for all signals
    print("\nCalculating performance...")
    
    for i, signal in enumerate(all_candidates, 1):
        if i % 50 == 0:
            print(f"  Progress: {i}/{len(all_candidates)}")
        
        perf = await calculate_signal_performance(fetcher, signal)
        signal["performance"] = perf
    
    # Save results
    results = {
        "target_metrics": target_metrics,
        "search_period": "Last 2 months",
        "symbols_checked": len(symbols),
        "successful_symbols": successful_symbols,
        "failed_symbols": failed_symbols,
        "total_signals": len(all_candidates),
        "unique_symbols_with_signals": len(successful_symbols),
        "signals": all_candidates
    }
    
    with open("new_historical_signals.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n{'=' * 100}")
    print("Analysis complete. Results saved to new_historical_signals.json")
    print(f"{'=' * 100}")
    
    # Print summary
    print(f"\n{'=' * 100}")
    print("SUMMARY")
    print(f"{'=' * 100}")
    
    tp_count = sum(1 for s in all_candidates if s['performance']['result'] == "TP")
    sl_count = sum(1 for s in all_candidates if s['performance']['result'] == "SL")
    no_rev_count = sum(1 for s in all_candidates if s['performance']['result'] == "NO_REVERSAL")
    error_count = sum(1 for s in all_candidates if s['performance']['result'] == "ERROR")
    
    print(f"\nTotal signals: {len(all_candidates)}")
    print(f"Unique symbols with signals: {len(successful_symbols)}")
    if len(all_candidates) > 0:
        print(f"TP: {tp_count} ({tp_count/len(all_candidates)*100:.1f}%)")
        print(f"SL: {sl_count} ({sl_count/len(all_candidates)*100:.1f}%)")
        print(f"NO_REVERSAL: {no_rev_count} ({no_rev_count/len(all_candidates)*100:.1f}%)")
        print(f"ERROR: {error_count}")
    else:
        print(f"TP: {tp_count}")
        print(f"SL: {sl_count}")
        print(f"NO_REVERSAL: {no_rev_count}")
        print(f"ERROR: {error_count}")
    
    # Per-symbol breakdown
    print(f"\n{'=' * 100}")
    print("PER-SYMBOL BREAKDOWN")
    print(f"{'=' * 100}")
    
    per_symbol = {}
    for signal in all_candidates:
        symbol = signal['symbol']
        if symbol not in per_symbol:
            per_symbol[symbol] = {"total": 0, "tp": 0, "sl": 0, "no_rev": 0}
        per_symbol[symbol]["total"] += 1
        if signal['performance']['result'] == "TP":
            per_symbol[symbol]["tp"] += 1
        elif signal['performance']['result'] == "SL":
            per_symbol[symbol]["sl"] += 1
        elif signal['performance']['result'] == "NO_REVERSAL":
            per_symbol[symbol]["no_rev"] += 1
    
    for symbol, stats in sorted(per_symbol.items(), key=lambda x: x[1]["total"], reverse=True):
        print(f"{symbol}: {stats['total']} signals (TP: {stats['tp']}, SL: {stats['sl']}, NO_REV: {stats['no_rev']})")


if __name__ == "__main__":
    asyncio.run(main())
