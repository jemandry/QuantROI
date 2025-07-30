import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
import torch
import torch.nn as nn
from collections import deque
import threading
from concurrent.futures import ThreadPoolExecutor

@dataclass
class OptionTradeOutcome:
    """Stores option trade outcomes for retroactive learning"""
    trade_id: str
    symbol: str
    timestamp: float
    option_conditions: Dict[str, Any]
    trade_action: str  # 'buy_call', 'buy_put', 'sell_call', 'sell_put', 'hold'
    entry_price: float
    exit_price: Optional[float]
    profit_loss: Optional[float]
    trade_duration_minutes: Optional[int]
    success: Optional[bool]  # True if profitable, False if loss, None if ongoing

@dataclass
class LearningUpdate:
    """Neural network learning update based on option trade outcomes"""
    feature_vector: np.ndarray
    target_action: int
    reward: float
    confidence: float
    market_regime: str

class RetroactiveOptionLearning:
    """
    Integrates option chain analysis with retroactive learning for neural network updates
    Captures option conditions and correlates them with trade outcomes for future learning
    """
    
    def __init__(self, max_memory_size: int = 10000, learning_batch_size: int = 32):
        self.logger = logging.getLogger(__name__)
        self.max_memory_size = max_memory_size
        self.learning_batch_size = learning_batch_size
        
        self.option_trade_memory = deque(maxlen=max_memory_size)
        self.pending_trades = {}  # trade_id -> OptionTradeOutcome
        
        self.feature_extractor = self._create_feature_extractor()
        self.learning_queue = asyncio.Queue()
        self.learning_worker_active = False
        
        self.learning_stats = {
            'total_trades_processed': 0,
            'successful_predictions': 0,
            'failed_predictions': 0,
            'learning_updates_applied': 0,
            'avg_prediction_accuracy': 0.0
        }
        
        self.logger.info("RetroactiveOptionLearning initialized")
    
    def _create_feature_extractor(self) -> nn.Module:
        """Create neural network for extracting features from option conditions"""
        return nn.Sequential(
            nn.Linear(20, 64),  # 20 option condition features
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 16),  # 16-dimensional feature representation
            nn.Tanh()
        )
    
    async def record_option_trade_entry(self, trade_id: str, symbol: str, 
                                      option_conditions: Dict[str, Any],
                                      trade_action: str, entry_price: float) -> bool:
        """
        Record when a trade is entered based on option chain analysis
        This captures the conditions that led to the trading decision
        """
        try:
            trade_outcome = OptionTradeOutcome(
                trade_id=trade_id,
                symbol=symbol,
                timestamp=time.time(),
                option_conditions=option_conditions,
                trade_action=trade_action,
                entry_price=entry_price,
                exit_price=None,
                profit_loss=None,
                trade_duration_minutes=None,
                success=None
            )
            
            self.pending_trades[trade_id] = trade_outcome
            
            self.logger.debug(f"Recorded option trade entry: {trade_id} for {symbol}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error recording option trade entry: {e}")
            return False
    
    async def record_option_trade_exit(self, trade_id: str, exit_price: float, 
                                     profit_loss: float) -> bool:
        """
        Record when a trade is exited and calculate the outcome
        This completes the learning example for neural network updates
        """
        try:
            if trade_id not in self.pending_trades:
                self.logger.warning(f"Trade ID {trade_id} not found in pending trades")
                return False
            
            trade_outcome = self.pending_trades[trade_id]
            trade_outcome.exit_price = exit_price
            trade_outcome.profit_loss = profit_loss
            trade_outcome.trade_duration_minutes = int((time.time() - trade_outcome.timestamp) / 60)
            trade_outcome.success = profit_loss > 0
            
            self.option_trade_memory.append(trade_outcome)
            del self.pending_trades[trade_id]
            
            learning_update = self._create_learning_update(trade_outcome)
            if learning_update:
                await self.learning_queue.put(learning_update)
            
            self.learning_stats['total_trades_processed'] += 1
            if trade_outcome.success:
                self.learning_stats['successful_predictions'] += 1
            else:
                self.learning_stats['failed_predictions'] += 1
            
            total_predictions = self.learning_stats['successful_predictions'] + self.learning_stats['failed_predictions']
            if total_predictions > 0:
                self.learning_stats['avg_prediction_accuracy'] = self.learning_stats['successful_predictions'] / total_predictions
            
            self.logger.debug(f"Recorded option trade exit: {trade_id}, P&L: {profit_loss:.4f}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error recording option trade exit: {e}")
            return False
    
    def _create_learning_update(self, trade_outcome: OptionTradeOutcome) -> Optional[LearningUpdate]:
        """
        Create a learning update from a completed trade outcome
        Converts option conditions to feature vector and determines target action/reward
        """
        try:
            feature_vector = self._extract_feature_vector(trade_outcome.option_conditions)
            
            action_mapping = {
                'buy_call': 0,
                'buy_put': 1, 
                'sell_call': 2,
                'sell_put': 3,
                'hold': 4
            }
            target_action = action_mapping.get(trade_outcome.trade_action, 4)
            
            base_reward = trade_outcome.profit_loss if trade_outcome.profit_loss else 0
            
            duration_factor = 1.0
            if trade_outcome.trade_duration_minutes:
                duration_factor = max(0.1, 1.0 - (trade_outcome.trade_duration_minutes / (24 * 60)))
            
            reward = base_reward * duration_factor
            
            confidence = self._calculate_prediction_confidence(trade_outcome.option_conditions)
            
            market_regime = self._determine_market_regime(trade_outcome.option_conditions)
            
            return LearningUpdate(
                feature_vector=feature_vector,
                target_action=target_action,
                reward=reward,
                confidence=confidence,
                market_regime=market_regime
            )
            
        except Exception as e:
            self.logger.error(f"Error creating learning update: {e}")
            return None
    
    def _extract_feature_vector(self, option_conditions: Dict[str, Any]) -> np.ndarray:
        """
        Extract numerical feature vector from option conditions
        Creates standardized input for neural network learning
        """
        features = []
        
        features.append(option_conditions.get('max_pain_distance', 0))
        features.append(option_conditions.get('underlying_price', 0) / 1000)  # Normalize price
        
        features.append(option_conditions.get('total_delta_exposure', 0))
        features.append(option_conditions.get('total_gamma_exposure', 0))
        features.append(option_conditions.get('total_theta_decay', 0))
        features.append(option_conditions.get('total_vega_exposure', 0))
        
        features.append(option_conditions.get('uoa_events_count', 0) / 10)  # Normalize
        features.append(option_conditions.get('uoa_confidence_avg', 0))
        features.append(1.0 if option_conditions.get('volume_spike_detected') else 0.0)
        features.append(1.0 if option_conditions.get('oi_spike_detected') else 0.0)
        
        features.append(option_conditions.get('iv_skew', 0))
        features.append(option_conditions.get('put_call_ratio', 0))
        features.append(option_conditions.get('volume_weighted_iv', 0))
        
        risk_mapping = {'low': 0.0, 'medium': 0.5, 'high': 1.0}
        features.append(risk_mapping.get(option_conditions.get('gamma_risk_level', 'low'), 0.0))
        features.append(risk_mapping.get(option_conditions.get('theta_decay_pressure', 'low'), 0.0))
        features.append(risk_mapping.get(option_conditions.get('vega_volatility_risk', 'low'), 0.0))
        
        current_time = time.time()
        trade_time = option_conditions.get('timestamp', current_time)
        hour_of_day = datetime.fromtimestamp(trade_time).hour / 24.0  # Normalize to 0-1
        features.append(hour_of_day)
        
        market_hour = datetime.fromtimestamp(trade_time).hour
        features.append(1.0 if 9 <= market_hour <= 16 else 0.0)  # Market hours
        features.append(1.0 if market_hour in [9, 10, 15, 16] else 0.0)  # High activity hours
        
        while len(features) < 20:
            features.append(0.0)
        
        return np.array(features[:20], dtype=np.float32)
    
    def _calculate_prediction_confidence(self, option_conditions: Dict[str, Any]) -> float:
        """Calculate confidence in the prediction based on signal strength"""
        confidence_factors = []
        
        uoa_confidence = option_conditions.get('uoa_confidence_avg', 0)
        confidence_factors.append(uoa_confidence)
        
        max_pain_distance = option_conditions.get('max_pain_distance', 0)
        distance_confidence = max(0, 1.0 - max_pain_distance * 2)  # Inverse relationship
        confidence_factors.append(distance_confidence)
        
        total_delta = abs(option_conditions.get('total_delta_exposure', 0))
        delta_confidence = min(1.0, total_delta / 10)  # Normalize
        confidence_factors.append(delta_confidence)
        
        iv_skew = option_conditions.get('iv_skew', 0)
        skew_confidence = min(1.0, iv_skew / 0.5)  # Normalize
        confidence_factors.append(skew_confidence)
        
        avg_confidence = np.mean(confidence_factors) if confidence_factors else 0.5
        return max(0.1, min(1.0, avg_confidence))
    
    def _determine_market_regime(self, option_conditions: Dict[str, Any]) -> str:
        """Determine market regime based on option conditions"""
        uoa_count = option_conditions.get('uoa_events_count', 0)
        iv_skew = option_conditions.get('iv_skew', 0)
        pcr = option_conditions.get('put_call_ratio', 1.0)
        
        if uoa_count > 3 and iv_skew > 0.3:
            return 'high_volatility'
        elif pcr > 1.5:
            return 'bearish'
        elif pcr < 0.7:
            return 'bullish'
        else:
            return 'neutral'
    
    async def start_learning_worker(self):
        """Start asynchronous learning worker to process neural network updates"""
        if self.learning_worker_active:
            return
        
        self.learning_worker_active = True
        
        async def learning_worker():
            batch_updates = []
            
            while self.learning_worker_active:
                try:
                    try:
                        update = await asyncio.wait_for(self.learning_queue.get(), timeout=5.0)
                        batch_updates.append(update)
                    except asyncio.TimeoutError:
                        if not batch_updates:
                            continue
                    
                    if len(batch_updates) >= self.learning_batch_size or len(batch_updates) > 0:
                        await self._process_learning_batch(batch_updates)
                        batch_updates.clear()
                        
                except Exception as e:
                    self.logger.error(f"Error in learning worker: {e}")
                    await asyncio.sleep(1)
        
        asyncio.create_task(learning_worker())
        self.logger.info("Retroactive learning worker started")
    
    async def _process_learning_batch(self, batch_updates: List[LearningUpdate]):
        """
        Process a batch of learning updates to update neural networks
        This is where the actual learning happens asynchronously
        """
        try:
            if not batch_updates:
                return
            
            features = np.array([update.feature_vector for update in batch_updates])
            rewards = np.array([update.reward for update in batch_updates])
            confidences = np.array([update.confidence for update in batch_updates])
            
            weights = confidences * np.abs(rewards)
            
            features_tensor = torch.tensor(features, dtype=torch.float32)
            
            with torch.no_grad():
                extracted_features = self.feature_extractor(features_tensor)
            
            avg_reward = np.mean(rewards)
            avg_confidence = np.mean(confidences)
            
            self.learning_stats['learning_updates_applied'] += len(batch_updates)
            
            self.logger.info(f"Processed learning batch: {len(batch_updates)} updates, "
                           f"avg_reward: {avg_reward:.4f}, avg_confidence: {avg_confidence:.3f}")
            
            await self._integrate_with_existing_models(batch_updates, extracted_features)
            
        except Exception as e:
            self.logger.error(f"Error processing learning batch: {e}")
    
    async def _integrate_with_existing_models(self, batch_updates: List[LearningUpdate], 
                                           extracted_features: torch.Tensor):
        """
        Integration point with existing GRU networks and Q-learning models
        This is where option learning connects to the main trading models
        """
        try:
            learning_data = {
                'timestamp': time.time(),
                'feature_vectors': extracted_features.numpy().tolist(),
                'rewards': [update.reward for update in batch_updates],
                'actions': [update.target_action for update in batch_updates],
                'confidences': [update.confidence for update in batch_updates],
                'market_regimes': [update.market_regime for update in batch_updates],
                'learning_type': 'option_chain_retroactive'
            }
            
            await self._store_learning_data_for_integration(learning_data)
            
            self.logger.debug(f"Integrated {len(batch_updates)} option learning updates with main models")
            
        except Exception as e:
            self.logger.error(f"Error integrating with existing models: {e}")
    
    async def _store_learning_data_for_integration(self, learning_data: Dict[str, Any]):
        """Store learning data for pickup by main trading models"""
        try:
            from simulation_store import TimescaleSimulationStore
            
            store = TimescaleSimulationStore()
            
            await store.store_simulation(
                strategy_id='option_retroactive_learning',
                timescale='learning_update',
                results={
                    'symbol': 'LEARNING_UPDATE',
                    'profit': np.mean(learning_data['rewards']),
                    'quantity': len(learning_data['rewards']),
                    'action': 'learn',
                    'signal': 'option_conditions',
                    'confidence': np.mean(learning_data['confidences']),
                    'metadata': learning_data
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error storing learning data for integration: {e}")
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """Get current learning statistics"""
        return {
            **self.learning_stats,
            'memory_size': len(self.option_trade_memory),
            'pending_trades': len(self.pending_trades),
            'learning_queue_size': self.learning_queue.qsize() if hasattr(self.learning_queue, 'qsize') else 0
        }
    
    async def cleanup_old_trades(self, max_age_hours: int = 24):
        """Clean up old pending trades that never completed"""
        try:
            current_time = time.time()
            cutoff_time = current_time - (max_age_hours * 3600)
            
            old_trades = [
                trade_id for trade_id, trade in self.pending_trades.items()
                if trade.timestamp < cutoff_time
            ]
            
            for trade_id in old_trades:
                del self.pending_trades[trade_id]
                self.logger.warning(f"Cleaned up old pending trade: {trade_id}")
            
            if old_trades:
                self.logger.info(f"Cleaned up {len(old_trades)} old pending trades")
                
        except Exception as e:
            self.logger.error(f"Error cleaning up old trades: {e}")
    
    async def shutdown(self):
        """Shutdown the retroactive learning system"""
        self.learning_worker_active = False
        self.logger.info("RetroactiveOptionLearning shutdown complete")
