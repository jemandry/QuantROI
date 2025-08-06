"""
Granularity Limiter (Resolution Guard) for Enhanced RIA Platform

This module implements a granularity limiter system that prevents over-magnification
of financial metrics by enforcing minimum time intervals for different metric types.
Designed for integration with existing Redis cache and Neo4j storage systems.

Based on quantitative finance principles to ensure metrics remain actionable
while maintaining regulatory compliance and reducing computational overhead.

License: Commercial use allowed
"""

import pandas as pd
import redis
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum
import json
import numpy as np
from neo4j import GraphDatabase

try:
    from ..neo4j_integration.cache import EncryptedCacheManager
except ImportError:
    EncryptedCacheManager = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MetricCategory(Enum):
    """Categories of financial metrics with different granularity requirements"""
    FUNDAMENTAL = "fundamental"  # PE ratio, EPS, ROE - quarterly/annual data
    TECHNICAL = "technical"      # Moving averages, RSI - daily/hourly data
    RISK = "risk"               # Beta, volatility, VaR - daily data
    PERFORMANCE = "performance"  # Sharpe ratio, alpha - weekly/monthly data
    MARKET = "market"           # Price, volume - real-time/minute data
    CAUSAL = "causal"           # Causal relationships - event-driven


@dataclass
class GranularityRule:
    """Rule defining minimum granularity for a metric"""
    metric_name: str
    min_interval: timedelta
    category: MetricCategory
    aggregation_method: str = "mean"  # mean, sum, last, vwap
    confidence_threshold: float = 0.95
    description: str = ""
    regulatory_basis: str = ""


@dataclass
class MetricRequest:
    """Request for metric data with granularity validation"""
    metric_name: str
    data_resolution: timedelta
    start_time: datetime
    end_time: datetime
    asset_id: Optional[str] = None
    override_requested: bool = False
    justification: str = ""


@dataclass
class GranularityValidationResult:
    """Result of granularity validation"""
    is_valid: bool
    enforced_resolution: timedelta
    aggregation_applied: bool
    audit_hash: str
    warning_message: Optional[str] = None
    performance_impact: Dict[str, Any] = None


class GranularityLimiter:
    """
    Granularity Limiter (Resolution Guard) for financial metrics
    
    Prevents over-magnification by enforcing minimum time intervals
    for different metric types based on quantitative finance principles.
    """
    
    def __init__(self, cache_manager: Optional[EncryptedCacheManager] = None,
                 neo4j_driver: Optional[GraphDatabase.driver] = None,
                 timescale_connection: Optional[Any] = None):
        """Initialize granularity limiter with storage integrations"""
        self.cache_manager = cache_manager
        self.neo4j_driver = neo4j_driver
        self.timescale_connection = timescale_connection
        
        self.rules = self._initialize_default_rules()
        
        self.performance_metrics = {
            "queries_processed": 0,
            "aggregations_applied": 0,
            "overrides_granted": 0,
            "cache_hits": 0,
            "avg_processing_time": 0.0,
            "data_reliability_alerts": 0,
            "async_operations": 0
        }
        
        logger.info("✅ Enhanced Granularity Limiter initialized with production-ready features")
        
        if self.cache_manager:
            if self.cache_manager:
                try:
                    self._cache_rules_in_redis()
                except Exception as e:
                    logger.error(f"Failed to cache rules in Redis: {e}")
    
    def _initialize_default_rules(self) -> Dict[str, GranularityRule]:
        """Initialize default granularity rules for financial metrics"""
        
        rules = {
            'pe_ratio': GranularityRule(
                metric_name='pe_ratio',
                min_interval=timedelta(days=1),
                category=MetricCategory.FUNDAMENTAL,
                aggregation_method='last',
                description='Price-to-Earnings ratio - daily minimum prevents HFT noise',
                regulatory_basis='SEC Form 10-K quarterly reporting'
            ),
            'eps': GranularityRule(
                metric_name='eps',
                min_interval=timedelta(days=90),
                category=MetricCategory.FUNDAMENTAL,
                aggregation_method='last',
                description='Earnings Per Share - quarterly reporting cycle',
                regulatory_basis='GAAP quarterly earnings requirements'
            ),
            'roe': GranularityRule(
                metric_name='roe',
                min_interval=timedelta(days=365),
                category=MetricCategory.FUNDAMENTAL,
                aggregation_method='last',
                description='Return on Equity - annual calculation standard',
                regulatory_basis='Annual financial statement requirements'
            ),
            'debt_to_equity': GranularityRule(
                metric_name='debt_to_equity',
                min_interval=timedelta(days=90),
                category=MetricCategory.FUNDAMENTAL,
                aggregation_method='last',
                description='Debt-to-Equity ratio - quarterly balance sheet data'
            ),
            
            'moving_average': GranularityRule(
                metric_name='moving_average',
                min_interval=timedelta(hours=1),
                category=MetricCategory.TECHNICAL,
                aggregation_method='mean',
                description='Moving averages - hourly minimum for trend analysis',
                regulatory_basis='Market structure noise reduction'
            ),
            'rsi': GranularityRule(
                metric_name='rsi',
                min_interval=timedelta(hours=1),
                category=MetricCategory.TECHNICAL,
                aggregation_method='last',
                description='Relative Strength Index - hourly for momentum analysis'
            ),
            'macd': GranularityRule(
                metric_name='macd',
                min_interval=timedelta(hours=1),
                category=MetricCategory.TECHNICAL,
                aggregation_method='last',
                description='MACD indicator - hourly for signal generation'
            ),
            
            'beta': GranularityRule(
                metric_name='beta',
                min_interval=timedelta(days=1),
                category=MetricCategory.RISK,
                aggregation_method='mean',
                description='Market beta - daily minimum for systematic risk measurement',
                regulatory_basis='CAPM model requirements'
            ),
            'volatility': GranularityRule(
                metric_name='volatility',
                min_interval=timedelta(days=1),
                category=MetricCategory.RISK,
                aggregation_method='mean',
                description='Historical volatility - daily for options pricing'
            ),
            'var': GranularityRule(
                metric_name='var',
                min_interval=timedelta(days=1),
                category=MetricCategory.RISK,
                aggregation_method='last',
                description='Value at Risk - daily calculation standard'
            ),
            
            'sharpe_ratio': GranularityRule(
                metric_name='sharpe_ratio',
                min_interval=timedelta(days=7),
                category=MetricCategory.PERFORMANCE,
                aggregation_method='last',
                description='Sharpe ratio - weekly minimum for risk-adjusted returns',
                regulatory_basis='Portfolio performance reporting standards'
            ),
            'alpha': GranularityRule(
                metric_name='alpha',
                min_interval=timedelta(days=30),
                category=MetricCategory.PERFORMANCE,
                aggregation_method='last',
                description='Jensen\'s alpha - monthly for excess return measurement'
            ),
            'information_ratio': GranularityRule(
                metric_name='information_ratio',
                min_interval=timedelta(days=30),
                category=MetricCategory.PERFORMANCE,
                aggregation_method='last',
                description='Information ratio - monthly for active management assessment'
            ),
            
            'correlation': GranularityRule(
                metric_name='correlation',
                min_interval=timedelta(days=1),
                category=MetricCategory.MARKET,
                aggregation_method='mean',
                description='Asset correlation - daily for portfolio diversification'
            ),
            
            'causal_impact': GranularityRule(
                metric_name='causal_impact',
                min_interval=timedelta(hours=1),
                category=MetricCategory.CAUSAL,
                aggregation_method='last',
                description='Causal impact measurement - hourly for event analysis'
            ),
            'granger_causality': GranularityRule(
                metric_name='granger_causality',
                min_interval=timedelta(days=1),
                category=MetricCategory.CAUSAL,
                aggregation_method='last',
                description='Granger causality test - daily for temporal relationships'
            )
        }
        
        return rules
    
    def validate_index(self, data_df: pd.DataFrame, default_resolution: timedelta = timedelta(days=1)) -> pd.DataFrame:
        """Validate DataFrame index and infer resolution if non-time-based."""
        if not isinstance(data_df.index, pd.DatetimeIndex):
            audit_hash = hashlib.sha256(str(data_df).encode()).hexdigest()
            logger.warning(f"Non-time-indexed data detected. Assigning default resolution: {default_resolution}. Audit hash: {audit_hash}")
            data_df.index = pd.date_range(start=datetime.now(), periods=len(data_df), freq=default_resolution)
            data_df.index.freq = default_resolution
            
            if self.neo4j_driver:
                self._store_audit_event("index_validation", {
                    "audit_hash": audit_hash,
                    "default_resolution": str(default_resolution),
                    "data_points": len(data_df)
                })
        return data_df
    
    async def _cache_rules_in_redis(self):
        """Cache granularity rules in Redis for <1μs lookups"""
        if not self.cache_manager:
            return
            
        try:
            for metric, rule in self.rules.items():
                cache_key = f"granularity_rule:{metric}"
                rule_data = {
                    "min_interval_seconds": rule.min_interval.total_seconds(),
                    "category": rule.category.value,
                    "aggregation_method": rule.aggregation_method,
                    "confidence_threshold": rule.confidence_threshold
                }
                
                self.cache_manager.cache_query(
                    "granularity_rules", 
                    {"metric": metric},
                    rule_data,
                    ttl=3600
                )
            logger.info("✅ Granularity rules cached in Redis for optimized lookup")
        except Exception as e:
            logger.error(f"Failed to cache rules in Redis: {e}")

    def get_cached_rule(self, metric_name: str) -> Optional[GranularityRule]:
        """Get cached granularity rule with <1μs lookup time"""
        if not self.cache_manager:
            return self.rules.get(metric_name)
            
        try:
            cached_data = self.cache_manager.get_cached_query(
                "granularity_rules",
                {"metric": metric_name}
            )
            
            if cached_data:
                self.performance_metrics["cache_hits"] += 1
                return GranularityRule(
                    metric_name=metric_name,
                    min_interval=timedelta(seconds=cached_data["min_interval_seconds"]),
                    category=MetricCategory(cached_data["category"]),
                    aggregation_method=cached_data["aggregation_method"],
                    confidence_threshold=cached_data["confidence_threshold"]
                )
            
            return self.rules.get(metric_name)
        except Exception as e:
            logger.error(f"Failed to get cached rule: {e}")
            return self.rules.get(metric_name)
    
    async def adjust_granularity_dynamically(self, metric_name: str, market_conditions: Dict[str, Any]) -> timedelta:
        """Dynamically adjust granularity based on AI-driven market analysis"""
        base_rule = self.get_cached_rule(metric_name)
        if not base_rule:
            return timedelta(days=1)
            
        base_interval = base_rule.min_interval
        
        volatility_index = market_conditions.get('volatility_index', 0)
        if volatility_index > 30:
            adjusted_interval = timedelta(seconds=base_interval.total_seconds() / 2)
            audit_hash = hashlib.sha256(f"{metric_name}:{adjusted_interval}".encode()).hexdigest()
            logger.info(f"Dynamic granularity adjustment for {metric_name}: {adjusted_interval}. Audit hash: {audit_hash}")
            
            if self.timescale_connection:
                await self._log_to_timescale("granularity_adjustment", {
                    "metric_name": metric_name,
                    "original_interval": base_interval.total_seconds(),
                    "adjusted_interval": adjusted_interval.total_seconds(),
                    "volatility_index": volatility_index,
                    "audit_hash": audit_hash
                })
            
            return adjusted_interval
            
        return base_interval
    
    def _store_audit_event(self, event_type: str, event_data: Dict[str, Any]):
        """Store audit event in Neo4j"""
        if not self.neo4j_driver:
            return
            
        try:
            query = """
            CREATE (e:AuditEvent {
                event_type: $event_type,
                timestamp: datetime(),
                data: $event_data,
                audit_hash: $audit_hash
            })
            """
            
            with self.neo4j_driver.session() as session:
                session.run(query,
                    event_type=event_type,
                    event_data=json.dumps(event_data),
                    audit_hash=event_data.get("audit_hash", "")
                )
        except Exception as e:
            logger.error(f"Failed to store audit event: {e}")
    
    async def _log_to_timescale(self, event_type: str, event_data: Dict[str, Any]):
        """Log event to TimescaleDB for audit trail"""
        if not self.timescale_connection:
            return
            
        try:
            await self.timescale_connection.log_audit_event(event_type, event_data)
        except Exception as e:
            logger.error(f"Failed to log to TimescaleDB: {e}")
    
    def validate_granularity(self, request: MetricRequest) -> GranularityValidationResult:
        """
        Validate and enforce granularity limits for metric requests
        
        Args:
            request: MetricRequest with metric details and requested resolution
            
        Returns:
            GranularityValidationResult with validation outcome and enforcement details
        """
        start_time = datetime.now()
        self.performance_metrics["queries_processed"] += 1
        
        try:
            if request.metric_name not in self.rules:
                logger.warning(f"No granularity rule found for metric: {request.metric_name}")
                return GranularityValidationResult(
                    is_valid=True,
                    enforced_resolution=request.data_resolution,
                    aggregation_applied=False,
                    audit_hash=self._generate_audit_hash(request, "no_rule"),
                    warning_message=f"No granularity rule defined for {request.metric_name}"
                )
            
            rule = self.rules[request.metric_name]
            
            if request.data_resolution >= rule.min_interval:
                return GranularityValidationResult(
                    is_valid=True,
                    enforced_resolution=request.data_resolution,
                    aggregation_applied=False,
                    audit_hash=self._generate_audit_hash(request, "approved"),
                    performance_impact=self._calculate_performance_impact(request, rule)
                )
            
            if request.override_requested:
                if self._validate_override_justification(request, rule):
                    self.performance_metrics["overrides_granted"] += 1
                    logger.info(f"Override granted for {request.metric_name}: {request.justification}")
                    return GranularityValidationResult(
                        is_valid=True,
                        enforced_resolution=request.data_resolution,
                        aggregation_applied=False,
                        audit_hash=self._generate_audit_hash(request, "override_granted"),
                        warning_message=f"Override granted: {request.justification}"
                    )
                else:
                    logger.warning(f"Override denied for {request.metric_name}: insufficient justification")
            
            self.performance_metrics["aggregations_applied"] += 1
            
            return GranularityValidationResult(
                is_valid=False,
                enforced_resolution=rule.min_interval,
                aggregation_applied=True,
                audit_hash=self._generate_audit_hash(request, "aggregated"),
                warning_message=f"Resolution too fine for {request.metric_name}. "
                              f"Minimum: {rule.min_interval}, Requested: {request.data_resolution}. "
                              f"Data will be aggregated using {rule.aggregation_method}.",
                performance_impact=self._calculate_performance_impact(request, rule)
            )
            
        finally:
            processing_time = (datetime.now() - start_time).total_seconds()
            self.performance_metrics["avg_processing_time"] = (
                (self.performance_metrics["avg_processing_time"] * 
                 (self.performance_metrics["queries_processed"] - 1) + processing_time) /
                self.performance_metrics["queries_processed"]
            )
    
    def aggregate_data_enhanced(self, data: pd.DataFrame, rule: GranularityRule, 
                               target_resolution: timedelta, aggregation_type: str = "roll_up") -> pd.DataFrame:
        """Enhanced aggregation with roll-up/drill-down support and metric-specific logic"""
        try:
            if not isinstance(data.index, pd.DatetimeIndex):
                data = self.validate_index(data)
            
            data = data.ffill()
            
            freq = self._timedelta_to_pandas_freq(target_resolution)
            
            if rule.metric_name == 'moving_average':
                span_hours = target_resolution.total_seconds() / 3600
                aggregated = data.ewm(span=span_hours).mean()
            elif rule.metric_name == 'volatility':
                window_size = max(1, int(target_resolution.total_seconds() / 3600))
                aggregated = data.rolling(window=window_size).std()
            elif rule.metric_name in ['pe_ratio', 'eps', 'roe', 'current_ratio', 'debt_to_equity', 'gross_profit_margin']:
                aggregated = data.resample(freq).last()
            elif rule.aggregation_method == 'vwap' and 'volume' in data.columns and 'price' in data.columns:
                aggregated = data.resample(freq).apply(
                    lambda x: (x['price'] * x['volume']).sum() / x['volume'].sum()
                    if x['volume'].sum() > 0 else x['price'].mean()
                )
            else:
                if rule.aggregation_method == 'mean':
                    aggregated = data.resample(freq).mean()
                elif rule.aggregation_method == 'sum':
                    aggregated = data.resample(freq).sum()
                elif rule.aggregation_method == 'last':
                    aggregated = data.resample(freq).last()
                else:
                    aggregated = data.resample(freq).mean()
            
            if aggregation_type == "roll_up":
                aggregated = aggregated.dropna()
            elif aggregation_type == "drill_down":
                aggregated['drill_down_flag'] = True
            
            missing_ratio = aggregated.isna().sum().sum() / (len(aggregated) * len(aggregated.columns))
            if missing_ratio > 0.1:
                self.performance_metrics["data_reliability_alerts"] += 1
                logger.warning(f"High missing data ratio ({missing_ratio:.2%}) in aggregated {rule.metric_name}")
            
            logger.info(f"Enhanced aggregation: {len(data)} → {len(aggregated)} records using {rule.aggregation_method}")
            return aggregated
            
        except Exception as e:
            logger.error(f"Enhanced aggregation failed: {e}")
            return data
    
    def aggregate_data(self, data: pd.DataFrame, rule: GranularityRule, 
                      target_resolution: timedelta) -> pd.DataFrame:
        """Legacy method for backward compatibility"""
        return self.aggregate_data_enhanced(data, rule, target_resolution)
    
    def _timedelta_to_pandas_freq(self, td: timedelta) -> str:
        """Convert timedelta to pandas frequency string"""
        total_seconds = int(td.total_seconds())
        
        if total_seconds >= 31536000:  # 365 days
            return f"{total_seconds // 31536000}Y"
        elif total_seconds >= 2592000:  # 30 days
            return f"{total_seconds // 2592000}M"
        elif total_seconds >= 86400:  # 1 day
            return f"{total_seconds // 86400}D"
        elif total_seconds >= 3600:  # 1 hour
            return f"{total_seconds // 3600}H"
        elif total_seconds >= 60:  # 1 minute
            return f"{total_seconds // 60}T"
        else:
            return f"{total_seconds}S"
    
    def _validate_override_justification(self, request: MetricRequest, 
                                       rule: GranularityRule) -> bool:
        """Validate if override justification is sufficient"""
        
        valid_justifications = [
            'hft_research', 'academic_study', 'regulatory_requirement',
            'risk_management', 'black_swan_analysis', 'microstructure_research',
            'algorithm_development', 'compliance_testing'
        ]
        
        justification_lower = request.justification.lower()
        
        has_valid_justification = any(
            keyword in justification_lower for keyword in valid_justifications
        )
        
        if rule.category in [MetricCategory.FUNDAMENTAL, MetricCategory.PERFORMANCE]:
            return has_valid_justification and len(request.justification) > 50
        
        return has_valid_justification
    
    def _generate_audit_hash(self, request: MetricRequest, action: str) -> str:
        """Generate audit hash for compliance tracking"""
        audit_data = {
            "metric_name": request.metric_name,
            "requested_resolution": str(request.data_resolution),
            "start_time": request.start_time.isoformat(),
            "end_time": request.end_time.isoformat(),
            "asset_id": request.asset_id,
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "override_requested": request.override_requested,
            "justification": request.justification
        }
        
        audit_json = json.dumps(audit_data, sort_keys=True)
        return hashlib.sha256(audit_json.encode()).hexdigest()
    
    def _calculate_performance_impact(self, request: MetricRequest, 
                                    rule: GranularityRule) -> Dict[str, Any]:
        """Calculate performance impact of granularity enforcement"""
        
        requested_seconds = request.data_resolution.total_seconds()
        enforced_seconds = rule.min_interval.total_seconds()
        reduction_ratio = enforced_seconds / requested_seconds if requested_seconds > 0 else 1
        
        time_span = (request.end_time - request.start_time).total_seconds()
        original_points = int(time_span / requested_seconds) if requested_seconds > 0 else 0
        enforced_points = int(time_span / enforced_seconds) if enforced_seconds > 0 else 0
        
        return {
            "data_reduction_ratio": reduction_ratio,
            "original_data_points": original_points,
            "enforced_data_points": enforced_points,
            "computational_savings_pct": (1 - (enforced_points / max(original_points, 1))) * 100,
            "storage_savings_pct": (1 - (1 / max(reduction_ratio, 1))) * 100
        }
    
    def cache_granularity_result(self, request: MetricRequest, 
                                result: GranularityValidationResult, 
                                ttl: int = 3600) -> bool:
        """Cache granularity validation results for performance"""
        
        if not self.cache_manager:
            return False
        
        try:
            cache_key = f"granularity:{request.metric_name}:{request.data_resolution}"
            cache_data = {
                "result": {
                    "is_valid": result.is_valid,
                    "enforced_resolution": str(result.enforced_resolution),
                    "aggregation_applied": result.aggregation_applied,
                    "audit_hash": result.audit_hash,
                    "warning_message": result.warning_message,
                    "performance_impact": result.performance_impact
                },
                "cached_at": datetime.now().isoformat()
            }
            
            success = self.cache_manager.cache_query(
                "granularity_validation", 
                {"metric": request.metric_name, "resolution": str(request.data_resolution)},
                cache_data,
                ttl
            )
            
            if success:
                self.performance_metrics["cache_hits"] += 1
                logger.debug(f"Cached granularity result for {request.metric_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to cache granularity result: {e}")
            return False
    
    def get_cached_granularity_result(self, request: MetricRequest) -> Optional[GranularityValidationResult]:
        """Retrieve cached granularity validation results"""
        
        if not self.cache_manager:
            return None
        
        try:
            cached_data = self.cache_manager.get_cached_query(
                "granularity_validation",
                {"metric": request.metric_name, "resolution": str(request.data_resolution)}
            )
            
            if cached_data and "result" in cached_data:
                result_data = cached_data["result"]
                return GranularityValidationResult(
                    is_valid=result_data["is_valid"],
                    enforced_resolution=pd.Timedelta(result_data["enforced_resolution"]),
                    aggregation_applied=result_data["aggregation_applied"],
                    audit_hash=result_data["audit_hash"],
                    warning_message=result_data.get("warning_message"),
                    performance_impact=result_data.get("performance_impact")
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve cached granularity result: {e}")
            return None
    
    def store_granularity_rule_in_neo4j(self, rule: GranularityRule) -> bool:
        """Store granularity rules in Neo4j for persistence"""
        
        if not self.neo4j_driver:
            return False
        
        try:
            query = """
            MERGE (r:GranularityRule {metric_name: $metric_name})
            SET r.min_interval_seconds = $min_interval_seconds,
                r.category = $category,
                r.aggregation_method = $aggregation_method,
                r.confidence_threshold = $confidence_threshold,
                r.description = $description,
                r.regulatory_basis = $regulatory_basis,
                r.updated_at = datetime()
            RETURN r
            """
            
            with self.neo4j_driver.session() as session:
                result = session.run(query,
                    metric_name=rule.metric_name,
                    min_interval_seconds=int(rule.min_interval.total_seconds()),
                    category=rule.category.value,
                    aggregation_method=rule.aggregation_method,
                    confidence_threshold=rule.confidence_threshold,
                    description=rule.description,
                    regulatory_basis=rule.regulatory_basis
                )
                
                record = result.single()
                if record:
                    logger.info(f"Stored granularity rule for {rule.metric_name} in Neo4j")
                    return True
                
            return False
            
        except Exception as e:
            logger.error(f"Failed to store granularity rule in Neo4j: {e}")
            return False
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for monitoring"""
        return {
            **self.performance_metrics,
            "rules_count": len(self.rules),
            "cache_hit_rate": (
                self.performance_metrics["cache_hits"] / 
                max(self.performance_metrics["queries_processed"], 1)
            ) * 100
        }
    
    def add_custom_rule(self, rule: GranularityRule) -> bool:
        """Add custom granularity rule"""
        try:
            self.rules[rule.metric_name] = rule
            
            if self.neo4j_driver:
                self.store_granularity_rule_in_neo4j(rule)
            
            logger.info(f"Added custom granularity rule for {rule.metric_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add custom rule: {e}")
            return False
    
    def get_rule_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get summary of all granularity rules"""
        summary = {}
        
        for metric_name, rule in self.rules.items():
            summary[metric_name] = {
                "min_interval": str(rule.min_interval),
                "category": rule.category.value,
                "aggregation_method": rule.aggregation_method,
                "description": rule.description,
                "regulatory_basis": rule.regulatory_basis
            }
        
        return summary
    
    async def validate_granularity_async(self, request: MetricRequest, 
                                        market_conditions: Optional[Dict[str, Any]] = None) -> GranularityValidationResult:
        """Async granularity validation with <50μs overhead for hot path"""
        start_time = datetime.now()
        self.performance_metrics["queries_processed"] += 1
        
        try:
            rule = self.get_cached_rule(request.metric_name)
            if not rule:
                logger.warning(f"No granularity rule found for metric: {request.metric_name}")
                return GranularityValidationResult(
                    is_valid=True,
                    enforced_resolution=request.data_resolution,
                    aggregation_applied=False,
                    audit_hash=self._generate_audit_hash(request, "no_rule"),
                    warning_message=f"No granularity rule defined for {request.metric_name}"
                )
            
            if market_conditions:
                adjusted_interval = await self.adjust_granularity_dynamically(
                    request.metric_name, market_conditions
                )
                rule.min_interval = adjusted_interval
            
            if request.data_resolution >= rule.min_interval:
                result = GranularityValidationResult(
                    is_valid=True,
                    enforced_resolution=request.data_resolution,
                    aggregation_applied=False,
                    audit_hash=self._generate_audit_hash(request, "approved"),
                    performance_impact=self._calculate_performance_impact(request, rule)
                )
            else:
                result = GranularityValidationResult(
                    is_valid=False,
                    enforced_resolution=rule.min_interval,
                    aggregation_applied=True,
                    audit_hash=self._generate_audit_hash(request, "aggregated"),
                    warning_message=f"Resolution too fine for {request.metric_name}. Aggregating to {rule.min_interval}.",
                    performance_impact=self._calculate_performance_impact(request, rule)
                )
            
            if self.timescale_connection:
                try:
                    import asyncio
                    asyncio.create_task(self._log_audit_async(request, result))
                except Exception as e:
                    logger.error(f"Failed to log audit async: {e}")
            
            return result
            
        finally:
            processing_time = (datetime.now() - start_time).total_seconds() * 1_000_000
            self.performance_metrics["avg_processing_time"] = (
                (self.performance_metrics["avg_processing_time"] * 
                 (self.performance_metrics["queries_processed"] - 1) + processing_time) /
                self.performance_metrics["queries_processed"]
            )
            
            if processing_time > 50:
                logger.warning(f"Granularity validation exceeded 50μs target: {processing_time:.1f}μs")

    async def _log_audit_async(self, request: MetricRequest, result: GranularityValidationResult):
        """Async audit logging to avoid blocking hot path"""
        try:
            self.performance_metrics["async_operations"] += 1
            
            if self.timescale_connection:
                await self.timescale_connection.log_audit_event(
                    "granularity_validation",
                    {
                        "metric_name": request.metric_name,
                        "requested_resolution": str(request.data_resolution),
                        "enforced_resolution": str(result.enforced_resolution),
                        "aggregation_applied": result.aggregation_applied,
                        "audit_hash": result.audit_hash,
                        "timestamp": datetime.now().isoformat()
                    }
                )
        except Exception as e:
            logger.error(f"Async audit logging failed: {e}")


def create_sample_data(metric_name: str, resolution: timedelta, 
                      duration_days: int = 30) -> pd.DataFrame:
    """Create sample financial data for testing"""
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=duration_days)
    
    freq = resolution.total_seconds()
    timestamps = pd.date_range(start=start_time, end=end_time, 
                              freq=f"{int(freq)}S")
    
    np.random.seed(42)  # For reproducible results
    
    if metric_name in ['pe_ratio']:
        base_value = 20
        values = base_value + np.random.normal(0, 2, len(timestamps))
        values = np.maximum(values, 5)  # Minimum PE of 5
        
    elif metric_name in ['moving_average', 'price']:
        base_price = 100
        returns = np.random.normal(0.0001, 0.02, len(timestamps))
        values = base_price * np.exp(np.cumsum(returns))
        
    elif metric_name in ['volatility']:
        base_vol = 0.2
        values = base_vol + np.random.normal(0, 0.05, len(timestamps))
        values = np.maximum(values, 0.01)  # Minimum volatility
        
    elif metric_name in ['beta']:
        base_beta = 1.0
        values = base_beta + np.random.normal(0, 0.3, len(timestamps))
        
    else:
        values = np.random.normal(0, 1, len(timestamps))
    
    return pd.DataFrame({
        'value': values,
        'volume': np.random.randint(1000, 10000, len(timestamps))
    }, index=timestamps)


class EnhancedDataExtractionRequest:
    """Enhanced data extraction request with granularity validation"""
    
    def __init__(self, granularity_limiter: GranularityLimiter):
        self.granularity_limiter = granularity_limiter
    
    def extract_metric_data(self, metric_name: str, data_resolution: timedelta,
                           start_time: datetime, end_time: datetime,
                           asset_id: Optional[str] = None,
                           override_requested: bool = False,
                           justification: str = "") -> Dict[str, Any]:
        """
        Extract metric data with granularity validation and enforcement
        
        Returns:
            Dict containing validated data, audit information, and performance metrics
        """
        
        request = MetricRequest(
            metric_name=metric_name,
            data_resolution=data_resolution,
            start_time=start_time,
            end_time=end_time,
            asset_id=asset_id,
            override_requested=override_requested,
            justification=justification
        )
        
        cached_result = self.granularity_limiter.get_cached_granularity_result(request)
        if cached_result:
            logger.info(f"Using cached granularity validation for {metric_name}")
            validation_result = cached_result
        else:
            validation_result = self.granularity_limiter.validate_granularity(request)
            
            self.granularity_limiter.cache_granularity_result(request, validation_result)
        
        raw_data = create_sample_data(metric_name, data_resolution, 
                                    duration_days=(end_time - start_time).days)
        
        if validation_result.aggregation_applied:
            rule = self.granularity_limiter.rules[metric_name]
            processed_data = self.granularity_limiter.aggregate_data(
                raw_data, rule, validation_result.enforced_resolution
            )
        else:
            processed_data = raw_data
        
        return {
            "data": processed_data,
            "validation_result": validation_result,
            "request": request,
            "audit_hash": validation_result.audit_hash,
            "performance_impact": validation_result.performance_impact,
            "data_points": len(processed_data),
            "processing_timestamp": datetime.now().isoformat()
        }
