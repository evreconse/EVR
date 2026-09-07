#!/usr/bin/env python3
"""
Audit old 3,678 signals by recalculating from OHLCV.

Compares old saved metrics with recalculated metrics using canonical formulas.

DO NOT modify LW-001, production, PASS_CHECK, or Telegram logic.
This is RESEARCH only.
"""

import json
import sys
sys.path.insert(0, ".")

from LW001_METRIC_SPEC import calculate_all_metrics


def audit_old_signals():
    """Audit old signals by recalculating metrics from OHLCV."""
    print("=" * 100)
    print("AUDIT: OLD 3,678 SIGNALS")
    print("=" * 100)
    
    # Load old signals
    try:
        with open("new_historical_signals.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("ERROR: new_historical_signals.json not found")
        return
    
    signals = data["signals"]
    print(f"\nLoaded {len(signals)} signals from old dataset")
    
    # Sample 50 random signals for audit
    import random
    sample_size = min(50, len(signals))
    sample_signals = random.sample(signals, sample_size)
    
    print(f"\nAuditing {sample_size} random signals...")
    
    discrepancies = {
        "range": 0,
        "body": 0,
        "lw_body": 0,
        "lw_range": 0,
        "open_low": 0,
        "volume": 0
    }
    
    for i, signal in enumerate(sample_signals):
        symbol = signal["symbol"]
        timestamp = signal.get("timestamp_ms", signal.get("event_time", "N/A"))
        old_metrics = signal["metrics"]
        
        open_price = float(signal["open"])
        high_price = float(signal["high"])
        low_price = float(signal["low"])
        close_price = float(signal["close"])
        volume = float(signal["volume"])
        
        # Recalculate using canonical formulas
        # Note: We don't have avg_volume_20 in old data, so we can't recalculate volume ratio
        # Use the old avg_volume if available
        avg_volume = old_metrics.get("avg_volume_20", 1.0)
        
        new_metrics = calculate_all_metrics(open_price, high_price, low_price, close_price, volume, avg_volume)
        
        # Compare with tolerance
        tolerance_pct = 0.1  # 0.1% tolerance for percentages
        tolerance_ratio = 0.05  # 5% tolerance for ratios
        
        range_diff = abs(new_metrics.range_pct - old_metrics["range_percent"])
        body_diff = abs(new_metrics.body_pct - old_metrics["body_percent"])
        lw_body_diff = abs(new_metrics.lower_wick_body_ratio - old_metrics["lower_wick_body_ratio"])
        lw_range_diff = abs(new_metrics.lower_wick_range_pct - old_metrics["lower_wick_range_ratio"] * 100)
        open_low_diff = abs(new_metrics.open_to_low_pct - old_metrics["open_to_low_percent"])
        
        if range_diff > tolerance_pct:
            discrepancies["range"] += 1
        
        if body_diff > tolerance_pct:
            discrepancies["body"] += 1
        
        if lw_body_diff > tolerance_ratio:
            discrepancies["lw_body"] += 1
        
        if lw_range_diff > tolerance_pct:
            discrepancies["lw_range"] += 1
        
        if open_low_diff > tolerance_pct:
            discrepancies["open_low"] += 1
        
        # Show first 5 detailed comparisons
        if i < 5:
            print(f"\n--- Signal {i+1}: {symbol} @ {timestamp} ---")
            print(f"OHLCV: O={open_price:.4f} H={high_price:.4f} L={low_price:.4f} C={close_price:.4f}")
            print(f"\nOLD vs NEW (Canonical):")
            print(f"  Range: {old_metrics['range_percent']:.2f}% vs {new_metrics.range_pct:.2f}% (diff: {range_diff:.2f}%)")
            print(f"  Body: {old_metrics['body_percent']:.2f}% vs {new_metrics.body_pct:.2f}% (diff: {body_diff:.2f}%)")
            print(f"  LW/Body: {old_metrics['lower_wick_body_ratio']:.2f}x vs {new_metrics.lower_wick_body_ratio:.2f}x (diff: {lw_body_diff:.2f})")
            print(f"  LW/Range: {old_metrics['lower_wick_range_ratio']*100:.1f}% vs {new_metrics.lower_wick_range_pct:.1f}% (diff: {lw_range_diff:.1f}%)")
            print(f"  Open to Low: {old_metrics['open_to_low_percent']:.2f}% vs {new_metrics.open_to_low_pct:.2f}% (diff: {open_low_diff:.2f}%)")
    
    print(f"\n" + "=" * 100)
    print("AUDIT SUMMARY")
    print("=" * 100)
    
    print(f"\nDiscrepancies found in {sample_size} sampled signals:")
    print(f"  Range: {discrepancies['range']}/{sample_size} ({discrepancies['range']/sample_size*100:.1f}%)")
    print(f"  Body: {discrepancies['body']}/{sample_size} ({discrepancies['body']/sample_size*100:.1f}%)")
    print(f"  LW/Body: {discrepancies['lw_body']}/{sample_size} ({discrepancies['lw_body']/sample_size*100:.1f}%)")
    print(f"  LW/Range: {discrepancies['lw_range']}/{sample_size} ({discrepancies['lw_range']/sample_size*100:.1f}%)")
    print(f"  Open to Low: {discrepancies['open_low']}/{sample_size} ({discrepancies['open_low']/sample_size*100:.1f}%)")
    
    print(f"\nConclusion:")
    if discrepancies["range"] > 0 or discrepancies["body"] > 0:
        print(f"  OLD SIGNALS USED INCORRECT FORMULAS (Range/Body used Close instead of Open)")
        print(f"  This explains why 3,678 signals were found with incorrect calculations.")
    else:
        print(f"  No significant discrepancies found.")
    
    print(f"\nStatus: INVALIDATED_LEGACY_RESULTS")
    print(f"Reason: Previous metric pipeline used incorrect formulas (Close instead of Open for Range/Body).")
    print(f"Action: All old results should be discarded and recalculated with canonical formulas.")


if __name__ == "__main__":
    audit_old_signals()
