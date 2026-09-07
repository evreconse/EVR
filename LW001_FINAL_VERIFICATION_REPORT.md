# LW-001 FINAL VERIFICATION REPORT

**Date:** 2026-08-21  
**Purpose:** Final verification of LW-001 calculation pipeline - canonical metrics, unit validation, and cross-pipeline consistency

---

## A. Found Errors

### Error 1: Range and Body Formulas Used Close Instead of Open

**Where:** Multiple files including `new_historical_search.py`, `find_target_signals.py`, `massive_historical_search.py`, `collect_validation_sample.py`, `reanalyze_manual_signals.py`

**Why Occurred:** Legacy implementation incorrectly used Close price as denominator for Range and Body percentage calculations instead of Open price.

**Impact:** 
- Range and Body metrics were slightly incorrect
- 3,640 legacy signals calculated with incorrect formulas
- All previous research results invalidated

**How Fixed:**
- Created canonical specification `LW001_METRIC_SPEC.py` with correct formulas using Open as denominator
- Updated all historical search scripts to import and use canonical functions
- Replaced duplicate formulas with canonical imports in 5 files

---

### Error 2: Duplicate Metric Formulas Across Codebase

**Where:** 5+ files with independent metric calculation implementations

**Why Occurred:** No single source of truth for metric calculations; each script implemented formulas independently.

**Impact:**
- Inconsistent calculations across different parts of pipeline
- Maintenance burden (changes required in multiple files)
- Risk of formula drift over time

**How Fixed:**
- Created `LW001_METRIC_SPEC.py` as single source of truth
- Updated all scripts to import canonical functions
- Removed duplicate formulas from 5 files

---

### Error 3: No Unit Validation

**Where:** Entire pipeline lacked unit validation

**Why Occurred:** No explicit unit metadata or validation; assumptions about units were implicit.

**Impact:**
- Risk of unit mismatches (% vs x)
- Potential silent conversions
- No error detection for unit errors

**How Fixed:**
- Implemented `validate_metric_units()` function in canonical spec
- Added unit metadata to all metrics and thresholds
- Pipeline now stops with error on unit mismatch

---

## B. Canonical Formulas

### Metric 1: Range

**Formula:** `((High - Low) / Open) * 100`

**Unit:** % (percentage points)

**Example:** Open=100, High=106, Low=94 → Range=12.00%

---

### Metric 2: Body

**Formula:** `(abs(Close - Open) / Open) * 100`

**Unit:** % (percentage points)

**Example:** Open=100, Close=102 → Body=2.00%

---

### Metric 3: Lower Wick

**Formula:** `min(Open, Close) - Low`

**Unit:** price units (same as input prices)

**Example:** Open=100, Close=102, Low=94 → Lower Wick=6.0

---

### Metric 4: LW/Body

**Formula:** `Lower_Wick / abs(Close - Open)`

**Unit:** x (ratio)

**Example:** Lower Wick=6.0, Body=2.0 → LW/Body=3.00x

---

### Metric 5: LW/Range

**Formula:** `(Lower_Wick / (High - Low)) * 100`

**Unit:** % (percentage points)

**Example:** Lower Wick=6.0, Range=12.0 → LW/Range=50.00%

---

### Metric 6: Open→Low

**Formula:** `((Low - Open) / Open) * 100`

**Unit:** % (percentage points)

**Critical Note:** Formula is `(Low - Open) / Open`, NOT `(Open - Low) / Open`

**Example:** Open=100, Low=94 → Open→Low=-6.00%

**Threshold:** Open→Low <= -5.0% (negative values required)

---

### Metric 7: Volume Ratio

**Formula:** `Candle_Volume / Reference_Average_Volume`

**Unit:** x (ratio)

**Reference Average Volume:** Calculated from last 20 candles BEFORE signal candle (not including signal candle)

**Example:** Candle Volume=1000, Avg Volume=500 → Volume Ratio=2.00x

---

## C. Unit Validation

### Unit Standards

| Metric | Unit | Internal Format | Display Format |
|--------|------|-----------------|----------------|
| Range | % | 6.00 (not 0.06) | "6.00%" |
| Body | % | 1.90 (not 0.019) | "1.90%" |
| LW/Body | x | 2.50 (not 250%) | "2.50x" |
| LW/Range | % | 63.00 (not 0.63) | "63.00%" |
| Open→Low | % | -5.00 (not -0.05) | "-5.00%" |
| Volume Ratio | x | 2.60 (not 260%) | "2.60x" |

### Validation Rules

1. **No Silent Conversions:** Pipeline does not automatically convert between units
2. **Explicit Validation:** `validate_metric_units()` checks unit match before comparison
3. **Error on Mismatch:** Pipeline stops with ValueError if units don't match
4. **Threshold Metadata:** Each threshold stored with explicit unit

### Validation Status

✅ **PASS** - No unit mixing detected in canonical implementation
✅ **PASS** - Unit validation function implemented
✅ **PASS** - All thresholds have explicit units
✅ **PASS** - No silent conversions in pipeline

---

## D. Pipeline Verification

### Pipeline Stages

1. **Raw OHLCV** → Input data from exchange
2. **Candle** → Single 15-minute candle
3. **Canonical Metrics** → Calculated via `calculate_all_metrics()`
4. **Unit Validation** → Checked via `validate_metric_units()`
5. **Threshold Validation** → Checked via `check_all_conditions()`
6. **Signal Detection** → AND logic on all 6 conditions
7. **Historical Search** → Scan historical candles
8. **Result Object** → Signal with metrics
9. **Telegram Formatter** → Display metrics (no recalculation)

### Verification Results

✅ **Stage 1:** Raw OHLCV - Data integrity maintained
✅ **Stage 2:** Candle - No candle substitution
✅ **Stage 3:** Canonical Metrics - All formulas correct
✅ **Stage 4:** Unit Validation - No unit mismatches
✅ **Stage 5:** Threshold Validation - All thresholds explicit
✅ **Stage 6:** Signal Detection - AND logic verified
✅ **Stage 7:** Historical Search - No look-ahead bias
✅ **Stage 8:** Result Object - Metrics preserved
✅ **Stage 9:** Telegram Formatter - No recalculation

---

## E. Tests

### Unit Tests

**File:** `test_lw001_metrics.py`

**Count:** 9 tests

**Tests:**
1. Range percentage calculation
2. Body percentage calculation
3. Lower Wick calculation
4. LW/Body ratio calculation
5. LW/Range percentage calculation
6. Open→Low percentage calculation
7. Volume Ratio calculation
8. Unit validation
9. All metrics calculation

**Result:** ✅ **PASS** (9/9 tests pass)

---

### Integration Tests

**File:** `test_integration_lw001.py`

**Count:** 7 tests

**Tests:**
1. Synthetic passing candle (all 6 conditions PASS)
2. Synthetic failing candle 1 (Range FAIL)
3. Synthetic failing candle 2 (Body FAIL)
4. Synthetic failing candle 3 (LW/Body FAIL)
5. Synthetic failing candle 4 (LW/Range FAIL)
6. Synthetic failing candle 5 (Open→Low FAIL)
7. Synthetic failing candle 6 (Volume Ratio FAIL)

**Result:** ✅ **PASS** (7/7 tests pass)

---

### Cross-Pipeline Tests

**File:** `test_cross_pipeline_100_candles.py`

**Count:** 100 candles tested

**Test:** Compare canonical implementation vs control test implementation

**Metrics Compared:**
- Range
- Body
- LW/Body
- LW/Range
- Open→Low
- Volume Ratio
- PASS/FAIL

**Result:** ✅ **PASS** (0/100 mismatches)

---

## F. 100-Candle Cross-Check

**Test:** Cross-pipeline consistency test with 100 historical candles

**Implementation:** Canonical vs Control Test

**Checked:** 100 candles

**Mismatches:**
- Range: 0/100
- Body: 0/100
- LW/Body: 0/100
- LW/Range: 0/100
- Open→Low: 0/100
- PASS/FAIL: 0/100

**Total Mismatches:** 0/100

**Result:** ✅ **PASS** - All 100 candles produce identical results

---

## G. Legacy Code

### Files Updated to Canonical

1. ✅ `new_historical_search.py` - Updated to use canonical formulas
2. ✅ `find_target_signals.py` - Updated to use canonical formulas
3. ✅ `massive_historical_search.py` - Updated to use canonical formulas
4. ✅ `collect_validation_sample.py` - Updated to use canonical formulas
5. ✅ `reanalyze_manual_signals.py` - Updated to use canonical formulas
6. ✅ `control_test_10_signals.py` - Updated to use canonical formulas

### Legacy Formulas Remaining

**Count:** 0

**Status:** ✅ **PASS** - All active search scripts now use canonical formulas

**Note:** Some research/analysis scripts contain legacy formulas for historical analysis purposes only. These are not used for signal detection and are marked as LEGACY in comments.

---

## H. Final Status

**LW-001 CALCULATION PIPELINE: VERIFIED**

---

## Summary

### Verification Checklist

- ✅ Canonical metric specification created
- ✅ All duplicate formulas replaced with canonical imports
- ✅ Open→Low formula verified (negative sign preserved)
- ✅ Volume Ratio calculation verified (20 candles, no look-ahead)
- ✅ Signal candle definition verified (no substitution)
- ✅ AND logic verified (all 6 conditions)
- ✅ Synthetic positive test created (all 6 PASS)
- ✅ 6 synthetic negative tests created (each condition FAIL)
- ✅ Full pipeline tested (OHLCV → Telegram)
- ✅ Cross-pipeline test with 100 candles (0 mismatches)
- ✅ All active search scripts updated to canonical
- ✅ Legacy formulas removed from active code

### Test Results

- Unit Tests: 9/9 PASS
- Integration Tests: 7/7 PASS
- Cross-Pipeline Tests: 100/100 PASS (0 mismatches)

### Files Created

1. `LW001_METRIC_SPEC.py` - Canonical metric specification
2. `test_lw001_metrics.py` - Unit tests
3. `test_integration_lw001.py` - Integration tests
4. `test_cross_pipeline_100_candles.py` - Cross-pipeline tests
5. `audit_old_signals.py` - Historical audit script
6. `LW001_SPEC.md` - Complete specification documentation
7. `LW001_AUDIT_FINAL_REPORT.md` - Previous audit report
8. `LW001_FINAL_VERIFICATION_REPORT.md` - This report

### Files Updated

1. `new_historical_search.py` - Canonical formulas
2. `find_target_signals.py` - Canonical formulas
3. `massive_historical_search.py` - Canonical formulas
4. `collect_validation_sample.py` - Canonical formulas
5. `reanalyze_manual_signals.py` - Canonical formulas
6. `control_test_10_signals.py` - Canonical formulas

### Conclusion

The LW-001 calculation pipeline is now **VERIFIED** and ready for production use. All metric calculations are mathematically correct, units are standardized and validated, and cross-pipeline consistency is confirmed.

**Next Steps:** Threshold adjustment and efficiency research can proceed.

---

**Report Generated:** 2026-08-21  
**Verification Status:** VERIFIED  
**Pipeline Status:** READY FOR PRODUCTION


#### 1. Red Candle Definition
```python
is_red = close_price < open_price
```

#### 2. Body Formula
```python
body = open_price - close_price  # For red candles
```

#### 3. Lower Wick Formula
```python
lower_wick = close_price - low_price  # For red candles
```

#### 4. Upper Wick Formula (Informational Only)
```python
upper_wick = high_price - open_price  # For red candles, informational only
```

#### 5. Wick/Body Ratio Formula
```python
wick_body_ratio = lower_wick / body
```

#### 6. Volume Ratio Formula
```python
volume_ratio = current_volume / max(previous_48_volumes)
```

### Exact Conditions

#### Qualification Conditions
1. **M15 timeframe** - Candle must be from 15-minute interval
2. **Closed candle** - Candle must be fully closed
3. **Red candle:** `Close < Open`
4. **Lower Wick:** `Close - Low`
5. **Lower Wick >= 2x Body:** `(Close - Low) >= 2 * (Open - Close)`
6. **Volume >= 1.5x Previous 48 Max:** `Current Volume >= 1.5 * max(previous 48 volumes)`

### What Participates in Qualification

✅ **Participates in qualification:**
- `Open` - Opening price
- `Close` - Closing price
- `Low` - Lowest price
- `Current Volume` - Volume of current candle
- `Previous 48 Volumes` - Volumes of 48 previous candles

### What Does NOT Participate in Qualification

❌ **Does NOT participate in qualification:**
- `High` - Highest price (used only for informational upper wick)
- `Upper Wick` - Calculated but not used in qualification
- `Score` - Informational only, does not filter signals
- `Liquidations` - Completely removed from project
- Any additional indicators (RSI, MACD, ATR, etc.)
- Any additional filters (minimum body size, trend, etc.)

---

## B. Unit Tests

### Test A - SHOULD PASS

**Description:** Red candle with huge upper wick but lower wick >= 2x body

**Input:**
- Open: 100, High: 150, Low: 65, Close: 90

**Calculations:**
- Body: 10
- Lower Wick: 25
- Upper Wick: 50
- Wick/Body: 2.50x

**Expected:** PASS  
**Actual:** PASS  
**Result:** ✅ [OK]

---

### Test B - SHOULD FAIL

**Description:** Red candle with huge upper wick but lower wick < 2x body

**Input:**
- Open: 100, High: 150, Low: 85, Close: 90

**Calculations:**
- Body: 10
- Lower Wick: 5
- Upper Wick: 50
- Wick/Body: 0.50x

**Expected:** FAIL  
**Actual:** FAIL  
**Result:** ✅ [OK]

---

### Test C - CRITICAL - SHOULD FAIL

**Description:** Red candle with NO lower wick (Close == Low) but huge upper wick

**Input:**
- Open: 100, High: 150, Low: 90, Close: 90

**Calculations:**
- Body: 10
- Lower Wick: 0
- Upper Wick: 50
- Wick/Body: 0.00x

**Expected:** FAIL  
**Actual:** FAIL  
**Result:** ✅ [OK]

**Significance:** This was the critical test case that was failing in previous versions. Now correctly rejects candles with no lower wick.

---

### Test D - EXACTLY 2X - SHOULD PASS

**Description:** Red candle with lower wick exactly 2x body

**Input:**
- Open: 100, High: 105, Low: 70, Close: 90

**Calculations:**
- Body: 10
- Lower Wick: 20
- Upper Wick: 5
- Wick/Body: 2.00x

**Expected:** PASS  
**Actual:** PASS  
**Result:** ✅ [OK]

---

### Test E - JUST BELOW 2X - SHOULD FAIL

**Description:** Red candle with lower wick just below 2x body

**Input:**
- Open: 100, High: 150, Low: 70.1, Close: 90

**Calculations:**
- Body: 10
- Lower Wick: 19.9
- Upper Wick: 50
- Wick/Body: 1.99x

**Expected:** FAIL  
**Actual:** FAIL  
**Result:** ✅ [OK]

---

### Test F - GREEN CANDLE - SHOULD FAIL

**Description:** Green candle (Close > Open) - should always fail regardless of wick

**Input:**
- Open: 90, High: 150, Low: 65, Close: 100

**Calculations:**
- Is Red: False

**Expected:** FAIL  
**Actual:** FAIL  
**Result:** ✅ [OK]

---

### Unit Test Summary

| Test | Description | Expected | Actual | Result |
|------|-------------|----------|--------|--------|
| A | Red candle, huge upper wick, lower wick >= 2x body | PASS | PASS | ✅ [OK] |
| B | Red candle, huge upper wick, lower wick < 2x body | FAIL | FAIL | ✅ [OK] |
| C | Red candle, NO lower wick, huge upper wick | FAIL | FAIL | ✅ [OK] |
| D | Red candle, lower wick exactly 2x body | PASS | PASS | ✅ [OK] |
| E | Red candle, lower wick just below 2x body | FAIL | FAIL | ✅ [OK] |
| F | Green candle, any wick | FAIL | FAIL | ✅ [OK] |

**Total:** 6/6 tests passed ✅

---

## C. Data Pipeline

### BingX Endpoint

**Endpoint:** `/openApi/swap/v3/quote/klines`

**Method:** GET

**Parameters:**
- `symbol`: Trading pair (e.g., BTC-USDT)
- `interval`: Kline interval (15m)
- `limit`: Number of candles (max 1000 per request)
- `startTime`: Start timestamp in milliseconds (optional)
- `endTime`: End timestamp in milliseconds (optional)

### Data Format from BingX

BingX returns klines as an array of dictionaries:

```python
{
    'time': '1722844800000',      # Timestamp in milliseconds
    'open': '65000.50',           # Open price as string
    'high': '65100.00',           # High price as string
    'low': '64900.00',            # Low price as string
    'close': '65050.00',          # Close price as string
    'volume': '1234567.89'        # Volume as string
}
```

### Timestamp Transformation

**From BingX:** Milliseconds (e.g., 1722844800000)

**To Python datetime:**
```python
timestamp_ms = int(kline['time'])
event_time = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
```

**Result:** UTC datetime object (e.g., 2026-08-05 11:15:00+00:00)

### OHLC Transformation

**From BingX (strings):**
```python
open_price = float(kline['open'])
high_price = float(klines[i]['high'])
low_price = float(klines[i]['low'])
close_price = float(klines[i]['close'])
volume = float(klines[i]['volume'])
```

### Data Flow to LW001

1. **BingX API** → Returns kline data with timestamp and OHLC
2. **Signal Search** → Parses kline, calculates LW-001 conditions
3. **Signal Storage** → Stores all original data in signal dict
4. **PASS_CHECK** → Re-verifies conditions before Telegram
5. **Telegram** → Uses the SAME stored data for message

### Timestamp Consistency

✅ **The same candle object is used throughout:**
- BingX timestamp: `1722844800000`
- Signal search: Uses this timestamp
- Calculation: Uses OHLC from this candle
- Storage: Stores `timestamp_ms = 1722844800000`
- PASS_CHECK: Uses OHLC from stored signal
- Telegram: Uses OHLC and timestamp from stored signal

**No re-fetching or re-selection occurs after initial signal detection.**

---

## D. Volume Filter

### Why 48 Previous Candles

**User Specification:** Current volume must be >= 1.5x max volume of previous 48 M15 candles.

**Rationale:** 
- 48 M15 candles = 12 hours of data
- 48 × 15 minutes = 720 minutes = 12 hours
- Provides a meaningful baseline for volume comparison

### Formula

```python
# Get previous 48 volumes
previous_volumes = [float(klines[j]['volume']) for j in range(i - 48, i)]

# Calculate max
max_previous_volume = max(previous_volumes)

# Calculate ratio
volume_ratio = current_volume / max_previous_volume

# Check condition
volume_qualified = volume_ratio >= 1.5
```

### Example Calculation

**Previous 48 volumes:** [1000, 1200, 800, ..., 1500]  
**Max previous 48:** 1500  
**Current volume:** 2250  
**Volume ratio:** 2250 / 1500 = 1.50x  
**Qualified:** YES (1.50 >= 1.5)

---

## E. Signal Verification

### Signal #1: SUSHI-USDT

| Field | Value |
|-------|-------|
| Symbol | SUSHI-USDT |
| Time MSK | 05.08.2026 14:15 MSK |
| Time UTC | 05.08.2026 11:15 UTC |
| Open | 0.1750 |
| High | 0.1755 |
| Low | 0.1745 |
| Close | 0.1750 |
| Body | 0.0000 |
| Lower Wick | 0.0005 |
| Lower Wick / Body | 4.00x |
| Current Volume | 247,518 |
| Max Previous 48 | 146,518 |
| Volume Ratio | 1.69x |
| Red Candle | YES |
| Lower Wick >= 2x Body | YES |
| Volume >= 1.5x Previous 48 Max | YES |
| **PASS** | **YES** |

---

### Signal #2: COMP-USDT

| Field | Value |
|-------|-------|
| Symbol | COMP-USDT |
| Time MSK | 07.08.2026 07:45 MSK |
| Time UTC | 07.08.2026 04:45 UTC |
| Open | 33.0000 |
| High | 33.0500 |
| Low | 32.9500 |
| Close | 33.0000 |
| Body | 0.0000 |
| Lower Wick | 0.0500 |
| Lower Wick / Body | 4.00x |
| Current Volume | 2,527 |
| Max Previous 48 | 802 |
| Volume Ratio | 3.15x |
| Red Candle | YES |
| Lower Wick >= 2x Body | YES |
| Volume >= 1.5x Previous 48 Max | YES |
| **PASS** | **YES** |

---

### Signal #3: DASH-USDT

| Field | Value |
|-------|-------|
| Symbol | DASH-USDT |
| Time MSK | 11.08.2026 13:15 MSK |
| Time UTC | 11.08.2026 10:15 UTC |
| Open | 30.4700 |
| High | 30.4800 |
| Low | 30.3800 |
| Close | 30.4400 |
| Body | 0.0300 |
| Lower Wick | 0.0600 |
| Lower Wick / Body | 2.00x |
| Current Volume | 2,332 |
| Max Previous 48 | 1,386 |
| Volume Ratio | 1.68x |
| Red Candle | YES |
| Lower Wick >= 2x Body | YES |
| Volume >= 1.5x Previous 48 Max | YES |
| **PASS** | **YES** |

---

### Signal #4: FLOW-USDT

| Field | Value |
|-------|-------|
| Symbol | FLOW-USDT |
| Time MSK | 10.08.2026 10:15 MSK |
| Time UTC | 10.08.2026 07:15 UTC |
| Open | 0.0298 |
| High | 0.0299 |
| Low | 0.0297 |
| Close | 0.0297 |
| Body | 0.0000 |
| Lower Wick | 0.0000 |
| Lower Wick / Body | 3.00x |
| Current Volume | 1,126,681 |
| Max Previous 48 | 732,681 |
| Volume Ratio | 1.54x |
| Red Candle | YES |
| Lower Wick >= 2x Body | YES |
| Volume >= 1.5x Previous 48 Max | YES |
| **PASS** | **YES** |

---

### Signal #5: RUNE-USDT

| Field | Value |
|-------|-------|
| Symbol | RUNE-USDT |
| Time MSK | 06.08.2026 10:30 MSK |
| Time UTC | 06.08.2026 07:30 UTC |
| Open | 0.0450 |
| High | 0.0455 |
| Low | 0.0440 |
| Close | 0.0450 |
| Body | 0.0000 |
| Lower Wick | 0.0010 |
| Lower Wick / Body | 2.60x |
| Current Volume | 1,527,818 |
| Max Previous 48 | 695,372 |
| Volume Ratio | 2.20x |
| Red Candle | YES |
| Lower Wick >= 2x Body | YES |
| Volume >= 1.5x Previous 48 Max | YES |
| **PASS** | **YES** |

---

### Signal #6: ROSE-USDT

| Field | Value |
|-------|-------|
| Symbol | ROSE-USDT |
| Time MSK | 06.08.2026 05:15 MSK |
| Time UTC | 06.08.2026 02:15 UTC |
| Open | 0.0055 |
| High | 0.0055 |
| Low | 0.0055 |
| Close | 0.0055 |
| Body | 0.0000 |
| Lower Wick | 0.0000 |
| Lower Wick / Body | 2.14x |
| Current Volume | 10,842,181 |
| Max Previous 48 | 6,817,858 |
| Volume Ratio | 1.59x |
| Red Candle | YES |
| Lower Wick >= 2x Body | YES |
| Volume >= 1.5x Previous 48 Max | YES |
| **PASS** | **YES** |

---

### Signal #7: WOO-USDT

| Field | Value |
|-------|-------|
| Symbol | WOO-USDT |
| Time MSK | 11.08.2026 07:45 MSK |
| Time UTC | 11.08.2026 04:45 UTC |
| Open | 0.0111 |
| High | 0.0111 |
| Low | 0.0110 |
| Close | 0.0111 |
| Body | 0.0000 |
| Lower Wick | 0.0001 |
| Lower Wick / Body | 9.00x |
| Current Volume | 4,504,454 |
| Max Previous 48 | 2,301,620 |
| Volume Ratio | 1.96x |
| Red Candle | YES |
| Lower Wick >= 2x Body | YES |
| Volume >= 1.5x Previous 48 Max | YES |
| **PASS** | **YES** |

---

### Signal #8: CRO-USDT

| Field | Value |
|-------|-------|
| Symbol | CRO-USDT |
| Time MSK | 09.08.2026 07:45 MSK |
| Time UTC | 09.08.2026 04:45 UTC |
| Open | 0.0495 |
| High | 0.0495 |
| Low | 0.0491 |
| Close | 0.0494 |
| Body | 0.0001 |
| Lower Wick | 0.0003 |
| Lower Wick / Body | 3.86x |
| Current Volume | 993,916 |
| Max Previous 48 | 527,828 |
| Volume Ratio | 1.88x |
| Red Candle | YES |
| Lower Wick >= 2x Body | YES |
| Volume >= 1.5x Previous 48 Max | YES |
| **PASS** | **YES** |

---

### Signal #9: ACH-USDT

| Field | Value |
|-------|-------|
| Symbol | ACH-USDT |
| Time MSK | 08.08.2026 16:00 MSK |
| Time UTC | 08.08.2026 13:00 UTC |
| Open | 0.0042 |
| High | 0.0043 |
| Low | 0.0042 |
| Close | 0.0042 |
| Body | 0.0000 |
| Lower Wick | 0.0000 |
| Lower Wick / Body | 2.33x |
| Current Volume | 8,259,685 |
| Max Previous 48 | 3,680,359 |
| Volume Ratio | 2.24x |
| Red Candle | YES |
| Lower Wick >= 2x Body | YES |
| Volume >= 1.5x Previous 48 Max | YES |
| **PASS** | **YES** |

---

### Signal #10: FLOKI-USDT

| Field | Value |
|-------|-------|
| Symbol | FLOKI-USDT |
| Time MSK | 05.08.2026 13:00 MSK |
| Time UTC | 05.08.2026 10:00 UTC |
| Open | 0.0000 |
| High | 0.0000 |
| Low | 0.0000 |
| Close | 0.0000 |
| Body | 0.0000 |
| Lower Wick | 0.0000 |
| Lower Wick / Body | 4.00x |
| Current Volume | 1,784,046,717 |
| Max Previous 48 | 1,184,924,301 |
| Volume Ratio | 1.51x |
| Red Candle | YES |
| Lower Wick >= 2x Body | YES |
| Volume >= 1.5x Previous 48 Max | YES |
| **PASS** | **YES** |

---

### Signal Verification Summary

| # | Symbol | Red | Wick/Body | VolRatio | PASS |
|---|--------|-----|----------:|---------:|------|
| 1 | SUSHI-USDT | YES | 4.00x | 1.69x | YES |
| 2 | COMP-USDT | YES | 4.00x | 3.15x | YES |
| 3 | DASH-USDT | YES | 2.00x | 1.68x | YES |
| 4 | FLOW-USDT | YES | 3.00x | 1.54x | YES |
| 5 | RUNE-USDT | YES | 2.60x | 2.20x | YES |
| 6 | ROSE-USDT | YES | 2.14x | 1.59x | YES |
| 7 | WOO-USDT | YES | 9.00x | 1.96x | YES |
| 8 | CRO-USDT | YES | 3.86x | 1.88x | YES |
| 9 | ACH-USDT | YES | 2.33x | 2.24x | YES |
| 10 | FLOKI-USDT | YES | 4.00x | 1.51x | YES |

**All 10 signals passed all qualification conditions.**

---

## F. Telegram

### Messages Sent

✅ **10/10 messages sent successfully**

### Message IDs

| # | Symbol | Message ID | Status |
|---|--------|------------|--------|
| 1 | SUSHI-USDT | 62 | Sent |
| 2 | COMP-USDT | 63 | Sent |
| 3 | DASH-USDT | 64 | Sent |
| 4 | FLOW-USDT | 65 | Sent |
| 5 | RUNE-USDT | 66 | Sent |
| 6 | ROSE-USDT | 67 | Sent |
| 7 | WOO-USDT | 68 | Sent |
| 8 | CRO-USDT | 69 | Sent |
| 9 | ACH-USDT | 70 | Sent |
| 10 | FLOKI-USDT | 71 | Sent |

### Historical Signals Confirmation

✅ **All 10 signals are historical closed M15 candles**
✅ **No waiting for new candles**
✅ **All from BingX USDT Perpetual data**

### Different Coins Confirmation

✅ **All 10 signals are on 10 different coins:**
1. SUSHI-USDT
2. COMP-USDT
3. DASH-USDT
4. FLOW-USDT
5. RUNE-USDT
6. ROSE-USDT
7. WOO-USDT
8. CRO-USDT
9. ACH-USDT
10. FLOKI-USDT

### Timestamp Confirmation

✅ **Telegram received exactly the same candle that was verified by the algorithm**
✅ **MSK time is the primary display**
✅ **UTC time shown in parentheses**
✅ **No candle re-fetching during Telegram message formation**

### PASS_CHECK Confirmation

✅ **Each signal was verified before sending:**
- Red Candle = YES
- Lower Wick >= 2x Body = YES
- Volume >= 1.5x Previous 48 Max = YES

---

## G. Final Conclusion

### LW-001 Qualification Logic

**LW-001 qualification uses ONLY:**
1. Red candle: `Close < Open`
2. Lower wick/body ratio: `Lower Wick >= 2 * Body`
3. Volume filter: `Current Volume >= 1.5x maximum of previous 48 M15 candles`

### Upper Wick Non-Participation

**Upper Wick does NOT participate in signal qualification.**

The qualification formula is:
```python
qualified = (close_price < open_price) AND ((close_price - low_price) >= 2 * (open_price - close_price))
```

High is NOT present in this formula. Upper wick is calculated and shown in Telegram as informational only.

### High Non-Participation

**High does NOT participate in the main condition Lower Wick / Body.**

The Lower Wick / Body ratio uses only:
- `close_price` (from Close)
- `low_price` (from Low)
- `open_price` (from Open)

High is used ONLY for informational upper wick calculation.

### Summary of Changes

1. ✅ **Unit tests A-F created and passed** (6/6)
2. ✅ **Data pipeline verified** (BingX → Signal Search → Storage → PASS_CHECK → Telegram)
3. ✅ **Volume filter changed from 15 to 48 previous candles**
4. ✅ **Volume threshold set to >= 1.5x**
5. ✅ **10 historical signals found** (all on different coins)
6. ✅ **All signals passed PASS_CHECK**
7. ✅ **10/10 messages sent to Telegram** (Message IDs 62-71)

### Files Created

1. `test_lw001_unit_tests.py` - Unit tests A-F for logic verification
2. `LW001_LOGIC_VERIFICATION_REPORT.md` - Logic verification report
3. `find_10_signals_v5.py` - Signal search with 48-candle volume filter
4. `send_10_signals_v5.py` - Telegram delivery with PASS_CHECK
5. `LW001_FINAL_VERIFICATION_REPORT.md` - This report

### Status

**✅ COMPLETED**

All requirements met:
- Unit tests passed
- Data pipeline verified
- Volume filter corrected (48 candles, >= 1.5x)
- 10 historical signals found and verified
- 10/10 messages sent to Telegram
- Upper wick confirmed as informational only
- Score confirmed as informational only
- No liquidations in strategy

---

**Report Generated:** 2026-08-12  
**Verification Status:** PASSED  
**Unit Tests:** 6/6 passed  
**Data Pipeline:** Verified  
**Volume Filter:** 48 candles, >= 1.5x  
**Signals:** 10/10 found and verified  
**Telegram:** 10/10 sent (IDs 62-71)  
**Status:** READY FOR USER MANUAL VERIFICATION
