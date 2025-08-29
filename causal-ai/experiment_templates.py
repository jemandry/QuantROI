#!/usr/bin/env python3
"""
MLflow Experiment Templates for Causal AI
Standardized experiment tracking with hierarchical parent/child runs
"""

import mlflow
import mlflow.pytorch
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import logging

class CausalExperimentTemplate:
    """Template for causal AI experiment tracking with hierarchical runs"""
    
    def __init__(self, experiment_name: str = "causal_ai_experiments"):
        mlflow.set_experiment(experiment_name)
        self.experiment_name = experiment_name
        self.logger = logging.getLogger(__name__)
        self.active_parent_run = None
    
    def start_parent_run(self, run_name: str, tags: Dict[str, str] = None) -> str:
        """Start parent run for causal analysis workflow"""
        self.active_parent_run = mlflow.start_run(run_name=run_name, tags=tags or {})
        
        mlflow.log_param("experiment_type", "causal_analysis")
        mlflow.log_param("start_time", datetime.now().isoformat())
        mlflow.log_param("framework", "causalnex_dowhy")
        mlflow.log_param("platform", "quantroi_ria")
        
        self.logger.info(f"Started parent run: {self.active_parent_run.info.run_id}")
        return self.active_parent_run.info.run_id
    
    def start_child_run(self, child_name: str, child_type: str, 
                       parent_run_id: str = None) -> str:
        """Start child run for specific causal analysis step"""
        parent_id = parent_run_id or (self.active_parent_run.info.run_id if self.active_parent_run else None)
        
        if not parent_id:
            raise ValueError("No parent run available. Start a parent run first.")
        
        with mlflow.start_run(run_id=parent_id):
            child_run = mlflow.start_run(
                run_name=f"{child_name}_{datetime.now().strftime('%H%M%S')}",
                nested=True,
                tags={"child_type": child_type, "parent_run_id": parent_id}
            )
            
            mlflow.log_param("parent_run_id", parent_id)
            mlflow.log_param("analysis_step", child_type)
            mlflow.log_param("step_start_time", datetime.now().isoformat())
            
            self.logger.info(f"Started child run: {child_run.info.run_id} for step: {child_type}")
            return child_run.info.run_id
    
    def log_causal_analysis_results(self, confidence_score: float, 
                                  causal_strength: float, granger_p_value: float,
                                  vote_refinements: int = 0, zkp_proof_hash: str = None):
        """Log causal analysis metrics and artifacts"""
        mlflow.log_metric("confidence_score", confidence_score)
        mlflow.log_metric("causal_strength", causal_strength)
        mlflow.log_metric("granger_p_value", granger_p_value)
        mlflow.log_metric("vote_refinements", vote_refinements)
        
        if zkp_proof_hash:
            mlflow.log_param("zkp_proof_hash", zkp_proof_hash)
        
        is_significant = granger_p_value < 0.05
        mlflow.log_param("statistically_significant", is_significant)
        
        self.logger.info(f"Logged causal analysis results: confidence={confidence_score:.3f}, strength={causal_strength:.3f}")
    
    def log_vote_integration_metrics(self, votes_processed: int, 
                                   confidence_improvement: float,
                                   consensus_score: float):
        """Log vote integration and consensus metrics"""
        mlflow.log_metric("votes_processed", votes_processed)
        mlflow.log_metric("confidence_improvement", confidence_improvement)
        mlflow.log_metric("consensus_score", consensus_score)
        
        vote_effectiveness = confidence_improvement / max(votes_processed, 1)
        mlflow.log_metric("vote_effectiveness", vote_effectiveness)
    
    def log_model_artifacts(self, model_path: str, model_type: str = "causal_model"):
        """Log model artifacts with metadata"""
        mlflow.log_artifact(model_path, artifact_path=f"models/{model_type}")
        mlflow.log_param("model_type", model_type)
        mlflow.log_param("model_path", model_path)
    
    def end_run(self):
        """End the current MLflow run"""
        if self.active_parent_run:
            mlflow.end_run()
            self.active_parent_run = None
            self.logger.info("Ended MLflow run")

class CausalWorkflowTracker:
    """Tracks complete causal analysis workflows with multiple steps"""
    
    def __init__(self):
        self.template = CausalExperimentTemplate()
        self.workflow_steps = []
    
    async def track_causal_workflow(self, symbols: List[str], timeframe: str) -> str:
        """Track complete causal analysis workflow"""
        workflow_name = f"causal_analysis_{'-'.join(symbols)}_{timeframe}"
        parent_run_id = self.template.start_parent_run(
            workflow_name,
            tags={
                "symbols": ",".join(symbols),
                "timeframe": timeframe,
                "workflow_type": "full_causal_analysis"
            }
        )
        
        data_run_id = self.template.start_child_run(
            "data_collection", "data_preprocessing", parent_run_id
        )
        
        discovery_run_id = self.template.start_child_run(
            "causal_discovery", "causal_inference", parent_run_id
        )
        
        validation_run_id = self.template.start_child_run(
            "validation", "statistical_validation", parent_run_id
        )
        
        self.workflow_steps = [data_run_id, discovery_run_id, validation_run_id]
        return parent_run_id
    
    async def log_workflow_completion(self, success: bool, total_time: float, 
                                    final_confidence: float):
        """Log workflow completion metrics"""
        mlflow.log_metric("workflow_success", 1.0 if success else 0.0)
        mlflow.log_metric("total_execution_time", total_time)
        mlflow.log_metric("final_confidence_score", final_confidence)
        
        self.template.end_run()
        self.logger.info(f"Workflow completed: success={success}, time={total_time:.2f}s")
