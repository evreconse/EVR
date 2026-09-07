èt"""
Find 10 Historical LW-001 Signals

Searches historical candle data from BingX to find candles that match LW-001 strategy criteria.
Finds ONE signal per coin (10 different coins total).
Sends found signals to Telegram.
"""
import asyncio
import sys
import os
from datetime import UTC, datetime, timedelta, timezone
from typing import List, Dict, Any

# Add src to path to import production modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models import MarketEvent
from models.enums import Exchange, Timeframe
from strategy.lw_001 import LW001Strategy
from strategy.context import StrategyConfig, StrategyContext
from exchange.bingx_fetcher import BingXFetcher

# Configuration
TIMEFRAME = "15m"
WICK_BODY_RATIO_THRESHOLD = 2.0
TARGET_SIGNALS = 10

# Load symbols from file
def load_symbols() -> List[str]:
    """Load symbols from usdt_perpetual_symbols.py"""
    try:
        with open("usdt_perpetual_symbols.py", "r") as f:
            content = f.read()
            import re
            match = re.search(r'SYMBOLS = \[(.*?)\]', content, re.DOTALL)
            if match:
                symbols_str = match.group(1)
                symbols = [s.strip().strip('"').strip("'") for s in symbols_str.split(',') if s.strip()]
                return symbols
            else:
                raise Exception("Could not parse symbols file")
    except Exception as e:
        print(f"Could not load symbols file: {e}")
        return []

def to_msk(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to MSK (UTC+3)."""
    msk_tz = timezone(timedelta(hours=3))
    return utc_dt.astimezone(msk_tz)

async def find_historical_signals():
    """Find 10 historical candles matching LW-001 strategy - ONE per coin."""
    print("=" * 80)
    print("Finding 10 Historical LW-001 Signals (1 per coin)")
    print("=" * 80)
    print(f"Wick/Body Ratio Threshold: {WICK_BODY_RATIO_THRESHOLD}x")
    print(f"Target Signals: {TARGET_SIGNALS}")
    print("=" * 80)
    print()
    
    # Load symbols
    symbols = load_symbols()
    if not symbols:
        print("No symbols loaded. Exiting.")
        return
    
    print(f"Loaded {len(symbols)} symbols")
    print()
    
    # Initialize strategy
    strategy = LW001Strategy()
    strategy_config = StrategyConfig(
        parameters={
            "lower_wick_ratio": WICK_BODY_RATIO_THRESHOLD,
            "scoring": {
                "lower_wick_weight": 70,
                "confirmation_weight": 30,
                "wick_tier_3x": 70,
                "wick_tier_2_5x": 60,
                "wick_tier_2x": 50,
                "wick_tier_1_5x": 35,
                "wick_tier_1x": 20,
                "wick_tier_doji": 25,
                "confirm_tier_bull_0_6": 30,
                "confirm_tier_bull_0_4": 25,
                "confirm_tier_bull_0_2": 20,
                "confirm_tier_bull_0_1": 15,
                "confirm_tier_bear_0_4": 20,
                "confirm_tier_bear_below": 10,
                "confirm_close_near_high_bonus": 5,
                "confirm_close_near_high_threshold": 0.8,
            }
        },
        enabled=True,
        strategy_id="LW-001",
        version="1.0.0"
    )
    strategy.initialize(strategy_config)
    
    # Initialize BingX fetcher
    api_key = "LY4rJlgmbxIhuniKUTibI16IhHnu937kDdPLOBfbo7BnfjHR3g6e3dUXTWBOj4NT4ZV7l4BRUed9ryYOnFFQ"
    api_secret = "q9DmZfQGGFjqN2yC8VGXVVEw5Ecws2mSmYOHGEEXTKWKIjgcafyrvcQrhKg4YAlBrj8rWaUUVxLiaOjA"
    fetcher = BingXFetcher(api_key=api_key, api_secret=api_secret)
    
    # Search for signals
    found_signals = []
    used_symbols = set()  # Track which symbols already have a signal
    
    # Search period: last 30 days
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=30)
    
    print(f"Searching period: {start_date} to {end_date}")
    print()
    
    for symbol in symbols:
        if len(found_signals) >= TARGET_SIGNALS:
            break
        
        if symbol in used_symbols:
            continue  # Skip if we already have a signal for this symbol
        
        print(f"Searching {symbol}...")
        
        # Convert to BingX format
        bingx_symbol = symbol.replace("USDT", "-USDT")
        
        # Fetch historical data
        start_time = int(start_date.timestamp() * 1000)
        end_time = int(end_date.timestamp() * 1000)
        
        try:
            klines = await fetcher.get_klines(bingx_symbol, TIMEFRAME, limit=10000, start_time=start_time, end_time=end_time)
        except Exception as e:
            print(f"  Error fetching data: {e}")
            continue
        
        if not klines:
            print(f"  No data")
            continue
        
        print(f"  Fetched {len(klines)} candles")
        
        # Process each candle - take FIRST qualifying candle for this symbol
        for kline in klines:
            # Handle dict format
            if isinstance(kline, dict):
                timestamp = int(kline.get("time", 0)) // 1000
                open_p = float(kline.get("open", 0))
                high_p = float(kline.get("high", 0))
                low_p = float(kline.get("low", 0))
                close_p = float(kline.get("close", 0))
                volume = float(kline.get("volume", 0))
            else:
                timestamp = int(kline[0]) // 1000
                open_p = float(kline[1])
                high_p = float(kline[2])
                low_p = float(kline[3])
                close_p = float(kline[4])
                volume = float(kline[5])
            
            dt = datetime.fromtimestamp(timestamp, tz=UTC)
            
            # Compute candle structure
            body = close_p - open_p
            body_size = abs(body)
            upper_wick = high_p - max(open_p, close_p)
            lower_wick = min(open_p, close_p) - low_p
            candle_range = high_p - low_p
            
            # Wick-to-body ratio
            wick_body_ratio = lower_wick / body_size if body_size > 0 else 0.0
            
            # Body ratio
            body_ratio = body_size / candle_range if candle_range > 0 else 0.0
            
            # Close position
            close_position = (close_p - low_p) / candle_range if candle_range > 0 else 0.0
            
            # Check if matches strategy (wick/body ratio >= 2.0)
            if wick_body_ratio >= WICK_BODY_RATIO_THRESHOLD:
                # Create MarketEvent
                market_event = MarketEvent.new(
                    symbol=symbol,
                    exchange=Exchange.BINGX,
                    timeframe=Timeframe.M15,
                    event_time=dt,
                    open_price=open_p,
                    high_price=high_p,
                    low_price=low_p,
                    close_price=close_p,
                    volume=volume
                )
                
                # Create StrategyData with confirm=True (candle is closed)
                from models.market_event import StrategyData
                market_event = MarketEvent(
                    schema_version=market_event.schema_version,
                    metadata=market_event.metadata,
                    market_data=market_event.market_data,
                    strategy_data=StrategyData(
                        strategy_id="LW-001",
                        lower_wick=lower_wick,
                        body=body_size,
                        wick_body_ratio=wick_body_ratio,
                        lower_wick_pct=(lower_wick / candle_range) if candle_range > 0 else 0,
                        body_pct=body_ratio,
                        confirm=True
                    )
                )
                
                # Create StrategyContext
                context = StrategyContext(
                    market_event=market_event,
                    config=strategy_config,
                    data_provider=None,
                    storage=None
                )
                
                # Evaluate with strategy
                try:
                    result = await strategy.evaluate(context)
                    
                    if result.qualified:
                        # Convert to MSK
                        msk_dt = to_msk(dt)
                        
                        signal = {
                            "symbol": symbol,
                            "date": dt.strftime("%Y-%m-%d"),
                            "time_utc": dt.strftime("%H:%M:%S UTC"),
                            "time_msk": msk_dt.strftime("%H:%M:%S MSK"),
                            "timeframe": "M15",
                            "open": open_p,
                            "high": high_p,
                            "low": low_p,
                            "close": close_p,
                            "body": body_size,
                            "lower_wick": lower_wick,
                            "upper_wick": upper_wick,
                            "wick_body_ratio": wick_body_ratio,
                            "body_ratio": body_ratio,
                            "close_position": close_position,
                            "score": result.final_score,
                            "explanation": result.explanation
                        }
                        found_signals.append(signal)
                        used_symbols.add(symbol)
                        print(f"  [+] SIGNAL #{len(found_signals)}: {symbol} at {msk_dt.strftime('%H:%M:%S MSK')} ({dt.strftime('%H:%M:%S UTC')}), wick/body={wick_body_ratio:.2f}x")
                        print(f"  [->] Moving to next symbol (used_symbols now has {len(used_symbols)} symbols)")
                        break  # Take only first signal for this symbol
                except Exception as e:
                    print(f"  Error evaluating: {e}")
        
        # CRITICAL: Check if we have enough signals after processing this symbol
        if len(found_signals) >= TARGET_SIGNALS:
            print(f"  [STOP] Reached target of {TARGET_SIGNALS} signals, stopping search")
            break
        
        print()
    
    print("=" * 80)
    print(f"Found {len(found_signals)} historical signals on {len(used_symbols)} different coins")
    print("=" * 80)
    print()
    
    # Print signals
    for i, signal in enumerate(found_signals, 1):
        print(f"Signal #{i}:")
        print(f"  Coin: {signal['symbol']}")
        print(f"  Date: {signal['date']}")
        print(f"  Time: {signal['time_msk']} ({signal['time_utc']})")
        print(f"  Timeframe: {signal['timeframe']}")
        print(f"  Open: {signal['open']:.4f}")
        print(f"  High: {signal['high']:.4f}")
        print(f"  Low: {signal['low']:.4f}")
        print(f"  Close: {signal['close']:.4f}")
        print(f"  Body: {signal['body']:.4f}")
        print(f"  Lower Wick: {signal['lower_wick']:.4f}")
        print(f"  Upper Wick: {signal['upper_wick']:.4f}")
        print(f"  Wick/Body: {signal['wick_body_ratio']:.2f}x")
        print(f"  Body/Range: {signal['body_ratio']:.2f}")
        print(f"  Close Position: {signal['close_position']:.2f}")
        print(f"  Score: {signal['score']:.1f} (informational)")
        print()
    
    return found_signals

async def send_to_telegram(signals: list):
    """Send found signals to Telegram."""
    print("=" * 80)
    print("Sending signals to Telegram")
    print("=" * 80)
    print()
    
    # Telegram credentials
    bot_token = "8730872028:AAEYFDMfc-Fv9Pe0x7beZL14GP4Jb7cd2_M"
    chat_id = "8307060083"
    
    # Import Telegram service
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    from notification.telegram_service import TelegramService, TelegramConfig
    from uuid import uuid4
    
    # Create custom notification class with required attributes
    class CustomNotification:
        def __init__(self, subject, body, format):
            self.notification_id = uuid4()
            self.subject = subject
            self.body = body
            self.format = format
    
    # Create Telegram service
    config = TelegramConfig(
        bot_token=bot_token,
        chat_id=chat_id,
        parse_mode="HTML"
    )
    service = TelegramService(config)
    
    try:
        await service.connect()
        print("Connected to Telegram")
        print()
        
        for i, signal in enumerate(signals, 1):
            # Format message
            subject = f"LW-001 Historical Signal #{i}"
            body = f"""
<b>Coin:</b> {signal['symbol']}
<b>Date:</b> {signal['date']}
<b>Time:</b> {signal['time_msk']} ({signal['time_utc']})
<b>Timeframe:</b> {signal['timeframe']}

<b>OHLC:</b>
Open: {signal['open']:.4f}
High: {signal['high']:.4f}
Low: {signal['low']:.4f}
Close: {signal['close']:.4f}

<b>Candle Structure:</b>
Body: {signal['body']:.4f}
Lower Wick: {signal['lower_wick']:.4f}
Upper Wick: {signal['upper_wick']:.4f}
Wick/Body: {signal['wick_body_ratio']:.2f}x
Body/Range: {signal['body_ratio']:.2f}
Close Position: {signal['close_position']:.2f}

<b>Score:</b> {signal['score']:.1f} (informational only)

<b>LW-001: PASS</b>
<b>Qualification:</b> Lower Wick / Body >= 2.0x ({signal['wick_body_ratio']:.2f}x >= 2.0x)
"""
            
            notification = CustomNotification(
                subject=subject,
                body=body.strip(),
                format="html"
            )
            
            result = await service.send(notification)
            print(f"Sent signal #{i}: {result.is_success}")
        
        print()
        print(f"Successfully sent {len(signals)} signals to Telegram")
        
    except Exception as e:
        print(f"Error sending to Telegram: {e}")
    finally:
        await service.disconnect()

async def main():
    """Main function."""
    signals = await find_historical_signals()
    
    # Verify we have exactly 10 unique symbols
    if signals:
        unique_symbols = set(s['symbol'] for s in signals)
        print("=" * 80)
        print("VERIFICATION")
        print("=" * 80)
        print(f"Total signals: {len(signals)}")
        print(f"Unique symbols: {len(unique_symbols)}")
        print(f"Symbols: {list(unique_symbols)}")
        
        if len(signals) != TARGET_SIGNALS:
            print(f"ERROR: Expected {TARGET_SIGNALS} signals, got {len(signals)}")
            return
        
        if len(unique_symbols) != TARGET_SIGNALS:
            print(f"ERROR: Expected {TARGET_SIGNALS} unique symbols, got {len(unique_symbols)}")
            return
        
        print("VERIFICATION PASSED: 10 signals on 10 unique symbols")
        print()
        
        # Send to Telegram
        print("Sending to Telegram...")
        await send_to_telegram(signals)
    
    print()
    print("=" * 80)
    print("Done")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
á *cascade08áΩ*cascade08Ω≥ *cascade08≥Ω*cascade08Ω˜ *cascade08˜¯*cascade08¯˘ *cascade08˘˙*cascade08˙¿ *cascade08¿È*cascade08È» *cascade08»◊*cascade08◊ü *cascade08ü¨*cascade08¨ê *cascade08ê÷*cascade08÷Ö *cascade08Ö˙*cascade08˙…% *cascade08…% %*cascade08 %À% *cascade08À%œ%*cascade08œ%–% *cascade08–%’%*cascade08’%÷% *cascade08÷%Ÿ%*cascade08Ÿ%€% *cascade08€%›%*cascade08›%ﬂ% *cascade08ﬂ%‡%*cascade08‡%·% *cascade08·%„%*cascade08„%‰% *cascade08‰%Ê%*cascade08Ê%Ë% *cascade08Ë%Î%*cascade08Î%Ï% *cascade08Ï%%*cascade08%Ò% *cascade08Ò%¯%*cascade08¯%Å& *cascade08Å&É&*cascade08É&Ñ& *cascade08Ñ&Ö&*cascade08Ö&Ü& *cascade08Ü&à&*cascade08à&â& *cascade08â&ã&*cascade08ã&å& *cascade08å&è&*cascade08è&ë& *cascade08ë&í&*cascade08í&—1 *cascade08—1“1*cascade08“1”1 *cascade08”1‘1*cascade08‘1ä6 *cascade08ä6ƒ<*cascade08ƒ<¯? *cascade08¯?Ê@*cascade08Ê@ïB *cascade08ïBôB*cascade08ôBµB *cascade08µB˛B*cascade08˛BèI *cascade08èI¿I*cascade08¿I I *cascade08 IÕI*cascade08ÕI˘I *cascade08˘I˝I*cascade08˝IˇI *cascade08ˇIòJ*cascade08òJôJ *cascade08ôJπJ*cascade08πJ€J *cascade08€JÕK*cascade08ÕK‡K *cascade08‡K®L*cascade08®L‘L *cascade08‘LÂL*cascade08ÂLÊL *cascade08ÊLÙL*cascade08ÙLÜM *cascade08ÜM˛N*cascade08˛N◊O *cascade08◊O˛O*cascade08˛OâR *cascade08âRçR*cascade08çRêR *cascade08êRßR*cascade08ßRÓW *cascade08ÓWˆW*cascade08ˆW¯W *cascade08¯WåX*cascade08åXéX *cascade08éX«Y *cascade08«Y»Y *cascade08»Y“Y *cascade08“Y”Y*cascade08”Y‘Y *cascade08‘Y’Y *cascade08’Y÷Y*cascade08÷Y◊Y *cascade08◊YÿY*cascade08ÿYŸY *cascade08ŸY€Y*cascade08€YﬁY *cascade08ﬁY‡Y*cascade08‡Y·Y*cascade08·Y‚Y*cascade08‚Y„Y *cascade08„YÁY*cascade08ÁYËY *cascade08ËYÍY*cascade08ÍYÎY *cascade08ÎYÓY*cascade08ÓYÔY *cascade08ÔYıY*cascade08ıYˆY *cascade08ˆY˙Y*cascade08˙Y˚Y *cascade08˚YˇY*cascade08ˇYêZ *cascade08êZìZ*cascade08ìZîZ *cascade08îZòZ*cascade08òZ›[ *cascade08›[à\*cascade08à\î\ *cascade08î\≈\*cascade08≈\–\ *cascade08–\“\*cascade08“\”\ *cascade08”\‡\*cascade08‡\·\ *cascade08·\˝\*cascade08˝\ˇ\ *cascade08ˇ\Å]*cascade08Å]Ç] *cascade08Ç]à]*cascade08à]â] *cascade08â]ì]*cascade08ì]î] *cascade08î]ó]*cascade08ó]¢] *cascade08¢]ê^*cascade08ê^Øb *cascade08Øb≥b*cascade08≥b∂b *cascade08∂bÕb*cascade08Õb≠f *cascade08≠fùg*cascade08ùgÀg *cascade08Àg–g*cascade08–g—g *cascade08—g£h *cascade08£h£h*cascade08£h¿i *cascade08¿i√i*cascade08√iñl *cascade08ñl≈l*cascade08≈lÿl *cascade08ÿlØr *cascade08Ør∞r*cascade08∞rœr *cascade08œr–r*cascade08–r—r *cascade08—r“r*cascade08“r”r *cascade08”r‘r*cascade08‘r’r *cascade08’r÷r*cascade08÷r„r *cascade08„r‰r*cascade08‰rÔr *cascade08Ôrãt *cascade08ãtèt *cascade082Vfile:///C:/Users/user/Documents/Default%20Project/EVRECONSE/find_historical_signals.py