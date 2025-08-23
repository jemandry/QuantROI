use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};

use crate::enhanced_confidence_engine::EventSourceData;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConflictAnalysis {
    pub conflict_id: String,
    pub event_type: String,
    pub sources_involved: Vec<String>,
    pub conflict_severity: ConflictSeverity,
    pub resolution_strategy: ResolutionStrategy,
    pub resolution_confidence: f32,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ConflictSeverity {
    Low,      // < 10% variance
    Medium,   // 10-30% variance
    High,     // 30-50% variance
    Critical, // > 50% variance
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ResolutionStrategy {
    TrustMostReliable,
    WeightedConsensus,
    TemporalPriority,
    SourceTypeHierarchy,
    BayesianInference,
    OutlierElimination,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConflictResolutionRule {
    pub rule_id: String,
    pub event_type_pattern: String,
    pub source_type_priorities: HashMap<String, u8>,
    pub variance_threshold: f32,
    pub preferred_strategy: ResolutionStrategy,
    pub confidence_boost: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResolutionHistory {
    pub resolution_id: String,
    pub original_conflict: ConflictAnalysis,
    pub applied_strategy: ResolutionStrategy,
    pub final_value: serde_json::Value,
    pub confidence_score: f32,
    pub validation_outcome: Option<ValidationOutcome>,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationOutcome {
    pub is_correct: bool,
    pub actual_value: Option<serde_json::Value>,
    pub accuracy_score: f32,
    pub validation_timestamp: DateTime<Utc>,
}

pub struct CrossSourceResolver {
    resolution_rules: Arc<RwLock<HashMap<String, ConflictResolutionRule>>>,
    resolution_history: Arc<RwLock<Vec<ResolutionHistory>>>,
    source_performance: Arc<RwLock<HashMap<String, SourcePerformanceMetrics>>>,
    bayesian_model: Arc<RwLock<BayesianConflictModel>>,
}

#[derive(Debug, Clone)]
pub struct SourcePerformanceMetrics {
    pub source_id: String,
    pub total_conflicts: u32,
    pub correct_resolutions: u32,
    pub accuracy_rate: f32,
    pub average_confidence: f32,
    pub last_updated: DateTime<Utc>,
}

#[allow(dead_code)]
#[derive(Debug)]
pub struct BayesianConflictModel {
    source_priors: HashMap<String, f32>,
    conflict_patterns: HashMap<String, ConflictPattern>,
    model_confidence: f32,
}

#[derive(Debug, Clone)]
pub struct ConflictPattern {
    pub pattern_id: String,
    pub source_combinations: Vec<String>,
    pub typical_variance: f32,
    pub resolution_success_rate: f32,
    pub occurrence_frequency: u32,
}

impl CrossSourceResolver {
    pub fn new() -> Self {
        let mut resolver = Self {
            resolution_rules: Arc::new(RwLock::new(HashMap::new())),
            resolution_history: Arc::new(RwLock::new(Vec::new())),
            source_performance: Arc::new(RwLock::new(HashMap::new())),
            bayesian_model: Arc::new(RwLock::new(BayesianConflictModel::new())),
        };
        
        resolver.initialize_default_rules();
        resolver
    }
    
    fn initialize_default_rules(&mut self) {
        let _default_rules = vec![
            ConflictResolutionRule {
                rule_id: "market_data_priority".to_string(),
                event_type_pattern: "price_*".to_string(),
                source_type_priorities: [
                    ("MarketData".to_string(), 10),
                    ("NewsAPI".to_string(), 7),
                    ("SocialMedia".to_string(), 3),
                ].iter().cloned().collect(),
                variance_threshold: 0.05,
                preferred_strategy: ResolutionStrategy::SourceTypeHierarchy,
                confidence_boost: 0.15,
            },
            ConflictResolutionRule {
                rule_id: "news_consensus".to_string(),
                event_type_pattern: "news_*".to_string(),
                source_type_priorities: [
                    ("NewsAPI".to_string(), 10),
                    ("SocialMedia".to_string(), 6),
                    ("MarketData".to_string(), 4),
                ].iter().cloned().collect(),
                variance_threshold: 0.3,
                preferred_strategy: ResolutionStrategy::WeightedConsensus,
                confidence_boost: 0.1,
            },
            ConflictResolutionRule {
                rule_id: "high_variance_outlier".to_string(),
                event_type_pattern: "*".to_string(),
                source_type_priorities: HashMap::new(),
                variance_threshold: 0.5,
                preferred_strategy: ResolutionStrategy::OutlierElimination,
                confidence_boost: 0.2,
            },
        ];
        
        tokio::spawn(async move {
        });
    }
    
    pub async fn analyze_conflict(&self, sources: &[EventSourceData], event_type: &str) -> ConflictAnalysis {
        let conflict_severity = self.calculate_conflict_severity(sources);
        let resolution_strategy = self.select_resolution_strategy(sources, event_type, &conflict_severity).await;
        
        ConflictAnalysis {
            conflict_id: uuid::Uuid::new_v4().to_string(),
            event_type: event_type.to_string(),
            sources_involved: sources.iter().map(|s| s.source.source_id.clone()).collect(),
            conflict_severity,
            resolution_strategy: resolution_strategy.clone(),
            resolution_confidence: self.calculate_resolution_confidence(sources, &resolution_strategy).await,
            timestamp: Utc::now(),
        }
    }
    
    fn calculate_conflict_severity(&self, sources: &[EventSourceData]) -> ConflictSeverity {
        if sources.len() < 2 {
            return ConflictSeverity::Low;
        }
        
        let values: Vec<f32> = sources.iter().map(|s| s.normalized_value).collect();
        let mean = values.iter().sum::<f32>() / values.len() as f32;
        let variance = values.iter()
            .map(|v| (v - mean).powi(2))
            .sum::<f32>() / values.len() as f32;
        
        let coefficient_of_variation = if mean != 0.0 {
            variance.sqrt() / mean.abs()
        } else {
            variance.sqrt()
        };
        
        match coefficient_of_variation {
            cv if cv < 0.05 => ConflictSeverity::Low,
            cv if cv < 0.15 => ConflictSeverity::Medium,
            cv if cv < 0.35 => ConflictSeverity::High,
            _ => ConflictSeverity::Critical,
        }
    }
    
    async fn select_resolution_strategy(
        &self,
        _sources: &[EventSourceData],
        event_type: &str,
        severity: &ConflictSeverity,
    ) -> ResolutionStrategy {
        let rules = self.resolution_rules.read().await;
        
        for rule in rules.values() {
            if self.matches_pattern(&rule.event_type_pattern, event_type) {
                return rule.preferred_strategy.clone();
            }
        }
        
        match severity {
            ConflictSeverity::Low => ResolutionStrategy::WeightedConsensus,
            ConflictSeverity::Medium => ResolutionStrategy::TrustMostReliable,
            ConflictSeverity::High => ResolutionStrategy::BayesianInference,
            ConflictSeverity::Critical => ResolutionStrategy::OutlierElimination,
        }
    }
    
    fn matches_pattern(&self, pattern: &str, event_type: &str) -> bool {
        if pattern == "*" {
            return true;
        }
        
        if pattern.ends_with('*') {
            let prefix = pattern.strip_suffix('*').unwrap();
            return event_type.starts_with(prefix);
        }
        
        if pattern.starts_with('*') {
            let suffix = pattern.strip_prefix('*').unwrap();
            return event_type.ends_with(suffix);
        }
        
        pattern == event_type
    }
    
    async fn calculate_resolution_confidence(
        &self,
        sources: &[EventSourceData],
        strategy: &ResolutionStrategy,
    ) -> f32 {
        let base_confidence = match strategy {
            ResolutionStrategy::TrustMostReliable => {
                sources.iter()
                    .map(|s| s.source.reliability_score)
                    .fold(0.0, f32::max)
            },
            ResolutionStrategy::WeightedConsensus => {
                let avg_reliability: f32 = sources.iter()
                    .map(|s| s.source.reliability_score)
                    .sum::<f32>() / sources.len() as f32;
                avg_reliability * 0.9 // Slight penalty for consensus
            },
            ResolutionStrategy::BayesianInference => {
                let model = self.bayesian_model.read().await;
                model.calculate_confidence(sources)
            },
            _ => 0.7, // Default confidence for other strategies
        };
        
        let diversity_bonus = if sources.len() > 2 { 0.1 } else { 0.0 };
        
        (base_confidence + diversity_bonus).min(1.0)
    }
    
    pub async fn resolve_conflict(
        &self,
        sources: &[EventSourceData],
        strategy: &ResolutionStrategy,
    ) -> Result<(f32, serde_json::Value), String> {
        match strategy {
            ResolutionStrategy::TrustMostReliable => self.trust_most_reliable(sources),
            ResolutionStrategy::WeightedConsensus => self.weighted_consensus(sources),
            ResolutionStrategy::TemporalPriority => self.temporal_priority(sources),
            ResolutionStrategy::SourceTypeHierarchy => self.source_type_hierarchy(sources).await,
            ResolutionStrategy::BayesianInference => self.bayesian_inference(sources).await,
            ResolutionStrategy::OutlierElimination => self.outlier_elimination(sources),
        }
    }
    
    fn trust_most_reliable(&self, sources: &[EventSourceData]) -> Result<(f32, serde_json::Value), String> {
        if sources.is_empty() {
            return Err("No sources provided".to_string());
        }
        
        let best_source = sources.iter()
            .max_by(|a, b| a.source.reliability_score.partial_cmp(&b.source.reliability_score).unwrap())
            .unwrap();
        
        Ok((best_source.source.reliability_score, best_source.raw_value.clone()))
    }
    
    fn weighted_consensus(&self, sources: &[EventSourceData]) -> Result<(f32, serde_json::Value), String> {
        if sources.is_empty() {
            return Err("No sources provided".to_string());
        }
        
        let total_weight: f32 = sources.iter()
            .map(|s| s.source.reliability_score * s.source_confidence)
            .sum();
        
        if total_weight == 0.0 {
            return self.trust_most_reliable(sources);
        }
        
        let weighted_value: f32 = sources.iter()
            .map(|s| s.normalized_value * s.source.reliability_score * s.source_confidence)
            .sum::<f32>() / total_weight;
        
        let confidence = total_weight / sources.len() as f32;
        
        Ok((confidence.min(1.0), serde_json::Value::Number(
            serde_json::Number::from_f64(weighted_value as f64).unwrap()
        )))
    }
    
    fn temporal_priority(&self, sources: &[EventSourceData]) -> Result<(f32, serde_json::Value), String> {
        if sources.is_empty() {
            return Err("No sources provided".to_string());
        }
        
        let most_recent = sources.iter()
            .max_by_key(|s| s.source.last_updated)
            .unwrap();
        
        let age_penalty = self.calculate_age_penalty(&most_recent.source.last_updated);
        let confidence = most_recent.source.reliability_score * (1.0 - age_penalty);
        
        Ok((confidence, most_recent.raw_value.clone()))
    }
    
    fn calculate_age_penalty(&self, timestamp: &DateTime<Utc>) -> f32 {
        let age = Utc::now().signed_duration_since(*timestamp);
        let age_minutes = age.num_minutes() as f32;
        
        (age_minutes / 60.0).min(0.5)
    }
    
    async fn source_type_hierarchy(&self, sources: &[EventSourceData]) -> Result<(f32, serde_json::Value), String> {
        let rules = self.resolution_rules.read().await;
        
        let mut best_source = None;
        let mut best_priority = 0u8;
        
        for source in sources {
            let source_type = format!("{:?}", source.source.source_type);
            for rule in rules.values() {
                if let Some(&priority) = rule.source_type_priorities.get(&source_type) {
                    if priority > best_priority {
                        best_priority = priority;
                        best_source = Some(source);
                    }
                }
            }
        }
        
        if let Some(source) = best_source {
            let confidence = source.source.reliability_score * (best_priority as f32 / 10.0);
            Ok((confidence, source.raw_value.clone()))
        } else {
            self.trust_most_reliable(sources)
        }
    }
    
    async fn bayesian_inference(&self, sources: &[EventSourceData]) -> Result<(f32, serde_json::Value), String> {
        let model = self.bayesian_model.read().await;
        model.infer_best_value(sources)
    }
    
    fn outlier_elimination(&self, sources: &[EventSourceData]) -> Result<(f32, serde_json::Value), String> {
        if sources.len() < 3 {
            return self.weighted_consensus(sources);
        }
        
        let values: Vec<f32> = sources.iter().map(|s| s.normalized_value).collect();
        let median = self.calculate_median(&values);
        
        let filtered_sources: Vec<&EventSourceData> = sources.iter()
            .filter(|s| {
                let deviation = (s.normalized_value - median).abs();
                deviation < 2.0 * self.calculate_std_dev(&values)
            })
            .collect();
        
        if filtered_sources.is_empty() {
            return self.trust_most_reliable(sources);
        }
        
        let filtered_owned: Vec<EventSourceData> = filtered_sources.into_iter().cloned().collect();
        self.weighted_consensus(&filtered_owned)
    }
    
    fn calculate_median(&self, values: &[f32]) -> f32 {
        let mut sorted = values.to_vec();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
        
        let len = sorted.len();
        if len % 2 == 0 {
            (sorted[len / 2 - 1] + sorted[len / 2]) / 2.0
        } else {
            sorted[len / 2]
        }
    }
    
    fn calculate_std_dev(&self, values: &[f32]) -> f32 {
        let mean = values.iter().sum::<f32>() / values.len() as f32;
        let variance = values.iter()
            .map(|v| (v - mean).powi(2))
            .sum::<f32>() / values.len() as f32;
        variance.sqrt()
    }
    
    pub async fn record_resolution(&self, resolution: ResolutionHistory) {
        let mut history = self.resolution_history.write().await;
        history.push(resolution.clone());
        
        self.update_source_performance(&resolution).await;
    }
    
    async fn update_source_performance(&self, resolution: &ResolutionHistory) {
        let mut performance = self.source_performance.write().await;
        
        for source_id in &resolution.original_conflict.sources_involved {
            let metrics = performance.entry(source_id.clone())
                .or_insert_with(|| SourcePerformanceMetrics {
                    source_id: source_id.clone(),
                    total_conflicts: 0,
                    correct_resolutions: 0,
                    accuracy_rate: 0.0,
                    average_confidence: 0.0,
                    last_updated: Utc::now(),
                });
            
            metrics.total_conflicts += 1;
            
            if let Some(validation) = &resolution.validation_outcome {
                if validation.is_correct {
                    metrics.correct_resolutions += 1;
                }
            }
            
            metrics.accuracy_rate = metrics.correct_resolutions as f32 / metrics.total_conflicts as f32;
            metrics.last_updated = Utc::now();
        }
    }
    
    pub async fn get_source_performance(&self, source_id: &str) -> Option<SourcePerformanceMetrics> {
        let performance = self.source_performance.read().await;
        performance.get(source_id).cloned()
    }
}

impl Default for BayesianConflictModel {
    fn default() -> Self {
        Self::new()
    }
}

impl BayesianConflictModel {
    pub fn new() -> Self {
        Self {
            source_priors: HashMap::new(),
            conflict_patterns: HashMap::new(),
            model_confidence: 0.5,
        }
    }
    
    pub fn calculate_confidence(&self, sources: &[EventSourceData]) -> f32 {
        if sources.is_empty() {
            return 0.0;
        }
        
        let mut total_prior = 0.0;
        let mut count = 0;
        
        for source in sources {
            if let Some(&prior) = self.source_priors.get(&source.source.source_id) {
                total_prior += prior * source.source.reliability_score;
                count += 1;
            }
        }
        
        if count > 0 {
            (total_prior / count as f32) * self.model_confidence
        } else {
            0.5 // Default confidence when no priors available
        }
    }
    
    pub fn infer_best_value(&self, sources: &[EventSourceData]) -> Result<(f32, serde_json::Value), String> {
        if sources.is_empty() {
            return Err("No sources provided".to_string());
        }
        
        let mut best_source = None;
        let mut best_posterior = 0.0;
        
        for source in sources {
            let prior = self.source_priors.get(&source.source.source_id).unwrap_or(&0.5);
            let likelihood = source.source.reliability_score * source.source_confidence;
            let posterior = prior * likelihood;
            
            if posterior > best_posterior {
                best_posterior = posterior;
                best_source = Some(source);
            }
        }
        
        if let Some(source) = best_source {
            Ok((best_posterior, source.raw_value.clone()))
        } else {
            Err("Could not determine best source".to_string())
        }
    }
}

impl Default for CrossSourceResolver {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::enhanced_confidence_engine::{EventSource, SourceType};
    
    #[tokio::test]
    async fn test_conflict_analysis() {
        let resolver = CrossSourceResolver::new();
        
        let sources = vec![
            EventSourceData {
                source: EventSource {
                    source_id: "source1".to_string(),
                    source_type: SourceType::MarketData,
                    reliability_score: 0.9,
                    latency_ms: 50,
                    last_updated: Utc::now(),
                    historical_accuracy: 0.85,
                },
                raw_value: serde_json::Value::Number(serde_json::Number::from(100)),
                normalized_value: 100.0,
                source_confidence: 0.9,
                timeliness_score: 0.95,
            },
            EventSourceData {
                source: EventSource {
                    source_id: "source2".to_string(),
                    source_type: SourceType::NewsAPI,
                    reliability_score: 0.7,
                    latency_ms: 200,
                    last_updated: Utc::now(),
                    historical_accuracy: 0.75,
                },
                raw_value: serde_json::Value::Number(serde_json::Number::from(150)),
                normalized_value: 150.0,
                source_confidence: 0.8,
                timeliness_score: 0.8,
            },
        ];
        
        let analysis = resolver.analyze_conflict(&sources, "price_update").await;
        
        assert!(!analysis.conflict_id.is_empty());
        assert_eq!(analysis.event_type, "price_update");
        assert_eq!(analysis.sources_involved.len(), 2);
        assert!(matches!(analysis.conflict_severity, ConflictSeverity::High));
    }
    
    #[tokio::test]
    async fn test_weighted_consensus_resolution() {
        let resolver = CrossSourceResolver::new();
        
        let sources = vec![
            EventSourceData {
                source: EventSource {
                    source_id: "source1".to_string(),
                    source_type: SourceType::MarketData,
                    reliability_score: 0.9,
                    latency_ms: 50,
                    last_updated: Utc::now(),
                    historical_accuracy: 0.85,
                },
                raw_value: serde_json::Value::Number(serde_json::Number::from(100)),
                normalized_value: 100.0,
                source_confidence: 0.9,
                timeliness_score: 0.95,
            },
            EventSourceData {
                source: EventSource {
                    source_id: "source2".to_string(),
                    source_type: SourceType::NewsAPI,
                    reliability_score: 0.7,
                    latency_ms: 200,
                    last_updated: Utc::now(),
                    historical_accuracy: 0.75,
                },
                raw_value: serde_json::Value::Number(serde_json::Number::from(110)),
                normalized_value: 110.0,
                source_confidence: 0.8,
                timeliness_score: 0.8,
            },
        ];
        
        let result = resolver.resolve_conflict(&sources, &ResolutionStrategy::WeightedConsensus).await;
        
        assert!(result.is_ok());
        let (confidence, _value) = result.unwrap();
        assert!(confidence > 0.0);
        assert!(confidence <= 1.0);
    }
}
