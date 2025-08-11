import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import hashlib
import os
from collections import defaultdict

try:
    from .nanosecond_timing import get_ns_timestamp, ClockType
    NANOSECOND_TIMING_AVAILABLE = True
except ImportError:
    NANOSECOND_TIMING_AVAILABLE = False
    import time

from .comprehensive_audit_integration import ComprehensiveAuditIntegration

class StreamBasedAuditLogger:
    """Real-time stream-based audit logger with nanosecond precision"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.audit_integration = ComprehensiveAuditIntegration()
        try:
            from .zkp_audit_router import ZKPAuditRouter
            self.zkp_router = ZKPAuditRouter()
        except ImportError:
            self.logger.warning("ZKPAuditRouter not available, using basic audit integration")
            self.zkp_router = None
        self.event_buffer = []
        self.buffer_size = 1000
        self.processing_stats = {
            'events_processed': 0,
            'events_per_second': 0,
            'last_stats_update': datetime.now()
        }
    
    async def log_event(self, event: Dict[str, Any]) -> str:
        """Log event with nanosecond precision timing"""
        if NANOSECOND_TIMING_AVAILABLE:
            event['ingestion_timestamp_ns'] = get_ns_timestamp(ClockType.REALTIME)
            if 'source_timestamp_ns' not in event:
                event['source_timestamp_ns'] = event['ingestion_timestamp_ns']
        else:
            current_time_ns = int(time.time() * 1_000_000_000)
            event['ingestion_timestamp_ns'] = current_time_ns
            if 'source_timestamp_ns' not in event:
                event['source_timestamp_ns'] = current_time_ns
        
        timestamp_delta = abs(event['ingestion_timestamp_ns'] - event['source_timestamp_ns'])
        event['timestamp_delta_ns'] = timestamp_delta
        
        if timestamp_delta > 3_600_000_000_000:
            event['timestamp_suspicious'] = True
            self.logger.warning(f"Suspicious timestamp delta: {timestamp_delta/1e9:.2f}s")
        
        audit_result = await self.audit_integration.process_audit_event(event)
        
        self.event_buffer.append({
            'event': event,
            'audit_result': audit_result,
            'buffer_timestamp': datetime.now().isoformat()
        })
        
        if len(self.event_buffer) >= self.buffer_size:
            await self._flush_buffer()
        
        self.processing_stats['events_processed'] += 1
        await self._update_processing_stats()
        
        return audit_result['event_id']
    
    async def _flush_buffer(self):
        """Flush event buffer to persistent storage"""
        if not self.event_buffer:
            return
        
        os.makedirs('audit_logs', exist_ok=True)
        batch_file = f"audit_logs/stream_batch_{int(datetime.now().timestamp())}.json"
        with open(batch_file, 'w') as f:
            json.dump(self.event_buffer, f, indent=2)
        
        self.logger.info(f"Flushed {len(self.event_buffer)} events to {batch_file}")
        self.event_buffer.clear()
    
    async def _update_processing_stats(self):
        """Update processing statistics"""
        current_time = datetime.now()
        time_diff = (current_time - self.processing_stats['last_stats_update']).total_seconds()
        
        if time_diff >= 1.0:  # Update every second
            self.processing_stats['events_per_second'] = 1 / time_diff if time_diff > 0 else 0
            self.processing_stats['last_stats_update'] = current_time
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get current processing statistics"""
        return self.processing_stats.copy()
    
    async def search_audit_logs(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search audit logs based on criteria"""
        results = []
        
        if 'event_id' in criteria:
            audit_trail = await self.audit_integration.get_audit_trail(criteria['event_id'])
            if audit_trail:
                results.append(audit_trail)
        
        return results
    
    async def force_flush_buffer(self):
        """Force flush buffer for testing or shutdown"""
        await self._flush_buffer()
    
    def get_buffer_status(self) -> Dict[str, Any]:
        """Get current buffer status"""
        return {
            'buffer_size': len(self.event_buffer),
            'buffer_capacity': self.buffer_size,
            'buffer_utilization': len(self.event_buffer) / self.buffer_size
        }

    async def log_performance_audit(self, component: str, metrics: Dict[str, Any], 
                                   thresholds: Dict[str, Any] = None) -> str:
        """Log performance metrics for audit compliance"""
        performance_event = {
            'event_type': 'performance_monitoring',
            'component': component,
            'metrics': metrics,
            'thresholds': thresholds or {},
            'violations': [],
            'compliance_status': 'compliant'
        }
        
        if thresholds:
            for metric_name, threshold in thresholds.items():
                if metric_name in metrics:
                    metric_value = metrics[metric_name]
                    if isinstance(threshold, dict):
                        if 'max' in threshold and metric_value > threshold['max']:
                            performance_event['violations'].append({
                                'metric': metric_name,
                                'value': metric_value,
                                'threshold': threshold['max'],
                                'type': 'exceeded_maximum'
                            })
                        if 'min' in threshold and metric_value < threshold['min']:
                            performance_event['violations'].append({
                                'metric': metric_name,
                                'value': metric_value,
                                'threshold': threshold['min'],
                                'type': 'below_minimum'
                            })
                    elif metric_value > threshold:
                        performance_event['violations'].append({
                            'metric': metric_name,
                            'value': metric_value,
                            'threshold': threshold,
                            'type': 'exceeded_threshold'
                        })
        
        if performance_event['violations']:
            performance_event['compliance_status'] = 'violation'
        
        return await self.log_event(performance_event)

    async def log_execution_audit(self, trade_data: Dict[str, Any], 
                                 execution_metrics: Dict[str, Any]) -> str:
        """Log trade execution metrics for regulatory compliance"""
        execution_event = {
            'event_type': 'trade_execution',
            'trade_id': trade_data.get('trade_id'),
            'symbol': trade_data.get('symbol'),
            'trade_type': trade_data.get('trade_type', 'unknown'),
            'execution_time_ms': execution_metrics.get('execution_time_ms'),
            'slippage_bps': execution_metrics.get('slippage_bps'),
            'expected_price': trade_data.get('expected_price'),
            'actual_price': execution_metrics.get('actual_price'),
            'api_latency_ms': execution_metrics.get('api_latency_ms'),
            'is_mock_trade': trade_data.get('is_mock_trade', False),
            'broker_response_time_ms': execution_metrics.get('broker_response_time_ms'),
            'market_impact_bps': execution_metrics.get('market_impact_bps'),
            'compliance_flags': []
        }
        
        if execution_event['execution_time_ms'] and execution_event['execution_time_ms'] > 1000:
            execution_event['compliance_flags'].append('high_execution_latency')
        
        if execution_event['slippage_bps'] and execution_event['slippage_bps'] > 50:
            execution_event['compliance_flags'].append('high_slippage')
        
        if execution_event['is_mock_trade']:
            execution_event['compliance_flags'].append('mock_trade_no_real_execution')
        
        return await self.log_event(execution_event)
