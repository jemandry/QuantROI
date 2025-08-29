import asyncio
import time
import statistics
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd

class LatencyAwareGranularityManager:
    """Dynamic granularity management based on network latency conditions"""
    
    def __init__(self, base_granularity_limiter):
        self.base_limiter = base_granularity_limiter
        self.latency_monitor = NetworkLatencyMonitor()
        self.adaptive_rules = {}
        self.performance_history = []
        
        self._initialize_adaptive_rules()
    
    def _initialize_adaptive_rules(self):
        """Initialize latency-aware granularity rules"""
        self.adaptive_rules = {
            'hot_tier': {
                'base_latency_threshold_us': 100,
                'granularity_multipliers': {
                    'low_latency': 1.0,
                    'medium_latency': 1.5,
                    'high_latency': 2.0
                }
            },
            'warm_tier': {
                'base_latency_threshold_us': 10000,
                'granularity_multipliers': {
                    'low_latency': 1.0,
                    'medium_latency': 1.2,
                    'high_latency': 1.5
                }
            },
            'cold_tier': {
                'base_latency_threshold_us': 100000,
                'granularity_multipliers': {
                    'low_latency': 1.0,
                    'medium_latency': 1.1,
                    'high_latency': 1.2
                }
            }
        }
    
    async def adaptive_preprocess_for_causal_study(self, data_df: pd.DataFrame,
                                                 metric_types: List[str],
                                                 causal_context: Dict[str, Any]) -> pd.DataFrame:
        """Preprocess data with latency-aware granularity adjustments"""
        
        current_latency = await self.latency_monitor.measure_current_latency()
        
        data_tier = self._determine_data_tier(data_df, causal_context)
        
        multiplier = self._calculate_granularity_multiplier(current_latency, data_tier)
        
        original_rules = self.base_limiter.rules.copy()
        
        try:
            for metric_type in metric_types:
                if metric_type in self.base_limiter.rules:
                    original_interval = self.base_limiter.rules[metric_type]
                    adjusted_interval = pd.Timedelta(
                        seconds=original_interval.total_seconds() * multiplier
                    )
                    self.base_limiter.rules[metric_type] = adjusted_interval
            
            result = self.base_limiter.preprocess_for_causal_study(
                data_df, metric_types, causal_context
            )
            
            await self._log_adaptive_performance(current_latency, multiplier, data_tier)
            
            return result
            
        finally:
            self.base_limiter.rules = original_rules
    
    def _determine_data_tier(self, data_df: pd.DataFrame, 
                           causal_context: Dict[str, Any]) -> str:
        """Determine appropriate data tier based on data characteristics"""
        
        if isinstance(data_df.index, pd.DatetimeIndex) and len(data_df) > 1:
            median_interval = data_df.index.to_series().diff().median()
            
            if median_interval <= pd.Timedelta(seconds=1):
                return 'hot_tier'
            elif median_interval <= pd.Timedelta(minutes=10):
                return 'warm_tier'
            else:
                return 'cold_tier'
        
        return 'warm_tier'
    
    def _calculate_granularity_multiplier(self, latency_us: float, tier: str) -> float:
        """Calculate granularity multiplier based on latency and tier"""
        
        if tier not in self.adaptive_rules:
            return 1.0
        
        tier_rules = self.adaptive_rules[tier]
        threshold = tier_rules['base_latency_threshold_us']
        multipliers = tier_rules['granularity_multipliers']
        
        if latency_us < threshold:
            return multipliers['low_latency']
        elif latency_us < threshold * 5:
            return multipliers['medium_latency']
        else:
            return multipliers['high_latency']
    
    async def _log_adaptive_performance(self, latency_us: float, 
                                      multiplier: float, tier: str):
        """Log adaptive performance metrics"""
        
        performance_record = {
            'timestamp': time.time(),
            'latency_us': latency_us,
            'granularity_multiplier': multiplier,
            'data_tier': tier,
            'adaptive_adjustment': multiplier != 1.0
        }
        
        self.performance_history.append(performance_record)
        
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-1000:]
    
    def get_adaptive_performance_stats(self) -> Dict[str, Any]:
        """Get statistics on adaptive performance"""
        
        if not self.performance_history:
            return {'error': 'No performance history available'}
        
        recent_records = self.performance_history[-100:]
        
        latencies = [r['latency_us'] for r in recent_records]
        multipliers = [r['granularity_multiplier'] for r in recent_records]
        adjustments = [r['adaptive_adjustment'] for r in recent_records]
        
        return {
            'avg_latency_us': statistics.mean(latencies),
            'median_latency_us': statistics.median(latencies),
            'max_latency_us': max(latencies),
            'avg_granularity_multiplier': statistics.mean(multipliers),
            'adjustment_rate': sum(adjustments) / len(adjustments),
            'performance_stability': statistics.stdev(latencies) / statistics.mean(latencies),
            'total_records': len(self.performance_history)
        }

class NetworkLatencyMonitor:
    """Monitor network latency for adaptive granularity management"""
    
    def __init__(self):
        self.latency_history = []
        self.target_endpoints = [
            'redis://localhost:6379',
            'postgresql://localhost:5432',
            'http://localhost:8000'
        ]
    
    async def measure_current_latency(self) -> float:
        """Measure current network latency to key endpoints"""
        
        latencies = []
        
        for endpoint in self.target_endpoints:
            try:
                latency = await self._ping_endpoint(endpoint)
                latencies.append(latency)
            except Exception:
                latencies.append(1000.0)
        
        current_latency = statistics.median(latencies) if latencies else 1000.0
        
        self.latency_history.append({
            'timestamp': time.time(),
            'latency_us': current_latency
        })
        
        if len(self.latency_history) > 1000:
            self.latency_history = self.latency_history[-1000:]
        
        return current_latency
    
    async def _ping_endpoint(self, endpoint: str) -> float:
        """Ping specific endpoint and measure latency"""
        
        start_time = time.time()
        
        
        end_time = time.time()
        latency_seconds = end_time - start_time
        latency_microseconds = latency_seconds * 1_000_000
        
        return latency_microseconds
