ìR# LW-001 Strategy Refinement Report

**Date:** 2026-08-08  
**Objective:** Thorough review and refinement of LW-001 strategy to ensure strict adherence to defined logic, decouple Score from signal qualification, and verify historical signal generation.

---

## Executive Summary

The LW-001 strategy has been successfully refined to:
1. Use only candle structure (wick/body ratio >= 1.5x) as the primary qualification criterion
2. Remove Score-based filtering - Score is now informational only
3. Update exchange support from Bybit to BingX
4. Verify all candle calculations (Body, Wicks, Ratios, Close Position)
5. Remove all liquidation-related logic
6. Find 10 historical candles matching the refined strategy

**Status:** âœ… **COMPLETE** - All tasks finished successfully.

---

## 1. Files Modified

### 1.1 `src/strategy/lw_001.py`

**Changes:**
- **Line 85:** Changed default `lower_wick_ratio` from 2.0 to 1.5
- **Lines 93-99:** Removed validation for `min_confidence_score` parameter
- **Line 119:** Changed exchange check from `[Exchange.BYBIT, Exchange("bybit_testnet")]` to `[Exchange.BINGX]`
- **Line 210:** Changed default `wick_ratio_threshold` from 2.0 to 1.5
- **Lines 320-322:** **Critical change** - Removed Score-based qualification:
  ```python
  # OLD:
  min_score = params.get("min_confidence_score", 80)
  qualified = final_score >= min_score
  
  # NEW:
  qualified = wick_body_ratio >= wick_ratio_threshold
  ```
- **Lines 327-336:** Updated explanation to reflect Score as informational only and include additional candle metrics

**Verification of Candle Calculations:**
- **Body:** `body_size = abs(close_price - open_price)` âœ…
- **Lower Wick:** `lower_wick = min(open_price, close_price) - low_price` âœ…
- **Upper Wick:** `upper_wick = high_price - max(open_price, close_price)` âœ…
- **Wick/Body Ratio:** `wick_body_ratio = lower_wick / body_size if body_size > 0 else 0.0` âœ…
- **Body/Range Ratio:** `body_ratio = body_size / candle_range if candle_range > 0 else 0.0` âœ…
- **Close Position:** `close_position = (close_price - low_price) / candle_range if candle_range > 0 else 0.0` âœ…

### 1.2 `config.yaml`

**Changes:**
- **Lines 56-57:** Removed `min_confidence_score: 80` parameter
- **Line 57:** Changed `lower_wick_ratio` from 2.0 to 1.5

### 1.3 `historical_backtest.py`

**Changes:**
- **Line 28:** Changed `lower_wick_ratio` from 2.0 to 1.5
- **Line 29:** Removed `min_confidence_score: 80` parameter

### 1.4 `find_historical_signals.py` (NEW FILE)

**Purpose:** Search historical BingX data for candles matching LW-001 criteria and send to Telegram.

**Features:**
- Loads 935 USDT Perpetual symbols from `usdt_perpetual_symbols.py`
- Searches last 30 days of M15 candle data
- Uses production LW-001 strategy class for evaluation
- Sends found signals to Telegram with specified format

---

## 2. Logic Removed

### 2.1 Score-Based Filtering

**Removed Logic:**
- `min_confidence_score` parameter validation in `validate_config()`
- `min_confidence_score` retrieval from config
- `qualified = final_score >= min_score` comparison
- Score threshold in explanation output

**Impact:** Signals now qualify **solely** based on candle structure (wick/body ratio >= 1.5x). Score is calculated and displayed but does not filter signals.

### 2.2 Liquidation-Related Logic

**Status:** Already removed in previous session. Verified no liquidation code remains in:
- `src/strategy/lw_001.py` - No liquidation references
- `src/models/market_event.py` - `StrategyData` no longer has liquidation fields
- `config.yaml` - No liquidation scoring parameters

### 2.3 Exchange Support

**Changed:** Exchange check updated from Bybit to BingX to match production data source.

---

## 3. Score System - New Role

### 3.1 Before Refinement
- Score was used as a **filter** - signals required `final_score >= 80`
- Score combined Lower Wick (70%) and Candle Confirmation (30%) scores
- Maximum possible score: 100 points

### 3.2 After Refinement
- Score is **informational only** - displayed in Telegram messages but does not affect qualification
- Qualification is based **exclusively** on `wick_body_ratio >= 1.5`
- Score calculation remains unchanged (70% wick + 30% confirmation)
- Score range: 0-100 points (for informational purposes)

### 3.3 Score Calculation (Unchanged)
```python
wick_score = 0-70 points (based on wick/body ratio tiers)
confirm_score = 0-30 points (based on body ratio and close position)
final_score = (wick_score * 0.7) + (confirm_score * 0.3)
```

---

## 4. Historical Signal Search Results

### 4.1 Search Parameters
- **Data Source:** BingX API
- **Symbols:** 935 USDT Perpetual (excluding TOP-20)
- **Timeframe:** M15
- **Period:** Last 30 days (2026-07-09 to 2026-08-08)
- **Qualification Criterion:** Wick/Body Ratio >= 1.5x
- **Target:** 10 signals

### 4.2 Results Found

**Total Signals Found:** 10  
**Symbol:** 0GUSDT  
**Date Range:** 2026-07-28 to 2026-07-29

| # | Date | Time (UTC) | Wick/Body | Body | Lower Wick | Upper Wick | Body/Range | Close Position | Score |
|---|------|------------|-----------|------|------------|------------|------------|----------------|-------|
| 1 | 2026-07-28 | 21:30:00 | 4.00x | 0.0001 | 0.0004 | 0.0007 | 0.08 | 0.42 | 53.5 |
| 2 | 2026-07-28 | 23:30:00 | 6.00x | 0.0001 | 0.0006 | 0.0002 | 0.11 | 0.78 | 53.5 |
| 3 | 2026-07-29 | 00:00:00 | 8.00x | 0.0002 | 0.0016 | 0.0010 | 0.07 | 0.64 | 53.5 |
| 4 | 2026-07-29 | 00:30:00 | 6.00x | 0.0002 | 0.0012 | 0.0007 | 0.10 | 0.57 | 52.0 |
| 5 | 2026-07-29 | 01:30:00 | 4.50x | 0.0002 | 0.0009 | 0.0007 | 0.11 | 0.61 | 53.5 |
| 6 | 2026-07-29 | 02:00:00 | 3.00x | 0.0003 | 0.0009 | 0.0004 | 0.19 | 0.75 | 46.5 |
| 7 | 2026-07-29 | 03:00:00 | 3.67x | 0.0003 | 0.0011 | 0.0003 | 0.18 | 0.82 | 55.0 |
| 8 | 2026-07-29 | 04:00:00 | 2.25x | 0.0004 | 0.0009 | 0.0003 | 0.25 | 0.81 | 42.5 |
| 9 | 2026-07-29 | 04:15:00 | 2.50x | 0.0006 | 0.0015 | 0.0006 | 0.22 | 0.56 | 45.0 |
| 10 | 2026-07-29 | 04:45:00 | 6.00x | 0.0001 | 0.0006 | 0.0006 | 0.08 | 0.54 | 53.5 |

### 4.3 Verification

All 10 signals:
- âœ… Have wick/body ratio >= 1.5x (range: 2.25x to 8.00x)
- âœ… Are from closed M15 candles
- âœ… Use only candle structure for qualification
- âœ… Have Score calculated but not used for filtering
- âœ… Are historical (not real-time)
- âœ… Contain no liquidation data

---

## 5. Telegram Delivery Status

### 5.1 Attempted Delivery
- **Status:** âœ… **SUCCESS** - All 10 signals sent successfully
- **Bot Token:** `8730872028:AAEYFDMfc-Fv9Pe0x7beZL14GP4Jb7cd2_M`
- **Chat ID:** `8307060083`
- **Bot Name:** CandlBing (@CandleBingx_bot)
- **Delivery Time:** 2026-08-08
- **Messages Sent:** 10/10 (100% success rate)

### 5.2 Message Format
Each Telegram message includes:
- Coin, Date, Time (UTC), Timeframe (M15)
- OHLC data (Open, High, Low, Close)
- Candle Structure (Body, Lower Wick, Upper Wick)
- Ratios (Wick/Body, Body/Range, Close Position)
- Score (marked as "informational only")
- **No liquidation data**

### 5.3 Delivery Details
- Signal #1: Message ID 3 - âœ… Delivered
- Signal #2: Message ID 4 - âœ… Delivered
- Signal #3: Message ID 5 - âœ… Delivered
- Signal #4: Message ID 6 - âœ… Delivered
- Signal #5: Message ID 7 - âœ… Delivered
- Signal #6: Message ID 8 - âœ… Delivered
- Signal #7: Message ID 9 - âœ… Delivered
- Signal #8: Message ID 10 - âœ… Delivered
- Signal #9: Message ID 11 - âœ… Delivered
- Signal #10: Message ID 12 - âœ… Delivered

---

## 6. Confirmations

### 6.1 Signal Qualification Based on Candle Structure Only
âœ… **Confirmed.** The qualification logic in `lw_001.py` line 322 is now:
```python
qualified = wick_body_ratio >= wick_ratio_threshold
```
Score is calculated but does not affect the `qualified` boolean.

### 6.2 Liquidations Completely Excluded
âœ… **Confirmed.** No liquidation-related code found in:
- Strategy implementation (`lw_001.py`)
- Market event model (`market_event.py`)
- Configuration (`config.yaml`)
- Historical backtest script

### 6.3 Production and Historical Use Same LW-001 Class
âœ… **Confirmed.** Both `find_historical_signals.py` and `historical_backtest.py` import and use:
```python
from strategy.lw_001 import LW001Strategy
```
The same class instance is used for both production and historical analysis.

### 6.4 Historical Candles Found (Not Real-Time)
âœ… **Confirmed.** The script searches historical data from BingX API with:
- Specific date range (last 30 days)
- Closed candles only (`confirm=True` in StrategyData)
- No real-time monitoring
- All found signals have timestamps in the past (July 2026)

---

## 7. Technical Details

### 7.1 Strategy Configuration
```yaml
strategies:
  LW-001:
    enabled: true
    timeframe: "15m"
    condition:
      lower_wick_ratio: 1.5  # Changed from 2.0
    scoring:
      lower_wick_weight: 70
      confirmation_weight: 30
      # ... scoring tiers (unchanged)
```

### 7.2 Candle Structure Verification
All calculations verified as mathematically correct:
- Body: Absolute difference between close and open
- Lower Wick: Distance from low to min(open, close)
- Upper Wick: Distance from max(open, close) to high
- Wick/Body: Lower wick divided by body (with zero-division protection)
- Body/Range: Body divided by total range (high - low)
- Close Position: Distance from low to close divided by range

### 7.3 Exchange Support
- **Previous:** Bybit (testnet and mainnet)
- **Current:** BingX only
- **Reason:** Production data migration to BingX completed in previous session

---

## 8. Next Steps (Awaiting User Confirmation)

1. âœ… **Review the 10 found signals** in Telegram to verify they match the expected LW-001 pattern
2. âœ… **Confirm strategy refinement** meets requirements
3. **Proceed to winrate analysis** (after user approval)
4. **Long-term historical testing** (after user approval)

---

## 9. Summary

The LW-001 strategy has been successfully refined according to all requirements:

- âœ… **Candle calculations verified** - All metrics computed correctly
- âœ… **Score decoupled from qualification** - Now informational only
- âœ… **Liquidations removed** - No traces remain in codebase
- âœ… **Exchange updated to BingX** - Matches production data source
- âœ… **Wick/Body threshold changed to 1.5x** - Per user requirements
- âœ… **10 historical signals found** - Using BingX data from last 30 days
- âœ… **All 10 signals sent to Telegram** - 100% delivery success rate

The strategy now operates with a single, clear qualification criterion: **lower wick must be at least 1.5 times the body size**. All other metrics are calculated and displayed but do not affect signal generation.
Û *cascade08Ûİ*cascade08İŞ *cascade08Şç*cascade08çè *cascade08èé*cascade08éê *cascade08êì*cascade08ìí *cascade08íî*cascade08îğ *cascade08ğó*cascade08óô *cascade08ôø*cascade08øù *cascade08ùú*cascade08úı *cascade08ış*cascade08şÿ *cascade08ÿ*cascade08ƒ *cascade08ƒ†*cascade08†‡ *cascade08‡‰*cascade08‰‡2 *cascade08‡2–2*cascade08–2™2 *cascade08™2œ2*cascade08œ22 *cascade0822*cascade082 2 *cascade08 2¡2*cascade08¡2¢2 *cascade08¢2£2*cascade08£2¥2 *cascade08¥2¦2*cascade08¦2¨2 *cascade08¨2©2*cascade08©2ª2 *cascade08ª2«2*cascade08«2­2 *cascade08­2±2*cascade08±2²2 *cascade08²2¹2*cascade08¹2»2*cascade08»2¼2 *cascade08¼2¾2 *cascade08¾2À2*cascade08À2Í2 *cascade08Í2Î2*cascade08Î2Ğ2 *cascade08Ğ2Ñ2*cascade08Ñ2Ò2 *cascade08Ò2Ó2*cascade08Ó2Ô2 *cascade08Ô2Ö2*cascade08Ö2Ù2 *cascade08Ù2Û2*cascade08Û2Ü2 *cascade08Ü2ß2*cascade08ß2à2 *cascade08à2â2*cascade08â2ã2 *cascade08ã2å2*cascade08å2æ2 *cascade08æ2é2*cascade08é2ê2 *cascade08ê2ğ2*cascade08ğ2ñ2 *cascade08ñ2õ2*cascade08õ2ö2 *cascade08ö2ú2*cascade08ú2œ3 *cascade08œ33*cascade0833 *cascade083£3*cascade08£3§3 *cascade08§3¨3 *cascade08¨3±3*cascade08±3²3 *cascade08²3µ3*cascade08µ3¶3 *cascade08¶3¸3*cascade08¸3º3 *cascade08º3¿3*cascade08¿3À3 *cascade08À3Á3*cascade08Á3Â3 *cascade08Â3Æ3*cascade08Æ3Ç3 *cascade08Ç3Ê3*cascade08Ê3Ë3 *cascade08Ë3Ì3*cascade08Ì3Í3 *cascade08Í3Ï3*cascade08Ï3Ğ3 *cascade08Ğ3Ó3*cascade08Ó3Ô3 *cascade08Ô3Õ3*cascade08Õ3Ö3 *cascade08Ö3ä3*cascade08ä3é3 *cascade08é3ê3*cascade08ê3ë3 *cascade08ë3ï3*cascade08ï3ğ3 *cascade08ğ3ö3*cascade08ö3ú3 *cascade08ú3ÿ3*cascade08ÿ3€4 *cascade08€44*cascade0844 *cascade0844*cascade0844 *cascade084“4*cascade08“4¬4 *cascade08¬4¯4*cascade08¯4Ê6 *cascade08Ê6Ë6*cascade08Ë6Í6 *cascade08Í6Õ6*cascade08Õ6Ö6 *cascade08Ö6×6*cascade08×6Ø6 *cascade08Ø6à6*cascade08à6á6 *cascade08á6ê6*cascade08ê6ë6 *cascade08ë6€7*cascade08€7‚7 *cascade08‚7†7*cascade08†7‡7 *cascade08‡7Š7*cascade08Š7‹7 *cascade08‹7“7*cascade08“7”7 *cascade08”7˜7*cascade08˜7™7 *cascade08™7 7*cascade08 7¡7 *cascade08¡7¤7*cascade08¤7¥7 *cascade08¥7¨7*cascade08¨7©7 *cascade08©7­7*cascade08­7®7 *cascade08®7°7*cascade08°7±7 *cascade08±7µ7*cascade08µ7¶7 *cascade08¶7·7*cascade08·7¸7 *cascade08¸7À7*cascade08À7Á7 *cascade08Á7Ñ7*cascade08Ñ7Ó7 *cascade08Ó7×7*cascade08×7Ø7 *cascade08Ø7Ú7*cascade08Ú7Û7 *cascade08Û7à7*cascade08à7á7 *cascade08á7ç7*cascade08ç7è7 *cascade08è7ë7*cascade08ë7ì7 *cascade08ì7ğ7*cascade08ğ7ñ7 *cascade08ñ7ò7*cascade08ò7ó7 *cascade08ó7ú7*cascade08ú7û7 *cascade08û7ˆ8*cascade08ˆ8‰8 *cascade08‰8‹8*cascade08‹8Œ8 *cascade08Œ88*cascade0888 *cascade088‘8*cascade08‘8’8 *cascade08’8¢8*cascade08¢8£8 *cascade08£8¦8*cascade08¦8§8 *cascade08§8ª8*cascade08ª8¬8 *cascade08¬8®8*cascade08®8¯8 *cascade08¯8·8*cascade08·8¹8 *cascade08¹8»8*cascade08»8¼8 *cascade08¼8Å8*cascade08Å8Æ8 *cascade08Æ8Ğ8*cascade08Ğ8Ñ8 *cascade08Ñ8Õ8*cascade08Õ8Ö8 *cascade08Ö8Ú8*cascade08Ú8Û8 *cascade08Û8ä8*cascade08ä8å8 *cascade08å8é8*cascade08é8ë8 *cascade08ë8ö8*cascade08ö8÷8 *cascade08÷8ü8*cascade08ü8ı8 *cascade08ı8ş8 *cascade08ş8‚9*cascade08‚9ƒ9 *cascade08ƒ9†9*cascade08†9ˆ9 *cascade08ˆ9”9*cascade08”9•9 *cascade08•9¡9*cascade08¡9¢9 *cascade08¢9£9*cascade08£9¤9 *cascade08¤9¨9*cascade08¨9©9 *cascade08©9ª9 *cascade08ª9±9*cascade08±9²9 *cascade08²9´9*cascade08´9µ9 *cascade08µ9º9*cascade08º9¼9 *cascade08¼9¿9*cascade08¿9Á9 *cascade08Á9Ã9*cascade08Ã9Ä9 *cascade08Ä9Î9*cascade08Î9Ğ9 *cascade08Ğ9Ò9*cascade08Ò9Ó9 *cascade08Ó9Û9*cascade08Û9Ü9 *cascade08Ü9İ9*cascade08İ9Ş9 *cascade08Ş9ä9*cascade08ä9å9 *cascade08å9í9*cascade08í9î9 *cascade08î9‚:*cascade08‚:¸J *cascade08¸J»J*cascade08»JÜJ *cascade08ÜJèJ*cascade08èJ™K *cascade08™KšK*cascade08šKœK *cascade08œK K*cascade08 KÓK *cascade08ÓKÔK*cascade08ÔKŒL *cascade08ŒLL*cascade08LÑP *cascade08ÑPÔP*cascade08ÔP×P *cascade08×PîP*cascade08îPöP *cascade08öPÿP*cascade08ÿP‰Q *cascade08‰QŠQ*cascade08ŠQ‹Q *cascade08‹QQ*cascade08QQ *cascade08QQ*cascade08Q‘Q *cascade08‘Q’Q*cascade08’QìR *cascade082Vfile:///C:/Users/user/Documents/Default%20Project/EVRECONSE/LW001_REFINEMENT_REPORT.md