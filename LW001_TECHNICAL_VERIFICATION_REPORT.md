# LW-001 Technical Verification Report

**Date:** 2026-08-11  
**Task:** Verify LW-001 qualification logic and confirm upper wick/score do not affect qualification

---

## 1. Qualification Logic Location

### File: `src/strategy/lw_001.py`

**Lines 320-324:**
```python
# LW-001 Qualification: RED candle AND Lower Wick / Body >= 2.0
# Score is informational only and does NOT filter signals
qualified = is_red and wick_body_ratio >= wick_ratio_threshold
```

**Variables Used in Qualification:**
- `is_red` - Boolean: `close_price < open_price`
- `wick_body_ratio` - Float: `lower_wick / body`
- `wick_ratio_threshold` - Float: 2.0 (from config)

**Variables NOT Used in Qualification:**
- `upper_wick` - Calculated but NOT used in qualification
- `score` - Calculated but NOT used in qualification
- `body_ratio` - Calculated but NOT used in qualification
- `close_position` - Calculated but NOT used in qualification

---

## 2. Variable Usage Analysis

### Variables That Participate in Qualification

| Variable | Location | Calculation | Used in Qualification |
|----------|----------|-------------|---------------------|
| `is_red` | Line 187 | `close_price < open_price` | YES |
| `wick_body_ratio` | Line 195 | `lower_wick / body` | YES |
| `wick_ratio_threshold` | Line 212 | From config (default 2.0) | YES |

### Variables That Do NOT Participate in Qualification

| Variable | Location | Calculation | Used in Qualification |
|----------|----------|-------------|---------------------|
| `upper_wick` | Line 190 | `high_price - max(open_price, close_price)` | NO (informational only) |
| `body` | Line 189 | `abs(close_price - open_price)` | NO (used to calculate ratio) |
| `lower_wick` | Line 191 | `close_price - low_price` | NO (used to calculate ratio) |
| `candle_range` | Line 192 | `high_price - low_price` | NO (informational only) |
| `body_ratio` | Line 198 | `body / candle_range` | NO (informational only) |
| `close_position` | Line 201 | `(close_price - low_price) / candle_range` | NO (informational only) |
| `wick_score` | Line 246-273 | Scoring calculation | NO (informational only) |
| `confirm_score` | Line 277-305 | Scoring calculation | NO (informational only) |
| `total_score` | Line 314-320 | Weighted score | NO (informational only) |
| `final_score` | Line 320 | `min(total_score, max_score)` | NO (informational only) |

---

## 3. Upper Wick Usage Verification

### Where Upper Wick is Calculated

**File: `src/strategy/lw_001.py`**
- Line 190: `upper_wick = high_price - max(open_price, close_price)`

### Where Upper Wick is Used

**File: `src/strategy/lw_001.py`**
- Line 336: Displayed in explanation string (informational only)
- Line 388: Recalculated in event_pipeline for Telegram message (informational only)
- Line 414: Displayed in Telegram message (informational only)

### Confirmation

**Upper Wick is NOT used in qualification logic anywhere in the codebase.**

The qualification formula at line 324 uses only:
```python
qualified = is_red and wick_body_ratio >= wick_ratio_threshold
```

Upper wick is calculated and displayed for informational purposes only.

---

## 4. Score Usage Verification

### Where Score is Calculated

**File: `src/strategy/lw_001.py`**
- Lines 246-273: `wick_score` calculation (0-70 points)
- Lines 277-305: `confirm_score` calculation (0-30 points)
- Lines 314-320: `total_score` weighted calculation
- Line 320: `final_score = min(total_score, max_score)`

### Where Score is Used

**File: `src/strategy/lw_001.py`**
- Line 331: Displayed in explanation string (informational only)
- Line 344: Returned in StrategyResult (informational only)

**File: `src/event_engine/event_pipeline.py`**
- Line 369: Notification condition checks `context.status == "qualified"` (NOT score)
- Line 362: Score logged for debugging (informational only)

### Confirmation

**Score is NOT used in qualification logic anywhere in the codebase.**

The notification pipeline at line 369 checks:
```python
if context.status == "qualified":
```

It does NOT check:
```python
if context.confidence_score >= 80.0:  # This was removed
```

Score is calculated and displayed for informational purposes only.

---

## 5. Exact Qualification Formula

### Implementation in Code

**File: `src/strategy/lw_001.py`, Lines 186-195, 212, 324**

```python
# Step 1: Check if red candle
is_red = close_price < open_price

# Step 2: Calculate body (absolute value)
body = abs(close_price - open_price)

# Step 3: Calculate lower wick
lower_wick = close_price - low_price

# Step 4: Calculate ratio
wick_body_ratio = lower_wick / body if body > 0 else 0.0

# Step 5: Get threshold from config
wick_ratio_threshold = condition.get("lower_wick_ratio", 2.0)

# Step 6: Qualification
qualified = is_red and wick_body_ratio >= wick_ratio_threshold
```

### Mathematical Formula

```
qualified = (Close < Open) AND ((Close - Low) / (Open - Close) >= 2.0)
```

### For Red Candles Specifically

```
Body = Open - Close
Lower Wick = Close - Low
Ratio = Lower Wick / Body
Qualified = (Ratio >= 2.0)
```

---

## 6. Unit Test Results

### Test File: `test_lw001_simple_formula.py`

**All 6 tests PASSED:**

| Test | Description | Expected | Result | Status |
|------|-------------|----------|--------|--------|
| Test 1 | Basic hammer (2x ratio) | PASS | PASS | ✅ |
| Test 2 | Insufficient lower wick (1x) | FAIL | FAIL | ✅ |
| Test 3 | Huge upper wick ignored | PASS | PASS | ✅ |
| Test 4 | Green candle rejected | FAIL | FAIL | ✅ |
| Test 5 | Strong hammer (3x ratio) | PASS | PASS | ✅ |
| Test 6 | Doji (no body) rejected | FAIL | FAIL | ✅ |

### Key Confirmations from Tests

✅ **Test 3 Confirmation:** A red candle with Open=100, Close=99, Low=97, High=150 (huge upper wick of 50) PASSES because upper wick is ignored in qualification.

✅ **Test 4 Confirmation:** A green candle with large lower wick FAILS because only red candles are considered.

✅ **Test 6 Confirmation:** A doji with no body FAILS because ratio cannot be calculated when body=0.

---

## 7. Code Search Results

### Files Searched

All Python files in `src/` directory were searched for:
- `upper_wick`
- `lower_wick`
- `wick_ratio`
- `wick_body_ratio`
- `body`
- `qualified`
- `score`

### Key Findings

1. **`src/strategy/lw_001.py`**
   - `upper_wick`: Calculated line 190, used in explanation line 336 (NOT in qualification)
   - `lower_wick`: Calculated line 191, used to calculate ratio line 195
   - `wick_body_ratio`: Calculated line 195, used in qualification line 324
   - `qualified`: Set at line 324 based on `is_red and wick_body_ratio >= wick_ratio_threshold`
   - `score`: Calculated lines 314-320, NOT used in qualification

2. **`src/event_engine/event_pipeline.py`**
   - `upper_wick`: Recalculated line 388 for Telegram message (informational only)
   - `lower_wick`: Recalculated line 389 for Telegram message (informational only)
   - `qualified`: Checked at line 369 for notification (`context.status == "qualified"`)
   - `score`: Logged at line 362, NOT used for notification filtering

3. **No other files** use these variables in qualification logic.

---

## 8. Notification Pipeline Verification

### File: `src/event_engine/event_pipeline.py`

**Line 369 - Notification Condition:**
```python
if context.status == "qualified":
    logger.info(f"[PIPELINE] Notifier stage: Event qualified for notification (status=qualified)")
```

**Previous (Removed) Code:**
```python
# This was removed - score filtering is disabled
# if context.confidence_score and context.confidence_score >= 80.0:
```

**Confirmation:**
- Notifications are sent based on `status == "qualified"`, NOT based on score
- Score threshold filtering has been removed from the notification pipeline

---

## 9. Final Qualification Formula Confirmation

### Exact Formula Implemented

```python
qualified = (close_price < open_price) and ((close_price - low_price) / (open_price - close_price) >= 2.0)
```

### Variables in Formula

1. **`close_price < open_price`** - Red candle check
2. **`close_price - low_price`** - Lower wick calculation
3. **`open_price - close_price`** - Body calculation
4. **`>= 2.0`** - Threshold comparison

### Variables NOT in Formula

- ❌ `high_price` (upper wick source)
- ❌ `upper_wick`
- ❌ `score`
- ❌ `confidence_score`
- ❌ `volume`
- ❌ `body_ratio`
- ❌ `close_position`

---

## 10. Summary

### Qualification Logic Status

✅ **CORRECT** - The qualification logic uses only:
- Red candle check (`Close < Open`)
- Lower wick / body ratio (`>= 2.0`)

### Upper Wick Status

✅ **CONFIRMED** - Upper wick is calculated but NOT used in qualification:
- Calculated for informational display
- Shown in Telegram messages
- Does NOT affect qualification

### Score Status

✅ **CONFIRMED** - Score is calculated but NOT used in qualification:
- Calculated for informational display
- Shown in explanation strings
- Notification pipeline checks `status == "qualified"`, NOT score
- Does NOT affect qualification

### Unit Test Status

✅ **ALL PASSED** - 6/6 unit tests confirm:
- Formula works correctly
- Upper wick is ignored
- Green candles are rejected
- Dojis are rejected
- Ratio threshold is exactly 2.0

### Code Changes Required

**NONE** - The qualification logic is already correct.

The formula implemented in `src/strategy/lw_001.py` line 324 is:
```python
qualified = is_red and wick_body_ratio >= wick_ratio_threshold
```

Which translates to:
```python
qualified = (Close < Open) AND ((Close - Low) / (Open - Close) >= 2.0)
```

This matches the user's exact specification.

---

## 11. Next Steps

Since the qualification logic is verified as correct, the next steps are:

1. Find NEW 10 historical signals using the verified formula
2. Send NEW 10 signals to Telegram with MSK time
3. Create final completion report

**No code changes are required to the qualification logic.**

---

**Report Generated:** 2026-08-11  
**Verification Status:** PASSED  
**Formula Verified:** qualified = (Close < Open) AND ((Close - Low) / (Open - Close) >= 2.0)
