# DEBUGGING REPORT: LW-001 SIGNAL SEARCH DISCREPANCY

## Problem Statement

Previous search found 3,678 signals, but many did not match specified parameters.
New strict search found 0 signals.

## Root Cause Analysis

### VARIANT A: Error was in formula of Range and Body metrics

**ISSUE FOUND:** Range and Body calculations use Close as denominator instead of Open.

### Formula Comparison

| Metric | User Specification | Current Code | Status |
|--------|-------------------|--------------|--------|
| Range | (High - Low) / Open × 100 | (High - Low) / Close × 100 | **INCORRECT** |
| Body | abs(Close - Open) / Open × 100 | abs(Close - Open) / Close × 100 | **INCORRECT** |
| LW | min(Open, Close) - Low | min(Open, Close) - Low | CORRECT |
| LW/Body | LW / abs(Close - Open) | LW / abs(Close - Open) | CORRECT |
| LW/Range | LW / (High - Low) | LW / (High - Low) | CORRECT |
| Open→Low | (Low - Open) / Open × 100 | (Low - Open) / Open × 100 | CORRECT |
| Volume Ratio | Volume / avg_volume_20 | Volume / avg_volume_20 | CORRECT |

### Impact

For a green candle (Close > Open):
- Using Close denominator: Range and Body appear **smaller**
- Using Open denominator: Range and Body appear **larger**

For a red candle (Close < Open):
- Using Close denominator: Range and Body appear **larger**
- Using Open denominator: Range and Body appear **smaller**

### Sample Test

Sample candle: Open=100, High=106, Low=94, Close=105

| Implementation | Range | Body |
|----------------|-------|------|
| Current (Close) | 11.43% | 4.76% |
| Corrected (Open) | 12.00% | 5.00% |
| Difference | +0.57% | +0.24% |

## Metric Distributions Analysis

Based on 3,640 signals from previous search (with incorrect formulas):

| Metric | Min | Max | Mean | Median |
|--------|-----|-----|------|--------|
| Range | 0.54% | 8.13% | 2.26% | 1.96% |
| Body | 0.00% | 5.58% | 1.25% | 1.11% |
| LW/Body | 0.00x | 5.45x | 0.82x | 0.53x |
| LW/Range | 0.0% | 84.4% | 29.7% | 28.6% |
| Open→Low | -6.43% | 0.00% | -1.49% | -1.38% |
| Volume Ratio | 0.73x | 6.06x | 1.47x | 1.28x |

## Strict Thresholds Analysis

| Condition | Threshold | Signals Passing | Percentage |
|-----------|-----------|-----------------|------------|
| Range >= | 6.0% | 44/3640 | 1.2% |
| Body >= | 1.9% | 681/3640 | 18.7% |
| LW/Body >= | 2.5x | 143/3640 | 3.9% |
| LW/Range >= | 63.0% | 159/3640 | 4.4% |
| Open→Low <= | -5.0% | 26/3640 | 0.7% |
| Volume Ratio >= | 2.6x | 177/3640 | 4.9% |

## Conclusion

**Primary Issue:** Range and Body calculations used Close instead of Open as denominator.

**Secondary Issue:** The strict minimum thresholds are extremely restrictive for actual market data:
- Only 0.7% of signals have Open→Low <= -5.0%
- Only 1.2% of signals have Range >= 6.0%
- Only 3.9% of signals have LW/Body >= 2.5x

Even with 3,640 signals, very few would pass all 6 conditions simultaneously.

## Recommendations

1. **Fix calculation formulas** to use Open as denominator for Range and Body
2. **Adjust thresholds** to match actual market distributions
3. **Use realistic thresholds** based on 75th-90th percentiles:
   - Range: ~3-4% (90th percentile)
   - Body: ~2-2.5% (90th percentile)
   - LW/Body: ~1.5-2.0x (90th percentile)
   - LW/Range: ~50-60% (90th percentile)
   - Open→Low: ~-3 to -4% (90th percentile)
   - Volume Ratio: ~2.0-2.5x (90th percentile)

## Next Steps

Await user guidance on:
1. Whether to use original target parameters (Range 4%, Body 1.8%, etc.)
2. Whether to adjust strict thresholds to realistic values
3. Whether to proceed with corrected formulas and adjusted thresholds
