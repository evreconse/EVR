#!/usr/bin/env python3
"""
Identify the single source of truth for LW-001 qualification.

Check:
1. Production LW-001 in src/strategy/lw_001.py
2. Historical search in find_10_signals_v6.py
3. PASS_CHECK in send_10_signals_v6.py
"""

import sys
sys.path.insert(0, "src")

print("=" * 80)
print("IDENTIFYING SINGLE SOURCE OF TRUTH FOR LW-001 QUALIFICATION")
print("=" * 80)

print("\n1. PRODUCTION LW-001 (src/strategy/lw_001.py)")
print("-" * 80)
print("File: src/strategy/lw_001.py")
print("Method: LW001Strategy.evaluate()")
print("Line 326:")
print("  qualified = is_red and wick_body_ratio >= wick_ratio_threshold")
print("\nWhere:")
print("  is_red = close_price < open_price")
print("  body = open_price - close_price if is_red else 0.0  (NO abs())")
print("  lower_wick = close_price - low_price")
print("  wick_body_ratio = lower_wick / body if body > 0 else 0.0")
print("  wick_ratio_threshold = 2.0 (from config)")
print("\nUpper wick is calculated but NOT used in qualification:")
print("  upper_wick = high_price - max(open_price, close_price)")
print("  (used only for informational display)")

print("\n2. HISTORICAL SEARCH (find_10_signals_v6.py)")
print("-" * 80)
print("File: find_10_signals_v6.py")
print("Function: check_lw001_strict()")
print("Lines 54-97:")
print("  is_red = close_price < open_price")
print("  body = open_price - close_price if is_red else 0.0  (NO abs())")
print("  lower_wick = close_price - low_price")
print("  upper_wick = high_price - open_price  (informational only)")
print("  ratio = lower_wick / body")
print("  qualified = ratio >= 2.0")
print("\nThis function DUPLICATES the production logic.")
print("It is NOT calling LW001Strategy.evaluate().")

print("\n3. PASS_CHECK (send_10_signals_v6.py)")
print("-" * 80)
print("File: send_10_signals_v6.py")
print("Function: pass_check_strict()")
print("Lines 52-73:")
print("  Uses the SAME check_lw001_strict() function as historical search")
print("  This is a copy-paste of the function from find_10_signals_v6.py")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("\nCURRENT SITUATION:")
print("  - Production LW-001: src/strategy/lw_001.py (single source for live trading)")
print("  - Historical search: find_10_signals_v6.py (DUPLICATES logic)")
print("  - PASS_CHECK: send_10_signals_v6.py (DUPLICATES logic)")
print("\nPROBLEM:")
print("  There are THREE independent implementations of LW-001 qualification.")
print("  This creates risk of divergence.")
print("\nGOOD NEWS:")
print("  All three implementations currently use the SAME formula:")
print("    body = open_price - close_price (NO abs())")
print("    lower_wick = close_price - low_price")
print("    qualified = (is_red) and (lower_wick >= 2 * body)")
print("  Upper wick is NOT used in qualification in any of them.")
print("\nRECOMMENDATION:")
print("  Historical search and PASS_CHECK should ideally call")
print("  LW001Strategy.evaluate() directly instead of duplicating logic.")
print("  However, since the formulas are currently identical,")
print("  this is not the source of the user's reported problem.")
