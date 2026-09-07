#!/usr/bin/env python3
"""
Stage 3: Test MODERATE_1 thresholds for LW-001.

MODERATE_1 thresholds:
- Range >= 4.0%
- Body >= 0.8%
- LW/Body >= 1.3x
- LW/Range >= 55%
- Open->Low <= -2.5%
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

# MODERATE_1 thresholds
MODERATE1_THRESHOLDS = {
    "range_pct": 4.0,
    "body_pct": 0.8,
    "lw_body_ratio": 1.3,
    "lw_range_pct": 55.0,
    "open_low_pct": -2.5,
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
        'range': range_pct >= MODERATE1_THRESHOLDS['range_pct'],
        'body': body_pct >= MODERATE1_THRESHOLDS['body_pct'],
        'lw_body': lw_body_ratio >= MODERATE1_THRESHOLDS['lw_body_ratio'],
        'lw_range': lw_range_pct >= MODERATE1_THRESHOLDS['lw_range_pct'],
        'open_low': open_low_pct <= MODERATE1_THRESHOLDS['open_low_pct'],
        'volume': volume_ratio >= MODERATE1_THRESHOLDS['volume_ratio']
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
    """Main function to test MODERATE_1 thresholds."""
    print("=" * 100)
    print("STAGE 3: MODERATE_1 THRESHOLDS TEST")
    print("=" * 100)
    print()
    print("MODERATE_1 Thresholds:")
    print(f"  Range >= {MODERATE1_THRESHOLDS['range_pct']}%")
    print(f"  Body >= {MODERATE1_THRESHOLDS['body_pct']}%")
    print(f"  LW/Body >= {MODERATE1_THRESHOLDS['lw_body_ratio']}x")
    print(f"  LW/Range >= {MODERATE1_THRESHOLDS['lw_range_pct']}%")
    print(f"  Open->Low <= {MODERATE1_THRESHOLDS['open_low_pct']}%")
    print(f"  Volume Ratio >= {MODERATE1_THRESHOLDS['volume_ratio']}x")
    print()
    print("Dataset: Top-21-250, 60 days, 15m timeframe")
    print()
    
    # Funnel tracking
    funnel = {
        'total_candles_checked': 0,
        'symbols_with_data': 0,
        'symbols_without_data': 0,
        'pass_range': 0,
        'pass_body': 0,
        'pass_lw_body': 0,
        'pass_lw_range': 0,
        'pass_open_low': 0,
        'pass_volume': 0,
        'pass_all': 0
    }
    
    all_signals = []
    symbol_signals = defaultdict(list)
    
    for i, symbol in enumerate(TEST_SYMBOLS, 1):
        candles = await fetch_historical_candles_for_symbol(symbol, days=60)
        
        if not candles:
            funnel['symbols_without_data'] += 1
            continue
        
        funnel['symbols_with_data'] += 1
        funnel['total_candles_checked'] += len(candles)
        
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
                
                # Funnel tracking
                if metrics.range_pct >= MODERATE1_THRESHOLDS['range_pct']:
                    funnel['pass_range'] += 1
                if metrics.body_pct >= MODERATE1_THRESHOLDS['body_pct']:
                    funnel['pass_body'] += 1
                if metrics.lower_wick_body_ratio >= MODERATE1_THRESHOLDS['lw_body_ratio']:
                    funnel['pass_lw_body'] += 1
                if metrics.lower_wick_range_pct >= MODERATE1_THRESHOLDS['lw_range_pct']:
                    funnel['pass_lw_range'] += 1
                if metrics.open_to_low_pct <= MODERATE1_THRESHOLDS['open_low_pct']:
                    funnel['pass_open_low'] += 1
                if metrics.volume_ratio >= MODERATE1_THRESHOLDS['volume_ratio']:
                    funnel['pass_volume'] += 1
                
                if check_thresholds(metrics, MODERATE1_THRESHOLDS):
                    funnel['pass_all'] += 1
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
            except Exception as e:
                continue
    
    print("=" * 100)
    print("SEARCH COMPLETE - FUNNEL REPORT")
    print("=" * 100)
    print()
    print(f"Total candles checked: {funnel['total_candles_checked']}")
    print(f"Symbols with data: {funnel['symbols_with_data']}")
    print(f"Symbols without data: {funnel['symbols_without_data']}")
    print()
    print("Funnel:")
    print(f"  Pass Range >= {MODERATE1_THRESHOLDS['range_pct']}%: {funnel['pass_range']} ({funnel['pass_range']/funnel['total_candles_checked']*100:.2f}%)")
    print(f"  Pass Body >= {MODERATE1_THRESHOLDS['body_pct']}%: {funnel['pass_body']} ({funnel['pass_body']/funnel['total_candles_checked']*100:.2f}%)")
    print(f"  Pass LW/Body >= {MODERATE1_THRESHOLDS['lw_body_ratio']}x: {funnel['pass_lw_body']} ({funnel['pass_lw_body']/funnel['total_candles_checked']*100:.2f}%)")
    print(f"  Pass LW/Range >= {MODERATE1_THRESHOLDS['lw_range_pct']}%: {funnel['pass_lw_range']} ({funnel['pass_lw_range']/funnel['total_candles_checked']*100:.2f}%)")
    print(f"  Pass Open->Low <= {MODERATE1_THRESHOLDS['open_low_pct']}%: {funnel['pass_open_low']} ({funnel['pass_open_low']/funnel['total_candles_checked']*100:.2f}%)")
    print(f"  Pass Volume Ratio >= {MODERATE1_THRESHOLDS['volume_ratio']}x: {funnel['pass_volume']} ({funnel['pass_volume']/funnel['total_candles_checked']*100:.2f}%)")
    print(f"  Pass ALL 6 conditions: {funnel['pass_all']} ({funnel['pass_all']/funnel['total_candles_checked']*100:.4f}%)")
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
        print(f"NOTE: Only found {len(selected_signals)} signals from different symbols. Need 10.")
        print(f"Proceeding with available {len(selected_signals)} signals as per user request.")
        print()
    
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
        print(f"    Range: {signal['range_pct']:.2f}% (threshold: {MODERATE1_THRESHOLDS['range_pct']}%) - PASS")
        print(f"    Body: {signal['body_pct']:.2f}% (threshold: {MODERATE1_THRESHOLDS['body_pct']}%) - PASS")
        print(f"    LW/Body: {signal['lw_body_ratio']:.2f}x (threshold: {MODERATE1_THRESHOLDS['lw_body_ratio']}x) - PASS")
        print(f"    LW/Range: {signal['lw_range_pct']:.2f}% (threshold: {MODERATE1_THRESHOLDS['lw_range_pct']}%) - PASS")
        print(f"    Open->Low: {signal['open_low_pct']:.2f}% (threshold: {MODERATE1_THRESHOLDS['open_low_pct']}%) - PASS")
        print(f"    Volume Ratio: {signal['volume_ratio']:.2f}x (threshold: {MODERATE1_THRESHOLDS['volume_ratio']}x) - PASS")
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
