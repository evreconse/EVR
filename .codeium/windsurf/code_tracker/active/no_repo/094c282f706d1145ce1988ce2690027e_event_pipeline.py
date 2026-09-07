…”"""
EVRECONSE Event Engine - Event Pipeline.

Pipeline for processing events through stages.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from .context import EventContext


class PipelineStage(ABC):
    """Abstract base class for pipeline stages."""
    
    @property
    @abstractmethod
    def stage_name(self) -> str:
        """Stage name."""
        ...
    
    @property
    @abstractmethod
    def stage_type(self) -> str:
        """Stage type identifier."""
        ...
    
    @abstractmethod
    async def process(self, context: EventContext) -> EventContext:
        """
        Process context through this stage.
        
        Args:
            context: Current event context
            
        Returns:
            Updated context
            
        Raises:
            PipelineError: If stage fails
        """
        ...


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Result of pipeline execution."""
    success: bool
    final_context: EventContext
    stage_results: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    error_stage: str | None = None
    duration_ms: float = 0.0


class PipelineStageBase:
    """Base class for pipeline stages."""
    
    def __init__(self, name: str, stage_type: str = "custom") -> None:
        self._name = name
        self._stage_type = stage_type
    
    @property
    def stage_name(self) -> str:
        return self._name
    
    @property
    def stage_type(self) -> str:
        return self._stage_type
    
    async def process(self, context: EventContext) -> EventContext:
        """
        Process context through this stage.
        
        Args:
            context: Event context
            
        Returns:
            Updated context
        """
        raise NotImplementedError


class PipelineStageValidator:
    """Validation stage - validates event before processing."""
    
    def __init__(self) -> None:
        self._name = "validator"
        self._stage_type = "validation"
    
    @property
    def stage_name(self) -> str:
        return self._name
    
    @property
    def stage_type(self) -> str:
        return self._stage_type
    
    async def process(self, context: EventContext) -> EventContext:
        # Validation happens in context creation
        return context


class PipelineStageStrategy:
    """Strategy evaluation stage."""
    
    def __init__(self, strategy_engine) -> None:
        self._strategy_engine = strategy_engine
        self._name = "strategy"
        self._stage_type = "strategy"
    
    @property
    def stage_name(self) -> str:
        return self._name
    
    @property
    def stage_type(self) -> str:
        return self._stage_type
    
    async def process(self, context: EventContext) -> EventContext:
        """Execute strategy evaluation on the event."""
        from strategy.context import StrategyContext
        from models import MarketEvent
        from core import get_logger
        
        logger = get_logger(__name__)
        logger.info(f"[PIPELINE] Strategy stage: Processing event for {context.symbol}")
        
        # Reconstruct MarketEvent from EventContext
        from models.enums import Exchange, Timeframe
        from models.market_event import MarketEvent as ME
        from datetime import UTC, datetime
        from uuid import uuid4
        
        # Create a minimal MarketEvent for strategy evaluation
        event = ME.new(
            symbol=context.symbol,
            exchange=Exchange(context.exchange),
            timeframe=Timeframe(context.timeframe),
            event_time=context.event_time,
            open_price=context.open_price,
            high_price=context.high_price,
            low_price=context.low_price,
            close_price=context.close_price,
            volume=context.volume,
        )
        
        logger.info(f"[PIPELINE] Strategy stage: MarketEvent reconstructed - O:{context.open_price} H:{context.high_price} L:{context.low_price} C:{context.close_price}")
        
        # Create StrategyContext
        strategy_context = StrategyContext(
            market_event=event,
            config=None,  # Will use default config
            data_provider=None,  # Not needed for basic evaluation
            storage=None,  # Not needed for basic evaluation
        )
        
        # Execute strategy (LW-001)
        try:
            from strategy import LW001Strategy, StrategyConfig
            strategy = LW001Strategy()
            config = StrategyConfig(
                strategy_id="LW-001",
                version="1.0.0",
                parameters={
                    "lower_wick_ratio": 2.0,
                    "liquidation_window": 12,
                    "min_confidence_score": 80,
                },
                enabled=True,
            )
            strategy.initialize(config)
            
            result = await strategy.evaluate(strategy_context)
            
            logger.info(f"[PIPELINE] Strategy stage: Result - qualified={result.qualified}, score={result.score if hasattr(result, 'score') else 'N/A'}")
            
            # Update context with strategy results
            return context.with_updates(
                strategy_id=result.strategy_id,
                lower_wick=event.strategy_data.lower_wick if event.strategy_data else None,
                body=event.strategy_data.body if event.strategy_data else None,
                wick_body_ratio=event.strategy_data.wick_body_ratio if event.strategy_data else None,
                liquidation_volume=event.strategy_data.liquidation_volume if event.strategy_data else None,
                liquidation_reference=event.strategy_data.liquidation_reference_value if event.strategy_data else None,
                status="qualified" if result.qualified else "rejected",
                updated_at=datetime.now(UTC),
            )
        except Exception as e:
            # Log error but continue pipeline
            logger.error(f"[PIPELINE] Strategy stage: Evaluation failed - {e}", exc_info=True)
            return context


class PipelineStageScorer:
    """Scoring stage."""
    
    def __init__(self, scoring_engine) -> None:
        self._scoring_engine = scoring_engine
        self._name = "scorer"
        self._stage_type = "scoring"
    
    @property
    def stage_name(self) -> str:
        return self._name
    
    @property
    def stage_type(self) -> str:
        return self._stage_type
    
    async def process(self, context: EventContext) -> EventContext:
        """Execute scoring on the event."""
        from core import get_logger
        
        logger = get_logger(__name__)
        logger.info(f"[PIPELINE] Scorer stage: Processing event for {context.symbol}")
        
        if not self._scoring_engine or not self._scoring_engine.is_initialized():
            # Scoring engine not available, skip scoring
            logger.warning(f"[PIPELINE] Scorer stage: Scoring engine not initialized, skipping")
            return context
        
        try:
            from scoring.context import ScoringContext, ScoringConfig
            from models import MarketEvent
            from models.enums import Exchange, Timeframe
            from models.market_event import MarketEvent as ME
            from datetime import UTC, datetime
            
            # Reconstruct MarketEvent from EventContext
            event = ME.new(
                symbol=context.symbol,
                exchange=Exchange(context.exchange),
                timeframe=Timeframe(context.timeframe),
                event_time=context.event_time,
                open_price=context.open_price,
                high_price=context.high_price,
                low_price=context.low_price,
                close_price=context.close_price,
                volume=context.volume,
            )
            
            # Create ScoringContext
            scoring_context = ScoringContext(
                market_event=event,
                config=ScoringConfig(
                    scoring_id="lw_001_scoring",
                    version="1.0.0",
                    parameters={},
                    enabled=True,
                    min_confidence_score=80.0,
                ),
                data_provider=None,  # Not needed for basic evaluation
                storage=None,  # Not needed for basic evaluation
            )
            
            result = self._scoring_engine.evaluate(scoring_context)
            
            logger.info(f"[PIPELINE] Scorer stage: Result - score={result.final_score}, qualified={result.qualified}")
            
            # Update context with scoring results
            return context.with_scoring(
                score=result.final_score,
                breakdown={"explanation": result.explanation, "qualified": result.qualified},
            )
        except Exception as e:
            logger.error(f"[PIPELINE] Scorer stage: Evaluation failed - {e}", exc_info=True)
            return context


class PipelineStageNotifier:
    """Notification stage."""
    
    def __init__(self, notification_engine) -> None:
        self._notification_engine = notification_engine
        self._name = "notifier"
        self._stage_type = "notification"
    
    @property
    def stage_name(self) -> str:
        return self._name
    
    @property
    def stage_type(self) -> str:
        return self._stage_type
    
    async def process(self, context: EventContext) -> EventContext:
        """Send notification if event is qualified."""
        from core import get_logger
        
        logger = get_logger(__name__)
        logger.info(f"[PIPELINE] Notifier stage: Processing event for {context.symbol}, confidence_score={context.confidence_score}")
        
        if not self._notification_engine:
            logger.warning(f"[PIPELINE] Notifier stage: Notification engine not available")
            return context
        
        # Send notification if event is qualified (has confidence score above threshold)
        if context.confidence_score and context.confidence_score >= 80.0:
            logger.info(f"[PIPELINE] Notifier stage: Event qualified for notification (score={context.confidence_score} >= 80)")
            try:
                from notification import Notification
                from datetime import UTC, datetime
                
                notification = Notification(
                    notification_id=str(datetime.now(UTC).timestamp()),
                    channel="telegram",
                    priority="high",
                    title=f"Signal: {context.symbol}",
                    message=(
                        f"Strategy: {context.strategy_id or 'LW-001'}\n"
                        f"Symbol: {context.symbol}\n"
                        f"Timeframe: {context.timeframe}\n"
                        f"Score: {context.confidence_score:.1f}/100\n"
                        f"Status: QUALIFIED"
                    ),
                    metadata={
                        "symbol": context.symbol,
                        "exchange": context.exchange,
                        "timeframe": context.timeframe,
                        "score": context.confidence_score,
                        "strategy_id": context.strategy_id,
                    },
                )
                
                logger.info(f"[PIPELINE] Notifier stage: Sending notification to Telegram")
                await self._notification_engine.send(notification)
                logger.info(f"[PIPELINE] Notifier stage: Notification sent successfully")
            except Exception as e:
                logger.error(f"[PIPELINE] Notifier stage: Notification failed - {e}", exc_info=True)
        else:
            logger.info(f"[PIPELINE] Notifier stage: Event not qualified for notification (score={context.confidence_score} < 80 or None)")
        
        return context


class PipelineStageOutcomeTracker:
    """Outcome tracking stage."""
    
    def __init__(self, outcome_tracker) -> None:
        self._outcome_tracker = outcome_tracker
        self._name = "outcome_tracker"
        self._stage_type = "outcome_tracking"
    
    @property
    def stage_name(self) -> str:
        return self._name
    
    @property
    def stage_type(self) -> str:
        return self._stage_type
    
    async def process(self, context: EventContext) -> EventContext:
        if context.market_event and context.market_event.status in ["monitoring", "completed", "expired"]:
            # Track outcome
            pass
        return context


class PipelineStageStorage:
    """Persistence stage."""
    
    def __init__(self, storage_service) -> None:
        self._storage = storage_service
        self._name = "storage"
        self._stage_type = "persistence"
    
    @property
    def stage_name(self) -> str:
        return self._name
    
    @property
    def stage_type(self) -> str:
        return self._stage_type
    
    async def process(self, context: EventContext) -> EventContext:
        """Persist event to storage."""
        from core import get_logger
        
        logger = get_logger(__name__)
        logger.info(f"[PIPELINE] Storage stage: Processing event for {context.symbol}")
        
        if not self._storage:
            logger.warning(f"[PIPELINE] Storage stage: Storage service not available")
            return context
        
        try:
            from models import MarketEvent
            from models.enums import Exchange, Timeframe
            from models.market_event import MarketEvent as ME
            from datetime import UTC, datetime
            
            # Reconstruct MarketEvent from EventContext
            event = ME.new(
                symbol=context.symbol,
                exchange=Exchange(context.exchange),
                timeframe=Timeframe(context.timeframe),
                event_time=context.event_time,
                open_price=context.open_price,
                high_price=context.high_price,
                low_price=context.low_price,
                close_price=context.close_price,
                volume=context.volume,
            )
            
            logger.info(f"[PIPELINE] Storage stage: MarketEvent reconstructed for storage")
            
            # Add strategy data if available
            if context.strategy_id:
                event = event.qualified(
                    strategy_id=context.strategy_id,
                    lower_wick=context.lower_wick or 0.0,
                    body=context.body or 0.0,
                    wick_body_ratio=context.wick_body_ratio or 0.0,
                    lower_wick_pct=0.0,
                    body_pct=0.0,
                    liquidation_volume=context.liquidation_volume or 0.0,
                    liquidation_reference_value=context.liquidation_reference or 0.0,
                )
            
            # Store the event
            await self._storage.store(event)
            logger.info(f"[PIPELINE] Storage stage: Event stored successfully")
        except Exception as e:
            logger.error(f"[PIPELINE] Storage stage: Storage failed - {e}", exc_info=True)
        
        return context


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    """Pipeline configuration."""
    stages: tuple[str, ...] = (
        "validator",
        "strategy",
        "scorer",
        "notifier",
        "outcome_tracker",
        "storage",
    )
    continue_on_error: bool = False
    timeout_seconds: float = 30.0


class EventPipeline:
    """
    Event processing pipeline.
    
    Executes stages sequentially, passing context through each.
    """
    
    def __init__(
        self,
        stages: list,
        config: PipelineConfig | None = None,
    ) -> None:
        self._stages = stages
        self._config = config or PipelineConfig()
        self._stages_dict = {s.stage_name: s for s in stages}
    
    async def execute(self, context: EventContext) -> PipelineResult:
        """
        Execute pipeline on context.
        
        Args:
            context: Initial event context
            
        Returns:
            PipelineResult with final context and results
        """
        start_time = time.monotonic()
        current_context = context
        stage_results = {}
        error = None
        error_stage = None
        
        for stage in self._stages:
            stage_start = time.monotonic()
            try:
                current_context = await stage.process(current_context)
                stage_duration = (time.monotonic() - stage_start) * 1000
                stage_results[stage.stage_name] = {
                    "success": True,
                    "duration_ms": stage_duration,
                }
            except Exception as e:
                stage_duration = (time.monotonic() - stage_start) * 1000
                error = str(e)
                error_stage = stage.stage_name
                stage_results[stage.stage_name] = {
                    "success": False,
                    "duration_ms": stage_duration,
                    "error": str(e),
                }
                
                if not self._config.continue_on_error:
                    break
        
        total_duration_ms = (time.monotonic() - start_time) * 1000
        
        return PipelineResult(
            success=error is None,
            final_context=current_context,
            stage_results=stage_results,
            error=error,
            error_stage=error_stage,
            duration_ms=total_duration_ms,
        )
    
    def get_stage(self, name: str) -> Any | None:
        """Get stage by name."""
        return self._stages_dict.get(name)
    
    def add_stage(self, stage: Any) -> None:
        """Add stage to pipeline."""
        self._stages.append(stage)
        self._stages_dict[stage.stage_name] = stage
    
    def remove_stage(self, name: str) -> bool:
        """Remove stage by name."""
        for i, s in enumerate(self._stages):
            if s.stage_name == name:
                self._stages.pop(i)
                self._stages_dict.pop(name, None)
                return True
        return False


def create_default_pipeline(
    strategy_engine=None,
    scoring_engine=None,
    notification_engine=None,
    outcome_tracker=None,
    storage_service=None,
) -> EventPipeline:
    """Create default event pipeline."""
    stages = [
        PipelineStageValidator(),
        PipelineStageStrategy(strategy_engine),
        PipelineStageScorer(scoring_engine),
        PipelineStageNotifier(notification_engine),
        PipelineStageOutcomeTracker(outcome_tracker),
        PipelineStageStorage(storage_service),
    ]
    
    return EventPipeline(stages=stages)€ *cascade08€¬*cascade08¬„ *cascade08„¸ *cascade08¸ î' *cascade08î'•)*cascade08•)÷/ *cascade08÷/‚0*cascade08‚0‹0 *cascade08‹00*cascade0800 *cascade080“0*cascade08“0£0 *cascade08£0¥0*cascade08¥0ª0 *cascade08ª0¹0*cascade08¹0¥4 *cascade08¥4Ñ4 *cascade08Ñ4„6*cascade08„6†7 *cascade08†7ç7*cascade08ç7ËC *cascade08ËCÏD*cascade08ÏDÒF *cascade08ÒFÊG*cascade08ÊGËG *cascade08ËG·K *cascade08·KîK *cascade08îKĞM*cascade08ĞMñM *cascade08ñMÍN*cascade08ÍNÓO *cascade08ÓOŞO *cascade08ŞO•P *cascade08•P–Q*cascade08–QºQ *cascade08ºQ»Q *cascade08»QÃQ*cascade08ÃQÄQ *cascade08ÄQÍQ*cascade08ÍQÎQ *cascade08ÎQŠR*cascade08ŠRŒR *cascade08ŒRîR*cascade08îRïR *cascade08ïRùR*cascade08ùRúR *cascade08úRıR*cascade08ıRşR *cascade08şRÿR*cascade08ÿR€S *cascade08€SˆS*cascade08ˆS‰S *cascade08‰S¢S*cascade08¢S£S *cascade08£S¬S*cascade08¬S®S *cascade08®S†T*cascade08†T‡T *cascade08‡TˆT*cascade08ˆTT *cascade08T’T*cascade08’T“T *cascade08“T²T*cascade08²T³T *cascade08³TÔT*cascade08ÔTÕT *cascade08ÕTáT*cascade08áTâT *cascade08âTæT*cascade08æTçT *cascade08çTíT*cascade08íTîT *cascade08îT¨U*cascade08¨U©U *cascade08©U‘V*cascade08‘V’V *cascade08’V—V*cascade08—V˜V *cascade08˜V›V*cascade08›VV *cascade08V¨V*cascade08¨V©V *cascade08©VÕV*cascade08ÕVÚV *cascade08ÚVñV*cascade08ñVòV *cascade08òVšW*cascade08šW›W *cascade08›W´W*cascade08´W·W *cascade08·WîW*cascade08îWïW *cascade08ïWõW*cascade08õWöW *cascade08öWÿW*cascade08ÿW€X *cascade08€X§X*cascade08§X©X *cascade08©X¼X*cascade08¼X½X *cascade08½XÈX*cascade08ÈXÕX *cascade08ÕXâX*cascade08âXãX *cascade08ãXèX*cascade08èXéX *cascade08éXëX*cascade08ëXìX *cascade08ìXúX*cascade08úXûX *cascade08ûXşY *cascade08şYÚZ*cascade08ÚZæZ *cascade08æZòZ *cascade08òZŒ[*cascade08Œ[™[ *cascade08™[¡[*cascade08¡[¢[ *cascade08¢[¼[*cascade08¼[½[ *cascade08½[À[*cascade08À[Á[ *cascade08Á[Å[*cascade08Å[Æ[ *cascade08Æ[Ì[*cascade08Ì[Í[ *cascade08Í[Î[*cascade08Î[Ó[ *cascade08Ó[Ô[ *cascade08Ô[×[*cascade08×[Ø[ *cascade08Ø[Ü[*cascade08Ü[İ[ *cascade08İ[æ[*cascade08æ[ó[ *cascade08ó[ù[*cascade08ù[ú[ *cascade08ú[ş[*cascade08ş[€\ *cascade08€\\*cascade08\ƒ\ *cascade08ƒ\‰\*cascade08‰\ \ *cascade08 \³\*cascade08³\´\ *cascade08´\µ\*cascade08µ\¶\ *cascade08¶\·\*cascade08·\¸\ *cascade08¸\À\*cascade08À\Â\ *cascade08Â\Æ\*cascade08Æ\Ç\ *cascade08Ç\Î\*cascade08Î\Ï\ *cascade08Ï\à\*cascade08à\á\ *cascade08á\ã\*cascade08ã\ä\ *cascade08ä\å\*cascade08å\æ\ *cascade08æ\ì\*cascade08ì\÷\ *cascade08÷\ı\*cascade08ı\…] *cascade08…]‰]*cascade08‰]] *cascade08]“]*cascade08“]—] *cascade08—]¢]*cascade08¢]¨] *cascade08¨]­]*cascade08­]®] *cascade08®]¶]*cascade08¶]·] *cascade08·]¹]*cascade08¹]º] *cascade08º]»]*cascade08»]¼] *cascade08¼]¾]*cascade08¾]¿] *cascade08¿]À]*cascade08À]Á] *cascade08Á]Ã]*cascade08Ã]Æ] *cascade08Æ]Ş]*cascade08Ş]ß] *cascade08ß]ö]*cascade08ö]ø] *cascade08ø]†^*cascade08†^‘^ *cascade08‘^™g *cascade08™gÁg *cascade08Ágõh*cascade08õhŠi *cascade08Šiái*cascade08áiık *cascade08ıkÿk *cascade08ÿkl*cascade08ll *cascade08l˜l*cascade08˜l™l *cascade08™lÕl*cascade08ÕlÖl *cascade08Öl²m*cascade08²m³m *cascade08³m¦o*cascade08¦o§o *cascade08§o²o*cascade08²o³o *cascade08³oÊo*cascade08ÊoËo *cascade08ËoÙo*cascade08ÙoÚo *cascade08Úoão*cascade08ãoäo *cascade08äoèo*cascade08èoéo *cascade08éo÷o *cascade08÷oàp*cascade08àp­q *cascade08­q¯q *cascade08¯q§v *cascade08§v®v*cascade08®v¯v *cascade08¯v±v*cascade08±v²v *cascade08²v´v*cascade08´vµv *cascade08µvÂv*cascade08ÂvÃv *cascade08ÃvÇv*cascade08ÇvÈv *cascade08ÈvËv*cascade08ËvÌv *cascade08ÌvÏv*cascade08ÏvÒv *cascade08Òv×v*cascade08×vØv *cascade08ØvÚv*cascade08ÚvÜv *cascade08ÜvŞv*cascade08Şvßv *cascade08ßvév*cascade08évêv *cascade08êvív*cascade08ív÷v *cascade08÷vüv*cascade08üvıv *cascade08ıv€w*cascade08€ww *cascade08w‚w*cascade08‚wƒw *cascade08ƒw„w*cascade08„w†w *cascade08†w‡w*cascade08‡wˆw *cascade08ˆwŠw*cascade08Šw‹w *cascade08‹wŒw*cascade08Œw¨w *cascade08¨wÂw*cascade08ÂwĞw *cascade08ĞwÒw*cascade08Òw×w *cascade08×wæw*cascade08æwğw *cascade08ğw…” *cascade082^file:///C:/Users/user/Documents/Default%20Project/EVRECONSE/src/event_engine/event_pipeline.py