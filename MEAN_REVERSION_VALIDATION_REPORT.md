# Mean-Reversion Hypothesis Validation Report

**Date:** 15.08.2026  
**Task:** Validate mean-reversion/bounce hypothesis on large independent sample  
**Sample Size:** 61 signals (37 unique symbols)  
**Time Period:** Last 60 days  
**Model:** TP +3% / SL -3%  
**Status:** FAILED

---

## Executive Summary

The mean-reversion hypothesis **FAILED** validation on an independent sample. Instead of improving performance, the proposed filters **increased** the SL rate significantly.

**Critical Finding:** The pattern observed in the previous 36-signal sample does **NOT** generalize to a larger, more diverse sample.

**Result:** The mean-reversion hypothesis is **REJECTED**. No filter should be deployed based on this research.

---

## Sample Characteristics

### Universe Attempted
- **Target:** 50+ diverse coins
- **Attempted:** 104 symbols
- **Successfully analyzed:** 37 coins
- **Failed:** 67 coins (offline or not available)

### Actual Sample
- **Total signals:** 61
- **Unique symbols:** 37
- **Signals per symbol:** Average 1.65 (target was 2-3)

### Symbols Analyzed
SIREN-USDT, HOME-USDT, 1000BONK-USDT, WIF-USDT, BOME-USDT, ORCA-USDT, JUP-USDT, GALA-USDT, SAND-USDT, AXS-USDT, IMX-USDT, ILV-USDT, YGG-USDT, ALICE-USDT, SUSHI-USDT, SNX-USDT, CRV-USDT, TAO-USDT, NMR-USDT, OP-USDT, TIA-USDT, INJ-USDT, DOGE-USDT, STG-USDT, JTO-USDT, STORJ-USDT, WLD-USDT, ONE-USDT, ROSE-USDT, VET-USDT, ICP-USDT, AXL-USDT, UMA-USDT, BCH-USDT, AVAX-USDT, GRT-USDT, SOL-USDT, UNI-USDT

### Baseline Classification
- **SL_HIT:** 19 (31.1%)
- **NO_REVERSAL:** 15 (24.6%)
- **VERY_FAST:** 5 (8.2%)
- **FAST:** 9 (14.8%)
- **SLOW:** 13 (21.3%)

---

## Filter Results

### Overall Metrics

| Filter | Total | FAST% | SL% | TP% | MAE | Time+2% |
|--------|-------|-------|-----|-----|-----|--------|
| **Baseline** | 61/61 | 23.0% | 31.1% | 42.6% | 2.53% | 26.0 |
| **PM10 >= 0** | 21/61 | 38.1% | 52.4% | 38.1% | 2.90% | 9.2 |
| **PM10 >= 0.5%** | 20/61 | 35.0% | 55.0% | 35.0% | 2.99% | 7.4 |
| **PM10 >= 0 AND 1H DOWN** | 2/61 | 50.0% | 50.0% | 50.0% | 2.37% | 22.0 |
| **PM10 >= 0.5% AND 1H DOWN** | 1/61 | 0.0% | 100.0% | 0.0% | 3.59% | N/A |

### Key Findings

1. **PM10 >= 0:** SL rate **INCREASED** from 31.1% to 52.4% (+21.3 pp)
2. **PM10 >= 0.5%:** SL rate **INCREASED** from 31.1% to 55.0% (+23.9 pp)
3. **PM10 >= 0 AND 1H DOWN:** Only 2 signals, 50% SL (insufficient sample)
4. **PM10 >= 0.5% AND 1H DOWN:** Only 1 signal, 100% SL (insufficient sample)

**Conclusion:** All filters performed **WORSE** than baseline.

---

## Per-Coin Analysis (PM10 >= 0.5%)

### Extreme Variance

| Symbol | Total | FAST% | SL% | TP% | MAE |
|--------|-------|-------|-----|-----|-----|
| CRV-USDT | 3 | 100.0% | 0.0% | 100.0% | 1.04% |
| BOME-USDT | 1 | 100.0% | 0.0% | 100.0% | 0.63% |
| ALICE-USDT | 1 | 100.0% | 0.0% | 100.0% | 1.23% |
| HOME-USDT | 3 | 33.3% | 66.7% | 33.3% | 4.52% |
| SIREN-USDT | 3 | 33.3% | 66.7% | 33.3% | 3.60% |
| STORJ-USDT | 3 | 0.0% | 100.0% | 0.0% | 3.91% |
| AXL-USDT | 1 | 0.0% | 100.0% | 0.0% | 3.11% |
| ILV-USDT | 1 | 0.0% | 100.0% | 0.0% | 3.03% |
| INJ-USDT | 1 | 0.0% | 100.0% | 0.0% | 3.59% |
| WLD-USDT | 1 | 0.0% | 100.0% | 0.0% | 3.04% |

**Key Finding:** Extreme variance between coins. CRV-USDT has 100% success, while STORJ-USDT has 0% success.

---

## Variance Analysis

### Group Split (Odd/Even Symbol Index)

#### Baseline
- **Group A (18 symbols):** FAST=20.7%, SL=27.6%, TP=44.8%
- **Group B (18 symbols):** FAST=25.0%, SL=34.4%, TP=40.6%
- **Variance:** FAST=4.3pp, SL=6.8pp, TP=4.2pp
- **Verdict:** STABLE

#### PM10 >= 0
- **Group A (7 symbols):** FAST=55.6%, SL=22.2%, TP=55.6%
- **Group B (6 symbols):** FAST=25.0%, SL=75.0%, TP=25.0%
- **Variance:** FAST=30.6pp, SL=52.8pp, TP=30.6pp
- **Verdict:** **UNSTABLE**

#### PM10 >= 0.5%
- **Group A (6 symbols):** FAST=40.0%, SL=40.0%, TP=40.0%
- **Group B (6 symbols):** FAST=30.0%, SL=70.0%, TP=30.0%
- **Variance:** FAST=10.0pp, SL=30.0pp, TP=10.0pp
- **Verdict:** **UNSTABLE**

#### PM10 >= 0 AND 1H DOWN
- **Group A (1 symbol):** FAST=0.0%, SL=100.0%, TP=0.0%
- **Group B (1 symbol):** FAST=100.0%, SL=0.0%, TP=100.0%
- **Variance:** FAST=100.0pp, SL=100.0pp, TP=100.0pp
- **Verdict:** **UNSTABLE** (insufficient sample)

---

## Success Criteria Evaluation

### Criteria 1: TP +3% before SL -3% noticeably higher than baseline
- **Required:** +15 pp improvement
- **Actual (PM10 >= 0.5%):** -7.6 pp (42.6% → 35.0%)
- **Result:** **FAILED**

### Criteria 2: SL rate noticeably lower than baseline
- **Required:** -15 pp reduction
- **Actual (PM10 >= 0.5%):** +23.9 pp increase (31.1% → 55.0%)
- **Result:** **FAILED** (opposite effect)

### Criteria 3: Results persist across most different coins
- **Required:** Variance < 30 pp
- **Actual (PM10 >= 0.5%):** 30.0 pp variance in SL
- **Result:** **FAILED** (unstable)

### Overall Verdict
**ALL THREE CRITERIA FAILED.** The hypothesis is rejected.

---

## What Went Wrong

### Previous Sample (36 signals)
- PM10 >= 0: 42.9% FAST, 35.7% SL, 42.9% TP
- PM10 >= 0.5%: 54.5% FAST, 18.2% SL, 54.5% TP
- PM10 >= 0 AND 1H DOWN: 100% FAST, 0% SL, 100% TP (4 signals)

### Validation Sample (61 signals)
- PM10 >= 0: 38.1% FAST, 52.4% SL, 38.1% TP
- PM10 >= 0.5%: 35.0% FAST, 55.0% SL, 35.0% TP
- PM10 >= 0 AND 1H DOWN: 50% FAST, 50% SL (2 signals)

### Explanation
The previous sample was **overfitted** to specific coin behavior. The pattern does not generalize to a larger, more diverse sample.

---

## Limitations

1. **Sample size:** 61 signals (target was 100-150)
2. **Symbol concentration:** 37 symbols (target was 50)
3. **API limitations:** 67 coins offline/unavailable
4. **Filter pass rates:** Very low for complex filters (1-2 signals)
5. **Time period:** Last 60 days (specific market conditions)

---

## Final Recommendation

### Decision
**REJECT the mean-reversion hypothesis.**

### Rationale
1. Filters **increased** SL rate instead of decreasing it
2. Extreme variance between different coins
3. Insufficient sample size for complex filters
4. Pattern does not generalize to independent sample

### Next Steps
1. **DO NOT deploy** any of the tested filters
2. Return to drawing board for new hypotheses
3. Consider alternative approaches:
   - Different timeframes
   - Different filter combinations
   - Different market conditions
   - Different asset classes

---

## Important Notes

**This is purely research.** No changes were made to:
- LW-001
- Production
- Backtest
- PASS_CHECK
- Telegram

The mean-reversion hypothesis is **REJECTED** based on this validation. No filter deployment is recommended.
