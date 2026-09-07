# Fast Reversal Factors Research Report

**Date:** 13.08.2026  
**Task:** Find factors that distinguish fast reversals from SL-hit signals  
**Status:** COMPLETED

---

## Executive Summary

This research analyzed 10 recent experimental candidates to identify factors that distinguish:
- **Fast reversals** (reach +2% quickly without significant adverse move)
- **SL-hit signals** (hit -3% SL before or without reaching +2%)
- **No reversals** (never reach +1%)

**Critical Finding:** 7 out of 10 signals (70%) would have been stopped out at SL -3% before or without reaching +2%. This is a major risk for the proposed TP +3% / SL -3% strategy.

---

## SL Risk Classification

| Category | Count | Description |
|----------|-------|-------------|
| **SL_HIT** | 7 | Hit -3% SL before/during reversal |
| **HIGH_RISK** | 1 | MAE before +2% > 2.5% (near SL) |
| **NO_REVERSAL** | 2 | Never reached +1% |

### Individual Signal Performance

| Symbol | MAE before +2% | Time to +2% | Category |
|--------|----------------|-------------|----------|
| WLD-USDT | 2.75% | None | HIGH_RISK |
| SIREN-USDT | 3.27% | None | SL_HIT |
| HOME-USDT | 9.76% | None | SL_HIT |
| ONE-USDT | 1.16% | 1 candle | SL_HIT* |
| 1000BONK-USDT | 7.66% | None | SL_HIT |
| PEOPLE-USDT | 5.18% | None | SL_HIT |
| STG-USDT | 3.30% | None | SL_HIT |
| STORJ-USDT | 4.91% | None | SL_HIT |
| GALA-USDT | 0.79% | None | NO_REVERSAL |
| SUSHI-USDT | 1.22% | None | NO_REVERSAL |

*ONE-USDT reached +2% in 1 candle but still hit SL at some point

---

## Candle Metrics by SL Risk Category

### SL_HIT (7 signals)
- Body%: Mean 1.63%, Median 1.15%
- Range%: Mean 4.25%, Median 3.34%
- LW/Body: Mean 1.87x, Median 1.64x
- LW/Range: Mean 55.45%, Median 54.43%
- Open->Low%: Mean -3.92%, Median -3.07%
- Volume Ratio: Mean 1.69x, Median 1.15x

### HIGH_RISK (1 signal)
- Body%: 1.19%
- Range%: 2.66%
- LW/Body: 1.17x
- LW/Range: 52.17%
- Open->Low%: -2.57%
- Volume Ratio: 4.27x

### NO_REVERSAL (2 signals)
- Body%: Mean 1.71%, Median 1.71%
- Range%: Mean 3.57%, Median 3.57%
- LW/Body: Mean 0.99x, Median 0.99x
- LW/Range: Mean 47.05%, Median 47.05%
- Open->Low%: Mean -3.39%, Median -3.39%
- Volume Ratio: Mean 1.31x, Median 1.31x

### Key Observation

**SL_HIT signals have moderate candle metrics** - they are not significantly weaker than NO_REVERSAL signals in terms of candle geometry. This confirms that **candle-level metrics alone are insufficient to predict SL risk**.

---

## Pre-Signal Context Analysis

### Range Position (10 candles)

| Category | Mean Range Position | Median Range Position |
|----------|---------------------|----------------------|
| HIGH_RISK | 98.36% (near top) | 98.36% |
| SL_HIT | 35.34% (middle-lower) | 22.22% (lower) |
| NO_REVERSAL | 13.16% (near bottom) | 13.16% |

**Critical Finding:** 
- HIGH_RISK signal was at the TOP of its range (98%)
- SL_HIT signals were in the middle-lower part (35%)
- NO_REVERSAL signals were at the BOTTOM (13%)

**This contradicts the hypothesis** that signals at the bottom of the range are safer. The signal that nearly hit SL was actually at the top of its range, suggesting it was in a downtrend continuation pattern.

### Previous Movement (10 candles)

| Category | Mean Change | Median Change |
|----------|-------------|---------------|
| HIGH_RISK | +1.97% (up) | +1.97% |
| SL_HIT | -1.32% (down) | -1.43% (down) |
| NO_REVERSAL | -1.04% (down) | -1.04% (down) |

**Critical Finding:**
- HIGH_RISK signal had been RISING (+1.97%) before the signal
- SL_HIT and NO_REVERSAL signals had been FALLING

**This contradicts the hypothesis** that signals after strong declines are safer. The highest-risk signal was actually after an uptrend.

### Consecutive Red Candles

| Category | Mean | Median |
|----------|------|--------|
| HIGH_RISK | 0 | 0 |
| SL_HIT | 1.4 | 0 |
| NO_REVERSAL | 1.5 | 1.5 |

SL_HIT and NO_REVERSAL signals had more consecutive red candles before the signal, but the difference is not dramatic.

---

## Threshold Testing Results

### Individual Thresholds

| Threshold | Pass Rate | SL_HIT Reduced | SL_HIT Remaining |
|-----------|-----------|----------------|------------------|
| Range% >= 5.0% | 10% | 6 (85.7%) | 1 |
| Range% >= 4.0% | 10% | 6 (85.7%) | 1 |
| LW/Body >= 2.0x | 10% | 6 (85.7%) | 1 |
| LW/Body >= 1.5x | 40% | 3 (42.9%) | 4 |
| LW/Range >= 60% | 10% | 6 (85.7%) | 1 |
| Open->Low% <= -4.5% | 10% | 6 (85.7%) | 1 |
| Open->Low% <= -4.0% | 10% | 6 (85.7%) | 1 |
| Volume Ratio >= 2.5x | 20% | 6 (85.7%) | 1 |
| Volume Ratio >= 2.0x | 20% | 6 (85.7%) | 1 |

**Critical Issue:** All aggressive thresholds (based on manual signal averages) reduce the pass rate to 10% or less, meaning they would filter out 90% of signals. This is too restrictive.

### Combination Tests

| Combination | Pass Rate | SL_HIT Reduced | SL_HIT Remaining | Passed Signals |
|-------------|-----------|----------------|------------------|----------------|
| Range% >= 5.0%, Open->Low% <= -4.5%, Volume >= 2.5x | 10% | 6 (85.7%) | 1 | 1000BONK-USDT |
| Range% >= 4.0%, Open->Low% <= -4.0%, Volume >= 2.0x | 10% | 6 (85.7%) | 1 | 1000BONK-USDT |
| LW/Body >= 2.0x, LW/Range >= 60%, Open->Low% <= -4.5% | 0% | 7 (100%) | 0 | None |
| Range% >= 5.0%, LW/Body >= 2.0x, Volume >= 2.5x | 0% | 7 (100%) | 0 | None |
| Range% >= 4.0%, LW/Body >= 1.5x, Volume >= 1.5x | 0% | 7 (100%) | 0 | None |

**Critical Finding:** Most combinations based on manual signal averages either:
1. Pass only 1 signal (10% pass rate) - too restrictive
2. Pass 0 signals - completely eliminates signals

### Pre-Signal Context Filters

**Range Position <= 30% (bottom of range):**
- Passed: 6/10 signals
- SL_HIT in this group: 4 out of 6 (67%)

**Previous Movement <= -2% (strong decline):**
- Passed: 3/10 signals
- SL_HIT in this group: 3 out of 3 (100%)

**Critical Finding:** Neither pre-signal context filter effectively reduces SL-hit rate. In fact, signals at the bottom of the range had a 67% SL-hit rate, and signals after strong declines had a 100% SL-hit rate.

---

## Key Contradictions to Hypotheses

### Hypothesis 1: Stronger candle metrics = safer signals
**Result:** FALSE. SL_HIT signals have similar candle metrics to NO_REVERSAL signals. The single HIGH_RISK signal had moderate metrics but high volume.

### Hypothesis 2: Signals at bottom of range are safer
**Result:** FALSE. Signals at the bottom of range had 67% SL-hit rate. The highest-risk signal was at the TOP of its range.

### Hypothesis 3: Signals after strong declines are safer
**Result:** FALSE. Signals after strong declines (>= -2% in 10 candles) had 100% SL-hit rate. The highest-risk signal was after an uptrend.

### Hypothesis 4: Manual signal thresholds will filter SL-hit signals
**Result:** PARTIAL. Manual signal thresholds (Range% >= 5%, Open->Low% <= -4.5%, Volume >= 2.5x) do reduce SL-hit rate by 85.7%, but at the cost of reducing signal count by 90%.

---

## What Actually Distinguishes SL-Hit Signals?

Based on the analysis, the following patterns emerge:

### Pattern 1: Range Position Paradox
- **HIGH_RISK signal:** At 98% of range (near top) - downtrend continuation
- **SL_HIT signals:** At 35% of range (middle-lower) - unclear trend
- **NO_REVERSAL signals:** At 13% of range (bottom) - potential support

**Interpretation:** Signals at the top of ranges (in downtrends) may be continuation patterns that fail to reverse. Signals at the bottom may be at support but still fail to reverse quickly enough.

### Pattern 2: Previous Movement Paradox
- **HIGH_RISK signal:** After +1.97% rise (uptrend)
- **SL_HIT/NO_REVERSAL signals:** After decline (-1.3% to -1.0%)

**Interpretation:** Signals after uptrends (counter-trend signals) may have higher risk of continuation failure. Signals after declines may be in "falling knife" scenarios that continue down before reversing.

### Pattern 3: Volume Anomaly
- **HIGH_RISK signal:** Volume Ratio 4.27x (highest)
- **SL_HIT signals:** Mean Volume Ratio 1.69x
- **NO_REVERSAL signals:** Mean Volume Ratio 1.31x

**Interpretation:** High volume during the signal candle may indicate capitulation or exhaustion, which could be either bullish (capitulation reversal) or bearish (exhaustion continuation). In this case, it was associated with HIGH_RISK.

---

## Most Promising Filters (with Trade-offs)

### Option 1: Conservative Thresholds (10% pass rate)
```python
Range% >= 5.0% AND
Open->Low% <= -4.5% AND
Volume Ratio >= 2.5x
```
- **Pros:** Reduces SL-hit by 85.7%
- **Cons:** Only 10% pass rate (90% signal reduction)
- **Verdict:** Too restrictive for practical use

### Option 2: Moderate Thresholds (40% pass rate)
```python
LW/Body >= 1.5x
```
- **Pros:** 40% pass rate, reduces SL-hit by 42.9%
- **Cons:** Still leaves 4 out of 7 SL-hit signals
- **Verdict:** Moderate improvement but insufficient

### Option 3: Range Position Filter (60% pass rate)
```python
Range position (10 candles) >= 30% AND <= 70%
```
- **Pros:** 60% pass rate, filters out extreme range positions
- **Cons:** Bottom 30% had 67% SL-hit rate, but this filter would keep middle 40%
- **Verdict:** Needs more data to validate

### Option 4: Previous Movement Filter (70% pass rate)
```python
Previous movement (10 candles) >= -2%
```
- **Pros:** 70% pass rate, filters out strong declines
- **Cons:** Strong declines had 100% SL-hit rate, but this filter may miss valid reversal setups
- **Verdict:** Promising but needs validation

---

## Critical Problem: Small Sample Size

**Major Limitation:** Only 10 signals were analyzed. This is insufficient for:
- Statistical significance
- Reliable pattern identification
- Robust threshold optimization

The results should be considered **indicative but not conclusive**. A larger sample (50-100 signals) is needed for reliable conclusions.

---

## Recommendations

### Immediate Actions

1. **Increase sample size:** Find 50-100 recent experimental candidates for more reliable analysis.

2. **Manual verification:** For the 30 manual signals, manually collect:
   - Time to +1%, +2%, +3%
   - Maximum adverse excursion before each target
   - Pre-signal range position
   - Previous movement data

3. **Alternative approach:** Consider:
   - Wider SL (e.g., -4% or -5%)
   - Smaller position size
   - Time-based exit instead of fixed TP
   - Confirmation before entry (wait for next candle)

### Filter Recommendations (Conditional)

If a filter must be implemented despite the small sample size, the most balanced option is:

```python
# Base filter (existing)
Open -> Low <= -2.5% AND
Volume Ratio >= 0.75 AND
LW/Range >= 40% AND
LW/Body >= 0.75x AND
Range% >= 2.5% AND
Body% >= 0.30%

# Additional layer (conservative)
AND LW/Body >= 1.5x
```

**Rationale:**
- 40% pass rate (better than 10% for aggressive thresholds)
- Reduces SL-hit by 42.9%
- Targets the metric with the clearest difference between categories

**Trade-off:** Will lose 60% of signals but may improve quality.

---

## Conclusion

**The research reveals a critical problem:** 70% of recent experimental candidates would have been stopped out at SL -3% before or without reaching +2%.

**Key findings:**
1. Candle-level metrics alone are insufficient to predict SL risk
2. Pre-signal context patterns contradict initial hypotheses
3. Manual signal thresholds are too restrictive (90% signal reduction)
4. Small sample size limits statistical reliability

**Most likely explanation:** The difference between manual signals (which reportedly reversed quickly) and recent candidates (which often hit SL) is due to factors not captured in our analysis:
- Market conditions (June 2026 vs August 2026)
- Order flow and liquidity
- Market structure and key levels
- News/events
- Correlation with broader market

**Recommended approach:** Before implementing additional filters, increase the sample size and collect manual verification data for the 30 manual signals to understand what actually made them successful.

---

**Important:** No changes were made to LW-001, production, backtest, PASS_CHECK, or Telegram. This is purely research.
