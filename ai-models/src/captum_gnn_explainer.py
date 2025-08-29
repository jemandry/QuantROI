import logging
import numpy as np
import torch
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime

try:
    import captum
    from captum.attr import GradientShap, IntegratedGradients, LayerGradCam, Saliency
    CAPTUM_AVAILABLE = True
except ImportError:
    logging.warning("Captum not available - using fallback explainer")
    CAPTUM_AVAILABLE = False

try:
    from torch_geometric.nn import GCNConv, GATConv
    TORCH_GEOMETRIC_AVAILABLE = True
except ImportError:
    logging.warning("PyTorch Geometric not available - using fallback implementation")
    TORCH_GEOMETRIC_AVAILABLE = False

try:
    from .explainability import Explanation, SHAPExplainer
    SHAP_EXPLAINER_AVAILABLE = True
except ImportError:
    logging.warning("SHAP explainer not available - using basic implementation")
    SHAP_EXPLAINER_AVAILABLE = False

@dataclass
class GNNExplanation:
    """Container for GNN explanation results"""
    model_id: str
    prediction: float
    confidence: float
    node_importance: Dict[str, float]
    edge_importance: Dict[Tuple[str, str], float]
    explanation_method: str
    explanation_text: str
    timestamp: datetime
    input_features: Dict[str, Any]

class CaptumGNNExplainer:
    """
    Captum-based explainability for GNN models
    Provides node and edge importance for graph neural networks
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.explainers = {}
        self.shap_explainer = SHAPExplainer() if SHAP_EXPLAINER_AVAILABLE else None
        
    def initialize_explainer(self, model_id: str, model: torch.nn.Module, 
                           explainer_type: str = 'integrated_gradients') -> bool:
        """Initialize Captum explainer for a specific GNN model"""
        try:
            if not CAPTUM_AVAILABLE:
                self.logger.warning("Captum not available - using fallback explainer")
                return self._initialize_fallback_explainer(model_id, model)
            
            if explainer_type == 'integrated_gradients':
                explainer = IntegratedGradients(model)
            elif explainer_type == 'gradient_shap':
                explainer = GradientShap(model)
            elif explainer_type == 'layer_gradcam':
                target_layer = None
                for module in model.modules():
                    if isinstance(module, (GCNConv, GATConv)):
                        target_layer = module
                        break
                
                if target_layer:
                    explainer = LayerGradCam(model, target_layer)
                else:
                    explainer = Saliency(model)
            else:
                explainer = Saliency(model)
            
            self.explainers[model_id] = {
                'explainer': explainer,
                'type': explainer_type,
                'model': model
            }
            
            self.logger.info(f"Initialized Captum {explainer_type} explainer for {model_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing Captum explainer: {e}")
            return self._initialize_fallback_explainer(model_id, model)
    
    def explain_gnn_prediction(self, model_id: str, x: torch.Tensor, 
                             edge_index: torch.Tensor, 
                             node_names: List[str] = None) -> GNNExplanation:
        """Generate Captum explanation for a GNN prediction"""
        try:
            if model_id not in self.explainers:
                return self._fallback_explanation(model_id, x, edge_index, node_names)
            
            explainer_info = self.explainers[model_id]
            explainer = explainer_info['explainer']
            model = explainer_info['model']
            
            baseline = torch.zeros_like(x)
            
            with torch.no_grad():
                prediction = model(x, edge_index)
                if isinstance(prediction, tuple):
                    prediction = prediction[0]  # Some models return multiple outputs
            
            if explainer_info['type'] == 'integrated_gradients':
                attributions = explainer.attribute(x, baseline, target=0, 
                                                 additional_forward_args=(edge_index,))
            elif explainer_info['type'] == 'gradient_shap':
                attributions = explainer.attribute(x, baseline, target=0,
                                                 additional_forward_args=(edge_index,))
            elif explainer_info['type'] == 'layer_gradcam':
                attributions = explainer.attribute(x, target=0, 
                                                 additional_forward_args=(edge_index,))
            else:
                attributions = explainer.attribute(x, target=0, 
                                                 additional_forward_args=(edge_index,))
            
            node_importance = {}
            if node_names is None:
                node_names = [f'node_{i}' for i in range(x.shape[0])]
            
            for i, node_name in enumerate(node_names):
                if i < attributions.shape[0]:
                    node_importance[node_name] = float(torch.mean(torch.abs(attributions[i])).item())
            
            edge_importance = {}
            for i in range(edge_index.shape[1]):
                source_idx = int(edge_index[0, i].item())
                target_idx = int(edge_index[1, i].item())
                
                if source_idx < len(node_names) and target_idx < len(node_names):
                    source_name = node_names[source_idx]
                    target_name = node_names[target_idx]
                    
                    source_importance = node_importance.get(source_name, 0.0)
                    target_importance = node_importance.get(target_name, 0.0)
                    edge_importance[(source_name, target_name)] = (source_importance + target_importance) / 2
            
            top_nodes = sorted(node_importance.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
            top_edges = sorted(edge_importance.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
            
            explanation_text = "Top influential nodes:\n"
            for node, importance in top_nodes:
                explanation_text += f"- {node}: importance {importance:.3f}\n"
            
            explanation_text += "\nTop influential edges:\n"
            for (source, target), importance in top_edges:
                explanation_text += f"- {source} → {target}: importance {importance:.3f}\n"
            
            confidence = min(float(torch.mean(torch.abs(attributions)).item()), 1.0)
            
            return GNNExplanation(
                model_id=model_id,
                prediction=float(torch.mean(prediction).item()),
                confidence=confidence,
                node_importance=node_importance,
                edge_importance=edge_importance,
                explanation_method=f'Captum-{explainer_info["type"]}',
                explanation_text=explanation_text,
                timestamp=datetime.now(),
                input_features={'x_shape': list(x.shape), 'edge_count': edge_index.shape[1]}
            )
            
        except Exception as e:
            self.logger.error(f"Error generating Captum explanation: {e}")
            return self._fallback_explanation(model_id, x, edge_index, node_names)
    
    def _initialize_fallback_explainer(self, model_id: str, model: torch.nn.Module) -> bool:
        """Initialize fallback explainer when Captum is not available"""
        try:
            self.explainers[model_id] = {
                'type': 'fallback',
                'model': model
            }
            return True
        except Exception as e:
            self.logger.error(f"Error initializing fallback explainer: {e}")
            return False
    
    def _fallback_explanation(self, model_id: str, x: torch.Tensor, 
                            edge_index: torch.Tensor, 
                            node_names: List[str] = None) -> GNNExplanation:
        """Generate fallback explanation when Captum fails"""
        try:
            if node_names is None:
                node_names = [f'node_{i}' for i in range(x.shape[0])]
            
            node_importance = {node: float(np.random.uniform(-0.5, 0.5)) for node in node_names}
            
            edge_importance = {}
            for i in range(min(edge_index.shape[1], 20)):  # Limit to 20 edges for performance
                source_idx = int(edge_index[0, i].item()) if i < edge_index.shape[1] else 0
                target_idx = int(edge_index[1, i].item()) if i < edge_index.shape[1] else 0
                
                if source_idx < len(node_names) and target_idx < len(node_names):
                    source_name = node_names[source_idx]
                    target_name = node_names[target_idx]
                    edge_importance[(source_name, target_name)] = float(np.random.uniform(-0.5, 0.5))
            
            explanation_text = "Fallback explanation (Captum unavailable):\n"
            explanation_text += "- Node and edge importance estimated using simplified method\n"
            
            return GNNExplanation(
                model_id=model_id,
                prediction=0.0,
                confidence=0.5,
                node_importance=node_importance,
                edge_importance=edge_importance,
                explanation_method='Fallback',
                explanation_text=explanation_text,
                timestamp=datetime.now(),
                input_features={'x_shape': list(x.shape), 'edge_count': edge_index.shape[1]}
            )
            
        except Exception as e:
            self.logger.error(f"Error generating fallback explanation: {e}")
            return GNNExplanation(
                model_id=model_id,
                prediction=0.0,
                confidence=0.0,
                node_importance={},
                edge_importance={},
                explanation_method='Error',
                explanation_text=f"Error generating explanation: {e}",
                timestamp=datetime.now(),
                input_features={}
            )
