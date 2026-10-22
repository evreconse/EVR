# LW-001 Production Specification

**Status: INACTIVE / LEGACY.** The production service currently runs the
Capitulation/Absorption monitor (`realtime_capitulation_monitor_fixed.py`).
LW-001 is retained for compatibility and research only. It must not be enabled
without an explicit owner decision.

**Canonical implementation:** `LW001_METRIC_SPEC.py`
**Adapter:** `src/strategy/lw001_canonical.py`
**Repository synchronization source:** production EVRECONSE server, inspected
read-only on 2026-10-22.

---

## Exchange and timeframe

- Exchange: BingX USDT Perpetual.
- Timeframe: 15m (M15).
- Universe: all active USDT perpetual contracts, no TOP-500 limit.
- Only a completed candle may be evaluated.
- A candle is complete when:

```python
candle_close_time_ms = candle_timestamp_ms + 15 * 60 * 1000
candle_close_time_ms <= now_ms
```

The monitor fetches four hours of candles and selects the last completed candle.
The legacy LW-001 monitor requires at least two candles and `candle_index >= 1`.

---

## Signal qualification (ALL REQUIRED — AND LOGIC)

```python
is_red          = close < open
range_pct       = (high - low) / open * 100
body_pct        = abs(close - open) / open * 100
lower_wick      = min(open, close) - low
lw_body_ratio   = lower_wick / body                 # 0.0 if body == 0
lw_range_pct    = lower_wick / (high - low) * 100   # 0.0 if range == 0
open_to_low_pct = (low - open) / open * 100
```

A signal is qualified only when **all** of the following are true:

```python
is_red
and range_pct >= 4.5
and body_pct >= 0.8
and lw_body_ratio >= 1.3
and lw_range_pct >= 55.0
and open_to_low_pct <= -5.0
```

| Condition | Threshold | Operator |
|---|---:|---|
| Candle direction | `close < open` | required |
| Range | 4.5% | `>=` |
| Body | 0.8% | `>=` |
| Lower Wick / Body | 1.3x | `>=` |
| Lower Wick / Range | 55.0% | `>=` |
| Open → Low | **-5.0%** | `<=` |

The **-5.0%** value is the production server value. Earlier GitHub
documentation and code used **-2.5%**; that value is stale and must not be used.

---

## Volume and score are NOT qualification gates

- Volume Ratio is **not** part of LW-001 qualification.
- Volume Ratio was removed from the canonical specification.
- `final_score` is not a score gate. The legacy strategy may populate an
  informational score, but qualification is determined only by the six
  conditions above.
- There is no minimum-score threshold.

---

## Canonical functions

```python
from LW001_METRIC_SPEC import calculate_all_metrics, check_all_conditions

metrics = calculate_all_metrics(open, high, low, close, volume, volume_3_candles_ago)
passed, failures = check_all_conditions(metrics)
```

The `volume` and `volume_3_candles_ago` parameters are retained for backward
compatibility; they do not affect LW-001 qualification.

Canonical adapter:

```python
from strategy.lw001_canonical import check_lw001_signal

result = check_lw001_signal(open_price, high_price, low_price, close_price)
# result.qualified, result.metrics, result.failed_conditions
```

---

## Deduplication and notification (legacy monitor)

`realtime_lw001_monitor.py` uses the same conceptual persistence model as the
active monitor:

- SQLite database: `sent_signals.db`;
- primary key: `(symbol, candle_timestamp)`;
- atomic claim before sending;
- rollback of the claim if Telegram delivery fails;
- in-memory set for fast duplicate checks;
- personal chat and optional channel destinations;
- success if at least one destination receives the message.

The legacy monitor is **not running** under `evreconse.service`. It also contains
an optional demo auto-trader initialization path; that path is not active and no
trading was executed during the audit.

---

## Verification

The repository includes `tests/test_server_sync_algorithms.py`, which verifies:

- exact LW-001 thresholds, including `open_to_low_pct == -5.0`;
- exact metric formulas;
- range/body/LW-body/LW-range boundaries;
- inclusive Open→Low boundary;
- absence of volume-ratio and score gates.

For the active Capitulation strategy, the same test module verifies the
server thresholds (`-5.0`, `2.0`, `1.0`, `30.0`), formulas, red-candle rule,
volume boundary, wick boundary, reclaim boundary, and absence of a score gate.

---

## Historical variants (archived — do not use)

Older research and audit documents may contain `-2.5%`, Volume Ratio, or
`avg(previous_20_volumes)` thresholds. Those describe historical experiments,
not the current production LW-001 specification. The canonical values are the
ones in `LW001_METRIC_SPEC.py` and in this document.

---

## Deployment

The production unit is:

```ini
ExecStart=/usr/bin/python3 /home/evreconse/realtime_capitulation_monitor_fixed.py
```

To run LW-001, a separate unit must be created and approved; do not overwrite
the active Capitulation service. Secrets are loaded from the deployment `.env`
and must never be committed.
