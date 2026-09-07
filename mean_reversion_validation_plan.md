# Mean-Reversion Hypothesis Validation Plan

**Date:** 15.08.2026  
**Task:** Validate mean-reversion/bounce hypothesis on large independent sample  
**Target Sample:** 50+ coins × 2-3 signals = 100-150+ signals  
**Time Period:** Last 60 days  
**Model:** TP +3% / SL -3%  
**Status:** PLANNING

---

## Background

Previous deep context research revealed a counterintuitive finding: LW-001 strategy appears to work as **mean-reversion/bounce**, not continuation/pullback.

### New Hypothesis
> **Positive PM10 on 15m + Downtrend on higher timeframes → Short-term bounce → Price reaches +2-3% quickly**

### Key Pattern from Previous Research
`PM10 >= 0 AND 1H Direction == DOWN` achieved 100% FAST, 0% SL, 100% TP (4 signals)

**But:** Sample was only 36 signals from 12 symbols. Overfitting test showed 70.8 pp variance between subsamples.

---

## Research Objective

Validate the mean-reversion hypothesis on a large independent sample to determine if the pattern is reproducible across diverse coins.

---

## Sample Requirements

- **Minimum:** 50 different coins
- **Signals per coin:** 2-3 (target)
- **Target total:** 100-150 signals
- **Time period:** Last 60 days
- **Model:** TP +3% / SL -3%
- **Constraint:** No changes to LW-001, production, backtest, PASS_CHECK, or Telegram

**Important:** If a coin is unavailable, do NOT replace with artificial data. Simply document the availability issue.

---

## Filters to Test

### 1. Baseline
No additional filter (current base filter only)

### 2. PM10 >= 0
Previous candidate from earlier research

### 3. PM10 >= 0.5%
Current candidate for simple filter

### 4. PM10 >= 0 AND 1H Direction == DOWN
New mean-reversion hypothesis

### 5. PM10 >= 0.5% AND 1H Direction == DOWN
Stricter variant of mean-reversion hypothesis

---

## Features to Extract for Each Signal

### Pre-Signal Context
- `previous_movement_10` (PM10)
- `previous_movement_20` (PM20)
- `short_term_direction` (5-candle direction)
- `range_position_20` (position in 20-candle range)
- `ema_21_slope` (EMA21 slope)
- `price_above_ema_21` (price position relative to EMA21)

### Higher Timeframe Context
- `1h_direction` (UP/DOWN/SIDEWAYS)
- `4h_direction` (UP/DOWN/SIDEWAYS)
- `1d_direction` (UP/DOWN/SIDEWAYS)
- `1h_pm10` (1H PM10)
- `4h_pm10` (4H PM10)
- `1d_pm10` (1D PM10)

### Post-Signal Performance
- MAE (Max Adverse Excursion)
- Time to +2% (candles)
- Time to +3% (candles)
- Hit TP before SL (boolean)
- Hit SL before TP (boolean)
- Result category (FAST/SLOW/SL_HIT/NO_REVERSAL)

---

## Analysis Requirements

### Overall Metrics
For each filter, calculate:
- Total signals
- Pass rate
- FAST %
- SLOW %
- SL_HIT %
- NO_REVERSAL %
- TP before SL %
- SL before TP %
- Average MAE
- Average time to +2%
- Average time to +3%

### Per-Coin Stability (Critical)
For each coin, calculate:
- Number of signals
- TP %
- SL %
- Average MAE
- Average time to +2%
- Average time to +3%

### Variance Analysis
- Split coins into two groups (odd/even index)
- Calculate variance between groups
- Assess stability across different coin sets

### Confidence Intervals
- Calculate 95% confidence intervals for key metrics where sample size permits

---

## Success Criteria

The hypothesis will be considered validated if ALL three conditions are met:

1. **TP +3% before SL -3% is noticeably higher than baseline**
2. **SL rate is noticeably lower than baseline**
3. **Results persist across most different coins** (not created by a few lucky symbols)

### Specific Thresholds
- **TP improvement:** At least +15 percentage points over baseline
- **SL reduction:** At least -15 percentage points over baseline
- **Stability:** Variance between coin groups < 30 percentage points
- **Minimum signals per group:** At least 5 signals per coin group for meaningful comparison

---

## Scripts to Create

### 1. `collect_validation_sample.py`
- Collect large independent sample from 50+ coins
- Use base filter on 15m klines
- Target 2-3 signals per symbol
- Save to `validation_sample.json`

### 2. `calculate_validation_performance.py`
- Calculate post-signal performance (TP +3% / SL -3%)
- Extract all required features
- Save to `validation_with_performance.json`

### 3. `test_validation_filters.py`
- Test all 5 filter variants
- Calculate overall metrics
- Calculate per-coin metrics
- Calculate variance between groups
- Calculate confidence intervals

### 4. `generate_validation_report.md`
- Comprehensive human-readable report
- Per-coin breakdown
- Variance analysis
- Confidence intervals
- Final recommendation

---

## Constraints

- **DO NOT modify LW-001**
- **DO NOT modify production**
- **DO NOT modify backtest**
- **DO NOT modify PASS_CHECK**
- **DO NOT modify Telegram**
- This is purely research

---

## Next Steps

1. Create `collect_validation_sample.py`
2. Run data collection
3. Create `calculate_validation_performance.py`
4. Run performance calculation
5. Create `test_validation_filters.py`
6. Run filter testing
7. Generate final report
8. Make recommendation based on results

---

## Expected Outcome

If the mean-reversion hypothesis is validated:
- Proceed to paper trading with recommended filter
- Monitor performance in live conditions
- Consider deployment if results remain stable

If the hypothesis is NOT validated:
- Abandon mean-reversion filter
- Return to drawing board
- Consider alternative hypotheses
