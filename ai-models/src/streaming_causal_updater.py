import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Deque
from collections import deque
import asyncio
import time

class StreamingCausalUpdater:
    """Real-time causal updating with streaming DAGs using incremental Bayesian updates"""
    
    def __init__(self, window_size: int = 1000, update_frequency: int = 100):
        self.window_size = window_size
        self.update_frequency = update_frequency
        self.data_buffer: Deque[Dict[str, Any]] = deque(maxlen=window_size)
        self.causal_structure = {}
        self.update_counter = 0
        self.streaming_stats = {
            'updates_processed': 0,
            'structure_changes': 0,
            'last_update_time': 0
        }
    
    async def process_streaming_data(self, data_point: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming streaming data point and update causal structure"""
        
        self.data_buffer.append(data_point)
        self.update_counter += 1
        
        result = {
            'data_point_processed': True,
            'buffer_size': len(self.data_buffer),
            'structure_updated': False,
            'causal_changes': []
        }
        
        if self.update_counter % self.update_frequency == 0:
            structure_update = await self._update_causal_structure()
            result.update(structure_update)
            result['structure_updated'] = True
        
        return result
    
    async def _update_causal_structure(self) -> Dict[str, Any]:
        """Update causal structure using incremental Bayesian updates"""
        
        if len(self.data_buffer) < 50:
            return {'error': 'Insufficient data for structure update'}
        
        current_data = pd.DataFrame(list(self.data_buffer))
        
        previous_structure = self.causal_structure.copy()
        
        new_structure = await self._learn_structure_incremental(current_data)
        
        changes = self._detect_structure_changes(previous_structure, new_structure)
        
        self.causal_structure = new_structure
        self.streaming_stats['updates_processed'] += 1
        self.streaming_stats['last_update_time'] = int(time.time())
        
        if changes:
            self.streaming_stats['structure_changes'] += 1
        
        return {
            'previous_structure': previous_structure,
            'new_structure': new_structure,
            'changes_detected': changes,
            'update_timestamp': time.time()
        }
    
    async def _learn_structure_incremental(self, data: pd.DataFrame) -> Dict[str, List[str]]:
        """Learn causal structure using incremental approach"""
        
        structure = {}
        numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
        
        for target in numeric_cols:
            potential_parents = [col for col in numeric_cols if col != target]
            parents = []
            
            for parent in potential_parents:
                correlation = data[parent].corr(data[target])
                if abs(correlation) > 0.3:
                    parents.append(parent)
            
            structure[target] = parents[:3]
        
        return structure
    
    def _detect_structure_changes(self, old_structure: Dict[str, List[str]], 
                                new_structure: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Detect changes in causal structure"""
        
        changes = []
        
        all_nodes = set(old_structure.keys()) | set(new_structure.keys())
        
        for node in all_nodes:
            old_parents = set(old_structure.get(node, []))
            new_parents = set(new_structure.get(node, []))
            
            added_parents = new_parents - old_parents
            removed_parents = old_parents - new_parents
            
            if added_parents:
                changes.append({
                    'type': 'edge_added',
                    'target': node,
                    'parents': list(added_parents)
                })
            
            if removed_parents:
                changes.append({
                    'type': 'edge_removed',
                    'target': node,
                    'parents': list(removed_parents)
                })
        
        return changes
    
    def get_current_structure(self) -> Dict[str, Any]:
        """Get current causal structure and statistics"""
        
        return {
            'causal_structure': self.causal_structure,
            'buffer_size': len(self.data_buffer),
            'streaming_stats': self.streaming_stats,
            'last_update': self.streaming_stats['last_update_time']
        }
    
    async def predict_causal_effect(self, intervention: Dict[str, float], 
                                  target: str) -> Dict[str, Any]:
        """Predict causal effect of intervention using current structure"""
        
        if target not in self.causal_structure:
            return {'error': f'Target {target} not in causal structure'}
        
        parents = self.causal_structure[target]
        
        if not parents:
            return {'predicted_effect': 0.0, 'confidence': 0.0}
        
        current_data = pd.DataFrame(list(self.data_buffer))
        
        effect_estimate = 0.0
        for parent in parents:
            if parent in intervention and parent in current_data.columns:
                correlation = current_data[parent].corr(current_data[target])
                effect_estimate += correlation * intervention[parent]
        
        confidence = min(1.0, len(self.data_buffer) / self.window_size)
        
        return {
            'predicted_effect': effect_estimate,
            'confidence': confidence,
            'contributing_parents': parents,
            'intervention': intervention
        }

class IncrementalBayesianUpdater:
    """Incremental Bayesian updates for streaming causal inference"""
    
    def __init__(self, prior_strength: float = 1.0):
        self.prior_strength = prior_strength
        self.posterior_params = {}
        self.observation_count = 0
    
    def update_posterior(self, variable: str, observation: float, 
                        parents: List[str], parent_values: Dict[str, float]) -> Dict[str, Any]:
        """Update posterior distribution for a variable given observation"""
        
        if variable not in self.posterior_params:
            self.posterior_params[variable] = {
                'mean': 0.0,
                'precision': self.prior_strength,
                'parent_coefficients': {parent: 0.0 for parent in parents}
            }
        
        params = self.posterior_params[variable]
        
        predicted_value = params['mean']
        for parent in parents:
            if parent in parent_values:
                predicted_value += params['parent_coefficients'][parent] * parent_values[parent]
        
        prediction_error = observation - predicted_value
        
        learning_rate = 1.0 / (params['precision'] + 1.0)
        
        params['mean'] += learning_rate * prediction_error
        params['precision'] += 1.0
        
        for parent in parents:
            if parent in parent_values:
                params['parent_coefficients'][parent] += learning_rate * prediction_error * parent_values[parent]
        
        self.observation_count += 1
        
        return {
            'variable': variable,
            'updated_mean': params['mean'],
            'updated_precision': params['precision'],
            'prediction_error': prediction_error,
            'learning_rate': learning_rate
        }
    
    def get_posterior_summary(self, variable: str) -> Dict[str, Any]:
        """Get summary of posterior distribution for a variable"""
        
        if variable not in self.posterior_params:
            return {'error': f'No posterior for variable {variable}'}
        
        params = self.posterior_params[variable]
        
        return {
            'variable': variable,
            'posterior_mean': params['mean'],
            'posterior_precision': params['precision'],
            'posterior_variance': 1.0 / params['precision'],
            'parent_coefficients': params['parent_coefficients'],
            'observations_processed': self.observation_count
        }
