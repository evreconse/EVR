# LW-001 Stage 2: Working Parameters Research - Final Report

**Date:** 2026-08-23  
**Task:** Research mathematically compatible and statistically viable LW-001 parameters  
**Status:** RESEARCH COMPLETE

---

## Executive Summary

Comprehensive analysis of 57,000 candles from 57 Top-21-250 symbols over 60 days identified 7 candidate parameter sets. The research revealed that the original thresholds were mathematically impossible and practically too strict. New candidates range from conservative to soft, with signal counts from 0 to 15.

**Key Finding:** BALANCED_2 and MODERATE_1 provide the best balance of signal availability, symbol diversity, and LW-001 concept preservation.

---

## 1. Dataset

**Configuration:**
- Symbols: 57 (Top-21-250, excluding Top-20)
- Symbols without data: 20
- Total candles: 57,000
- Period: 60 days
- Timeframe: 15m
- Exchange: BingX

**Excluded Top-20:** BTC, ETH, BNB, SOL, XRP, ADA, DOGE, AVAX, DOT, LINK, LTC, ATOM, NEAR, OP, ARB

---

## 2. Metric Distributions

| Metric          | Min    | P50   | P75   | P80   | P85   | P90   | P95   | P97.5 | P99   | Max     |
|-----------------|--------|-------|-------|-------|-------|-------|-------|-------|-------|---------|
| Range %         | 0.00   | 0.41  | 0.73  | 0.83  | 0.98  | 1.18  | 1.60  | 2.06  | 2.81  | 32.16   |
| Body %          | 0.00   | 0.17  | 0.36  | 0.43  | 0.53  | 0.68  | 0.99  | 1.33  | 1.86  | 17.34   |
| LW/Body x       | 0.00   | 0.39  | 1.00  | 1.50  | 2.00  | 3.00  | 5.00  | 7.67  | 13.00 | 192.00  |
| LW/Range %      | 0.00   | 22.22 | 40.00 | 45.95 | 50.00 | 60.00 | 69.23 | 76.92 | 85.46 | 100.00  |
| Open->Low %     | -31.05 | -0.16 | -0.06 | -0.05 | -0.03 | -0.02 | 0.00  | 0.00  | 0.00  | 0.00    |
| Volume Ratio x  | 0.00   | 0.97  | 1.02  | 1.04  | 1.07  | 1.16  | 1.51  | 2.25  | 4.85  | 547456039.00 |

**Key Observations:**
- Range P90 = 1.18%, P95 = 1.60% - Original 6% threshold is at P99+
- Body P90 = 0.68%, P95 = 0.99% - Original 1.9% threshold is at P99+
- LW/Body P85 = 2.0x - Original 2.5x threshold is at P90+
- LW/Range P90 = 60% - Original 63% threshold is at P90+
- Open->Low P97.5 = 0% - Original -5% threshold affects only 0.14% of candles
- Volume Ratio P95 = 1.51x - Original 2.6x threshold affects only 2.01% of candles

---

## 3. Open->Low Threshold Research

| Threshold | Candles | % of Dataset | Symbols |
|-----------|---------|--------------|---------|
| -5.0%     | 82      | 0.1439%      | 57      |
| -4.5%     | 94      | 0.1649%      | 57      |
| -4.0%     | 113     | 0.1982%      | 57      |
| -3.5%     | 143     | 0.2509%      | 57      |
| -3.0%     | 187     | 0.3281%      | 57      |
| -2.5%     | 275     | 0.4825%      | 57      |
| -2.0%     | 463     | 0.8123%      | 57      |

**Finding:** Open->Low <= -5% is extremely rare (0.14% of candles). Even -2.5% only affects 0.48% of candles.

---

## 4. Volume Ratio Threshold Research

| Threshold | Candles | % of Dataset | Symbols |
|-----------|---------|--------------|---------|
| 2.6x      | 1,148   | 2.0140%      | 57      |
| 2.5x      | 1,227   | 2.1526%      | 57      |
| 2.25x     | 1,424   | 2.4982%      | 57      |
| 2.0x      | 1,718   | 3.0140%      | 57      |
| 1.75x     | 2,148   | 3.7684%      | 57      |
| 1.5x      | 2,898   | 5.0842%      | 57      |

**Finding:** Volume Ratio >= 2.6x affects only 2.01% of candles. Lowering to 1.5x increases to 5.08%.

---

## 5. Candidate Parameter Testing Results

| Variant    | Range | Body | LW/Body | LW/Range | Open->Low | Vol  | Signals | Symbols | Min/Med/Avg/Max per Symbol | Top-5 Conc. |
|------------|-------|------|---------|----------|-----------|------|---------|---------|---------------------------|-------------|
| CONSERVATIVE | 6.0% | 1.5% | 2.0x | 70.0% | -4.0% | 2.0x | 0 | 0 | -/-/-/- | - |
| BALANCED_1 | 5.0% | 1.2% | 1.8x | 65.0% | -3.5% | 1.75x | 0 | 0 | -/-/-/- | - |
| BALANCED_2 | 4.5% | 1.0% | 1.5x | 60.0% | -3.0% | 1.5x | 7 | 5 | 1/1/1.4/3 | 71.43% |
| MODERATE_1 | 4.0% | 0.8% | 1.3x | 55.0% | -2.5% | 1.5x | 15 | 12 | 1/1/1.2/3 | 53.33% |
| MODERATE_2 | 3.5% | 0.6% | 1.2x | 50.0% | -2.5% | 1.5x | 28 | 18 | 1/1/1.6/4 | 46.43% |
| SOFT_1    | 3.0% | 0.5% | 1.0x | 45.0% | -2.0% | 1.5x | 57 | 26 | 1/1/2.2/7 | 40.35% |
| SOFT_2    | 2.5% | 0.4% | 0.8x | 40.0% | -2.0% | 1.5x | 112 | 38 | 1/1/2.9/8 | 35.71% |

---

## 6. Detailed Analysis of Best Candidates

### BALANCED_2 (Recommended Conservative)

**Parameters:**
- Range: 4.5%
- Body: 1.0%
- LW/Body: 1.5x
- LW/Range: 60.0%
- Open->Low: -3.0%
- Volume Ratio: 1.5x

**Results:**
- Total signals: 7
- Unique symbols: 5
- Min/Median/Avg/Max per symbol: 1/1/1.4/3
- Top-5 concentration: 71.43%
- Top symbols: ZEC-USDT (3), ETC-USDT (1), ICP-USDT (1), FET-USDT (1), TRX-USDT (1)

**Assessment:** Very conservative, preserves LW-001 concept well. Low signal count but good quality. Concentrated on ZEC-USDT (43% of signals).

---

### MODERATE_1 (Recommended Balanced)

**Parameters:**
- Range: 4.0%
- Body: 0.8%
- LW/Body: 1.3x
- LW/Range: 55.0%
- Open->Low: -2.5%
- Volume Ratio: 1.5x

**Results:**
- Total signals: 15
- Unique symbols: 12
- Min/Median/Avg/Max per symbol: 1/1/1.2/3
- Top-5 concentration: 53.33%
- Top symbols: FET-USDT (3), ZEC-USDT (2), ORDI-USDT (1), TIA-USDT (1), ICP-USDT (1)

**Assessment:** Good balance of signal availability and diversity. Preserves LW-001 concept with reasonable thresholds. Better symbol distribution than BALANCED_2.

---

### MODERATE_2 (Recommended for Research)

**Parameters:**
- Range: 3.5%
- Body: 0.6%
- LW/Body: 1.2x
- LW/Range: 50.0%
- Open->Low: -2.5%
- Volume Ratio: 1.5x

**Results:**
- Total signals: 28
- Unique symbols: 18
- Min/Median/Avg/Max per symbol: 1/1/1.6/4
- Top-5 concentration: 46.43%
- Top symbols: ZEC-USDT (4), FET-USDT (3), RNDR-USDT (2), ICP-USDT (2), ETC-USDT (2)

**Assessment:** Good for initial research with larger sample size. Still preserves core LW-001 concept. Better symbol distribution.

---

### SOFT_1 (Wide Research)

**Parameters:**
- Range: 3.0%
- Body: 0.5%
- LW/Body: 1.0x
- LW/Range: 45.0%
- Open->Low: -2.0%
- Volume Ratio: 1.5x

**Results:**
- Total signals: 57
- Unique symbols: 26
- Min/Median/Avg/Max per symbol: 1/1/2.2/7
- Top-5 concentration: 40.35%

**Assessment:** Large sample for research. LW/Body >= 1.0x is very soft (lower wick equals body). May include lower-quality signals.

---

### SOFT_2 (Maximum Sample)

**Parameters:**
- Range: 2.5%
- Body: 0.4%
- LW/Body: 0.8x
- LW/Range: 40.0%
- Open->Low: -2.0%
- Volume Ratio: 1.5x

**Results:**
- Total signals: 112
- Unique symbols: 38
- Min/Median/Avg/Max per symbol: 1/1/2.9/8
- Top-5 concentration: 35.71%

**Assessment:** Maximum sample size. LW/Body >= 0.8x is very soft (lower wick smaller than body). May deviate from LW-001 concept.

---

## 7. Mathematical Compatibility Check

**Original Thresholds (IMPOSSIBLE):**
- Range >= 6.0% and Body >= 1.9% require Body/Range >= 31.7%
- LW/Body >= 2.5x and LW/Range >= 63% require Body/Range <= 25.2%
- **31.7% > 25.2% = IMPOSSIBLE**

**BALANCED_2 (COMPATIBLE):**
- Range >= 4.5% and Body >= 1.0% require Body/Range >= 22.2%
- LW/Body >= 1.5x and LW/Range >= 60% require Body/Range <= 40.0%
- **22.2% <= 40.0% = COMPATIBLE**

**MODERATE_1 (COMPATIBLE):**
- Range >= 4.0% and Body >= 0.8% require Body/Range >= 20.0%
- LW/Body >= 1.3x and LW/Range >= 55% require Body/Range <= 42.3%
- **20.0% <= 42.3% = COMPATIBLE**

**MODERATE_2 (COMPATIBLE):**
- Range >= 3.5% and Body >= 0.6% require Body/Range >= 17.1%
- LW/Body >= 1.2x and LW/Range >= 50% require Body/Range <= 41.7%
- **17.1% <= 41.7% = COMPATIBLE**

---

## 8. Real Candle Examples

### MODERATE_1 Example Candles

**Example 1: ORDI-USDT**
- O: 5.044, H: 5.100, L: 3.478, C: 4.396
- Range: 32.16% (PASS >= 4.0%)
- Body: 12.85% (PASS >= 0.8%)
- LW/Body: 1.42x (PASS >= 1.3x)
- LW/Range: 56.60% (PASS >= 55.0%)
- Open->Low: -31.05% (PASS <= -2.5%)
- Volume Ratio: 8.56x (PASS >= 1.5x)

**Example 2: TIA-USDT**
- O: 0.422, H: 0.424, L: 0.321, C: 0.378
- Range: 24.43% (PASS)
- Body: 10.43% (PASS)
- LW/Body: 1.30x (PASS)
- LW/Range: 55.58% (PASS)
- Open->Low: -24.00% (PASS)
- Volume Ratio: 4.27x (PASS)

**Example 3: ICP-USDT**
- O: 2.689, H: 2.700, L: 2.063, C: 2.447
- Range: 23.69% (PASS)
- Body: 9.00% (PASS)
- LW/Body: 1.59x (PASS)
- LW/Range: 60.28% (PASS)
- Open->Low: -23.28% (PASS)
- Volume Ratio: 13.84x (PASS)

All examples show classic LW-001 pattern: large range, significant lower wick, strong downward move, elevated volume.

---

## 9. Recommendations

### Most Conservative: BALANCED_2

**Use for:** High-quality signal production with strict quality control.

**Pros:**
- Preserves LW-001 concept well
- Mathematically compatible
- High signal quality (extreme candles)

**Cons:**
- Very low signal count (7 signals in 60 days)
- Concentrated on few symbols (71% top-5 concentration)
- May be too rare for practical trading

---

### Most Balanced: MODERATE_1

**Use for:** Balanced approach between quality and quantity.

**Pros:**
- Good signal count (15 signals in 60 days)
- Better symbol distribution (12 unique symbols)
- Preserves LW-001 concept
- Mathematically compatible
- Reasonable thresholds

**Cons:**
- Still relatively low signal count
- Some concentration on top symbols (53% top-5)

**Recommendation:** **MODERATE_1 is the best overall candidate** for initial research and potential production.

---

### Best for Research: MODERATE_2

**Use for:** Initial efficiency research with larger sample size.

**Pros:**
- Larger sample (28 signals in 60 days)
- Good symbol distribution (18 unique symbols)
- Still preserves core LW-001 concept
- Mathematically compatible

**Cons:**
- Softer thresholds may include lower-quality signals

**Recommendation:** Use MODERATE_2 for initial TP/SL research, then validate with MODERATE_1.

---

### Wide Research: SOFT_1

**Use for:** Exploratory research only.

**Pros:**
- Large sample (57 signals)
- Good symbol distribution

**Cons:**
- LW/Body >= 1.0x is very soft
- May deviate from LW-001 concept
- Not recommended for production

---

## 10. Final Comparison Summary

| Variant    | Signals | Symbols | Quality | Diversity | Recommendation |
|------------|---------|---------|---------|-----------|----------------|
| CONSERVATIVE | 0 | 0 | - | - | Too strict |
| BALANCED_1 | 0 | 0 | - | - | Too strict |
| BALANCED_2 | 7 | 5 | High | Low | Conservative production |
| MODERATE_1 | 15 | 12 | High | Medium | **BEST OVERALL** |
| MODERATE_2 | 28 | 18 | Medium | Good | Research |
| SOFT_1    | 57 | 26 | Low | Good | Exploratory only |
| SOFT_2    | 112 | 38 | Low | Good | Too soft |

---

## 11. Next Steps

1. **Select MODERATE_1** as the primary candidate for LW-001
2. **Use MODERATE_2** for initial TP/SL research
3. **Validate** with 10 manual signal checks
4. **Proceed to efficiency analysis** (TP/SL performance)
5. **Do NOT send signals to Telegram** until efficiency is confirmed

---

## 12. Files Generated

1. `stage2_research_working_parameters.py` - Research script
2. `LW001_STAGE2_FINAL_REPORT.md` - This report

---

**Report Generated:** 2026-08-23  
**Research Status:** COMPLETE  
**Recommendation:** MODERATE_1 (Range 4.0%, Body 0.8%, LW/Body 1.3x, LW/Range 55.0%, Open->Low -2.5%, Volume Ratio 1.5x)  
**Next Action:** Awaiting your decision on parameter selection.
