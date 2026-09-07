#!/usr/bin/env python3
"""
Find 10 historical LW-001 signals matching target parameters.

Target parameters:
- Range: 4%
- Body: 1.8%
- LW/Body: 2.0x
- LW/Range: 60%
- Open → Low: -5%
- Volume Ratio: 2.0x

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
    
    # Open → Low deviation
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


async def search_symbol_for_signals(fetcher, symbol, target_metrics, lookback_days=90):
    """Search for signals matching target parameters on a single symbol."""
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=lookback_days)
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    try:
        klines = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            limit=1000,
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
        for kline in klines[20:-20]:
            metrics = calculate_kline_metrics(kline, avg_volume_20)
            
            if metrics is None:
                continue
            
            # Calculate deviation from target
            deviation = calculate_deviation(metrics, target_metrics)
            
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
        
        # Sort by deviation (lowest first)
        candidates.sort(key=lambda x: x["deviation"])
        
        # Return top 3 candidates for this symbol
        return candidates[:3]
        
    except Exception as e:
        print(f"  {symbol}: Error - {str(e)}")
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
    print("FINDING 10 HISTORICAL SIGNALS MATCHING TARGET PARAMETERS")
    print("=" * 100)
    
    target_metrics = {
        "range_percent": 4.0,
        "body_percent": 1.8,
        "lower_wick_body_ratio": 2.0,
        "lower_wick_range_ratio": 0.6,
        "open_to_low_percent": -5.0,
        "volume_ratio": 2.0
    }
    
    print(f"\nTarget parameters:")
    print(f"  Range: {target_metrics['range_percent']}%")
    print(f"  Body: {target_metrics['body_percent']}%")
    print(f"  LW/Body: {target_metrics['lower_wick_body_ratio']}x")
    print(f"  LW/Range: {target_metrics['lower_wick_range_ratio']*100}%")
    print(f"  Open to Low: {target_metrics['open_to_low_percent']}%")
    print(f"  Volume Ratio: {target_metrics['volume_ratio']}x")
    
    fetcher = BingXFetcher()
    
    # List of symbols to search
    symbols = [
        "SIREN-USDT", "HOME-USDT", "KITE-USDT", "1000BONK-USDT",
        "PEPE-USDT", "FLOKI-USDT", "WIF-USDT", "BOME-USDT",
        "GALA-USDT", "SAND-USDT", "AXS-USDT", "ALICE-USDT",
        "SUSHI-USDT", "CRV-USDT", "STG-USDT", "JTO-USDT",
        "STORJ-USDT", "WLD-USDT", "ONE-USDT", "ROSE-USDT",
        "VET-USDT", "ICP-USDT", "AXL-USDT", "UMA-USDT",
        "BCH-USDT", "AVAX-USDT", "GRT-USDT", "SOL-USDT",
        "UNI-USDT", "OP-USDT", "ARB-USDT", "INJ-USDT",
        "TIA-USDT", "DOGE-USDT", "SHIB-USDT", "BONK-USDT",
        "ORCA-USDT", "RAY-USDT", "JUP-USDT", "WEN-USDT",
        "IMX-USDT", "ILV-USDT", "YGG-USDT", "RPL-USDT",
        "BAL-USDT", "SNX-USDT", "LOOKS-USDT", "BLUR-USDT",
        "FET-USDT", "RNDR-USDT", "AGIX-USDT", "OCEAN-USDT",
        "NMR-USDT", "GLM-USDT", "TAO-USDT", "SEI-USDT",
        "SUI-USDT", "APT-USDT", "KAVA-USDT", "ALGO-USDT",
        "CELO-USDT", "HBAR-USDT", "EGLD-USDT", "QNT-USDT",
        "ZEC-USDT", "DASH-USDT", "MINA-USDT", "MASK-USDT",
        "BAND-USDT", "THETA-USDT", "TFUEL-USDT", "XLM-USDT",
        "HOT-USDT", "IOTA-USDT", "XEM-USDT", "XTZ-USDT",
        "EOS-USDT", "TRX-USDT", "XMR-USDT", "ETC-USDT",
    ]
    
    print(f"\nSearching across {len(symbols)} symbols...")
    
    all_candidates = []
    
    for i, symbol in enumerate(symbols, 1):
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(symbols)}")
        
        candidates = await search_symbol_for_signals(fetcher, symbol, target_metrics)
        all_candidates.extend(candidates)
    
    print(f"\nFound {len(all_candidates)} candidates")
    
    # Sort all candidates by deviation
    all_candidates.sort(key=lambda x: x["deviation"])
    
    # Select top 10 from different symbols
    selected = []
    used_symbols = set()
    
    for candidate in all_candidates:
        if candidate["symbol"] not in used_symbols:
            selected.append(candidate)
            used_symbols.add(candidate["symbol"])
            
            if len(selected) >= 10:
                break
    
    print(f"Selected {len(selected)} signals from different symbols")
    
    # Calculate performance for selected signals
    print("\nCalculating performance...")
    
    for i, signal in enumerate(selected, 1):
        print(f"  {i}/{len(selected)}: {signal['symbol']}")
        perf = await calculate_signal_performance(fetcher, signal)
        signal["performance"] = perf
    
    # Save results
    results = {
        "target_metrics": target_metrics,
        "selected_signals": selected
    }
    
    with open("target_signals.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n{'=' * 100}")
    print("Analysis complete. Results saved to target_signals.json")
    print(f"{'=' * 100}")
    
    # Print summary
    print(f"\n{'=' * 100}")
    print("SELECTED SIGNALS")
    print(f"{'=' * 100}")
    
    for i, signal in enumerate(selected, 1):
        print(f"\n{i}. {signal['symbol']}")
        print(f"   Time: {signal['event_time']}")
        print(f"   Entry: {signal['close']}")
        print(f"   Range: {signal['metrics']['range_percent']:.2f}% (target: 4%)")
        print(f"   Body: {signal['metrics']['body_percent']:.2f}% (target: 1.8%)")
        print(f"   LW/Body: {signal['metrics']['lower_wick_body_ratio']:.2f}x (target: 2.0x)")
        print(f"   LW/Range: {signal['metrics']['lower_wick_range_ratio']*100:.1f}% (target: 60%)")
        print(f"   Open to Low: {signal['metrics']['open_to_low_percent']:.2f}% (target: -5%)")
        print(f"   Volume Ratio: {signal['metrics']['volume_ratio']:.2f}x (target: 2.0x)" if signal['metrics']['volume_ratio'] else f"   Volume Ratio: N/A (target: 2.0x)")
        print(f"   Deviation: {signal['deviation']:.2f}")
        print(f"   Result: {signal['performance']['result']}")
        print(f"   Time to result: {signal['performance']['time_to_result_candles']} candles" if signal['performance']['time_to_result_candles'] else f"   Time to result: N/A")


if __name__ == "__main__":
    asyncio.run(main())
