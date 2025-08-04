use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventSource {
    pub source_id: String,
    pub source_type: SourceType,
    pub reliability_score: f32,
    pub latency_ms: u64,
    pub last_updated: DateTime<Utc>,
    pub historical_accuracy: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SourceType {
    MarketData,
    NewsAPI,
    SocialMedia,
    InsiderTrading,
    EarningsData,
    OptionsFlow,
    BlockchainEvents,
    GovernmentData,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MultiSourceEvent {
    pub event_id: String,
    pub event_type: String,
    pub timestamp: DateTime<Utc>,
    pub sources: Vec<EventSourceData>,
    pub confidence_score: f32,
    pub conflict_resolution_method: ConflictResolutionMethod,
    pub final_value: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventSourceData {
    pub source: EventSource,
    pub raw_value: serde_json::Value,
    pub normalized_value: f32,
    pub source_confidence: f32,
    pub timeliness_score: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum ConflictResolutionMethod {
    ConfidenceWeightedAverage,
    HighestReliabilitySource,
    TimelinessWeighted,
    BayesianConsensus,
    MulticalibrationScoring,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfidenceMetrics {
    pub overall_confidence: f32,
    pub source_diversity_score: f32,
    pub temporal_consistency_score: f32,
    pub cross_validation_score: f32,
    pub multicalibration_score: f32,
}

pub struct EnhancedConfidenceEngine {
    sources: Arc<RwLock<HashMap<String, EventSource>>>,
    events: Arc<RwLock<HashMap<String, MultiSourceEvent>>>,
    calibration_model: Arc<RwLock<MulticalibrationModel>>,
    conflict_resolver: Arc<ConflictResolver>,
}

#[derive(Debug)]
#[allow(dead_code)]
pub struct MulticalibrationModel {
    calibration_bins: Vec<CalibrationBin>,
    model_weights: HashMap<String, f32>,
    historical_performance: HashMap<String, f32>,
}

#[derive(Debug, Clone)]
pub struct CalibrationBin {
    pub confidence_range: (f32, f32),
    pub predicted_accuracy: f32,
    pub actual_accuracy: f32,
    pub sample_count: u32,
}

pub struct ConflictResolver {
    resolution_strategies: HashMap<ConflictResolutionMethod, Box<dyn ConflictResolutionStrategy + Send + Sync>>,
}

pub trait ConflictResolutionStrategy {
    fn resolve_conflict(&self, sources: &[EventSourceData]) -> (f32, serde_json::Value);
    fn calculate_confidence(&self, sources: &[EventSourceData]) -> f32;
}

impl EnhancedConfidenceEngine {
    pub fn new() -> Self {
        let mut resolver = ConflictResolver {
            resolution_strategies: HashMap::new(),
        };
        
        resolver.resolution_strategies.insert(
            ConflictResolutionMethod::ConfidenceWeightedAverage,
            Box::new(ConfidenceWeightedStrategy::new()),
        );
        
        resolver.resolution_strategies.insert(
            ConflictResolutionMethod::MulticalibrationScoring,
            Box::new(MulticalibrationStrategy::new()),
        );
        
        resolver.resolution_strategies.insert(
            ConflictResolutionMethod::BayesianConsensus,
            Box::new(ConfidenceWeightedStrategy::new()),
        );
        
        Self {
            sources: Arc::new(RwLock::new(HashMap::new())),
            events: Arc::new(RwLock::new(HashMap::new())),
            calibration_model: Arc::new(RwLock::new(MulticalibrationModel::new())),
            conflict_resolver: Arc::new(resolver),
        }
    }
    
    pub async fn register_source(&self, source: EventSource) {
        let mut sources = self.sources.write().await;
        sources.insert(source.source_id.clone(), source);
    }
    
    pub async fn process_multi_source_event(
        &self,
        event_id: String,
        event_type: String,
        source_data: Vec<EventSourceData>,
    ) -> Result<MultiSourceEvent, String> {
        if source_data.is_empty() {
            return Err("No source data provided".to_string());
        }
        
        let resolution_method = self.select_resolution_method(&source_data).await;
        
        let (confidence_score, final_value) = self.conflict_resolver
            .resolve_conflict(&resolution_method, &source_data)?;
        
        let event = MultiSourceEvent {
            event_id: event_id.clone(),
            event_type,
            timestamp: Utc::now(),
            sources: source_data,
            confidence_score,
            conflict_resolution_method: resolution_method,
            final_value,
        };
        
        let mut events = self.events.write().await;
        events.insert(event_id, event.clone());
        
        self.update_calibration_model(&event).await;
        
        Ok(event)
    }
    
    async fn select_resolution_method(&self, source_data: &[EventSourceData]) -> ConflictResolutionMethod {
        let source_diversity = self.calculate_source_diversity(source_data);
        let conflict_level = self.calculate_conflict_level(source_data);
        
        if conflict_level > 0.7 && source_diversity > 0.5 {
            ConflictResolutionMethod::MulticalibrationScoring
        } else if source_diversity > 0.8 {
            ConflictResolutionMethod::BayesianConsensus
        } else {
            ConflictResolutionMethod::ConfidenceWeightedAverage
        }
    }
    
    fn calculate_source_diversity(&self, source_data: &[EventSourceData]) -> f32 {
        let unique_types: std::collections::HashSet<_> = source_data
            .iter()
            .map(|s| std::mem::discriminant(&s.source.source_type))
            .collect();
        
        unique_types.len() as f32 / source_data.len() as f32
    }
    
    fn calculate_conflict_level(&self, source_data: &[EventSourceData]) -> f32 {
        if source_data.len() < 2 {
            return 0.0;
        }
        
        let values: Vec<f32> = source_data.iter().map(|s| s.normalized_value).collect();
        let mean = values.iter().sum::<f32>() / values.len() as f32;
        let variance = values.iter()
            .map(|v| (v - mean).powi(2))
            .sum::<f32>() / values.len() as f32;
        
        variance.sqrt() / mean.abs().max(1.0)
    }
    
    async fn update_calibration_model(&self, event: &MultiSourceEvent) {
        let mut model = self.calibration_model.write().await;
        model.update_with_event(event);
    }
    
    pub async fn get_confidence_metrics(&self, event_id: &str) -> Option<ConfidenceMetrics> {
        let events = self.events.read().await;
        let event = events.get(event_id)?;
        
        Some(ConfidenceMetrics {
            overall_confidence: event.confidence_score,
            source_diversity_score: self.calculate_source_diversity(&event.sources),
            temporal_consistency_score: self.calculate_temporal_consistency(event).await,
            cross_validation_score: self.calculate_cross_validation_score(event).await,
            multicalibration_score: self.calculate_multicalibration_score(event).await,
        })
    }
    
    async fn calculate_temporal_consistency(&self, event: &MultiSourceEvent) -> f32 {
        let time_diffs: Vec<i64> = event.sources.iter()
            .map(|s| (event.timestamp - s.source.last_updated).num_seconds())
            .collect();
        
        let max_diff = time_diffs.iter().max().unwrap_or(&0);
        let consistency = 1.0 - (*max_diff as f32 / 3600.0).min(1.0);
        consistency.max(0.0)
    }
    
    async fn calculate_cross_validation_score(&self, event: &MultiSourceEvent) -> f32 {
        if event.sources.len() < 2 {
            return 0.5;
        }
        
        let mut total_agreement = 0.0;
        let mut comparisons = 0;
        
        for i in 0..event.sources.len() {
            for j in (i + 1)..event.sources.len() {
                let diff = (event.sources[i].normalized_value - event.sources[j].normalized_value).abs();
                let agreement = 1.0 - diff.min(1.0);
                total_agreement += agreement;
                comparisons += 1;
            }
        }
        
        if comparisons > 0 {
            total_agreement / comparisons as f32
        } else {
            0.5
        }
    }
    
    async fn calculate_multicalibration_score(&self, event: &MultiSourceEvent) -> f32 {
        let model = self.calibration_model.read().await;
        model.get_calibration_score(event.confidence_score)
    }
}

impl Default for MulticalibrationModel {
    fn default() -> Self {
        Self::new()
    }
}

impl MulticalibrationModel {
    pub fn new() -> Self {
        let calibration_bins = (0..10)
            .map(|i| CalibrationBin {
                confidence_range: (i as f32 * 0.1, (i + 1) as f32 * 0.1),
                predicted_accuracy: (i as f32 + 1.0) * 0.1,
                actual_accuracy: 0.0,
                sample_count: 0,
            })
            .collect();
        
        Self {
            calibration_bins,
            model_weights: HashMap::new(),
            historical_performance: HashMap::new(),
        }
    }
    
    pub fn update_with_event(&mut self, event: &MultiSourceEvent) {
        let bin_index = (event.confidence_score * 10.0).floor() as usize;
        if bin_index < self.calibration_bins.len() {
            let bin = &mut self.calibration_bins[bin_index];
            bin.sample_count += 1;
        }
    }
    
    pub fn get_calibration_score(&self, confidence: f32) -> f32 {
        let bin_index = (confidence * 10.0).floor() as usize;
        if bin_index < self.calibration_bins.len() {
            let bin = &self.calibration_bins[bin_index];
            if bin.sample_count > 0 {
                return bin.actual_accuracy;
            }
        }
        confidence
    }
}

impl ConflictResolver {
    pub fn resolve_conflict(
        &self,
        method: &ConflictResolutionMethod,
        sources: &[EventSourceData],
    ) -> Result<(f32, serde_json::Value), String> {
        if let Some(strategy) = self.resolution_strategies.get(method) {
            let (confidence, value) = strategy.resolve_conflict(sources);
            Ok((confidence, value))
        } else {
            Err(format!("Resolution method {:?} not implemented", method))
        }
    }
}

pub struct ConfidenceWeightedStrategy;

impl Default for ConfidenceWeightedStrategy {
    fn default() -> Self {
        Self::new()
    }
}

impl ConfidenceWeightedStrategy {
    pub fn new() -> Self {
        Self
    }
}

impl ConflictResolutionStrategy for ConfidenceWeightedStrategy {
    fn resolve_conflict(&self, sources: &[EventSourceData]) -> (f32, serde_json::Value) {
        if sources.is_empty() {
            return (0.0, serde_json::Value::Null);
        }
        
        let total_weight: f32 = sources.iter()
            .map(|s| s.source_confidence * s.source.reliability_score)
            .sum();
        
        if total_weight == 0.0 {
            return (0.0, sources[0].raw_value.clone());
        }
        
        let weighted_average: f32 = sources.iter()
            .map(|s| s.normalized_value * s.source_confidence * s.source.reliability_score)
            .sum::<f32>() / total_weight;
        
        let confidence = self.calculate_confidence(sources);
        
        (confidence, serde_json::Value::Number(serde_json::Number::from_f64(weighted_average as f64).unwrap()))
    }
    
    fn calculate_confidence(&self, sources: &[EventSourceData]) -> f32 {
        if sources.is_empty() {
            return 0.0;
        }
        
        let avg_source_confidence: f32 = sources.iter()
            .map(|s| s.source_confidence)
            .sum::<f32>() / sources.len() as f32;
        
        let avg_reliability: f32 = sources.iter()
            .map(|s| s.source.reliability_score)
            .sum::<f32>() / sources.len() as f32;
        
        let diversity_bonus = if sources.len() > 1 { 0.1 } else { 0.0 };
        
        (avg_source_confidence * avg_reliability + diversity_bonus).min(1.0)
    }
}

pub struct MulticalibrationStrategy;

impl Default for MulticalibrationStrategy {
    fn default() -> Self {
        Self::new()
    }
}

impl MulticalibrationStrategy {
    pub fn new() -> Self {
        Self
    }
}

impl ConflictResolutionStrategy for MulticalibrationStrategy {
    fn resolve_conflict(&self, sources: &[EventSourceData]) -> (f32, serde_json::Value) {
        if sources.is_empty() {
            return (0.0, serde_json::Value::Null);
        }
        
        let mut calibrated_sources: Vec<_> = sources.iter()
            .map(|s| {
                let calibrated_confidence = self.calibrate_confidence(s.source_confidence, &s.source);
                (s, calibrated_confidence)
            })
            .collect();
        
        calibrated_sources.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        
        let best_source = calibrated_sources[0].0;
        let confidence = calibrated_sources[0].1;
        
        (confidence, best_source.raw_value.clone())
    }
    
    fn calculate_confidence(&self, sources: &[EventSourceData]) -> f32 {
        if sources.is_empty() {
            return 0.0;
        }
        
        sources.iter()
            .map(|s| self.calibrate_confidence(s.source_confidence, &s.source))
            .fold(0.0, f32::max)
    }
}

impl MulticalibrationStrategy {
    fn calibrate_confidence(&self, raw_confidence: f32, source: &EventSource) -> f32 {
        let reliability_factor = source.reliability_score;
        let historical_factor = source.historical_accuracy;
        
        let calibrated = raw_confidence * reliability_factor * historical_factor;
        calibrated.clamp(0.0, 1.0)
    }
}

impl Default for EnhancedConfidenceEngine {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_confidence_engine_creation() {
        let engine = EnhancedConfidenceEngine::new();
        assert!(engine.sources.read().await.is_empty());
    }
    
    #[tokio::test]
    async fn test_source_registration() {
        let engine = EnhancedConfidenceEngine::new();
        
        let source = EventSource {
            source_id: "test_source".to_string(),
            source_type: SourceType::MarketData,
            reliability_score: 0.9,
            latency_ms: 100,
            last_updated: Utc::now(),
            historical_accuracy: 0.85,
        };
        
        engine.register_source(source.clone()).await;
        
        let sources = engine.sources.read().await;
        assert!(sources.contains_key("test_source"));
    }
    
    #[tokio::test]
    async fn test_conflict_resolution() {
        let engine = EnhancedConfidenceEngine::new();
        
        let source_data = vec![
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
                raw_value: serde_json::Value::Number(serde_json::Number::from(105)),
                normalized_value: 105.0,
                source_confidence: 0.8,
                timeliness_score: 0.8,
            },
        ];
        
        let result = engine.process_multi_source_event(
            "test_event".to_string(),
            "price_update".to_string(),
            source_data,
        ).await;
        
        assert!(result.is_ok());
        let event = result.unwrap();
        assert!(event.confidence_score > 0.0);
        assert!(event.confidence_score <= 1.0);
    }
}
