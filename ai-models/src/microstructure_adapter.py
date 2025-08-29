import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
import asyncio
import time

class MicrostructureAdaptiveRules:
    """Market microstructure-adaptive granularity rules"""
    
    def __init__(self, base_granularity_limiter):
        self.base_limiter = base_granularity_limiter
        self.microstructure_monitor = MicrostructureMonitor()
        self.adaptive_thresholds = {
            'spread_percentiles': {
                'tight': 25,
                'normal': 75,
                'wide': 100
            },
            'volume_percentiles': {
                'low': 25,
                'normal': 75,
                'high': 100
            },
            'volatility_percentiles': {
                'low': 25,
                'normal': 75,
                'high': 100
            }
        }
        self.rule_adjustments = {}
        self._initialize_rule_adjustments()
    
    def _initialize_rule_adjustments(self):
        """Initialize microstructure-based rule adjustments"""
        self.rule_adjustments = {
            'tight_spread_low_volume': {
                'granularity_multiplier': 0.5,
                'description': 'Tight spreads with low volume - increase precision'
            },
            'wide_spread_high_volume': {
                'granularity_multiplier': 1.5,
                'description': 'Wide spreads with high volume - reduce noise'
            },
            'high_volatility': {
                'granularity_multiplier': 0.75,
                'description': 'High volatility - capture rapid changes'
            },
            'low_volatility': {
                'granularity_multiplier': 1.25,
                'description': 'Low volatility - reduce over-sampling'
            },
            'market_stress': {
                'granularity_multiplier': 0.25,
                'description': 'Market stress conditions - maximum precision'
            }
        }
    
    async def adaptive_granularity_adjustment(self, data_df: pd.DataFrame,
                                            metric_types: List[str],
                                            symbol: str) -> Dict[str, Any]:
        """Adjust granularity based on current market microstructure"""
        
        microstructure_analysis = await self.microstructure_monitor.analyze_conditions(
            data_df, symbol
        )
        
        rule_key = self._determine_rule_adjustment(microstructure_analysis)
        
        if rule_key not in self.rule_adjustments:
            rule_key = 'normal'
            multiplier = 1.0
        else:
            multiplier = self.rule_adjustments[rule_key]['granularity_multiplier']
        
        adjusted_rules = {}
        for metric_type in metric_types:
            if metric_type in self.base_limiter.rules:
                original_interval = self.base_limiter.rules[metric_type]
                adjusted_interval = pd.Timedelta(
                    seconds=original_interval.total_seconds() * multiplier
                )
                adjusted_rules[metric_type] = adjusted_interval
        
        return {
            'microstructure_conditions': microstructure_analysis,
            'rule_adjustment': rule_key,
            'granularity_multiplier': multiplier,
            'adjusted_rules': adjusted_rules,
            'adjustment_reason': self.rule_adjustments.get(rule_key, {}).get('description', 'Normal conditions')
        }
    
    def _determine_rule_adjustment(self, microstructure_analysis: Dict[str, Any]) -> str:
        """Determine appropriate rule adjustment based on microstructure analysis"""
        
        spread_percentile = microstructure_analysis.get('spread_percentile', 50)
        volume_percentile = microstructure_analysis.get('volume_percentile', 50)
        volatility_percentile = microstructure_analysis.get('volatility_percentile', 50)
        market_stress_score = microstructure_analysis.get('market_stress_score', 0)
        
        if market_stress_score > 0.8:
            return 'market_stress'
        
        if volatility_percentile > self.adaptive_thresholds['volatility_percentiles']['normal']:
            return 'high_volatility'
        
        if volatility_percentile < self.adaptive_thresholds['volatility_percentiles']['low']:
            return 'low_volatility'
        
        if (spread_percentile < self.adaptive_thresholds['spread_percentiles']['tight'] and
            volume_percentile < self.adaptive_thresholds['volume_percentiles']['low']):
            return 'tight_spread_low_volume'
        
        if (spread_percentile > self.adaptive_thresholds['spread_percentiles']['normal'] and
            volume_percentile > self.adaptive_thresholds['volume_percentiles']['normal']):
            return 'wide_spread_high_volume'
        
        return 'normal'

class MicrostructureMonitor:
    """Monitor market microstructure conditions"""
    
    def __init__(self):
        self.historical_spreads = {}
        self.historical_volumes = {}
        self.historical_volatilities = {}
    
    async def analyze_conditions(self, data_df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """Analyze current market microstructure conditions"""
        
        analysis = {
            'symbol': symbol,
            'timestamp': time.time(),
            'data_points': len(data_df)
        }
        
        if 'bid' in data_df.columns and 'ask' in data_df.columns:
            spreads = data_df['ask'] - data_df['bid']
            current_spread = spreads.iloc[-1] if len(spreads) > 0 else 0
            
            if symbol not in self.historical_spreads:
                self.historical_spreads[symbol] = []
            
            self.historical_spreads[symbol].extend(spreads.tolist())
            
            if len(self.historical_spreads[symbol]) > 10000:
                self.historical_spreads[symbol] = self.historical_spreads[symbol][-10000:]
            
            if len(self.historical_spreads[symbol]) > 100:
                spread_percentile = (
                    sum(1 for s in self.historical_spreads[symbol] if s <= current_spread) /
                    len(self.historical_spreads[symbol]) * 100
                )
            else:
                spread_percentile = 50
            
            analysis.update({
                'current_spread': float(current_spread),
                'avg_spread': float(spreads.mean()),
                'spread_percentile': spread_percentile
            })
        
        if 'volume' in data_df.columns:
            volumes = data_df['volume']
            current_volume = volumes.iloc[-1] if len(volumes) > 0 else 0
            
            if symbol not in self.historical_volumes:
                self.historical_volumes[symbol] = []
            
            self.historical_volumes[symbol].extend(volumes.tolist())
            
            if len(self.historical_volumes[symbol]) > 10000:
                self.historical_volumes[symbol] = self.historical_volumes[symbol][-10000:]
            
            if len(self.historical_volumes[symbol]) > 100:
                volume_percentile = (
                    sum(1 for v in self.historical_volumes[symbol] if v <= current_volume) /
                    len(self.historical_volumes[symbol]) * 100
                )
            else:
                volume_percentile = 50
            
            analysis.update({
                'current_volume': float(current_volume),
                'avg_volume': float(volumes.mean()),
                'volume_percentile': volume_percentile
            })
        
        if 'price' in data_df.columns:
            prices = data_df['price']
            returns = prices.pct_change().dropna()
            current_volatility = returns.std() if len(returns) > 1 else 0
            
            if symbol not in self.historical_volatilities:
                self.historical_volatilities[symbol] = []
            
            if current_volatility > 0:
                self.historical_volatilities[symbol].append(current_volatility)
            
            if len(self.historical_volatilities[symbol]) > 1000:
                self.historical_volatilities[symbol] = self.historical_volatilities[symbol][-1000:]
            
            if len(self.historical_volatilities[symbol]) > 50:
                volatility_percentile = (
                    sum(1 for v in self.historical_volatilities[symbol] if v <= current_volatility) /
                    len(self.historical_volatilities[symbol]) * 100
                )
            else:
                volatility_percentile = 50
            
            analysis.update({
                'current_volatility': float(current_volatility),
                'volatility_percentile': volatility_percentile
            })
        
        market_stress_score = self._calculate_market_stress_score(analysis)
        analysis['market_stress_score'] = market_stress_score
        
        return analysis
    
    def _calculate_market_stress_score(self, analysis: Dict[str, Any]) -> float:
        """Calculate market stress score based on microstructure indicators"""
        
        stress_indicators = []
        
        spread_percentile = analysis.get('spread_percentile', 50)
        if spread_percentile > 90:
            stress_indicators.append(0.3)
        elif spread_percentile > 75:
            stress_indicators.append(0.1)
        
        volume_percentile = analysis.get('volume_percentile', 50)
        if volume_percentile < 10:
            stress_indicators.append(0.2)
        elif volume_percentile > 90:
            stress_indicators.append(0.2)
        
        volatility_percentile = analysis.get('volatility_percentile', 50)
        if volatility_percentile > 95:
            stress_indicators.append(0.4)
        elif volatility_percentile > 80:
            stress_indicators.append(0.2)
        
        stress_score = sum(stress_indicators)
        return min(stress_score, 1.0)
