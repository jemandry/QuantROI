#!/usr/bin/env python3
"""
Trading Instructions Integration for Master Strategy
Provides specific trading instruction capabilities for the master strategy system
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import numpy as np

from enhanced_causal_trading_model import (
    RLStrategyType, MarketData, QoSRequirements, TradingResult, MarketRegime
)

class TradingInstructionType(Enum):
    MOMENTUM_BREAKOUT = "momentum_breakout"
    MEAN_REVERSION = "mean_reversion"
    PAIRS_TRADING = "pairs_trading"
    SENTIMENT_DRIVEN = "sentiment_driven"
    VOLATILITY_ARBITRAGE = "volatility_arbitrage"
    TREND_FOLLOWING = "trend_following"
    CONTRARIAN = "contrarian"
    SCALPING = "scalping"

@dataclass
class TradingInstruction:
    instruction_type: TradingInstructionType
    entry_conditions: Dict[str, Any]
    exit_conditions: Dict[str, Any]
    risk_parameters: Dict[str, float]
    position_sizing: Dict[str, float]
    time_horizon: str  # "short", "medium", "long"
    confidence_threshold: float
    max_drawdown_limit: float
    profit_target: float
    stop_loss: float

@dataclass
class MarketSignal:
    signal_type: str
    strength: float  # 0.0 to 1.0
    direction: str   # "buy", "sell", "hold"
    confidence: float
    timestamp: datetime
    source: str
    metadata: Dict[str, Any]

class TechnicalIndicators:
    """Technical analysis indicators for trading instructions"""
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return 50.0  # Neutral RSI
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> Tuple[float, float, float]:
        """Calculate Bollinger Bands (upper, middle, lower)"""
        if len(prices) < period:
            current_price = prices[-1] if prices else 0.0
            return current_price * 1.02, current_price, current_price * 0.98
        
        recent_prices = prices[-period:]
        middle = np.mean(recent_prices)
        std = np.std(recent_prices)
        
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        
        return upper, middle, lower
    
    @staticmethod
    def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[float, float, float]:
        """Calculate MACD (macd_line, signal_line, histogram)"""
        if len(prices) < slow:
            return 0.0, 0.0, 0.0
        
        ema_fast = TechnicalIndicators._ema(prices, fast)
        ema_slow = TechnicalIndicators._ema(prices, slow)
        
        macd_line = ema_fast - ema_slow
        
        macd_values = [macd_line] * signal  # Simplified
        signal_line = np.mean(macd_values)
        
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def _ema(prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return np.mean(prices) if prices else 0.0
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema

class TradingInstructionEngine:
    """Engine for processing and executing trading instructions"""
    
    def __init__(self):
        self.active_instructions: List[TradingInstruction] = []
        self.market_signals: List[MarketSignal] = []
        self.price_history: Dict[str, List[float]] = {}
        self.performance_tracker = {}
        self.logger = logging.getLogger(__name__)
        
        self._initialize_default_instructions()
    
    def _initialize_default_instructions(self):
        """Initialize default trading instruction set"""
        
        momentum_instruction = TradingInstruction(
            instruction_type=TradingInstructionType.MOMENTUM_BREAKOUT,
            entry_conditions={
                "rsi_above": 70,
                "volume_spike": 1.5,
                "price_breakout": True,
                "bollinger_position": "upper"
            },
            exit_conditions={
                "rsi_below": 30,
                "profit_target_hit": True,
                "stop_loss_hit": True,
                "time_limit_hours": 24
            },
            risk_parameters={
                "max_position_size": 0.05,  # 5% of portfolio
                "volatility_limit": 0.03,
                "correlation_limit": 0.7
            },
            position_sizing={
                "base_size": 0.02,
                "volatility_adjustment": True,
                "kelly_criterion": True
            },
            time_horizon="short",
            confidence_threshold=0.75,
            max_drawdown_limit=0.02,
            profit_target=0.015,
            stop_loss=0.008
        )
        
        mean_reversion_instruction = TradingInstruction(
            instruction_type=TradingInstructionType.MEAN_REVERSION,
            entry_conditions={
                "rsi_below": 30,
                "bollinger_position": "lower",
                "price_deviation": -2.0,  # 2 standard deviations below mean
                "volume_confirmation": True
            },
            exit_conditions={
                "rsi_above": 50,
                "bollinger_position": "middle",
                "profit_target_hit": True,
                "stop_loss_hit": True
            },
            risk_parameters={
                "max_position_size": 0.03,
                "volatility_limit": 0.025,
                "correlation_limit": 0.6
            },
            position_sizing={
                "base_size": 0.015,
                "volatility_adjustment": True,
                "mean_reversion_sizing": True
            },
            time_horizon="medium",
            confidence_threshold=0.70,
            max_drawdown_limit=0.015,
            profit_target=0.012,
            stop_loss=0.006
        )
        
        trend_following_instruction = TradingInstruction(
            instruction_type=TradingInstructionType.TREND_FOLLOWING,
            entry_conditions={
                "macd_crossover": True,
                "trend_strength": 0.6,
                "moving_average_alignment": True,
                "volume_trend": "increasing"
            },
            exit_conditions={
                "macd_divergence": True,
                "trend_weakening": True,
                "profit_target_hit": True,
                "trailing_stop_hit": True
            },
            risk_parameters={
                "max_position_size": 0.04,
                "volatility_limit": 0.035,
                "trend_correlation": 0.8
            },
            position_sizing={
                "base_size": 0.025,
                "trend_strength_adjustment": True,
                "pyramid_scaling": True
            },
            time_horizon="long",
            confidence_threshold=0.80,
            max_drawdown_limit=0.025,
            profit_target=0.025,
            stop_loss=0.012
        )
        
        self.active_instructions = [
            momentum_instruction,
            mean_reversion_instruction,
            trend_following_instruction
        ]
    
    def update_market_data(self, symbol: str, market_data: MarketData):
        """Update market data for instruction processing"""
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        self.price_history[symbol].append(market_data.price)
        
        if len(self.price_history[symbol]) > 200:
            self.price_history[symbol] = self.price_history[symbol][-200:]
        
        self._generate_market_signals(symbol, market_data)
    
    def _generate_market_signals(self, symbol: str, market_data: MarketData):
        """Generate market signals based on technical analysis"""
        prices = self.price_history[symbol]
        
        if len(prices) < 20:  # Need minimum data for analysis
            return
        
        rsi = TechnicalIndicators.calculate_rsi(prices)
        upper_bb, middle_bb, lower_bb = TechnicalIndicators.calculate_bollinger_bands(prices)
        macd_line, signal_line, histogram = TechnicalIndicators.calculate_macd(prices)
        
        current_price = market_data.price
        
        if rsi > 70:
            self.market_signals.append(MarketSignal(
                signal_type="rsi_overbought",
                strength=min((rsi - 70) / 30, 1.0),
                direction="sell",
                confidence=0.7,
                timestamp=datetime.now(),
                source="technical_analysis",
                metadata={"rsi": rsi, "symbol": symbol}
            ))
        elif rsi < 30:
            self.market_signals.append(MarketSignal(
                signal_type="rsi_oversold",
                strength=min((30 - rsi) / 30, 1.0),
                direction="buy",
                confidence=0.7,
                timestamp=datetime.now(),
                source="technical_analysis",
                metadata={"rsi": rsi, "symbol": symbol}
            ))
        
        if current_price > upper_bb:
            self.market_signals.append(MarketSignal(
                signal_type="bollinger_breakout_upper",
                strength=min((current_price - upper_bb) / upper_bb, 1.0),
                direction="buy" if market_data.volatility > 0.02 else "sell",
                confidence=0.75,
                timestamp=datetime.now(),
                source="technical_analysis",
                metadata={"price": current_price, "upper_bb": upper_bb, "symbol": symbol}
            ))
        elif current_price < lower_bb:
            self.market_signals.append(MarketSignal(
                signal_type="bollinger_breakout_lower",
                strength=min((lower_bb - current_price) / lower_bb, 1.0),
                direction="buy",
                confidence=0.75,
                timestamp=datetime.now(),
                source="technical_analysis",
                metadata={"price": current_price, "lower_bb": lower_bb, "symbol": symbol}
            ))
        
        if macd_line > signal_line and histogram > 0:
            self.market_signals.append(MarketSignal(
                signal_type="macd_bullish",
                strength=min(abs(histogram) / abs(macd_line), 1.0),
                direction="buy",
                confidence=0.8,
                timestamp=datetime.now(),
                source="technical_analysis",
                metadata={"macd": macd_line, "signal": signal_line, "symbol": symbol}
            ))
        elif macd_line < signal_line and histogram < 0:
            self.market_signals.append(MarketSignal(
                signal_type="macd_bearish",
                strength=min(abs(histogram) / abs(macd_line), 1.0),
                direction="sell",
                confidence=0.8,
                timestamp=datetime.now(),
                source="technical_analysis",
                metadata={"macd": macd_line, "signal": signal_line, "symbol": symbol}
            ))
        
        if len(self.market_signals) > 100:
            self.market_signals = self.market_signals[-100:]
    
    def evaluate_trading_instructions(self, market_data: MarketData, current_strategy: RLStrategyType) -> Optional[TradingInstruction]:
        """Evaluate which trading instruction should be applied"""
        
        symbol = market_data.symbol
        if symbol not in self.price_history or len(self.price_history[symbol]) < 20:
            return None
        
        prices = self.price_history[symbol]
        rsi = TechnicalIndicators.calculate_rsi(prices)
        upper_bb, middle_bb, lower_bb = TechnicalIndicators.calculate_bollinger_bands(prices)
        macd_line, signal_line, histogram = TechnicalIndicators.calculate_macd(prices)
        
        best_instruction = None
        best_score = 0.0
        
        for instruction in self.active_instructions:
            score = self._calculate_instruction_score(
                instruction, market_data, rsi, upper_bb, middle_bb, lower_bb, 
                macd_line, signal_line, histogram, current_strategy
            )
            
            if score > best_score and score > instruction.confidence_threshold:
                best_score = score
                best_instruction = instruction
        
        if best_instruction:
            self.logger.info(f"Selected trading instruction: {best_instruction.instruction_type.value} "
                           f"with score: {best_score:.3f}")
        
        return best_instruction
    
    def _calculate_instruction_score(self, instruction: TradingInstruction, market_data: MarketData,
                                   rsi: float, upper_bb: float, middle_bb: float, lower_bb: float,
                                   macd_line: float, signal_line: float, histogram: float,
                                   current_strategy: RLStrategyType) -> float:
        """Calculate score for a trading instruction based on current conditions"""
        
        score = 0.0
        current_price = market_data.price
        
        strategy_alignment = {
            TradingInstructionType.MOMENTUM_BREAKOUT: {
                RLStrategyType.GATED_DEEP_Q_LEARNING: 0.8,
                RLStrategyType.GATED_POLICY_GRADIENT: 0.9,
                RLStrategyType.TEMPORAL_FUSION_TRANSFORMER: 0.6
            },
            TradingInstructionType.MEAN_REVERSION: {
                RLStrategyType.GATED_DEEP_Q_LEARNING: 0.9,
                RLStrategyType.GATED_POLICY_GRADIENT: 0.6,
                RLStrategyType.TEMPORAL_FUSION_TRANSFORMER: 0.8
            },
            TradingInstructionType.TREND_FOLLOWING: {
                RLStrategyType.GATED_DEEP_Q_LEARNING: 0.7,
                RLStrategyType.GATED_POLICY_GRADIENT: 0.9,
                RLStrategyType.TEMPORAL_FUSION_TRANSFORMER: 0.9
            }
        }
        
        if instruction.instruction_type in strategy_alignment:
            score += strategy_alignment[instruction.instruction_type].get(current_strategy, 0.5) * 0.3
        
        entry_conditions = instruction.entry_conditions
        
        if instruction.instruction_type == TradingInstructionType.MOMENTUM_BREAKOUT:
            if "rsi_above" in entry_conditions and rsi > entry_conditions["rsi_above"]:
                score += 0.2
            if "price_breakout" in entry_conditions and current_price > upper_bb:
                score += 0.3
            if "volume_spike" in entry_conditions and market_data.volume > 1000:  # Simplified
                score += 0.2
        
        elif instruction.instruction_type == TradingInstructionType.MEAN_REVERSION:
            if "rsi_below" in entry_conditions and rsi < entry_conditions["rsi_below"]:
                score += 0.3
            if "bollinger_position" in entry_conditions and current_price < lower_bb:
                score += 0.3
            if "price_deviation" in entry_conditions:
                deviation = (current_price - middle_bb) / middle_bb
                if deviation < entry_conditions["price_deviation"] / 100:
                    score += 0.2
        
        elif instruction.instruction_type == TradingInstructionType.TREND_FOLLOWING:
            if "macd_crossover" in entry_conditions and macd_line > signal_line:
                score += 0.3
            if "trend_strength" in entry_conditions and abs(histogram) > 0.1:
                score += 0.2
            if market_data.volatility < 0.02:  # Stable trend conditions
                score += 0.2
        
        if market_data.volatility > 0.03:  # High volatility
            if instruction.instruction_type == TradingInstructionType.MOMENTUM_BREAKOUT:
                score += 0.1
            else:
                score -= 0.1
        
        if abs(market_data.sentiment_score) > 0.5:  # Strong sentiment
            if instruction.instruction_type in [TradingInstructionType.MOMENTUM_BREAKOUT, TradingInstructionType.TREND_FOLLOWING]:
                score += 0.1
        
        return min(score, 1.0)
    
    def apply_trading_instruction(self, instruction: TradingInstruction, market_data: MarketData, 
                                base_result: TradingResult) -> TradingResult:
        """Apply trading instruction to modify base trading result"""
        
        modified_result = TradingResult(
            action=base_result.action,
            quantity=base_result.quantity,
            confidence=base_result.confidence,
            expected_return=base_result.expected_return,
            strategy_used=base_result.strategy_used,
            risk_score=base_result.risk_score,
            timestamp=base_result.timestamp
        )
        
        position_sizing = instruction.position_sizing
        if "volatility_adjustment" in position_sizing and position_sizing["volatility_adjustment"]:
            volatility_factor = max(0.5, min(2.0, 1.0 / (market_data.volatility + 0.01)))
            modified_result.quantity *= volatility_factor
        
        risk_params = instruction.risk_parameters
        max_position = risk_params.get("max_position_size", 0.05)
        modified_result.quantity = min(modified_result.quantity, max_position * 1000)  # Simplified scaling
        
        instruction_confidence_boost = 0.1
        modified_result.confidence = min(1.0, modified_result.confidence + instruction_confidence_boost)
        
        return_adjustments = {
            TradingInstructionType.MOMENTUM_BREAKOUT: 1.2,
            TradingInstructionType.MEAN_REVERSION: 1.1,
            TradingInstructionType.TREND_FOLLOWING: 1.15,
            TradingInstructionType.SCALPING: 0.8,
            TradingInstructionType.VOLATILITY_ARBITRAGE: 1.3
        }
        
        adjustment = return_adjustments.get(instruction.instruction_type, 1.0)
        modified_result.expected_return *= adjustment
        
        volatility_limit = risk_params.get("volatility_limit", 0.03)
        if market_data.volatility > volatility_limit:
            modified_result.risk_score = min(1.0, modified_result.risk_score * 1.2)
        
        self.logger.info(f"Applied trading instruction {instruction.instruction_type.value}: "
                        f"quantity={modified_result.quantity:.2f}, "
                        f"confidence={modified_result.confidence:.3f}, "
                        f"expected_return={modified_result.expected_return:.4f}")
        
        return modified_result
    
    def get_instruction_insights(self) -> Dict[str, Any]:
        """Get insights about trading instruction performance"""
        return {
            "active_instructions": len(self.active_instructions),
            "recent_signals": len([s for s in self.market_signals if 
                                 (datetime.now() - s.timestamp).seconds < 3600]),
            "instruction_types": [inst.instruction_type.value for inst in self.active_instructions],
            "signal_distribution": self._get_signal_distribution(),
            "performance_summary": self.performance_tracker
        }
    
    def _get_signal_distribution(self) -> Dict[str, int]:
        """Get distribution of recent market signals"""
        recent_signals = [s for s in self.market_signals if 
                         (datetime.now() - s.timestamp).seconds < 3600]
        
        distribution = {}
        for signal in recent_signals:
            signal_type = signal.signal_type
            distribution[signal_type] = distribution.get(signal_type, 0) + 1
        
        return distribution

class EnhancedMasterStrategy:
    """Enhanced master strategy with trading instruction integration"""
    
    def __init__(self, master_learning_engine, trading_instruction_engine):
        self.master_learning_engine = master_learning_engine
        self.trading_instruction_engine = trading_instruction_engine
        self.logger = logging.getLogger(__name__)
    
    def execute_enhanced_trading(self, market_data: MarketData, qos_requirements: QoSRequirements) -> TradingResult:
        """Execute trading with both strategy learning and instruction integration"""
        
        self.trading_instruction_engine.update_market_data(market_data.symbol, market_data)
        
        optimal_strategy = self.master_learning_engine.select_optimal_strategy(market_data, qos_requirements)
        
        base_result = self._execute_base_strategy(optimal_strategy, market_data)
        
        instruction = self.trading_instruction_engine.evaluate_trading_instructions(market_data, optimal_strategy)
        
        if instruction:
            enhanced_result = self.trading_instruction_engine.apply_trading_instruction(
                instruction, market_data, base_result
            )
            
            self.master_learning_engine.update_strategy_performance(optimal_strategy, enhanced_result, market_data)
            
            self.logger.info(f"Enhanced trading executed with instruction: {instruction.instruction_type.value}")
            return enhanced_result
        else:
            self.master_learning_engine.update_strategy_performance(optimal_strategy, base_result, market_data)
            return base_result
    
    def _execute_base_strategy(self, strategy: RLStrategyType, market_data: MarketData) -> TradingResult:
        """Execute base strategy (simplified for demonstration)"""
        return TradingResult(
            action="buy" if market_data.price > market_data.bid else "hold",
            quantity=100.0,
            confidence=0.75,
            expected_return=0.002,
            strategy_used=strategy,
            risk_score=0.3,
            timestamp=datetime.now().isoformat()
        )
    
    def get_comprehensive_insights(self) -> Dict[str, Any]:
        """Get comprehensive insights from both learning engine and instruction engine"""
        learning_insights = self.master_learning_engine.get_learning_insights()
        instruction_insights = self.trading_instruction_engine.get_instruction_insights()
        
        return {
            "learning_engine": learning_insights,
            "instruction_engine": instruction_insights,
            "integration_status": "active",
            "timestamp": datetime.now().isoformat()
        }
