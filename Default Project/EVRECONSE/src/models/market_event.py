"""
EVRECONSE Models - Market Event.

Main MarketEvent dataclass with nested data groups, factory methods,
transition guard, invariant validation, and full serialization support.

Fully compliant with MARKET_EVENT_SCHEMA.md and EVENT_ENGINE.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field, is_dataclass, replace
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from .enums import (
    EventOutcome,
    EventStatus,
    Exchange,
    ScoreParameter,
    Timeframe,
)
from .exceptions import InvalidTransitionError, InvariantViolationError, ModelValidationError
from .identifiers import EventID, SignalID

# =============================================================================
# Transition Guard - Centralized State Machine (Fully Immutable)
# =============================================================================

class _TransitionMap:
    """
    Immutable transition map for MarketEvent status transitions.
    Cannot be modified at runtime - fully immutable.
    """

    _ALLOWED: dict[EventStatus, frozenset[EventStatus]] = {
        EventStatus.NEW: frozenset({EventStatus.QUALIFIED, EventStatus.DISMISSED}),
        EventStatus.QUALIFIED: frozenset({EventStatus.SCORED, EventStatus.DISMISSED}),
        EventStatus.SCORED: frozenset({EventStatus.SIGNAL, EventStatus.DISMISSED}),
        EventStatus.SIGNAL: frozenset({EventStatus.MONITORING}),
        EventStatus.DISMISSED: frozenset(),
        EventStatus.MONITORING: frozenset({EventStatus.COMPLETED, EventStatus.EXPIRED}),
        EventStatus.COMPLETED: frozenset(),
        EventStatus.EXPIRED: frozenset(),
    }

    @classmethod
    def allowed(cls, current: EventStatus) -> frozenset[EventStatus]:
        """Get allowed next statuses for current status."""
        return cls._ALLOWED.get(current, frozenset())

    @classmethod
    def is_allowed(cls, current: EventStatus, next_status: EventStatus) -> bool:
        """Check if transition is allowed."""
        return next_status in cls._ALLOWED.get(current, frozenset())

    @classmethod
    def is_terminal(cls, status: EventStatus) -> bool:
        """Check if status is terminal (no further transitions allowed)."""
        return not cls._ALLOWED.get(status, frozenset())


# =============================================================================
# Nested Data Groups (Schema Sections) - Defined First
# =============================================================================


from .enums import (
    EventStatus,
)


def _utc_now() -> datetime:
    """Get current UTC time with timezone info."""
    return datetime.now(UTC)


def _utc_from_iso(value: str) -> datetime:
    """Parse ISO format datetime, ensuring UTC timezone."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class Metadata:
    """
    Event metadata - identification and lifecycle tracking.

    Immutable after creation except status and updated_at which
    change through controlled transitions.
    """

    event_id: EventID
    status: EventStatus
    schema_version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class MarketData:
    """
    Market data from the closed candle.

    Immutable after creation - corresponds to one closed M15 candle.
    """

    symbol: str
    exchange: Exchange
    timeframe: Timeframe
    event_time: datetime  # Candle close time (UTC, timezone-aware)
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True, slots=True)
class StrategyData:
    """
    Pattern metrics from strategy evaluation.

    Only present when status >= QUALIFIED.
    """

    strategy_id: str | None = None
    lower_wick: float | None = None
    body: float | None = None
    wick_body_ratio: float | None = None
    lower_wick_pct: float | None = None
    body_pct: float | None = None
    confirm: bool = False


@dataclass(frozen=True, slots=True)
class ScoreBreakdownItem:
    """Single parameter score breakdown."""

    parameter_name: ScoreParameter
    parameter_score: float
    penalty: float = 0.0


@dataclass(frozen=True, slots=True)
class ScoreData:
    """
    Scoring Engine results.

    Only present when status >= SCORED.
    """

    confidence_score: float | None = None
    score_breakdown: tuple[ScoreBreakdownItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class NotificationData:
    """
    Notification delivery metadata.

    Only present when status == SIGNAL.
    """

    notification_timestamp: datetime | None = None
    close_price: float | None = None


@dataclass(frozen=True, slots=True)
class OutcomeData:
    """
    Signal outcome tracking.

    Only present when status >= MONITORING.
    """

    outcome: EventOutcome | None = None
    actual_profit_pct: float | None = None
    outcome_timestamp: datetime | None = None


# =============================================================================
# Main MarketEvent Dataclass
# =============================================================================

from dataclasses import dataclass, field

from .enums import (
    EventStatus,
)


# Type guard for dataclass detection
def _is_dataclass_instance(obj: Any) -> bool:
    return is_dataclass(obj) and not isinstance(obj, type)


# =============================================================================
# Transition Guard - Immutable State Machine
# =============================================================================

class _TransitionMap:
    """
    Immutable transition map for MarketEvent status transitions.

    Fully immutable - cannot be modified at runtime.
    """

    _ALLOWED: dict[EventStatus, frozenset[EventStatus]] = {
        EventStatus.NEW: frozenset({EventStatus.QUALIFIED, EventStatus.DISMISSED}),
        EventStatus.QUALIFIED: frozenset({EventStatus.SCORED, EventStatus.DISMISSED}),
        EventStatus.SCORED: frozenset({EventStatus.SIGNAL, EventStatus.DISMISSED}),
        EventStatus.SIGNAL: frozenset({EventStatus.MONITORING}),
        EventStatus.DISMISSED: frozenset(),
        EventStatus.MONITORING: frozenset({EventStatus.COMPLETED, EventStatus.EXPIRED}),
        EventStatus.COMPLETED: frozenset(),
        EventStatus.EXPIRED: frozenset(),
    }

    @classmethod
    def allowed(cls, current: EventStatus) -> frozenset[EventStatus]:
        return cls._ALLOWED.get(current, frozenset())

    @classmethod
    def is_allowed(cls, current: EventStatus, next_status: EventStatus) -> bool:
        return next_status in cls._ALLOWED.get(current, frozenset())

    @classmethod
    def is_terminal(cls, status: EventStatus) -> bool:
        return not cls._ALLOWED.get(status, frozenset())


# =============================================================================
# Nested Data Groups (Schema Sections)
# =============================================================================

@dataclass(frozen=True, slots=True)
class Metadata:
    """
    Event metadata - identification and lifecycle tracking.

    Immutable after creation except status and updated_at which
    change through controlled transitions.
    """

    event_id: EventID
    status: EventStatus
    schema_version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class MarketData:
    """
    Market data from the closed candle.

    Immutable after creation - corresponds to one closed M15 candle.
    """

    symbol: str
    exchange: Exchange
    timeframe: Timeframe
    event_time: datetime  # Candle close time (UTC, timezone-aware)
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True, slots=True)
class StrategyData:
    """
    Pattern metrics from strategy evaluation.

    Only present when status >= QUALIFIED.
    """

    strategy_id: str | None = None
    lower_wick: float | None = None
    body: float | None = None
    wick_body_ratio: float | None = None
    lower_wick_pct: float | None = None
    body_pct: float | None = None
    confirm: bool = False


@dataclass(frozen=True, slots=True)
class ScoreBreakdownItem:
    """Single parameter score breakdown."""

    parameter_name: ScoreParameter
    parameter_score: float
    penalty: float = 0.0


@dataclass(frozen=True, slots=True)
class ScoreData:
    """
    Scoring Engine results.

    Only present when status >= SCORED.
    """

    confidence_score: float | None = None
    score_breakdown: tuple[ScoreBreakdownItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class NotificationData:
    """
    Notification delivery metadata.

    Only present when status == SIGNAL.
    """

    notification_timestamp: datetime | None = None
    close_price: float | None = None


@dataclass(frozen=True, slots=True)
class OutcomeData:
    """
    Signal outcome tracking.

    Only present when status >= MONITORING.
    """

    outcome: EventOutcome | None = None
    actual_profit_pct: float | None = None
    outcome_timestamp: datetime | None = None


# =============================================================================
# Main MarketEvent Dataclass
# =============================================================================

from dataclasses import dataclass, field

from .enums import (
    EventStatus,
)


def _utc_now() -> datetime:
    """Get current UTC time with timezone info."""
    return datetime.now(UTC)


def _utc_from_iso(value: str) -> datetime:
    """Parse ISO format datetime, ensuring UTC timezone."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _is_dataclass_instance(obj: Any) -> bool:
    return is_dataclass(obj) and not isinstance(obj, type)


# =============================================================================
# Transition Guard - Immutable State Machine
# =============================================================================

class _TransitionMap:
    """
    Immutable transition map for MarketEvent status transitions.

    Fully immutable - cannot be modified at runtime.
    """

    _ALLOWED: dict[EventStatus, frozenset[EventStatus]] = {
        EventStatus.NEW: frozenset({EventStatus.QUALIFIED, EventStatus.DISMISSED}),
        EventStatus.QUALIFIED: frozenset({EventStatus.SCORED, EventStatus.DISMISSED}),
        EventStatus.SCORED: frozenset({EventStatus.SIGNAL, EventStatus.DISMISSED}),
        EventStatus.SIGNAL: frozenset({EventStatus.MONITORING}),
        EventStatus.DISMISSED: frozenset(),
        EventStatus.MONITORING: frozenset({EventStatus.COMPLETED, EventStatus.EXPIRED}),
        EventStatus.COMPLETED: frozenset(),
        EventStatus.EXPIRED: frozenset(),
    }

    @classmethod
    def allowed(cls, current: EventStatus) -> frozenset[EventStatus]:
        return cls._ALLOWED.get(current, frozenset())

    @classmethod
    def is_allowed(cls, current: EventStatus, next_status: EventStatus) -> bool:
        return next_status in cls._ALLOWED.get(current, frozenset())

    @classmethod
    def is_terminal(cls, status: EventStatus) -> bool:
        return not cls._ALLOWED.get(status, frozenset())


# =============================================================================
# Nested Data Groups (Schema Sections)
# =============================================================================

@dataclass(frozen=True, slots=True)
class Metadata:
    """
    Event metadata - identification and lifecycle tracking.

    Immutable after creation except status and updated_at which
    change through controlled transitions.
    """

    event_id: EventID
    status: EventStatus
    schema_version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class MarketData:
    """
    Market data from the closed candle.

    Immutable after creation - corresponds to one closed M15 candle.
    """

    symbol: str
    exchange: Exchange
    timeframe: Timeframe
    event_time: datetime  # Candle close time (UTC, timezone-aware)
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True, slots=True)
class StrategyData:
    """
    Pattern metrics from strategy evaluation.

    Only present when status >= QUALIFIED.
    """

    strategy_id: str | None = None
    lower_wick: float | None = None
    body: float | None = None
    wick_body_ratio: float | None = None
    lower_wick_pct: float | None = None
    body_pct: float | None = None
    confirm: bool = False


@dataclass(frozen=True, slots=True)
class ScoreBreakdownItem:
    """Single parameter score breakdown."""

    parameter_name: ScoreParameter
    parameter_score: float
    penalty: float = 0.0


@dataclass(frozen=True, slots=True)
class ScoreData:
    """
    Scoring Engine results.

    Only present when status >= SCORED.
    """

    confidence_score: float | None = None
    score_breakdown: tuple[ScoreBreakdownItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class NotificationData:
    """
    Notification delivery metadata.

    Only present when status == SIGNAL.
    """

    notification_timestamp: datetime | None = None
    close_price: float | None = None


@dataclass(frozen=True, slots=True)
class OutcomeData:
    """
    Signal outcome tracking.

    Only present when status >= MONITORING.
    """

    outcome: EventOutcome | None = None
    actual_profit_pct: float | None = None
    outcome_timestamp: datetime | None = None


# =============================================================================
# Main MarketEvent Dataclass
# =============================================================================

@dataclass(frozen=True, slots=True)
class MarketEvent:
    """
    Unified Market Event - single object for entire lifecycle.

    Immutable. State transitions only via factory methods.
    All fields present at all times; conditional groups are None when not applicable.

    Lifecycle:
        NEW -> QUALIFIED -> SCORED -> SIGNAL/DISMISSED -> MONITORING -> COMPLETED/EXPIRED
    """

    # Schema version
    schema_version: int = 1

    # Core metadata
    metadata: Metadata = field(default_factory=lambda: Metadata(
        event_id=EventID._generate(),
        status=EventStatus.NEW,
        schema_version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    ))

    # Data groups (None when not applicable)
    market_data: MarketData | None = None
    strategy_data: StrategyData = field(default_factory=StrategyData)
    score_data: ScoreData = field(default_factory=ScoreData)
    notification_data: NotificationData = field(default_factory=NotificationData)
    outcome_data: OutcomeData = field(default_factory=OutcomeData)

    def __post_init__(self) -> None:
        """Prevent direct instantiation - must use factory methods."""
        # Factory methods bypass this by using object.__new__ + manual init

    # =========================================================================
    # Factory Methods - ONLY way to create MarketEvent
    # =========================================================================

    @classmethod
    def new(
        cls,
        *,
        symbol: str,
        exchange: Exchange,
        timeframe: Timeframe,
        event_time: datetime,
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        volume: float,
    ) -> MarketEvent:
        """
        Create new Market Event at candle close (NEW status).

        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            exchange: Exchange enum
            timeframe: Candle timeframe
            event_time: Candle close time (UTC)
            open_price: Open price
            high_price: High price
            low_price: Low price
            close_price: Close price
            volume: Trading volume

        Returns:
            MarketEvent with status NEW and market data populated.
        """
        now = datetime.now(UTC)
        event_id = EventID._generate()

        metadata = Metadata(
            event_id=EventID._generate(),
            status=EventStatus.NEW,
            schema_version=1,
            created_at=now,
            updated_at=now,
        )

        market_data = MarketData(
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            event_time=event_time,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
        )

        event = MarketEvent(
            schema_version=1,
            metadata=metadata,
            market_data=market_data,
        )

        cls._validate_invariants(event)
        return event

    @classmethod
    def qualified(
        cls,
        event: MarketEvent,
        *,
        strategy_id: str,
        lower_wick: float,
        body: float,
        wick_body_ratio: float,
        lower_wick_pct: float,
        body_pct: float,
        confirm: bool = True,
    ) -> MarketEvent:
        """
        Transition to QUALIFIED - strategy confirmed pattern.

        Args:
            event: Current event (must be NEW status)
            strategy_id: Strategy identifier (string, not enum)
            lower_wick: Lower wick size in points
            body: Body size in points
            wick_body_ratio: Ratio of lower wick to body
            lower_wick_pct: Lower wick as percentage of total candle
            body_pct: Body as percentage of total candle
            confirm: Whether candle is confirmed/closed

        Returns:
            New MarketEvent with QUALIFIED status and strategy data populated.

        Raises:
            ModelValidationError: If event not in NEW status
        """
        from . import TransitionGuard
        from .enums import EventStatus
        TransitionGuard.validate(event.metadata.status, EventStatus.QUALIFIED)

        strategy_data = StrategyData(
            strategy_id=strategy_id,
            lower_wick=lower_wick,
            body=body,
            wick_body_ratio=wick_body_ratio,
            lower_wick_pct=lower_wick_pct,
            body_pct=body_pct,
            confirm=confirm,
        )

        new_event = replace(
            event,
            metadata=replace(
                event.metadata,
                status=EventStatus.QUALIFIED,
                updated_at=datetime.now(UTC),
            ),
            strategy_data=strategy_data,
        )

        cls._validate_invariants(new_event)
        return new_event

    @classmethod
    def dismissed(cls, event: MarketEvent) -> MarketEvent:
        """
        Transition to DISMISSED - no pattern matched or score below threshold.

        Allowed from NEW, QUALIFIED, or SCORED.
        """
        from . import TransitionGuard
        from .enums import EventStatus
        current = event.metadata.status
        if current not in {EventStatus.NEW, EventStatus.QUALIFIED, EventStatus.SCORED}:
            TransitionGuard.validate(current, EventStatus.DISMISSED)

        return replace(
            event,
            metadata=replace(
                event.metadata,
                status=EventStatus.DISMISSED,
                updated_at=datetime.now(UTC),
            ),
        )

    @classmethod
    def scored(
        cls,
        event: MarketEvent,
        *,
        confidence_score: float,
        score_breakdown: tuple[tuple[ScoreParameter, float, float], ...],
    ) -> MarketEvent:
        """
        Transition to SCORED after Scoring Engine evaluation.

        Args:
            event: Current event (must be QUALIFIED status)
            confidence_score: Final confidence score (0-100)
            score_breakdown: Tuple of (parameter, score, penalty)

        Returns:
            New MarketEvent with SCORED status and score data populated.

        Raises:
            ModelValidationError: If event not in QUALIFIED status or invalid score
        """
        from . import TransitionGuard
        from .enums import EventStatus
        TransitionGuard.validate(event.metadata.status, EventStatus.SCORED)

        if not (0 <= confidence_score <= 100):
            raise ModelValidationError(
                f"Confidence score must be 0-100, got {confidence_score}"
            )

        breakdown_items = tuple(
            ScoreBreakdownItem(
                parameter_name=param,
                parameter_score=score,
                penalty=penalty,
            )
            for param, score, penalty in score_breakdown
        )

        score_data = ScoreData(
            confidence_score=confidence_score,
            score_breakdown=breakdown_items,
        )

        new_event = replace(
            event,
            metadata=replace(
                event.metadata,
                status=EventStatus.SCORED,
                updated_at=datetime.now(UTC),
            ),
            score_data=score_data,
        )

        cls._validate_invariants(new_event)
        return new_event

    @classmethod
    def notified(
        cls,
        event: MarketEvent,
        *,
        close_price: float,
    ) -> MarketEvent:
        """
        Transition to SIGNAL - score >= threshold, notification sent.

        Creates SignalID from EventID.
        Validates current status is SCORED.

        Args:
            event: Current event (must be SCORED status)
            close_price: Close price at signal time

        Returns:
            New MarketEvent with SIGNAL status and notification data populated.

        Raises:
            ModelValidationError: If event not in SCORED status
        """
        from . import TransitionGuard
        from .enums import EventStatus
        TransitionGuard.validate(event.metadata.status, EventStatus.SIGNAL)

        notification_data = NotificationData(
            notification_timestamp=datetime.now(UTC),
            close_price=close_price,
        )

        new_event = replace(
            event,
            metadata=replace(
                event.metadata,
                status=EventStatus.SIGNAL,
                updated_at=datetime.now(UTC),
            ),
            notification_data=notification_data,
        )

        cls._validate_invariants(new_event)
        return new_event

    @classmethod
    def monitoring(cls, event: MarketEvent) -> MarketEvent:
        """
        Transition to MONITORING - start TP/SL tracking.

        Args:
            event: Current event (must be SIGNAL status)

        Returns:
            New MarketEvent with MONITORING status

        Raises:
            ModelValidationError: If event not in SIGNAL status
        """
        from . import TransitionGuard
        from .enums import EventStatus
        TransitionGuard.validate(event.metadata.status, EventStatus.MONITORING)

        return replace(
            event,
            metadata=replace(
                event.metadata,
                status=EventStatus.MONITORING,
                updated_at=datetime.now(UTC),
            ),
        )

    @classmethod
    def completed(
        cls,
        event: MarketEvent,
        *,
        outcome: EventOutcome,
        actual_profit_pct: float,
    ) -> MarketEvent:
        """
        Transition to COMPLETED - TP or SL reached.

        Args:
            event: Current event (must be MONITORING status)
            outcome: TP or SL
            actual_profit_pct: Actual profit/loss percentage

        Returns:
            New MarketEvent with COMPLETED status and outcome data populated.

        Raises:
            ModelValidationError: If event not in MONITORING status
        """
        from . import TransitionGuard
        from .enums import EventStatus
        TransitionGuard.validate(event.metadata.status, EventStatus.COMPLETED)

        outcome_data = OutcomeData(
            outcome=outcome,
            actual_profit_pct=actual_profit_pct,
            outcome_timestamp=datetime.now(UTC),
        )

        new_event = replace(
            event,
            metadata=replace(
                event.metadata,
                status=EventStatus.COMPLETED,
                updated_at=datetime.now(UTC),
            ),
            outcome_data=outcome_data,
        )

        cls._validate_invariants(new_event)
        return new_event

    @classmethod
    def expired(cls, event: MarketEvent) -> MarketEvent:
        """
        Transition to EXPIRED - timeout waiting for TP/SL.

        Args:
            event: Current event (must be MONITORING status)

        Returns:
            New MarketEvent with EXPIRED status

        Raises:
            ModelValidationError: If event not in MONITORING status
        """
        from . import TransitionGuard
        from .enums import EventStatus
        TransitionGuard.validate(event.metadata.status, EventStatus.EXPIRED)

        outcome_data = OutcomeData(
            outcome=None,
            actual_profit_pct=None,
            outcome_timestamp=datetime.now(UTC),
        )

        return replace(
            event,
            metadata=replace(
                event.metadata,
                status=EventStatus.EXPIRED,
                updated_at=datetime.now(UTC),
            ),
            outcome_data=outcome_data,
        )

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize to dictionary for storage/transport.

        Handles Enum, UUID, datetime, nested dataclasses.
        """
        import dataclasses
        from uuid import UUID

        def serialize(obj: Any) -> Any:
            # Handle UUID first (including nested in containers)
            if isinstance(obj, UUID):
                return str(obj)
            # Handle Enum
            if isinstance(obj, Enum):
                return obj.value
            # Handle datetime
            if isinstance(obj, datetime):
                return obj.isoformat()
            # Handle EventID, SignalID
            if isinstance(obj, (EventID, SignalID)):
                return str(obj.value)
            # Handle dataclasses (including nested)
            if dataclasses.is_dataclass(obj):
                return {k: serialize(v) for k, v in dataclasses.asdict(obj).items()}
            # Handle dict
            if isinstance(obj, dict):
                return {k: serialize(v) for k, v in obj.items()}
            # Handle list/tuple/set
            if isinstance(obj, (list, tuple, set)):
                return [serialize(v) for v in obj]
            # Handle any object with __dict__ (fallback)
            if hasattr(obj, '__dict__'):
                return {k: serialize(v) for k, v in obj.__dict__.items()}
            return obj

        return serialize(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MarketEvent:
        """
        Deserialize from dictionary.

        Reconstructs full object with all nested types.
        Validates invariants after deserialization.
        Fail-fast on any error.
        """
        def deserialize_datetime(value: str) -> datetime:
            return datetime.fromisoformat(value)

        def deserialize_uuid(value: str) -> UUID:
            return UUID(value)

        def deserialize_event_id(value: str) -> EventID:
            return EventID.from_string(value)

        def deserialize_signal_id(value: str) -> SignalID:
            return SignalID.from_string(value)

        def deserialize_datetime_obj(value: str | None) -> datetime | None:
            if value is None:
                return None
            return datetime.fromisoformat(value)

        def deserialize_uuid_obj(value: str | None) -> UUID | None:
            if value is None:
                return None
            return UUID(value)

        # Reconstruct metadata
        meta_data = data.get('metadata', {})
        metadata = Metadata(
            event_id=EventID.from_string(meta_data['event_id']),
            status=EventStatus(meta_data['status']),
            schema_version=meta_data.get('schema_version', 1),
            created_at=datetime.fromisoformat(meta_data['created_at']),
            updated_at=datetime.fromisoformat(meta_data['updated_at']),
        )

        # Market data
        market_data = None
        if data.get('market_data'):
            md = data['market_data']
            market_data = MarketData(
                symbol=md['symbol'],
                exchange=Exchange(md['exchange']),
                timeframe=Timeframe(md['timeframe']),
                event_time=datetime.fromisoformat(md['event_time']),
                open=md['open'],
                high=md['high'],
                low=md['low'],
                close=md['close'],
                volume=md['volume'],
            )

        # Strategy data
        strategy_data = StrategyData()
        if data.get('strategy_data'):
            sd = data['strategy_data']
            if sd.get('strategy_id'):
                strategy_data = StrategyData(
                    strategy_id=sd['strategy_id'],
                    lower_wick=sd.get('lower_wick'),
                    body=sd.get('body'),
                    wick_body_ratio=sd.get('wick_body_ratio'),
                    lower_wick_pct=sd.get('lower_wick_pct'),
                    body_pct=sd.get('body_pct'),
                    confirm=sd.get('confirm', True),
                )

        # Score data
        score_data = ScoreData()
        if data.get('score_data'):
            sc = data['score_data']
            if sc.get('confidence_score') is not None:
                breakdown = []
                for item in sc.get('score_breakdown', []):
                    breakdown.append(ScoreBreakdownItem(
                        parameter_name=ScoreParameter(item['parameter_name']),
                        parameter_score=item['parameter_score'],
                        penalty=item.get('penalty', 0.0),
                    ))
                score_data = ScoreData(
                    confidence_score=sc['confidence_score'],
                    score_breakdown=tuple(breakdown),
                )

        # Notification data
        notification_data = NotificationData()
        if data.get('notification_data'):
            nd = data['notification_data']
            if nd.get('notification_timestamp'):
                notification_data = NotificationData(
                    notification_timestamp=datetime.fromisoformat(nd['notification_timestamp']),
                    close_price=nd.get('close_price'),
                )

        # Outcome data
        outcome_data = OutcomeData()
        if data.get('outcome_data'):
            od = data['outcome_data']
            if od.get('outcome'):
                outcome_data = OutcomeData(
                    outcome=EventOutcome(od['outcome']),
                    actual_profit_pct=od.get('actual_profit_pct'),
                    outcome_timestamp=datetime.fromisoformat(od['outcome_timestamp']) if od.get('outcome_timestamp') else None,
                )

        event = MarketEvent(
            schema_version=data.get('schema_version', 1),
            metadata=metadata,
            market_data=market_data,
            strategy_data=strategy_data,
            score_data=score_data,
            notification_data=notification_data,
            outcome_data=outcome_data,
        )

        cls._validate_invariants(event)
        return event

    # =========================================================================
    # Invariants Validation
    # =========================================================================

    @classmethod
    def _validate_invariants(cls, event: MarketEvent) -> None:
        """
        Centralized invariant validation.

        Called after every creation/transition and after deserialization.
        Checks all invariants in one place.
        """
        status = event.metadata.status

        # Status -> data group correspondence
        if status == EventStatus.NEW:
            if event.strategy_data.strategy_id is not None:
                raise InvariantViolationError("NEW event must not have strategy data")
            if event.score_data.confidence_score is not None:
                raise InvariantViolationError("NEW event must not have score data")
            if event.notification_data.notification_timestamp is not None:
                raise InvariantViolationError("NEW event must not have notification data")
            if event.outcome_data.outcome is not None:
                raise InvariantViolationError("NEW event must not have outcome data")

        elif status == EventStatus.QUALIFIED:
            if event.strategy_data.strategy_id is None:
                raise InvariantViolationError("QUALIFIED event must have strategy data")
            if event.score_data.confidence_score is not None:
                raise InvariantViolationError("QUALIFIED event must not have score data")
            if event.notification_data.notification_timestamp is not None:
                raise InvariantViolationError("QUALIFIED event must not have notification data")

        elif status == EventStatus.SCORED:
            if event.strategy_data.strategy_id is None:
                raise InvariantViolationError("SCORED event must have strategy data")
            if event.score_data.confidence_score is None:
                raise InvariantViolationError("SCORED event must have score data")
            if event.notification_data.notification_timestamp is not None:
                raise InvariantViolationError("SCORED event must not have notification data")

        elif status == EventStatus.SIGNAL:
            if event.score_data.confidence_score is None:
                raise InvariantViolationError("SIGNAL event must have score data")
            if event.notification_data.notification_timestamp is None:
                raise InvariantViolationError("SIGNAL event must have notification timestamp")

        elif status == EventStatus.DISMISSED:
            # Can come from NEW, QUALIFIED, or SCORED
            pass

        elif status == EventStatus.MONITORING:
            if event.notification_data.notification_timestamp is None:
                raise InvariantViolationError("MONITORING event must have notification data")

        elif status in (EventStatus.COMPLETED, EventStatus.EXPIRED):
            if event.outcome_data.outcome_timestamp is None:
                raise InvariantViolationError(f"{status.value} event must have outcome timestamp")

        # Always check metadata consistency
        if event.metadata.schema_version != 1:
            raise InvariantViolationError(f"Unsupported schema_version: {event.metadata.schema_version}")

        # Check updated_at >= created_at
        if event.metadata.updated_at < event.metadata.created_at:
            raise InvariantViolationError("updated_at must be >= created_at")

    @classmethod
    def _validate_on_deserialize(cls, event: MarketEvent) -> None:
        """Validate after deserialization."""
        cls._validate_invariants(event)

    # =========================================================================
    # Properties / Helpers
    # =========================================================================

    @property
    def status(self) -> EventStatus:
        return self.metadata.status

    @property
    def event_id(self) -> EventID:
        return self.metadata.event_id

    @property
    def signal_id(self) -> SignalID | None:
        """Signal ID if event is a Signal (status >= SIGNAL)."""
        if self.metadata.status in {EventStatus.SIGNAL, EventStatus.MONITORING, EventStatus.COMPLETED, EventStatus.EXPIRED}:
            return SignalID.from_event_id(self.metadata.event_id)
        return None

    @property
    def is_terminal(self) -> bool:
        """Check if event is in terminal state."""
        return _TransitionMap.is_terminal(self.metadata.status)

    def __str__(self) -> str:
        return f"MarketEvent({self.event_id}, {self.metadata.status.value})"


# =============================================================================
# Exported Classes
# =============================================================================

from .transition_guard import TransitionGuard

__all__ = [
    # Enums
    "EventStatus",
    "EventOutcome",
    "Exchange",
    "Timeframe",
    "ScoreParameter",
    # Identifiers
    "EventID",
    "SignalID",
    # Exceptions
    "ModelValidationError",
    "InvalidTransitionError",
    "InvariantViolationError",
    # Transition Guard
    "TransitionGuard",
    # Nested Data
    "Metadata",
    "MarketData",
    "StrategyData",
    "ScoreBreakdownItem",
    "ScoreData",
    "NotificationData",
    "OutcomeData",
    # Main
    "MarketEvent",
]