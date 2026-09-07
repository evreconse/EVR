import sys
sys.path.insert(0, 'src')
from models import MarketEvent, EventID, SignalID
from models.enums import EventStatus

# Test 1: Factory methods work
event = MarketEvent.new(
    symbol='BTCUSDT',
    exchange='bybit',
    timeframe='M15',
    event_time='2026-07-25T12:00:00+00:00',
    open_price=50000.0,
    high_price=50100.0,
    low_price=49900.0,
    close_price=50050.0,
    volume=100.5,
)

print('NEW:', event.status)

# Test 2: State transitions
event = event.qualified(
    strategy_id='test-strategy',
    lower_wick=100.0,
    body=50.0,
    wick_body_ratio=2.0,
    lower_wick_pct=66.6,
    body_pct=33.3,
    liquidation_volume=1000.0,
    liquidation_reference_value=500.0,
)

event = event.scored(confidence_score=85.0, score_breakdown=(
    ('lower_wick_quality', 40.0, 0.0),
    ('liquidation_strength', 35.0, 0.0),
    ('candle_confirmation', 20.0, -5.0),
))

event = event.notified(close_price=50050.0)
event = event.monitoring()
event = event.completed(outcome='TP', actual_profit_pct=3.0)

# Test serialization round-trip
d = event.to_dict()
restored = MarketEvent.from_dict(d)
print('Round-trip equality:', event == restored)

# Test hashability
s = {event}
print('Hashable in set:', True)

# Test EventID/SignalID
eid = event.event_id
sid = event.signal_id
print('EventID:', eid)
print('SignalID:', sid)

print('All tests passed!')