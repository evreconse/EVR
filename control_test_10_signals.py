#!/usr/bin/env python3
"""
Control test: Find exactly 10 signals on 10 different coins with STRICT minimum thresholds.

STRICT CONDITIONS (ALL must pass):
- Range >= 6%
- Body >= 1.9%
- LW/Body >= 2.5x
- LW/Range >= 63%
- Open→Low <= -5%
- Volume Ratio >= 2.6x

DO NOT use deviation or approximate matching.

DO NOT modify LW-001, production, PASS_CHECK, or Telegram logic.
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
from LW001_METRIC_SPEC import calculate_all_metrics, check_all_conditions


def check_strict_conditions(kline_metrics):
    """Check if kline meets ALL 6 strict conditions using canonical validation."""
    # Convert dict to LW001Metrics format for canonical check
    from LW001_METRIC_SPEC import LW001Metrics
    
    metrics = LW001Metrics(
        range_pct=kline_metrics["range_percent"],
        body_pct=kline_metrics["body_percent"],
        lower_wick_body_ratio=kline_metrics["lower_wick_body_ratio"],
        lower_wick_range_pct=kline_metrics["lower_wick_range_ratio"],
        open_to_low_pct=kline_metrics["open_to_low_percent"],
        volume_ratio=kline_metrics.get("volume_ratio")
    )
    
    passed, failures = check_all_conditions(metrics)
    
    if passed:
        return True, "All conditions PASS"
    else:
        return False, "; ".join(failures)


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


async def search_symbol_for_signals(fetcher, symbol, lookback_days=60):
    """Search for signals meeting ALL 6 strict conditions on a single symbol."""
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
            
            # Check if meets ALL 6 strict conditions
            passes, reason = check_strict_conditions(metrics)
            
            if passes:
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
                    "metrics": metrics
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
    print("CONTROL TEST: 10 SIGNALS WITH STRICT MINIMUM THRESHOLDS")
    print("=" * 100)
    
    print(f"\nSTRICT CONDITIONS (ALL must PASS):")
    print(f"  Range >= 6%")
    print(f"  Body >= 1.9%")
    print(f"  LW/Body >= 2.5x")
    print(f"  LW/Range >= 63%")
    print(f"  Open to Low <= -5%")
    print(f"  Volume Ratio >= 2.6x")
    
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
        "BLUR-USDT", "X2Y2-USDT", "ARPA-USDT", "IDEX-USDT", "HARD-USDT",
        "KSM-USDT", "OXY-USDT", "RUNE-USDT", "SCRT-USDT", "STX-USDT",
        "AKRO-USDT", "ANKR-USDT", "BNT-USDT", "CQT-USDT", "DIA-USDT",
        "DKA-USDT", "ELF-USDT", "FORTH-USDT", "GNO-USDT", "HIVE-USDT",
        "IOST-USDT", "JST-USDT", "KMD-USDT", "LDO-USDT", "LRC-USDT",
        "MCO2-USDT", "MOVR-USDT", "NEXO-USDT", "OAX-USDT", "PNT-USDT",
        "QKC-USDT", "RAMP-USDT", "RARI-USDT", "SNT-USDT", "SXP-USDT",
        "TCT-USDT", "TRB-USDT", "UOS-USDT", "VITE-USDT", "WAN-USDT",
        "XVS-USDT", "YFII-USDT", "ZEN-USDT",
    ]
    
    print(f"\nSearching across {len(symbols)} symbols...")
    print(f"Period: Last 2 months")
    print(f"Goal: Exactly 10 signals on 10 different coins")
    
    all_candidates = []
    successful_symbols = []
    
    for i, symbol in enumerate(symbols, 1):
        # Stop if we have 10 signals on 10 different coins
        if len(successful_symbols) >= 10:
            break
        
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(symbols)} (Found: {len(successful_symbols)} signals)")
        
        candidates = await search_symbol_for_signals(fetcher, symbol)
        
        if candidates:
            # Take only the first signal from each symbol
            all_candidates.append(candidates[0])
            successful_symbols.append(symbol)
            print(f"  Found signal on {symbol} ({len(successful_symbols)}/10)")
    
    print(f"\nSearch complete:")
    print(f"  Successful symbols: {len(successful_symbols)}")
    print(f"  Total signals found: {len(all_candidates)}")
    
    if len(all_candidates) < 10:
        print(f"\nERROR: Only found {len(all_candidates)} signals. Need 10.")
        return
    
    # Calculate performance for all signals
    print("\nCalculating performance...")
    
    for i, signal in enumerate(all_candidates, 1):
        perf = await calculate_signal_performance(fetcher, signal)
        signal["performance"] = perf
    
    # Display all signals for verification
    print(f"\n{'=' * 100}")
    print("SIGNAL VERIFICATION - ALL 6 CONDITIONS")
    print(f"{'=' * 100}")
    
    for i, signal in enumerate(all_candidates, 1):
        print(f"\nSignal {i}/10:")
        print(f"Coin: {signal['symbol']}")
        print(f"Date/Time: {signal['event_time']}")
        print(f"Entry: {signal['close']}")
        print(f"")
        print(f"Range: {signal['metrics']['range_percent']:.2f}%          {'PASS' if signal['metrics']['range_percent'] >= 6.0 else 'FAIL'}")
        print(f"Body: {signal['metrics']['body_percent']:.2f}%           {'PASS' if signal['metrics']['body_percent'] >= 1.9 else 'FAIL'}")
        print(f"LW/Body: {signal['metrics']['lower_wick_body_ratio']:.2f}x        {'PASS' if signal['metrics']['lower_wick_body_ratio'] >= 2.5 else 'FAIL'}")
        print(f"LW/Range: {signal['metrics']['lower_wick_range_ratio']*100:.1f}%       {'PASS' if signal['metrics']['lower_wick_range_ratio'] >= 0.63 else 'FAIL'}")
        print(f"Open to Low: {signal['metrics']['open_to_low_percent']:.2f}%       {'PASS' if signal['metrics']['open_to_low_percent'] <= -5.0 else 'FAIL'}")
        print(f"Volume Ratio: {signal['metrics']['volume_ratio']:.2f}x   {'PASS' if signal['metrics']['volume_ratio'] >= 2.6 else 'FAIL'}")
        print(f"")
        print(f"Performance: {signal['performance']['result']}")
        if signal['performance']['time_to_result_candles']:
            print(f"Time to result: {signal['performance']['time_to_result_candles']} candles")
        print(f"{'-' * 100}")
    
    # Save results
    results = {
        "test_type": "control_test_10_signals",
        "strict_conditions": {
            "range_percent": ">= 6%",
            "body_percent": ">= 1.9%",
            "lower_wick_body_ratio": ">= 2.5x",
            "lower_wick_range_ratio": ">= 63%",
            "open_to_low_percent": "<= -5%",
            "volume_ratio": ">= 2.6x"
        },
        "search_period": "Last 2 months",
        "symbols_checked": len(symbols),
        "successful_symbols": successful_symbols,
        "total_signals": len(all_candidates),
        "signals": all_candidates
    }
    
    with open("control_test_10_signals.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n{'=' * 100}")
    print(f"Control test complete. Results saved to control_test_10_signals.json")
    print(f"{'=' * 100}")
    print(f"\nWAITING FOR USER VERIFICATION BEFORE SENDING TO TELEGRAM")


if __name__ == "__main__":
    asyncio.run(main())
