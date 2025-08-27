#!/usr/bin/env python3
"""
Enhanced Causal AI Orchestrator with Advanced VIX Regime Detection
Integrates regime-switching CIR models with existing causal inference
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime

from .advanced_regime_detection import AdvancedVIXRegimeDetector, RegimeDetectionResult
from ..quantitative_finance.gpu_accelerated_models import HybridCPUGPUProcessor
from .causal_ai_orchestrator import CausalAIOrchestrator  # Import existing orchestrator

logger = logging.getLogger(__name__)

class EnhancedCausalAIOrchestrator(CausalAIOrchestrator):
    """
    Enhanced Causal AI Orchestrator with advanced VIX regime detection
    Extends existing orchestrator with regime-switching CIR models
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.regime_detector = AdvancedVIXRegimeDetector(n_regimes=3)
        self.gpu_processor = HybridCPUGPUProcessor()
        
        self.current_regime_state = None
        self.regime_history = []
        
    async def detect_market_regime_advanced(self, 
                                          vix_data: pd.Series,
                                          lookback_window: int = 252) -> Dict[str, Any]:
        """
        Advanced VIX-based regime detection using regime-switching CIR models
        Replaces basic threshold-based approach
        """
        logger.info("Starting advanced VIX regime detection")
        
        try:
            recent_vix = vix_data.tail(lookback_window)
            
            if len(recent_vix) < 50:
                logger.warning("Insufficient VIX data for regime detection")
                return await self.detect_market_regime_vix_based(vix_data.iloc[-1])
            
            regime_result = await self.regime_detector.detect_vix_regimes(recent_vix)
            
            current_regime = regime_result.most_likely_regimes[-1]
            current_regime_prob = regime_result.regime_probabilities[-1]
            
            regime_labels = {0: 'low_volatility', 1: 'normal_volatility', 2: 'high_volatility'}
            current_regime_label = regime_labels.get(current_regime, 'unknown')
            
            self.current_regime_state = {
                'regime': current_regime_label,
                'regime_number': int(current_regime),
                'probabilities': current_regime_prob.tolist(),
                'confidence': float(np.max(current_regime_prob)),
                'timestamp': datetime.now().isoformat(),
                'model_fit': {
                    'log_likelihood': regime_result.log_likelihood,
                    'aic': regime_result.aic,
                    'bic': regime_result.bic
                }
            }
            
            self.regime_history.append(self.current_regime_state)
            
            if len(self.regime_history) > 1000:
                self.regime_history = self.regime_history[-1000:]
            
            if len(self.regime_history) > 1:
                prev_regime = self.regime_history[-2]['regime_number']
                if current_regime != prev_regime:
                    logger.info(f"Regime change detected: {prev_regime} -> {current_regime}")
                    await self._handle_regime_change(regime_result)
            
            return {
                'success': True,
                'regime_detection_result': self.current_regime_state,
                'cir_parameters': {
                    'kappa': regime_result.regime_parameters.kappa.tolist(),
                    'theta': regime_result.regime_parameters.theta.tolist(),
                    'xi': regime_result.regime_parameters.xi.tolist(),
                    'transition_matrix': regime_result.regime_parameters.transition_matrix.tolist()
                },
                'processing_time_ms': 0,  # Will be updated by caller
                'method': 'regime_switching_cir'
            }
            
        except Exception as e:
            logger.error(f"Advanced regime detection failed: {e}")
            return await self.detect_market_regime_vix_based(vix_data.iloc[-1])
    
    async def _handle_regime_change(self, regime_result: RegimeDetectionResult):
        """
        Handle regime change by triggering appropriate processing
        """
        try:
            market_params = {
                'regime_probabilities': regime_result.regime_probabilities,
                'cir_parameters': regime_result.regime_parameters,
                'high_vol_initial': float(np.max(regime_result.regime_parameters.theta))
            }
            
            simulation_results = await self.gpu_processor.process_regime_conditioned_simulations(
                regime_result.regime_probabilities,
                market_params
            )
            
            await self.adapt_causal_model_to_regime_advanced(regime_result)
            
            logger.info("Regime change processing completed")
            
        except Exception as e:
            logger.error(f"Regime change handling failed: {e}")
    
    async def adapt_causal_model_to_regime_advanced(self, regime_result: RegimeDetectionResult):
        """
        Adapt causal model parameters based on detected regime
        Enhanced version with CIR parameters
        """
        try:
            current_regime = regime_result.most_likely_regimes[-1]
            cir_params = regime_result.regime_parameters
            
            if current_regime == 0:  # Low volatility regime
                adaptation_params = {
                    'learning_rate_multiplier': 1.2,
                    'confidence_threshold': 0.7,
                    'volatility_adjustment': float(cir_params.theta[0]),
                    'mean_reversion_speed': float(cir_params.kappa[0])
                }
            elif current_regime == 1:  # Normal volatility regime
                adaptation_params = {
                    'learning_rate_multiplier': 1.0,
                    'confidence_threshold': 0.8,
                    'volatility_adjustment': float(cir_params.theta[1]),
                    'mean_reversion_speed': float(cir_params.kappa[1])
                }
            else:  # High volatility regime
                adaptation_params = {
                    'learning_rate_multiplier': 0.8,
                    'confidence_threshold': 0.9,
                    'volatility_adjustment': float(cir_params.theta[2]),
                    'mean_reversion_speed': float(cir_params.kappa[2])
                }
            
            if hasattr(self, 'causal_model') and self.causal_model:
                self.causal_model.update_regime_parameters(adaptation_params)
            
            logger.info(f"Causal model adapted for regime {current_regime}")
            
        except Exception as e:
            logger.error(f"Causal model adaptation failed: {e}")
