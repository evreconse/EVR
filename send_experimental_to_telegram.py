#!/usr/bin/env python3
"""
Send experimental candidates to Telegram for manual verification.

DO NOT modify existing LW-001 strategy, production, backtest, PASS_CHECK, or Telegram.
This is RESEARCH only.
"""

import json
import sys
import os
from dotenv import load_dotenv
import aiohttp

load_dotenv()


def format_signal_message(candidates):
    """Format candidates into Telegram message."""
    message = "🔬 ЭКСПЕРИМЕНТАЛЬНЫЕ СИГНАЛЫ (Formula 3)\n\n"
    message += "Фильтр:\n"
    message += "• Open -> Low <= -2.5%\n"
    message += "• Volume Ratio >= 0.75\n"
    message += "• LW/Range >= 40%\n"
    message += "• LW/Body >= 0.75\n"
    message += "• Range% >= 2.5%\n"
    message += "• Body% >= 0.30%\n\n"
    
    for i, cand in enumerate(candidates, 1):
        message += f"📊 {i}. {cand['symbol']}\n"
        message += f"   {cand['event_time']} / {cand['event_time_msk']}\n"
        message += f"   O={cand['open']:.6f} H={cand['high']:.6f} L={cand['low']:.6f} C={cand['close']:.6f}\n"
        message += f"   Body%={cand['formula_details']['body_percent']:.4f}% Range%={cand['formula_details']['range_percent']:.4f}%\n"
        message += f"   LW/Body={cand['lower_wick_body_ratio']:.2f}x LW/Range={cand['lower_wick_range_ratio']*100:.1f}%\n"
        message += f"   Vol Ratio={cand['volume_ratio']:.2f}x Open->Low%={cand['formula_details']['open_to_low_percent']:.4f}%\n\n"
    
    message += "⚠️ Это ИССЛЕДОВАНИЕ. Проверьте вручную."
    
    return message


async def send_telegram_message(message: str):
    """Send message to Telegram using API."""
    bot_token = os.getenv("EVRECONSE_TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("EVRECONSE_TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        raise ValueError("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in environment")
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            result = await response.json()
            if not result.get("ok"):
                raise Exception(f"Telegram API error: {result}")
            return result


async def main():
    """Main function to send to Telegram."""
    print("=" * 100)
    print("SENDING EXPERIMENTAL CANDIDATES TO TELEGRAM")
    print("=" * 100)
    
    # Load candidates
    with open("experimental_candidates_formula3.json", "r") as f:
        candidates = json.load(f)
    
    print(f"Loaded {len(candidates)} candidates")
    
    # Format message
    message = format_signal_message(candidates)
    
    # Split message if too long (Telegram limit is 4096 chars)
    messages = []
    current_message = ""
    
    for line in message.split('\n'):
        if len(current_message) + len(line) + 1 > 4000:
            messages.append(current_message)
            current_message = line
        else:
            if current_message:
                current_message += '\n' + line
            else:
                current_message = line
    
    if current_message:
        messages.append(current_message)
    
    print(f"Split into {len(messages)} message(s)")
    
    for i, msg in enumerate(messages, 1):
        print(f"Sending message {i}/{len(messages)}...")
        try:
            await send_telegram_message(msg)
            print(f"Message {i} sent successfully")
        except Exception as e:
            print(f"Error sending message {i}: {e}")
    
    print("\n" + "=" * 100)
    print("TELEGRAM SEND COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
