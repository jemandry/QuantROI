import asyncio
import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json

try:
    from nanosecond_timing import get_ns_timestamp, ClockType
    NANOSECOND_TIMING_AVAILABLE = True
except ImportError:
    NANOSECOND_TIMING_AVAILABLE = False

class NormalizationStrategy(Enum):
    AGGREGATION = "aggregation"
    DELTA_ENCODING = "delta_encoding"
    BUCKETING = "bucketing"
    SAMPLING = "sampling"
    COMPRESSION = "compression"

@dataclass
class LatencyBucket:
    """Latency bucket for histogram storage"""
    bucket_id: str
    min_latency_ns: int
    max_latency_ns: int
    count: int
    avg_latency_ns: int
    percentiles: Dict[str, int]
    metadata: Dict[str, Any]

@dataclass
class AggregatedLatencyMetrics:
    """Aggregated latency metrics for time window"""
    window_start_ns: int
    window_end_ns: int
    window_duration_seconds: int
    event_count: int
    avg_latency_ns: int
    min_latency_ns: int
    max_latency_ns: int
    p50_latency_ns: int
    p95_latency_ns: int
    p99_latency_ns: int
    std_deviation_ns: int
    causal_event_ids: List[str]
    symbols: List[str]
    metadata: Dict[str, Any]

class LatencyDataNormalizer:
    """
    Data normalization system for efficient latency storage
    Reduces storage requirements while preserving essential precision for causal analysis
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.aggregation_windows = [60, 300, 3600]
        self.bucket_thresholds = [50_000, 100_000, 500_000, 1_000_000, 5_000_000]
        self.sampling_rate = 0.1
        self.baseline_latency = {}
        
        self.logger.info("✅ Latency data normalizer initialized")
    
    async def normalize_latency_data(self, 
                                   raw_events: List[Dict[str, Any]],
                                   strategy: NormalizationStrategy) -> Dict[str, Any]:
        """Normalize latency data using specified strategy"""
        try:
            if strategy == NormalizationStrategy.AGGREGATION:
                return await self._aggregate_latency_data(raw_events)
            elif strategy == NormalizationStrategy.DELTA_ENCODING:
                return await self._delta_encode_latency_data(raw_events)
            elif strategy == NormalizationStrategy.BUCKETING:
                return await self._bucket_latency_data(raw_events)
            elif strategy == NormalizationStrategy.SAMPLING:
                return await self._sample_latency_data(raw_events)
            elif strategy == NormalizationStrategy.COMPRESSION:
                return await self._compress_latency_data(raw_events)
            else:
                return {'error': f'Unknown normalization strategy: {strategy}'}
                
        except Exception as e:
            self.logger.error(f"Error normalizing latency data: {e}")
            return {'error': str(e)}
    
    async def _aggregate_latency_data(self, raw_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate latency metrics over time windows"""
        aggregated_metrics = []
        
        for window_seconds in self.aggregation_windows:
            window_metrics = await self._aggregate_by_window(raw_events, window_seconds)
            aggregated_metrics.extend(window_metrics)
        
        return {
            'strategy': 'aggregation',
            'original_event_count': len(raw_events),
            'aggregated_metrics_count': len(aggregated_metrics),
            'compression_ratio': len(raw_events) / len(aggregated_metrics) if aggregated_metrics else 0,
            'aggregated_metrics': aggregated_metrics
        }
    
    async def _aggregate_by_window(self, events: List[Dict[str, Any]], 
                                 window_seconds: int) -> List[AggregatedLatencyMetrics]:
        """Aggregate events by time window"""
        if not events:
            return []
        
        window_ns = window_seconds * 1_000_000_000
        windows = {}
        
        for event in events:
            timestamp_ns = event.get('timestamp_ns', 0)
            window_start = (timestamp_ns // window_ns) * window_ns
            
            if window_start not in windows:
                windows[window_start] = []
            windows[window_start].append(event)
        
        aggregated = []
        for window_start, window_events in windows.items():
            latencies = [e.get('latency_ns', 0) for e in window_events if e.get('latency_ns')]
            
            if latencies:
                latencies.sort()
                
                metrics = AggregatedLatencyMetrics(
                    window_start_ns=window_start,
                    window_end_ns=window_start + window_ns,
                    window_duration_seconds=window_seconds,
                    event_count=len(window_events),
                    avg_latency_ns=sum(latencies) // len(latencies),
                    min_latency_ns=min(latencies),
                    max_latency_ns=max(latencies),
                    p50_latency_ns=latencies[len(latencies) // 2],
                    p95_latency_ns=latencies[int(len(latencies) * 0.95)],
                    p99_latency_ns=latencies[int(len(latencies) * 0.99)],
                    std_deviation_ns=int(np.std(latencies)),
                    causal_event_ids=[e.get('causal_event_id', '') for e in window_events if e.get('causal_event_id')],
                    symbols=list(set(e.get('symbol', '') for e in window_events if e.get('symbol'))),
                    metadata={'window_seconds': window_seconds}
                )
                aggregated.append(metrics)
        
        return aggregated
    
    async def _delta_encode_latency_data(self, raw_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Delta encode latency values against baseline"""
        if not raw_events:
            return {'strategy': 'delta_encoding', 'encoded_events': []}
        
        encoded_events = []
        
        for event in raw_events:
            symbol = event.get('symbol', 'default')
            stage = event.get('stage', 'default')
            latency_ns = event.get('latency_ns', 0)
            
            baseline_key = f"{symbol}_{stage}"
            
            if baseline_key not in self.baseline_latency:
                self.baseline_latency[baseline_key] = latency_ns
                delta = 0
            else:
                delta = latency_ns - self.baseline_latency[baseline_key]
                self.baseline_latency[baseline_key] = latency_ns
            
            encoded_event = {
                'measurement_id': event.get('measurement_id'),
                'symbol': symbol,
                'stage': stage,
                'timestamp_ns': event.get('timestamp_ns'),
                'latency_delta_ns': delta,
                'baseline_latency_ns': self.baseline_latency[baseline_key],
                'causal_event_id': event.get('causal_event_id'),
                'metadata': event.get('metadata', {})
            }
            encoded_events.append(encoded_event)
        
        return {
            'strategy': 'delta_encoding',
            'original_event_count': len(raw_events),
            'encoded_events': encoded_events,
            'baseline_values': self.baseline_latency
        }
    
    async def _bucket_latency_data(self, raw_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Bucket latency values into histograms"""
        buckets = {}
        
        for event in raw_events:
            latency_ns = event.get('latency_ns', 0)
            symbol = event.get('symbol', 'default')
            
            bucket_id = self._get_latency_bucket(latency_ns)
            bucket_key = f"{symbol}_{bucket_id}"
            
            if bucket_key not in buckets:
                bucket_range = self._get_bucket_range(bucket_id)
                buckets[bucket_key] = LatencyBucket(
                    bucket_id=bucket_id,
                    min_latency_ns=bucket_range[0],
                    max_latency_ns=bucket_range[1],
                    count=0,
                    avg_latency_ns=0,
                    percentiles={},
                    metadata={'symbol': symbol, 'latencies': []}
                )
            
            buckets[bucket_key].count += 1
            buckets[bucket_key].metadata['latencies'].append(latency_ns)
        
        for bucket in buckets.values():
            latencies = bucket.metadata['latencies']
            if latencies:
                latencies.sort()
                bucket.avg_latency_ns = sum(latencies) // len(latencies)
                bucket.percentiles = {
                    'p50': latencies[len(latencies) // 2],
                    'p95': latencies[int(len(latencies) * 0.95)],
                    'p99': latencies[int(len(latencies) * 0.99)]
                }
            del bucket.metadata['latencies']
        
        return {
            'strategy': 'bucketing',
            'original_event_count': len(raw_events),
            'bucket_count': len(buckets),
            'compression_ratio': len(raw_events) / len(buckets) if buckets else 0,
            'buckets': [asdict(bucket) for bucket in buckets.values()]
        }
    
    def _get_latency_bucket(self, latency_ns: int) -> str:
        """Get bucket ID for latency value"""
        for i, threshold in enumerate(self.bucket_thresholds):
            if latency_ns <= threshold:
                return f"bucket_{i}"
        return f"bucket_{len(self.bucket_thresholds)}"
    
    def _get_bucket_range(self, bucket_id: str) -> Tuple[int, int]:
        """Get min/max range for bucket"""
        bucket_index = int(bucket_id.split('_')[1])
        
        if bucket_index == 0:
            return (0, self.bucket_thresholds[0])
        elif bucket_index < len(self.bucket_thresholds):
            return (self.bucket_thresholds[bucket_index - 1], self.bucket_thresholds[bucket_index])
        else:
            return (self.bucket_thresholds[-1], float('inf'))
    
    async def _sample_latency_data(self, raw_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Sample subset of latency events"""
        if not raw_events:
            return {'strategy': 'sampling', 'sampled_events': []}
        
        sample_size = max(1, int(len(raw_events) * self.sampling_rate))
        
        np.random.seed(42)
        sampled_indices = np.random.choice(len(raw_events), sample_size, replace=False)
        sampled_events = [raw_events[i] for i in sampled_indices]
        
        return {
            'strategy': 'sampling',
            'original_event_count': len(raw_events),
            'sampled_event_count': len(sampled_events),
            'sampling_rate': self.sampling_rate,
            'compression_ratio': len(raw_events) / len(sampled_events),
            'sampled_events': sampled_events
        }
    
    async def _compress_latency_data(self, raw_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compress latency data using columnar format"""
        if not raw_events:
            return {'strategy': 'compression', 'compressed_data': {}}
        
        compressed_data = {
            'measurement_ids': [e.get('measurement_id') for e in raw_events],
            'symbols': [e.get('symbol') for e in raw_events],
            'timestamps_ns': [e.get('timestamp_ns') for e in raw_events],
            'latencies_ns': [e.get('latency_ns') for e in raw_events],
            'stages': [e.get('stage') for e in raw_events],
            'causal_event_ids': [e.get('causal_event_id') for e in raw_events]
        }
        
        unique_symbols = list(set(compressed_data['symbols']))
        unique_stages = list(set(compressed_data['stages']))
        
        symbol_indices = [unique_symbols.index(s) if s in unique_symbols else -1 for s in compressed_data['symbols']]
        stage_indices = [unique_stages.index(s) if s in unique_stages else -1 for s in compressed_data['stages']]
        
        return {
            'strategy': 'compression',
            'original_event_count': len(raw_events),
            'compressed_data': {
                'measurement_ids': compressed_data['measurement_ids'],
                'symbol_indices': symbol_indices,
                'stage_indices': stage_indices,
                'timestamps_ns': compressed_data['timestamps_ns'],
                'latencies_ns': compressed_data['latencies_ns'],
                'causal_event_ids': compressed_data['causal_event_ids'],
                'symbol_lookup': unique_symbols,
                'stage_lookup': unique_stages
            },
            'compression_metadata': {
                'unique_symbols': len(unique_symbols),
                'unique_stages': len(unique_stages),
                'estimated_size_reduction': '30-50%'
            }
        }
    
    def estimate_storage_savings(self, original_event_count: int, 
                                strategy: NormalizationStrategy) -> Dict[str, Any]:
        """Estimate storage savings for normalization strategy"""
        base_event_size_bytes = 200
        
        if strategy == NormalizationStrategy.AGGREGATION:
            reduction_factor = 60
            estimated_size_reduction = 95
        elif strategy == NormalizationStrategy.DELTA_ENCODING:
            reduction_factor = 2
            estimated_size_reduction = 50
        elif strategy == NormalizationStrategy.BUCKETING:
            reduction_factor = 100
            estimated_size_reduction = 99
        elif strategy == NormalizationStrategy.SAMPLING:
            reduction_factor = int(1 / self.sampling_rate)
            estimated_size_reduction = (1 - self.sampling_rate) * 100
        elif strategy == NormalizationStrategy.COMPRESSION:
            reduction_factor = 2
            estimated_size_reduction = 40
        else:
            reduction_factor = 1
            estimated_size_reduction = 0
        
        original_size_mb = (original_event_count * base_event_size_bytes) / (1024 * 1024)
        normalized_size_mb = original_size_mb / reduction_factor
        savings_mb = original_size_mb - normalized_size_mb
        
        return {
            'strategy': strategy.value,
            'original_event_count': original_event_count,
            'original_size_mb': original_size_mb,
            'normalized_size_mb': normalized_size_mb,
            'savings_mb': savings_mb,
            'size_reduction_percent': estimated_size_reduction,
            'compression_ratio': reduction_factor
        }
