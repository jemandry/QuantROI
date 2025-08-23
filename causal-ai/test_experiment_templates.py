#!/usr/bin/env python3
"""
Unit Tests for MLflow Experiment Templates
Tests hierarchical experiment tracking functionality
"""

import unittest
import tempfile
import os
from unittest.mock import patch, MagicMock
from experiment_templates import CausalExperimentTemplate, CausalWorkflowTracker

class TestCausalExperimentTemplate(unittest.TestCase):
    """Test causal experiment template functionality"""
    
    def setUp(self):
        self.template = CausalExperimentTemplate("test_experiment")
    
    @patch('mlflow.set_experiment')
    @patch('mlflow.start_run')
    @patch('mlflow.log_param')
    def test_start_parent_run(self, mock_log_param, mock_start_run, mock_set_experiment):
        """Test starting parent run"""
        mock_run = MagicMock()
        mock_run.info.run_id = "test_parent_run_id"
        mock_start_run.return_value = mock_run
        
        run_id = self.template.start_parent_run("test_run", {"tag1": "value1"})
        
        self.assertEqual(run_id, "test_parent_run_id")
        mock_set_experiment.assert_called_once_with("test_experiment")
        mock_start_run.assert_called_once()
        self.assertEqual(mock_log_param.call_count, 4)
    
    @patch('mlflow.start_run')
    @patch('mlflow.log_param')
    def test_start_child_run(self, mock_log_param, mock_start_run):
        """Test starting child run"""
        mock_parent_run = MagicMock()
        mock_parent_run.info.run_id = "parent_id"
        self.template.active_parent_run = mock_parent_run
        
        mock_child_run = MagicMock()
        mock_child_run.info.run_id = "child_id"
        mock_start_run.return_value = mock_child_run
        
        child_id = self.template.start_child_run("test_child", "data_preprocessing")
        
        self.assertEqual(child_id, "child_id")
        self.assertEqual(mock_log_param.call_count, 3)
    
    @patch('mlflow.log_metric')
    @patch('mlflow.log_param')
    def test_log_causal_analysis_results(self, mock_log_param, mock_log_metric):
        """Test logging causal analysis results"""
        self.template.log_causal_analysis_results(
            confidence_score=0.85,
            causal_strength=0.75,
            granger_p_value=0.03,
            vote_refinements=5,
            zkp_proof_hash="0x123abc"
        )
        
        self.assertEqual(mock_log_metric.call_count, 4)
        self.assertEqual(mock_log_param.call_count, 2)
    
    @patch('mlflow.log_metric')
    def test_log_vote_integration_metrics(self, mock_log_metric):
        """Test logging vote integration metrics"""
        self.template.log_vote_integration_metrics(
            votes_processed=10,
            confidence_improvement=0.15,
            consensus_score=0.88
        )
        
        self.assertEqual(mock_log_metric.call_count, 4)
    
    @patch('mlflow.log_artifact')
    @patch('mlflow.log_param')
    def test_log_model_artifacts(self, mock_log_param, mock_log_artifact):
        """Test logging model artifacts"""
        with tempfile.NamedTemporaryFile() as temp_file:
            self.template.log_model_artifacts(temp_file.name, "test_model")
            
            mock_log_artifact.assert_called_once()
            self.assertEqual(mock_log_param.call_count, 2)

class TestCausalWorkflowTracker(unittest.TestCase):
    """Test causal workflow tracker functionality"""
    
    def setUp(self):
        self.tracker = CausalWorkflowTracker()
    
    @patch.object(CausalExperimentTemplate, 'start_parent_run')
    @patch.object(CausalExperimentTemplate, 'start_child_run')
    async def test_track_causal_workflow(self, mock_start_child, mock_start_parent):
        """Test tracking complete causal workflow"""
        mock_start_parent.return_value = "parent_id"
        mock_start_child.side_effect = ["child1", "child2", "child3"]
        
        parent_id = await self.tracker.track_causal_workflow(
            symbols=["AAPL", "MSFT"],
            timeframe="1d"
        )
        
        self.assertEqual(parent_id, "parent_id")
        mock_start_parent.assert_called_once()
        self.assertEqual(mock_start_child.call_count, 3)
        self.assertEqual(len(self.tracker.workflow_steps), 3)
    
    @patch('mlflow.log_metric')
    @patch.object(CausalExperimentTemplate, 'end_run')
    async def test_log_workflow_completion(self, mock_end_run, mock_log_metric):
        """Test logging workflow completion"""
        await self.tracker.log_workflow_completion(
            success=True,
            total_time=45.5,
            final_confidence=0.92
        )
        
        self.assertEqual(mock_log_metric.call_count, 3)
        mock_end_run.assert_called_once()

if __name__ == '__main__':
    unittest.main()
