#!/usr/bin/env python3
"""
EVRECONSE Historical Validation Script - Alternative Data Source.

Validates LW-001 strategy on real historical data using alternative sources.
Finds 10 real signals from non-TOP20 symbols.

Uses Yahoo Finance (yfinance) as primary data source when Bybit is blocked.
Falls back to other public APIs if needed.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Try to import yfinance
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("WARNING: yfinance not installed. Install with: pip install yfinance")

from core import init_logging, LogLevel, LoggingConfig
from models.enums import Exchange, Timeframe, EventStatus
from application.bootstrap import bootstrap
from event_engine.event_pipeline import create_default_pipeline
from event_engine.context import EventContext
from models import MarketEvent
from models.enums import EventStatus
from models.identifiers import EventID
from models.market_event import MarketData, Metadata, StrategyData


# TOP-20 symbols to EXCLUDE
TOP20_SYMBOLS = {
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "TRXUSDT", "LINKUSDT",
    "DOTUSDT", "MATICUSDT", "ICPUSDT", "SHIBUSDT", "LTCUSDT",
    "BCHUSDT", "UNIUSDT", "ATOMUSDT", "ETCUSDT", "FILUSDT"
}

# Alternative symbols to test (non-TOP20, high volatility)
ALT_SYMBOLS = [
    "INJUSDT", "SEIUSDT", "TIAUSDT", "SUIUSDT", "WIFUSDT",
    "BONKUSDT", "PEPEUSDT", "FLOKIUSDT", "TURBOUSDT", "BRETTUSDT",
    "JASMYUSDT", "ARKMUSDT", "APTUSDT", "NOTUSDT", "WUSDT",
    "PYTHUSDT", "JTOUSDT", "DYDXUSDT", "OPUSDT", "ARBUSDT",
    "IMXUSDT", "BLURUSDT", "MAGICUSDT", "GALAUSDT", "SANDUSDT",
    "MANAUSDT", "AXSUSDT", "CHZUSDT", "ENJUSDT", "GMTUSDT",
]


def yahoo_to_bybit_symbol(symbol: str) -> str:
    """Convert Bybit symbol (e.g., INJUSDT) to Yahoo Finance format (e.g., INJ-USD)."""
    if symbol.endswith("USDT"):
        base = symbol[:-4]
        return f"{base}-USD"
    return symbol


async def get_historical_klines_yfinance(symbol: str, days_back: int = 30) -> list:
    """Get historical klines from Yahoo Finance."""
    if not YFINANCE_AVAILABLE:
        raise RuntimeError("yfinance not installed. Run: pip install yfinance")
    
    yf_symbol = yahoo_to_bybit_symbol(symbol)
    end_date = datetime.now(UTC)
    start_date = datetime.now(UTC) - timedelta(days=days_back)
    
    try:
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            interval="15m",  # 15-minute intervals
            auto_adjust=False,
        )
        
        if df.empty:
            return []
        
        # Convert to Bybit-style kline format
        # yfinance returns: Open, High, Low, Close, Volume
        # Bybit format: [startTime, openPrice, highPrice, lowPrice, closePrice, volume, turnover]
        klines = []
        for idx, row in df.iterrows():
            start_time = int(idx.timestamp() * 1000)
            klines.append([
                start_time,
                float(row['Open']),
                float(row['High']),
                float(row['Low']),
                float(row['Close']),
                float(row['Volume']),
                float(row['Close']) * float(row['Volume']),  # turnover approximation
            ])
        
        return klines
    except Exception as e:
        print(f"Error getting yfinance data for {symbol}: {e}")
        return []


async def get_historical_klines_bybit(data_provider, symbol: str, timeframe: str, days_back: int = 30) -> list:
    """Get historical klines from Bybit (original method)."""
    tf_map = {"15m": "15", "1m": "1", "5m": "5", "30m": "30", "1h": "60", "4h": "240", "1d": "D"}
    interval = tf_map.get(timeframe, "15")
    
    try:
        result = await data_provider._rest_client.get_klines(
            category="linear",
            symbol=symbol,
            interval=interval,
            limit=200,
        )
        klines = result.get("result", {}).get("list", [])
        return klines
    except Exception as e:
        print(f"Bybit error for {symbol}: {e}")
        return []


async def get_available_symbols(data_provider) -> list:
    """Get all available USDT perpetual symbols from Bybit."""
    try:
        result = await data_provider._rest_client._request(
            "GET", "/v5/market/tickers", {"category": "linear"}
        )
        symbols = []
        for ticker in result.get("result", {}).get("list", []):
            if ticker.get("symbol", "").endswith("USDT") and ticker.get("status") == "Trading":
                symbols.append(ticker["symbol"])
        return symbols
    except Exception as e:
        print(f"Error getting symbols from Bybit: {e}")
        # Fallback to predefined altcoins
        return [s for s in ALT_SYMBOLS if s not in TOP20_SYMBOLS]


async def run_strategy_on_klines(context, pipeline, symbol: str, klines: list) -> list:
    """Run LW-001 strategy on historical klines and return signals."""
    signals = []
    
    pipeline_obj = create_default_pipeline(
        strategy_engine=context.strategy_engine,
        scoring_engine=context.scoring_engine,
        notification_engine=context.notification_engine,
        outcome_tracker=context.outcome_tracker,
        storage_service=context.storage_engine,
    )
    
    # Process each closed candle (skip last one which might be forming)
    for i, kline in enumerate(klines[:-1]):
        try:
            # Parse kline data: [startTime, openPrice, highPrice, lowPrice, closePrice, volume, turnover]
            start_time = int(kline[0])
            open_price = float(kline[1])
            high_price = float(kline[2])
            low_price = float(kline[3])
            close_price = float(kline[4])
            volume = float(kline[5])
            
            event_time = datetime.fromtimestamp(start_time / 1000, tz=UTC)
            
            # Compute candle structure
            body = close_price - open_price
            body_size = abs(body)
            upper_wick = high_price - max(open_price, close_price)
            lower_wick = min(open_price, close_price) - low_price
            candle_range = high_price - low_price
            
            if body_size == 0:
                continue  # Skip doji candles
            
            wick_body_ratio = lower_wick / body_size if body_size > 0 else 0.0
            
            # Create event
            event_id = EventID._generate()
            event_time = datetime.fromtimestamp(start_time / 1000, tz=UTC)
            
            event = MarketEvent(
                schema_version=1,
                metadata=Metadata(
                    event_id=EventID._generate(),
                    status=EventStatus.NEW,
                    schema_version=1,
                    created_at=event_time,
                    updated_at=event_time,
                ),
                market_data=MarketData(
                    symbol=symbol,
                    exchange=Exchange.BYBIT,
                    timeframe=Timeframe.M15,
                    event_time=event_time,
                    open=open_price,
                    high=high_price,
                    low=low_price,
                    close=close_price,
                    volume=volume,
                ),
                strategy_data=StrategyData(
                    strategy_id="LW-001",
                    lower_wick=lower_wick,
                    body=body_size,
                    wick_body_ratio=wick_body_ratio,
                    lower_wick_pct=lower_wick / candle_range if candle_range > 0 else 0.0,
                    body_pct=body_size / candle_range if candle_range > 0 else 0.0,
                    liquidation_volume=0.0,  # Would need liquidation API
                    liquidation_reference_value=0.0,
                ),
            )
            
            # Create pipeline context
            pipeline_context = EventContext(
                event_id=event_id,
                event_type="market_event",
                status="new",
                created_at=event_time,
                updated_at=event_time,
                symbol=symbol,
                exchange="bybit",
                timeframe="15m",
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=volume,
                event_time=event_time,
                strategy_id="LW-001",
                lower_wick=lower_wick,
                body=body_size,
                wick_body_ratio=wick_body_ratio,
                liquidation_volume=0.0,
                liquidation_reference=0.0,
            )
            
            # Run through pipeline
            result = await pipeline.execute(pipeline_context)
            
            if result.final_context.confidence_score and result.final_context.confidence_score >= 80.0:
                signals.append({
                    "symbol": symbol,
                    "time": event_time,
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                    "volume": volume,
                    "lower_wick": lower_wick,
                    "body": body_size,
                    "wick_body_ratio": wick_body_ratio,
                    "score": result.final_context.confidence_score,
                    "status": "qualified",
                })
                print(f"  SIGNAL: {symbol} at {event_time} - Score: {result.final_context.confidence_score:.1f}")
                print(f"    O={open_price:.4f} H={high_price:.4f} L={low_price:.4f} C={close_price:.4f}")
                print(f"    Body={body_size:.4f}, LowerWick={lower_wick:.4f}, Ratio={wick_body_ratio:.2f}x")
                
        except Exception as e:
            print(f"  Error processing kline {i}: {e}")
            continue
    
    return signals


async def main():
    print("=" * 60)
    print("EVRECONSE HISTORICAL VALIDATION - LW-001")
    print("=" * 60)
    print("Using Yahoo Finance (yfinance) as primary data source")
    print("Falling back to Bybit if available")
    print()
    
    # Initialize logging
    from core import init_logging, LogLevel, LoggingConfig
    log_config = LoggingConfig(
        level=LogLevel.INFO,
        log_path=None,
        console_enabled=True,
        file_enabled=False,
        json_format=False,
    )
    init_logging(log_config)
    
    # Bootstrap application
    print("\n[1/4] BOOTSTRAPPING APPLICATION")
    from pathlib import Path
    from application.bootstrap import bootstrap
    context = await bootstrap(config_path=Path("config.yaml"))
    
    # Create pipeline with all engines
    print("\n[1.5/4] CREATING PIPELINE")
    pipeline = create_default_pipeline(
        strategy_engine=context.strategy_engine,
        scoring_engine=context.scoring_engine,
        notification_engine=context.notification_engine,
        outcome_tracker=context.outcome_tracker,
        storage_service=context.storage_engine,
    )
    
    # Get available symbols
    print("\n[2/4] GETTING AVAILABLE SYMBOLS")
    symbols = await get_available_symbols(context.data_provider)
    top20 = TOP20_SYMBOLS
    non_top20 = [s for s in symbols if s not in top20]
    print(f"  Total symbols: {len(symbols)}")
    print(f"  Non-TOP20 symbols: {len(non_top20)}")
    
    if len(non_top20) == 0:
        print("  WARNING: No non-TOP20 symbols from Bybit. Using predefined altcoin list.")
        non_top20 = [s for s in ALT_SYMBOLS if s not in TOP20_SYMBOLS]
        print(f"  Using predefined altcoins: {len(non_top20)} symbols")
    
    # Test a subset of symbols
    test_symbols = non_top20[:30]
    print(f"  Testing first {len(test_symbols)} non-TOP20 symbols...")
    
    # Get historical data and run strategy
    print("\n[3/4] RUNNING HISTORICAL VALIDATION")
    all_signals = []
    
    for symbol in test_symbols:
        print(f"\n  Processing {symbol}...")
        
        # Try Bybit first, fallback to yfinance
        klines = []
        try:
            klines = await get_historical_klines_bybit(context.data_provider, symbol, "15m", 30)
            if len(klines) >= 10:
                print(f"  Got {len(klines)} klines from Bybit")
        except Exception as e:
            print(f"  Bybit failed: {e}")
        
        if len(klines) < 10 and YFINANCE_AVAILABLE:
            print(f"  Trying Yahoo Finance...")
            klines = await get_historical_klines_yfinance(symbol, 30)
            print(f"  Got {len(klines)} klines from Yahoo Finance")
        
        if len(klines) < 10:
            print(f"  Skipping {symbol} - insufficient data")
            continue
            
        signals = await run_strategy_on_klines(context, pipeline, symbol, klines)
        all_signals.extend(signals)
        
        if len(all_signals) >= 10:
            print(f"\n  Found {len(all_signals)} signals, stopping early")
            break
    
    # Report results
    print("\n[4/4] VALIDATION RESULTS")
    print(f"Total signals found: {len(all_signals)}")
    
    for i, sig in enumerate(all_signals[:10]):
        print(f"\n  Signal {i+1}:")
        print(f"  Symbol: {sig['symbol']}")
        print(f"  Time: {sig['time']}")
        print(f"  OHLC: O={sig['open']:.4f} H={sig['high']:.4f} L={sig['low']:.4f} C={sig['close']:.4f}")
        print(f"  Volume: {sig['volume']:.0f}")
        print(f"  Lower Wick: {sig['lower_wick']:.4f}")
        print(f"  Body: {sig['body']:.4f}")
        print(f"  Wick/Body Ratio: {sig['wick_body_ratio']:.2f}x")
        print(f"  Score: {sig['score']:.1f}/100")
        
        # Verify the signal logic
        body = sig['close'] - sig['open']
        body_size = abs(body)
        lower_wick = min(sig['open'], sig['close']) - sig['low']
        ratio = sig['lower_wick'] / body_size if body_size != 0 else 0
        print(f"  Verification: Body={body:.4f}, LowerWick={sig['lower_wick']:.4f}, Ratio={ratio:.2f}x")
    
    # Shutdown
    from application.bootstrap import shutdown
    await shutdown(context)
    
    return all_signals


if __name__ == "__main__":
    from datetime import UTC, datetime
    import asyncio
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    
    from core import init_logging, LogLevel, LoggingConfig
    from models.enums import Exchange, Timeframe, EventStatus
    from application.bootstrap import bootstrap
    from event_engine.event_pipeline import create_default_pipeline
    from event_engine.context import EventContext
    from models import MarketEvent
    from models.enums import EventStatus
    from models.identifiers import EventID
    from models.market_event import MarketData, Metadata, StrategyData
    
    signals = asyncio.run(main())
    print(f"\nValidation complete. Found {len(signals)} signals.")
    if len(signals) == 0:
        print("No signals found. Check data sources and strategy parameters.")
    sys.exit(0 if len(signals) >= 10 else 1)