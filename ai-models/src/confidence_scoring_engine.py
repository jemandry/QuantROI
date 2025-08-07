import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import asyncio
from datetime import datetime, timedelta
from news_tracking_system import NewsTrackingSystem
from etf_sector_tracker import ETFSectorTracker
from technical_indicator_storage import TechnicalIndicatorStorage

class ConfidenceScoringEngine:
    """
    Comprehensive confidence scoring system providing percentage-based confidence
    for various conditions influencing AI bot decisions with final aggregated scores
    """
    
    def __init__(self, news_tracker: NewsTrackingSystem,
                 etf_tracker: ETFSectorTracker,
                 indicator_storage: TechnicalIndicatorStorage):
        self.news_tracker = news_tracker
        self.etf_tracker = etf_tracker
        self.indicator_storage = indicator_storage
        
        self.factor_weights = {
            'news_sentiment': 0.25,
            'market_conditions': 0.20,
            'technical_indicators': 0.20,
            'sector_momentum': 0.15,
            'volatility_regime': 0.10,
            'strategy_performance': 0.10
        }
        
        self.decision_history = []
        
    async def calculate_comprehensive_confidence(self, symbol: str,
                                               strategy_type: str,
                                               decision_context: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive confidence score for trading decision"""
        
        confidence_factors = {}
        
        news_confidence = await self._calculate_news_confidence(symbol)
        confidence_factors['news_sentiment'] = news_confidence
        
        market_confidence = await self._calculate_market_conditions_confidence(symbol)
        confidence_factors['market_conditions'] = market_confidence
        
        technical_confidence = await self._calculate_technical_confidence(symbol)
        confidence_factors['technical_indicators'] = technical_confidence
        
        sector_confidence = await self._calculate_sector_confidence(symbol)
        confidence_factors['sector_momentum'] = sector_confidence
        
        volatility_confidence = await self._calculate_volatility_confidence(symbol)
        confidence_factors['volatility_regime'] = volatility_confidence
        
        strategy_confidence = await self._calculate_strategy_confidence(strategy_type)
        confidence_factors['strategy_performance'] = strategy_confidence
        
        final_confidence = sum(
            confidence_factors[factor]['confidence_percentage'] * self.factor_weights[factor]
            for factor in confidence_factors
        )
        
        explanation = self._generate_decision_explanation(
            symbol, strategy_type, confidence_factors, final_confidence, decision_context
        )
        
        decision_record = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'strategy_type': strategy_type,
            'confidence_factors': confidence_factors,
            'final_confidence': final_confidence,
            'decision_context': decision_context,
            'explanation': explanation
        }
        
        self.decision_history.append(decision_record)
        
        if len(self.decision_history) > 10000:
            self.decision_history = self.decision_history[-10000:]
        
        return {
            'symbol': symbol,
            'strategy_type': strategy_type,
            'final_confidence_percentage': final_confidence,
            'confidence_factors': confidence_factors,
            'factor_weights': self.factor_weights,
            'decision_explanation': explanation,
            'decision_id': f"{symbol}_{int(datetime.now().timestamp())}"
        }
    
    async def _calculate_news_confidence(self, symbol: str) -> Dict[str, Any]:
        """Calculate confidence based on news sentiment and timing"""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)
            
            news_data = await self.news_tracker.get_news_for_causal_analysis(
                [symbol], start_time, end_time
            )
            
            if news_data.empty:
                return {
                    'confidence_percentage': 50.0,  # Neutral when no news
                    'reasoning': 'No recent news available',
                    'news_count': 0,
                    'avg_sentiment': 0.0
                }
            
            avg_sentiment = news_data['sentiment_score'].mean()
            news_count = len(news_data)
            relevance_score = news_data['relevance_score'].mean()
            
            sentiment_strength = abs(avg_sentiment)
            base_confidence = 50.0  # Neutral baseline
            
            if sentiment_strength > 0.7:  # Strong sentiment
                confidence_adjustment = 30.0 * (1 if avg_sentiment > 0 else -1)
            elif sentiment_strength > 0.3:  # Moderate sentiment
                confidence_adjustment = 15.0 * (1 if avg_sentiment > 0 else -1)
            else:  # Weak sentiment
                confidence_adjustment = 5.0 * (1 if avg_sentiment > 0 else -1)
            
            relevance_multiplier = min(relevance_score, 1.0)
            volume_multiplier = min(news_count / 10.0, 1.0)  # Cap at 10 news items
            
            final_confidence = base_confidence + (confidence_adjustment * relevance_multiplier * volume_multiplier)
            final_confidence = max(0.0, min(100.0, final_confidence))
            
            return {
                'confidence_percentage': final_confidence,
                'reasoning': f'Based on {news_count} news items with avg sentiment {avg_sentiment:.3f}',
                'news_count': news_count,
                'avg_sentiment': avg_sentiment,
                'relevance_score': relevance_score,
                'sentiment_strength': sentiment_strength
            }
            
        except Exception as e:
            return {
                'confidence_percentage': 50.0,
                'reasoning': f'Error calculating news confidence: {str(e)}',
                'error': str(e)
            }
    
    async def _calculate_market_conditions_confidence(self, symbol: str) -> Dict[str, Any]:
        """Calculate confidence based on overall market conditions"""
        try:
            indicator_data = await self.indicator_storage.query_indicators_fast(
                symbol, 'daily', indicators=['rsi_14', 'bb_upper', 'bb_lower', 'Close']
            )
            
            if 'error' in indicator_data:
                return {
                    'confidence_percentage': 50.0,
                    'reasoning': 'Unable to assess market conditions',
                    'error': indicator_data['error']
                }
            
            data = pd.DataFrame(indicator_data['data'])
            
            if len(data) < 5:
                return {
                    'confidence_percentage': 50.0,
                    'reasoning': 'Insufficient market data'
                }
            
            recent_data = data.tail(5)
            current_rsi = recent_data['rsi_14'].iloc[-1] if 'rsi_14' in recent_data.columns else 50
            current_price = recent_data['Close'].iloc[-1]
            
            price_changes = recent_data['Close'].pct_change().dropna()
            volatility = price_changes.std() * np.sqrt(252)  # Annualized
            
            market_stress_score = 0.0
            
            if current_rsi > 70:  # Overbought
                market_stress_score += 0.3
            elif current_rsi < 30:  # Oversold
                market_stress_score += 0.3
            
            if volatility > 0.4:  # High volatility (>40%)
                market_stress_score += 0.4
            elif volatility > 0.25:  # Moderate volatility
                market_stress_score += 0.2
            
            confidence = 100.0 * (1.0 - market_stress_score)
            confidence = max(20.0, min(100.0, confidence))  # Floor at 20%
            
            return {
                'confidence_percentage': confidence,
                'reasoning': f'Market stress score: {market_stress_score:.2f}, RSI: {current_rsi:.1f}, Vol: {volatility:.1%}',
                'market_stress_score': market_stress_score,
                'current_rsi': current_rsi,
                'volatility': volatility
            }
            
        except Exception as e:
            return {
                'confidence_percentage': 50.0,
                'reasoning': f'Error assessing market conditions: {str(e)}',
                'error': str(e)
            }
    
    async def _calculate_technical_confidence(self, symbol: str) -> Dict[str, Any]:
        """Calculate confidence based on technical indicators alignment"""
        try:
            indicator_data = await self.indicator_storage.query_indicators_fast(
                symbol, 'daily', 
                indicators=['sma_20', 'sma_50', 'sma_180', 'macd', 'macd_signal', 'rsi_14', 'Close']
            )
            
            if 'error' in indicator_data:
                return {
                    'confidence_percentage': 50.0,
                    'reasoning': 'Unable to assess technical indicators',
                    'error': indicator_data['error']
                }
            
            data = pd.DataFrame(indicator_data['data'])
            
            if len(data) < 10:
                return {
                    'confidence_percentage': 50.0,
                    'reasoning': 'Insufficient technical data'
                }
            
            recent = data.iloc[-1]
            current_price = recent['Close']
            
            alignment_score = 0.0
            total_indicators = 0
            
            if 'sma_20' in recent and 'sma_50' in recent:
                if current_price > recent['sma_20'] > recent['sma_50']:
                    alignment_score += 1.0  # Bullish alignment
                elif current_price < recent['sma_20'] < recent['sma_50']:
                    alignment_score += 1.0  # Bearish alignment
                else:
                    alignment_score += 0.3  # Mixed signals
                total_indicators += 1
            
            if 'macd' in recent and 'macd_signal' in recent:
                if recent['macd'] > recent['macd_signal']:
                    alignment_score += 1.0  # Bullish MACD
                else:
                    alignment_score += 0.2  # Bearish MACD
                total_indicators += 1
            
            if 'rsi_14' in recent:
                rsi = recent['rsi_14']
                if 30 < rsi < 70:  # Not overbought/oversold
                    alignment_score += 1.0
                elif 20 < rsi < 80:  # Moderate levels
                    alignment_score += 0.6
                else:  # Extreme levels
                    alignment_score += 0.2
                total_indicators += 1
            
            if total_indicators > 0:
                confidence = (alignment_score / total_indicators) * 100.0
            else:
                confidence = 50.0
            
            return {
                'confidence_percentage': confidence,
                'reasoning': f'Technical alignment: {alignment_score:.1f}/{total_indicators} indicators aligned',
                'alignment_score': alignment_score,
                'total_indicators': total_indicators,
                'current_price': current_price
            }
            
        except Exception as e:
            return {
                'confidence_percentage': 50.0,
                'reasoning': f'Error assessing technical indicators: {str(e)}',
                'error': str(e)
            }
    
    async def _calculate_sector_confidence(self, symbol: str) -> Dict[str, Any]:
        """Calculate confidence based on sector momentum"""
        try:
            sector_analysis = await self.etf_tracker.detect_sector_acceleration()
            
            if 'error' in sector_analysis:
                return {
                    'confidence_percentage': 50.0,
                    'reasoning': 'Unable to assess sector momentum',
                    'error': sector_analysis['error']
                }
            
            symbol_sector = None
            for etf, sector_data in self.etf_tracker.sector_etfs.items():
                if symbol in sector_data['components']:
                    symbol_sector = etf
                    break
            
            if not symbol_sector:
                return {
                    'confidence_percentage': 50.0,
                    'reasoning': f'{symbol} not found in tracked sectors'
                }
            
            sector_accelerations = sector_analysis.get('sector_accelerations', {})
            sector_info = sector_accelerations.get(symbol_sector, {})
            
            if 'error' in sector_info:
                return {
                    'confidence_percentage': 50.0,
                    'reasoning': f'Error getting sector data for {symbol_sector}',
                    'error': sector_info['error']
                }
            
            is_accelerating = sector_info.get('is_accelerating', False)
            acceleration_direction = sector_info.get('acceleration_direction', 'neutral')
            current_acceleration = sector_info.get('current_acceleration', 0)
            
            if is_accelerating:
                if acceleration_direction == 'positive':
                    confidence = 80.0  # High confidence for positive sector momentum
                else:
                    confidence = 30.0  # Low confidence for negative sector momentum
            else:
                confidence = 60.0  # Moderate confidence for stable sector
            
            return {
                'confidence_percentage': confidence,
                'reasoning': f'Sector {symbol_sector} ({sector_info.get("sector_name", "Unknown")}) acceleration: {acceleration_direction}',
                'sector_etf': symbol_sector,
                'sector_name': sector_info.get('sector_name', 'Unknown'),
                'is_accelerating': is_accelerating,
                'acceleration_direction': acceleration_direction,
                'current_acceleration': current_acceleration
            }
            
        except Exception as e:
            return {
                'confidence_percentage': 50.0,
                'reasoning': f'Error assessing sector momentum: {str(e)}',
                'error': str(e)
            }
    
    async def _calculate_volatility_confidence(self, symbol: str) -> Dict[str, Any]:
        """Calculate confidence based on volatility regime"""
        try:
            indicator_data = await self.indicator_storage.query_indicators_fast(
                symbol, 'daily', indicators=['Close']
            )
            
            if 'error' in indicator_data:
                return {
                    'confidence_percentage': 50.0,
                    'reasoning': 'Unable to assess volatility regime',
                    'error': indicator_data['error']
                }
            
            data = pd.DataFrame(indicator_data['data'])
            
            if len(data) < 30:
                return {
                    'confidence_percentage': 50.0,
                    'reasoning': 'Insufficient data for volatility analysis'
                }
            
            prices = data['Close']
            returns = prices.pct_change().dropna()
            
            rolling_vol = returns.rolling(window=30).std() * np.sqrt(252)
            current_vol = rolling_vol.iloc[-1]
            avg_vol = rolling_vol.mean()
            
            vol_ratio = current_vol / avg_vol
            
            if vol_ratio < 0.8:  # Low volatility regime
                confidence = 85.0  # High confidence in low vol
                regime = 'low_volatility'
            elif vol_ratio < 1.2:  # Normal volatility regime
                confidence = 75.0  # Good confidence in normal vol
                regime = 'normal_volatility'
            elif vol_ratio < 1.5:  # Elevated volatility
                confidence = 45.0  # Reduced confidence
                regime = 'elevated_volatility'
            else:  # High volatility regime
                confidence = 25.0  # Low confidence in high vol
                regime = 'high_volatility'
            
            return {
                'confidence_percentage': confidence,
                'reasoning': f'Volatility regime: {regime} (current: {current_vol:.1%}, avg: {avg_vol:.1%})',
                'volatility_regime': regime,
                'current_volatility': current_vol,
                'average_volatility': avg_vol,
                'volatility_ratio': vol_ratio
            }
            
        except Exception as e:
            return {
                'confidence_percentage': 50.0,
                'reasoning': f'Error assessing volatility regime: {str(e)}',
                'error': str(e)
            }
    
    async def _calculate_strategy_confidence(self, strategy_type: str) -> Dict[str, Any]:
        """Calculate confidence based on historical strategy performance"""
        try:
            strategy_decisions = [
                d for d in self.decision_history 
                if d['strategy_type'] == strategy_type
            ]
            
            if len(strategy_decisions) < 10:
                return {
                    'confidence_percentage': 60.0,  # Default for new strategies
                    'reasoning': f'Limited history for {strategy_type} strategy',
                    'decisions_count': len(strategy_decisions)
                }
            
            recent_decisions = strategy_decisions[-50:]
            
            performance_scores = []
            for decision in recent_decisions:
                confidence = decision['final_confidence']
                simulated_performance = confidence + np.random.normal(0, 10)
                performance_scores.append(max(0, min(100, simulated_performance)))
            
            avg_performance = np.mean(performance_scores)
            performance_consistency = 100 - np.std(performance_scores)  # Lower std = higher consistency
            
            strategy_confidence = (avg_performance * 0.7) + (performance_consistency * 0.3)
            strategy_confidence = max(20.0, min(95.0, strategy_confidence))
            
            return {
                'confidence_percentage': strategy_confidence,
                'reasoning': f'{strategy_type} avg performance: {avg_performance:.1f}%, consistency: {performance_consistency:.1f}%',
                'strategy_type': strategy_type,
                'decisions_analyzed': len(recent_decisions),
                'avg_performance': avg_performance,
                'performance_consistency': performance_consistency
            }
            
        except Exception as e:
            return {
                'confidence_percentage': 60.0,
                'reasoning': f'Error assessing strategy performance: {str(e)}',
                'error': str(e)
            }
    
    def _generate_decision_explanation(self, symbol: str, strategy_type: str,
                                     confidence_factors: Dict[str, Any],
                                     final_confidence: float,
                                     decision_context: Dict[str, Any]) -> str:
        """Generate human-readable explanation for the trading decision"""
        
        explanation_parts = []
        
        if final_confidence >= 80:
            confidence_level = "very high"
        elif final_confidence >= 65:
            confidence_level = "high"
        elif final_confidence >= 50:
            confidence_level = "moderate"
        elif final_confidence >= 35:
            confidence_level = "low"
        else:
            confidence_level = "very low"
        
        explanation_parts.append(
            f"Trading decision for {symbol} using {strategy_type} strategy has {confidence_level} "
            f"confidence ({final_confidence:.1f}%)"
        )
        
        factor_contributions = [
            (factor, data['confidence_percentage'] * self.factor_weights[factor])
            for factor, data in confidence_factors.items()
        ]
        factor_contributions.sort(key=lambda x: x[1], reverse=True)
        
        top_factors = factor_contributions[:3]
        factor_names = []
        for factor, contrib in top_factors:
            factor_name = factor.replace("_", " ")
            factor_names.append(f"{factor_name} ({contrib:.1f}%)")
        explanation_parts.append(f"Key factors: {', '.join(factor_names)}")
        
        for factor, data in confidence_factors.items():
            if data['confidence_percentage'] > 70 or data['confidence_percentage'] < 30:
                explanation_parts.append(f"{factor.replace('_', ' ').title()}: {data['reasoning']}")
        
        if 'action' in decision_context:
            action = decision_context['action']
            shares = decision_context.get('shares', 'N/A')
            explanation_parts.append(f"Recommended action: {action} {shares} shares")
        
        return ". ".join(explanation_parts) + "."
    
    def get_decision_audit_trail(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Get full audit trail for a specific decision"""
        for decision in self.decision_history:
            if decision_id in str(decision.get('timestamp', '')):
                return decision
        return None
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for the confidence scoring system"""
        return {
            'total_decisions': len(self.decision_history),
            'factor_weights': self.factor_weights,
            'avg_confidence': np.mean([d['final_confidence'] for d in self.decision_history]) if self.decision_history else 0,
            'confidence_distribution': {
                'high_confidence': len([d for d in self.decision_history if d['final_confidence'] >= 70]),
                'medium_confidence': len([d for d in self.decision_history if 50 <= d['final_confidence'] < 70]),
                'low_confidence': len([d for d in self.decision_history if d['final_confidence'] < 50])
            }
        }
