#!/usr/bin/env python3
"""
Test LW-001 with relaxed thresholds.

Specified thresholds:
- Range >= 6%
- Body >= 1.5%
- LW/Body >= 2.0x
- LW/Range >= 63%
- Open->Low <= -3%
- Volume Ratio >= 1.5x

Goal: Find 10 valid signals on 10 different symbols from Top-21-250.
"""

import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

import asyncio
from datetime import datetime, UTC, timedelta
from collections import defaultdict

from src.exchange.bingx_fetcher import BingXFetcher
from LW001_METRIC_SPEC import (
    calculate_all_metrics,
    LW001_THRESHOLDS
)


# Top-20 symbols to EXCLUDE
TOP_20_EXCLUDE = {
    "BTC-USDT", "ETH-USDT", "BNB-USDT", "SOL-USDT", "XRP-USDT",
    "ADA-USDT", "DOGE-USDT", "AVAX-USDT", "DOT-USDT", "LINK-USDT",
    "LTC-USDT", "ATOM-USDT", "NEAR-USDT", "OP-USDT", "ARB-USDT"
}

# Mid-tier symbols (rank 21-250 approximation)
MID_TIER_SYMBOLS = [
    "PEPE-USDT", "SHIB-USDT", "FLOKI-USDT", "BONK-USDT", "WIF-USDT",
    "ORDI-USDT", "SATS-USDT", "1000PEPE-USDT", "1000SHIB-USDT", "MEME-USDT",
    "TIA-USDT", "SEI-USDT", "SUI-USDT", "INJ-USDT", "APT-USDT",
    "FTM-USDT", "QNT-USDT", "ALGO-USDT", "VET-USDT", "ICP-USDT",
    "HBAR-USDT", "EOS-USDT", "XLM-USDT", "XEM-USDT", "XTZ-USDT",
    "BCH-USDT", "ETC-USDT", "ZEC-USDT", "DASH-USDT", "KAVA-USDT",
    "MINA-USDT", "ROSE-USDT", "CELO-USDT", "GLM-USDT", "RNDR-USDT",
    "FET-USDT", "AGIX-USDT", "OCEAN-USDT", "MASK-USDT", "LDO-USDT",
    "AAVE-USDT", "MKR-USDT", "COMP-USDT", "UNI-USDT", "CRV-USDT",
    "SNX-USDT", "1INCH-USDT", "YFI-USDT", "PERP-USDT", "GMX-USDT",
    "GRT-USDT", "LRC-USDT", "MANA-USDT", "SAND-USDT", "AXS-USDT",
    "ENJ-USDT", "IMX-USDT", "GALA-USDT", "STX-USDT", "FLOW-USDT",
    "NEO-USDT", "ONT-USDT", "ZIL-USDT", "QTUM-USDT", "IOST-USDT",
    "TRX-USDT", "XDC-USDT", "CSPR-USDT", "PHB-USDT", "KSM-USDT",
    "DOT-USDT", "AVAX-USDT", "NEAR-USDT", "FIL-USDT", "AR-USDT",
    "STORJ-USDT", "SC-USDT", "RVN-USDT", "KDA-USDT", "NEXO-USDT"
]

# Filter out Top-20 from mid-tier list
TEST_SYMBOLS = [s for s in MID_TIER_SYMBOLS if s not in TOP_20_EXCLUDE]

# Specified thresholds
SPECIFIED_THRESHOLDS = {
    "range_pct": 6.0,
    "body_pct": 1.5,
    "lw_body_ratio": 2.0,
    "lw_range_pct": 63.0,
    "open_low_pct": -3.0,
    "volume_ratio": 1.5
}


async def fetch_historical_candles_for_symbol(symbol: str, days: int = 60):
    """Fetch historical candles for a single symbol."""
    fetcher = BingXFetcher()
    
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=days)
    
    try:
        candles = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            limit=1000,
            start_time=int(start_time.timestamp() * 1000),
            end_time=int(end_time.timestamp() * 1000)
        )
        return candles
    except Exception as e:
        print(f"  Error: {e}")
        return []


def calculate_avg_volume_20(candles, index):
    """Calculate average volume of previous 20 candles."""
    start_idx = max(0, index - 20)
    if start_idx >= index:
        return 1.0
    
    volumes = []
    for i in range(start_idx, index):
        vol = float(candles[i].get('volume', candles[i].get('vol', 0)))
        volumes.append(vol)
    
    if not volumes:
        return 1.0
    
    return sum(volumes) / len(volumes)


def check_thresholds(metrics, thresholds):
    """Check if metrics pass all thresholds."""
    return (
        metrics.range_pct >= thresholds["range_pct"] and
        metrics.body_pct >= thresholds["body_pct"] and
        metrics.lower_wick_body_ratio >= thresholds["lw_body_ratio"] and
        metrics.lower_wick_range_pct >= thresholds["lw_range_pct"] and
        metrics.open_to_low_pct <= thresholds["open_low_pct"] and
        metrics.volume_ratio >= thresholds["volume_ratio"]
    )


def verify_signal_independent(candle_data):
    """Verify signal with independent recalculation from OHLCV."""
    open_price = candle_data['open']
    high_price = candle_data['high']
    low_price = candle_data['low']
    close_price = candle_data['close']
    volume = candle_data['volume']
    avg_volume_20 = candle_data['avg_volume_20']
    
    # Independent calculation
    range_pct = (high_price - low_price) / open_price * 100
    body_pct = abs(close_price - open_price) / open_price * 100
    lower_wick = min(open_price, close_price) - low_price
    lw_body_ratio = lower_wick / abs(close_price - open_price) if abs(close_price - open_price) > 0 else 0
    lw_range_pct = lower_wick / (high_price - low_price) * 100 if (high_price - low_price) > 0 else 0
    open_low_pct = (low_price - open_price) / open_price * 100
    volume_ratio = volume / avg_volume_20 if avg_volume_20 > 0 else 0
    
    # Check against thresholds
    checks = {
        'range': range_pct >= SPECIFIED_THRESHOLDS['range_pct'],
        'body': body_pct >= SPECIFIED_THRESHOLDS['body_pct'],
        'lw_body': lw_body_ratio >= SPECIFIED_THRESHOLDS['lw_body_ratio'],
        'lw_range': lw_range_pct >= SPECIFIED_THRESHOLDS['lw_range_pct'],
        'open_low': open_low_pct <= SPECIFIED_THRESHOLDS['open_low_pct'],
        'volume': volume_ratio >= SPECIFIED_THRESHOLDS['volume_ratio']
    }
    
    all_pass = all(checks.values())
    
    return {
        'range_pct': range_pct,
        'body_pct': body_pct,
        'lw_body_ratio': lw_body_ratio,
        'lw_range_pct': lw_range_pct,
        'open_low_pct': open_low_pct,
        'volume_ratio': volume_ratio,
        'checks': checks,
        'all_pass': all_pass
    }


async def main():
    """Main function to test relaxed thresholds."""
    print("=" * 100)
    print("LW-001 RELAXED THRESHOLDS TEST")
    print("=" * 100)
    print()
    print("Specified Thresholds:")
    print(f"  Range >= {SPECIFIED_THRESHOLDS['range_pct']}%")
    print(f"  Body >= {SPECIFIED_THRESHOLDS['body_pct']}%")
    print(f"  LW/Body >= {SPECIFIED_THRESHOLDS['lw_body_ratio']}x")
    print(f"  LW/Range >= {SPECIFIED_THRESHOLDS['lw_range_pct']}%")
    print(f"  Open->Low <= {SPECIFIED_THRESHOLDS['open_low_pct']}%")
    print(f"  Volume Ratio >= {SPECIFIED_THRESHOLDS['volume_ratio']}x")
    print()
    print("Dataset: Top-21-250, 60 days, 15m timeframe")
    print()
    
    all_signals = []
    symbol_signals = defaultdict(list)
    
    for i, symbol in enumerate(TEST_SYMBOLS, 1):
        print(f"[{i}/{len(TEST_SYMBOLS)}] Fetching {symbol}...")
        candles = await fetch_historical_candles_for_symbol(symbol, days=60)
        
        if not candles:
            print(f"  No data")
            continue
        
        print(f"  Collected {len(candles)} candles")
        
        for j in range(len(candles)):
            try:
                open_price = float(candles[j].get('open', 0))
                high_price = float(candles[j].get('high', 0))
                low_price = float(candles[j].get('low', 0))
                close_price = float(candles[j].get('close', 0))
                volume = float(candles[j].get('volume', candles[j].get('vol', 0)))
                timestamp = candles[j].get('time', candles[j].get('timestamp', 0))
                
                if open_price <= 0:
                    continue
                
                avg_volume_20 = calculate_avg_volume_20(candles, j)
                
                metrics = calculate_all_metrics(
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=close_price,
                    volume=volume,
                    reference_average_volume=avg_volume_20
                )
                
                if check_thresholds(metrics, SPECIFIED_THRESHOLDS):
                    signal = {
                        'symbol': symbol,
                        'timestamp': timestamp,
                        'open': open_price,
                        'high': high_price,
                        'low': low_price,
                        'close': close_price,
                        'volume': volume,
                        'avg_volume_20': avg_volume_20,
                        'range_pct': metrics.range_pct,
                        'body_pct': metrics.body_pct,
                        'lw_body_ratio': metrics.lower_wick_body_ratio,
                        'lw_range_pct': metrics.lower_wick_range_pct,
                        'open_low_pct': metrics.open_to_low_pct,
                        'volume_ratio': metrics.volume_ratio
                    }
                    all_signals.append(signal)
                    symbol_signals[symbol].append(signal)
                    print(f"  SIGNAL FOUND: {symbol} @ {timestamp}")
            except Exception as e:
                continue
    
    print()
    print("=" * 100)
    print("SEARCH COMPLETE")
    print("=" * 100)
    print()
    print(f"Total signals found: {len(all_signals)}")
    print(f"Unique symbols: {len(symbol_signals)}")
    print()
    
    # Get signals from different symbols
    selected_signals = []
    seen_symbols = set()
    
    for signal in all_signals:
        if signal['symbol'] not in seen_symbols:
            selected_signals.append(signal)
            seen_symbols.add(signal['symbol'])
            if len(selected_signals) >= 10:
                break
    
    print(f"Selected {len(selected_signals)} signals from {len(seen_symbols)} different symbols")
    print()
    
    if len(selected_signals) < 10:
        print(f"ERROR: Only found {len(selected_signals)} signals from different symbols. Need 10.")
        return
    
    # Verify each signal independently
    print("=" * 100)
    print("INDEPENDENT VERIFICATION")
    print("=" * 100)
    print()
    
    verified_signals = []
    
    for i, signal in enumerate(selected_signals, 1):
        print(f"Verifying Signal {i}: {signal['symbol']}")
        
        verification = verify_signal_independent(signal)
        
        if verification['all_pass']:
            print(f"  VERIFIED: PASS")
            verified_signals.append(signal)
        else:
            print(f"  VERIFICATION FAILED:")
            for check, passed in verification['checks'].items():
                if not passed:
                    print(f"    {check}: FAIL")
            print(f"  STOPPING TEST")
            print()
            print("ERROR: Signal verification failed. Test stopped.")
            return
        
        print()
    
    print("=" * 100)
    print("ALL 10 SIGNALS VERIFIED SUCCESSFULLY")
    print("=" * 100)
    print()
    
    # Output detailed results
    print("=" * 100)
    print("DETAILED SIGNAL RESULTS")
    print("=" * 100)
    print()
    
    for i, signal in enumerate(verified_signals, 1):
        print(f"Signal {i}: {signal['symbol']}")
        print(f"  Timestamp: {signal['timestamp']}")
        print(f"  OHLCV: O={signal['open']:.4f}, H={signal['high']:.4f}, L={signal['low']:.4f}, C={signal['close']:.4f}, V={signal['volume']:.2f}")
        print()
        print(f"  Metrics:")
        print(f"    Range: {signal['range_pct']:.2f}% (threshold: {SPECIFIED_THRESHOLDS['range_pct']}%) - {'PASS' if signal['range_pct'] >= SPECIFIED_THRESHOLDS['range_pct'] else 'FAIL'}")
        print(f"    Body: {signal['body_pct']:.2f}% (threshold: {SPECIFIED_THRESHOLDS['body_pct']}%) - {'PASS' if signal['body_pct'] >= SPECIFIED_THRESHOLDS['body_pct'] else 'FAIL'}")
        print(f"    LW/Body: {signal['lw_body_ratio']:.2f}x (threshold: {SPECIFIED_THRESHOLDS['lw_body_ratio']}x) - {'PASS' if signal['lw_body_ratio'] >= SPECIFIED_THRESHOLDS['lw_body_ratio'] else 'FAIL'}")
        print(f"    LW/Range: {signal['lw_range_pct']:.2f}% (threshold: {SPECIFIED_THRESHOLDS['lw_range_pct']}%) - {'PASS' if signal['lw_range_pct'] >= SPECIFIED_THRESHOLDS['lw_range_pct'] else 'FAIL'}")
        print(f"    Open->Low: {signal['open_low_pct']:.2f}% (threshold: {SPECIFIED_THRESHOLDS['open_low_pct']}%) - {'PASS' if signal['open_low_pct'] <= SPECIFIED_THRESHOLDS['open_low_pct'] else 'FAIL'}")
        print(f"    Volume Ratio: {signal['volume_ratio']:.2f}x (threshold: {SPECIFIED_THRESHOLDS['volume_ratio']}x) - {'PASS' if signal['volume_ratio'] >= SPECIFIED_THRESHOLDS['volume_ratio'] else 'FAIL'}")
        print(f"  Result: VALID SIGNAL")
        print()
    
    print("=" * 100)
    print("TEST COMPLETE")
    print("=" * 100)
    print()
    print(f"Found and verified {len(verified_signals)} valid LW-001 signals on {len(seen_symbols)} different symbols.")
    print()
    print("READY TO SEND TO TELEGRAM - AWAITING USER COMMAND")


if __name__ == "__main__":
    asyncio.run(main())
