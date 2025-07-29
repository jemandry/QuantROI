import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum

try:
    from simulation_store import TimescaleSimulationStore
    from news_sentiment_analyzer import NewsSentimentAnalyzer
except ImportError:
    from .simulation_store import TimescaleSimulationStore
    from .news_sentiment_analyzer import NewsSentimentAnalyzer

try:
    from enhanced_causal_trading_model import QoSRequirements, MarketData, AdaptiveStrategyManager
except ImportError:
    try:
        from .enhanced_causal_trading_model import QoSRequirements, MarketData, AdaptiveStrategyManager
    except ImportError:
        logging.warning("Enhanced causal trading model not available - using fallback")
        QoSRequirements = None
        MarketData = None
        AdaptiveStrategyManager = None

class TimescaleLevel(Enum):
    MILLISECOND = "ms"
    SECOND = "sec"
    MINUTE = "min"
    HOUR = "hour"

class MultiTimescaleDecisionEngine:
    """
    Multi-timescale decision engine integrating with existing QoSRouter
    Handles millisecond HFT, second news reactions, minute intraday, hour macro
    """
    
    def __init__(self):
        self.sim_store = TimescaleSimulationStore()
        self.sentiment_analyzer = NewsSentimentAnalyzer()
        self.strategy_manager = AdaptiveStrategyManager() if AdaptiveStrategyManager else None
        
        self.handlers = {
            TimescaleLevel.MILLISECOND: self.handle_millisecond_hft,
            TimescaleLevel.SECOND: self.handle_second_news,
            TimescaleLevel.MINUTE: self.handle_minute_intraday,
            TimescaleLevel.HOUR: self.handle_hour_macro
        }
        
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """Initialize all components"""
        await self.sim_store.initialize()
        
    def determine_timescale(self, event: Dict[str, Any], qos_requirements: Any) -> TimescaleLevel:
        """Determine appropriate timescale based on event and QoS requirements"""
        
        if hasattr(qos_requirements, 'latency_requirement') and qos_requirements.latency_requirement < 1:
            return TimescaleLevel.MILLISECOND
        elif event.get('latency_requirement', 1000) < 1:
            return TimescaleLevel.MILLISECOND
            
        elif event.get('event_type') == 'news' or 'sentiment' in event:
            return TimescaleLevel.SECOND
            
        elif event.get('event_type') in ['strategy_signal', 'market_regime_change']:
            return TimescaleLevel.MINUTE
            
        else:
            return TimescaleLevel.HOUR
    
    async def process_multi_timescale_event(self, event: Dict[str, Any], qos_requirements: Any) -> Dict[str, Any]:
        """Main entry point for multi-timescale event processing"""
        
        timescale = self.determine_timescale(event, qos_requirements)
        handler = self.handlers[timescale]
        
        start_time = datetime.now()
        result = await handler(event)
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return {
            'result': result,
            'timescale': timescale.value,
            'processing_time_ms': processing_time,
            'timestamp': datetime.now().isoformat()
        }
    
    async def handle_millisecond_hft(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Millisecond HFT decisions using simulation lookup (<5ms target)"""
        try:
            symbol = event.get('symbol', 'UNKNOWN')
            
            sim_result = await self.sim_store.retrieve_simulation("arbitrage", "ms", time_range_minutes=1)
            
            if sim_result and sim_result.get('profit', 0) > 0:
                return {
                    "type": "ORDER",
                    "action": sim_result.get('action', 'buy'),
                    "quantity": sim_result.get('quantity', 100),
                    "symbol": symbol,
                    "strategy": "hft_arbitrage",
                    "confidence": sim_result.get('confidence', 0.8)
                }
            
            return {"type": "HOLD", "reason": "no_arbitrage_opportunity"}
            
        except Exception as e:
            self.logger.error(f"Error in millisecond HFT processing: {e}")
            return {"type": "ERROR", "message": str(e)}
    
    async def handle_second_news(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Second-level news sentiment processing (<1s target)"""
        try:
            news_text = event.get('news_text', event.get('text', ''))
            symbol = event.get('symbol', 'GENERAL')
            
            if not news_text:
                return {"type": "HOLD", "reason": "no_news_text"}
            
            sentiment_score = self.sentiment_analyzer.score_news(news_text)
            
            self.sentiment_analyzer.store_news(news_text, sentiment_score, datetime.now(), symbol)
            
            signal = self.sentiment_analyzer.generate_trading_signal(sentiment_score, symbol)
            
            if signal:
                return signal
            
            return {
                "type": "HOLD", 
                "sentiment_score": sentiment_score,
                "reason": f"sentiment_neutral={sentiment_score:.3f}"
            }
            
        except Exception as e:
            self.logger.error(f"Error in news sentiment processing: {e}")
            return {"type": "ERROR", "message": str(e)}
    
    async def handle_minute_intraday(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Minute-level intraday strategy adjustments"""
        try:
            symbol = event.get('symbol', 'UNKNOWN')
            
            sim_result = await self.sim_store.retrieve_simulation("momentum", "min", time_range_minutes=30)
            
            if sim_result and sim_result.get('signal') == 'crossover':
                return {
                    "type": "ORDER",
                    "action": sim_result.get('action', 'buy'),
                    "quantity": sim_result.get('quantity', 500),
                    "symbol": symbol,
                    "strategy": "momentum_crossover",
                    "confidence": sim_result.get('confidence', 0.7)
                }
            
            return {"type": "HOLD", "reason": "no_momentum_signal"}
            
        except Exception as e:
            self.logger.error(f"Error in minute intraday processing: {e}")
            return {"type": "ERROR", "message": str(e)}
    
    async def handle_hour_macro(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Hour-level macro rebalancing decisions"""
        try:
            portfolio_id = event.get('portfolio_id', 'default')
            
            sim_result = await self.sim_store.retrieve_simulation("macro_rebalance", "hour", time_range_minutes=480)  # 8 hours
            
            if sim_result:
                return {
                    "type": "REBALANCE",
                    "action": sim_result.get('action', 'rebalance'),
                    "allocation": sim_result.get('metadata', {}).get('allocation', {}),
                    "portfolio_id": portfolio_id,
                    "strategy": "macro_rebalancing",
                    "confidence": sim_result.get('confidence', 0.6)
                }
            
            return {"type": "HOLD", "reason": "no_rebalancing_signal"}
            
        except Exception as e:
            self.logger.error(f"Error in hour macro processing: {e}")
            return {"type": "ERROR", "message": str(e)}
