#!/usr/bin/env python3
"""
Send all massive historical signals to Telegram in batches.

DO NOT modify LW-001, production, PASS_CHECK, or Telegram logic.
This is RESEARCH only.
"""

import json
import os
import sys
import asyncio
import aiohttp
from dotenv import load_dotenv


def format_signal_message(signal):
    """Format a single signal for Telegram."""
    lines = []
    
    lines.append(f"{signal['symbol']}")
    lines.append(f"Time: {signal['event_time']}")
    lines.append(f"Entry: {signal['close']}")
    lines.append(f"Range: {signal['metrics']['range_percent']:.2f}%")
    lines.append(f"Body: {signal['metrics']['body_percent']:.2f}%")
    lines.append(f"LW/Body: {signal['metrics']['lower_wick_body_ratio']:.2f}x")
    lines.append(f"LW/Range: {signal['metrics']['lower_wick_range_ratio']*100:.1f}%")
    lines.append(f"Open to Low: {signal['metrics']['open_to_low_percent']:.2f}%")
    if signal['metrics']['volume_ratio']:
        lines.append(f"Volume Ratio: {signal['metrics']['volume_ratio']:.2f}x")
    else:
        lines.append(f"Volume Ratio: N/A")
    lines.append(f"Deviation: {signal['deviation']:.2f}")
    
    result = signal['performance']['result']
    if result == "TP":
        result_emoji = "[TP]"
    elif result == "SL":
        result_emoji = "[SL]"
    else:
        result_emoji = "[NO_REVERSAL]"
    
    lines.append(f"Result: {result_emoji}")
    
    if signal['performance']['time_to_result_candles']:
        lines.append(f"Time to result: {signal['performance']['time_to_result_candles']} candles")
    else:
        lines.append(f"Time to result: N/A")
    
    return "\n".join(lines)


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
    print("SENDING MASSIVE HISTORICAL SIGNALS TO TELEGRAM")
    print("=" * 100)
    
    # Load environment
    load_dotenv()
    
    bot_token = os.getenv("EVRECONSE_TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("EVRECONSE_TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not found in environment")
        return
    
    # Load results
    with open("new_historical_signals.json", "r") as f:
        data = json.load(f)
    
    signals = data["signals"]
    
    print(f"\nLoaded {len(signals)} signals")
    print("Sending in batches of 10 signals per message...")
    
    # Send in batches of 10 signals per message
    batch_size = 10
    total_batches = (len(signals) + batch_size - 1) // batch_size
    
    success_count = 0
    error_count = 0
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(signals))
        batch_signals = signals[start_idx:end_idx]
        
        # Format batch message
        lines = []
        lines.append(f"Batch {batch_num + 1}/{total_batches}")
        lines.append(f"Signals {start_idx + 1}-{end_idx} of {len(signals)}")
        lines.append("")
        
        for i, signal in enumerate(batch_signals, 1):
            lines.append(f"{start_idx + i}. {format_signal_message(signal)}")
            lines.append("")
        
        message = "\n".join(lines)
        
        # Send message
        try:
            success = await send_telegram_message(bot_token, chat_id, message)
            
            if success:
                success_count += 1
                print(f"  Batch {batch_num + 1}/{total_batches}: Sent successfully")
            else:
                error_count += 1
                print(f"  Batch {batch_num + 1}/{total_batches}: Failed to send")
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(1)
            
        except Exception as e:
            error_count += 1
            print(f"  Batch {batch_num + 1}/{total_batches}: Error - {str(e)}")
    
    print(f"\n{'=' * 100}")
    print(f"Sending complete:")
    print(f"  Successful batches: {success_count}/{total_batches}")
    print(f"  Failed batches: {error_count}/{total_batches}")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    asyncio.run(main())
