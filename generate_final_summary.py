#!/usr/bin/env python3
"""
Generate and send final summary statistics for massive historical search.

DO NOT modify LW-001, production, PASS_CHECK, or Telegram logic.
This is RESEARCH only.
"""

import json
import os
import sys
import asyncio
import aiohttp
from dotenv import load_dotenv
from statistics import mean, median


async def send_telegram_message(bot_token, chat_id, message):
    """Send a message to Telegram."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        "disable_web_page_preview": True
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            result = await response.json()
            return result.get("ok", False)


async def main():
    """Main function."""
    print("=" * 100)
    print("GENERATING FINAL SUMMARY STATISTICS")
    print("=" * 100)
    
    # Load environment
    load_dotenv()
    
    bot_token = os.getenv("EVRECONSE_TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("EVRECONSE_TELEGRAM_CHAT_ID")
    
    # Load results
    with open("new_historical_signals.json", "r") as f:
        data = json.load(f)
    
    signals = data["signals"]
    successful_symbols = data["successful_symbols"]
    failed_symbols = data["failed_symbols"]
    symbols_checked = data["symbols_checked"]
    
    print(f"\nLoaded {len(signals)} signals")
    
    # Calculate statistics
    tp_signals = [s for s in signals if s['performance']['result'] == "TP"]
    sl_signals = [s for s in signals if s['performance']['result'] == "SL"]
    no_rev_signals = [s for s in signals if s['performance']['result'] == "NO_REVERSAL"]
    error_signals = [s for s in signals if s['performance']['result'] == "ERROR"]
    
    tp_count = len(tp_signals)
    sl_count = len(sl_signals)
    no_rev_count = len(no_rev_signals)
    error_count = len(error_signals)
    total_count = len(signals)
    
    # Time to result statistics
    tp_times = [s['performance']['time_to_result_candles'] for s in tp_signals if s['performance']['time_to_result_candles'] is not None]
    sl_times = [s['performance']['time_to_result_candles'] for s in sl_signals if s['performance']['time_to_result_candles'] is not None]
    
    avg_tp_time = mean(tp_times) if tp_times else None
    median_tp_time = median(tp_times) if tp_times else None
    avg_sl_time = mean(sl_times) if sl_times else None
    median_sl_time = median(sl_times) if sl_times else None
    
    # Per-symbol breakdown
    per_symbol = {}
    for signal in signals:
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
    
    # Format summary message
    lines = []
    lines.append("=" * 50)
    lines.append("MASSIVE HISTORICAL LW-001 SEARCH - FINAL SUMMARY")
    lines.append("=" * 50)
    lines.append("")
    lines.append("SEARCH PARAMETERS:")
    lines.append("- Period: Last 2 months")
    lines.append("- Coins: Top 20-250 range")
    lines.append("- Target: Range 4%, Body 1.8%, LW/Body 2.0x, LW/Range 60%, Open to Low -5%, Volume Ratio 2.0x")
    lines.append("- Deviation threshold: < 10")
    lines.append("")
    lines.append("SEARCH RESULTS:")
    lines.append(f"- Symbols checked: {symbols_checked}")
    lines.append(f"- Successful symbols: {len(successful_symbols)}")
    lines.append(f"- Failed symbols: {len(failed_symbols)}")
    lines.append(f"- Total signals found: {total_count}")
    lines.append("")
    lines.append("PERFORMANCE SUMMARY:")
    lines.append(f"- TP (+3%): {tp_count} ({tp_count/total_count*100:.1f}%)")
    lines.append(f"- SL (-3%): {sl_count} ({sl_count/total_count*100:.1f}%)")
    lines.append(f"- NO_REVERSAL: {no_rev_count} ({no_rev_count/total_count*100:.1f}%)")
    lines.append(f"- ERROR: {error_count}")
    lines.append("")
    
    if avg_tp_time:
        lines.append("TIME STATISTICS:")
        lines.append(f"- Avg time to TP: {avg_tp_time:.1f} candles")
        lines.append(f"- Median time to TP: {median_tp_time:.1f} candles")
        lines.append(f"- Avg time to SL: {avg_sl_time:.1f} candles")
        lines.append(f"- Median time to SL: {median_sl_time:.1f} candles")
        lines.append("")
    
    lines.append("TOP 20 COINS BY SIGNAL COUNT:")
    sorted_symbols = sorted(per_symbol.items(), key=lambda x: x[1]["total"], reverse=True)[:20]
    for symbol, stats in sorted_symbols:
        tp_pct = stats['tp'] / stats['total'] * 100 if stats['total'] > 0 else 0
        sl_pct = stats['sl'] / stats['total'] * 100 if stats['total'] > 0 else 0
        lines.append(f"- {symbol}: {stats['total']} signals (TP: {stats['tp']} ({tp_pct:.1f}%), SL: {stats['sl']} ({sl_pct:.1f}%))")
    
    lines.append("")
    lines.append("=" * 50)
    lines.append("This is historical research data only.")
    lines.append("No changes to LW-001, production, or Telegram logic.")
    lines.append("=" * 50)
    
    message = "\n".join(lines)
    
    print(f"\nMessage length: {len(message)} characters")
    
    # Send to Telegram
    if bot_token and chat_id:
        try:
            success = await send_telegram_message(bot_token, chat_id, message)
            
            if success:
                print("\nSummary sent to Telegram successfully")
            else:
                print("\nFailed to send summary to Telegram")
                print(f"Message content:\n{message}")
        except Exception as e:
            print(f"\nError sending to Telegram: {str(e)}")
    
    print(f"\n{'=' * 100}")
    print("Summary generation complete")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    asyncio.run(main())
