"""
EventStrand and MarketStrand classes with vectorized operations
Optimized data structures for high-frequency event processing
"""

import numpy as np
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
import hashlib
from datetime import datetime
import struct
import json

@dataclass
class EventStrand:
    """Optimized event strand for high-frequency processing with vectorized operations"""
    strand_id: str
    timestamps_ns: np.ndarray  # Nanosecond timestamps
    event_types: np.ndarray    # Vectorized event type IDs
    payloads: np.ndarray       # Compressed payload data
    source_ids: np.ndarray     # Source attribution
    first_occurrence_flags: np.ndarray  # Boolean array for first occurrence
    causal_features: Dict[str, np.ndarray] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Ensure chronological ordering and validate data integrity"""
        if len(self.timestamps_ns) > 1:
            sort_indices = np.argsort(self.timestamps_ns)
            self.timestamps_ns = self.timestamps_ns[sort_indices]
            self.event_types = self.event_types[sort_indices]
            self.payloads = self.payloads[sort_indices]
            self.source_ids = self.source_ids[sort_indices]
            self.first_occurrence_flags = self.first_occurrence_flags[sort_indices]
            
            for feature_name, feature_data in self.causal_features.items():
                if isinstance(feature_data, np.ndarray) and len(feature_data) == len(sort_indices):
                    self.causal_features[feature_name] = feature_data[sort_indices]
    
    @classmethod
    def create_from_events(cls, events: List[Dict[str, Any]], 
                          regime_context: Optional[str] = None) -> 'EventStrand':
        """Vectorized creation from event list with performance optimization"""
        if not events:
            raise ValueError("Cannot create strand from empty events list")
        
        n_events = len(events)
        
        timestamps_ns = np.zeros(n_events, dtype=np.int64)
        event_types = np.zeros(n_events, dtype=np.int32)
        payloads = np.zeros(n_events, dtype=object)
        source_ids = np.zeros(n_events, dtype=np.int32)
        first_occurrence_flags = np.zeros(n_events, dtype=bool)
        
        seen_events = set()
        
        for i, event in enumerate(events):
            timestamps_ns[i] = event.get('timestamp_ns', int(datetime.now().timestamp() * 1e9))
            event_types[i] = event.get('type_id', 0)
            payloads[i] = cls._compress_payload(event.get('payload', {}))
            source_ids[i] = event.get('source_id', 0)
            
            event_signature = cls._create_event_signature(event)
            first_occurrence_flags[i] = event_signature not in seen_events
            seen_events.add(event_signature)
        
        strand_id = cls._generate_strand_id(events, regime_context)
        
        causal_features = cls._extract_causal_features(events)
        
        metadata = {
            "created_at": datetime.now().isoformat(),
            "regime_context": regime_context,
            "event_count": n_events,
            "time_span_ns": int(timestamps_ns[-1] - timestamps_ns[0]) if n_events > 1 else 0,
            "unique_sources": len(np.unique(source_ids)),
            "first_occurrence_count": int(np.sum(first_occurrence_flags))
        }
        
        return cls(
            strand_id=strand_id,
            timestamps_ns=timestamps_ns,
            event_types=event_types,
            payloads=payloads,
            source_ids=source_ids,
            first_occurrence_flags=first_occurrence_flags,
            causal_features=causal_features,
            metadata=metadata
        )
    
    @staticmethod
    def _compress_payload(payload: Any) -> bytes:
        """Compress payload data for efficient storage"""
        try:
            if isinstance(payload, dict):
                json_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
                return json_str.encode('utf-8')
            elif isinstance(payload, (str, bytes)):
                return str(payload).encode('utf-8')
            else:
                return str(payload).encode('utf-8')
        except Exception:
            return b''
    
    @staticmethod
    def _create_event_signature(event: Dict[str, Any]) -> str:
        """Create unique signature for event to detect first occurrence"""
        key_fields = ['type_id', 'source_id', 'payload']
        signature_data = {}
        
        for field in key_fields:
            if field in event:
                signature_data[field] = event[field]
        
        signature_str = json.dumps(signature_data, sort_keys=True, separators=(',', ':'))
        return hashlib.md5(signature_str.encode()).hexdigest()
    
    @staticmethod
    def _generate_strand_id(events: List[Dict[str, Any]], 
                           regime_context: Optional[str] = None) -> str:
        """Generate unique strand ID based on events and context"""
        if not events:
            return hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()
        
        id_components = [
            str(len(events)),
            str(events[0].get('timestamp_ns', 0)),
            str(events[-1].get('timestamp_ns', 0)),
            regime_context or "unknown"
        ]
        
        for event in events[:5]:  # Use first 5 events for ID
            id_components.append(str(event.get('type_id', 0)))
            id_components.append(str(event.get('source_id', 0)))
        
        id_string = '|'.join(id_components)
        return hashlib.sha256(id_string.encode()).hexdigest()[:32]
    
    @staticmethod
    def _extract_causal_features(events: List[Dict[str, Any]]) -> Dict[str, np.ndarray]:
        """Extract causal features from events using vectorized operations"""
        causal_features = {}
        
        if not events:
            return causal_features
        
        feature_keys = ['price', 'volume', 'sentiment', 'volatility', 'news_impact', 'order_flow']
        
        for feature_key in feature_keys:
            feature_values = []
            for event in events:
                if feature_key in event:
                    value = event[feature_key]
                    if isinstance(value, (int, float)):
                        feature_values.append(float(value))
                    elif isinstance(value, list) and value and isinstance(value[0], (int, float)):
                        feature_values.append(float(value[0]))
                else:
                    feature_values.append(0.0)
            
            if feature_values:
                causal_features[feature_key] = np.array(feature_values, dtype=np.float64)
        
        if len(events) > 1:
            timestamps = np.array([e.get('timestamp_ns', 0) for e in events], dtype=np.int64)
            time_deltas = np.diff(timestamps)
            causal_features['time_deltas_ns'] = np.concatenate([[0], time_deltas])
            
            if 'price' in causal_features:
                price_changes = np.diff(causal_features['price'])
                causal_features['price_changes'] = np.concatenate([[0], price_changes])
                
                if len(price_changes) > 0:
                    causal_features['price_volatility'] = np.array([
                        np.std(causal_features['price'][max(0, i-10):i+1]) 
                        for i in range(len(causal_features['price']))
                    ])
        
        return causal_features
    
    def get_events_in_time_range(self, start_ns: int, end_ns: int) -> 'EventStrand':
        """Get events within specified time range using vectorized operations"""
        mask = (self.timestamps_ns >= start_ns) & (self.timestamps_ns <= end_ns)
        
        if not np.any(mask):
            return EventStrand.create_from_events([])
        
        filtered_causal_features = {}
        for feature_name, feature_data in self.causal_features.items():
            if isinstance(feature_data, np.ndarray) and len(feature_data) == len(mask):
                filtered_causal_features[feature_name] = feature_data[mask]
        
        return EventStrand(
            strand_id=f"{self.strand_id}_filtered_{start_ns}_{end_ns}",
            timestamps_ns=self.timestamps_ns[mask],
            event_types=self.event_types[mask],
            payloads=self.payloads[mask],
            source_ids=self.source_ids[mask],
            first_occurrence_flags=self.first_occurrence_flags[mask],
            causal_features=filtered_causal_features,
            metadata={**self.metadata, "filtered": True, "filter_range": [start_ns, end_ns]}
        )
    
    def get_first_occurrences_only(self) -> 'EventStrand':
        """Get only first occurrence events using vectorized operations"""
        mask = self.first_occurrence_flags
        
        if not np.any(mask):
            return EventStrand.create_from_events([])
        
        filtered_causal_features = {}
        for feature_name, feature_data in self.causal_features.items():
            if isinstance(feature_data, np.ndarray) and len(feature_data) == len(mask):
                filtered_causal_features[feature_name] = feature_data[mask]
        
        return EventStrand(
            strand_id=f"{self.strand_id}_first_only",
            timestamps_ns=self.timestamps_ns[mask],
            event_types=self.event_types[mask],
            payloads=self.payloads[mask],
            source_ids=self.source_ids[mask],
            first_occurrence_flags=self.first_occurrence_flags[mask],
            causal_features=filtered_causal_features,
            metadata={**self.metadata, "first_occurrences_only": True}
        )
    
    def calculate_causal_correlations(self) -> Dict[str, float]:
        """Calculate causal correlations between features using vectorized operations"""
        correlations = {}
        
        feature_names = list(self.causal_features.keys())
        
        for i, feature1 in enumerate(feature_names):
            for feature2 in feature_names[i+1:]:
                data1 = self.causal_features[feature1]
                data2 = self.causal_features[feature2]
                
                if len(data1) == len(data2) and len(data1) > 1:
                    try:
                        correlation = np.corrcoef(data1, data2)[0, 1]
                        if not np.isnan(correlation):
                            correlations[f"{feature1}_vs_{feature2}"] = float(correlation)
                    except Exception:
                        pass
        
        return correlations
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert strand to dictionary for serialization"""
        return {
            "strand_id": self.strand_id,
            "timestamps_ns": self.timestamps_ns.tolist(),
            "event_types": self.event_types.tolist(),
            "payloads": [payload.decode('utf-8') if isinstance(payload, bytes) else str(payload) 
                        for payload in self.payloads],
            "source_ids": self.source_ids.tolist(),
            "first_occurrence_flags": self.first_occurrence_flags.tolist(),
            "causal_features": {k: v.tolist() if isinstance(v, np.ndarray) else v 
                               for k, v in self.causal_features.items()},
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EventStrand':
        """Create strand from dictionary"""
        causal_features = {}
        for k, v in data.get("causal_features", {}).items():
            if isinstance(v, list):
                causal_features[k] = np.array(v, dtype=np.float64)
            else:
                causal_features[k] = v
        
        payloads = np.array([
            payload.encode('utf-8') if isinstance(payload, str) else payload
            for payload in data.get("payloads", [])
        ], dtype=object)
        
        return cls(
            strand_id=data["strand_id"],
            timestamps_ns=np.array(data["timestamps_ns"], dtype=np.int64),
            event_types=np.array(data["event_types"], dtype=np.int32),
            payloads=payloads,
            source_ids=np.array(data["source_ids"], dtype=np.int32),
            first_occurrence_flags=np.array(data["first_occurrence_flags"], dtype=bool),
            causal_features=causal_features,
            metadata=data.get("metadata", {})
        )

class MarketStrand(EventStrand):
    """Specialized strand for market data with financial metrics and optimizations"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._price_data: Optional[np.ndarray] = None
        self._volume_data: Optional[np.ndarray] = None
        self._volatility_metrics: Optional[np.ndarray] = None
        self._market_indicators: Dict[str, np.ndarray] = {}
    
    @property
    def price_data(self) -> Optional[np.ndarray]:
        """Get price data with lazy loading"""
        if self._price_data is None and 'price' in self.causal_features:
            self._price_data = self.causal_features['price']
        return self._price_data
    
    @property
    def volume_data(self) -> Optional[np.ndarray]:
        """Get volume data with lazy loading"""
        if self._volume_data is None and 'volume' in self.causal_features:
            self._volume_data = self.causal_features['volume']
        return self._volume_data
    
    @property
    def volatility_metrics(self) -> Optional[np.ndarray]:
        """Get volatility metrics with lazy computation"""
        if self._volatility_metrics is None and self.price_data is not None:
            self._volatility_metrics = self._calculate_volatility_metrics()
        return self._volatility_metrics
    
    def _calculate_volatility_metrics(self) -> np.ndarray:
        """Calculate rolling volatility metrics using vectorized operations"""
        if self.price_data is None or len(self.price_data) < 2:
            return np.array([])
        
        returns = np.diff(np.log(self.price_data + 1e-8))
        
        volatility_windows = [5, 10, 20]
        volatilities = []
        
        for window in volatility_windows:
            rolling_vol = np.array([
                np.std(returns[max(0, i-window):i+1]) if i >= window-1 else np.nan
                for i in range(len(returns))
            ])
            volatilities.append(rolling_vol)
        
        return np.column_stack(volatilities)
    
    def calculate_market_indicators(self) -> Dict[str, np.ndarray]:
        """Calculate comprehensive market indicators using vectorized operations"""
        if self.price_data is None:
            return {}
        
        indicators = {}
        
        if len(self.price_data) >= 20:
            indicators['sma_20'] = self._calculate_sma(self.price_data, 20)
            indicators['ema_20'] = self._calculate_ema(self.price_data, 20)
        
        if len(self.price_data) >= 50:
            indicators['sma_50'] = self._calculate_sma(self.price_data, 50)
        
        if len(self.price_data) >= 2:
            indicators['returns'] = np.concatenate([[0], np.diff(self.price_data) / (self.price_data[:-1] + 1e-8)])
            indicators['log_returns'] = np.concatenate([[0], np.diff(np.log(self.price_data + 1e-8))])
        
        if self.volume_data is not None and len(self.volume_data) >= 20:
            indicators['volume_sma_20'] = self._calculate_sma(self.volume_data, 20)
            
            if len(self.price_data) == len(self.volume_data):
                indicators['vwap'] = self._calculate_vwap(self.price_data, self.volume_data)
        
        if len(self.price_data) >= 14:
            indicators['rsi'] = self._calculate_rsi(self.price_data, 14)
        
        self._market_indicators = indicators
        return indicators
    
    @staticmethod
    def _calculate_sma(data: np.ndarray, window: int) -> np.ndarray:
        """Calculate Simple Moving Average using vectorized operations"""
        sma = np.full(len(data), np.nan)
        for i in range(window-1, len(data)):
            sma[i] = np.mean(data[i-window+1:i+1])
        return sma
    
    @staticmethod
    def _calculate_ema(data: np.ndarray, window: int) -> np.ndarray:
        """Calculate Exponential Moving Average using vectorized operations"""
        alpha = 2.0 / (window + 1)
        ema = np.zeros(len(data))
        ema[0] = data[0]
        
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
        
        return ema
    
    @staticmethod
    def _calculate_vwap(prices: np.ndarray, volumes: np.ndarray) -> np.ndarray:
        """Calculate Volume Weighted Average Price using vectorized operations"""
        cumulative_pv = np.cumsum(prices * volumes)
        cumulative_volume = np.cumsum(volumes)
        
        vwap = np.divide(cumulative_pv, cumulative_volume, 
                        out=np.zeros_like(cumulative_pv), 
                        where=cumulative_volume!=0)
        return vwap
    
    @staticmethod
    def _calculate_rsi(prices: np.ndarray, window: int = 14) -> np.ndarray:
        """Calculate Relative Strength Index using vectorized operations"""
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gains = np.full(len(prices), np.nan)
        avg_losses = np.full(len(prices), np.nan)
        
        if len(gains) >= window:
            avg_gains[window] = np.mean(gains[:window])
            avg_losses[window] = np.mean(losses[:window])
            
            for i in range(window + 1, len(prices)):
                avg_gains[i] = (avg_gains[i-1] * (window-1) + gains[i-1]) / window
                avg_losses[i] = (avg_losses[i-1] * (window-1) + losses[i-1]) / window
        
        rs = np.divide(avg_gains, avg_losses, out=np.zeros_like(avg_gains), where=avg_losses!=0)
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def detect_price_patterns(self) -> Dict[str, Any]:
        """Detect price patterns using vectorized operations"""
        if self.price_data is None or len(self.price_data) < 10:
            return {}
        
        patterns = {}
        
        returns = np.diff(self.price_data) / (self.price_data[:-1] + 1e-8)
        
        patterns['trend_direction'] = 'up' if np.mean(returns) > 0 else 'down'
        patterns['volatility_regime'] = 'high' if np.std(returns) > 0.02 else 'low'
        
        if len(self.price_data) >= 20:
            sma_20 = self._calculate_sma(self.price_data, 20)
            current_price = self.price_data[-1]
            current_sma = sma_20[-1]
            
            if not np.isnan(current_sma):
                patterns['price_vs_sma20'] = 'above' if current_price > current_sma else 'below'
                patterns['sma20_distance_pct'] = ((current_price - current_sma) / current_sma) * 100
        
        recent_highs = np.max(self.price_data[-10:]) if len(self.price_data) >= 10 else self.price_data[-1]
        recent_lows = np.min(self.price_data[-10:]) if len(self.price_data) >= 10 else self.price_data[-1]
        
        patterns['near_recent_high'] = abs(self.price_data[-1] - recent_highs) / recent_highs < 0.01
        patterns['near_recent_low'] = abs(self.price_data[-1] - recent_lows) / recent_lows < 0.01
        
        return patterns
    
    @classmethod
    def create_from_market_events(cls, events: List[Dict[str, Any]], 
                                 regime_context: Optional[str] = None) -> 'MarketStrand':
        """Create MarketStrand with market-specific optimizations"""
        strand = super().create_from_events(events, regime_context)
        
        market_strand = cls(
            strand_id=strand.strand_id,
            timestamps_ns=strand.timestamps_ns,
            event_types=strand.event_types,
            payloads=strand.payloads,
            source_ids=strand.source_ids,
            first_occurrence_flags=strand.first_occurrence_flags,
            causal_features=strand.causal_features,
            metadata=strand.metadata
        )
        
        market_strand.calculate_market_indicators()
        
        market_strand.metadata.update({
            "strand_type": "market",
            "price_range": [float(np.min(market_strand.price_data)), float(np.max(market_strand.price_data))] 
                          if market_strand.price_data is not None else None,
            "volume_total": float(np.sum(market_strand.volume_data)) 
                           if market_strand.volume_data is not None else None,
            "patterns": market_strand.detect_price_patterns()
        })
        
        return market_strand
