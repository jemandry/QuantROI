use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CausalNode {
    pub node_id: String,
    pub node_type: CausalNodeType,
    pub temporal_weight: f32,
    pub confidence_score: f32,
    pub decay_factor: f32,
    pub created_at: DateTime<Utc>,
    pub last_updated: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum CausalNodeType {
    ExogenousEvent,
    MediatorVariable,
    OutcomeVariable,
    ConfounderVariable,
    InstrumentalVariable,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CausalEdge {
    pub edge_id: String,
    pub source_node: String,
    pub target_node: String,
    pub causal_strength: f32,
    pub temporal_lag: i64,
    pub decay_rate: f32,
    pub confidence_interval: (f32, f32),
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TemporalDecayModel {
    pub decay_rate: f32,
    pub half_life_ms: i64,
    pub minimum_weight: f32,
    pub decay_function: DecayFunction,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DecayFunction {
    Exponential,
    Linear,
    Logarithmic,
    PowerLaw,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SemanticAnalyzer {
    pub embeddings_cache: HashMap<String, Vec<f32>>,
    pub similarity_threshold: f32,
    pub embedding_dimension: usize,
    pub model_name: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LLMCausalExtractor {
    pub model_endpoint: String,
    pub api_key: Option<String>,
    pub max_tokens: u32,
    pub temperature: f32,
    pub extraction_prompts: HashMap<String, String>,
}

#[allow(dead_code)]
pub struct AICausalGraphBuilder {
    temporal_decay_model: TemporalDecayModel,
    semantic_analyzer: SemanticAnalyzer,
    llm_integration: LLMCausalExtractor,
    causal_graphs: Arc<RwLock<HashMap<String, CausalGraph>>>,
    node_registry: Arc<RwLock<HashMap<String, CausalNode>>>,
    edge_registry: Arc<RwLock<HashMap<String, CausalEdge>>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CausalGraph {
    pub graph_id: String,
    pub nodes: HashMap<String, CausalNode>,
    pub edges: HashMap<String, CausalEdge>,
    pub temporal_window: i64,
    pub confidence_threshold: f32,
    pub created_at: DateTime<Utc>,
    pub last_updated: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CausalInsight {
    pub insight_id: String,
    pub insight_type: InsightType,
    pub description: String,
    pub confidence_score: f32,
    pub supporting_evidence: Vec<String>,
    pub temporal_context: TemporalContext,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum InsightType {
    DirectCausation,
    IndirectCausation,
    ConfoundingDetected,
    TemporalPattern,
    AnomalousRelation,
    CausalChain,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TemporalContext {
    pub time_window_start: DateTime<Utc>,
    pub time_window_end: DateTime<Utc>,
    pub lag_duration_ms: i64,
    pub seasonal_pattern: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphBuildRequest {
    pub session_id: String,
    pub data_sources: Vec<String>,
    pub temporal_window_hours: i64,
    pub confidence_threshold: f32,
    pub include_semantic_analysis: bool,
    pub use_llm_extraction: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphBuildResult {
    pub graph_id: String,
    pub nodes_created: usize,
    pub edges_created: usize,
    pub insights_generated: Vec<CausalInsight>,
    pub build_duration_ms: i64,
    pub confidence_metrics: ConfidenceMetrics,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfidenceMetrics {
    pub overall_confidence: f32,
    pub node_confidence_distribution: HashMap<String, f32>,
    pub edge_confidence_distribution: HashMap<String, f32>,
    pub temporal_consistency_score: f32,
}

impl Default for TemporalDecayModel {
    fn default() -> Self {
        Self {
            decay_rate: 0.1,
            half_life_ms: 3600000, // 1 hour
            minimum_weight: 0.01,
            decay_function: DecayFunction::Exponential,
        }
    }
}

impl Default for SemanticAnalyzer {
    fn default() -> Self {
        Self {
            embeddings_cache: HashMap::new(),
            similarity_threshold: 0.7,
            embedding_dimension: 384,
            model_name: "sentence-transformers/all-MiniLM-L6-v2".to_string(),
        }
    }
}

impl Default for LLMCausalExtractor {
    fn default() -> Self {
        Self {
            model_endpoint: "https://api.openai.com/v1/chat/completions".to_string(),
            api_key: None,
            max_tokens: 1000,
            temperature: 0.3,
            extraction_prompts: HashMap::new(),
        }
    }
}

impl AICausalGraphBuilder {
    pub fn new() -> Self {
        Self {
            temporal_decay_model: TemporalDecayModel::default(),
            semantic_analyzer: SemanticAnalyzer::default(),
            llm_integration: LLMCausalExtractor::default(),
            causal_graphs: Arc::new(RwLock::new(HashMap::new())),
            node_registry: Arc::new(RwLock::new(HashMap::new())),
            edge_registry: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub async fn build_causal_graph(&self, request: GraphBuildRequest) -> Result<GraphBuildResult, String> {
        let start_time = std::time::Instant::now();
        let graph_id = format!("graph_{}_{}", request.session_id, chrono::Utc::now().timestamp());
        
        let mut nodes = HashMap::new();
        let mut edges = HashMap::new();

        for source in &request.data_sources {
            let extracted_nodes = self.extract_nodes_from_source(source, &request).await?;
            for node in extracted_nodes {
                nodes.insert(node.node_id.clone(), node);
            }
        }

        let potential_edges = self.identify_causal_relationships(&nodes, &request).await?;
        for edge in potential_edges {
            if edge.causal_strength >= request.confidence_threshold {
                edges.insert(edge.edge_id.clone(), edge);
            }
        }

        self.apply_temporal_decay(&mut nodes, &mut edges).await;

        let insights = self.generate_causal_insights(&nodes, &edges).await?;

        let graph = CausalGraph {
            graph_id: graph_id.clone(),
            nodes: nodes.clone(),
            edges: edges.clone(),
            temporal_window: request.temporal_window_hours * 3600000, // Convert to ms
            confidence_threshold: request.confidence_threshold,
            created_at: chrono::Utc::now(),
            last_updated: chrono::Utc::now(),
        };

        {
            let mut graphs = self.causal_graphs.write().await;
            graphs.insert(graph_id.clone(), graph);
        }

        let build_duration = start_time.elapsed().as_millis() as i64;
        
        Ok(GraphBuildResult {
            graph_id,
            nodes_created: nodes.len(),
            edges_created: edges.len(),
            insights_generated: insights,
            build_duration_ms: build_duration,
            confidence_metrics: self.calculate_confidence_metrics(&nodes, &edges).await,
        })
    }

    async fn extract_nodes_from_source(&self, source: &str, _request: &GraphBuildRequest) -> Result<Vec<CausalNode>, String> {
        let mut nodes = Vec::new();
        
        match source {
            "market_data" => {
                nodes.push(CausalNode {
                    node_id: format!("market_price_{}", chrono::Utc::now().timestamp()),
                    node_type: CausalNodeType::ExogenousEvent,
                    temporal_weight: 1.0,
                    confidence_score: 0.9,
                    decay_factor: self.temporal_decay_model.decay_rate,
                    created_at: chrono::Utc::now(),
                    last_updated: chrono::Utc::now(),
                });
            },
            "news_sentiment" => {
                nodes.push(CausalNode {
                    node_id: format!("sentiment_score_{}", chrono::Utc::now().timestamp()),
                    node_type: CausalNodeType::MediatorVariable,
                    temporal_weight: 0.8,
                    confidence_score: 0.7,
                    decay_factor: self.temporal_decay_model.decay_rate,
                    created_at: chrono::Utc::now(),
                    last_updated: chrono::Utc::now(),
                });
            },
            "trading_volume" => {
                nodes.push(CausalNode {
                    node_id: format!("volume_spike_{}", chrono::Utc::now().timestamp()),
                    node_type: CausalNodeType::OutcomeVariable,
                    temporal_weight: 0.9,
                    confidence_score: 0.85,
                    decay_factor: self.temporal_decay_model.decay_rate,
                    created_at: chrono::Utc::now(),
                    last_updated: chrono::Utc::now(),
                });
            },
            _ => return Err(format!("Unknown data source: {}", source)),
        }

        Ok(nodes)
    }

    async fn identify_causal_relationships(&self, nodes: &HashMap<String, CausalNode>, _request: &GraphBuildRequest) -> Result<Vec<CausalEdge>, String> {
        let mut edges = Vec::new();
        
        let node_ids: Vec<_> = nodes.keys().collect();
        for i in 0..node_ids.len() {
            for j in (i+1)..node_ids.len() {
                let source_id = node_ids[i];
                let target_id = node_ids[j];
                
                let causal_strength = self.calculate_causal_strength(
                    &nodes[source_id], 
                    &nodes[target_id]
                ).await;
                
                if causal_strength > 0.1 {
                    edges.push(CausalEdge {
                        edge_id: format!("edge_{}_{}", source_id, target_id),
                        source_node: source_id.clone(),
                        target_node: target_id.clone(),
                        causal_strength,
                        temporal_lag: 300000, // 5 minutes in ms
                        decay_rate: self.temporal_decay_model.decay_rate,
                        confidence_interval: (causal_strength - 0.1, causal_strength + 0.1),
                        created_at: chrono::Utc::now(),
                    });
                }
            }
        }

        Ok(edges)
    }

    async fn calculate_causal_strength(&self, source: &CausalNode, target: &CausalNode) -> f32 {
        let type_compatibility = match (&source.node_type, &target.node_type) {
            (CausalNodeType::ExogenousEvent, CausalNodeType::MediatorVariable) => 0.8,
            (CausalNodeType::MediatorVariable, CausalNodeType::OutcomeVariable) => 0.9,
            (CausalNodeType::ExogenousEvent, CausalNodeType::OutcomeVariable) => 0.6,
            _ => 0.3,
        };
        
        let confidence_factor = (source.confidence_score + target.confidence_score) / 2.0;
        let temporal_factor = (source.temporal_weight + target.temporal_weight) / 2.0;
        
        type_compatibility * confidence_factor * temporal_factor
    }

    async fn apply_temporal_decay(&self, nodes: &mut HashMap<String, CausalNode>, edges: &mut HashMap<String, CausalEdge>) {
        let now = chrono::Utc::now();
        
        for node in nodes.values_mut() {
            let age_ms = (now - node.created_at).num_milliseconds();
            let decay_factor = match self.temporal_decay_model.decay_function {
                DecayFunction::Exponential => {
                    (-self.temporal_decay_model.decay_rate * age_ms as f32 / 1000.0).exp()
                },
                DecayFunction::Linear => {
                    1.0 - (age_ms as f32 / self.temporal_decay_model.half_life_ms as f32).min(1.0)
                },
                _ => 1.0, // Simplified for other functions
            };
            
            node.temporal_weight *= decay_factor.max(self.temporal_decay_model.minimum_weight);
        }
        
        for edge in edges.values_mut() {
            let age_ms = (now - edge.created_at).num_milliseconds();
            let decay_factor = (-self.temporal_decay_model.decay_rate * age_ms as f32 / 1000.0).exp();
            edge.causal_strength *= decay_factor.max(self.temporal_decay_model.minimum_weight);
        }
    }

    async fn generate_causal_insights(&self, nodes: &HashMap<String, CausalNode>, edges: &HashMap<String, CausalEdge>) -> Result<Vec<CausalInsight>, String> {
        let mut insights = Vec::new();
        
        for edge in edges.values() {
            if edge.causal_strength > 0.8 {
                insights.push(CausalInsight {
                    insight_id: format!("insight_{}", chrono::Utc::now().timestamp_nanos_opt().unwrap_or(0)),
                    insight_type: InsightType::DirectCausation,
                    description: format!("Strong causal relationship detected between {} and {}", 
                                       edge.source_node, edge.target_node),
                    confidence_score: edge.causal_strength,
                    supporting_evidence: vec![edge.edge_id.clone()],
                    temporal_context: TemporalContext {
                        time_window_start: edge.created_at - chrono::Duration::hours(1),
                        time_window_end: edge.created_at,
                        lag_duration_ms: edge.temporal_lag,
                        seasonal_pattern: None,
                    },
                    created_at: chrono::Utc::now(),
                });
            }
        }
        
        let high_confidence_nodes: Vec<_> = nodes.values()
            .filter(|n| n.confidence_score > 0.9)
            .collect();
            
        if high_confidence_nodes.len() > 2 {
            insights.push(CausalInsight {
                insight_id: format!("insight_{}", chrono::Utc::now().timestamp_nanos_opt().unwrap_or(0)),
                insight_type: InsightType::ConfoundingDetected,
                description: "Multiple high-confidence variables detected - potential confounding".to_string(),
                confidence_score: 0.7,
                supporting_evidence: high_confidence_nodes.iter().map(|n| n.node_id.clone()).collect(),
                temporal_context: TemporalContext {
                    time_window_start: chrono::Utc::now() - chrono::Duration::hours(1),
                    time_window_end: chrono::Utc::now(),
                    lag_duration_ms: 0,
                    seasonal_pattern: None,
                },
                created_at: chrono::Utc::now(),
            });
        }

        Ok(insights)
    }

    async fn calculate_confidence_metrics(&self, nodes: &HashMap<String, CausalNode>, edges: &HashMap<String, CausalEdge>) -> ConfidenceMetrics {
        let overall_confidence = if !nodes.is_empty() && !edges.is_empty() {
            let node_avg = nodes.values().map(|n| n.confidence_score).sum::<f32>() / nodes.len() as f32;
            let edge_avg = edges.values().map(|e| e.causal_strength).sum::<f32>() / edges.len() as f32;
            (node_avg + edge_avg) / 2.0
        } else {
            0.0
        };

        let node_confidence_distribution = nodes.iter()
            .map(|(id, node)| (id.clone(), node.confidence_score))
            .collect();

        let edge_confidence_distribution = edges.iter()
            .map(|(id, edge)| (id.clone(), edge.causal_strength))
            .collect();

        let temporal_consistency_score = self.calculate_temporal_consistency(nodes, edges).await;

        ConfidenceMetrics {
            overall_confidence,
            node_confidence_distribution,
            edge_confidence_distribution,
            temporal_consistency_score,
        }
    }

    async fn calculate_temporal_consistency(&self, _nodes: &HashMap<String, CausalNode>, edges: &HashMap<String, CausalEdge>) -> f32 {
        if edges.is_empty() {
            return 1.0;
        }

        let temporal_lags: Vec<i64> = edges.values().map(|e| e.temporal_lag).collect();
        let avg_lag = temporal_lags.iter().sum::<i64>() as f32 / temporal_lags.len() as f32;
        
        let variance = temporal_lags.iter()
            .map(|&lag| (lag as f32 - avg_lag).powi(2))
            .sum::<f32>() / temporal_lags.len() as f32;
        
        1.0 / (1.0 + variance / 1000000.0) // Normalize by 1 second in ms
    }

    pub async fn get_causal_graph(&self, graph_id: &str) -> Option<CausalGraph> {
        let graphs = self.causal_graphs.read().await;
        graphs.get(graph_id).cloned()
    }

    pub async fn get_causal_insights(&self, graph_id: &str) -> Result<Vec<CausalInsight>, String> {
        let graph = self.get_causal_graph(graph_id).await
            .ok_or_else(|| format!("Graph not found: {}", graph_id))?;
        
        self.generate_causal_insights(&graph.nodes, &graph.edges).await
    }

    pub async fn update_semantic_similarity(&self, _node_id: &str, _embedding: Vec<f32>) -> Result<(), String> {
        Ok(())
    }

    pub async fn extract_causal_relations_with_llm(&self, _text_data: &str) -> Result<Vec<CausalEdge>, String> {
        Ok(Vec::new())
    }
}

impl Default for AICausalGraphBuilder {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_ai_causal_graph_builder_creation() {
        let builder = AICausalGraphBuilder::new();
        assert_eq!(builder.temporal_decay_model.decay_rate, 0.1);
    }

    #[tokio::test]
    async fn test_causal_graph_building() {
        let builder = AICausalGraphBuilder::new();
        
        let request = GraphBuildRequest {
            session_id: "test_session".to_string(),
            data_sources: vec!["market_data".to_string(), "news_sentiment".to_string()],
            temporal_window_hours: 24,
            confidence_threshold: 0.5,
            include_semantic_analysis: true,
            use_llm_extraction: false,
        };

        let result = builder.build_causal_graph(request).await;
        assert!(result.is_ok());
        
        let graph_result = result.unwrap();
        assert!(graph_result.nodes_created > 0);
        assert!(!graph_result.graph_id.is_empty());
    }

    #[tokio::test]
    async fn test_temporal_decay_application() {
        let builder = AICausalGraphBuilder::new();
        
        let mut nodes = HashMap::new();
        nodes.insert("test_node".to_string(), CausalNode {
            node_id: "test_node".to_string(),
            node_type: CausalNodeType::ExogenousEvent,
            temporal_weight: 1.0,
            confidence_score: 0.9,
            decay_factor: 0.1,
            created_at: chrono::Utc::now() - chrono::Duration::hours(1),
            last_updated: chrono::Utc::now(),
        });

        let mut edges = HashMap::new();
        
        builder.apply_temporal_decay(&mut nodes, &mut edges).await;
        
        let node = nodes.get("test_node").unwrap();
        assert!(node.temporal_weight < 1.0); // Should have decayed
    }
}
