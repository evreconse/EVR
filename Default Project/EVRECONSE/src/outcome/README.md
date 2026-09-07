# Outcome Module

Outcome Tracker for monitoring TP/SL and recording trade results.

## Purpose

Monitors active signals to determine:
- Take Profit (TP) reached
- Stop Loss (SL) reached  
- Position expired (48 hours max)

## Files

| File | Purpose |
|------|---------|
| `outcome_tracker.py` | Main outcome tracking logic |
| `exceptions.py` | Outcome-specific exceptions |
| `__init__.py` | Public API exports |

## Configuration

From config.yaml:
```yaml
risk:
  take_profit_percent: 3.0
  stop_loss_percent: -3.0
  monitoring:
    max_duration_hours: 24
    expire_after_hours: 48
```

## Lifecycle

Signal → Monitoring → Completed/Expired
