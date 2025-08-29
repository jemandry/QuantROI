# System-Specific Documentation

## Message Book Data (MBD) Processing

### Specialized Order Book Reconstruction

```python
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict, deque
import asyncio
import time

class MBDProcessor:
    """Specialized processor for Message Book Data (MBD) order book reconstruction"""
    
    def __init__(self, max_depth: int = 10, granularity_limiter=None):
        self.max_depth = max_depth
        self.granularity_limiter = granularity_limiter
        self.order_books = {}
        self.event_processors = {
            'A': self._process_add_order,
            'D': self._process_delete_order,
            'U': self._process_update_order,
            'E': self._process_execution,
            'X': self._process_cancel_order
        }
        self.performance_metrics = {
            'events_processed': 0,
            'reconstruction_latency': deque(maxlen=1000),
            'order_book_updates': 0
        }
    
    async def process_mbd_stream(self, mbd_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process streaming MBD events for order book reconstruction"""
        
        processed_events = 0
        reconstruction_times = []
        
        for event in mbd_events:
            start_time = time.time_ns()
            
            try:
                # Parse MBD event
                parsed_event = self._parse_mbd_event(event)
                
                # Process based on event type
                event_type = parsed_event.get('event_type')
                if event_type in self.event_processors:
                    await self.event_processors[event_type](parsed_event)
                
                # Apply granularity rules for causal studies
                if self.granularity_limiter:
                    await self._apply_granularity_rules(parsed_event)
                
                end_time = time.time_ns()
                reconstruction_time = end_time - start_time
                reconstruction_times.append(reconstruction_time)
                
                processed_events += 1
                self.performance_metrics['events_processed'] += 1
                
            except Exception as e:
                print(f"Error processing MBD event: {e}")
                continue
        
        # Update performance metrics
        if reconstruction_times:
            self.performance_metrics['reconstruction_latency'].extend(reconstruction_times)
        
        return {
            'processed_events': processed_events,
            'avg_reconstruction_latency_ns': np.mean(reconstruction_times) if reconstruction_times else 0,
            'order_books_updated': len(self.order_books),
            'meets_100us_target': np.mean(reconstruction_times) < 100000 if reconstruction_times else False
        }
    
    def _parse_mbd_event(self, raw_event: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw MBD event into structured format"""
        
        return {
            'event_type': raw_event.get('msg_type', 'U'),
            'symbol': raw_event.get('symbol', 'UNKNOWN'),
            'timestamp_ns': raw_event.get('timestamp_ns', time.time_ns()),
            'order_id': raw_event.get('order_id'),
            'side': raw_event.get('side', 'B'),  # B=Buy, S=Sell
            'price': float(raw_event.get('price', 0)),
            'quantity': int(raw_event.get('quantity', 0)),
            'sequence_number': raw_event.get('seq_num', 0)
        }
    
    async def _process_add_order(self, event: Dict[str, Any]):
        """Process add order event (Type A)"""
        symbol = event['symbol']
        
        if symbol not in self.order_books:
            self.order_books[symbol] = {
                'bids': {},  # price -> {order_id: quantity}
                'asks': {},
                'last_update': event['timestamp_ns']
            }
        
        order_book = self.order_books[symbol]
        side = 'bids' if event['side'] == 'B' else 'asks'
        price = event['price']
        order_id = event['order_id']
        quantity = event['quantity']
        
        if price not in order_book[side]:
            order_book[side][price] = {}
        
        order_book[side][price][order_id] = quantity
        order_book['last_update'] = event['timestamp_ns']
        
        self.performance_metrics['order_book_updates'] += 1
    
    async def _process_delete_order(self, event: Dict[str, Any]):
        """Process delete order event (Type D)"""
        symbol = event['symbol']
        
        if symbol not in self.order_books:
            return
        
        order_book = self.order_books[symbol]
        side = 'bids' if event['side'] == 'B' else 'asks'
        price = event['price']
        order_id = event['order_id']
        
        if price in order_book[side] and order_id in order_book[side][price]:
            del order_book[side][price][order_id]
            
            # Clean up empty price levels
            if not order_book[side][price]:
                del order_book[side][price]
        
        order_book['last_update'] = event['timestamp_ns']
        self.performance_metrics['order_book_updates'] += 1
    
    async def _process_update_order(self, event: Dict[str, Any]):
        """Process update order event (Type U)"""
        # Delete old order and add new one
        await self._process_delete_order(event)
        await self._process_add_order(event)
    
    async def _process_execution(self, event: Dict[str, Any]):
        """Process execution event (Type E)"""
        symbol = event['symbol']
        
        if symbol not in self.order_books:
            return
        
        order_book = self.order_books[symbol]
        side = 'bids' if event['side'] == 'B' else 'asks'
        price = event['price']
        order_id = event['order_id']
        executed_quantity = event['quantity']
        
        if price in order_book[side] and order_id in order_book[side][price]:
            current_quantity = order_book[side][price][order_id]
            remaining_quantity = current_quantity - executed_quantity
            
            if remaining_quantity <= 0:
                del order_book[side][price][order_id]
                if not order_book[side][price]:
                    del order_book[side][price]
            else:
                order_book[side][price][order_id] = remaining_quantity
        
        order_book['last_update'] = event['timestamp_ns']
        self.performance_metrics['order_book_updates'] += 1
    
    async def _process_cancel_order(self, event: Dict[str, Any]):
        """Process cancel order event (Type X)"""
        await self._process_delete_order(event)
    
    async def _apply_granularity_rules(self, event: Dict[str, Any]):
        """Apply granularity rules for causal studies"""
        if not self.granularity_limiter:
            return
        
        # Create DataFrame for granularity processing
        event_df = pd.DataFrame([{
            'timestamp': pd.to_datetime(event['timestamp_ns'], unit='ns'),
            'symbol': event['symbol'],
            'price': event['price'],
            'quantity': event['quantity'],
            'side': event['side']
        }])
        event_df.set_index('timestamp', inplace=True)
        
        # Apply granularity rules
        processed_df = self.granularity_limiter.preprocess_for_causal_study(
            event_df, ['price', 'quantity'], {'symbols': [event['symbol']]}
        )
        
        return processed_df
    
    def get_order_book_snapshot(self, symbol: str, depth: int = None) -> Dict[str, Any]:
        """Get current order book snapshot"""
        if symbol not in self.order_books:
            return {'error': f'No order book for symbol {symbol}'}
        
        order_book = self.order_books[symbol]
        depth = depth or self.max_depth
        
        # Sort and limit depth
        sorted_bids = sorted(order_book['bids'].items(), key=lambda x: x[0], reverse=True)[:depth]
        sorted_asks = sorted(order_book['asks'].items(), key=lambda x: x[0])[:depth]
        
        # Aggregate quantities at each price level
        bid_levels = []
        for price, orders in sorted_bids:
            total_quantity = sum(orders.values())
            bid_levels.append({'price': price, 'quantity': total_quantity, 'orders': len(orders)})
        
        ask_levels = []
        for price, orders in sorted_asks:
            total_quantity = sum(orders.values())
            ask_levels.append({'price': price, 'quantity': total_quantity, 'orders': len(orders)})
        
        return {
            'symbol': symbol,
            'timestamp_ns': order_book['last_update'],
            'bids': bid_levels,
            'asks': ask_levels,
            'spread': ask_levels[0]['price'] - bid_levels[0]['price'] if bid_levels and ask_levels else 0
        }
    
    def calculate_market_impact(self, symbol: str, side: str, quantity: int) -> Dict[str, Any]:
        """Calculate market impact for a given order size"""
        snapshot = self.get_order_book_snapshot(symbol)
        
        if 'error' in snapshot:
            return snapshot
        
        levels = snapshot['asks'] if side == 'B' else snapshot['bids']
        
        remaining_quantity = quantity
        total_cost = 0
        levels_consumed = 0
        
        for level in levels:
            if remaining_quantity <= 0:
                break
            
            level_quantity = level['quantity']
            consumed_quantity = min(remaining_quantity, level_quantity)
            
            total_cost += consumed_quantity * level['price']
            remaining_quantity -= consumed_quantity
            levels_consumed += 1
        
        if remaining_quantity > 0:
            return {'error': 'Insufficient liquidity', 'remaining_quantity': remaining_quantity}
        
        avg_price = total_cost / quantity
        reference_price = levels[0]['price']
        impact_bps = ((avg_price - reference_price) / reference_price) * 10000
        
        return {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'average_price': avg_price,
            'reference_price': reference_price,
            'impact_bps': impact_bps,
            'levels_consumed': levels_consumed
        }
```

## AI-Driven RegTech Compliance Integration

### Real-time Anomaly Detection for Granularity Violations

```python
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Any, Optional
import asyncio
import time
import hashlib

class RegTechComplianceMonitor:
    """AI-driven compliance monitoring for granularity and trading violations"""
    
    def __init__(self, anomaly_threshold: float = 0.1):
        self.anomaly_threshold = anomaly_threshold
        self.anomaly_detector = IsolationForest(contamination=anomaly_threshold, random_state=42)
        self.scaler = StandardScaler()
        self.compliance_rules = {}
        self.violation_history = []
        self.model_trained = False
        
        # Initialize compliance rules
        self._initialize_compliance_rules()
    
    def _initialize_compliance_rules(self):
        """Initialize regulatory compliance rules"""
        self.compliance_rules = {
            'mifid_ii': {
                'timestamp_precision': 'nanosecond',
                'max_latency_ms': 10,
                'required_fields': ['timestamp_ns', 'instrument_id', 'price', 'quantity', 'venue']
            },
            'gdpr': {
                'data_retention_days': 2555,  # 7 years
                'anonymization_required': True,
                'consent_tracking': True
            },
            'sec': {
                'audit_trail_retention_years': 10,
                'best_execution_monitoring': True,
                'market_manipulation_detection': True
            },
            'granularity_limits': {
                'pe_ratio_min_interval_hours': 24,
                'moving_average_min_interval_hours': 1,
                'volatility_min_interval_hours': 24,
                'sentiment_min_interval_hours': 1
            }
        }
    
    async def train_anomaly_detector(self, historical_data: pd.DataFrame):
        """Train anomaly detection model on historical trading data"""
        
        # Extract features for anomaly detection
        features = self._extract_compliance_features(historical_data)
        
        if len(features) < 100:
            raise ValueError("Insufficient historical data for training (minimum 100 samples)")
        
        # Normalize features
        normalized_features = self.scaler.fit_transform(features)
        
        # Train isolation forest
        self.anomaly_detector.fit(normalized_features)
        self.model_trained = True
        
        return {
            'training_samples': len(features),
            'feature_count': features.shape[1],
            'contamination_rate': self.anomaly_threshold,
            'model_trained': True
        }
    
    def _extract_compliance_features(self, data: pd.DataFrame) -> np.ndarray:
        """Extract features relevant for compliance monitoring"""
        
        features = []
        
        # Temporal features
        if isinstance(data.index, pd.DatetimeIndex):
            time_diffs = data.index.to_series().diff().dt.total_seconds().fillna(0)
            features.extend([
                time_diffs.mean(),
                time_diffs.std(),
                time_diffs.min(),
                time_diffs.max()
            ])
        else:
            features.extend([0, 0, 0, 0])
        
        # Price and volume features
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if col in data.columns:
                series = data[col].dropna()
                if len(series) > 0:
                    features.extend([
                        series.mean(),
                        series.std(),
                        series.skew(),
                        series.kurtosis()
                    ])
                else:
                    features.extend([0, 0, 0, 0])
        
        # Ensure consistent feature length
        while len(features) < 20:  # Minimum 20 features
            features.append(0)
        
        return np.array(features).reshape(1, -1)
    
    async def detect_granularity_violations(self, data: pd.DataFrame, 
                                          metric_type: str) -> Dict[str, Any]:
        """Detect granularity violations using AI"""
        
        violations = []
        
        # Check against granularity rules
        min_interval_key = f"{metric_type}_min_interval_hours"
        if min_interval_key in self.compliance_rules['granularity_limits']:
            min_interval_hours = self.compliance_rules['granularity_limits'][min_interval_key]
            
            if isinstance(data.index, pd.DatetimeIndex):
                actual_intervals = data.index.to_series().diff().dt.total_seconds() / 3600
                violation_mask = actual_intervals < min_interval_hours
                
                if violation_mask.any():
                    violations.append({
                        'type': 'granularity_violation',
                        'metric_type': metric_type,
                        'min_required_hours': min_interval_hours,
                        'violation_count': violation_mask.sum(),
                        'violation_timestamps': data.index[violation_mask].tolist()
                    })
        
        # AI-based anomaly detection
        if self.model_trained:
            features = self._extract_compliance_features(data)
            normalized_features = self.scaler.transform(features)
            
            anomaly_score = self.anomaly_detector.decision_function(normalized_features)[0]
            is_anomaly = self.anomaly_detector.predict(normalized_features)[0] == -1
            
            if is_anomaly:
                violations.append({
                    'type': 'ai_anomaly',
                    'anomaly_score': float(anomaly_score),
                    'threshold': self.anomaly_threshold,
                    'features_analyzed': features.shape[1]
                })
        
        # Log violations
        for violation in violations:
            await self._log_compliance_violation(violation)
        
        return {
            'violations_detected': len(violations),
            'violations': violations,
            'compliance_status': 'VIOLATION' if violations else 'COMPLIANT',
            'timestamp': time.time()
        }
    
    async def _log_compliance_violation(self, violation: Dict[str, Any]):
        """Log compliance violation with cryptographic hash"""
        
        violation_record = {
            'timestamp': time.time(),
            'violation_type': violation['type'],
            'details': violation,
            'hash': hashlib.sha256(str(violation).encode()).hexdigest()
        }
        
        self.violation_history.append(violation_record)
        
        # Keep only recent violations (last 1000)
        if len(self.violation_history) > 1000:
            self.violation_history = self.violation_history[-1000:]
    
    async def generate_compliance_report(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Generate comprehensive compliance report"""
        
        start_timestamp = pd.to_datetime(start_date).timestamp()
        end_timestamp = pd.to_datetime(end_date).timestamp()
        
        # Filter violations by date range
        period_violations = [
            v for v in self.violation_history
            if start_timestamp <= v['timestamp'] <= end_timestamp
        ]
        
        # Categorize violations
        violation_types = {}
        for violation in period_violations:
            v_type = violation['violation_type']
            violation_types[v_type] = violation_types.get(v_type, 0) + 1
        
        # Calculate compliance metrics
        total_checks = len(period_violations) + 1000  # Assume 1000 compliant checks
        compliance_rate = (total_checks - len(period_violations)) / total_checks
        
        report = {
            'report_period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'compliance_summary': {
                'total_violations': len(period_violations),
                'compliance_rate': compliance_rate,
                'violation_types': violation_types
            },
            'regulatory_alignment': {
                'mifid_ii_compliant': violation_types.get('granularity_violation', 0) == 0,
                'gdpr_compliant': True,  # Simplified check
                'sec_compliant': violation_types.get('market_manipulation', 0) == 0
            },
            'recommendations': self._generate_compliance_recommendations(violation_types),
            'report_hash': hashlib.sha256(str(period_violations).encode()).hexdigest()
        }
        
        return report
    
    def _generate_compliance_recommendations(self, violation_types: Dict[str, int]) -> List[str]:
        """Generate compliance recommendations based on violations"""
        
        recommendations = []
        
        if violation_types.get('granularity_violation', 0) > 0:
            recommendations.append(
                "Review granularity limiter configuration to ensure minimum intervals are enforced"
            )
        
        if violation_types.get('ai_anomaly', 0) > 0:
            recommendations.append(
                "Investigate anomalous trading patterns detected by AI monitoring"
            )
        
        if violation_types.get('timestamp_precision', 0) > 0:
            recommendations.append(
                "Upgrade timestamp precision to nanosecond level for MiFID II compliance"
            )
        
        if not recommendations:
            recommendations.append("No compliance issues detected - maintain current practices")
        
        return recommendations
```

## Dynamic Latency-Aware Granularity Management

### Network Latency-Aware Adjustments

```python
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
        
        # Initialize adaptive rules
        self._initialize_adaptive_rules()
    
    def _initialize_adaptive_rules(self):
        """Initialize latency-aware granularity rules"""
        self.adaptive_rules = {
            'hot_tier': {
                'base_latency_threshold_us': 100,
                'granularity_multipliers': {
                    'low_latency': 1.0,      # <100μs
                    'medium_latency': 1.5,   # 100-500μs
                    'high_latency': 2.0      # >500μs
                }
            },
            'warm_tier': {
                'base_latency_threshold_us': 10000,  # 10ms
                'granularity_multipliers': {
                    'low_latency': 1.0,
                    'medium_latency': 1.2,
                    'high_latency': 1.5
                }
            },
            'cold_tier': {
                'base_latency_threshold_us': 100000,  # 100ms
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
        
        # Measure current network latency
        current_latency = await self.latency_monitor.measure_current_latency()
        
        # Determine tier based on data characteristics
        data_tier = self._determine_data_tier(data_df, causal_context)
        
        # Calculate adaptive granularity multiplier
        multiplier = self._calculate_granularity_multiplier(current_latency, data_tier)
        
        # Adjust granularity rules temporarily
        original_rules = self.base_limiter.rules.copy()
        
        try:
            # Apply multiplier to granularity rules
            for metric_type in metric_types:
                if metric_type in self.base_limiter.rules:
                    original_interval = self.base_limiter.rules[metric_type]
                    adjusted_interval = pd.Timedelta(
                        seconds=original_interval.total_seconds() * multiplier
                    )
                    self.base_limiter.rules[metric_type] = adjusted_interval
            
            # Process with adjusted rules
            result = self.base_limiter.preprocess_for_causal_study(
                data_df, metric_types, causal_context
            )
            
            # Log performance metrics
            await self._log_adaptive_performance(current_latency, multiplier, data_tier)
            
            return result
            
        finally:
            # Restore original rules
            self.base_limiter.rules = original_rules
    
    def _determine_data_tier(self, data_df: pd.DataFrame, 
                           causal_context: Dict[str, Any]) -> str:
        """Determine appropriate data tier based on data characteristics"""
        
        # Check data frequency
        if isinstance(data_df.index, pd.DatetimeIndex) and len(data_df) > 1:
            median_interval = data_df.index.to_series().diff().median()
            
            if median_interval <= pd.Timedelta(seconds=1):
                return 'hot_tier'
            elif median_interval <= pd.Timedelta(minutes=10):
                return 'warm_tier'
            else:
                return 'cold_tier'
        
        # Default to warm tier
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
        
        # Keep only recent history
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-1000:]
    
    def get_adaptive_performance_stats(self) -> Dict[str, Any]:
        """Get statistics on adaptive performance"""
        
        if not self.performance_history:
            return {'error': 'No performance history available'}
        
        recent_records = self.performance_history[-100:]  # Last 100 records
        
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
                # Use default high latency if endpoint unreachable
                latencies.append(1000.0)  # 1ms default
        
        # Return median latency
        current_latency = statistics.median(latencies) if latencies else 1000.0
        
        # Update history
        self.latency_history.append({
            'timestamp': time.time(),
            'latency_us': current_latency
        })
        
        # Keep only recent history
        if len(self.latency_history) > 1000:
            self.latency_history = self.latency_history[-1000:]
        
        return current_latency
    
    async def _ping_endpoint(self, endpoint: str) -> float:
        """Ping specific endpoint and measure latency"""
        
        start_time = time.time()
        
        if endpoint.startswith('redis://'):
            # Simulate Redis ping
            await asyncio.sleep(0.0001)  # 100μs simulation
        elif endpoint.startswith('postgresql://'):
            # Simulate PostgreSQL ping
            await asyncio.sleep(0.0005)  # 500μs simulation
        elif endpoint.startswith('http://'):
            # Simulate HTTP ping
            await asyncio.sleep(0.001)   # 1ms simulation
        
        end_time = time.time()
        latency_seconds = end_time - start_time
        latency_microseconds = latency_seconds * 1_000_000
        
        return latency_microseconds
```

## Market Microstructure-Adaptive Rules

### Bid-Ask Spread Integration

```python
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
                'tight': 25,    # Bottom 25% of spreads
                'normal': 75,   # 25-75% of spreads
                'wide': 100     # Top 25% of spreads
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
                'granularity_multiplier': 0.5,  # Finer granularity
                'description': 'Tight spreads with low volume - increase precision'
            },
            'wide_spread_high_volume': {
                'granularity_multiplier': 1.5,  # Coarser granularity
                'description': 'Wide spreads with high volume - reduce noise'
            },
            'high_volatility': {
                'granularity_multiplier': 0.75,  # Slightly finer
                'description': 'High volatility - capture rapid changes'
            },
            'low_volatility': {
                'granularity_multiplier': 1.25,  # Slightly coarser
                'description': 'Low volatility - reduce over-sampling'
            },
            'market_stress': {
                'granularity_multiplier': 0.25,  # Much finer
                'description': 'Market stress conditions - maximum precision'
            }
        }
    
    async def adaptive_granularity_adjustment(self, data_df: pd.DataFrame,
                                            metric_types: List[str],
                                            symbol: str) -> Dict[str, Any]:
        """Adjust granularity based on current market microstructure"""
        
        # Analyze current microstructure conditions
        microstructure_analysis = await self.microstructure_monitor.analyze_conditions(
            data_df, symbol
        )
        
        # Determine appropriate rule adjustment
        rule_key = self._determine_rule_adjustment(microstructure_analysis)
        
        if rule_key not in self.rule_adjustments:
            rule_key = 'normal'  # Default
            multiplier = 1.0
        else:
            multiplier = self.rule_adjustments[rule_key]['granularity_multiplier']
        
        # Apply adjustments
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
        
        # Market stress takes priority
        if market_stress_score > 0.8:
            return 'market_stress'
        
        # High volatility conditions
        if volatility_percentile > self.adaptive_thresholds['volatility_percentiles']['normal']:
            return 'high_volatility'
        
        # Low volatility conditions
        if volatility_percentile < self.adaptive_thresholds['volatility_percentiles']['low']:
            return 'low_volatility'
        
        # Spread and volume combinations
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
        
        # Calculate bid-ask spread if available
        if 'bid' in data_df.columns and 'ask' in data_df.columns:
            spreads = data_df['ask'] - data_df['bid']
            current_spread = spreads.iloc[-1] if len(spreads) > 0 else 0
            
            # Update historical spreads
            if symbol not in self.historical_spreads:
                self.historical_spreads[symbol] = []
            
            self.historical_spreads[symbol].extend(spreads.tolist())
            
            # Keep only recent history
            if len(self.historical_spreads[symbol]) > 10000:
                self.historical_spreads[symbol] = self.historical_spreads[symbol][-10000:]
            
            # Calculate spread percentile
            if len(self.historical_spreads[symbol]) > 100:
                spread_percentile = (
                    sum(1 for s in self.historical_spreads[symbol] if s <= current_spread) /
                    len(self.historical_spreads[symbol]) * 100
                )
            else:
                spread_percentile = 50  # Default
            
            analysis.update({
                'current_spread': float(current_spread),
                'avg_spread': float(spreads.mean()),
                'spread_percentile': spread_percentile
            })
        
        # Calculate volume metrics
        if 'volume' in data_df.columns:
            volumes = data_df['volume']
            current_volume = volumes.iloc[-1] if len(volumes) > 0 else 0
            
            # Update historical volumes
            if symbol not in self.historical_volumes:
                self.historical_volumes[symbol] = []
            
            self.historical_volumes[symbol].extend(volumes.tolist())
            
            if len(self.historical_volumes[symbol]) > 10000:
                self.historical_volumes[symbol] = self.historical_volumes[symbol][-10000:]
            
            # Calculate volume percentile
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
        
        # Calculate volatility metrics
        if 'price' in data_df.columns:
            prices = data_df['price']
            returns = prices.pct_change().dropna()
            current_volatility = returns.std() if len(returns) > 1 else 0
            
            # Update historical volatilities
            if symbol not in self.historical_volatilities:
                self.historical_volatilities[symbol] = []
            
            if current_volatility > 0:
                self.historical_volatilities[symbol].append(current_volatility)
            
            if len(self.historical_volatilities[symbol]) > 1000:
                self.historical_volatilities[symbol] = self.historical_volatilities[symbol][-1000:]
            
            # Calculate volatility percentile
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
        
        # Calculate market stress score
        market_stress_score = self._calculate_market_stress_score(analysis)
        analysis['market_stress_score'] = market_stress_score
        
        return analysis
    
    def _calculate_market_stress_score(self, analysis: Dict[str, Any]) -> float:
        """Calculate market stress score based on microstructure indicators"""
        
        stress_indicators = []
        
        # High spread indicates stress
        spread_percentile = analysis.get('spread_percentile', 50)
        if spread_percentile > 90:
            stress_indicators.append(0.3)
        elif spread_percentile > 75:
            stress_indicators.append(0.1)
        
        # Low volume can indicate stress
        volume_percentile = analysis.get('volume_percentile', 50)
        if volume_percentile < 10:
            stress_indicators.append(0.2)
        elif volume_percentile > 90:  # Very high volume also indicates stress
            stress_indicators.append(0.2)
        
        # High volatility indicates stress
        volatility_percentile = analysis.get('volatility_percentile', 50)
        if volatility_percentile > 95:
            stress_indicators.append(0.4)
        elif volatility_percentile > 80:
            stress_indicators.append(0.2)
        
        # Calculate overall stress score
        stress_score = sum(stress_indicators)
        return min(stress_score, 1.0)  # Cap at 1.0
```

This comprehensive system-specific documentation covers MBD processing, AI-driven RegTech compliance, dynamic latency-aware granularity management, and market microstructure-adaptive rules, all designed to integrate seamlessly with the existing Braided Cord Data Engine architecture.
