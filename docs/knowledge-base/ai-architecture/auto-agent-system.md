# Auto-Agent System for Data Gap Resolution

## Overview
Automated agent system for data gap resolution, API quota management, and cost controls with yfinance/Alpha Vantage integration, building on existing granularity limiter patterns.

## Core Architecture

### Data Gap Detection and Resolution
```python
import asyncio
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from scipy import interpolate
import logging

from enhanced_ria_features.storage_granularity.granularity_limiter import GranularityLimiter, MetricRequest

logger = logging.getLogger(__name__)

@dataclass
class DataGap:
    symbol: str
    metric_type: str
    start_time: datetime
    end_time: datetime
    expected_resolution: str
    gap_size_hours: float
    priority: int  # 1-5, 5 being highest
    estimated_cost: float

@dataclass
class ResolutionStrategy:
    method: str  # "interpolation", "api_fetch", "model_prediction"
    confidence: float
    cost_estimate: float
    time_estimate_seconds: float
    data_quality_score: float

class DataGapDetector:
    """Detect gaps in time series data"""
    
    def __init__(self, granularity_limiter: GranularityLimiter):
        self.granularity_limiter = granularity_limiter
        
    async def detect_gaps(self, data: pd.DataFrame, symbol: str, 
                         metric_type: str) -> List[DataGap]:
        """Detect gaps in time series data"""
        
        if 'timestamp' not in data.columns:
            return []
        
        # Sort by timestamp
        data = data.sort_values('timestamp')
        
        # Get expected resolution from granularity limiter
        metric_request = MetricRequest(
            metric_name=metric_type,
            symbol=symbol,
            start_time=data['timestamp'].min(),
            end_time=data['timestamp'].max(),
            requested_granularity=timedelta(minutes=1)
        )
        
        validation_result = await self.granularity_limiter.validate_granularity_async(metric_request)
        expected_interval = validation_result.adjusted_granularity
        
        # Detect gaps
        gaps = []
        timestamps = pd.to_datetime(data['timestamp'])
        
        for i in range(1, len(timestamps)):
            time_diff = timestamps.iloc[i] - timestamps.iloc[i-1]
            
            if time_diff > expected_interval * 2:  # Gap threshold
                gap = DataGap(
                    symbol=symbol,
                    metric_type=metric_type,
                    start_time=timestamps.iloc[i-1],
                    end_time=timestamps.iloc[i],
                    expected_resolution=str(expected_interval),
                    gap_size_hours=time_diff.total_seconds() / 3600,
                    priority=self._calculate_gap_priority(time_diff, metric_type),
                    estimated_cost=self._estimate_gap_cost(time_diff, metric_type)
                )
                gaps.append(gap)
        
        return gaps
    
    def _calculate_gap_priority(self, time_diff: timedelta, metric_type: str) -> int:
        """Calculate gap priority based on size and metric importance"""
        hours = time_diff.total_seconds() / 3600
        
        # Base priority on gap size
        if hours < 1:
            base_priority = 1
        elif hours < 24:
            base_priority = 2
        elif hours < 168:  # 1 week
            base_priority = 3
        else:
            base_priority = 4
        
        # Adjust for metric importance
        high_priority_metrics = ['price', 'volume', 'volatility']
        if metric_type in high_priority_metrics:
            base_priority = min(5, base_priority + 1)
        
        return base_priority
    
    def _estimate_gap_cost(self, time_diff: timedelta, metric_type: str) -> float:
        """Estimate cost to fill gap"""
        hours = time_diff.total_seconds() / 3600
        
        # Base cost per hour of data
        base_cost_per_hour = {
            'price': 0.01,
            'volume': 0.01,
            'volatility': 0.02,
            'sentiment': 0.05,
            'news': 0.10
        }
        
        cost_per_hour = base_cost_per_hour.get(metric_type, 0.03)
        return hours * cost_per_hour

class DataResolutionAgent:
    """Agent for resolving data gaps using multiple strategies"""
    
    def __init__(self, granularity_limiter: GranularityLimiter):
        self.granularity_limiter = granularity_limiter
        self.api_quotas = self._initialize_api_quotas()
        self.daily_cost_limit = 100.0  # $100 daily limit
        self.current_daily_cost = 0.0
        
    def _initialize_api_quotas(self) -> Dict[str, Dict[str, Any]]:
        """Initialize API quota tracking"""
        return {
            "yfinance": {
                "requests_per_minute": 60,
                "requests_per_day": 2000,
                "current_minute_count": 0,
                "current_day_count": 0,
                "last_reset_minute": datetime.now(),
                "last_reset_day": datetime.now(),
                "cost_per_request": 0.0  # Free tier
            },
            "alpha_vantage": {
                "requests_per_minute": 5,
                "requests_per_day": 500,
                "current_minute_count": 0,
                "current_day_count": 0,
                "last_reset_minute": datetime.now(),
                "last_reset_day": datetime.now(),
                "cost_per_request": 0.01
            }
        }
    
    async def resolve_data_gap(self, gap: DataGap) -> Dict[str, Any]:
        """Resolve a single data gap using optimal strategy"""
        
        # Evaluate resolution strategies
        strategies = await self._evaluate_resolution_strategies(gap)
        
        # Select best strategy based on cost, quality, and availability
        best_strategy = self._select_best_strategy(strategies, gap)
        
        if not best_strategy:
            return {
                "success": False,
                "error": "No viable resolution strategy found",
                "gap": gap.__dict__
            }
        
        # Execute resolution strategy
        resolution_result = await self._execute_resolution_strategy(gap, best_strategy)
        
        return {
            "success": resolution_result["success"],
            "strategy_used": best_strategy.method,
            "data_points_filled": resolution_result.get("data_points", 0),
            "cost_incurred": resolution_result.get("cost", 0.0),
            "quality_score": resolution_result.get("quality_score", 0.0),
            "gap": gap.__dict__,
            "filled_data": resolution_result.get("data")
        }

class AutoAgentOrchestrator:
    """Main orchestrator for auto-agent system"""
    
    def __init__(self, granularity_limiter: GranularityLimiter):
        self.granularity_limiter = granularity_limiter
        self.gap_detector = DataGapDetector(granularity_limiter)
        self.resolution_agent = DataResolutionAgent(granularity_limiter)
        
    async def process_data_with_gap_resolution(self, data: pd.DataFrame, 
                                             symbol: str, metric_type: str) -> Dict[str, Any]:
        """Process data and automatically resolve gaps"""
        
        # Detect gaps
        gaps = await self.gap_detector.detect_gaps(data, symbol, metric_type)
        
        if not gaps:
            return {
                "success": True,
                "gaps_found": 0,
                "original_data": data,
                "message": "No gaps detected"
            }
        
        # Sort gaps by priority
        gaps.sort(key=lambda x: x.priority, reverse=True)
        
        # Resolve gaps
        resolution_results = []
        filled_data_segments = []
        
        for gap in gaps:
            result = await self.resolution_agent.resolve_data_gap(gap)
            resolution_results.append(result)
            
            if result["success"] and "filled_data" in result:
                filled_data_segments.append(result["filled_data"])
        
        # Merge original data with filled segments
        complete_data = self._merge_data_segments(data, filled_data_segments)
        
        return {
            "success": True,
            "gaps_found": len(gaps),
            "gaps_resolved": sum(1 for r in resolution_results if r["success"]),
            "total_cost": sum(r.get("cost_incurred", 0) for r in resolution_results),
            "original_data": data,
            "complete_data": complete_data,
            "resolution_details": resolution_results
        }
```

## Performance Optimization

### Batch Gap Resolution
```python
class BatchGapResolver:
    """Resolve multiple gaps in batch for efficiency"""
    
    async def resolve_gaps_batch(self, gaps: List[DataGap]) -> List[Dict[str, Any]]:
        """Resolve multiple gaps in parallel"""
        
        # Group gaps by resolution strategy
        strategy_groups = {}
        for gap in gaps:
            strategies = await self.resolution_agent._evaluate_resolution_strategies(gap)
            best_strategy = self.resolution_agent._select_best_strategy(strategies, gap)
            
            if best_strategy:
                if best_strategy.method not in strategy_groups:
                    strategy_groups[best_strategy.method] = []
                strategy_groups[best_strategy.method].append((gap, best_strategy))
        
        # Execute strategies in parallel
        all_results = []
        for method, gap_strategy_pairs in strategy_groups.items():
            if method == "yfinance_api":
                # Batch yfinance requests
                batch_results = await self._batch_yfinance_requests(gap_strategy_pairs)
                all_results.extend(batch_results)
            else:
                # Process individually for other methods
                for gap, strategy in gap_strategy_pairs:
                    result = await self.resolution_agent._execute_resolution_strategy(gap, strategy)
                    all_results.append(result)
        
        return all_results
```

## Integration with Existing Systems

### Granularity Limiter Integration
```python
# Extension to existing granularity_limiter.py
async def enhanced_metric_processing_with_auto_agent(self, metric_request: MetricRequest) -> Dict[str, Any]:
    """Enhanced metric processing with automatic gap resolution"""
    
    # Initialize auto-agent
    auto_agent = AutoAgentOrchestrator(self)
    
    # Process with gap resolution
    result = await auto_agent.process_data_with_gap_resolution(
        data=metric_request.data,
        symbol=metric_request.symbol,
        metric_type=metric_request.metric_name
    )
    
    return result
```

This auto-agent system provides comprehensive data gap resolution with API quota management and cost controls, seamlessly integrating with existing granularity limiter patterns for optimal HFT performance.
