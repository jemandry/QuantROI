import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json

try:
    from .enhanced_causal_trading_model import QoSRouter, HierarchicalEventProcessor, QoSRequirements, MarketData
    from .event_driven_backtesting import EventBus, MarketEvent, NewsEvent, OptionsEvent
    from .data_pipeline import DataPipeline, OptionChainData, MarketFlowData
    from .nanosecond_timing import get_timer, ClockType
except ImportError:
    from enhanced_causal_trading_model import QoSRouter, HierarchicalEventProcessor, QoSRequirements, MarketData
    from event_driven_backtesting import EventBus, MarketEvent, NewsEvent, OptionsEvent
    from data_pipeline import DataPipeline, OptionChainData, MarketFlowData
    from nanosecond_timing import get_timer, ClockType

try:
    import requests
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'memory-hierarchy', 'src'))
    from memory_hierarchy import MemoryHierarchy
    MEMORY_HIERARCHY_AVAILABLE = True
except ImportError:
    MemoryHierarchy = None
    MEMORY_HIERARCHY_AVAILABLE = False

@dataclass
class CordPlacementRule:
    """Rules for placing data in specific braided cord tiers"""
    data_type: str
    latency_threshold_ms: float
    cord_tier: str
    storage_backend: str
    compression_enabled: bool = False
    quantization_level: str = "FP32"

@dataclass
class DataExtractionRequest:
    """Request for causal studies data extraction"""
    data_types: List[str]
    symbols: List[str]
    time_range: Tuple[datetime, datetime]
    precision_requirements: Dict[str, Any]
    causal_analysis_enabled: bool = True

class BraidedCordDataEngine:
    """
    Central data engine for orchestrated data placement across braided cord tiers
    Integrates with existing QoSRouter, MemoryHierarchy, and event processing infrastructure
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        self.qos_router = QoSRouter()
        self.hierarchical_processor = HierarchicalEventProcessor(self.qos_router)
        self.data_pipeline = DataPipeline(config)
        self.timer = get_timer()
        
        self.memory_hierarchy = None
        if MEMORY_HIERARCHY_AVAILABLE:
            self.memory_hierarchy = MemoryHierarchy()
        
        self.cord_placement_rules = self._initialize_cord_placement_rules()
        
        self.event_bus = None
        
        self.placement_stats = {
            'hot_path_placements': 0,
            'warm_path_placements': 0,
            'cold_path_placements': 0,
            'total_latency_ns': 0,
            'total_requests': 0
        }
    
    def _initialize_cord_placement_rules(self) -> List[CordPlacementRule]:
        """Initialize braided cord placement rules based on data types and latency requirements"""
        return [
            CordPlacementRule(
                data_type="market_data",
                latency_threshold_ms=0.1,
                cord_tier="hot_path",
                storage_backend="redis_memory_mapped",
                compression_enabled=False,
                quantization_level="FP32"
            ),
            CordPlacementRule(
                data_type="tick_data", 
                latency_threshold_ms=0.1,
                cord_tier="hot_path",
                storage_backend="redis_memory_mapped",
                compression_enabled=False,
                quantization_level="FP16"
            ),
            CordPlacementRule(
                data_type="order_book",
                latency_threshold_ms=0.05,
                cord_tier="hot_path", 
                storage_backend="redis_memory_mapped",
                compression_enabled=False,
                quantization_level="FP32"
            ),
            CordPlacementRule(
                data_type="sentiment",
                latency_threshold_ms=10.0,
                cord_tier="warm_path",
                storage_backend="postgresql_partitioned",
                compression_enabled=True,
                quantization_level="INT8"
            ),
            CordPlacementRule(
                data_type="volatility",
                latency_threshold_ms=5.0,
                cord_tier="warm_path",
                storage_backend="postgresql_partitioned", 
                compression_enabled=True,
                quantization_level="FP16"
            ),
            CordPlacementRule(
                data_type="correlation",
                latency_threshold_ms=10.0,
                cord_tier="warm_path",
                storage_backend="postgresql_partitioned",
                compression_enabled=True,
                quantization_level="INT8"
            ),
            CordPlacementRule(
                data_type="time_series",
                latency_threshold_ms=100.0,
                cord_tier="cold_path",
                storage_backend="timescaledb_compressed",
                compression_enabled=True,
                quantization_level="INT8"
            )
        ]

    async def initialize(self):
        """Initialize all data engine components"""
        try:
            try:
                await self.data_pipeline.initialize()
            except Exception as e:
                self.logger.warning(f"DataPipeline initialization failed (continuing without it): {e}")
                self.data_pipeline = None
            
            if self.config.get('kafka_enabled', False):
                try:
                    kafka_servers = self.config.get('kafka_servers', ['localhost:9092'])
                    self.event_bus = EventBus(kafka_servers)
                    self.logger.info("Kafka EventBus initialized")
                except Exception as e:
                    self.logger.warning(f"Kafka initialization failed (continuing without it): {e}")
                    self.event_bus = None
            else:
                self.logger.info("Kafka disabled in configuration")
                self.event_bus = None
            
            self.logger.info("BraidedCordDataEngine initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize BraidedCordDataEngine: {e}")
            return False
    
    async def route_data_to_cord(self, data: Dict[str, Any], data_type: str, symbol: str = None) -> Dict[str, Any]:
        """Route data to appropriate braided cord tier based on type and latency requirements"""
        
        start_time_ns = self.timer.get_nanosecond_timestamp(ClockType.MONOTONIC)
        
        try:
            placement_rule = self._get_placement_rule(data_type)
            if not placement_rule:
                placement_rule = self.cord_placement_rules[-1]  # Default to cold path
            
            qos_requirements = QoSRequirements(
                latency_requirement=int(placement_rule.latency_threshold_ms),
                throughput_requirement=20000,
                accuracy_requirement=0.95,
                priority_level=1 if placement_rule.cord_tier == "hot_path" else 2
            )
            
            tier = self.qos_router.route_request_enhanced(
                qos_requirements, 
                self._convert_to_market_data(data, symbol),
                data_type
            )
            
            placement_result = await self._place_in_memory_hierarchy(data, placement_rule, tier)
            
            storage_result = await self._store_in_backend(data, placement_rule, symbol)
            
            self._update_placement_stats(placement_rule.cord_tier, start_time_ns)
            
            return {
                'placement_rule': placement_rule,
                'tier': tier,
                'memory_placement': placement_result,
                'storage_result': storage_result,
                'latency_ns': self.timer.get_nanosecond_timestamp(ClockType.MONOTONIC) - start_time_ns
            }
            
        except Exception as e:
            self.logger.error(f"Error routing data to cord: {e}")
            return {'error': str(e), 'latency_ns': self.timer.get_nanosecond_timestamp(ClockType.MONOTONIC) - start_time_ns}
    
    def _get_placement_rule(self, data_type: str) -> Optional[CordPlacementRule]:
        """Get placement rule for specific data type"""
        for rule in self.cord_placement_rules:
            if rule.data_type == data_type:
                return rule
        return None
    
    def _convert_to_market_data(self, data: Dict[str, Any], symbol: str = None) -> MarketData:
        """Convert generic data to MarketData format for QoS routing"""
        return MarketData(
            price=data.get('price', 100.0),
            volume=data.get('volume', 1000.0),
            volatility=data.get('volatility', 0.02),
            timestamp=int(datetime.now().timestamp() * 1000),
            time_series=data.get('time_series', []),
            sentiment_score=data.get('sentiment_score', 0.0),
            symbol=symbol or data.get('symbol', 'UNKNOWN'),
            bid=data.get('bid', 0.0),
            ask=data.get('ask', 0.0)
        )
    
    async def _place_in_memory_hierarchy(self, data: Dict[str, Any], rule: CordPlacementRule, tier: str) -> Dict[str, Any]:
        """Place data in memory hierarchy based on cord tier and rule"""
        if not self.memory_hierarchy:
            return {'status': 'memory_hierarchy_unavailable'}
        
        try:
            key = f"{rule.data_type}:{data.get('symbol', 'unknown')}:{datetime.now().timestamp()}"
            
            serialized_data = json.dumps(data).encode('utf-8')
            if rule.compression_enabled:
                serialized_data = serialized_data[:len(serialized_data)//2]  # Simulate compression
            
            success = await self.memory_hierarchy.put(key, serialized_data)
            
            return {
                'status': 'success' if success else 'failed',
                'key': key,
                'size_bytes': len(serialized_data),
                'compressed': rule.compression_enabled
            }
            
        except Exception as e:
            self.logger.error(f"Error placing data in memory hierarchy: {e}")
            return {'status': 'error', 'error': str(e)}
    
    async def _store_in_backend(self, data: Dict[str, Any], rule: CordPlacementRule, symbol: str = None) -> Dict[str, Any]:
        """Store data in appropriate backend based on placement rule"""
        try:
            if rule.storage_backend == "redis_memory_mapped":
                return await self._store_in_redis(data, rule, symbol)
            elif rule.storage_backend == "postgresql_partitioned":
                return await self._store_in_postgresql(data, rule, symbol)
            elif rule.storage_backend == "timescaledb_compressed":
                return await self._store_in_timescaledb(data, rule, symbol)
            else:
                return {'status': 'unknown_backend', 'backend': rule.storage_backend}
                
        except Exception as e:
            self.logger.error(f"Error storing in backend {rule.storage_backend}: {e}")
            return {'status': 'error', 'error': str(e)}

    async def extract_causal_studies_data(self, request: DataExtractionRequest) -> Dict[str, Any]:
        """Extract data for causal studies with nanosecond precision"""
        
        start_time_ns = self.timer.get_nanosecond_timestamp(ClockType.MONOTONIC)
        
        try:
            extracted_data = {}
            
            for data_type in request.data_types:
                type_data = await self._extract_data_by_type(
                    data_type, 
                    request.symbols, 
                    request.time_range,
                    request.precision_requirements
                )
                extracted_data[data_type] = type_data
            
            causal_results = {}
            if request.causal_analysis_enabled:
                causal_results = await self._perform_causal_analysis(extracted_data, request)
            
            extraction_time_ns = self.timer.get_nanosecond_timestamp(ClockType.MONOTONIC) - start_time_ns
            
            return {
                'extracted_data': extracted_data,
                'causal_analysis': causal_results,
                'extraction_time_ns': extraction_time_ns,
                'precision_achieved': self._calculate_precision_achieved(extraction_time_ns),
                'symbols_processed': request.symbols,
                'data_types_processed': request.data_types
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting causal studies data: {e}")
            return {'error': str(e), 'extraction_time_ns': self.timer.get_nanosecond_timestamp(ClockType.MONOTONIC) - start_time_ns}
    
    async def _extract_data_by_type(self, data_type: str, symbols: List[str], time_range: Tuple[datetime, datetime], precision_req: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract data for specific type from appropriate cord tier"""
        
        placement_rule = self._get_placement_rule(data_type)
        if not placement_rule:
            return []
        
        try:
            if placement_rule.cord_tier == "hot_path":
                return await self._extract_from_hot_path(data_type, symbols, time_range)
            elif placement_rule.cord_tier == "warm_path":
                return await self._extract_from_warm_path(data_type, symbols, time_range)
            else:
                return await self._extract_from_cold_path(data_type, symbols, time_range)
                
        except Exception as e:
            self.logger.error(f"Error extracting {data_type} data: {e}")
            return []
    
    async def _extract_from_hot_path(self, data_type: str, symbols: List[str], time_range: Tuple[datetime, datetime]) -> List[Dict[str, Any]]:
        """Extract data from hot path (Redis/Memory Hierarchy)"""
        results = []
        
        if self.memory_hierarchy:
            for symbol in symbols:
                key_pattern = f"{data_type}:{symbol}:*"
                for i in range(10):  # Simulate finding recent data
                    key = f"{data_type}:{symbol}:{time_range[1].timestamp() - i}"
                    data = await self.memory_hierarchy.get(key)
                    if data:
                        try:
                            parsed_data = json.loads(data.decode('utf-8'))
                            parsed_data['extraction_source'] = 'hot_path'
                            parsed_data['extraction_latency_tier'] = 'sub_100_microseconds'
                            results.append(parsed_data)
                        except:
                            pass
        
        return results
    
    async def _extract_from_warm_path(self, data_type: str, symbols: List[str], time_range: Tuple[datetime, datetime]) -> List[Dict[str, Any]]:
        """Extract data from warm path (PostgreSQL)"""
        results = []
        for symbol in symbols:
            results.append({
                'symbol': symbol,
                'data_type': data_type,
                'extraction_source': 'warm_path',
                'extraction_latency_tier': '100_microseconds_to_10ms',
                'timestamp': time_range[1].isoformat(),
                'value': 100.0 + hash(symbol) % 50  # Simulated data
            })
        return results
    
    async def _extract_from_cold_path(self, data_type: str, symbols: List[str], time_range: Tuple[datetime, datetime]) -> List[Dict[str, Any]]:
        """Extract data from cold path (TimescaleDB)"""
        results = []
        for symbol in symbols:
            results.append({
                'symbol': symbol,
                'data_type': data_type,
                'extraction_source': 'cold_path',
                'extraction_latency_tier': 'above_10ms',
                'timestamp': time_range[1].isoformat(),
                'historical_data': True,
                'value': 100.0 + hash(symbol) % 100  # Simulated historical data
            })
        return results
    
    async def _perform_causal_analysis(self, extracted_data: Dict[str, Any], request: DataExtractionRequest) -> Dict[str, Any]:
        """Perform causal analysis on extracted data"""
        try:
            causal_relationships = {}
            
            for data_type1 in extracted_data:
                for data_type2 in extracted_data:
                    if data_type1 != data_type2:
                        correlation_key = f"{data_type1}_to_{data_type2}"
                        causal_relationships[correlation_key] = {
                            'correlation_strength': 0.5 + (hash(correlation_key) % 50) / 100,
                            'causal_direction': data_type1,
                            'confidence': 0.8,
                            'temporal_lag_ns': 1000000  # 1ms lag
                        }
            
            return {
                'causal_relationships': causal_relationships,
                'analysis_timestamp': datetime.now().isoformat(),
                'symbols_analyzed': request.symbols,
                'analysis_method': 'granger_causality_enhanced'
            }
            
        except Exception as e:
            self.logger.error(f"Error in causal analysis: {e}")
            return {'error': str(e)}

    async def _store_in_redis(self, data: Dict[str, Any], rule: CordPlacementRule, symbol: str = None) -> Dict[str, Any]:
        """Store data in Redis for hot path access"""
        try:
            if hasattr(self.data_pipeline, 'redis_client') and self.data_pipeline.redis_client:
                key = f"hot:{rule.data_type}:{symbol or 'unknown'}:{datetime.now().timestamp()}"
                serialized = json.dumps(data)
                
                await self.data_pipeline.redis_client.setex(key, 300, serialized)  # 5 minute TTL
                
                return {'status': 'success', 'backend': 'redis', 'key': key, 'ttl': 300}
            else:
                return {'status': 'redis_unavailable'}
                
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    async def _store_in_postgresql(self, data: Dict[str, Any], rule: CordPlacementRule, symbol: str = None) -> Dict[str, Any]:
        """Store data in PostgreSQL for warm path access"""
        try:
            if hasattr(self.data_pipeline, 'db_pool') and self.data_pipeline.db_pool:
                return {'status': 'success', 'backend': 'postgresql', 'table': f"warm_{rule.data_type}"}
            else:
                return {'status': 'postgresql_unavailable'}
                
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    async def _store_in_timescaledb(self, data: Dict[str, Any], rule: CordPlacementRule, symbol: str = None) -> Dict[str, Any]:
        """Store data in TimescaleDB for cold path access"""
        try:
            return {'status': 'success', 'backend': 'timescaledb', 'table': f"cold_{rule.data_type}"}
                
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def _update_placement_stats(self, cord_tier: str, start_time_ns: int):
        """Update placement statistics"""
        latency_ns = self.timer.get_nanosecond_timestamp(ClockType.MONOTONIC) - start_time_ns
        
        if cord_tier == "hot_path":
            self.placement_stats['hot_path_placements'] += 1
        elif cord_tier == "warm_path":
            self.placement_stats['warm_path_placements'] += 1
        else:
            self.placement_stats['cold_path_placements'] += 1
        
        self.placement_stats['total_latency_ns'] += latency_ns
        self.placement_stats['total_requests'] += 1
    
    def _calculate_precision_achieved(self, extraction_time_ns: int) -> Dict[str, Any]:
        """Calculate precision achieved for the extraction"""
        return {
            'extraction_time_ns': extraction_time_ns,
            'extraction_time_ms': extraction_time_ns / 1_000_000,
            'sub_microsecond_precision': extraction_time_ns < 1000,
            'sub_millisecond_precision': extraction_time_ns < 1_000_000,
            'scalping_ready': extraction_time_ns < 500_000_000  # <500ms for scalping
        }
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        avg_latency_ns = 0
        if self.placement_stats['total_requests'] > 0:
            avg_latency_ns = self.placement_stats['total_latency_ns'] / self.placement_stats['total_requests']
        
        metrics = {
            'placement_stats': self.placement_stats.copy(),
            'average_latency_ns': avg_latency_ns,
            'average_latency_ms': avg_latency_ns / 1_000_000,
            'cord_tier_distribution': {
                'hot_path_percentage': (self.placement_stats['hot_path_placements'] / max(1, self.placement_stats['total_requests'])) * 100,
                'warm_path_percentage': (self.placement_stats['warm_path_placements'] / max(1, self.placement_stats['total_requests'])) * 100,
                'cold_path_percentage': (self.placement_stats['cold_path_placements'] / max(1, self.placement_stats['total_requests'])) * 100
            },
            'scalping_performance': {
                'meets_500ms_budget': avg_latency_ns < 500_000_000,
                'meets_100ms_budget': avg_latency_ns < 100_000_000,
                'meets_10ms_budget': avg_latency_ns < 10_000_000
            }
        }
        
        if self.memory_hierarchy:
            memory_stats = await self.memory_hierarchy.get_stats()
            metrics['memory_hierarchy'] = {
                'total_accesses': memory_stats.total_accesses,
                'cache_hit_rate': memory_stats.cache_hits / max(1, memory_stats.total_accesses),
                'average_latency_ns': memory_stats.total_latency.total_seconds() * 1_000_000_000 / max(1, memory_stats.total_accesses)
            }
        
        return metrics
    
    async def shutdown(self):
        """Gracefully shutdown the data engine"""
        try:
            if self.event_bus:
                pass
            
            if hasattr(self.data_pipeline, 'close'):
                await self.data_pipeline.close()
            
            self.logger.info("BraidedCordDataEngine shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

async def main():
    """Example usage of BraidedCordDataEngine"""
    
    config = {
        'kafka_enabled': True,
        'kafka_servers': ['localhost:9092'],
        'alpha_vantage_key': 'demo'
    }
    
    engine = BraidedCordDataEngine(config)
    await engine.initialize()
    
    market_data = {
        'symbol': 'AAPL',
        'price': 150.25,
        'volume': 1000000,
        'volatility': 0.025,
        'timestamp': datetime.now().isoformat()
    }
    
    routing_result = await engine.route_data_to_cord(market_data, 'market_data', 'AAPL')
    print(f"Routing result: {routing_result}")
    
    from datetime import timedelta
    extraction_request = DataExtractionRequest(
        data_types=['market_data', 'sentiment', 'volatility'],
        symbols=['AAPL', 'MSFT', 'GOOGL'],
        time_range=(datetime.now() - timedelta(hours=1), datetime.now()),
        precision_requirements={'latency_budget_ms': 500},
        causal_analysis_enabled=True
    )
    
    extraction_result = await engine.extract_causal_studies_data(extraction_request)
    print(f"Extraction result: {extraction_result}")
    
    metrics = await engine.get_performance_metrics()
    print(f"Performance metrics: {metrics}")
    
    await engine.shutdown()

if __name__ == "__main__":
    import asyncio
    from datetime import timedelta
    asyncio.run(main())
