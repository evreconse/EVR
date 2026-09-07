"""
Historical Backtest for LW-001 Strategy

Uses production LW-001 class directly to ensure identical logic.
Fetches historical data from BingX and evaluates signals.
"""
import asyncio
import sys
import os
from datetime import UTC, datetime, timedelta
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
LIMIT = 1000  # Max candles per request

# Strategy configuration (matches config.yaml)
STRATEGY_CONFIG = {
    "lower_wick_ratio": 2.0,
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
}

def create_strategy_data(metrics: Dict) -> Dict:
    """Create strategy_data dict from candle metrics."""
    body = metrics["close"] - metrics["open"]
    body_size = abs(body)
    lower_wick = min(metrics["open"], metrics["close"]) - metrics["low"]
    candle_range = metrics["high"] - metrics["low"]
    
    return {
        "lower_wick": lower_wick,
        "body": body_size,
        "wick_body_ratio": lower_wick / body_size if body_size > 0 else 0.0,
        "lower_wick_pct": lower_wick / candle_range if candle_range > 0 else 0.0,
        "body_pct": body_size / candle_range if candle_range > 0 else 0.0,
        "confirm": True,  # Historical candles are always confirmed/closed
    }

async def evaluate_signal_outcome(symbol: str, signal_close: float, signal_timestamp: int, fetcher: BingXFetcher, max_hours: int = 24) -> Dict[str, Any]:
    """
    Evaluate if signal resulted in +3% growth within max_hours.
    
    Fetches future candles and checks if price reached +3% above signal close.
    """
    # Convert symbol to BingX format (USDT -> -USDT)
    bingx_symbol = symbol.replace("USDT", "-USDT")
    
    # Fetch candles after signal time
    start_time = signal_timestamp * 1000  # BingX uses milliseconds
    end_time = (signal_timestamp + (max_hours * 3600)) * 1000
    
    future_klines = await fetcher.get_klines(bingx_symbol, TIMEFRAME, limit=1000, start_time=start_time, end_time=end_time)
    
    if not future_klines:
        return {
            "status": "NO_DATA",
            "max_growth_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "hours_elapsed": 0,
        }
    
    target_price = signal_close * 1.03  # +3% target
    max_high = signal_close
    max_low = signal_close
    hours_elapsed = 0
    
    # BingX returns dicts: {'time': ms, 'open': str, 'high': str, 'low': str, 'close': str, 'volume': str}
    for kline in future_klines:
        # Handle dict format
        if isinstance(kline, dict):
            kline_time = int(kline.get("time", 0)) // 1000
            high_p = float(kline.get("high", 0))
            low_p = float(kline.get("low", 0))
        else:
            kline_time = int(kline[0]) // 1000
            high_p = float(kline[3])
            low_p = float(kline[4])
        
        max_high = max(max_high, high_p)
        max_low = min(max_low, low_p)
        hours_elapsed = (kline_time - signal_timestamp) / 3600
        
        if high_p >= target_price:
            return {
                "status": "PASS",
                "max_growth_pct": ((max_high - signal_close) / signal_close) * 100,
                "max_drawdown_pct": ((max_low - signal_close) / signal_close) * 100,
                "hours_elapsed": hours_elapsed,
            }
    
    # No +3% reached within timeframe
    return {
        "status": "FAIL",
        "max_growth_pct": ((max_high - signal_close) / signal_close) * 100,
        "max_drawdown_pct": ((max_low - signal_close) / signal_close) * 100,
        "hours_elapsed": hours_elapsed,
    }

async def run_backtest(symbols: List[str], start_date: datetime, end_date: datetime):
    """Run historical backtest using production LW-001 class."""
    print("=" * 80)
    print("LW-001 Historical Backtest (Production Strategy) - BingX")
    print("=" * 80)
    print(f"Symbols: {len(symbols)}")
    print(f"Timeframe: {TIMEFRAME}")
    print(f"Period: {start_date} to {end_date}")
    print(f"Min Confidence Score: {STRATEGY_CONFIG['min_confidence_score']}")
    print(f"Target Growth: +3%")
    print("=" * 80)
    print()
    
    # Initialize production strategy
    strategy = LW001Strategy()
    strategy_config = StrategyConfig(
        parameters=STRATEGY_CONFIG,
        enabled=True,
        strategy_id="LW-001",
        version="1.0.0"
    )
    strategy.initialize(strategy_config)
    
    # Initialize BingX fetcher with API keys
    api_key = "LY4rJlgmbxIhuniKUTibI16IhHnu937kDdPLOBfbo7BnfjHR3g6e3dUXTWBOj4NT4ZV7l4BRUed9ryYOnFFQ"
    api_secret = "q9DmZfQGGFjqN2yC8VGXVVEw5Ecws2mSmYOHGEEXTKWKIjgcafyrvcQrhKg4YAlBrj8rWaUUVxLiaOjA"
    fetcher = BingXFetcher(api_key=api_key, api_secret=api_secret)
    signals = []
    
    for symbol in symbols:
        print(f"Processing {symbol}...")
        
        # Convert to BingX format
        bingx_symbol = symbol.replace("USDT", "-USDT")
        
        # Use date range for historical analysis
        start_time = int(start_date.timestamp() * 1000)  # BingX uses milliseconds
        end_time = int(end_date.timestamp() * 1000)
        
        try:
            klines = await fetcher.get_klines(bingx_symbol, TIMEFRAME, limit=50000, start_time=start_time, end_time=end_time)
        except Exception as e:
            print(f"  Error fetching data: {e}")
            import traceback
            traceback.print_exc()
            continue
        
        if not klines:
            print(f"  No data for {symbol}")
            continue
        
        print(f"  Fetched {len(klines)} candles")
        
        # Process each candle (oldest first)
        # BingX returns dicts: {'time': ms, 'open': str, 'high': str, 'low': str, 'close': str, 'volume': str}
        for kline in reversed(klines):
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
                volume=volume,
            )
            
            # Calculate candle metrics
            metrics = {
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "volume": volume,
            }
            strategy_data_dict = create_strategy_data(metrics)
            
            # Create StrategyData object
            from models.market_event import StrategyData
            strategy_data = StrategyData(
                strategy_id="LW-001",
                **strategy_data_dict
            )
            
            # Update market_event with strategy_data
            from dataclasses import replace
            market_event = replace(market_event, strategy_data=strategy_data)
            
            # Create StrategyContext
            class MockDataProvider:
                async def get_snapshot(self, symbol, timeframe, limit):
                    return []
                async def get_liquidations(self, symbol, limit):
                    return []
            
            class MockStorage:
                async def save_event(self, event):
                    pass
                async def get_events(self, symbol, start, end):
                    return []
            
            context = StrategyContext(
                market_event=market_event,
                config=strategy_config,
                data_provider=MockDataProvider(),
                storage=MockStorage(),
            )
            
            # Evaluate using production strategy
            try:
                result = await strategy.evaluate(context)
                
                if result.qualified:
                    body = close_p - open_p
                    body_size = abs(body)
                    lower_wick = min(open_p, close_p) - low_p
                    upper_wick = high_p - max(open_p, close_p)
                    candle_range = high_p - low_p
                    close_position = (close_p - low_p) / candle_range if candle_range > 0 else 0.0
                    
                    signal = {
                        "symbol": symbol,
                        "timestamp": timestamp,
                        "datetime": dt,
                        "open": open_p,
                        "high": high_p,
                        "low": low_p,
                        "close": close_p,
                        "volume": volume,
                        "body": body_size,
                        "lower_wick": lower_wick,
                        "upper_wick": upper_wick,
                        "wick_body_ratio": lower_wick / body_size if body_size > 0 else 0.0,
                        "body_ratio": body_size / candle_range if candle_range > 0 else 0.0,
                        "close_position": close_position,
                        "final_score": result.final_score,
                        "explanation": result.explanation,
                    }
                    signals.append(signal)
                    print(f"  SIGNAL FOUND: {symbol} at {dt}, score={result.final_score}")
            except Exception as e:
                # Debug: show why candle was rejected for first symbol
                if symbol == "0GUSDT" and len([s for s in signals if s['symbol'] == symbol]) == 0:
                    print(f"  First candle rejected: {e}")
                pass
        
        print(f"  Found {len([s for s in signals if s['symbol'] == symbol])} signals")
        print()
    
    # Evaluate outcomes for all signals
    print("=" * 80)
    print("Evaluating signal outcomes (+3% target)...")
    print("=" * 80)
    print()
    
    for signal in signals:
        outcome = await evaluate_signal_outcome(
            signal["symbol"],
            signal["close"],
            signal["timestamp"],
            fetcher,
            max_hours=24
        )
        signal["outcome"] = outcome
    
    # Calculate statistics
    total_signals = len(signals)
    passed = [s for s in signals if s["outcome"]["status"] == "PASS"]
    failed = [s for s in signals if s["outcome"]["status"] == "FAIL"]
    no_data = [s for s in signals if s["outcome"]["status"] == "NO_DATA"]
    
    winrate = (len(passed) / total_signals * 100) if total_signals > 0 else 0
    
    if signals:
        avg_growth = sum(s["outcome"]["max_growth_pct"] for s in signals) / total_signals
        max_growth = max(s["outcome"]["max_growth_pct"] for s in signals)
        max_drawdown = min(s["outcome"]["max_drawdown_pct"] for s in signals)
    else:
        avg_growth = 0
        max_growth = 0
        max_drawdown = 0
    
    # Output results
    print("=" * 80)
    print(f"TOTAL SIGNALS FOUND: {total_signals}")
    print("=" * 80)
    print(f"PASS (+3% reached): {len(passed)}")
    print(f"FAIL (+3% not reached): {len(failed)}")
    print(f"NO DATA: {len(no_data)}")
    print(f"WINRATE: {winrate:.2f}%")
    print(f"AVG GROWTH: {avg_growth:.2f}%")
    print(f"MAX GROWTH: {max_growth:.2f}%")
    print(f"MAX DRAWDOWN: {max_drawdown:.2f}%")
    print("=" * 80)
    print()
    
    if signals:
        # Sort by timestamp
        signals.sort(key=lambda x: x["timestamp"])
        
        # Show first 10 signals with outcomes
        print("FIRST 10 SIGNALS WITH OUTCOMES:")
        print("=" * 80)
        for i, signal in enumerate(signals[:10], 1):
            print(f"\nSignal #{i}")
            print(f"  Symbol: {signal['symbol']}")
            print(f"  Date: {signal['datetime']}")
            print(f"  OHLC: O={signal['open']:.4f} H={signal['high']:.4f} L={signal['low']:.4f} C={signal['close']:.4f}")
            print(f"  Volume: {signal['volume']:.2f}")
            print(f"  Body: {signal['body']:.4f}")
            print(f"  Lower Wick: {signal['lower_wick']:.4f}")
            print(f"  Upper Wick: {signal['upper_wick']:.4f}")
            print(f"  Wick/Body Ratio: {signal['wick_body_ratio']:.2f}x")
            print(f"  Body/Range Ratio: {signal['body_ratio']:.2%}")
            print(f"  Close Position: {signal['close_position']:.2%}")
            print(f"  FINAL SCORE: {signal['final_score']:.1f}/100")
            print(f"  OUTCOME: {signal['outcome']['status']}")
            print(f"  Max Growth: {signal['outcome']['max_growth_pct']:.2f}%")
            print(f"  Max Drawdown: {signal['outcome']['max_drawdown_pct']:.2f}%")
            print(f"  Hours Elapsed: {signal['outcome']['hours_elapsed']:.1f}h")
            print("-" * 80)
        
        # Save to file
        import json
        with open("historical_signals.json", "w") as f:
            serializable_signals = []
            for s in signals:
                s_copy = s.copy()
                s_copy["datetime"] = s["datetime"].isoformat()
                serializable_signals.append(s_copy)
            json.dump(serializable_signals, f, indent=2)
        
        print(f"\nAll signals saved to: historical_signals.json")
    else:
        print("No signals found in the tested period.")

if __name__ == "__main__":
    # Load symbols from file if available, otherwise use placeholder
    try:
        with open("usdt_perpetual_symbols.py", "r") as f:
            content = f.read()
            # Extract symbols list from the file
            import re
            match = re.search(r'SYMBOLS = \[(.*?)\]', content, re.DOTALL)
            if match:
                symbols_str = match.group(1)
                SYMBOLS = [s.strip().strip('"').strip("'") for s in symbols_str.split(',') if s.strip()]
                print(f"Loaded {len(SYMBOLS)} symbols from usdt_perpetual_symbols.py")
            else:
                raise Exception("Could not parse symbols file")
    except Exception as e:
        print(f"Could not load symbols file: {e}")
        print("Using placeholder symbols")
        SYMBOLS = ["INJUSDT", "SEIUSDT", "PEPEUSDT"]
    
    # Use all symbols for full historical analysis
    print(f"Running full analysis with {len(SYMBOLS)} symbols")
    
    START_DATE = datetime(2025, 1, 1, tzinfo=UTC)
    END_DATE = datetime.now(UTC)
    
    asyncio.run(run_backtest(SYMBOLS, START_DATE, END_DATE))
