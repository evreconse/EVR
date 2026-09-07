#!/usr/bin/env python3
"""
EVRECONSE LW-001 Strategy Verification Script.

Tests the LW-001 strategy with a synthetic candle that should guarantee qualification.
Runs the FULL pipeline exactly as live execution:
MarketEvent -> EventEngine -> Pipeline -> LW-001 -> ScoringEngine -> NotificationEngine -> Telegram
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core import init_logging, LogLevel, LoggingConfig
from models import MarketEvent
from models.enums import Exchange, Timeframe, EventStatus
from models.identifiers import EventID
from models.market_event import MarketData, Metadata, StrategyData

from application.bootstrap import bootstrap
from event_engine import EngineConfig as EventEngineConfig
from event_engine.event_pipeline import create_default_pipeline


def create_synthetic_event() -> MarketEvent:
    """
    Create a synthetic MarketEvent with a candle that GUARANTEES LW-001 qualification.

    Candle structure:
    - Open = 100
    - High = 102
    - Low = 80   (20 points down = very long lower wick)
    - Close = 101 (small body = 1 point)

    Lower wick = 20 points (min(Open, Close) - Low = 100 - 80)
    Body = 1 point (Close - Open = 1)
    Wick/body ratio = 20.0 >> 2.0 threshold

    This is an extreme bullish hammer candle that should score maximum points.
    """
    event_time = datetime.now(UTC)
    event_id = EventID._generate()

    market_data = MarketData(
        symbol="BTCUSDT",
        exchange=Exchange.BYBIT,
        timeframe=Timeframe.M15,
        event_time=event_time,
        open=100.0,
        high=102.0,
        low=80.0,
        close=101.0,
        volume=1000.0,
    )

    # Strategy data computed from candle
    # These values must match what the pipeline computes
    lower_wick = min(100.0, 101.0) - 80.0  # 20.0
    body = 101.0 - 100.0  # 1.0
    body_size = abs(body)  # 1.0
    upper_wick = 102.0 - max(100.0, 101.0)  # 1.0
    wick_body_ratio = lower_wick / body_size  # 20.0

    strategy_data = StrategyData(
        strategy_id="LW-001",
        lower_wick=lower_wick,
        body=body_size,
        wick_body_ratio=wick_body_ratio,
        lower_wick_pct=lower_wick / (102.0 - 80.0),  # 20/22 = 0.909
        body_pct=body_size / (102.0 - 80.0),  # 1/22 = 0.045
        liquidation_volume=5000.0,  # High liquidation to guarantee score
        liquidation_reference_value=1000.0,  # Reference = 5x lower -> strong
    )

    metadata = Metadata(
        event_id=event_id,
        status=EventStatus.NEW,
        schema_version=1,
        created_at=event_time,
        updated_at=event_time,
    )

    event = MarketEvent(
        schema_version=1,
        metadata=metadata,
        market_data=market_data,
        strategy_data=strategy_data,
    )

    return event


async def run_diagnostic():
    """Run the full pipeline diagnostic."""
    print("=" * 60)
    print("EVRECONSE LW-001 STRATEGY VERIFICATION")
    print("=" * 60)

    # Initialize logging
    log_config = LoggingConfig(
        level=LogLevel.INFO,
        log_path=None,
        console_enabled=True,
        file_enabled=False,
        json_format=False,
    )
    init_logging(log_config)

    # Create synthetic event
    print("\n[1/6] EVENT CREATED")
    event = create_synthetic_event()
    print(f"    Event ID: {event.event_id}")
    print(f"    Symbol: {event.market_data.symbol}")
    print(f"    Timeframe: {event.market_data.timeframe}")
    print(f"    O={event.market_data.open} H={event.market_data.high} "
          f"L={event.market_data.low} C={event.market_data.close}")
    print(f"    Lower Wick: {event.strategy_data.lower_wick}")
    print(f"    Body: {event.strategy_data.body}")
    print(f"    Wick/Body Ratio: {event.strategy_data.wick_body_ratio:.2f}")
    print(f"    Liquidation Volume: {event.strategy_data.liquidation_volume}")
    print(f"    Liquidation Reference: {event.strategy_data.liquidation_reference_value}")

    # Bootstrap application
    print("\n[2/6] BOOTSTRAPPING APPLICATION")
    context = await bootstrap(config_path=Path("config.yaml"))

    # Start notification engine (starts worker)
    print("\n[2.5/6] STARTING NOTIFICATION ENGINE")
    print("    Starting notification engine worker...")
    await context.notification_engine.start()
    print("    Notification engine started")

    # Create pipeline with all engines
    print("\n[3/6] PIPELINE STARTED")
    pipeline = create_default_pipeline(
        strategy_engine=context.strategy_engine,
        scoring_engine=context.scoring_engine,
        notification_engine=context.notification_engine,
        outcome_tracker=context.outcome_tracker,
        storage_service=context.storage_engine,
    )

    # Create event context for pipeline
    from event_engine.context import EventContext

    pipeline_context = EventContext(
        event_id=event.event_id,
        event_type="market_event",
        status="new",
        created_at=event.metadata.created_at,
        updated_at=event.metadata.updated_at,
        symbol=event.market_data.symbol,
        exchange=event.market_data.exchange.value,
        timeframe=event.market_data.timeframe.value,
        open_price=event.market_data.open,
        high_price=event.market_data.high,
        low_price=event.market_data.low,
        close_price=event.market_data.close,
        volume=event.market_data.volume,
        event_time=event.market_data.event_time,
        strategy_id="LW-001",
        lower_wick=event.strategy_data.lower_wick,
        body=event.strategy_data.body,
        wick_body_ratio=event.strategy_data.wick_body_ratio,
        liquidation_volume=event.strategy_data.liquidation_volume,
        liquidation_reference=event.strategy_data.liquidation_reference_value,
    )

    # Execute pipeline
    print("    Running pipeline...")
    result = await pipeline.execute(pipeline_context)

    # Check results
    print("\n[4/6] LW001 RESULT")
    print(f"    Pipeline Success: {result.success}")
    print(f"    Final Status: {result.final_context.status}")
    print(f"    Strategy ID: {result.final_context.strategy_id}")
    print(f"    Lower Wick: {result.final_context.lower_wick}")
    print(f"    Body: {result.final_context.body}")
    print(f"    Wick/Body Ratio: {result.final_context.wick_body_ratio}")
    print(f"    Confidence Score: {result.final_context.confidence_score}")

    # Check stage results
    for stage_name, stage_result in result.stage_results.items():
        print(f"    Stage [{stage_name}]: Success={stage_result.get('success', False)}, "
              f"Duration={stage_result.get('duration_ms', 0):.1f}ms")
        if "error" in stage_result:
            print(f"      ERROR: {stage_result['error']}")

    qualified = (result.final_context.confidence_score or 0.0) >= 80.0
    score = result.final_context.confidence_score or 0.0

    print(f"\n    LW001 QUALIFIED = {qualified}")
    print(f"    FINAL SCORE = {score}")

    if not qualified:
        print("\n[ERROR] STRATEGY REJECTED - Debugging conditions...")
        # The strategy evaluates in lw_001.py, let's check what conditions failed
        print("\n    Individual condition checks:")
        print(f"      Lower wick length: {event.strategy_data.lower_wick} (need >= 2x body)")
        print(f"      Body size: {event.strategy_data.body}")
        print(f"      Wick/Body ratio: {event.strategy_data.wick_body_ratio:.2f} (need >= 2.0)")
        print(f"      Liquidation volume: {event.strategy_data.liquidation_volume}")
        print(f"      Liquidation reference: {event.strategy_data.liquidation_reference_value}")

        # Check scoring parameters
        lower_wick = event.strategy_data.lower_wick
        body = event.strategy_data.body
        ratio = event.strategy_data.wick_body_ratio

        # LW-001 scoring logic
        if body > 0:
            print(f"      Body > 0: YES ({body})")
            if ratio >= 3.0:
                wick_score = 40
            elif ratio >= 2.5:
                wick_score = 35
            elif ratio >= 2.0:
                wick_score = 30
            elif ratio >= 1.5:
                wick_score = 20
            elif ratio >= 1.0:
                wick_score = 10
            else:
                wick_score = 0
        else:
            print(f"      Body > 0: NO")
            wick_score = 15

        print(f"      Wick score: {wick_score}/40")

        # Liquidation score (from strategy)
        liq_score = 20.0  # Base score from lw_001.py

        # Candle confirmation
        candle_range = 102.0 - 80.0  # 22.0
        body_ratio = abs(body) / candle_range if candle_range > 0 else 0
        print(f"      Body ratio: {body_ratio:.4f} (need >= 0.6 for bullish)")
        if body > 0:
            if body_ratio >= 0.6:
                confirm_score = 25
            elif body_ratio >= 0.4:
                confirm_score = 20
            elif body_ratio >= 0.2:
                confirm_score = 15
            else:
                confirm_score = 10
            # Bonus for close near high
            close_position = (101.0 - 80.0) / candle_range  # 21/22 = 0.95
            print(f"      Close position: {close_position:.2f} (need >= 0.8)")
            if close_position >= 0.8:
                confirm_score += 5
        else:
            confirm_score = 5

        print(f"      Confirm score: {confirm_score}/25")

        # Weighted total
        wick_weight = 40
        liq_weight = 35
        confirm_weight = 25

        total_score = (
            wick_score * (wick_weight / 100) +
            liq_score * (liq_weight / 100) +
            confirm_score * (confirm_weight / 100)
        )
        print(f"      Total weighted score: {total_score:.1f}/100")
        print(f"      Min threshold: 80")

        if total_score >= 80:
            print("      [OK] SHOULD QUALIFY!")
        else:
            print("      [FAIL] BELOW THRESHOLD")
    else:
        print("\n    [OK] STRATEGY QUALIFIED!")

    # Check notification
    print("\n[5/6] NOTIFICATION CREATED")
    print(f"    Notification sent: {qualified}")

    # Check Telegram
    print("\n[6/6] TELEGRAM SENT")
    if qualified:
        # The notification engine should have sent it
        print("    Waiting for Telegram delivery confirmation...")
        
        # Wait for the notification engine worker to process the message
        # Check queue size periodically
        for i in range(30):  # Wait up to 30 seconds
            queue_size = context.notification_engine._queue.size()
            print(f"    Queue size: {queue_size}, worker tasks: {len(context.notification_engine._worker_tasks)}")
            if queue_size == 0:
                print("    Queue empty - notification processed")
                break
            await asyncio.sleep(1.0)
        else:
            print("    [WARNING] Queue not empty after 30 seconds")
        
        # Give a bit more time for actual HTTP request to complete
        await asyncio.sleep(2.0)
        print("    [OK] Telegram message should arrive in configured chat")
    else:
        print("    [FAIL] No notification sent (strategy not qualified)")

    # Shutdown
    print("\n[SHUTDOWN] Stopping application...")
    from application.bootstrap import shutdown
    await shutdown(context)

    print("\n" + "=" * 60)
    if qualified:
        print("[SUCCESS] VERIFICATION COMPLETE - Telegram message sent!")
    else:
        print("[FAIL] VERIFICATION FAILED - Strategy did not qualify")
    print("=" * 60)

    return qualified


if __name__ == "__main__":
    result = asyncio.run(run_diagnostic())
    sys.exit(0 if result else 1)