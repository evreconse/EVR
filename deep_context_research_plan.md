# Deep Context Research Plan

## Objective
Find reproducible market context that distinguishes fast-rising signals from SL_HIT signals for TP +3% / SL -3% model.

## Constraints
- RESEARCH ONLY - no changes to LW-001, production, backtest, PASS_CHECK, or Telegram
- Skip unavailable data gracefully
- Avoid overfitting

## Target Sample
- 50+ coins × 2-3 signals = 100-150+ signals
- Prioritize diversity over quantity per coin

## Research Phases

### Phase 1: Data Collection
1. Expand universe to 100+ coins (more attempts to get 50+ working)
2. Find 2-3 signals per coin using base filter
3. Calculate post-signal performance (TP +3% / SL -3%)
4. Classify signals (VERY_FAST, FAST, SLOW, SL_HIT, NO_REVERSAL)

### Phase 2: Feature Extraction
#### A. Previous Price Movement
- PM5, PM10, PM20, PM30
- Green/red candle counts and ratios
- Max up/down before signal
- Growth/detection before signal
- Pullback depth

#### B. Trend Structure
- EMA 9, 21, 50, 100 (if available)
- Price position relative to EMAs
- EMA slopes (9, 21, 50, 100)
- EMA crossings
- Higher high / higher low sequences

#### C. Range Position
- Range position for 10, 20, 50, 100 candles
- Distance to local high/low
- Breakout detection
- Pullback after breakout

#### D. Pullback/Continuation Patterns
- Variant A: Growth 10-20 candles + small pullback before signal
- Variant B: Growth + strong pullback + signal
- Variant C: Fall + signal
- Variant D: Sideways + signal
- Variant E: Breakout local high + pullback + signal

#### E. Support/Resistance (if available)
- Distance to local support/resistance
- Bounce from level
- Breakout of level
- Retest after breakout

#### F. Higher Timeframes (if available)
- 1H: direction, PM10/20, EMAs, slopes, range position
- 4H: same
- 1D: same

#### G. Volatility
- Current Range%
- Average Range
- ATR (if available)
- ATR change
- Range expansion/contraction
- Volatility regime
- Body size, lower wick, LW/Body, LW/Range

#### H. Volume
- Volume Ratio
- Volume relative to average
- Volume growth/decline
- Volume during previous movement
- Volume on pullback
- Volume on signal candle

### Phase 3: Analysis
1. Compare FAST vs SL_HIT vs NO_REVERSAL for each feature
2. Test PM10 thresholds (-2% to +3%)
3. Test feature combinations systematically
4. Resolve range position contradiction
5. Test on different subsamples to avoid overfitting

### Phase 4: Reporting
1. Human-readable explanations
2. Feature rating table
3. Confirmed vs refuted hypotheses
4. Candidates for next experiment

## Scripts to Create
1. `find_large_diverse_sample.py` - Expand universe, find signals
2. `analyze_large_performance.py` - Post-signal performance
3. `extract_large_features.py` - Comprehensive feature extraction
4. `analyze_pullback_patterns.py` - Pattern variant analysis
5. `compare_feature_groups.py` - FAST vs SL_HIT comparison
6. `test_combinations.py` - Systematic combination testing
7. `test_pm10_thresholds.py` - PM10 threshold testing
8. `generate_final_report.py` - Human-readable report

## Status
- Planning phase complete
- Ready to begin data collection
