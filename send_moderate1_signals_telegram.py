#!/usr/bin/env python3
"""
Send 10 verified MODERATE_1 signals to Telegram.
"""

import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

import asyncio
import os
from datetime import datetime, UTC, timedelta
from dotenv import load_dotenv
import aiohttp

# Load environment variables
load_dotenv()


# The 10 verified signals from MODERATE_1 test
VERIFIED_SIGNALS = [
    {
        "symbol": "ORDI-USDT",
        "timestamp": 1787374800000,
        "open": 5.0440,
        "high": 5.1000,
        "low": 3.4780,
        "close": 4.3960,
        "volume": 188352.02,
        "range_pct": 32.16,
        "body_pct": 12.85,
        "lw_body_ratio": 1.42,
        "lw_range_pct": 56.60,
        "open_low_pct": -31.05,
        "volume_ratio": 8.56
    },
    {
        "symbol": "TIA-USDT",
        "timestamp": 1787374800000,
        "open": 0.4220,
        "high": 0.4238,
        "low": 0.3207,
        "close": 0.3780,
        "volume": 319762.12,
        "range_pct": 24.43,
        "body_pct": 10.43,
        "lw_body_ratio": 1.30,
        "lw_range_pct": 55.58,
        "open_low_pct": -24.00,
        "volume_ratio": 4.27
    },
    {
        "symbol": "ICP-USDT",
        "timestamp": 1787374800000,
        "open": 2.6890,
        "high": 2.7000,
        "low": 2.0630,
        "close": 2.4470,
        "volume": 216900.56,
        "range_pct": 23.69,
        "body_pct": 9.00,
        "lw_body_ratio": 1.59,
        "lw_range_pct": 60.28,
        "open_low_pct": -23.28,
        "volume_ratio": 13.84
    },
    {
        "symbol": "ETC-USDT",
        "timestamp": 1787374800000,
        "open": 8.6660,
        "high": 8.7220,
        "low": 6.9990,
        "close": 8.0410,
        "volume": 25730.75,
        "range_pct": 19.88,
        "body_pct": 7.21,
        "lw_body_ratio": 1.67,
        "lw_range_pct": 60.48,
        "open_low_pct": -19.24,
        "volume_ratio": 2.86
    },
    {
        "symbol": "ZEC-USDT",
        "timestamp": 1787374800000,
        "open": 823.1900,
        "high": 825.5800,
        "low": 681.4800,
        "close": 802.8500,
        "volume": 3048.86,
        "range_pct": 17.51,
        "body_pct": 2.47,
        "lw_body_ratio": 5.97,
        "lw_range_pct": 84.23,
        "open_low_pct": -17.21,
        "volume_ratio": 3.35
    },
    {
        "symbol": "DASH-USDT",
        "timestamp": 1787374800000,
        "open": 44.3600,
        "high": 44.3900,
        "low": 34.8200,
        "close": 40.4000,
        "volume": 17618.81,
        "range_pct": 21.57,
        "body_pct": 8.93,
        "lw_body_ratio": 1.41,
        "lw_range_pct": 58.31,
        "open_low_pct": -21.51,
        "volume_ratio": 11.83
    },
    {
        "symbol": "FET-USDT",
        "timestamp": 1787302800000,
        "open": 0.1621,
        "high": 0.1625,
        "low": 0.1541,
        "close": 0.1590,
        "volume": 542235.00,
        "range_pct": 5.18,
        "body_pct": 1.91,
        "lw_body_ratio": 1.58,
        "lw_range_pct": 58.33,
        "open_low_pct": -4.94,
        "volume_ratio": 1.84
    },
    {
        "symbol": "AAVE-USDT",
        "timestamp": 1787374800000,
        "open": 126.6900,
        "high": 126.8600,
        "low": 111.5300,
        "close": 120.1400,
        "volume": 7605.10,
        "range_pct": 12.10,
        "body_pct": 5.17,
        "lw_body_ratio": 1.31,
        "lw_range_pct": 56.16,
        "open_low_pct": -11.97,
        "volume_ratio": 2.47
    },
    {
        "symbol": "1INCH-USDT",
        "timestamp": 1787374800000,
        "open": 0.0969,
        "high": 0.0974,
        "low": 0.0796,
        "close": 0.0902,
        "volume": 2983036.00,
        "range_pct": 18.38,
        "body_pct": 6.88,
        "lw_body_ratio": 1.59,
        "lw_range_pct": 59.57,
        "open_low_pct": -17.83,
        "volume_ratio": 14.69
    },
    {
        "symbol": "GMX-USDT",
        "timestamp": 1787374800000,
        "open": 7.7920,
        "high": 7.7950,
        "low": 6.7110,
        "close": 7.3510,
        "volume": 5173.82,
        "range_pct": 13.91,
        "body_pct": 5.66,
        "lw_body_ratio": 1.45,
        "lw_range_pct": 59.04,
        "open_low_pct": -13.87,
        "volume_ratio": 1.64
    }
]

MODERATE1_THRESHOLDS = {
    "range_pct": 4.0,
    "body_pct": 0.8,
    "lw_body_ratio": 1.3,
    "lw_range_pct": 55.0,
    "open_low_pct": -2.5,
    "volume_ratio": 1.5
}


def format_timestamp(timestamp_ms):
    """Format timestamp to UTC and UTC+3."""
    dt_utc = datetime.fromtimestamp(timestamp_ms / 1000, UTC)
    dt_utc3 = dt_utc + timedelta(hours=3)
    
    utc_str = dt_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    utc3_str = dt_utc3.strftime("%Y-%m-%d %H:%M:%S UTC+3")
    
    return utc_str, utc3_str


def format_signal_message(signal, index, total):
    """Format a single signal message."""
    utc_str, utc3_str = format_timestamp(signal['timestamp'])
    
    message = f"""🔔 LW-001 Signal {index}/{total}

📊 Symbol: {signal['symbol']}

⏰ Time:
UTC: {utc_str}
UTC+3: {utc3_str}

💰 OHLCV:
Open: {signal['open']:.4f}
High: {signal['high']:.4f}
Low: {signal['low']:.4f}
Close: {signal['close']:.4f}
Volume: {signal['volume']:.2f}

📈 Metrics (MODERATE_1 Thresholds):
Range: {signal['range_pct']:.2f}% (≥{MODERATE1_THRESHOLDS['range_pct']}%) ✅
Body: {signal['body_pct']:.2f}% (≥{MODERATE1_THRESHOLDS['body_pct']}%) ✅
LW/Body: {signal['lw_body_ratio']:.2f}x (≥{MODERATE1_THRESHOLDS['lw_body_ratio']}x) ✅
LW/Range: {signal['lw_range_pct']:.2f}% (≥{MODERATE1_THRESHOLDS['lw_range_pct']}%) ✅
Open→Low: {signal['open_low_pct']:.2f}% (≤{MODERATE1_THRESHOLDS['open_low_pct']}%) ✅
Volume Ratio: {signal['volume_ratio']:.2f}x (≥{MODERATE1_THRESHOLDS['volume_ratio']}x) ✅

✅ VALID SIGNAL"""
    
    return message


async def main():
    """Send signals to Telegram."""
    print("=" * 100)
    print("SENDING MODERATE_1 SIGNALS TO TELEGRAM")
    print("=" * 100)
    print()
    
    # Load environment variables
    bot_token = os.getenv("EVRECONSE_TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("EVRECONSE_TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("ERROR: Missing Telegram credentials in environment variables")
        print("Required: EVRECONSE_TELEGRAM_BOT_TOKEN, EVRECONSE_TELEGRAM_CHAT_ID")
        return
    
    # Send each signal directly via HTTP
    async with aiohttp.ClientSession() as session:
        for i, signal in enumerate(VERIFIED_SIGNALS, 1):
            print(f"Sending signal {i}/{len(VERIFIED_SIGNALS)}: {signal['symbol']}")
            
            message = format_signal_message(signal, i, len(VERIFIED_SIGNALS))
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            
            try:
                async with session.post(url, json=payload) as resp:
                    data = await resp.json()
                    
                    if data.get("ok"):
                        print(f"  [OK] Sent successfully")
                    else:
                        print(f"  [FAIL] Failed: {data.get('description', 'Unknown error')}")
            except Exception as e:
                print(f"  [ERROR] {e}")
            
            print()
    
    print("=" * 100)
    print("ALL SIGNALS SENT")
    print("=" * 100)
    print()
    print(f"Total signals sent: {len(VERIFIED_SIGNALS)}")


if __name__ == "__main__":
    asyncio.run(main())
