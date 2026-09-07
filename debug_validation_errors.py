#!/usr/bin/env python3
"""
Debug validation sample errors.

Research: Investigate why 55/100 signals have ERROR classification.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import json

# Load validation performance analysis
with open("validation_performance_analysis.json", "r") as f:
    data = json.load(f)

candidates = data["candidates"]

# Find ERROR signals
error_signals = [c for c in candidates if c["category"] == "ERROR"]

print(f"Total ERROR signals: {len(error_signals)}")
print(f"\nFirst 5 ERROR signals:")

for i, signal in enumerate(error_signals[:5]):
    print(f"\n--- Signal {i+1} ---")
    print(f"Symbol: {signal['symbol']}")
    print(f"Time: {signal['event_time']}")
    print(f"Performance error: {signal['performance'].get('error', 'No error field')}")

# Check if there are duplicates
timestamps = [c['timestamp_ms'] for c in candidates]
duplicates = [t for t in timestamps if timestamps.count(t) > 1]
print(f"\nDuplicate timestamps: {len(set(duplicates))} unique duplicates")
