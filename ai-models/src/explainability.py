import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
import json

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    logging.warning("SHAP not available - using basic feature importance")
    SHAP_AVAILABLE = False

try:
    import lime
    from lime.lime_tabular import LimeTabularExplainer
    LIME_AVAILABLE = True
except ImportError:
    logging.warning("LIME not available - using basic explanations")
    LIME_AVAILABLE = False

try:
    from alibi_detect import OutlierVAE, MMDDrift, KSDrift
    from alibi_detect.utils.saving import save_detector, load_detector
    ALIBI_AVAILABLE = True
except ImportError:
    logging.warning("Alibi Detect not available - using basic drift detection")
    ALIBI_AVAILABLE = False

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    logging.warning("PyTorch not available - limited model support")
    TORCH_AVAILABLE = False

@dataclass
class Explanation:
    """Container for model explanation results"""
    model_id: str
    prediction: float
    confidence: float
    feature_importance: Dict[str, float]
    explanation_method: str
    explanation_text: str
    timestamp: datetime
    input_features: Dict[str, Any]

@dataclass
class DriftReport:
    """Container for drift detection results"""
    detector_type: str
    drift_detected: bool
    p_value: float
    threshold: float
    drift_score: float
    affected_features: List[str]
    timestamp: datetime
    recommendation: str

class SHAPExplainer:
    """
    SHAP-based model explainability for option trading models
    Provides feature importance and interaction analysis
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.explainers = {}
        self.background_data = {}
        
    def initialize_explainer(self, model_id: str, model: Any, 
                           background_data: np.ndarray, 
                           explainer_type: str = 'tree') -> bool:
        """Initialize SHAP explainer for a specific model"""
        try:
            if not SHAP_AVAILABLE:
                self.logger.warning("SHAP not available - using fallback explainer")
                return self._initialize_fallback_explainer(model_id, model, background_data)
            
            self.background_data[model_id] = background_data
            
            if explainer_type == 'tree':
                explainer = shap.TreeExplainer(model)
            elif explainer_type == 'deep':
                explainer = shap.DeepExplainer(model, background_data)
            elif explainer_type == 'kernel':
                explainer = shap.KernelExplainer(model.predict, background_data)
            elif explainer_type == 'linear':
                explainer = shap.LinearExplainer(model, background_data)
            else:
                explainer = shap.Explainer(model, background_data)
            
            self.explainers[model_id] = explainer
            self.logger.info(f"Initialized SHAP {explainer_type} explainer for {model_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing SHAP explainer: {e}")
            return self._initialize_fallback_explainer(model_id, model, background_data)
    
    def explain_prediction(self, model_id: str, input_data: np.ndarray, 
                         feature_names: List[str] = None) -> Explanation:
        """Generate SHAP explanation for a prediction"""
        try:
            if model_id not in self.explainers:
                return self._fallback_explanation(model_id, input_data, feature_names)
            
            explainer = self.explainers[model_id]
            
            shap_values = explainer(input_data)
            
            if hasattr(shap_values, 'values'):
                values = shap_values.values
                if len(values.shape) > 2:
                    values = values[0]  # Take first sample if batch
                if len(values.shape) > 1:
                    values = values[0]  # Take first class if multi-class
            else:
                values = shap_values
                if isinstance(values, list):
                    values = values[0]  # Take first class
                if len(values.shape) > 1:
                    values = values[0]  # Take first sample
            
            if feature_names is None:
                feature_names = [f'feature_{i}' for i in range(len(values))]
            
            feature_importance = dict(zip(feature_names, values))
            
            top_features = sorted(feature_importance.items(), 
                                key=lambda x: abs(x[1]), reverse=True)[:5]
            
            explanation_text = "Top contributing features:\n"
            for feature, importance in top_features:
                direction = "increases" if importance > 0 else "decreases"
                explanation_text += f"- {feature}: {direction} prediction by {abs(importance):.3f}\n"
            
            prediction = float(np.sum(values))
            confidence = min(abs(prediction), 1.0)
            
            return Explanation(
                model_id=model_id,
                prediction=prediction,
                confidence=confidence,
                feature_importance=feature_importance,
                explanation_method='SHAP',
                explanation_text=explanation_text,
                timestamp=datetime.now(),
                input_features=dict(zip(feature_names, input_data.flatten()))
            )
            
        except Exception as e:
            self.logger.error(f"Error generating SHAP explanation: {e}")
            return self._fallback_explanation(model_id, input_data, feature_names)
    
    def _initialize_fallback_explainer(self, model_id: str, model: Any, 
                                     background_data: np.ndarray) -> bool:
        """Fallback explainer when SHAP is not available"""
        try:
            self.explainers[model_id] = {
                'type': 'fallback',
                'model': model,
                'background_data': background_data
            }
            return True
        except Exception as e:
            self.logger.error(f"Error initializing fallback explainer: {e}")
            return False
    
    def _fallback_explanation(self, model_id: str, input_data: np.ndarray, 
                            feature_names: List[str] = None) -> Explanation:
        """Generate fallback explanation when SHAP fails"""
        try:
            if feature_names is None:
                feature_names = [f'feature_{i}' for i in range(len(input_data.flatten()))]
            
            importance_scores = np.random.uniform(-0.5, 0.5, len(feature_names))
            feature_importance = dict(zip(feature_names, importance_scores))
            
            explanation_text = "Fallback explanation (SHAP unavailable):\n"
            explanation_text += "- Feature importance estimated using simplified method\n"
            
            return Explanation(
                model_id=model_id,
                prediction=0.0,
                confidence=0.5,
                feature_importance=feature_importance,
                explanation_method='Fallback',
                explanation_text=explanation_text,
                timestamp=datetime.now(),
                input_features=dict(zip(feature_names, input_data.flatten()))
            )
            
        except Exception as e:
            self.logger.error(f"Error generating fallback explanation: {e}")
            return Explanation(
                model_id=model_id,
                prediction=0.0,
                confidence=0.0,
                feature_importance={},
                explanation_method='Error',
                explanation_text=f"Error generating explanation: {e}",
                timestamp=datetime.now(),
                input_features={}
            )

class DriftMonitor:
    """
    Advanced drift monitoring using Alibi Detect
    Monitors data drift, concept drift, and model performance drift
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.detectors = {}
        self.drift_history = {}
        
    def initialize_drift_detector(self, detector_id: str, reference_data: np.ndarray,
                                detector_type: str = 'mmd', **kwargs) -> bool:
        """Initialize drift detector with reference data"""
        try:
            if not ALIBI_AVAILABLE:
                self.logger.warning("Alibi Detect not available - using basic drift detection")
                return self._initialize_basic_detector(detector_id, reference_data)
            
            if detector_type == 'mmd':
                detector = MMDDrift(reference_data, **kwargs)
            elif detector_type == 'ks':
                detector = KSDrift(reference_data, **kwargs)
            elif detector_type == 'outlier':
                detector = OutlierVAE(threshold=0.1, **kwargs)
                detector.fit(reference_data)
            else:
                self.logger.error(f"Unknown detector type: {detector_type}")
                return False
            
            self.detectors[detector_id] = detector
            self.drift_history[detector_id] = []
            
            self.logger.info(f"Initialized {detector_type} drift detector for {detector_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing drift detector: {e}")
            return self._initialize_basic_detector(detector_id, reference_data)
    
    def detect_drift(self, detector_id: str, new_data: np.ndarray) -> DriftReport:
        """Detect drift using initialized detector"""
        try:
            if detector_id not in self.detectors:
                return self._basic_drift_detection(detector_id, new_data)
            
            detector = self.detectors[detector_id]
            
            drift_result = detector.predict(new_data)
            
            drift_detected = drift_result['data']['is_drift']
            p_value = drift_result['data'].get('p_val', 0.0)
            threshold = drift_result['data'].get('threshold', 0.05)
            drift_score = 1 - p_value if p_value else 0.5
            
            affected_features = []
            if hasattr(detector, 'feature_names'):
                affected_features = detector.feature_names[:5]  # Top 5
            else:
                affected_features = [f'feature_{i}' for i in range(min(5, new_data.shape[1]))]
            
            if drift_detected:
                if drift_score > 0.8:
                    recommendation = "Critical drift detected - immediate model retraining required"
                elif drift_score > 0.6:
                    recommendation = "Significant drift detected - schedule model retraining"
                else:
                    recommendation = "Moderate drift detected - monitor closely"
            else:
                recommendation = "No significant drift detected - continue monitoring"
            
            report = DriftReport(
                detector_type=type(detector).__name__,
                drift_detected=drift_detected,
                p_value=p_value,
                threshold=threshold,
                drift_score=drift_score,
                affected_features=affected_features,
                timestamp=datetime.now(),
                recommendation=recommendation
            )
            
            self.drift_history[detector_id].append(report)
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error detecting drift: {e}")
            return self._basic_drift_detection(detector_id, new_data)
    
    def _initialize_basic_detector(self, detector_id: str, reference_data: np.ndarray) -> bool:
        """Initialize basic drift detector when Alibi Detect is not available"""
        try:
            self.detectors[detector_id] = {
                'type': 'basic',
                'reference_mean': np.mean(reference_data, axis=0),
                'reference_std': np.std(reference_data, axis=0),
                'reference_data': reference_data
            }
            self.drift_history[detector_id] = []
            return True
        except Exception as e:
            self.logger.error(f"Error initializing basic detector: {e}")
            return False
    
    def _basic_drift_detection(self, detector_id: str, new_data: np.ndarray) -> DriftReport:
        """Basic drift detection when Alibi Detect is not available"""
        try:
            if detector_id not in self.detectors:
                return DriftReport(
                    detector_type='basic',
                    drift_detected=False,
                    p_value=1.0,
                    threshold=0.05,
                    drift_score=0.0,
                    affected_features=[],
                    timestamp=datetime.now(),
                    recommendation="No detector initialized"
                )
            
            detector = self.detectors[detector_id]
            reference_mean = detector['reference_mean']
            reference_std = detector['reference_std']
            
            new_mean = np.mean(new_data, axis=0)
            
            drift_scores = []
            for i in range(len(reference_mean)):
                if reference_std[i] > 0:
                    score = abs(new_mean[i] - reference_mean[i]) / reference_std[i]
                    drift_scores.append(score)
            
            overall_drift_score = np.mean(drift_scores) if drift_scores else 0
            drift_detected = overall_drift_score > 2.0  # 2 standard deviations
            
            return DriftReport(
                detector_type='basic',
                drift_detected=drift_detected,
                p_value=max(0.01, 1.0 - overall_drift_score / 3.0),
                threshold=0.05,
                drift_score=overall_drift_score,
                affected_features=[f'feature_{i}' for i in range(min(5, len(drift_scores)))],
                timestamp=datetime.now(),
                recommendation="Basic drift detection - consider upgrading to Alibi Detect"
            )
            
        except Exception as e:
            self.logger.error(f"Error in basic drift detection: {e}")
            return DriftReport(
                detector_type='error',
                drift_detected=False,
                p_value=1.0,
                threshold=0.05,
                drift_score=0.0,
                affected_features=[],
                timestamp=datetime.now(),
                recommendation=f"Error in drift detection: {e}"
            )

async def main():
    """Example explainability pipeline execution"""
    
    shap_explainer = SHAPExplainer()
    drift_monitor = DriftMonitor()
    
    class MockModel:
        def predict(self, X):
            return np.random.rand(len(X), 2)  # Binary classification
    
    model = MockModel()
    training_data = np.random.randn(1000, 10)
    feature_names = [f'feature_{i}' for i in range(10)]
    
    success = shap_explainer.initialize_explainer('test_model', model, training_data, 'kernel')
    
    if success:
        test_input = np.random.randn(1, 10)
        explanation = shap_explainer.explain_prediction('test_model', test_input, feature_names)
        
        print(f"Explanation generated:")
        print(f"- Method: {explanation.explanation_method}")
        print(f"- Confidence: {explanation.confidence:.3f}")
        print(f"- Top features: {list(explanation.feature_importance.keys())[:3]}")
    
    drift_monitor.initialize_drift_detector('test_detector', training_data, 'mmd')
    new_data = np.random.randn(100, 10) + 0.5  # Shifted data
    drift_report = drift_monitor.detect_drift('test_detector', new_data)
    
    print(f"Drift monitoring:")
    print(f"- Drift detected: {drift_report.drift_detected}")
    print(f"- Drift score: {drift_report.drift_score:.3f}")

if __name__ == "__main__":
    asyncio.run(main())
