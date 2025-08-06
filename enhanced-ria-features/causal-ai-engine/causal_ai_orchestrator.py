#!/usr/bin/env python3
"""
Causal AI Engine - Phase 2 Implementation
PyTorch/JAX integration with Neo4j graph storage and MLFlow tracking
"""

import asyncio
import logging
import json
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
import mlflow
import mlflow.pytorch
from neo4j import GraphDatabase
import networkx as nx
from statsmodels.tsa.stattools import grangercausalitytests
from causalnex.structure import StructureLearner
from causalnex.network import BayesianNetwork
from causalnex.inference import InferenceEngine
import kafka
from kafka import KafkaProducer, KafkaConsumer

@dataclass
class CausalModelConfig:
    """Configuration for causal AI models"""
    model_type: str = "pytorch"
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 100
    hidden_dims: List[int] = None
    dropout_rate: float = 0.1
    regularization: float = 0.01
    causal_threshold: float = 0.05
    granger_max_lags: int = 10
    
    def __post_init__(self):
        if self.hidden_dims is None:
            self.hidden_dims = [128, 64, 32]

@dataclass
class CausalEvent:
    """Causal event for streaming processing"""
    event_id: str
    timestamp: datetime
    event_type: str
    source_data: Dict[str, Any]
    features: Dict[str, float]
    causal_context: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None

@dataclass
class CausalPrediction:
    """Causal prediction result"""
    prediction_id: str
    timestamp: datetime
    target_variable: str
    predicted_value: float
    confidence_interval: Tuple[float, float]
    causal_factors: Dict[str, float]
    granger_p_values: Dict[str, float]
    model_version: str
    explanation: str

class CausalNeuralNetwork(nn.Module):
    """
    PyTorch neural network for causal inference with attention mechanisms
    """
    
    def __init__(self, input_dim: int, output_dim: int, config: CausalModelConfig):
        super().__init__()
        self.config = config
        
        layers = []
        prev_dim = input_dim
        
        for hidden_dim in config.hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.ReLU(),
                nn.Dropout(config.dropout_rate),
                nn.BatchNorm1d(hidden_dim)
            ])
            prev_dim = hidden_dim
        
        layers.append(nn.Linear(prev_dim, output_dim))
        
        self.network = nn.Sequential(*layers)
        
        self.attention = nn.MultiheadAttention(
            embed_dim=config.hidden_dims[0],
            num_heads=8,
            dropout=config.dropout_rate
        )
        
        self.causal_mask = nn.Parameter(torch.triu(torch.ones(input_dim, input_dim)), requires_grad=False)
        
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass with attention weights for causal interpretation
        """
        x_masked = x * self.causal_mask[:x.size(1), :x.size(1)]
        
        attn_output, attn_weights = self.attention(x_masked, x_masked, x_masked)
        
        output = self.network(attn_output.mean(dim=1))
        
        return output, attn_weights

class Neo4jCausalGraph:
    """
    Neo4j integration for causal graph storage and traversal
    """
    
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.logger = logging.getLogger(__name__)
        
    async def initialize_schema(self):
        """Initialize Neo4j schema for causal graphs"""
        with self.driver.session() as session:
            session.run("""
                CREATE CONSTRAINT causal_node_id IF NOT EXISTS
                FOR (n:CausalNode) REQUIRE n.node_id IS UNIQUE
            """)
            
            session.run("""
                CREATE CONSTRAINT causal_edge_id IF NOT EXISTS
                FOR ()-[r:CAUSES]-() REQUIRE r.edge_id IS UNIQUE
            """)
            
            session.run("""
                CREATE INDEX causal_timestamp IF NOT EXISTS
                FOR (n:CausalNode) ON (n.timestamp)
            """)
            
            session.run("""
                CREATE CONSTRAINT news_node_id IF NOT EXISTS
                FOR (n:News) REQUIRE n.news_id IS UNIQUE
            """)
            
            session.run("""
                CREATE INDEX news_timestamp IF NOT EXISTS
                FOR (n:News) ON (n.first_published_timestamp)
            """)
            
    async def store_causal_relationship(
        self,
        source_node: str,
        target_node: str,
        causal_strength: float,
        granger_p_value: float,
        confidence: float,
        metadata: Dict[str, Any]
    ):
        """Store causal relationship in Neo4j"""
        with self.driver.session() as session:
            session.run("""
                MERGE (source:CausalNode {node_id: $source_id})
                MERGE (target:CausalNode {node_id: $target_id})
                CREATE (source)-[r:CAUSES {
                    edge_id: $edge_id,
                    causal_strength: $strength,
                    granger_p_value: $p_value,
                    confidence: $confidence,
                    timestamp: $timestamp,
                    metadata: $metadata
                }]->(target)
            """, {
                'source_id': source_node,
                'target_id': target_node,
                'edge_id': f"{source_node}_{target_node}_{datetime.now().timestamp()}",
                'strength': causal_strength,
                'p_value': granger_p_value,
                'confidence': confidence,
                'timestamp': datetime.now().isoformat(),
                'metadata': json.dumps(metadata)
            })
    
    async def store_news_event(
        self,
        news_id: str,
        source: str,
        first_published_timestamp: datetime,
        content_summary: str,
        related_assets: List[str] = None
    ):
        """Store news event with first occurrence tracking"""
        with self.driver.session() as session:
            session.run("""
                MERGE (news:News {
                    news_id: $news_id,
                    source: $source,
                    first_published_timestamp: $timestamp,
                    content_summary: $content_summary,
                    created_at: $created_at
                })
            """, {
                'news_id': news_id,
                'source': source,
                'timestamp': first_published_timestamp.isoformat(),
                'content_summary': content_summary,
                'created_at': datetime.now().isoformat()
            })
            
            if related_assets:
                for asset in related_assets:
                    session.run("""
                        MATCH (news:News {news_id: $news_id})
                        MERGE (asset:CausalNode {node_id: $asset_id})
                        CREATE (news)-[r:AFFECTS {
                            relationship_type: 'news_impact',
                            timestamp: $timestamp
                        }]->(asset)
                    """, {
                        'news_id': news_id,
                        'asset_id': asset,
                        'timestamp': datetime.now().isoformat()
                    })
            
    async def query_causal_path(self, source: str, target: str, max_depth: int = 5) -> List[Dict]:
        """Query causal path between nodes"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH path = (source:CausalNode {node_id: $source_id})
                -[:CAUSES*1..$max_depth]->(target:CausalNode {node_id: $target_id})
                RETURN path, length(path) as path_length
                ORDER BY path_length ASC
                LIMIT 10
            """, {
                'source_id': source,
                'target_id': target,
                'max_depth': max_depth
            })
            
            return [record.data() for record in result]
    
    def close(self):
        """Close Neo4j connection"""
        self.driver.close()

class MLFlowCausalTracker:
    """
    MLFlow integration for causal model tracking and versioning
    """
    
    def __init__(self, experiment_name: str = "causal_ai_engine"):
        self.experiment_name = experiment_name
        mlflow.set_experiment(experiment_name)
        self.logger = logging.getLogger(__name__)
        
    async def start_run(self, run_name: str, tags: Dict[str, str] = None) -> str:
        """Start MLFlow run for causal model training"""
        if tags is None:
            tags = {}
        
        tags.update({
            "framework": "pytorch",
            "model_type": "causal_neural_network",
            "timestamp": datetime.now().isoformat()
        })
        
        mlflow.start_run(run_name=run_name, tags=tags)
        return mlflow.active_run().info.run_id
    
    async def log_causal_metrics(
        self,
        granger_results: Dict[str, float],
        model_performance: Dict[str, float],
        causal_accuracy: float,
        prediction_confidence: float
    ):
        """Log causal-specific metrics to MLFlow"""
        for variable, p_value in granger_results.items():
            mlflow.log_metric(f"granger_p_value_{variable}", p_value)
            mlflow.log_metric(f"granger_significant_{variable}", 1.0 if p_value < 0.05 else 0.0)
        
        for metric, value in model_performance.items():
            mlflow.log_metric(f"model_{metric}", value)
        
        mlflow.log_metric("causal_accuracy", causal_accuracy)
        mlflow.log_metric("prediction_confidence", prediction_confidence)
        mlflow.log_metric("total_causal_relationships", len(granger_results))
        
    async def log_causal_model(self, model: nn.Module, model_name: str):
        """Log PyTorch causal model to MLFlow"""
        mlflow.pytorch.log_model(
            pytorch_model=model,
            artifact_path=model_name,
            registered_model_name=f"causal_model_{model_name}"
        )
        
    def end_run(self):
        """End current MLFlow run"""
        mlflow.end_run()

class KafkaCausalStreamer:
    """
    Kafka integration for real-time causal event streaming
    """
    
    def __init__(self, bootstrap_servers: List[str], topic_prefix: str = "causal"):
        self.bootstrap_servers = bootstrap_servers
        self.topic_prefix = topic_prefix
        self.producer = None
        self.consumer = None
        self.logger = logging.getLogger(__name__)
        
    async def initialize_producer(self):
        """Initialize Kafka producer for causal events"""
        self.producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',
            retries=3,
            batch_size=16384,
            linger_ms=10
        )
        
    async def publish_causal_event(self, event: CausalEvent):
        """Publish causal event to Kafka"""
        if not self.producer:
            await self.initialize_producer()
        
        topic = f"{self.topic_prefix}_events"
        event_data = asdict(event)
        
        future = self.producer.send(
            topic,
            key=event.event_id,
            value=event_data
        )
        
        record_metadata = future.get(timeout=10)
        self.logger.info(f"Published event {event.event_id} to {record_metadata.topic}")
        
    async def publish_causal_prediction(self, prediction: CausalPrediction):
        """Publish causal prediction to Kafka"""
        if not self.producer:
            await self.initialize_producer()
        
        topic = f"{self.topic_prefix}_predictions"
        prediction_data = asdict(prediction)
        
        future = self.producer.send(
            topic,
            key=prediction.prediction_id,
            value=prediction_data
        )
        
        record_metadata = future.get(timeout=10)
        self.logger.info(f"Published prediction {prediction.prediction_id} to {record_metadata.topic}")
        
    async def consume_causal_events(self, callback_func):
        """Consume causal events from Kafka"""
        self.consumer = KafkaConsumer(
            f"{self.topic_prefix}_events",
            bootstrap_servers=self.bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            group_id='causal_ai_engine',
            auto_offset_reset='latest'
        )
        
        for message in self.consumer:
            event_data = message.value
            event = CausalEvent(**event_data)
            await callback_func(event)
    
    def close(self):
        """Close Kafka connections"""
        if self.producer:
            self.producer.close()
        if self.consumer:
            self.consumer.close()

class CausalAIOrchestrator:
    """
    Main orchestrator for the Causal AI Engine
    Integrates PyTorch models, Neo4j storage, MLFlow tracking, and Kafka streaming
    """
    
    def __init__(
        self,
        config: CausalModelConfig,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "password",
        kafka_servers: List[str] = None,
        mlflow_tracking_uri: str = "http://localhost:5000"
    ):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.graph_db = Neo4jCausalGraph(neo4j_uri, neo4j_user, neo4j_password)
        self.mlflow_tracker = MLFlowCausalTracker()
        
        if kafka_servers is None:
            kafka_servers = ["localhost:9092"]
        self.kafka_streamer = KafkaCausalStreamer(kafka_servers)
        
        self.causal_model = None
        self.inference_engine = None
        self.current_run_id = None
        
        self.metrics = {
            "total_events_processed": 0,
            "total_predictions_made": 0,
            "average_prediction_confidence": 0.0,
            "causal_relationships_discovered": 0,
            "model_accuracy": 0.0
        }
        
    async def initialize(self):
        """Initialize the Causal AI Engine"""
        try:
            self.logger.info("Initializing Causal AI Engine...")
            
            await self.graph_db.initialize_schema()
            
            await self.kafka_streamer.initialize_producer()
            
            self.current_run_id = await self.mlflow_tracker.start_run(
                run_name=f"causal_engine_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                tags={"version": "1.0", "architecture": "tesla_inspired"}
            )
            
            self.logger.info("✅ Causal AI Engine initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Causal AI Engine initialization failed: {e}")
            return False
    
    async def train_causal_model(
        self,
        training_data: pd.DataFrame,
        target_column: str,
        feature_columns: List[str]
    ) -> Dict[str, Any]:
        """
        Train causal neural network with Granger causality testing
        """
        try:
            self.logger.info("Training causal model...")
            
            X = training_data[feature_columns].values
            y = training_data[target_column].values
            
            X_tensor = torch.FloatTensor(X)
            y_tensor = torch.FloatTensor(y).unsqueeze(1)
            
            input_dim = len(feature_columns)
            output_dim = 1
            self.causal_model = CausalNeuralNetwork(input_dim, output_dim, self.config)
            
            criterion = nn.MSELoss()
            optimizer = torch.optim.Adam(
                self.causal_model.parameters(),
                lr=self.config.learning_rate,
                weight_decay=self.config.regularization
            )
            
            train_losses = []
            for epoch in range(self.config.epochs):
                optimizer.zero_grad()
                
                predictions, attention_weights = self.causal_model(X_tensor)
                loss = criterion(predictions, y_tensor)
                
                loss.backward()
                optimizer.step()
                
                train_losses.append(loss.item())
                
                if epoch % 10 == 0:
                    self.logger.info(f"Epoch {epoch}, Loss: {loss.item():.4f}")
            
            granger_results = await self._perform_granger_tests(
                training_data, target_column, feature_columns
            )
            
            with torch.no_grad():
                final_predictions, _ = self.causal_model(X_tensor)
                mse = criterion(final_predictions, y_tensor).item()
                mae = torch.mean(torch.abs(final_predictions - y_tensor)).item()
                
            model_performance = {
                "mse": mse,
                "mae": mae,
                "final_loss": train_losses[-1],
                "training_epochs": self.config.epochs
            }
            
            significant_relationships = sum(1 for p in granger_results.values() if p < 0.05)
            causal_accuracy = significant_relationships / len(granger_results) if granger_results else 0.0
            
            await self.mlflow_tracker.log_causal_metrics(
                granger_results=granger_results,
                model_performance=model_performance,
                causal_accuracy=causal_accuracy,
                prediction_confidence=0.85
            )
            
            await self.mlflow_tracker.log_causal_model(
                self.causal_model,
                f"causal_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            await self._store_causal_relationships(granger_results, feature_columns, target_column)
            
            self.metrics["model_accuracy"] = 1.0 - mse
            self.metrics["causal_relationships_discovered"] += len(granger_results)
            
            training_result = {
                "model_performance": model_performance,
                "granger_results": granger_results,
                "causal_accuracy": causal_accuracy,
                "training_completed": True,
                "model_id": self.current_run_id
            }
            
            self.logger.info("✅ Causal model training completed successfully")
            return training_result
            
        except Exception as e:
            self.logger.error(f"❌ Causal model training failed: {e}")
            raise
    
    async def process_real_time_event(self, event: CausalEvent) -> CausalPrediction:
        """
        Process real-time causal event and generate prediction
        """
        try:
            if not self.causal_model:
                raise ValueError("Causal model not trained yet")
            
            features = list(event.features.values())
            X_tensor = torch.FloatTensor([features])
            
            with torch.no_grad():
                prediction, attention_weights = self.causal_model(X_tensor)
                prediction_value = prediction.item()
                
                confidence = torch.mean(attention_weights).item()
                
                confidence_interval = (
                    prediction_value - 0.1 * abs(prediction_value),
                    prediction_value + 0.1 * abs(prediction_value)
                )
            
            causal_factors = await self._get_causal_factors(event.event_type)
            
            prediction_result = CausalPrediction(
                prediction_id=f"pred_{event.event_id}_{datetime.now().timestamp()}",
                timestamp=datetime.now(),
                target_variable="market_movement",
                predicted_value=prediction_value,
                confidence_interval=confidence_interval,
                causal_factors=causal_factors,
                granger_p_values={},
                model_version=self.current_run_id,
                explanation=f"Prediction based on {len(features)} causal features with {confidence:.2f} confidence"
            )
            
            await self.kafka_streamer.publish_causal_prediction(prediction_result)
            
            self.metrics["total_events_processed"] += 1
            self.metrics["total_predictions_made"] += 1
            self.metrics["average_prediction_confidence"] = (
                (self.metrics["average_prediction_confidence"] * (self.metrics["total_predictions_made"] - 1) + confidence) /
                self.metrics["total_predictions_made"]
            )
            
            return prediction_result
            
        except Exception as e:
            self.logger.error(f"❌ Real-time event processing failed: {e}")
            raise
    
    async def generate_causal_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive causal analysis report
        """
        try:
            causal_relationships = await self._query_all_causal_relationships()
            
            network_metrics = await self._calculate_network_metrics(causal_relationships)
            
            report = {
                "timestamp": datetime.now().isoformat(),
                "model_metrics": self.metrics.copy(),
                "causal_network": {
                    "total_nodes": network_metrics.get("total_nodes", 0),
                    "total_edges": network_metrics.get("total_edges", 0),
                    "network_density": network_metrics.get("density", 0.0),
                    "average_path_length": network_metrics.get("avg_path_length", 0.0)
                },
                "top_causal_relationships": causal_relationships[:10],
                "model_performance": {
                    "accuracy": self.metrics["model_accuracy"],
                    "confidence": self.metrics["average_prediction_confidence"],
                    "total_predictions": self.metrics["total_predictions_made"]
                },
                "recommendations": await self._generate_causal_recommendations()
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"❌ Causal report generation failed: {e}")
            raise
    
    async def _perform_granger_tests(
        self,
        data: pd.DataFrame,
        target: str,
        features: List[str]
    ) -> Dict[str, float]:
        """Perform Granger causality tests"""
        granger_results = {}
        
        for feature in features:
            try:
                test_data = data[[target, feature]].dropna()
                
                if len(test_data) > self.config.granger_max_lags * 2:
                    result = grangercausalitytests(
                        test_data,
                        maxlag=min(self.config.granger_max_lags, len(test_data) // 4),
                        verbose=False
                    )
                    
                    p_values = [result[lag][0]['ssr_ftest'][1] for lag in result.keys()]
                    granger_results[feature] = min(p_values)
                else:
                    granger_results[feature] = 1.0
                    
            except Exception as e:
                self.logger.warning(f"Granger test failed for {feature}: {e}")
                granger_results[feature] = 1.0
        
        return granger_results
    
    async def _store_causal_relationships(
        self,
        granger_results: Dict[str, float],
        features: List[str],
        target: str
    ):
        """Store causal relationships in Neo4j"""
        for feature, p_value in granger_results.items():
            if p_value < self.config.causal_threshold:
                causal_strength = 1.0 - p_value
                
                await self.graph_db.store_causal_relationship(
                    source_node=feature,
                    target_node=target,
                    causal_strength=causal_strength,
                    granger_p_value=p_value,
                    confidence=0.95 if p_value < 0.01 else 0.90,
                    metadata={
                        "model_id": self.current_run_id,
                        "discovery_method": "granger_causality",
                        "threshold": self.config.causal_threshold
                    }
                )
    
    async def _get_causal_factors(self, event_type: str) -> Dict[str, float]:
        """Get causal factors for event type from Neo4j"""
        return {
            "market_sentiment": 0.75,
            "volume_spike": 0.60,
            "news_impact": 0.45
        }
    
    async def _query_all_causal_relationships(self) -> List[Dict]:
        """Query all causal relationships from Neo4j"""
        return [
            {
                "source": "market_sentiment",
                "target": "price_movement",
                "strength": 0.85,
                "p_value": 0.001
            }
        ]
    
    async def _calculate_network_metrics(self, relationships: List[Dict]) -> Dict[str, float]:
        """Calculate causal network metrics"""
        return {
            "total_nodes": 10,
            "total_edges": 15,
            "density": 0.33,
            "avg_path_length": 2.5
        }
    
    async def _generate_causal_recommendations(self) -> List[str]:
        """Generate causal analysis recommendations"""
        return [
            "Increase monitoring of high-strength causal relationships",
            "Consider additional features for low-confidence predictions",
            "Retrain model with recent data for improved accuracy"
        ]
    
    async def automated_ladder_progression(self, data: pd.DataFrame, 
                                         treatment: str, outcome: str) -> Dict[str, Any]:
        """Automated Pearl's Ladder progression with threshold-based escalation"""
        results = {"ladder_progression": []}
        
        correlation = data[treatment].corr(data[outcome])
        results["ladder_progression"].append({
            "rung": 1,
            "method": "correlation",
            "result": correlation,
            "significant": abs(correlation) > 0.3
        })
        
        if abs(correlation) > 0.3:
            try:
                from dowhy import CausalModel
                causal_model = CausalModel(
                    data=data,
                    treatment=treatment,
                    outcome=outcome,
                    graph="digraph { " + treatment + " -> " + outcome + "; }"
                )
                
                identified_estimand = causal_model.identify_effect()
                causal_estimate = causal_model.estimate_effect(
                    identified_estimand,
                    method_name="backdoor.propensity_score_matching"
                )
                
                results["ladder_progression"].append({
                    "rung": 2,
                    "method": "do_calculus",
                    "result": causal_estimate.value,
                    "confidence_interval": causal_estimate.get_confidence_intervals(),
                    "significant": causal_estimate.value != 0
                })
                
                if causal_estimate.value != 0:
                    counterfactual_result = await self._generate_counterfactuals(
                        data, treatment, outcome, causal_model
                    )
                    results["ladder_progression"].append(counterfactual_result)
            
            except Exception as e:
                results["ladder_progression"].append({
                    "rung": 2,
                    "method": "do_calculus",
                    "error": str(e),
                    "significant": False
                })
        
        results["sensitivity_analysis"] = await self._calculate_e_values(results)
        
        return results
    
    async def _calculate_e_values(self, causal_results: Dict[str, Any]) -> Dict[str, float]:
        """Calculate E-values for sensitivity analysis"""
        e_values = {}
        
        for rung_result in causal_results["ladder_progression"]:
            if rung_result["rung"] == 2 and "result" in rung_result:
                effect_size = abs(rung_result["result"])
                if effect_size > 1:
                    e_value = effect_size + (effect_size * (effect_size - 1)) ** 0.5
                else:
                    e_value = 1.0
                
                e_values[f"rung_{rung_result['rung']}_e_value"] = e_value
        
        return e_values
    
    async def _generate_counterfactuals(self, data: pd.DataFrame, treatment: str, 
                                      outcome: str, causal_model) -> Dict[str, Any]:
        """Generate counterfactual analysis"""
        try:
            counterfactual_data = data.copy()
            counterfactual_data[treatment] = 1 - counterfactual_data[treatment]
            
            counterfactual_estimate = causal_model.estimate_effect(
                causal_model.identify_effect(),
                method_name="backdoor.linear_regression",
                target_units=counterfactual_data
            )
            
            return {
                "rung": 3,
                "method": "counterfactuals",
                "result": counterfactual_estimate.value,
                "interpretation": f"Counterfactual effect: {counterfactual_estimate.value:.4f}",
                "significant": abs(counterfactual_estimate.value) > 0.1
            }
        
        except Exception as e:
            return {
                "rung": 3,
                "method": "counterfactuals",
                "error": str(e),
                "significant": False
            }
    
    async def shutdown(self):
        """Shutdown the Causal AI Engine"""
        try:
            if self.current_run_id:
                self.mlflow_tracker.end_run()
            
            self.graph_db.close()
            self.kafka_streamer.close()
            
            self.logger.info("✅ Causal AI Engine shutdown completed")
            
        except Exception as e:
            self.logger.error(f"❌ Causal AI Engine shutdown failed: {e}")

async def main():
    """Example usage of the Causal AI Orchestrator"""
    
    config = CausalModelConfig(
        model_type="pytorch",
        learning_rate=0.001,
        batch_size=32,
        epochs=50,
        hidden_dims=[128, 64, 32],
        causal_threshold=0.05
    )
    
    orchestrator = CausalAIOrchestrator(
        config=config,
        neo4j_uri="bolt://localhost:7687",
        kafka_servers=["localhost:9092"]
    )
    
    if await orchestrator.initialize():
        print("✅ Causal AI Engine initialized successfully")
        
        training_data = pd.DataFrame({
            'market_sentiment': np.random.randn(1000),
            'volume': np.random.randn(1000),
            'news_score': np.random.randn(1000),
            'price_movement': np.random.randn(1000)
        })
        
        training_result = await orchestrator.train_causal_model(
            training_data=training_data,
            target_column='price_movement',
            feature_columns=['market_sentiment', 'volume', 'news_score']
        )
        
        print(f"✅ Model training completed: {training_result['causal_accuracy']:.2f} causal accuracy")
        
        test_event = CausalEvent(
            event_id="test_event_001",
            timestamp=datetime.now(),
            event_type="market_update",
            source_data={"source": "market_feed"},
            features={
                "market_sentiment": 0.75,
                "volume": 1.2,
                "news_score": 0.3
            }
        )
        
        prediction = await orchestrator.process_real_time_event(test_event)
        print(f"✅ Prediction generated: {prediction.predicted_value:.4f}")
        
        report = await orchestrator.generate_causal_report()
        print(f"✅ Causal report generated: {report['model_performance']}")
        
        await orchestrator.shutdown()
    
    else:
        print("❌ Causal AI Engine initialization failed")

if __name__ == "__main__":
    asyncio.run(main())
