
use std::collections::HashMap;
use std::time::{Duration, Instant};
use serde::{Deserialize, Serialize};
use tokio::sync::RwLock;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CausalRelationship {
    pub cause: String,
    pub effect: String,
    pub strength: f64,
    pub confidence: f64,
    pub last_updated: Instant,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CausalIndex {
    pub relationships: HashMap<String, Vec<CausalRelationship>>,
    pub vix_velocity_priority: f64,
    pub access_patterns: HashMap<String, AccessPattern>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AccessPattern {
    pub access_count: u64,
    pub last_access: Instant,
    pub causal_score: f64,
    pub velocity_correlation: f64,
}

pub struct CausalMemoryHierarchy {
    pub causal_index: RwLock<CausalIndex>,
    pub hot_tier_capacity: usize,
    pub vix_velocity_threshold: f64,
}

impl CausalMemoryHierarchy {
    pub fn new(hot_tier_capacity: usize) -> Self {
        Self {
            causal_index: RwLock::new(CausalIndex {
                relationships: HashMap::new(),
                vix_velocity_priority: 1.0,
                access_patterns: HashMap::new(),
            }),
            hot_tier_capacity,
            vix_velocity_threshold: 0.7,
        }
    }
    
    pub async fn update_causal_relationship(
        &self,
        cause: String,
        effect: String,
        strength: f64,
        confidence: f64,
    ) {
        let mut index = self.causal_index.write().await;
        
        let relationship = CausalRelationship {
            cause: cause.clone(),
            effect: effect.clone(),
            strength,
            confidence,
            last_updated: Instant::now(),
        };
        
        index.relationships
            .entry(cause)
            .or_insert_with(Vec::new)
            .push(relationship);
        
        if effect.contains("velocity") && cause.contains("VIX") {
            index.vix_velocity_priority = strength * confidence;
        }
    }
    
    pub async fn calculate_causal_priority(&self, key: &str) -> f64 {
        let index = self.causal_index.read().await;
        
        let mut priority = 1.0;
        
        if key.contains("VIX") || key.contains("velocity") {
            priority *= index.vix_velocity_priority;
        }
        
        if let Some(pattern) = index.access_patterns.get(key) {
            let recency_factor = 1.0 / (pattern.last_access.elapsed().as_secs() as f64 + 1.0);
            let frequency_factor = (pattern.access_count as f64).ln();
            let causal_factor = pattern.causal_score;
            
            priority *= recency_factor * frequency_factor * causal_factor;
        }
        
        for relationships in index.relationships.values() {
            for rel in relationships {
                if rel.effect == key || rel.cause == key {
                    priority *= 1.0 + (rel.strength * rel.confidence);
                }
            }
        }
        
        priority
    }
    
    pub async fn should_promote_to_hot_tier(&self, key: &str) -> bool {
        let priority = self.calculate_causal_priority(key).await;
        priority > self.vix_velocity_threshold
    }
    
    pub async fn update_access_pattern(&self, key: String) {
        let mut index = self.causal_index.write().await;
        
        let pattern = index.access_patterns
            .entry(key.clone())
            .or_insert(AccessPattern {
                access_count: 0,
                last_access: Instant::now(),
                causal_score: 1.0,
                velocity_correlation: 0.0,
            });
        
        pattern.access_count += 1;
        pattern.last_access = Instant::now();
        
        let mut causal_score = 1.0;
        for relationships in index.relationships.values() {
            for rel in relationships {
                if rel.effect == key || rel.cause == key {
                    causal_score += rel.strength * rel.confidence;
                }
            }
        }
        pattern.causal_score = causal_score;
        
        if key.contains("VIX") {
            pattern.velocity_correlation = index.vix_velocity_priority;
        }
    }
}
