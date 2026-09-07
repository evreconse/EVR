# LW-001 Canonical Specification

**Version:** 1.0  
**Status:** VALIDATED  
**Last Updated:** 2026-08-19

---

## 1. Purpose

LW-001 is a candlestick pattern detection strategy that identifies potential bullish reversal signals based on long lower wick patterns on 15-minute timeframe.

---

## 2. Timeframe

- **Primary Timeframe:** 15 minutes (M15)
- **Exchange:** BingX
- **Candle Type:** Historical closed candles only

---

## 3. Metric Formulas

### 3.1 Range

**Formula:** `((High - Low) / Open) * 100`

**Unit:** % (percentage points)

**Internal Storage:** Numeric value (e.g., 6.00 for 6%)

**Display:** Add "%" suffix (e.g., "6.00%")

**Example:**
- Open = 100.0
- High = 106.0
- Low = 94.0
- Range = (106 - 94) / 100 * 100 = 12.00%

---

### 3.2 Body

**Formula:** `(abs(Close - Open) / Open) * 100`

**Unit:** % (percentage points)

**Internal Storage:** Numeric value (e.g., 1.90 for 1.9%)

**Display:** Add "%" suffix (e.g., "1.90%")

**Example:**
- Open = 100.0
- Close = 102.0
- Body = abs(102 - 100) / 100 * 100 = 2.00%

---

### 3.3 Lower Wick

**Formula:** `min(Open, Close) - Low`

**Unit:** Price units (same as input prices)

**Internal Storage:** Numeric value

**Display:** Same as input

**Example:**
- Open = 100.0
- Close = 102.0
- Low = 94.0
- Lower Wick = min(100, 102) - 94 = 6.0

---

### 3.4 LW / Body

**Formula:** `Lower_Wick / abs(Close - Open)`

**Unit:** x (ratio)

**Internal Storage:** Numeric value (e.g., 2.50 for 2.5x)

**Display:** Add "x" suffix (e.g., "2.50x")

**Example:**
- Lower Wick = 6.0
- Body = 2.0
- LW/Body = 6.0 / 2.0 = 3.00x

---

### 3.5 LW / Range

**Formula:** `(Lower_Wick / (High - Low)) * 100`

**Unit:** % (percentage points)

**Internal Storage:** Numeric value (e.g., 63.00 for 63%)

**Display:** Add "%" suffix (e.g., "63.00%")

**Example:**
- Lower Wick = 6.0
- Range = 12.0
- LW/Range = 6.0 / 12.0 * 100 = 50.00%

---

### 3.6 Open to Low

**Formula:** `((Low - Open) / Open) * 100`

**Unit:** % (percentage points)

**Internal Storage:** Numeric value (e.g., -5.00 for -5%)

**Display:** Add "%" suffix (e.g., "-5.00%")

**Example:**
- Open = 100.0
- Low = 95.0
- Open→Low = (95 - 100) / 100 * 100 = -5.00%

**Critical Note:** Formula is `(Low - Open) / Open`, NOT `(Open - Low) / Open`

---

### 3.7 Volume Ratio

**Formula:** `Candle_Volume / Reference_Average_Volume`

**Unit:** x (ratio)

**Internal Storage:** Numeric value (e.g., 2.60 for 2.6x)

**Display:** Add "x" suffix (e.g., "2.60x")

**Reference Average Volume Definition:**
- Calculated from the last 20 candles BEFORE the signal candle
- Does NOT include the signal candle itself
- If reference average is 0, Volume Ratio is 0

**Example:**
- Candle Volume = 1000.0
- Average Volume (last 20) = 500.0
- Volume Ratio = 1000 / 500 = 2.00x

---

## 4. Internal Format Standards

### 4.1 Percentage Metrics

**Metrics:** Range, Body, LW/Range, Open→Low

**Internal Format:** Numeric value in percentage points
- Range: 6.00 (not 0.06)
- Body: 1.90 (not 0.019)
- LW/Range: 63.00 (not 0.63)
- Open→Low: -5.00 (not -0.05)

**Display Format:** Add "%" suffix
- "6.00%"
- "1.90%"
- "63.00%"
- "-5.00%"

---

### 4.2 Ratio Metrics

**Metrics:** LW/Body, Volume Ratio

**Internal Format:** Numeric value as ratio
- LW/Body: 2.50 (not 250%)
- Volume Ratio: 2.60 (not 260%)

**Display Format:** Add "x" suffix
- "2.50x"
- "2.60x"

---

## 5. Thresholds

### 5.1 Current Strict Thresholds

| Metric | Threshold | Operator | Unit |
|--------|-----------|----------|------|
| Range | 6.0 | >= | % |
| Body | 1.9 | >= | % |
| LW/Body | 2.5 | >= | x |
| LW/Range | 63.0 | >= | % |
| Open→Low | -5.0 | <= | % |
| Volume Ratio | 2.6 | >= | x |

---

### 5.2 Condition Logic

**All 6 conditions use AND logic**

A candle is a valid signal ONLY if ALL 6 conditions pass simultaneously.

No deviation-based or approximate matching allowed.

---

## 6. Unit Validation

### 6.1 Validation Rule

Before any metric-threshold comparison, the system validates:

```python
metric.unit == threshold.unit
```

### 6.2 Validation Failure

If units do not match, the pipeline stops with error:

```
UNIT_MISMATCH

Metric: LW/Range
Metric unit: fraction
Threshold: 63%
Expected unit: %
Pipeline stopped.
```

### 6.3 No Silent Conversions

The system does NOT automatically convert between units:
- 0.63 → 63 (NOT automatic)
- 2.5 → 250% (NOT automatic)
- 0.06 → 6% (NOT automatic)

All conversions must be explicit and tested.

---

## 7. Candle Definition

**Candle:** A single 15-minute OHLCV candle

**Fields:**
- Open: Opening price
- High: Highest price
- Low: Lowest price
- Close: Closing price
- Volume: Trading volume

**Requirement:** Candle must be closed/confirmed before evaluation

---

## 8. Lower Wick Definition

**Lower Wick:** The lower shadow of the candle

**Formula:** `min(Open, Close) - Low`

**Interpretation:** The distance from the lowest point of the candle to the lower boundary of the candle body

---

## 9. Implementation

### 9.1 Canonical Implementation

**File:** `LW001_METRIC_SPEC.py`

**Functions:**
- `calculate_range_pct()`
- `calculate_body_pct()`
- `calculate_lower_wick()`
- `calculate_lower_wick_body_ratio()`
- `calculate_lower_wick_range_pct()`
- `calculate_open_to_low_pct()`
- `calculate_volume_ratio()`
- `calculate_all_metrics()`
- `validate_metric_units()`
- `check_all_conditions()`

**Requirement:** All metric calculations must use these canonical functions.

---

### 9.2 Single Source of Truth

**Rule:** Each metric is calculated in ONE place only.

**Canonical Location:** `LW001_METRIC_SPEC.py`

**Other Components:** Must use canonical functions, not duplicate formulas.

---

## 10. Test Coverage

### 10.1 Unit Tests

**File:** `test_lw001_metrics.py`

**Tests:**
- Range percentage calculation
- Body percentage calculation
- Lower Wick calculation
- LW/Body ratio calculation
- LW/Range percentage calculation
- Open→Low percentage calculation
- Volume Ratio calculation
- Unit validation
- All metrics calculation

**Status:** ✅ All tests PASS

---

### 10.2 Integration Tests

**File:** `test_integration_lw001.py`

**Tests:**
- Synthetic passing candle (all 6 conditions PASS)
- Synthetic failing candles (each condition FAIL individually)

**Status:** ✅ All tests PASS

---

## 11. Historical Data Audit

### 11.1 Legacy Results

**File:** `new_historical_signals.json`

**Signal Count:** 3,640 signals

**Status:** ❌ INVALIDATED_LEGACY_RESULTS

---

### 11.2 Audit Findings

**Audit File:** `audit_old_signals.py`

**Sample Size:** 50 random signals

**Discrepancies:**
- Range: 6.0% (3/50)
- Body: 2.0% (1/50)
- LW/Body: 0.0% (0/50)
- LW/Range: 0.0% (0/50)
- Open→Low: 0.0% (0/50)

---

### 11.3 Root Cause

**Issue:** Previous metric pipeline used Close as denominator for Range and Body instead of Open.

**Impact:** Range and Body values were slightly incorrect, leading to 3,640 signals being found with incorrect calculations.

**Resolution:** All old results invalidated. New searches must use canonical formulas.

---

## 12. Changelog

### Version 1.0 (2026-08-19)

**Initial Release:**
- Created canonical metric specification
- Defined all formulas with Open as denominator for Range and Body
- Implemented unit validation
- Created unit tests (all PASS)
- Created integration tests (all PASS)
- Audited old 3,640 signals (INVALIDATED due to formula errors)
- Fixed Range and Body calculations to use Open instead of Close

---

## 13. Validation Status

**LW-001 Status:** ✅ VALIDATED

**Validation Summary:**
- ✅ All formulas correct
- ✅ All units defined
- ✅ Unit validation implemented
- ✅ Unit tests PASS
- ✅ Integration tests PASS
- ✅ Historical audit complete
- ✅ Legacy results invalidated

**Ready for:** Control test with 10 signals

---

## 14. Usage Guidelines

### 14.1 For New Code

1. Import from `LW001_METRIC_SPEC.py`
2. Use `calculate_all_metrics()` for metric calculation
3. Use `check_all_conditions()` for signal validation
4. Never duplicate metric formulas
5. Always validate units before comparison

---

### 14.2 For Historical Searches

1. Use canonical formulas only
2. Recalculate all metrics from OHLCV
3. Do not use saved metric values from legacy data
4. Apply unit validation before threshold checks
5. Use AND logic for all 6 conditions

---

### 14.3 For Telegram Formatting

1. Display metrics with proper units (% or x)
2. Show threshold comparisons
3. Indicate PASS/FAIL for each condition
4. Include OHLCV data for verification
5. Use canonical metric values

---

## 15. Contact

**Maintainer:** EVRECONSE Project  
**Documentation Version:** 1.0  
**Last Review:** 2026-08-19
