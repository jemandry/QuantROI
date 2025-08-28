"""
Automated Strand Creator (Octopus Engine) for intelligent strand library creation
Uses ML-based pattern recognition and causal relationship detection
"""

import asyncio
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
import logging
from collections import defaultdict, deque
import time
import json

try:
    from sklearn.cluster import DBSCAN
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from strand_types import EventStrand, MarketStrand
from event_upload_processor import EventUploadProcessor
from market_regime_detector import BayesianRegimeDetector, MarketRegime
from braided_cord_data_engine import BraidedCordDataEngine
from dag_template_engine import DAGTemplateEngine

@dataclass
class StrandCreationRule:
    """Rules for automated strand creation based on market regime"""
    regime: MarketRegime
    time_window_ms: int
    similarity_threshold: float
    causal_features: List[str]
    max_strand_size: int
    min_events_per_strand: int
    clustering_params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CausalPattern:
    """Detected causal pattern between events"""
    source_feature: str
    target_feature: str
    correlation_strength: float
    lag_ns: int
    confidence: float
    regime_context: MarketRegime
    sample_count: int

@dataclass
class StrandLibraryStats:
    """Statistics for the strand library"""
    total_strands: int = 0
    market_strands: int = 0
    general_strands: int = 0
    avg_strand_size: float = 0.0
    causal_patterns_detected: int = 0
    regime_distribution: Dict[str, int] = field(default_factory=dict)
    creation_rate_per_second: float = 0.0

class AutomatedStrandCreator:
    """Octopus Engine for intelligent strand library creation with ML-based optimization"""
    
    def __init__(self, 
                 enable_ml_clustering: bool = True,
                 causal_detection_threshold: float = 0.3,
                 pattern_learning_window: int = 10000):
        
        self.enable_ml_clustering = enable_ml_clustering and SKLEARN_AVAILABLE
        self.causal_detection_threshold = causal_detection_threshold
        self.pattern_learning_window = pattern_learning_window
        
        self.regime_detector = BayesianRegimeDetector()
        self.event_processor = EventUploadProcessor()
        self.data_engine = BraidedCordDataEngine()
        self.dag_engine = DAGTemplateEngine()
        
        self.creation_rules = self._initialize_creation_rules()
        self.strand_library = {}  # Cache of created strands
        self.causal_patterns = {}  # Learned causal relationships
        self.pattern_history = deque(maxlen=pattern_learning_window)
        
        self.library_stats = StrandLibraryStats()
        self.performance_metrics = {
            "strands_created_per_second": 0.0,
            "ml_clustering_time_ms": 0.0,
            "causal_detection_time_ms": 0.0,
            "total_processing_time_ms": 0.0
        }
        
        self.logger = logging.getLogger(__name__)
        
        if self.enable_ml_clustering:
            self.scaler = StandardScaler()
            self.pca = PCA(n_components=10)
            self.clusterer = DBSCAN(eps=0.3, min_samples=5)
        
        self._access_patterns = defaultdict(list)
        self._strand_relationships = defaultdict(set)
        
    def _initialize_creation_rules(self) -> Dict[MarketRegime, StrandCreationRule]:
        """Initialize regime-specific strand creation rules"""
        return {
            MarketRegime.LOW_VOLATILITY_STABLE: StrandCreationRule(
                regime=MarketRegime.LOW_VOLATILITY_STABLE,
                time_window_ms=60000,  # 1 minute windows
                similarity_threshold=0.8,
                causal_features=['price', 'volume', 'sentiment'],
                max_strand_size=1000,
                min_events_per_strand=5,
                clustering_params={'eps': 0.3, 'min_samples': 5}
            ),
            MarketRegime.HIGH_VOLATILITY_TURBULENT: StrandCreationRule(
                regime=MarketRegime.HIGH_VOLATILITY_TURBULENT,
                time_window_ms=5000,   # 5 second windows
                similarity_threshold=0.9,
                causal_features=['price', 'news', 'order_flow'],
                max_strand_size=500,
                min_events_per_strand=3,
                clustering_params={'eps': 0.2, 'min_samples': 3}
            ),
            MarketRegime.BULL_MARKET: StrandCreationRule(
                regime=MarketRegime.BULL_MARKET,
                time_window_ms=300000,  # 5 minute windows
                similarity_threshold=0.7,
                causal_features=['sector_momentum', 'earnings_trend', 'macro_growth'],
                max_strand_size=2000,
                min_events_per_strand=10,
                clustering_params={'eps': 0.4, 'min_samples': 8}
            ),
            MarketRegime.BEAR_MARKET: StrandCreationRule(
                regime=MarketRegime.BEAR_MARKET,
                time_window_ms=120000,  # 2 minute windows
                similarity_threshold=0.85,
                causal_features=['credit_spread', 'vix', 'defensive_flows'],
                max_strand_size=800,
                min_events_per_strand=5,
                clustering_params={'eps': 0.25, 'min_samples': 4}
            ),
            MarketRegime.CRISIS_CORRELATION: StrandCreationRule(
                regime=MarketRegime.CRISIS_CORRELATION,
                time_window_ms=1000,   # 1 second windows
                similarity_threshold=0.95,
                causal_features=['correlation_spike', 'liquidity_drain', 'volatility'],
                max_strand_size=200,
                min_events_per_strand=2,
                clustering_params={'eps': 0.1, 'min_samples': 2}
            ),
            MarketRegime.EARNINGS_SEASON: StrandCreationRule(
                regime=MarketRegime.EARNINGS_SEASON,
                time_window_ms=3600000,  # 1 hour windows
                similarity_threshold=0.75,
                causal_features=['earnings_surprise', 'guidance', 'sector_rotation'],
                max_strand_size=1500,
                min_events_per_strand=8,
                clustering_params={'eps': 0.35, 'min_samples': 6}
            )
        }
    
    async def initialize(self):
        """Initialize all components"""
        try:
            await self.data_engine.initialize()
            await self.event_processor.initialize()
            self.logger.info("AutomatedStrandCreator initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize AutomatedStrandCreator: {e}")
            raise
    
    async def create_strands_from_events(self, 
                                       events: List[Dict[str, Any]],
                                       market_data: Dict[str, Any]) -> List[EventStrand]:
        """Automatically create optimized strands from raw events using ML and causal analysis with parallel processing"""
        start_time = time.perf_counter()
        
        try:
            if not events:
                return []
            
            regime_result = self.regime_detector.detect_regime(market_data)
            current_regime = regime_result.regime
            
            rules = self.creation_rules.get(current_regime)
            if not rules:
                rules = self.creation_rules[MarketRegime.LOW_VOLATILITY_STABLE]  # Default
            
            self.logger.info(f"Creating strands for regime {current_regime.value} with {len(events)} events")
            
            if len(events) > 1000:
                return await self._create_strands_parallel(events, rules, current_regime)
            
            event_groups = await self._group_events_intelligently(events, rules)
            
            strand_tasks = []
            for group in event_groups:
                if len(group) >= rules.min_events_per_strand:
                    task = asyncio.create_task(self._create_strand_from_group(group, rules, current_regime))
                    strand_tasks.append(task)
            
            if strand_tasks:
                strand_results = await asyncio.gather(*strand_tasks, return_exceptions=True)
                strands = [s for s in strand_results if s and not isinstance(s, Exception)]
            else:
                strands = []
            
            if strands:
                asyncio.create_task(self._update_causal_patterns(strands, current_regime))
                asyncio.create_task(self._store_strands_in_library(strands))
            
            self._update_performance_metrics(start_time, len(strands))
            
            self.logger.info(f"Created {len(strands)} strands from {len(events)} events")
            
            return strands
            
        except Exception as e:
            self.logger.error(f"Failed to create strands from events: {e}")
            return []
    
    async def _create_strands_parallel(self, events: List[Dict[str, Any]], 
                                     rules: StrandCreationRule, 
                                     current_regime: MarketRegime) -> List[EventStrand]:
        """Create strands using parallel processing for large datasets"""
        chunk_size = 500  # Process in chunks for better memory management
        chunks = [events[i:i + chunk_size] for i in range(0, len(events), chunk_size)]
        
        chunk_tasks = []
        for chunk in chunks:
            task = asyncio.create_task(self._process_event_chunk(chunk, rules, current_regime))
            chunk_tasks.append(task)
        
        chunk_results = await asyncio.gather(*chunk_tasks, return_exceptions=True)
        
        all_strands = []
        for result in chunk_results:
            if not isinstance(result, Exception) and result:
                all_strands.extend(result)
        
        return all_strands
    
    async def _process_event_chunk(self, events: List[Dict[str, Any]], 
                                 rules: StrandCreationRule,
                                 current_regime: MarketRegime) -> List[EventStrand]:
        """Process a chunk of events into strands"""
        event_groups = await self._group_events_intelligently(events, rules)
        
        strands = []
        for group in event_groups:
            if len(group) >= rules.min_events_per_strand:
                strand = await self._create_strand_from_group(group, rules, current_regime)
                if strand:
                    strands.append(strand)
        
        return strands
    
    async def _create_strand_from_group(self, group: List[Dict[str, Any]], 
                                      rules: StrandCreationRule,
                                      current_regime: MarketRegime) -> EventStrand:
        """Create a single strand from an event group"""
        if self._is_market_data_group(group):
            strand = MarketStrand.create_from_market_events(group, current_regime.value)
            self.library_stats.market_strands += 1
        else:
            strand = EventStrand.create_from_events(group, current_regime.value)
            self.library_stats.general_strands += 1
        
        await self._enhance_strand_with_causal_features(strand, rules)
        return strand
    
    async def _group_events_intelligently(self, 
                                        events: List[Dict[str, Any]], 
                                        rules: StrandCreationRule) -> List[List[Dict[str, Any]]]:
        """Group events using ML clustering and temporal analysis"""
        if not events:
            return []
        
        if self.enable_ml_clustering and len(events) > 10:
            return await self._ml_based_grouping(events, rules)
        else:
            return await self._temporal_grouping(events, rules)
    
    async def _ml_based_grouping(self, 
                               events: List[Dict[str, Any]], 
                               rules: StrandCreationRule) -> List[List[Dict[str, Any]]]:
        """Use ML clustering for intelligent event grouping"""
        start_time = time.perf_counter()
        
        try:
            feature_matrix = self._extract_feature_matrix(events, rules.causal_features)
            
            if feature_matrix.shape[0] < 2:
                return [events]
            
            scaled_features = self.scaler.fit_transform(feature_matrix)
            
            if scaled_features.shape[1] > 10:
                reduced_features = self.pca.fit_transform(scaled_features)
            else:
                reduced_features = scaled_features
            
            clustering_params = rules.clustering_params.copy()
            clusterer = DBSCAN(**clustering_params)
            cluster_labels = clusterer.fit_predict(reduced_features)
            
            groups = defaultdict(list)
            for i, label in enumerate(cluster_labels):
                if label != -1:  # Not noise
                    groups[label].append(events[i])
                else:
                    groups['noise'].append(events[i])
            
            result_groups = [group for group in groups.values() 
                           if len(group) >= rules.min_events_per_strand]
            
            ml_time_ms = (time.perf_counter() - start_time) * 1000
            self.performance_metrics["ml_clustering_time_ms"] = ml_time_ms
            
            self.logger.debug(f"ML clustering created {len(result_groups)} groups in {ml_time_ms:.2f}ms")
            
            return result_groups
            
        except Exception as e:
            self.logger.warning(f"ML clustering failed, falling back to temporal grouping: {e}")
            return await self._temporal_grouping(events, rules)
    
    async def _temporal_grouping(self, 
                               events: List[Dict[str, Any]], 
                               rules: StrandCreationRule) -> List[List[Dict[str, Any]]]:
        """Group events by time windows and similarity"""
        try:
            events_sorted = sorted(events, key=lambda x: x.get('timestamp_ns', 0))
            
            groups = []
            current_group = []
            current_window_start = None
            
            for event in events_sorted:
                timestamp_ns = event.get('timestamp_ns', time.time_ns())
                
                if current_window_start is None:
                    current_window_start = timestamp_ns
                    current_group = [event]
                elif (timestamp_ns - current_window_start) <= (rules.time_window_ms * 1e6):
                    if len(current_group) < rules.max_strand_size:
                        current_group.append(event)
                    else:
                        if len(current_group) >= rules.min_events_per_strand:
                            groups.append(current_group)
                        current_group = [event]
                        current_window_start = timestamp_ns
                else:
                    if len(current_group) >= rules.min_events_per_strand:
                        groups.append(current_group)
                    current_group = [event]
                    current_window_start = timestamp_ns
            
            if len(current_group) >= rules.min_events_per_strand:
                groups.append(current_group)
            
            return groups
            
        except Exception as e:
            self.logger.error(f"Temporal grouping failed: {e}")
            return [events] if len(events) >= rules.min_events_per_strand else []
    
    def _extract_feature_matrix(self, 
                               events: List[Dict[str, Any]], 
                               causal_features: List[str]) -> np.ndarray:
        """Extract feature matrix for ML clustering with vectorized operations"""
        try:
            if not events:
                return np.array([])
            
            n_events = len(events)
            n_base_features = 3 + len(causal_features) + 4  # timestamp, type_id, source_id + causal + payload features
            feature_matrix = np.zeros((n_events, n_base_features), dtype=np.float64)
            
            timestamps = np.array([event.get('timestamp_ns', 0) / 1e9 for event in events])
            type_ids = np.array([event.get('type_id', 0) for event in events])
            source_ids = np.array([event.get('source_id', 0) for event in events])
            
            feature_matrix[:, 0] = timestamps
            feature_matrix[:, 1] = type_ids
            feature_matrix[:, 2] = source_ids
            
            for i, feature_name in enumerate(causal_features):
                feature_values = []
                for event in events:
                    if feature_name in event:
                        value = event[feature_name]
                        if isinstance(value, (int, float)):
                            feature_values.append(float(value))
                        elif isinstance(value, list) and value and isinstance(value[0], (int, float)):
                            feature_values.append(float(value[0]))
                        else:
                            feature_values.append(0.0)
                    else:
                        feature_values.append(0.0)
                feature_matrix[:, 3 + i] = feature_values
            
            payload_features = ['price', 'volume', 'sentiment', 'volatility']
            for i, key in enumerate(payload_features):
                payload_values = []
                for event in events:
                    payload = event.get('payload', {})
                    if isinstance(payload, dict) and key in payload:
                        value = payload[key]
                        if isinstance(value, (int, float)):
                            payload_values.append(float(value))
                        else:
                            payload_values.append(0.0)
                    else:
                        payload_values.append(0.0)
                feature_matrix[:, 3 + len(causal_features) + i] = payload_values
            
            return feature_matrix
            
        except Exception as e:
            self.logger.error(f"Feature extraction failed: {e}")
            return np.zeros((len(events), 1))
    
    def _is_market_data_group(self, events: List[Dict[str, Any]]) -> bool:
        """Determine if event group contains market data"""
        market_indicators = ['price', 'volume', 'trade', 'quote', 'order', 'market']
        
        market_event_count = 0
        for event in events:
            event_type = str(event.get('type', '')).lower()
            payload = event.get('payload', {})
            
            if any(indicator in event_type for indicator in market_indicators):
                market_event_count += 1
                continue
            
            if isinstance(payload, dict):
                payload_str = str(payload).lower()
                if any(indicator in payload_str for indicator in market_indicators):
                    market_event_count += 1
        
        return market_event_count / len(events) > 0.5  # >50% market events
    
    async def _enhance_strand_with_causal_features(self, 
                                                 strand: EventStrand, 
                                                 rules: StrandCreationRule):
        """Enhance strand with causal features and relationships"""
        try:
            if not strand.causal_features:
                return
            
            feature_names = list(strand.causal_features.keys())
            
            for i, source_feature in enumerate(feature_names):
                for target_feature in feature_names[i+1:]:
                    correlation = await self._calculate_causal_correlation(
                        strand.causal_features[source_feature],
                        strand.causal_features[target_feature],
                        strand.timestamps_ns
                    )
                    
                    if abs(correlation) > self.causal_detection_threshold:
                        pattern_key = f"{source_feature}_to_{target_feature}"
                        if pattern_key not in strand.metadata:
                            strand.metadata[pattern_key] = correlation
            
            dag_template = self.dag_engine.get_template(rules.regime)
            if dag_template:
                strand.metadata['dag_template_id'] = dag_template.regime.value
                strand.metadata['dag_validation_score'] = await self._validate_strand_against_dag(
                    strand, dag_template
                )
            
        except Exception as e:
            self.logger.error(f"Failed to enhance strand with causal features: {e}")
    
    async def _calculate_causal_correlation(self, 
                                          source_data: np.ndarray, 
                                          target_data: np.ndarray,
                                          timestamps: np.ndarray) -> float:
        """Calculate causal correlation with lag analysis"""
        start_time = time.perf_counter()
        
        try:
            if len(source_data) != len(target_data) or len(source_data) < 3:
                return 0.0
            
            max_correlation = 0.0
            best_lag = 0
            
            max_lag = min(10, len(source_data) // 3)
            
            for lag in range(max_lag + 1):
                if lag == 0:
                    corr = np.corrcoef(source_data, target_data)[0, 1]
                else:
                    if len(source_data) > lag:
                        source_lagged = source_data[:-lag]
                        target_current = target_data[lag:]
                        
                        if len(source_lagged) > 1 and len(target_current) > 1:
                            corr = np.corrcoef(source_lagged, target_current)[0, 1]
                        else:
                            corr = 0.0
                    else:
                        corr = 0.0
                
                if not np.isnan(corr) and abs(corr) > abs(max_correlation):
                    max_correlation = corr
                    best_lag = lag
            
            causal_time_ms = (time.perf_counter() - start_time) * 1000
            self.performance_metrics["causal_detection_time_ms"] = causal_time_ms
            
            return max_correlation
            
        except Exception as e:
            self.logger.error(f"Causal correlation calculation failed: {e}")
            return 0.0
    
    async def _validate_strand_against_dag(self, 
                                         strand: EventStrand, 
                                         dag_template) -> float:
        """Validate strand against DAG template structure"""
        try:
            validation_score = 0.0
            total_checks = 0
            
            for edge in dag_template.edges:
                source_node, target_node = edge
                source_key = source_node.lower()
                target_key = target_node.lower()
                
                if source_key in strand.causal_features and target_key in strand.causal_features:
                    correlation = await self._calculate_causal_correlation(
                        strand.causal_features[source_key],
                        strand.causal_features[target_key],
                        strand.timestamps_ns
                    )
                    
                    if abs(correlation) > 0.1:  # Minimum threshold for edge validation
                        validation_score += abs(correlation)
                    
                    total_checks += 1
            
            return validation_score / total_checks if total_checks > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"DAG validation failed: {e}")
            return 0.0
    
    async def _update_causal_patterns(self, 
                                    strands: List[EventStrand], 
                                    regime: MarketRegime):
        """Update learned causal patterns from new strands"""
        try:
            for strand in strands:
                for key, value in strand.metadata.items():
                    if '_to_' in key and isinstance(value, (int, float)):
                        source_feature, target_feature = key.split('_to_')
                        
                        pattern = CausalPattern(
                            source_feature=source_feature,
                            target_feature=target_feature,
                            correlation_strength=float(value),
                            lag_ns=0,  # TODO: Extract lag information
                            confidence=abs(float(value)),
                            regime_context=regime,
                            sample_count=len(strand.timestamps_ns)
                        )
                        
                        pattern_key = f"{regime.value}_{source_feature}_{target_feature}"
                        
                        if pattern_key in self.causal_patterns:
                            existing = self.causal_patterns[pattern_key]
                            existing.correlation_strength = (
                                existing.correlation_strength * existing.sample_count + 
                                pattern.correlation_strength * pattern.sample_count
                            ) / (existing.sample_count + pattern.sample_count)
                            existing.sample_count += pattern.sample_count
                        else:
                            self.causal_patterns[pattern_key] = pattern
                
                self.pattern_history.append({
                    'strand_id': strand.strand_id,
                    'regime': regime.value,
                    'timestamp': time.time(),
                    'causal_features': list(strand.causal_features.keys())
                })
            
            self.library_stats.causal_patterns_detected = len(self.causal_patterns)
            
        except Exception as e:
            self.logger.error(f"Failed to update causal patterns: {e}")
    
    async def _store_strands_in_library(self, strands: List[EventStrand]):
        """Store strands in the library and data engine"""
        try:
            for strand in strands:
                self.strand_library[strand.strand_id] = strand
                
                try:
                    await self.event_processor._store_strand(strand)
                except Exception as e:
                    self.logger.warning(f"Failed to store strand {strand.strand_id} in data engine: {e}")
            
            self.library_stats.total_strands = len(self.strand_library)
            
            if self.library_stats.total_strands > 0:
                total_events = sum(len(strand.timestamps_ns) for strand in self.strand_library.values())
                self.library_stats.avg_strand_size = total_events / self.library_stats.total_strands
            
        except Exception as e:
            self.logger.error(f"Failed to store strands in library: {e}")
    
    def _update_performance_metrics(self, start_time: float, strands_created: int):
        """Update performance metrics"""
        total_time_ms = (time.perf_counter() - start_time) * 1000
        self.performance_metrics["total_processing_time_ms"] = total_time_ms
        
        if total_time_ms > 0:
            self.performance_metrics["strands_created_per_second"] = (strands_created * 1000) / total_time_ms
        
        self.library_stats.creation_rate_per_second = self.performance_metrics["strands_created_per_second"]
    
    async def search_strands_by_pattern(self, 
                                      causal_pattern: str, 
                                      regime: Optional[MarketRegime] = None,
                                      time_range: Optional[Tuple[int, int]] = None) -> List[EventStrand]:
        """Search strand library for specific causal patterns"""
        try:
            matching_strands = []
            
            for strand in self.strand_library.values():
                if regime and strand.metadata.get('regime_context') != regime.value:
                    continue
                
                if time_range:
                    start_time, end_time = time_range
                    strand_start = strand.timestamps_ns[0] if len(strand.timestamps_ns) > 0 else 0
                    strand_end = strand.timestamps_ns[-1] if len(strand.timestamps_ns) > 0 else 0
                    
                    if not (start_time <= strand_end and end_time >= strand_start):
                        continue
                
                if causal_pattern in strand.metadata:
                    matching_strands.append(strand)
                    
                    self._access_patterns[strand.strand_id].append(time.time())
            
            self.logger.info(f"Found {len(matching_strands)} strands matching pattern '{causal_pattern}'")
            return matching_strands
            
        except Exception as e:
            self.logger.error(f"Strand search failed: {e}")
            return []
    
    async def get_causal_insights(self, regime: Optional[MarketRegime] = None) -> Dict[str, Any]:
        """Get causal insights from learned patterns"""
        try:
            insights = {
                "total_patterns": len(self.causal_patterns),
                "strong_patterns": [],
                "regime_specific_patterns": {},
                "top_correlations": []
            }
            
            for pattern_key, pattern in self.causal_patterns.items():
                if regime and pattern.regime_context != regime:
                    continue
                
                if pattern.confidence > 0.7:
                    insights["strong_patterns"].append({
                        "source": pattern.source_feature,
                        "target": pattern.target_feature,
                        "strength": pattern.correlation_strength,
                        "confidence": pattern.confidence,
                        "regime": pattern.regime_context.value,
                        "sample_count": pattern.sample_count
                    })
                
                regime_key = pattern.regime_context.value
                if regime_key not in insights["regime_specific_patterns"]:
                    insights["regime_specific_patterns"][regime_key] = []
                
                insights["regime_specific_patterns"][regime_key].append({
                    "pattern": f"{pattern.source_feature} -> {pattern.target_feature}",
                    "strength": pattern.correlation_strength
                })
            
            sorted_patterns = sorted(
                self.causal_patterns.values(),
                key=lambda p: p.confidence,
                reverse=True
            )
            
            insights["top_correlations"] = [
                {
                    "pattern": f"{p.source_feature} -> {p.target_feature}",
                    "strength": p.correlation_strength,
                    "confidence": p.confidence,
                    "regime": p.regime_context.value
                }
                for p in sorted_patterns[:10]
            ]
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Failed to get causal insights: {e}")
            return {}
    
    def get_library_statistics(self) -> Dict[str, Any]:
        """Get comprehensive strand library statistics"""
        try:
            regime_distribution = defaultdict(int)
            for strand in self.strand_library.values():
                regime = strand.metadata.get('regime_context', 'unknown')
                regime_distribution[regime] += 1
            
            self.library_stats.regime_distribution = dict(regime_distribution)
            
            access_stats = {}
            for strand_id, access_times in self._access_patterns.items():
                if access_times:
                    access_stats[strand_id] = {
                        "access_count": len(access_times),
                        "last_access": max(access_times),
                        "avg_access_interval": np.mean(np.diff(sorted(access_times))) if len(access_times) > 1 else 0
                    }
            
            return {
                "library_stats": {
                    "total_strands": self.library_stats.total_strands,
                    "market_strands": self.library_stats.market_strands,
                    "general_strands": self.library_stats.general_strands,
                    "avg_strand_size": self.library_stats.avg_strand_size,
                    "causal_patterns_detected": self.library_stats.causal_patterns_detected,
                    "regime_distribution": self.library_stats.regime_distribution,
                    "creation_rate_per_second": self.library_stats.creation_rate_per_second
                },
                "performance_metrics": self.performance_metrics,
                "access_patterns": {
                    "total_accessed_strands": len(access_stats),
                    "most_accessed": sorted(
                        access_stats.items(),
                        key=lambda x: x[1]["access_count"],
                        reverse=True
                    )[:10]
                },
                "ml_clustering_enabled": self.enable_ml_clustering,
                "pattern_learning_window": self.pattern_learning_window,
                "causal_detection_threshold": self.causal_detection_threshold
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get library statistics: {e}")
            return {}
    
    async def optimize_library(self):
        """Optimize strand library based on access patterns and performance"""
        try:
            current_time = time.time()
            
            strands_to_promote = []
            strands_to_archive = []
            
            for strand_id, strand in self.strand_library.items():
                access_times = self._access_patterns.get(strand_id, [])
                
                if access_times:
                    recent_accesses = [t for t in access_times if current_time - t < 3600]  # Last hour
                    
                    if len(recent_accesses) > 5:  # Frequently accessed
                        strands_to_promote.append(strand_id)
                    elif not recent_accesses and access_times and current_time - max(access_times) > 86400:  # Not accessed in 24h
                        strands_to_archive.append(strand_id)
            
            for strand_id in strands_to_promote:
                strand = self.strand_library[strand_id]
                try:
                    await self.event_processor._store_strand(strand)
                    self.logger.debug(f"Promoted strand {strand_id} to hot storage")
                except Exception as e:
                    self.logger.warning(f"Failed to promote strand {strand_id}: {e}")
            
            for strand_id in strands_to_archive[:100]:  # Limit archiving to prevent performance impact
                if strand_id in self.strand_library:
                    del self.strand_library[strand_id]
                    self.logger.debug(f"Archived strand {strand_id}")
            
            self.library_stats.total_strands = len(self.strand_library)
            
            self.logger.info(f"Library optimization: promoted {len(strands_to_promote)}, "
                           f"archived {len(strands_to_archive)} strands")
            
        except Exception as e:
            self.logger.error(f"Library optimization failed: {e}")
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            await self.data_engine.cleanup()
            await self.event_processor.stop_processing()
            self.logger.info("AutomatedStrandCreator cleanup completed")
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
