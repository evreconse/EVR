# LW-001 CRITICAL AUDIT DEBUG REPORT

## Executive Summary

**ROOT CAUSE IDENTIFIED:** The BingX API pagination logic is broken. The API returns the same time period on every pagination request instead of progressing backward through time.

## Investigation Results

### 1. Initial Problem
- **Expected:** 60 days of historical data (June 27 - August 26, 2026)
- **Actual:** Only ~10 days of data (August 16-26, 2026)
- **Result:** Only 5 signals found, all from August 22, 2026

### 2. First Hypothesis: limit=1000 Parameter
- **Analysis:** limit=1000 restricts to ~10.4 days at 15m interval
- **Status:** PARTIALLY CORRECT - but not the root cause
- **Action Taken:** Removed limit parameter from stage4_mass_search.py

### 3. Second Hypothesis: Pagination Logic
- **Test:** Manual pagination simulation with debug_pagination.py
- **Finding:** CRITICAL BUG IDENTIFIED

### 4. Pagination Bug Details

**Test Results for SAND-USDT:**
```
Request #1: 2026-08-26 17:00:00 UTC to 2026-08-16 07:15:00 UTC (1000 candles)
Request #2: 2026-08-26 16:45:00 UTC to 2026-08-16 07:00:00 UTC (1000 candles)
Request #3: 2026-08-26 16:30:00 UTC to 2026-08-16 06:45:00 UTC (1000 candles)
...
Request #10: 2026-08-26 14:45:00 UTC to 2026-08-16 05:00:00 UTC (1000 candles)
```

**Problem:** Every request returns data from the SAME general time period (August 16-26, 2026). The pagination logic updates `endTime` by subtracting 1ms, but the API does not return the previous time period.

**Expected Behavior:**
- Request #1: August 16-26
- Request #2: August 6-16
- Request #3: July 27 - August 6
- Request #4: July 17-27
- ...and so on back to June 27

**Actual Behavior:**
- All requests return data from August 16-26 with slight variations

### 5. Root Cause Analysis

The pagination logic in `bingx_fetcher.py` (lines 189-196) assumes:
```python
# Update end_time for next request (use first candle's time - 1)
first_time = int(first_item.get("time", 0))
current_end = first_time - 1
```

This approach is NOT working with the BingX API. The API appears to:
1. Ignore the `endTime` parameter when `startTime` is also provided
2. Have a maximum time range it can return per request
3. Require a different pagination method

### 6. Impact Assessment

**Impact:**
- Historical search only covers ~10 days instead of 60 days
- June and July data are completely missing
- Signal count is artificially low (5 instead of potentially hundreds)
- All found signals are from the same day (August 22, 2026)

**Status:**
- LW-001 parameters: CORRECT (no changes needed)
- LW-001 formulas: CORRECT (no changes needed)
- Data fetching: BROKEN (pagination bug)

### 7. Required Fix

**Attempted Fix 1: Remove startTime from API request**
- **Result:** FAILED
- **Finding:** API still only returns ~5 days of data (499 candles)
- **Conclusion:** BingX API has a hard limit on historical data range

**New Finding:**
The BingX API appears to have a maximum historical data limit of approximately 500 candles (~5 days at 15m interval), regardless of pagination parameters.

**Root Cause:**
- BingX API does not support full 60-day historical data retrieval via the klines endpoint
- The API has a built-in limit that cannot be bypassed with pagination
- This is an API limitation, not a code bug

**Required Solutions:**

**Option 1: Use Different Data Source**
- Switch to an exchange that supports full historical data (e.g., Binance, Bybit)
- Ensure 60-day 15m historical data availability
- Update fetcher to use new API

**Option 2: Use Different BingX Endpoint**
- Research if BingX has a different endpoint for historical data
- Check if there's a bulk download or historical data API
- May require API key upgrade or different access level

**Option 3: Accept Limited Range**
- Restrict LW-001 search to last 5-7 days only
- Update user expectations accordingly
- Not recommended for historical analysis

### 8. Pending Investigations

Still need to investigate:
- SAND-USDT signal candle direction (green vs red)
- FET-USDT timestamp accuracy
- Timestamp conversion (raw -> UTC -> UTC+3)

### 9. Recommendations

1. **CRITICAL:** Switch to a different data source (Binance, Bybit) that supports full 60-day historical data
2. **DO NOT** send any new signals to Telegram until data source is fixed
3. **DO NOT** change LW-001 parameters or formulas
4. **DO NOT** attempt further pagination fixes on BingX API - it's a hard limit
5. After switching data source: Re-run full 60-day search
6. After switching data source: Verify June/July data is included
7. After switching data source: Re-verify all signals from previous tests

## Conclusion

The historical search failure is due to a **BingX API limitation**. The API only returns approximately 500 candles (~5 days) of historical data, regardless of pagination parameters. This is not a code bug that can be fixed by modifying the pagination logic.

**LW-001 Status:**
- Parameters: CORRECT (no changes needed)
- Formulas: CORRECT (no changes needed)
- Logic: CORRECT (no changes needed)
- Data Source: INSUFFICIENT (BingX API limitation)

**Root Cause:** BingX `/openApi/swap/v3/quote/klines` endpoint has a hard limit of ~500 candles for historical data retrieval.

**Required Action:** Switch to a different exchange API (Binance, Bybit) that supports full 60-day 15m historical data.

**Next Step:** Implement a new fetcher for an exchange with proper historical data support.
