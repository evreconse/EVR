�^# Historical Backtest Audit Report

**Date:** 2026-08-05  
**File:** `historical_backtest.py`  
**Objective:** Verify that backtest implements exact LW-001 production strategy

---

## 1. Source of Data

### historical_backtest.py

| Field | Source | Details |
|-------|--------|---------|
| **Candles (OHLC)** | Bybit REST V5 | Line 34: `BASE_URL = "https://api.bybit.com/v5/market/kline"` |
| **Volume** | Bybit REST V5 | Line 79: `volume = float(ohlc[5])` from kline data |
| **Liquidations** | ❌ NOT AVAILABLE | Line 135-136: `liq_score = 0.0` with placeholder explanation |
| **Candle Confirmation** | ❌ NOT CHECKED | No validation that candle is closed/confirmed |

### Production LW-001 (src/strategy/lw_001.py)

| Field | Source | Details |
|-------|--------|---------|
| **Candles (OHLC)** | Bybit WebSocket | Lines 203-207: Extracted from `market_data` (from WebSocket) |
| **Volume** | Bybit WebSocket | Line 207: `volume = market_data.volume` |
| **Liquidations** | strategy_data | Lines 230-231: `liquidation_volume = strategy_data.liquidation_volume` |
| **Candle Confirmation** | strategy_data | Lines 197-198: `if not getattr(strategy_data, "confirm", False)` |

### ❌ CRITICAL DIFFERENCE #1: Liquidation Data

**historical_backtest.py:**
- Line 135-136: `liq_score = 0.0` with comment "Placeholder"
- Line 136: `liq_explanation = "Liquidation data not available (placeholder)"`
- **NO actual liquidation data is fetched or used**

**Production LW-001:**
- Lines 230-231: Expects `strategy_data.liquidation_volume` and `strategy_data.liquidation_reference_value`
- Lines 325-348: Full liquidation scoring logic with tiers (5x, 3x, 2x, 1.5x, 1x, below, none)
- Uses real liquidation data from Bybit

### ❌ CRITICAL DIFFERENCE #2: Candle Confirmation

**historical_backtest.py:**
- NO check for candle confirmation/closure
- Processes all candles regardless of whether they're closed

**Production LW-001:**
- Lines 197-198: Explicit check `if not getattr(strategy_data, "confirm", False)`
- Raises `StrategyExecutionError` if candle not confirmed/closed
- Only processes confirmed closed candles

---

## 2. Candle Calculation Formulas

### historical_backtest.py (lines 73-105)

```python
body = close_p - open_p
body_size = abs(body)
upper_wick = high_p - max(open_p, close_p)
lower_wick = min(open_p, close_p) - low_p
candle_range = high_p - low_p
wick_body_ratio = lower_wick / body_size if body_size > 0 else 0.0
body_ratio = body_size / candle_range if candle_range > 0 else 0.0
close_position = (close_p - low_p) / candle_range if candle_range > 0 else 0.0
```

### Production LW-001 (lines 212-225)

```python
body = close_price - open_price
body_size = abs(body)
upper_wick = high_price - max(open_price, close_price)
lower_wick = min(open_price, close_price) - low_price
candle_range = high_price - low_price
wick_body_ratio = lower_wick / body_size if body_size > 0 else 0.0
body_ratio = body_size / candle_range if candle_range > 0 else 0.0
close_position = (close_price - low_price) / candle_range if candle_range > 0 else 0.0
```

### ✅ VERDICT: Formulas IDENTICAL

All candle structure calculations match exactly between backtest and production.

---

## 3. Score Calculation

### historical_backtest.py

#### Lower Wick Score (lines 109-132)
```python
if ratio >= 3.0:
    wick_score = 40.0
elif ratio >= 2.5:
    wick_score = 35.0
elif ratio >= 2.0:
    wick_score = 30.0
elif ratio >= 1.5:
    wick_score = 20.0
elif ratio >= 1.0:
    wick_score = 10.0
else:
    wick_score = 0.0
```

#### Liquidation Score (lines 134-136)
```python
liq_score = 0.0  # ❌ HARDCODED TO ZERO
liq_explanation = "Liquidation data not available (placeholder)"
```

#### Confirmation Score (lines 138-165)
```python
if body_ratio >= 0.6:
    confirm_score = 25.0
elif body_ratio >= 0.4:
    confirm_score = 20.0
elif body_ratio >= 0.2:
    confirm_score = 15.0
else:
    confirm_score = 10.0

# Bonus for close near high
if close_position >= 0.8:
    confirm_score += 5.0
```

#### Final Score (lines 167-175)
```python
total_score = (
    wick_score * (WICK_WEIGHT / 100) +
    liq_score * (LIQ_WEIGHT / 100) +
    confirm_score * (CONFIRM_WEIGHT / 100)
)
final_score = min(total_score, 100.0)
qualified = final_score >= MIN_CONFIDENCE_SCORE
```

### Production LW-001

#### Lower Wick Score (lines 293-319)
```python
if ratio >= 3.0:
    wick_score = wick_tiers["3x"]  # 40
elif ratio >= 2.5:
    wick_score = wick_tiers["2_5x"]  # 35
elif ratio >= 2.0:
    wick_score = wick_tiers["2x"]  # 30
elif ratio >= 1.5:
    wick_score = wick_tiers["1_5x"]  # 20
elif ratio >= 1.0:
    wick_score = wick_tiers["1x"]  # 10
else:
    wick_score = 0
```

#### Liquidation Score (lines 325-348)
```python
if liq_ratio >= 5.0:
    liq_score = liq_tiers["5x"]  # 35
elif liq_ratio >= 3.0:
    liq_score = liq_tiers["3x"]  # 30
elif liq_ratio >= 2.0:
    liq_score = liq_tiers["2x"]  # 25
elif liq_ratio >= 1.5:
    liq_score = liq_tiers["1_5x"]  # 20
elif liq_ratio >= 1.0:
    liq_score = liq_tiers["1x"]  # 15
else:
    liq_score = liq_tiers["below"]  # 10
```

#### Confirmation Score (lines 350-379)
```python
if body_ratio >= 0.6:
    confirm_score = confirm_tiers["bull_0_6"]  # 25
elif body_ratio >= 0.4:
    confirm_score = confirm_tiers["bull_0_4"]  # 20
elif body_ratio >= 0.2:
    confirm_score = confirm_tiers["bull_0_2"]  # 15
else:
    confirm_score = confirm_tiers["bull_0_1"]  # 10

# Bonus for close near high
if close_position >= 0.8:
    confirm_score += 5
```

#### Final Score (lines 386-397)
```python
total_score = (
    wick_score * (wick_weight / 100) +
    liq_score * (liq_weight / 100) +
    confirm_score * (confirm_weight / 100)
)
final_score = min(total_score, max_score)
qualified = final_score >= min_score
```

### ❌ CRITICAL DIFFERENCE #3: Liquidation Score

**historical_backtest.py:**
- Liquidation score is **HARDCODED TO 0**
- No liquidation data is fetched
- No liquidation ratio calculation
- No liquidation tier logic

**Production LW-001:**
- Full liquidation scoring with 7 tiers (5x, 3x, 2x, 1.5x, 1x, below, none)
- Calculates `liq_ratio = liquidation_volume / liquidation_reference`
- Uses real liquidation data from Bybit

### ✅ VERDICT: Lower Wick and Confirmation scores match, but Liquidation score is completely different

---

## 4. Configuration Parameters

### historical_backtest.py (lines 24-29)

```python
LOWER_WICK_RATIO = 2.0
MIN_CONFIDENCE_SCORE = 80.0
WICK_WEIGHT = 40.0
LIQ_WEIGHT = 35.0
CONFIRM_WEIGHT = 25.0
```

### Production config.yaml (after fix)

```yaml
strategy:
  LW-001:
    condition:
      lower_wick_ratio: 2.0
      min_confidence_score: 80
    scoring:
      lower_wick_weight: 40
      liquidation_weight: 35
      confirmation_weight: 25
```

### ✅ VERDICT: Configuration parameters match production values

However, the backtest does NOT use:
- `lower_wick_min_points` (defined in config but not used in backtest)
- `liquidation_min_ratio` (defined in config but not used in backtest)
- `body_max_ratio` (defined in config but not used in backtest)

These parameters are read by production LW-001 but ignored by backtest.

---

## 5. Liquidation Data - CRITICAL ISSUE

### historical_backtest.py

**Source:** NONE

**Implementation:** 
- Line 135: `liq_score = 0.0` (hardcoded)
- Line 136: `liq_explanation = "Liquidation data not available (placeholder)"`
- NO API call to fetch liquidation data
- NO liquidation calculation
- NO liquidation ratio computation

**Explanation in script (lines 295-298):**
```
print("This could indicate:")
print("  - Market conditions don't meet strategy criteria")
print("  - Liquidation data is needed (currently placeholder)")
print("  - Configuration thresholds may be too strict")
```

### Production LW-001

**Source:** `strategy_data.liquidation_volume` and `strategy_data.liquidation_reference_value`

**Implementation:**
- Lines 230-231: Extracts liquidation data from strategy_data
- Lines 325-348: Full liquidation scoring logic
- Calculates `liq_ratio = liquidation_volume / liquidation_reference`
- Applies 7-tier scoring system

### ❌ CRITICAL FINDING: Historical liquidation data is NOT available

**Bybit API Limitation:**
- Bybit REST V5 `/v5/market/kline` endpoint provides ONLY OHLCV data
- Historical liquidation data is NOT available via public API
- Liquidation data is only available via WebSocket in real-time

**Impact:**
- Backtest CANNOT accurately reproduce production strategy
- Liquidation score is always 0 in backtest
- This means backtest will produce MORE signals than production (since 35 points are always missing from score calculation)
- Any signals found by backtest would have LOWER scores in production (or be rejected entirely)

---

## 6. Data Verification

### historical_backtest.py uses:

| Data Type | Source | Status |
|-----------|--------|--------|
| Candles (OHLC) | Bybit REST V5 | ✅ Real data |
| Volume | Bybit REST V5 | ✅ Real data |
| Liquidations | NONE | ❌ Placeholder (0) |
| Candle confirmation | NONE | ❌ Not checked |

### Production LW-001 uses:

| Data Type | Source | Status |
|-----------|--------|--------|
| Candles (OHLC) | Bybit WebSocket | ✅ Real data |
| Volume | Bybit WebSocket | ✅ Real data |
| Liquidations | strategy_data | ✅ Real data (when available) |
| Candle confirmation | strategy_data | ✅ Checked |

### ❌ VERDICT: Backtest uses placeholder data for liquidations

---

## 7. Strategy Identity Verification

### Differences Found:

1. **Liquidation Data:** Backtest has none, production requires it
2. **Candle Confirmation:** Backtest doesn't check, production requires it
3. **Liquidation Scoring:** Backtest hardcoded to 0, production has full 7-tier system
4. **Configuration Parameters:** Backtest ignores `lower_wick_min_points`, `liquidation_min_ratio`, `body_max_ratio`

### ❌ VERDICT: historical_backtest.py does NOT implement the same strategy as production LW-001

The backtest is a **simplified version** that:
- Ignores liquidation data (35% of scoring weight)
- Ignores candle confirmation
- Will produce different results than production

---

## 8. Final Conclusion

| Check | Status | Details |
|-------|--------|---------|
| Source of candles | ✅ | Bybit REST V5 (real data) |
| Source of liquidations | ❌ | NONE - hardcoded to 0 |
| Formulas match | ⚠️ | Candle formulas match, but liquidation formula missing |
| Score matches | ❌ | Liquidation score is 0 instead of full tier system |
| Configuration production | ⚠️ | Main weights match, but some parameters ignored |
| No test data | ❌ | Uses placeholder for liquidations |
| Fully identical to LW-001 | ❌ | **NOT IDENTICAL** - missing critical components |

---

## Summary

**historical_backtest.py CANNOT be used to verify LW-001 strategy because:**

1. **Liquidation data is not available historically** - Bybit does not provide historical liquidation data via public API
2. **Backtest uses placeholder (0) for liquidation score** - This is 35% of the total scoring weight
3. **Candle confirmation is not checked** - Production requires candles to be confirmed/closed
4. **Results will be different** - Backtest will find more signals (lower threshold due to missing 35 points) than production

---

## Recommended Solution

To properly backtest LW-001 strategy:

1. **Option A: Run real-time test**
   - Start the production bot
   - Let it run for 1-2 weeks
   - Collect actual signals with real liquidation data
   - Analyze those signals

2. **Option B: Use alternative data source**
   - Find a third-party provider that has historical liquidation data
   - Integrate that data source into backtest
   - This requires external API/service

3. **Option C: Simplified backtest with disclaimer**
   - Run current backtest with clear documentation that liquidation data is missing
   - Understand that results will be optimistic (more signals than production)
   - Use only for preliminary candle pattern analysis, NOT for final strategy validation

**Current backtest is NOT suitable for production strategy validation.**
�^*cascade082Xfile:///C:/Users/user/Documents/Default%20Project/EVRECONSE/HISTORICAL_BACKTEST_AUDIT.md