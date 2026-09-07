ß]"""
Diagnostic Script for LW-001 Signal Detection

This script diagnoses the signal detection process WITHOUT sending to Telegram.
It outputs the first 20 candidates with full calculation details.
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
MAX_DIAGNOSTIC_CANDIDATES = 20  # Only show first 20 candidates

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

async def diagnose_signals():
    """Diagnose signal detection - show first 20 candidates with full calculation."""
    print("=" * 80)
    print("LW-001 DIAGNOSTIC MODE")
    print("=" * 80)
    print(f"Wick/Body Ratio Threshold: {WICK_BODY_RATIO_THRESHOLD}x")
    print(f"Max Candidates to Show: {MAX_DIAGNOSTIC_CANDIDATES}")
    print("=" * 80)
    print()
    
    # Load symbols
    symbols = load_symbols()
    if not symbols:
        print("No symbols loaded. Exiting.")
        return
    
    print(f"Loaded {len(symbols)} symbols")
    print(f"First 10 symbols: {symbols[:10]}")
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
    candidates = []
    processed_symbols = set()
    
    # Search period: last 30 days
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=30)
    
    print(f"Searching period: {start_date} to {end_date}")
    print()
    
    for symbol in symbols:
        if len(candidates) >= MAX_DIAGNOSTIC_CANDIDATES:
            break
        
        # CRITICAL: Skip if we already have a candidate for this symbol
        if symbol in processed_symbols:
            print(f"  Skipping {symbol} (already have candidate)")
            continue
        
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
        
        # Process each candle
        for kline in klines:
            if len(candidates) >= MAX_DIAGNOSTIC_CANDIDATES:
                break
            
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
                        body_pct=body_size / candle_range if candle_range > 0 else 0,
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
                        msk_dt = to_msk(dt)
                        
                        candidate = {
                            "symbol": symbol,
                            "date": dt.strftime("%Y-%m-%d"),
                            "time_utc": dt.strftime("%H:%M:%S UTC"),
                            "time_msk": msk_dt.strftime("%H:%M:%S MSK"),
                            "open": open_p,
                            "high": high_p,
                            "low": low_p,
                            "close": close_p,
                            "body": body_size,
                            "lower_wick": lower_wick,
                            "upper_wick": upper_wick,
                            "wick_body_ratio": wick_body_ratio,
                            "is_red": close_p < open_p,
                            "score": result.final_score,
                            "qualified": result.qualified
                        }
                        candidates.append(candidate)
                        processed_symbols.add(symbol)
                        print(f"  [+] CANDIDATE #{len(candidates)}: {symbol} at {msk_dt.strftime('%H:%M:%S MSK')}, wick/body={wick_body_ratio:.2f}x")
                        print(f"  [->] Moving to next symbol (processed_symbols now has {len(processed_symbols)} symbols)")
                        break  # Take only first candidate for this symbol
                except Exception as e:
                    print(f"  Error evaluating: {e}")
        
        # CRITICAL: Check if we have enough candidates after processing this symbol
        if len(candidates) >= MAX_DIAGNOSTIC_CANDIDATES:
            print(f"  [STOP] Reached target of {MAX_DIAGNOSTIC_CANDIDATES} candidates, stopping search")
            break
        
        print()
    
    print("=" * 80)
    print(f"FOUND {len(candidates)} CANDIDATES")
    print(f"Unique symbols: {len(set(c['symbol'] for c in candidates))}")
    print("=" * 80)
    print()
    
    # Print detailed diagnostic output for each candidate
    for i, cand in enumerate(candidates, 1):
        print("=" * 80)
        print(f"CANDIDATE #{i}")
        print("=" * 80)
        print(f"Symbol: {cand['symbol']}")
        print(f"Time: {cand['time_msk']}")
        print()
        print(f"Open:  {cand['open']:.6f}")
        print(f"High:  {cand['high']:.6f}")
        print(f"Low:   {cand['low']:.6f}")
        print(f"Close: {cand['close']:.6f}")
        print()
        print(f"RED: {'YES' if cand['is_red'] else 'NO'}")
        print()
        print(f"Body: {cand['body']:.6f}")
        print(f"Lower Wick: {cand['lower_wick']:.6f}")
        print(f"Upper Wick: {cand['upper_wick']:.6f}")
        print()
        print(f"Lower Wick / Body: {cand['wick_body_ratio']:.2f}x")
        print()
        print(f"Qualified: {'YES' if cand['qualified'] else 'NO'}")
        print()
        print("=" * 80)
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total candidates found: {len(candidates)}")
    print(f"Unique symbols: {len(set(c['symbol'] for c in candidates))}")
    print()
    
    # Verify all candidates actually meet threshold
    print("VERIFICATION:")
    all_valid = all(c['wick_body_ratio'] >= WICK_BODY_RATIO_THRESHOLD for c in candidates)
    print(f"  All candidates meet threshold: {all_valid}")
    for c in candidates:
        status = "PASS" if c['wick_body_ratio'] >= WICK_BODY_RATIO_THRESHOLD else "FAIL"
        print(f"  {c['symbol']}: {c['wick_body_ratio']:.2f}x - {status}")
    print()
    
    return candidates

async def main():
    """Main function."""
    await diagnose_signals()
    print("=" * 80)
    print("DIAGNOSTIC COMPLETE - NO TELEGRAM MESSAGES SENT")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
• *cascade08•Ì*cascade08Ìå  *cascade08å œ *cascade08œ ÿE *cascade08ÿEêF*cascade08êFçH *cascade08çHêH*cascade08êHôI *cascade08ôI£I *cascade08£IßI*cascade08ßIïJ *cascade08ïJ–J *cascade08–J≠K*cascade08≠K—L *cascade08—L◊L*cascade08◊LµM *cascade08µM˚P *cascade08˚P¬W*cascade08¬Wß] *cascade082Ofile:///C:/Users/user/Documents/Default%20Project/EVRECONSE/diagnose_signals.py