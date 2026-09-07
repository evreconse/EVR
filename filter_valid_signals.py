#!/usr/bin/env python3
"""
Filter valid signals from validation sample.

Research: Remove ERROR signals and work with valid data only.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import json

# Load validation performance analysis
with open("validation_performance_analysis.json", "r") as f:
    data = json.load(f)

candidates = data["candidates"]

# Filter valid signals (not ERROR)
valid_signals = [c for c in candidates if c["category"] != "ERROR"]

print(f"Total signals: {len(candidates)}")
print(f"ERROR signals: {len(candidates) - len(valid_signals)}")
print(f"Valid signals: {len(valid_signals)}")

# Save filtered data
filtered_data = {
    "candidates": valid_signals,
    "classification": data["classification"],
    "note": "Filtered out ERROR signals due to API connection errors for historical data"
}

with open("validation_performance_filtered.json", "w") as f:
    json.dump(filtered_data, f, indent=2, default=str)

print(f"\nSaved valid signals to validation_performance_filtered.json")

# Show classification of valid signals
categories = {}
for candidate in valid_signals:
    cat = candidate["category"]
    if cat not in categories:
        categories[cat] = []
    categories[cat].append(candidate)

print(f"\nClassification of valid signals:")
for cat, signals in sorted(categories.items()):
    print(f"{cat}: {len(signals)} signals ({len(signals)/len(valid_signals)*100:.1f}%)")
