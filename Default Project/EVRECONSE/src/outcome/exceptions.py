"""Outcome module exceptions."""


class OutcomeError(Exception):
    """Base exception for outcome module."""
    pass


class OutcomeTrackerError(OutcomeError):
    """Error in outcome tracker."""
    pass


class OutcomeNotFoundError(OutcomeError):
    """Outcome not found."""
    pass


class InvalidOutcomeStateError(OutcomeError):
    """Invalid outcome state transition."""
    pass


class MonitoringExpiredError(OutcomeError):
    """Monitoring period expired."""
    pass
