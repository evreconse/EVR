ß{"""
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
- *cascade08-0*cascade0802 *cascade0824*cascade0845 *cascade0857*cascade0878 *cascade0889*cascade089: *cascade08:<*cascade08<= *cascade08=G*cascade08GJ *cascade08JK*cascade08KL *cascade08LO*cascade08OP *cascade08PR*cascade08RV *cascade08VW*cascade08WY *cascade08Y]*cascade08]^ *cascade08^`*cascade08`a *cascade08ad*cascade08dg *cascade08gh*cascade08hi *cascade08iu*cascade08u… *cascade08… *cascade08*cascade08¦ *cascade08¦» *cascade08»Ð*cascade08Ð¡ *cascade08¡·*cascade08·¾ *cascade08¾À*cascade08ÀÁ *cascade08ÁÆ*cascade08ÆÈ *cascade08ÈÌ*cascade08ÌÍ *cascade08ÍÖ*cascade08ÖØ *cascade08ØÚ*cascade08ÚÜ *cascade08ÜÞ*cascade08Þß *cascade08ßä*cascade08äå *cascade08åí*cascade08íî *cascade08îï*cascade08ïð *cascade08ðú*cascade08úû *cascade08ûý*cascade08ýÿ *cascade08ÿ…*cascade08…† *cascade08†‹*cascade08‹Œ *cascade08Œ”*cascade08”• *cascade08•™*cascade08™š *cascade08š *cascade08 ¡ *cascade08¡§*cascade08§¨ *cascade08¨®*cascade08®¯ *cascade08¯³*cascade08³´ *cascade08´¸*cascade08¸¹ *cascade08¹Å*cascade08ÅÆ *cascade08ÆÌ*cascade08ÌÎ *cascade08ÎÕ*cascade08ÕØ *cascade08Øà*cascade08àá *cascade08áå*cascade08åæ *cascade08æõ*cascade08õö *cascade08öü*cascade08üý *cascade08ýþ*cascade08þÿ *cascade08ÿ‚*cascade08‚ƒ *cascade08ƒŠ*cascade08Š‹ *cascade08‹*cascade08 *cascade08 *cascade08 ¡ *cascade08¡§*cascade08§© *cascade08©¶*cascade08¶¹ *cascade08¹Ç*cascade08ÇÈ *cascade08Èø*cascade08øù *cascade08ùˆ*cascade08ˆ˜ *cascade08˜™*cascade08™Ï *cascade08ÏÖ*cascade08ÖØ *cascade08ØÞ*cascade08Þß *cascade08ßà*cascade08àá *cascade08áã*cascade08ãå *cascade08åò*cascade08òó *cascade08óõ*cascade08õø *cascade08øû*cascade08û *cascade08‚*cascade08‚… *cascade08…†*cascade08†‹ *cascade08‹–*cascade08–— *cascade08—ž*cascade08žŸ *cascade08Ÿ *cascade08 ¡ *cascade08¡¢*cascade08¢£ *cascade08£ª *cascade08ª«*cascade08«® *cascade08®²*cascade08²³ *cascade08³¾*cascade08¾¿ *cascade08¿Å*cascade08ÅÆ *cascade08ÆÊ*cascade08ÊË *cascade08ËÛ*cascade08ÛÜ *cascade08ÜÝ*cascade08ÝÞ *cascade08Þâ*cascade08âã *cascade08ãä*cascade08äæ *cascade08æè*cascade08èé *cascade08éñ*cascade08ñó *cascade08ó*cascade08‚ *cascade08‚Ž*cascade08Ž *cascade08”*cascade08”• *cascade08•—*cascade08—› *cascade08›²*cascade08²³ *cascade08³´*cascade08´¸ *cascade08¸¹*cascade08¹¼ *cascade08¼Á*cascade08ÁÂ *cascade08ÂÉ*cascade08ÉÊ *cascade08ÊÙ*cascade08ÙÜ *cascade08ÜÝ*cascade08Ýà *cascade08àæ*cascade08æç *cascade08çì*cascade08ìñ *cascade08ñˆ*cascade08ˆ *cascade08Ž*cascade08Ž *cascade08–*cascade08–— *cascade08—›*cascade08›œ *cascade08œŸ*cascade08Ÿ  *cascade08 ²*cascade08²³ *cascade08³´*cascade08´µ *cascade08µ¸*cascade08¸¹ *cascade08¹¼*cascade08¼½ *cascade08½À*cascade08ÀÁ *cascade08ÁÊ*cascade08ÊË *cascade08ËÌ*cascade08ÌÍ *cascade08ÍÙ*cascade08ÙÚ *cascade08ÚÜ*cascade08ÜÝ *cascade08Ýß*cascade08ßà *cascade08àë*cascade08ëí *cascade08íñ*cascade08ñó *cascade08óû*cascade08ûý *cascade08ý„	*cascade08„	…	 *cascade08…	”	*cascade08”	•	 *cascade08•	˜	*cascade08˜	™	 *cascade08™	£	*cascade08£	¤	 *cascade08¤	¦	*cascade08¦	§	 *cascade08§	©	*cascade08©	«	 *cascade08«	µ	*cascade08µ	·	 *cascade08·	¼	*cascade08¼	½	 *cascade08½	¾	*cascade08¾	¿	 *cascade08¿	Å	*cascade08Å	Ç	 *cascade08Ç	Î	*cascade08Î	Ï	 *cascade08Ï	Ú	*cascade08Ú	Û	 *cascade08Û	ß	*cascade08ß	è	 *cascade08è	ì	*cascade08ì	í	 *cascade08í	ò	*cascade08ò	ó	 *cascade08ó	õ	*cascade08õ	ö	 *cascade08ö	÷	*cascade08÷	ù	 *cascade08ù	ú	*cascade08ú	û	 *cascade08û	ü	*cascade08ü	ý	 *cascade08ý	þ	*cascade08þ	ÿ	 *cascade08ÿ	‚
*cascade08‚
ƒ
 *cascade08ƒ
‘
*cascade08‘
“
 *cascade08“
”
*cascade08”
–
 *cascade08–
š
*cascade08š
›
 *cascade08›
œ
*cascade08œ
ž
 *cascade08ž
¢
*cascade08¢
£
 *cascade08£
§
*cascade08§
¨
 *cascade08¨
­
*cascade08­
®
 *cascade08®
¯
*cascade08¯
°
 *cascade08°
²
*cascade08²
»
 *cascade08»
¿
*cascade08¿
Á
 *cascade08Á
Ã
*cascade08Ã
Ä
 *cascade08Ä
Ç
*cascade08Ç
É
 *cascade08É
Ë
*cascade08Ë
Ì
 *cascade08Ì
Ô
*cascade08Ô
Õ
 *cascade08Õ
æ
*cascade08æ
ç
 *cascade08ç
è
*cascade08è
é
 *cascade08é
ì
 *cascade08ì
ì
*cascade08ì
ó
 *cascade08ó
² *cascade08²Ž *cascade08Ž‘*cascade08‘ì *cascade08ìÙ*cascade08Ùš *cascade08š¼*cascade08¼Ì *cascade08ÌÍ*cascade08Íò *cascade08òú*cascade08ú¢ *cascade08¢£*cascade08£­ *cascade08­³*cascade08³» *cascade08»Ý*cascade08Ýé *cascade08éò*cascade08òÏ *cascade08ÏÐ*cascade08ÐÑ *cascade08ÑÒ*cascade08ÒÔ *cascade08ÔØ*cascade08ØÙ *cascade08ÙÞ*cascade08Þß *cascade08ßé*cascade08éê *cascade08êì *cascade08ìñ*cascade08ñó *cascade08óô*cascade08ô÷ *cascade08÷ø *cascade08øþ*cascade08þÿ*cascade08ÿ€ *cascade08€*cascade08… *cascade08…‹*cascade08‹ *cascade08Ž*cascade08Ž‘ *cascade08‘—*cascade08—™ *cascade08™š*cascade08šž *cascade08žŸ *cascade08Ÿ¥*cascade08¥§*cascade08§¨*cascade08¨© *cascade08©­*cascade08­® *cascade08®¹*cascade08¹º *cascade08º¿*cascade08¿À *cascade08ÀÂ*cascade08ÂÃ *cascade08ÃÄ*cascade08ÄÅ *cascade08ÅÌ*cascade08ÌÍ *cascade08ÍÕ*cascade08ÕÚ *cascade08Úì*cascade08ìï *cascade08ï÷*cascade08÷ø *cascade08ø‰*cascade08‰Ž *cascade08Ž*cascade08 *cascade08¥*cascade08¥§ *cascade08§æ*cascade08æç *cascade08çè *cascade08èë*cascade08ëì *cascade08ìô*cascade08ôõ *cascade08õ’*cascade08’“ *cascade08“*cascade08¢ *cascade08¢¼*cascade08¼½ *cascade08½¾*cascade08¾À *cascade08ÀÄ*cascade08Ä÷ *cascade08÷û*cascade08û *cascade08‘*cascade08‘” *cascade08”˜*cascade08˜´ *cascade08´µ*cascade08µ™$ *cascade08™$¡$*cascade08¡$€% *cascade08€%€%*cascade08€%Ú( *cascade08Ú(Ð**cascade08Ð*Ü* *cascade08Ü*ß**cascade08ß*ç* *cascade08ç*+*cascade08+ú+ *cascade08ú+Ü,*cascade08Ü,Þ, *cascade08Þ,á,*cascade08á,â, *cascade08â,ã,*cascade08ã,å, *cascade08å,æ, *cascade08æ,ç, *cascade08ç,è, *cascade08è,ê, *cascade08ê,ë,*cascade08ë,ì, *cascade08ì,ð,*cascade08ð,ñ, *cascade08ñ,ò,*cascade08ò,ó, *cascade08ó,ô,*cascade08ô,õ, *cascade08õ,ö, *cascade08ö,ù,*cascade08ù,ú, *cascade08ú,û,*cascade08û,ü, *cascade08ü,ý, *cascade08ý,þ, *cascade08þ,„-*cascade08„-†- *cascade08†-‡- *cascade08‡-Š-*cascade08Š-‹- *cascade08‹-- *cascade08-Ž-*cascade08Ž-- *cascade08-“-*cascade08“-”- *cascade08”-–-*cascade08–-˜- *cascade08˜-™-*cascade08™-š- *cascade08š-›- *cascade08›-œ- *cascade08œ- -*cascade08 -¡- *cascade08¡-¢-*cascade08¢-£- *cascade08£-¥-*cascade08¥-¨- *cascade08¨-©-*cascade08©-ª- *cascade08ª-¬-*cascade08¬-­- *cascade08­-®- *cascade08®-¯- *cascade08¯-´-*cascade08´-µ- *cascade08µ-¶-*cascade08¶-·- *cascade08·-¼-*cascade08¼-¾- *cascade08¾-¿-*cascade08¿-À- *cascade08À-Å-*cascade08Å-Æ- *cascade08Æ-Ê-*cascade08Ê-Ë- *cascade08Ë-Ð-*cascade08Ð-Ñ- *cascade08Ñ-Ò- *cascade08Ò-Ó-*cascade08Ó-Ô- *cascade08Ô-Õ- *cascade08Õ-×-*cascade08×-à- *cascade08à-è- *cascade08è-é- *cascade08é-ê-*cascade08ê-ë- *cascade08ë-ì-*cascade08ì-í- *cascade08í-ï-*cascade08ï-ð- *cascade08ð-‹.*cascade08‹.. *cascade08.®.*cascade08®.Å. *cascade08Å.Æ.*cascade08Æ.Ð. *cascade08Ð.Ö.*cascade08Ö.Þ. *cascade08Þ.ï. *cascade08ï.ð.*cascade08ð.ñ.*cascade08ñ.ó. *cascade08ó.ô.*cascade08ô./ *cascade08/•/ *cascade08•/ž/*cascade08ž/Ÿ/ *cascade08Ÿ/î/ *cascade08î/­0*cascade08­0Ã0 *cascade08Ã0–2 *cascade08–2¯2 *cascade08¯2¹2*cascade08¹2¼2 *cascade08¼2Á2*cascade08Á2Ã2 *cascade08Ã2Ä2*cascade08Ä2È2 *cascade08È2Î2*cascade08Î2Ð2 *cascade08Ð2Ñ2*cascade08Ñ2Õ2 *cascade08Õ2Û2*cascade08Û2Ý2 *cascade08Ý2Þ2*cascade08Þ2á2 *cascade08á2ç2*cascade08ç2é2 *cascade08é2ê2*cascade08ê2ï2 *cascade08ï2õ2*cascade08õ2÷2 *cascade08÷2ø2*cascade08ø2þ2 *cascade08þ2€3*cascade08€3‚3 *cascade08‚3…3*cascade08…3¹3 *cascade08¹3†4 *cascade08†4›4 *cascade08›4¨4*cascade08¨4©4 *cascade08©4ª4*cascade08ª4´4 *cascade08´4·4*cascade08·4Ã4 *cascade08Ã4Ñ4*cascade08Ñ4Ò4 *cascade08Ò4ÿ4*cascade08ÿ4‚5 *cascade08‚5…5*cascade08…5‡5 *cascade08‡55*cascade085‘5 *cascade08‘5”5*cascade08”5•5 *cascade08•5À5*cascade08À5Â5 *cascade08Â5ë5*cascade08ë5ì5 *cascade08ì5í5*cascade08í5î5 *cascade08î5ï5*cascade08ï5ð5 *cascade08ð5ó5*cascade08ó5ô5 *cascade08ô5õ5*cascade08õ5ö5 *cascade08ö5ù5*cascade08ù5û5 *cascade08û5¥6*cascade08¥6¦6 *cascade08¦6©6*cascade08©6ª6 *cascade08ª6«6*cascade08«6¬6 *cascade08¬6¯6*cascade08¯6°6 *cascade08°6¶6*cascade08¶6·6 *cascade08·6¹6*cascade08¹6»6 *cascade08»6½6*cascade08½6Ë6 *cascade08Ë6Ð6*cascade08Ð6Ñ6 *cascade08Ñ6‡7*cascade08‡7¬7 *cascade08¬7¯7*cascade08¯7»7 *cascade08»7¼7*cascade08¼7á7 *cascade08á7å7*cascade08å7ý7 *cascade08ý7€8*cascade08€8Œ8 *cascade08Œ88*cascade088³8 *cascade08³8·8*cascade08·8Î8 *cascade08Î8–9*cascade08–9³9 *cascade08³9µ: *cascade08µ:¸:*cascade08¸:ðS *cascade08ðSËT*cascade08ËTôT *cascade08ôTõT*cascade08õTöT *cascade08öTøT*cascade08øTùT *cascade08ùT‚U*cascade08‚U„U *cascade08„UŒU*cascade08ŒUU *cascade08UŽU*cascade08ŽU•U *cascade08•U—U *cascade08—U¨U*cascade08¨U¯U *cascade08¯U°U *cascade08°UÇU *cascade08ÇUÉU*cascade08ÉUÏU *cascade08ÏUÒU *cascade08ÒUÓU*cascade08ÓUÕU *cascade08ÕU×U*cascade08×UŠV *cascade08ŠV£V *cascade08£V¥V *cascade08¥V¨V*cascade08¨V©V *cascade08©VªV *cascade08ªV±V*cascade08±VµV *cascade08µV·V *cascade08·V»V*cascade08»V¾V *cascade08¾VÆV*cascade08ÆVÍ] *cascade08Í]Î]*cascade08Î]Ìn *cascade08ÌnÏn *cascade08Ïnör *cascade08ör˜s *cascade08˜s­s*cascade08­s®s *cascade08®s°s*cascade08°s±s *cascade08±s²s*cascade08²s³s *cascade08³sÇs*cascade08ÇsÈs *cascade08ÈsÌs*cascade08ÌsÍs *cascade08ÍsÛs*cascade08ÛsÜs *cascade08ÜsÞs*cascade08Þsßs *cascade08ßsäs*cascade08äsås *cascade08ås€t*cascade08€tt *cascade08t”t*cascade08”t–t *cascade08–t¬t*cascade08¬t®t *cascade08®t¯t*cascade08¯t°t *cascade08°tµt*cascade08µt¶t *cascade08¶tËt*cascade08ËtÌt *cascade08ÌtÐt*cascade08ÐtÑt *cascade08ÑtÕt*cascade08Õt×t *cascade08×tæt*cascade08ætèt *cascade08ètõu*cascade08õuöu *cascade08öu›v*cascade08›vœv *cascade08œvÔv*cascade08ÔvÕv *cascade08Õv’w*cascade08’w“w *cascade08“w”w*cascade08”w•w *cascade08•w­w*cascade08­w®w *cascade08®w·w*cascade08·w¸w *cascade08¸w¹w*cascade08¹wºw *cascade08ºw¾w*cascade08¾w¿w *cascade08¿wðw*cascade08ðwñw *cascade08ñw÷w*cascade08÷wùw *cascade08ùw„x*cascade08„x†x *cascade08†x™x*cascade08™xšx *cascade08šx¨x*cascade08¨x©x *cascade08©xÁx*cascade08ÁxÂx *cascade08ÂxÈx*cascade08ÈxÉx *cascade08ÉxÌx*cascade08ÌxÎx *cascade08ÎxÔx*cascade08ÔxÕx *cascade08ÕxØx*cascade08Øxßx *cascade08ßxàx*cascade08àxáx *cascade08áxãx*cascade08ãxäx *cascade08äx÷x*cascade08÷xøx *cascade08øxùx*cascade08ùxúx *cascade08úx—y*cascade08—y˜y *cascade08˜yœy*cascade08œyÌy *cascade08ÌyÍy*cascade08ÍyÐy *cascade08ÐyÑy*cascade08ÑyÖy *cascade08ÖyÜy *cascade08Üyßy*cascade08ßyìy *cascade08ìyðy*cascade08ðyñy *cascade08ñyòy*cascade08òyóy *cascade08óyôy*cascade08ôyöy *cascade08öy÷y*cascade08÷yøy *cascade08øyúy*cascade08úyüy *cascade08üyýy*cascade08ýyÿy *cascade08ÿyz*cascade08z„z *cascade08„z‘z *cascade08‘z•z*cascade08•z™z *cascade08™z§z*cascade08§z«z *cascade08«z­z *cascade08­z±z*cascade08±z¸z *cascade08¸z¹z*cascade08¹zºz *cascade08ºzÂz*cascade08ÂzÎz *cascade08ÎzÜ{ *cascade08Ü{ß{ *cascade082Rfile:///C:/Users/user/Documents/Default%20Project/EVRECONSE/historical_backtest.py