# Stage 0: Full Audit Report

**Date:** 2026-08-05  
**Objective:** Complete audit of EVRECONSE project before any modifications

---

## Requirements vs Implementation Table

| Requirement | Where Implemented | Status | Differences |
|-------------|-------------------|--------|-------------|
| **Strategy LW-001** | | | |
| Long lower wick pattern (>= 2x body) | `src/strategy/lw_001.py` lines 31-33, 88-93 | ✅ MATCH | None |
| M15 timeframe only | `src/strategy/lw_001.py` lines 35, 68-69 | ✅ MATCH | None |
| Real Bybit data only | `src/strategy/lw_001.py` lines 35, 64-66, 144-146 | ✅ MATCH | None |
| Lower Wick Quality scoring (0-40) | `src/strategy/lw_001.py` lines 289-319 | ✅ MATCH | None |
| Liquidation Strength scoring (0-35) | `src/strategy/lw_001.py` lines 321-348 | ✅ MATCH | None |
| Candle Confirmation scoring (0-25) | `src/strategy/lw_001.py` lines 350-379 | ✅ MATCH | None |
| **Configuration Weights** | | | |
| lower_wick_weight = 40 | `config.yaml` line 74 | ❌ MISMATCH | Currently 50 (should be 40) |
| liquidation_weight = 35 | `config.yaml` line 75 | ❌ MISMATCH | Currently 0 (should be 35) |
| confirmation_weight = 25 | `config.yaml` line 76 | ❌ MISMATCH | Currently 50 (should be 25) |
| **Thresholds** | | | |
| min_confidence_score = 80 | `config.yaml` line 66 | ❌ MISMATCH | Currently 25 (should be 80) |
| lower_wick_ratio = 2.0 | `config.yaml` line 62 | ✅ MATCH | None |
| liquidation_window = 12 | `config.yaml` line 65 | ✅ MATCH | None |
| **Scoring Engine** | | | |
| minimum_signal_score = 80.0 | `config.yaml` line 101 | ✅ MATCH | None |
| lower_wick_quality max_score = 40 | `config.yaml` line 111 | ✅ MATCH | None |
| liquidation_strength max_score = 35 | `config.yaml` line 114 | ✅ MATCH | None |
| candle_confirmation max_score = 25 | `config.yaml` line 117 | ✅ MATCH | None |
| **Scoring Parameters** | | | |
| Lower Wick Quality parameter | `src/scoring/parameters/lower_wick.py` | ✅ EXISTS | Uses strategy_data.lower_wick and strategy_data.body |
| Liquidation Strength parameter | `src/scoring/parameters/liquidation.py` | ✅ EXISTS | |
| Candle Confirmation parameter | `src/scoring/parameters/candle_confirmation.py` | ✅ EXISTS | |
| **Data Flow** | | | |
| Bybit WebSocket → EventEngine | `src/data_provider/bybit_provider.py` + `src/event_engine/event_engine.py` | ✅ MATCH | |
| EventEngine → Strategy | `src/event_engine/event_pipeline.py` PipelineStageStrategy | ✅ MATCH | |
| Strategy → Scoring | `src/event_engine/event_pipeline.py` PipelineStageScorer | ✅ MATCH | |
| Scoring → Notification | `src/event_engine/event_pipeline.py` PipelineStageNotifier | ✅ MATCH | |
| Notification → Telegram | `src/notification/telegram_service.py` | ✅ MATCH | Verified working |

---

## Critical Issues Found

### Issue #1: Production Configuration Has Test Values

**Location:** `config.yaml` lines 66, 74-76

**Problem:** The production configuration contains test values that were set during previous testing with Yahoo Finance:

```yaml
strategy:
  LW-001:
    condition:
      min_confidence_score: 25  # ❌ WRONG - should be 80
    scoring:
      lower_wick_weight: 50     # ❌ WRONG - should be 40
      liquidation_weight: 0     # ❌ WRONG - should be 35 (was set to 0 for Yahoo Finance tests)
      confirmation_weight: 50   # ❌ WRONG - should be 25
```

**Impact:** 
- Strategy will generate many more signals than intended (threshold 25 instead of 80)
- Liquidation data is completely ignored (weight 0 instead of 35)
- Weights are unbalanced (50/0/50 instead of 40/35/25)

**Correct Production Values:**
```yaml
strategy:
  LW-001:
    condition:
      min_confidence_score: 80
    scoring:
      lower_wick_weight: 40
      liquidation_weight: 35
      confirmation_weight: 25
```

---

## Coin List Analysis

**Current Symbols in config.yaml (lines 27-32):**
```
INJUSDT, SEIUSDT, TIAUSDT, SUIUSDT, WIFUSDT,
BONKUSDT, PEPEUSDT, FLOKIUSDT, TURBOUSDT, BRETTUSDT,
JASMYUSDT, ARKMUSDT, APTUSDT, NOTUSDT, WUSDT,
PYTHUSDT, JTOUSDT, DYDXUSDT, OPUSDT, ARBUSDT
```

**Analysis Required:** 
- Verify each symbol exists on Bybit Futures
- Ensure all are volatile altcoins below TOP-20
- Replace any missing symbols

**Status:** ⏳ PENDING - Need to verify on Bybit Futures

---

## Strategy Implementation Analysis

### How LW-001 Currently Works:

1. **Input Data:**
   - OHLC from Bybit WebSocket (real-time)
   - Liquidation data from strategy_data (currently placeholder)

2. **Candle Structure Calculation** (lines 212-225):
   - Computed from OHLC, not from strategy_data
   - body = close - open
   - lower_wick = min(open, close) - low
   - wick_body_ratio = lower_wick / body_size

3. **Scoring Components:**
   - **Lower Wick Quality (0-40):** Based on wick-to-body ratio tiers
   - **Liquidation Strength (0-35):** Based on liquidation volume vs reference
   - **Candle Confirmation (0-25):** Based on body ratio and close position

4. **Final Score Calculation** (lines 386-393):
   - Weighted sum: wick_score * (wick_weight/100) + liq_score * (liq_weight/100) + confirm_score * (confirm_weight/100)
   - Capped at 100

5. **Qualification:** final_score >= min_confidence_score

### Potential Issues:

1. **Liquidation Data:** Strategy expects `strategy_data.liquidation_volume` and `strategy_data.liquidation_reference_value` (lines 230-231), but these are currently placeholders (line 348: "Liquidation data not available or reference is zero")

2. **Scoring Parameter Implementation:** The separate scoring parameters in `src/scoring/parameters/` use `strategy_data.lower_wick` and `strategy_data.body`, but the strategy computes these from OHLC. This could cause inconsistency.

---

## Next Steps

**Stage 1:** Fix production configuration to correct values  
**Stage 2:** Verify and correct coin list for Bybit Futures  
**Stage 3:** Investigate liquidation data integration  
**Stage 4:** Run historical backtest with corrected configuration

---

## Summary

**Critical Blockers:**
1. ❌ Production configuration has test values (min_confidence_score=25, liquidation_weight=0)
2. ⏳ Coin list needs verification on Bybit Futures
3. ⏳ Liquidation data integration incomplete (placeholder values)

**Non-Critical:**
- Scoring parameters may have data source inconsistency (strategy_data vs OHLC computation)

**Infrastructure Status:** ✅ All pipeline components working correctly
