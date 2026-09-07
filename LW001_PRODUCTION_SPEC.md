# LW-001 Production Specification

**Status:** ACTIVE PRODUCTION SPEC  
**Version:** 1.0  
**Date:** 2026-08-30  
**DO NOT USE HISTORICAL LW-001 THRESHOLDS**

---

## Exchange & Market

| Parameter | Value |
|-----------|-------|
| Exchange | BingX |
| Market | USDT Perpetual Futures |
| Symbol Format | `BASE-QUOTE` (e.g., `BTC-USDT`) |
| Timeframe | 15 minutes (M15) |
| Candle Type | Fully closed/confirmed candles only |

---

## Signal Qualification Conditions (ALL REQUIRED — AND LOGIC)

A candle qualifies as LW-001 signal **only if ALL 7 conditions pass**:

```python
signal = (
    close < open                                    # 1. Red candle
    and range_pct >= 4.5                            # 2. Range % >= 4.5%
    and body_pct >= 0.8                             # 3. Body % >= 0.8%
    and lw_body_ratio >= 1.3                        # 4. LW/Body >= 1.3x
    and lw_range_pct >= 55.0                        # 5. LW/Range % >= 55.0%
    and open_to_low_pct <= -2.5                     # 6. Open→Low % <= -2.5%
    and volume_ratio >= 1.5                         # 7. Volume Ratio >= 1.5x
)
```

---

## Metric Formulas (Canonical)

All formulas use **Open as denominator** for percentage metrics.

| Metric | Formula | Unit | Internal Format |
|--------|---------|------|-----------------|
| Range % | `(High - Low) / Open * 100` | % | 4.50 (not 0.045) |
| Body % | `abs(Close - Open) / Open * 100` | % | 0.80 (not 0.008) |
| Lower Wick | `min(Open, Close) - Low` | price | raw price units |
| LW/Body | `Lower_Wick / abs(Close - Open)` | x | 1.30 (not 130%) |
| LW/Range % | `Lower_Wick / (High - Low) * 100` | % | 55.00 (not 0.55) |
| Open→Low % | `(Low - Open) / Open * 100` | % | -2.50 (not -0.025) |
| Volume Ratio | `Current_Vol / Avg(Previous_20_Volumes)` | x | 1.50 (not 150%) |

**Critical:** `(Low - Open) / Open` — NOT `(Open - Low) / Open`. Result is negative.

---

## Volume Ratio Calculation

```
Volume Ratio = Current_Candle_Volume / Average(Previous_20_Candle_Volumes)
```

- **Reference:** Previous 20 closed candles ONLY
- **Excludes:** Current candle (no look-ahead)
- **Excludes:** Future candles (no data leakage)
- **If insufficient data:** Return 0.0 (safe default)
- **If average = 0:** Return 0.0

---

## Candle Requirements

| Requirement | Detail |
|-------------|--------|
| Timeframe | 15 minutes exactly |
| Status | Fully closed/confirmed |
| Direction | Red only (Close < Open) |
| Green/Doji | Automatically rejected |

---

## What Does NOT Participate in Qualification

- ❌ High price (except for LW/Range calculation)
- ❌ Upper wick
- ❌ Score (informational only)
- ❌ Liquidations (removed from project)
- ❌ RSI, MACD, ATR, Funding Rate, Open Interest
- ❌ Trend direction
- ❌ Minimum body size beyond 0.8%
- ❌ Any additional filters

---

## Scoring (Informational Only)

Score does **not** filter signals. Used for Telegram display only.

| Parameter | Weight | Max Score |
|-----------|--------|-----------|
| Lower Wick Quality | 70% | 70 |
| Candle Confirmation | 30% | 30 |

**Threshold:** 80/100 (for display only)

---

## Risk Parameters

| Parameter | Value |
|-----------|-------|
| Take Profit | 3.0% |
| Stop Loss | -3.0% |
| Max Duration | 24 hours |
| Expire After | 48 hours |

---

## Notification

| Property | Value |
|----------|-------|
| Channel | Telegram |
| Format | Plain text (no Markdown/HTML) |
| Timezone | **UTC ONLY** |
| Timestamp Format | `DD.MM.YYYY HH:MM UTC` |
| Template | Fixed (see below) |

### Telegram Template (Immutable)

```
LW-001 SIGNAL

Symbol: {symbol}

Time: {DD.MM.YYYY HH:MM UTC}

OHLCV
Open: {open:.6f}
High: {high:.6f}
Low: {low:.6f}
Close: {close:.6f}
Volume: {volume:,.0f}

Metrics
Range: {range_pct:.2f}%
Body: {body_pct:.2f}%
LW/Body: {lw_body_ratio:.2f}x
LW/Range: {lw_range_pct:.2f}%
Open-Low: {open_to_low_pct:.2f}%
Volume Ratio: {volume_ratio:.2f}x

Conditions
Range >= 4.5% - PASS/FAIL
Body >= 0.8% - PASS/FAIL
LW/Body >= 1.3x - PASS/FAIL
LW/Range >= 55% - PASS/FAIL
Open-Low <= -2.5% - PASS/FAIL
Volume Ratio >= 1.5x - PASS/FAIL

VALID SIGNAL
```

---

## Deduplication

**Key:** `symbol + candle_timestamp`  
If signal already sent → **DO NOT SEND AGAIN**

---

## Timestamp Requirements

| Rule | Requirement |
|------|-------------|
| Source | BingX kline `time` field (milliseconds) |
| Conversion | `datetime.fromtimestamp(ms/1000, tz=UTC)` |
| Display | UTC only (`DD.MM.YYYY HH:MM UTC`) |
| Forbidden | MSK, UTC+3, local time, send time, computer time |
| Consistency | Same timestamp used from BingX → Strategy → Telegram |

---

## Pipeline Architecture

```
BingX REST API (klines)
    ↓
BingXDataProvider (implements MarketDataProvider)
    ↓
EventEngine.process_market_data()
    ↓
PipelineStageStrategy → check_lw001_signal() [CANONICAL]
    ↓
PipelineStageScorer (informational)
    ↓
PipelineStageNotifier → Telegram (UTC, plain text)
    ↓
PipelineStageStorage → FileRepository
    ↓
PipelineStageOutcomeTracker → TP/SL monitoring
```

---

## Canonical Functions (Single Source of Truth)

**File:** `src/strategy/lw001_canonical.py`

```python
# Main qualification function
check_lw001_signal(open, high, low, close, volume, prev_20_volumes) 
    → LW001CheckResult(qualified, metrics, failed_conditions)

# Metrics calculation
calculate_lw001_metrics(open, high, low, close, volume, prev_20_volumes)
    → LW001Metrics

# Telegram formatting
format_lw001_telegram_message(symbol, time_utc, open, high, low, close, volume, metrics)
    → str (plain text, UTC)
```

**All components MUST use these functions. No duplicate logic allowed.**

---

## Unit Tests (20 Tests)

Run: `python -m src.strategy.lw001_canonical`

| Test | Description |
|------|-------------|
| 1 | Valid red candle passes all 6 conditions |
| 2 | Green candle rejected |
| 3 | Doji (Close==Open) rejected |
| 4 | LW/Body 1.29x rejected |
| 5 | LW/Body 1.30x boundary passes |
| 6 | Volume Ratio 1.49x rejected |
| 7 | Volume Ratio 1.50x passes |
| 8 | Range 4.49% rejected |
| 9 | Range 4.50% passes |
| 10 | Body 0.79% rejected |
| 11 | Body 0.80% passes |
| 12 | (LW/Range boundary - covered by test 9) |
| 13 | Open→Low -2.49% rejected |
| 14 | Open→Low -2.50% passes |
| 15 | Volume ref uses exactly 20 previous candles |
| 16 | Current candle NOT in reference average |
| 17 | No look-ahead / future data |
| 18 | Timestamp consistency (pipeline level) |
| 19 | Timestamp + OHLCV consistency (pipeline level) |
| 20 | Telegram uses UTC only, plain text |

---

## Historical Versions (ARCHIVED — DO NOT USE)

| Version | Range | Body | LW/Body | LW/Range | Open→Low | Vol | Status |
|---------|-------|------|---------|----------|----------|-----|--------|
| Original (Impossible) | 6.0% | 1.9% | 2.5x | 63% | -5% | 2.6x | ❌ Geometrically impossible |
| Stage 2 MODERATE_1 | 4.0% | 0.8% | 1.3x | 55% | -2.5% | 1.5x | ❌ Research only |
| Stage 2 BALANCED_2 | 4.5% | 1.0% | 1.5x | 60% | -3.0% | 1.5x | ❌ Research only |
| Working Logic (v5) | — | — | 2.0x | — | — | 1.5x (max 48) | ❌ Superseded |

**Only the specification in this document is valid for production.**

---

## Configuration (config.yaml)

```yaml
exchange:
  name: "bingx"
  timeframe: "15m"
  # symbols loaded from BingX API

strategy:
  active: ["LW-001"]
  strategies:
    LW-001:
      enabled: true
      timeframe: "15m"
      risk:
        take_profit_percent: 3.0
        stop_loss_percent: -3.0

scoring:
  minimum_signal_score: 80.0
  parameters_active:
    - "lower_wick_quality"
    - "candle_confirmation"
  lower_wick_quality:
    enabled: true
    max_score: 70
  candle_confirmation:
    enabled: true
    max_score: 30
```

---

## Verification Checklist Before Deploy

- [ ] All 20 unit tests pass
- [ ] 10 real historical signals verified manually
- [ ] Telegram receives UTC timestamps
- [ ] No MSK/local time in messages
- [ ] Deduplication works (symbol + timestamp)
- [ ] Volume ratio uses avg(prev 20), not max(prev 48)
- [ ] Red candle only (green rejected)
- [ ] Liquidations completely removed
- [ ] Score is informational only
- [ ] No duplicate metric calculations in codebase
- [ ] Single canonical function used everywhere

---

## Contacts

**Maintainer:** EVRECONSE Project  
**Canonical Spec:** `src/strategy/lw001_canonical.py`  
**Production Spec:** `LW001_PRODUCTION_SPEC.md` (this file)

---

**Historical threshold variants are archived and must not be used for production signal qualification.**