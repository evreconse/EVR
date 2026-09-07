#!/usr/bin/env python3
"""
Generate candlestick chart from diagnostic results.
"""

import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# Load diagnostic results
with open('diagnostic_results.json', 'r') as f:
    results = json.load(f)

# Use BCH-USDT (first result) for the chart
target = results[0]
candles = target['chart_candles']

# Prepare data for plotting
dates = [c['time'] for c in candles]
opens = [c['open'] for c in candles]
highs = [c['high'] for c in candles]
lows = [c['low'] for c in candles]
closes = [c['close'] for c in candles]
is_target = [c['is_target'] for c in candles]

# Create figure
fig, ax = plt.subplots(figsize=(12, 6))

# Plot candlesticks
for i in range(len(candles)):
    date = dates[i]
    open_price = opens[i]
    high = highs[i]
    low = lows[i]
    close = closes[i]
    target = is_target[i]
    
    # Color based on candle direction
    color = 'red' if close < open else 'green'
    
    # Highlight target candle
    linewidth = 3 if target else 1
    alpha = 1.0 if target else 0.7
    
    # Plot wick
    ax.plot([date, date], [low, high], color=color, linewidth=linewidth, alpha=alpha)
    
    # Plot body
    body_height = abs(close - open)
    body_bottom = min(open, close)
    ax.bar(date, body_height, bottom=body_bottom, width=mdates.date2num(date) * 0.0001, 
           color=color, alpha=alpha, edgecolor='black', linewidth=linewidth)

# Format x-axis
ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
plt.xticks(rotation=45)

# Add title and labels
title = f"{target['symbol']} M15 Candlestick Chart\n"
title += f"Target: {target['actual_time_msk']} | Ratio: {target['ratio']:.2f}x\n"
title += f"Open: {target['open']:.4f} | High: {target['high']:.4f} | Low: {target['low']:.4f} | Close: {target['close']:.4f}"
plt.title(title)
plt.xlabel('Time (UTC)')
plt.ylabel('Price')
plt.grid(True, alpha=0.3)
plt.tight_layout()

# Save chart
plt.savefig('BCH_USDT_chart.png', dpi=150, bbox_inches='tight')
print("Chart saved to: BCH_USDT_chart.png")

# Also create a chart for VET-USDT (the one with extremely small body)
target2 = results[8]  # VET-USDT
candles2 = target2['chart_candles']

dates2 = [c['time'] for c in candles2]
opens2 = [c['open'] for c in candles2]
highs2 = [c['high'] for c in candles2]
lows2 = [c['low'] for c in candles2]
closes2 = [c['close'] for c in candles2]
is_target2 = [c['is_target'] for c in candles2]

fig2, ax2 = plt.subplots(figsize=(12, 6))

for i in range(len(candles2)):
    date = dates2[i]
    open_price = opens2[i]
    high = highs2[i]
    low = lows2[i]
    close = closes2[i]
    target = is_target2[i]
    
    color = 'red' if close < open_price else 'green'
    linewidth = 3 if target else 1
    alpha = 1.0 if target else 0.7
    
    ax2.plot([date, date], [low, high], color=color, linewidth=linewidth, alpha=alpha)
    
    body_height = abs(close - open_price)
    body_bottom = min(open_price, close)
    ax2.bar(date, body_height, bottom=body_bottom, width=mdates.date2num(date) * 0.0001, 
            color=color, alpha=alpha, edgecolor='black', linewidth=linewidth)

ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
ax2.xaxis.set_major_locator(mdates.HourLocator(interval=1))
plt.xticks(rotation=45)

title2 = f"{target2['symbol']} M15 Candlestick Chart\n"
title2 += f"Target: {target2['actual_time_msk']} | Ratio: {target2['ratio']:.2f}x\n"
title2 += f"Open: {target2['open']:.6f} | High: {target2['high']:.6f} | Low: {target2['low']:.6f} | Close: {target2['close']:.6f}"
plt.title(title2)
plt.xlabel('Time (UTC)')
plt.ylabel('Price')
plt.grid(True, alpha=0.3)
plt.tight_layout()

plt.savefig('VET_USDT_chart.png', dpi=150, bbox_inches='tight')
print("Chart saved to: VET_USDT_chart.png")
