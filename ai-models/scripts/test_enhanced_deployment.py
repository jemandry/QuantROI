#!/usr/bin/env python3
"""
Test script for enhanced deployment components:
- MRMBot (Model Risk Monitoring Bot)
- Enhanced IPFS Audit Logger
- OpenTelemetry Integration
- Vector Clock System
"""

import asyncio
import logging
import json
import time
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.enhanced_deployment_integration import create_enhanced_deployment_stack

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_mrm_bot_functionality(deployment):
    """Test MRMBot functionality"""
    
    logger.info("Testing MRMBot functionality...")
    
    test_predictions = [
        {
            'id': 'pred_001',
            'model_id': 'causal_trading_model_v1',
            'confidence': 0.92,
            'signal_strength': 0.85,
            'predicted_return': 0.025,
            'strategy': 'momentum_breakout'
        },
        {
            'id': 'pred_002',
            'model_id': 'causal_trading_model_v1',
            'confidence': 0.78,  # Below threshold
            'signal_strength': 0.65,
            'predicted_return': 0.015,
            'strategy': 'mean_reversion'
        },
        {
            'id': 'pred_003',
            'model_id': 'risk_assessment_model_v2',
            'confidence': 0.95,
            'signal_strength': 0.90,
            'predicted_return': -0.010,
            'strategy': 'risk_hedge'
        }
    ]
    
    results = []
    for prediction in test_predictions:
        actual_outcome = None
        if prediction['id'] in ['pred_001']:
            actual_outcome = {
                'actual_return': prediction['predicted_return'] + 0.005,  # Slight positive error
                'execution_time_ms': 1.2
            }
        
        result = await deployment.mrm_bot.monitor_model_prediction(
            prediction['model_id'],
            prediction,
            actual_outcome
        )
        
        results.append({
            'prediction_id': prediction['id'],
            'result': result
        })
        
        logger.info(f"Monitored prediction {prediction['id']}: {result['status']}")
        
        await asyncio.sleep(0.1)
    
    performance_summary = await deployment.mrm_bot.get_model_performance_summary()
    logger.info(f"MRMBot performance summary: {json.dumps(performance_summary, indent=2)}")
    
    return results

async def test_ipfs_audit_logging(deployment):
    """Test IPFS audit logging functionality"""
    
    logger.info("Testing IPFS audit logging...")
    
    test_decisions = [
        {
            'decision_id': 'trade_001',
            'action': 'buy',
            'symbol': 'AAPL',
            'quantity': 100,
            'price': 150.25,
            'confidence': 0.89,
            'reasoning': 'Strong momentum signal with high volume confirmation'
        },
        {
            'decision_id': 'trade_002',
            'action': 'sell',
            'symbol': 'TSLA',
            'quantity': 50,
            'price': 245.80,
            'confidence': 0.76,
            'reasoning': 'Risk management override due to portfolio concentration'
        },
        {
            'decision_id': 'override_001',
            'action': 'override',
            'original_signal': 'buy_NVDA',
            'override_reason': 'Model confidence below threshold',
            'confidence': 0.72
        }
    ]
    
    ipfs_entries = []
    for decision in test_decisions:
        entry = await deployment.ipfs_logger.log_immutable_decision(
            decision_data=decision,
            decision_type='trading_decision'
        )
        
        if entry:
            ipfs_entries.append(entry)
            logger.info(f"Logged decision {decision['decision_id']} to IPFS: {entry.ipfs_hash}")
        
        await asyncio.sleep(0.1)
    
    if ipfs_entries:
        test_entry = ipfs_entries[0]
        audit_trail = await deployment.ipfs_logger.get_decision_audit_trail(test_entry.entry_id)
        logger.info(f"Retrieved audit trail: {json.dumps(audit_trail, indent=2)}")
    
    storage_report = await deployment.ipfs_logger.generate_storage_report()
    logger.info(f"IPFS storage report: {json.dumps(storage_report, indent=2)}")
    
    return ipfs_entries

async def test_telemetry_integration(deployment):
    """Test OpenTelemetry integration"""
    
    logger.info("Testing OpenTelemetry integration...")
    
    async with deployment.telemetry.trace_operation(
        "test_trading_operation",
        component="test_suite",
        attributes={"test_type": "integration", "operation_count": 3}
    ):
        operations = [
            ("market_data_processing", 0.3),
            ("risk_assessment", 4.5),
            ("trade_execution", 0.8),
            ("portfolio_update", 2.1)
        ]
        
        for operation_name, delay_ms in operations:
            async with deployment.telemetry.trace_operation(
                operation_name,
                component="trading_engine",
                attributes={"simulated_delay_ms": delay_ms}
            ):
                await asyncio.sleep(delay_ms / 1000)
                logger.info(f"Completed {operation_name} in {delay_ms}ms")
    
    performance_report = await deployment.telemetry.get_performance_report()
    logger.info(f"Telemetry performance report: {json.dumps(performance_report, indent=2)}")
    
    return performance_report

async def test_vector_clock_system(deployment):
    """Test Vector Clock system"""
    
    logger.info("Testing Vector Clock system...")
    
    test_events = [
        {
            'event_type': 'market_data_update',
            'event_data': {'symbol': 'AAPL', 'price': 150.25, 'volume': 1000000}
        },
        {
            'event_type': 'trading_signal_generated',
            'event_data': {'signal': 'buy', 'confidence': 0.89, 'symbol': 'AAPL'},
            'dependencies': []  # Will be updated with previous event
        },
        {
            'event_type': 'trade_executed',
            'event_data': {'action': 'buy', 'symbol': 'AAPL', 'quantity': 100, 'price': 150.30},
            'dependencies': []  # Will be updated
        },
        {
            'event_type': 'risk_assessment_updated',
            'event_data': {'portfolio_risk': 0.15, 'var_95': -0.025},
            'dependencies': []  # Will be updated
        }
    ]
    
    created_events = []
    for i, event_data in enumerate(test_events):
        if i > 0:
            event_data['dependencies'] = [created_events[-1].event_id]
        
        event = await deployment.vector_clock.create_event(
            event_type=event_data['event_type'],
            event_data=event_data['event_data'],
            dependencies=event_data.get('dependencies', [])
        )
        
        created_events.append(event)
        logger.info(f"Created event {event.event_id} with clock {event.vector_clock.clock}")
        
        await asyncio.sleep(0.1)
    
    if created_events:
        test_event = created_events[-1]  # Last event should have full causal history
        causal_history = await deployment.vector_clock.get_causal_history(test_event.event_id)
        logger.info(f"Causal history for {test_event.event_id}: {json.dumps(causal_history, indent=2)}")
    
    causal_report = await deployment.vector_clock.generate_causal_audit_report()
    logger.info(f"Vector clock audit report: {json.dumps(causal_report, indent=2)}")
    
    return created_events

async def test_integrated_workflow(deployment):
    """Test integrated workflow using all components"""
    
    logger.info("Testing integrated workflow...")
    
    test_scenarios = [
        {
            'model_id': 'integrated_model_v1',
            'prediction': {
                'id': 'integrated_pred_001',
                'confidence': 0.91,
                'signal_strength': 0.88,
                'predicted_return': 0.032,
                'symbol': 'MSFT',
                'action': 'buy',
                'quantity': 200
            },
            'actual_outcome': {
                'actual_return': 0.029,
                'execution_time_ms': 1.1,
                'slippage': 0.001
            }
        },
        {
            'model_id': 'integrated_model_v1',
            'prediction': {
                'id': 'integrated_pred_002',
                'confidence': 0.73,  # Below threshold - should trigger override
                'signal_strength': 0.65,
                'predicted_return': 0.018,
                'symbol': 'GOOGL',
                'action': 'buy',
                'quantity': 50
            },
            'actual_outcome': None  # No execution due to override
        }
    ]
    
    workflow_results = []
    for scenario in test_scenarios:
        result = await deployment.process_trading_decision(
            model_id=scenario['model_id'],
            prediction=scenario['prediction'],
            actual_outcome=scenario['actual_outcome']
        )
        
        workflow_results.append(result)
        logger.info(f"Integrated workflow result: {json.dumps(result, indent=2)}")
        
        await asyncio.sleep(0.2)
    
    return workflow_results

async def main():
    """Main test function"""
    
    logger.info("Starting enhanced deployment components test...")
    
    try:
        deployment = await create_enhanced_deployment_stack("test_node_001")
        
        status = await deployment.get_system_status()
        logger.info(f"System status: {json.dumps(status, indent=2)}")
        
        logger.info("\n" + "="*50)
        logger.info("RUNNING COMPONENT TESTS")
        logger.info("="*50)
        
        mrm_results = await test_mrm_bot_functionality(deployment)
        
        ipfs_results = await test_ipfs_audit_logging(deployment)
        
        telemetry_results = await test_telemetry_integration(deployment)
        
        vector_results = await test_vector_clock_system(deployment)
        
        logger.info("\n" + "="*50)
        logger.info("RUNNING INTEGRATED WORKFLOW TEST")
        logger.info("="*50)
        
        workflow_results = await test_integrated_workflow(deployment)
        
        logger.info("\n" + "="*50)
        logger.info("GENERATING COMPREHENSIVE REPORT")
        logger.info("="*50)
        
        comprehensive_report = await deployment.generate_comprehensive_report()
        
        def json_serializer(obj):
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: json_serializer(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [json_serializer(item) for item in obj]
            return str(obj)
        
        serializable_report = json_serializer(comprehensive_report)
        
        report_filename = f"enhanced_deployment_test_report_{int(datetime.now().timestamp())}.json"
        with open(report_filename, 'w') as f:
            json.dump(serializable_report, f, indent=2)
        
        logger.info(f"Comprehensive report saved to: {report_filename}")
        logger.info(f"Report summary: {json.dumps(comprehensive_report['system_health'], indent=2)}")
        
        await deployment.shutdown_all_components()
        
        logger.info("\n" + "="*50)
        logger.info("TEST COMPLETED SUCCESSFULLY")
        logger.info("="*50)
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
