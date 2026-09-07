#!/usr/bin/env python3
"""
Real-time LW-001 Monitor

Monitors 15m candles in real-time and sends signals to Telegram when conditions are met.
Uses fixed parameters from Stage 6.
"""

import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

import asyncio
from datetime import datetime, UTC, timedelta
from collections import defaultdict
import os
from dotenv import load_dotenv
import aiohttp
import time

# Load environment variables
load_dotenv()

# Top-20 symbols to exclude
TOP_20_EXCLUDE = {
    "BTC-USDT", "ETH-USDT", "BNB-USDT", "SOL-USDT", "XRP-USDT",
    "DOGE-USDT", "ADA-USDT", "TRX-USDT", "TON-USDT", "AVAX-USDT",
    "SHIB-USDT", "DOT-USDT", "LINK-USDT", "MATIC-USDT", "PEPE-USDT",
    "LTC-USDT", "ATOM-USDT", "NEAR-USDT", "OP-USDT", "ARB-USDT"
}

# Mid-tier symbols (rank 21-250 from CoinMarketCap, filtered)
MID_TIER_SYMBOLS = [
    "GRAM-USDT", "HBAR-USDT", "SUI-USDT", "UNI-USDT", "CRO-USDT",
    "TAO-USDT", "M-USDT", "OKB-USDT", "AAVE-USDT", "ASTER-USDT",
    "PUMP-USDT", "WLFI-USDT", "ONDO-USDT", "MNT-USDT", "SKY-USDT",
    "ENA-USDT", "WLD-USDT", "BGB-USDT", "ICP-USDT", "MORPHO-USDT",
    "U-USDT", "ETC-USDT", "POL-USDT", "PI-USDT", "KCS-USDT",
    "GT-USDT", "LIT-USDT", "VVV-USDT", "KAS-USDT", "ALGO-USDT",
    "JST-USDT", "JUP-USDT", "RENDER-USDT", "QNT-USDT", "TRUMP-USDT",
    "VET-USDT", "XDC-USDT", "PENGU-USDT", "FIL-USDT", "FLR-USDT",
    "NEXO-USDT", "CAKE-USDT", "ETHFI-USDT", "INJ-USDT", "SPX-USDT",
    "AERO-USDT", "DASH-USDT", "CRV-USDT", "STX-USDT", "APT-USDT",
    "VIRTUAL-USDT", "ZRO-USDT", "PYTH-USDT", "FET-USDT", "SEI-USDT",
    "BSV-USDT", "NIGHT-USDT", "MON-USDT", "SUN-USDT", "TIA-USDT",
    "GNO-USDT", "KITE-USDT", "LDO-USDT", "PENDLE-USDT", "PIEVERSE-USDT",
    "LUNC-USDT", "BTT-USDT", "FF-USDT", "BONK-USDT", "IMX-USDT",
    "JTO-USDT", "FLOKI-USDT", "XTZ-USDT", "DCR-USDT", "ENS-USDT",
    "CFX-USDT", "XPL-USDT", "JASMY-USDT", "CVX-USDT", "RAY-USDT",
    "SYRUP-USDT", "WIF-USDT", "ZBCN-USDT", "KAIA-USDT", "FARTCOIN-USDT",
    "2Z-USDT", "COMP-USDT", "TWT-USDT", "IOTA-USDT", "GRT-USDT",
    "STRK-USDT", "TEL-USDT", "THETA-USDT", "EIGEN-USDT", "DEXE-USDT",
    "TRAC-USDT", "RUNE-USDT", "MX-USDT", "AXS-USDT", "AKT-USDT",
    "NEO-USDT", "H-USDT", "VSN-USDT", "MANA-USDT", "CHZ-USDT",
    "KMNO-USDT", "APE-USDT", "XEC-USDT", "AR-USDT", "XCN-USDT",
    "EDGE-USDT", "GOMINING-USDT", "B-USDT", "SFP-USDT", "A-USDT",
    "1INCH-USDT", "AWE-USDT", "SOON-USDT", "MELANIA-USDT", "MET-USDT",
    "ZAMA-USDT", "SAND-USDT", "GLM-USDT", "FLUID-USDT", "CAP-USDT",
    "BAT-USDT", "EGLD-USDT", "WEMIX-USDT", "CHEEMS-USDT", "GEOD-USDT",
    "AB-USDT", "ATH-USDT", "DYDX-USDT", "ZEN-USDT", "GENIUS-USDT",
    "PROM-USDT", "FORM-USDT", "SENT-USDT", "CHIP-USDT", "RSR-USDT",
    "NEX-USDT", "GALA-USDT", "S-USDT", "TAG-USDT", "BANANAS31-USDT",
    "PLUME-USDT", "QTUM-USDT", "XPR-USDT", "DGB-USDT", "ZK-USDT",
    "GRASS-USDT", "BEAM-USDT", "ORDI-USDT", "GAS-USDT", "RE-USDT",
    "YFI-USDT", "ZRX-USDT", "RAIN-USDT", "DEL-USDT", "HTX-USDT",
    "BTW-USDT", "CTM-USDT", "JLP-USDT", "GHO-USDT", "BDX-USDT",
    "UB-USDT", "TIBBIR-USDT", "APEPE-USDT", "AUSD-USDT", "KOGE-USDT",
    "AKE-USDT", "BORG-USDT", "WFI-USDT", "ANSEM-USDT", "LIGHT-USDT",
    "JSM-USDT", "STRCX-USDT", "ALE-USDT", "SHFL-USDT", "NPC-USDT",
    "ZANO-USDT", "RLB-USDT", "DRV-USDT", "VCNT-USDT", "CRCLon-USDT",
    "BP-USDT", "CYS-USDT", "SOSO-USDT", "Q-USDT", "REAL-USDT",
    "AVV-USDT", "PONS-USDT", "ANTFUN-USDT", "YZY-USDT"
]

# Filter out Top-20
MONITOR_SYMBOLS = [s for s in MID_TIER_SYMBOLS if s not in TOP_20_EXCLUDE]

# FIXED LW-001 thresholds (from Stage 6)
FIXED_THRESHOLDS = {
    "range_pct": 4.5,
    "body_pct": 0.8,
    "lw_body_ratio": 1.3,
    "lw_range_pct": 45.0,
    "open_low_pct": -2.5,
    "volume_ratio": 1.5
}

# Track already sent signals (in-memory, could be persisted to file)
SENT_SIGNALS = set()


def format_timestamp_utc(timestamp_ms):
    """Convert raw candle timestamp to UTC format ONLY."""
    timestamp_sec = timestamp_ms / 1000
    dt_utc = datetime.fromtimestamp(timestamp_sec, UTC)
    utc_str = dt_utc.strftime("%d.%m.%Y %H:%M UTC")
    return utc_str


def check_red_candle(open_price, close_price):
    """Check if candle is red (Close < Open)."""
    return close_price < open_price


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


def verify_signal_comprehensive(candle_data, avg_volume_20):
    """Comprehensive verification of a signal."""
    from LW001_METRIC_SPEC import calculate_all_metrics
    
    open_price = float(candle_data['open'])
    high_price = float(candle_data['high'])
    low_price = float(candle_data['low'])
    close_price = float(candle_data['close'])
    volume = float(candle_data['volume'])
    timestamp = candle_data.get('time', candle_data.get('timestamp', 0))
    
    # 1. Check timestamp is valid
    if timestamp <= 0:
        return False, None, "Invalid timestamp"
    
    # 2. Check candle is red (Close < Open)
    if not check_red_candle(open_price, close_price):
        return False, None, "Candle is not red (Close >= Open)"
    
    # 3. Calculate metrics
    metrics = calculate_all_metrics(
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
        volume=volume,
        reference_average_volume=avg_volume_20
    )
    
    # 4. Check all thresholds
    if not check_thresholds(metrics, FIXED_THRESHOLDS):
        return False, None, "Metrics do not pass thresholds"
    
    # 5. Verify timestamp format
    try:
        utc_str = format_timestamp_utc(timestamp)
        if not utc_str.endswith(" UTC"):
            return False, None, "Timestamp format error"
    except:
        return False, None, "Timestamp conversion error"
    
    return True, metrics, "OK"


def format_telegram_message(signal):
    """Format signal using fixed immutable template."""
    metrics = signal['metrics']
    symbol = signal['symbol']
    timestamp = signal['timestamp']
    
    message = f"""📌 **LW-001 SIGNAL**

🪙 **Symbol:** {symbol}

⏰ **Time:** {format_timestamp_utc(timestamp)}

💰 **OHLCV**
Open: {signal['open']:.6f}
High: {signal['high']:.6f}
Low: {signal['low']:.6f}
Close: {signal['close']:.6f}
Volume: {signal['volume']:.2f}

📊 **Metrics**
Range: {metrics.range_pct:.2f}%
Body: {metrics.body_pct:.2f}%
LW/Body: {metrics.lower_wick_body_ratio:.2f}x
LW/Range: {metrics.lower_wick_range_pct:.2f}%
Open→Low: {metrics.open_to_low_pct:.2f}%
Volume Ratio: {metrics.volume_ratio:.2f}x

✅ **Conditions**
Range ≥ 4.5% — PASS
Body ≥ 0.8% — PASS
LW/Body ≥ 1.3x — PASS
LW/Range ≥ 45% — PASS
Open→Low ≤ -2.5% — PASS
Volume Ratio ≥ 1.5x — PASS

✅ **VALID SIGNAL**"""
    
    return message


async def send_signal_to_telegram(signal):
    """Send a single signal to Telegram."""
    bot_token = os.getenv("EVRECONSE_TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("EVRECONSE_TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("ERROR: Telegram credentials not found")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    message = format_telegram_message(signal)
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('ok', False)
                else:
                    print(f"ERROR: Telegram API returned status {resp.status}")
                    return False
    except Exception as e:
        print(f"ERROR sending to Telegram: {e}")
        return False


async def check_latest_candle(symbol):
    """Check the latest completed 15m candle for a symbol."""
    from src.exchange.bingx_fetcher import BingXFetcher
    fetcher = BingXFetcher()
    
    # Fetch last 25 candles (to have 20 for volume average + 5 latest)
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(hours=6)  # 6 hours = 24 candles
    
    try:
        candles = await fetcher.get_klines(
            symbol=symbol,
            interval="15m",
            start_time=int(start_time.timestamp() * 1000),
            end_time=int(end_time.timestamp() * 1000)
        )
        
        if not candles or len(candles) < 21:
            return None
        
        # Get the most recent completed candle (second to last, as last might be incomplete)
        latest_candle = candles[-2]
        timestamp = latest_candle.get('time', latest_candle.get('timestamp', 0))
        
        # Check if this candle was already processed
        if (symbol, timestamp) in SENT_SIGNALS:
            return None
        
        # Calculate average volume from previous 20 candles
        candle_index = len(candles) - 2
        avg_volume_20 = calculate_avg_volume_20(candles, candle_index)
        
        # Verify signal
        passed, metrics, reason = verify_signal_comprehensive(latest_candle, avg_volume_20)
        
        if passed:
            return {
                'symbol': symbol,
                'timestamp': timestamp,
                'open': float(latest_candle['open']),
                'high': float(latest_candle['high']),
                'low': float(latest_candle['low']),
                'close': float(latest_candle['close']),
                'volume': float(latest_candle['volume']),
                'metrics': metrics
            }
        
        return None
        
    except Exception as e:
        try:
            print(f"Error checking {symbol}: {e}")
        except UnicodeEncodeError:
            print(f"Error checking {symbol}: API error (rate limit or temporary issue)")
        return None


async def monitor_symbols():
    """Monitor all symbols for signals."""
    print("="*100)
    print("LW-001 REAL-TIME MONITOR")
    print("="*100)
    print()
    print(f"Monitoring {len(MONITOR_SYMBOLS)} symbols")
    print(f"Timeframe: 15m")
    print(f"Thresholds: Range >= 4.5%, Body >= 0.8%, LW/Body >= 1.3x, LW/Range >= 45%")
    print(f"           Open->Low <= -2.5%, Volume Ratio >= 1.5x")
    print(f"Candle direction: RED only (Close < Open)")
    print()
    print("Press Ctrl+C to stop")
    print()
    print("="*100)
    print()
    
    signals_found = 0
    signals_sent = 0
    
    try:
        while True:
            print(f"[{datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}] Checking symbols...")
            
            for symbol in MONITOR_SYMBOLS:
                signal = await check_latest_candle(symbol)
                
                if signal:
                    signals_found += 1
                    print(f"  SIGNAL FOUND: {signal['symbol']} at {format_timestamp_utc(signal['timestamp'])}")
                    
                    # Mark as sent
                    SENT_SIGNALS.add((signal['symbol'], signal['timestamp']))
                    
                    # Send to Telegram
                    success = await send_signal_to_telegram(signal)
                    if success:
                        signals_sent += 1
                        print(f"    [OK] Sent to Telegram")
                    else:
                        print(f"    [ERROR] Failed to send")
            
            print(f"  Total signals found: {signals_found}, Sent: {signals_sent}")
            print()
            
            # Wait until next 15m candle completes
            now = datetime.now(UTC)
            minutes = now.minute
            seconds = now.second
            
            # Calculate time until next 15m mark (00, 15, 30, 45)
            next_15m = ((minutes // 15) + 1) * 15
            if next_15m >= 60:
                next_15m = 0
                wait_minutes = 60 - minutes + next_15m - (seconds / 60)
            else:
                wait_minutes = next_15m - minutes - (seconds / 60)
            
            # Wait 1 minute after candle completion to ensure data is available
            wait_seconds = int(wait_minutes * 60) + 60
            
            print(f"Waiting {wait_seconds} seconds until next check...")
            print()
            await asyncio.sleep(wait_seconds)
            
    except KeyboardInterrupt:
        print()
        print("="*100)
        print("MONITOR STOPPED")
        print("="*100)
        print()
        print(f"Total signals found: {signals_found}")
        print(f"Total signals sent: {signals_sent}")
        print()


async def main():
    """Main function."""
    await monitor_symbols()


if __name__ == "__main__":
    asyncio.run(main())
