#!/usr/bin/env python3
"""
Send 10 historical signals to Telegram.

DO NOT modify LW-001, production, PASS_CHECK, or Telegram logic.
This is RESEARCH only.
"""

import json
import os
import sys
import asyncio
import aiohttp
from dotenv import load_dotenv


def format_telegram_message(signals):
    """Format signals for Telegram message."""
    lines = []
    
    lines.append("10 Historical LW-001 Signals")
    lines.append("")
    lines.append("Target Parameters:")
    lines.append("- Range: 4%")
    lines.append("- Body: 1.8%")
    lines.append("- LW/Body: 2.0x")
    lines.append("- LW/Range: 60%")
    lines.append("- Open to Low: -5%")
    lines.append("- Volume Ratio: 2.0x")
    lines.append("")
    lines.append("=" * 40)
    lines.append("")
    
    for i, signal in enumerate(signals, 1):
        lines.append(f"{i}. {signal['symbol']}")
        lines.append(f"   Time: {signal['event_time']}")
        lines.append(f"   Entry: {signal['close']}")
        lines.append(f"   Range: {signal['metrics']['range_percent']:.2f}%")
        lines.append(f"   Body: {signal['metrics']['body_percent']:.2f}%")
        lines.append(f"   LW/Body: {signal['metrics']['lower_wick_body_ratio']:.2f}x")
        lines.append(f"   LW/Range: {signal['metrics']['lower_wick_range_ratio']*100:.1f}%")
        lines.append(f"   Open to Low: {signal['metrics']['open_to_low_percent']:.2f}%")
        if signal['metrics']['volume_ratio']:
            lines.append(f"   Volume Ratio: {signal['metrics']['volume_ratio']:.2f}x")
        else:
            lines.append(f"   Volume Ratio: N/A")
        lines.append(f"   Deviation: {signal['deviation']:.2f}")
        
        # Result with emoji
        result = signal['performance']['result']
        if result == "TP":
            result_emoji = "[TP]"
        elif result == "SL":
            result_emoji = "[SL]"
        else:
            result_emoji = "[NO_REVERSAL]"
        
        lines.append(f"   Result: {result_emoji}")
        
        if signal['performance']['time_to_result_candles']:
            lines.append(f"   Time to result: {signal['performance']['time_to_result_candles']} candles")
        else:
            lines.append(f"   Time to result: N/A")
        
        lines.append("")
    
    # Summary
    tp_count = sum(1 for s in signals if s['performance']['result'] == "TP")
    sl_count = sum(1 for s in signals if s['performance']['result'] == "SL")
    no_rev_count = sum(1 for s in signals if s['performance']['result'] == "NO_REVERSAL")
    
    lines.append("=" * 40)
    lines.append("")
    lines.append("Summary:")
    lines.append(f"[TP]: {tp_count}/10 ({tp_count*10}%)")
    lines.append(f"[SL]: {sl_count}/10 ({sl_count*10}%)")
    lines.append(f"[NO_REVERSAL]: {no_rev_count}/10 ({no_rev_count*10}%)")
    lines.append("")
    lines.append("This is historical research data only.")
    lines.append("No changes to LW-001, production, or Telegram logic.")
    
    return "\n".join(lines)


async def main():
    """Main function."""
    print("=" * 100)
    print("SENDING 10 HISTORICAL SIGNALS TO TELEGRAM")
    print("=" * 100)
    
    # Load environment
    load_dotenv()
    
    bot_token = os.getenv("EVRECONSE_TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("EVRECONSE_TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not found in environment")
        return
    
    # Load results
    with open("target_signals.json", "r") as f:
        data = json.load(f)
    
    signals = data["selected_signals"]
    
    print(f"\nLoaded {len(signals)} signals")
    
    # Format message
    message = format_telegram_message(signals)
    
    print(f"\nMessage length: {len(message)} characters")
    
    # Send to Telegram using simple HTTP request
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                result = await response.json()
                
                if result.get("ok"):
                    print("\nMessage sent to Telegram successfully")
                else:
                    print(f"\nError sending to Telegram: {result}")
                    print(f"Message content:\n{message}")
        
    except Exception as e:
        print(f"\nError sending to Telegram: {str(e)}")
        print(f"Message content:\n{message}")
    
    print(f"\n{'=' * 100}")


if __name__ == "__main__":
    asyncio.run(main())
