import asyncio
import logging
import numpy as np
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
        
        try:
            from batch_simulation_engine import BatchSimulationEngine
            self.batch_sim_engine = BatchSimulationEngine()
            self.cached_results_available = True
        except ImportError:
            from .batch_simulation_engine import BatchSimulationEngine
            self.batch_sim_engine = BatchSimulationEngine()
            self.cached_results_available = True
        except Exception as e:
            logging.warning(f"Batch simulation engine not available: {e}")
            self.batch_sim_engine = None
            self.cached_results_available = False
        
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
        """Millisecond HFT decisions using cached simulation lookup (<1s target)"""
        try:
            symbol = event.get('symbol', 'UNKNOWN')
            
            if self.cached_results_available:
                cached_result = await self.batch_sim_engine.query_cached_simulation(
                    symbol=symbol,
                    strategy_type="arbitrage",
                    scenario_type="high_volatility"
                )
                
                if cached_result and cached_result.get('confidence_score', 0) > 0.7:
                    return {
                        "type": "ORDER",
                        "action": "buy" if cached_result['outcomes'].get('bullseye_profit', 0) > 0 else "sell",
                        "quantity": min(1000, int(cached_result['confidence_score'] * 500)),
                        "symbol": symbol,
                        "strategy": "cached_hft_arbitrage",
                        "confidence": cached_result['confidence_score'],
                        "source": "cached_simulation",
                        "stock_category": cached_result.get('stock_metrics', {}).get('market_cap_category', 'unknown')
                    }
            
            sim_result = await self.sim_store.retrieve_simulation("arbitrage", "ms", time_range_minutes=1)
            
            if sim_result and sim_result.get('profit', 0) > 0:
                return {
                    "type": "ORDER",
                    "action": sim_result.get('action', 'buy'),
                    "quantity": sim_result.get('quantity', 100),
                    "symbol": symbol,
                    "strategy": "hft_arbitrage",
                    "confidence": sim_result.get('confidence', 0.8),
                    "source": "real_time_simulation"
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
    
    async def handle_option_sniffing(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle option chain sniffing for unusual activity detection"""
        try:
            symbol = event.get('symbol', 'UNKNOWN')
            option_data = event.get('option_data', {})
            
            if not option_data:
                return {"type": "HOLD", "reason": "no_option_data"}
            
            put_volume = option_data.get('put_volume', 0)
            call_volume = option_data.get('call_volume', 0)
            pcr_volume = put_volume / call_volume if call_volume > 0 else 0
            
            iv_change = option_data.get('iv_change', 0)
            volume_spike = option_data.get('volume_spike_ratio', 1.0)
            gamma_exposure = option_data.get('gamma_exposure', 0)
            
            unusual_activity_score = 0.0
            
            if pcr_volume > 1.5:  # High put activity
                unusual_activity_score += 0.3
            elif pcr_volume < 0.5:  # High call activity
                unusual_activity_score += 0.3
            
            if volume_spike > 2.0:
                unusual_activity_score += 0.4
            
            if abs(iv_change) > 0.1:
                unusual_activity_score += 0.2
            
            if abs(gamma_exposure) > 1000000:  # Large gamma exposure
                unusual_activity_score += 0.1
            
            if unusual_activity_score > 0.6:  # 60% threshold for action
                action = "buy" if pcr_volume < 0.8 else "sell"
                confidence = min(unusual_activity_score, 1.0)
                
                return {
                    "type": "ORDER",
                    "action": action,
                    "quantity": int(500 * confidence),
                    "symbol": symbol,
                    "strategy": "option_sniffing",
                    "confidence": confidence,
                    "uoa_score": unusual_activity_score,
                    "indicators": {
                        "pcr_volume": pcr_volume,
                        "iv_change": iv_change,
                        "volume_spike": volume_spike,
                        "gamma_exposure": gamma_exposure
                    }
                }
            
            return {
                "type": "HOLD", 
                "reason": f"uoa_score_below_threshold={unusual_activity_score:.3f}",
                "uoa_score": unusual_activity_score
            }
            
        except Exception as e:
            self.logger.error(f"Error in option sniffing processing: {e}")
            return {"type": "ERROR", "message": str(e)}
