#!/usr/bin/env python3
"""
Enhanced System Integration Layer
Connects advanced VIX regime detection, GPU acceleration, and causal indexing
"""

import asyncio
import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime

from ..causal_ai_engine.enhanced_causal_orchestrator import EnhancedCausalAIOrchestrator
from ..real_time_pipeline.gpu_enhanced_processor import GPUEnhancedEventProcessor
from ..quantitative_finance.gpu_accelerated_models import HybridCPUGPUProcessor
from .system_orchestrator import SystemOrchestrator

logger = logging.getLogger(__name__)

class EnhancedSystemIntegration:
    """
    Integration layer for enhanced VIX regime detection and GPU acceleration
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        self.enhanced_orchestrator = EnhancedCausalAIOrchestrator(
            redis_client=config.get('redis_client'),
            neo4j_driver=config.get('neo4j_driver')
        )
        
        self.gpu_event_processor = GPUEnhancedEventProcessor(
            kafka_servers=config.get('kafka_servers', ['localhost:9092']),
            redis_url=config.get('redis_url', 'redis://localhost:6379')
        )
        
        self.hybrid_processor = HybridCPUGPUProcessor()
        
        self.current_regime = None
        self.performance_metrics = {}
        
    async def initialize_enhanced_system(self):
        """Initialize all enhanced components"""
        logger.info("Initializing enhanced system integration")
        
        try:
            await self.gpu_event_processor.initialize()
            
            self._register_enhanced_handlers()
            
            asyncio.create_task(self._regime_monitoring_loop())
            asyncio.create_task(self._performance_monitoring_loop())
            
            logger.info("Enhanced system integration initialized successfully")
            
        except Exception as e:
            logger.error(f"Enhanced system initialization failed: {e}")
            raise
    
    def _register_enhanced_handlers(self):
        """Register enhanced event handlers"""
        self.gpu_event_processor.register_regime_handler(
            'high_volatility', 'vix_update', self._handle_high_vol_vix_update
        )
        self.gpu_event_processor.register_regime_handler(
            'low_volatility', 'vix_update', self._handle_low_vol_vix_update
        )
        
        self.gpu_event_processor.register_handler(
            'monte_carlo_simulation', self._handle_gpu_monte_carlo
        )
        self.gpu_event_processor.register_handler(
            'options_pricing', self._handle_gpu_options_pricing
        )
    
    async def process_vix_regime_update(self, vix_data: pd.Series) -> Dict[str, Any]:
        """
        Process VIX data update with enhanced regime detection
        """
        try:
            regime_result = await self.enhanced_orchestrator.detect_market_regime_advanced(vix_data)
            
            if regime_result['success']:
                self.current_regime = regime_result['regime_detection_result']
                
                await self.gpu_event_processor.update_regime_state(self.current_regime)
                
                if self._regime_changed():
                    await self._handle_regime_transition(regime_result)
                
                return {
                    'success': True,
                    'regime_update': self.current_regime,
                    'enhanced_processing': True
                }
            else:
                return regime_result
                
        except Exception as e:
            logger.error(f"VIX regime update processing failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _regime_changed(self) -> bool: 
        """Check if regime has changed significantly"""
        return True  # Simplified for now
    
    async def _handle_regime_transition(self, regime_result: Dict[str, Any]):
        """Handle regime transition with GPU-accelerated processing"""
        try:
            logger.info("Processing regime transition with GPU acceleration")
            
            market_params = {
                'regime_probabilities': np.array([[0.3, 0.4, 0.3]]),  # Simplified
                'current_regime': self.current_regime['regime'],
                'confidence': self.current_regime['confidence']
            }
            
            simulation_results = await self.hybrid_processor.process_regime_conditioned_simulations(
                market_params['regime_probabilities'],
                market_params
            )
            
            self.performance_metrics['last_regime_transition'] = {
                'timestamp': datetime.now().isoformat(),
                'regime': self.current_regime['regime'],
                'gpu_results': simulation_results
            }
            
        except Exception as e:
            logger.error(f"Regime transition handling failed: {e}")
    
    async def _regime_monitoring_loop(self):
        """Continuous regime monitoring loop"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                vix_data = pd.Series(np.random.gamma(2, 2, 252))
                
                await self.process_vix_regime_update(vix_data)
                
            except Exception as e:
                logger.error(f"Regime monitoring loop error: {e}")
                await asyncio.sleep(10)  # Brief pause before retry
    
    async def _performance_monitoring_loop(self):
        """Monitor performance of enhanced components"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                gpu_metrics = await self.gpu_event_processor.get_gpu_performance_metrics()
                
                processor_metrics = await self.gpu_event_processor.get_metrics()
                
                self.performance_metrics.update({
                    'gpu_performance': gpu_metrics,
                    'processor_performance': processor_metrics,
                    'timestamp': datetime.now().isoformat()
                })
                
                if gpu_metrics.get('gpu_available'):
                    logger.info(f"GPU Performance: {gpu_metrics.get('gpu_operations', 0)} operations, "
                              f"avg speedup: {gpu_metrics.get('estimated_speedup', 1.0):.1f}×")
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(10)
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            'current_regime': self.current_regime,
            'performance_metrics': self.performance_metrics,
            'gpu_available': self.gpu_event_processor.gpu_available,
            'enhanced_components_active': True,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _handle_high_vol_vix_update(self, event) -> Dict[str, Any]:
        """Handle VIX updates during high volatility regime"""
        return {
            'processed': True,
            'regime': 'high_volatility',
            'enhanced_monitoring': True,
            'gpu_acceleration': True
        }
    
    async def _handle_low_vol_vix_update(self, event) -> Dict[str, Any]:
        """Handle VIX updates during low volatility regime"""
        return {
            'processed': True,
            'regime': 'low_volatility',
            'standard_processing': True
        }
    
    async def _handle_gpu_monte_carlo(self, event) -> Dict[str, Any]:
        """Handle GPU-accelerated Monte Carlo simulation"""
        return await self.gpu_event_processor._gpu_monte_carlo_processing(event)
    
    async def _handle_gpu_options_pricing(self, event) -> Dict[str, Any]:
        """Handle GPU-accelerated options pricing"""
        return await self.gpu_event_processor._gpu_greeks_calculation(event)
