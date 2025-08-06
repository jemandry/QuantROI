"""
Integration Layer for Granularity Limiter with Existing Storage Systems

This module provides integration utilities for connecting the granularity limiter
with existing Redis cache, Neo4j storage, and data extraction pipelines.

License: Commercial use allowed
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import pandas as pd

try:
    from ..neo4j_integration.cache import EncryptedCacheManager
    from ..neo4j_integration.nodes import NodeManager
    from .granularity_limiter import GranularityLimiter, MetricRequest, EnhancedDataExtractionRequest
except ImportError as e:
    logging.warning(f"Import warning in granularity integration: {e}")
    EncryptedCacheManager = None
    NodeManager = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class GranularityIntegratedStorageManager:
    """
    Integrated storage manager with granularity limiting capabilities
    
    Combines Redis caching, Neo4j storage, and granularity enforcement
    for comprehensive financial data management.
    """
    
    def __init__(self, redis_config: Optional[Dict] = None, 
                 neo4j_config: Optional[Dict] = None):
        """Initialize integrated storage manager"""
        
        if EncryptedCacheManager and redis_config:
            self.cache_manager = EncryptedCacheManager(**redis_config)
        else:
            self.cache_manager = None
            logger.warning("Redis cache manager not available")
        
        if NodeManager and neo4j_config:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                neo4j_config.get('uri', 'bolt://localhost:7687'),
                auth=(neo4j_config.get('user', 'neo4j'), 
                      neo4j_config.get('password', os.getenv('NEO4J_PASSWORD', 'neo4j')))
            )
            self.node_manager = NodeManager(driver)
            self.neo4j_driver = driver
        else:
            self.node_manager = None
            self.neo4j_driver = None
            logger.warning("Neo4j node manager not available")
        
        self.granularity_limiter = GranularityLimiter(
            cache_manager=self.cache_manager,
            neo4j_driver=self.neo4j_driver
        )
        
        self.data_extractor = EnhancedDataExtractionRequest(self.granularity_limiter)
        
        logger.info("✅ Granularity Integrated Storage Manager initialized")
    
    async def store_metric_with_granularity_check(self, metric_name: str, 
                                                 data: pd.DataFrame,
                                                 data_resolution: timedelta,
                                                 asset_id: Optional[str] = None,
                                                 metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Store metric data with granularity validation and enforcement
        
        Args:
            metric_name: Name of the financial metric
            data: DataFrame with timestamp index and metric values
            data_resolution: Time resolution of the input data
            asset_id: Optional asset identifier
            metadata: Additional metadata for storage
            
        Returns:
            Dict with storage results and granularity validation info
        """
        
        try:
            start_time = data.index.min().to_pydatetime()
            end_time = data.index.max().to_pydatetime()
            
            request = MetricRequest(
                metric_name=metric_name,
                data_resolution=data_resolution,
                start_time=start_time,
                end_time=end_time,
                asset_id=asset_id
            )
            
            validation_result = self.granularity_limiter.validate_granularity(request)
            
            if validation_result.aggregation_applied:
                rule = self.granularity_limiter.rules[metric_name]
                processed_data = self.granularity_limiter.aggregate_data(
                    data, rule, validation_result.enforced_resolution
                )
                logger.info(f"Applied granularity aggregation for {metric_name}")
            else:
                processed_data = data
            
            cache_success = False
            if self.cache_manager:
                cache_data = {
                    "metric_name": metric_name,
                    "data_points": len(processed_data),
                    "resolution": str(validation_result.enforced_resolution),
                    "asset_id": asset_id,
                    "validation_hash": validation_result.audit_hash,
                    "metadata": metadata or {}
                }
                
                cache_success = self.cache_manager.cache_query(
                    "granularity_metric",
                    {"metric": metric_name, "asset": asset_id or "default"},
                    cache_data,
                    ttl=7200  # 2 hours
                )
            
            neo4j_success = False
            if self.node_manager:
                try:
                    metric_data = {
                        "metric_name": metric_name,
                        "asset_id": asset_id or "default",
                        "data_points": len(processed_data),
                        "resolution_seconds": int(validation_result.enforced_resolution.total_seconds()),
                        "aggregation_applied": validation_result.aggregation_applied,
                        "audit_hash": validation_result.audit_hash,
                        "stored_at": datetime.now().isoformat()
                    }
                    
                    discovery_result = self.node_manager.create_discovery_node(
                        discovery_id=f"metric_{metric_name}_{asset_id}_{datetime.now().timestamp()}",
                        source="granularity_limiter",
                        title=f"Metric Storage: {metric_name}",
                        content=f"Stored {len(processed_data)} data points with {validation_result.enforced_resolution} resolution",
                        relevance_score=1.0,
                        confidence_rating=95,
                        causal_explanation=f"Granularity enforcement applied: {validation_result.aggregation_applied}",
                        category="metric_storage"
                    )
                    
                    neo4j_success = discovery_result is not None
                    
                except Exception as e:
                    logger.error(f"Failed to store metric metadata in Neo4j: {e}")
            
            return {
                "success": True,
                "processed_data_points": len(processed_data),
                "original_data_points": len(data),
                "validation_result": validation_result,
                "cache_stored": cache_success,
                "neo4j_stored": neo4j_success,
                "audit_hash": validation_result.audit_hash,
                "performance_impact": validation_result.performance_impact
            }
            
        except Exception as e:
            logger.error(f"Failed to store metric with granularity check: {e}")
            return {
                "success": False,
                "error": str(e),
                "processed_data_points": 0,
                "original_data_points": len(data) if data is not None else 0
            }
    
    async def retrieve_metric_with_granularity(self, metric_name: str,
                                             requested_resolution: timedelta,
                                             start_time: datetime,
                                             end_time: datetime,
                                             asset_id: Optional[str] = None,
                                             override_requested: bool = False,
                                             justification: str = "") -> Dict[str, Any]:
        """
        Retrieve metric data with granularity validation
        
        Args:
            metric_name: Name of the financial metric
            requested_resolution: Requested time resolution
            start_time: Start time for data retrieval
            end_time: End time for data retrieval
            asset_id: Optional asset identifier
            override_requested: Whether to request granularity override
            justification: Justification for override request
            
        Returns:
            Dict with retrieved data and granularity validation info
        """
        
        try:
            result = self.data_extractor.extract_metric_data(
                metric_name=metric_name,
                data_resolution=requested_resolution,
                start_time=start_time,
                end_time=end_time,
                asset_id=asset_id,
                override_requested=override_requested,
                justification=justification
            )
            
            cache_hit = False
            if self.cache_manager:
                cached_data = self.cache_manager.get_cached_query(
                    "granularity_metric",
                    {"metric": metric_name, "asset": asset_id or "default"}
                )
                if cached_data:
                    cache_hit = True
                    logger.info(f"Cache hit for metric {metric_name}")
            
            result["cache_hit"] = cache_hit
            result["retrieval_timestamp"] = datetime.now().isoformat()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to retrieve metric with granularity: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": None,
                "cache_hit": False
            }
    
    def get_granularity_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report for granularity system"""
        
        granularity_metrics = self.granularity_limiter.get_performance_metrics()
        
        cache_stats = {}
        if self.cache_manager:
            cache_stats = self.cache_manager.get_cache_stats()
        
        rule_summary = self.granularity_limiter.get_rule_summary()
        
        return {
            "granularity_performance": granularity_metrics,
            "cache_performance": cache_stats,
            "active_rules": rule_summary,
            "system_status": {
                "cache_available": self.cache_manager is not None,
                "neo4j_available": self.node_manager is not None,
                "granularity_limiter_active": True
            },
            "report_timestamp": datetime.now().isoformat()
        }
    
    async def run_granularity_compliance_check(self) -> Dict[str, Any]:
        """Run compliance check for granularity enforcement"""
        
        compliance_results = {
            "rules_validated": 0,
            "compliance_issues": [],
            "recommendations": [],
            "overall_status": "compliant"
        }
        
        try:
            for metric_name, rule in self.granularity_limiter.rules.items():
                compliance_results["rules_validated"] += 1
                
                if rule.category.value == "fundamental" and rule.min_interval < timedelta(days=1):
                    compliance_results["compliance_issues"].append(
                        f"Fundamental metric {metric_name} allows sub-daily resolution"
                    )
                
                if not rule.regulatory_basis:
                    compliance_results["recommendations"].append(
                        f"Add regulatory basis for {metric_name} rule"
                    )
            
            if compliance_results["compliance_issues"]:
                compliance_results["overall_status"] = "non_compliant"
            elif compliance_results["recommendations"]:
                compliance_results["overall_status"] = "compliant_with_recommendations"
            
            logger.info(f"Granularity compliance check completed: {compliance_results['overall_status']}")
            
        except Exception as e:
            logger.error(f"Failed to run compliance check: {e}")
            compliance_results["overall_status"] = "error"
            compliance_results["error"] = str(e)
        
        return compliance_results
    
    def close(self):
        """Close all connections"""
        if self.cache_manager:
            self.cache_manager.close()
        
        if self.neo4j_driver:
            self.neo4j_driver.close()
        
        logger.info("Granularity Integrated Storage Manager closed")


async def test_granularity_integration():
    """Test the granularity integration system"""
    
    logger.info("🧪 Testing Granularity Integration System")
    
    storage_manager = GranularityIntegratedStorageManager()
    
    try:
        logger.info("Test 1: Storing PE ratio data with 1-minute resolution")
        
        from .granularity_limiter import create_sample_data
        pe_data = create_sample_data("pe_ratio", timedelta(minutes=1), duration_days=7)
        
        store_result = await storage_manager.store_metric_with_granularity_check(
            metric_name="pe_ratio",
            data=pe_data,
            data_resolution=timedelta(minutes=1),
            asset_id="AAPL",
            metadata={"source": "test_data", "quality": "high"}
        )
        
        logger.info(f"Store result: {store_result['success']}, "
                   f"Aggregation applied: {store_result['validation_result'].aggregation_applied}")
        
        logger.info("Test 2: Retrieving data with override request")
        
        retrieve_result = await storage_manager.retrieve_metric_with_granularity(
            metric_name="pe_ratio",
            requested_resolution=timedelta(minutes=1),
            start_time=datetime.now() - timedelta(days=7),
            end_time=datetime.now(),
            asset_id="AAPL",
            override_requested=True,
            justification="hft_research for academic study on market microstructure"
        )
        
        logger.info(f"Retrieve result: Override granted: "
                   f"{not retrieve_result['validation_result'].aggregation_applied}")
        
        logger.info("Test 3: Generating performance report")
        
        performance_report = storage_manager.get_granularity_performance_report()
        logger.info(f"Performance report generated with "
                   f"{performance_report['granularity_performance']['queries_processed']} queries processed")
        
        logger.info("Test 4: Running compliance check")
        
        compliance_result = await storage_manager.run_granularity_compliance_check()
        logger.info(f"Compliance status: {compliance_result['overall_status']}")
        
        logger.info("✅ Granularity integration tests completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Granularity integration test failed: {e}")
        
    finally:
        storage_manager.close()


if __name__ == "__main__":
    asyncio.run(test_granularity_integration())
