use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EdgeDeduplicationRequest {
    pub request_id: String,
    pub events: Vec<EdgeEvent>,
    pub dedup_window_ms: i64,
    pub similarity_threshold: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EdgeEvent {
    pub event_id: String,
    pub event_type: String,
    pub timestamp: DateTime<Utc>,
    pub content_hash: String,
    pub source_id: String,
    pub metadata: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EdgeDeduplicationResult {
    pub request_id: String,
    pub unique_events: Vec<EdgeEvent>,
    pub duplicate_groups: Vec<DuplicateGroup>,
    pub processing_time_ms: u64,
    pub confidence_score: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DuplicateGroup {
    pub group_id: String,
    pub canonical_event: EdgeEvent,
    pub duplicates: Vec<EdgeEvent>,
    pub similarity_scores: Vec<f32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WasmModuleConfig {
    pub module_id: String,
    pub module_path: String,
    pub max_memory_mb: u32,
    pub timeout_ms: u32,
    pub security_policy: SecurityPolicy,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityPolicy {
    pub allow_network: bool,
    pub allow_filesystem: bool,
    pub max_cpu_time_ms: u32,
    pub memory_limit_mb: u32,
}

pub struct WasmEdgeClient {
    modules: Arc<RwLock<HashMap<String, WasmModule>>>,
    dedup_cache: Arc<RwLock<HashMap<String, EdgeEvent>>>,
    performance_metrics: Arc<RwLock<EdgePerformanceMetrics>>,
}

#[derive(Debug)]
struct WasmModule {
    config: WasmModuleConfig,
    instance: Option<WasmInstance>,
    last_used: DateTime<Utc>,
    execution_count: u64,
}

#[allow(dead_code)]
#[derive(Debug)]
struct WasmInstance {
    module_id: String,
    memory_usage: u32,
    cpu_time_used: u32,
}

#[derive(Debug, Clone)]
pub struct EdgePerformanceMetrics {
    pub total_requests: u64,
    pub successful_deduplications: u64,
    pub average_processing_time_ms: f64,
    pub memory_usage_mb: f64,
    pub cache_hit_ratio: f64,
    pub error_rate: f64,
}

impl WasmEdgeClient {
    pub fn new() -> Self {
        Self {
            modules: Arc::new(RwLock::new(HashMap::new())),
            dedup_cache: Arc::new(RwLock::new(HashMap::new())),
            performance_metrics: Arc::new(RwLock::new(EdgePerformanceMetrics {
                total_requests: 0,
                successful_deduplications: 0,
                average_processing_time_ms: 0.0,
                memory_usage_mb: 0.0,
                cache_hit_ratio: 0.0,
                error_rate: 0.0,
            })),
        }
    }

    pub async fn register_wasm_module(&self, config: WasmModuleConfig) -> Result<(), String> {
        let module = WasmModule {
            config: config.clone(),
            instance: None,
            last_used: Utc::now(),
            execution_count: 0,
        };

        let mut modules = self.modules.write().await;
        modules.insert(config.module_id.clone(), module);
        
        Ok(())
    }

    pub async fn process_deduplication_request(
        &self,
        request: EdgeDeduplicationRequest,
    ) -> Result<EdgeDeduplicationResult, String> {
        let start_time = std::time::Instant::now();
        
        {
            let mut metrics = self.performance_metrics.write().await;
            metrics.total_requests += 1;
        }

        let (unique_events, duplicate_groups) = self.deduplicate_events(&request.events, &request).await?;

        let processing_time = start_time.elapsed().as_millis() as u64;
        let confidence_score = self.calculate_deduplication_confidence(&unique_events, &duplicate_groups);

        self.update_performance_metrics(processing_time, true).await;

        Ok(EdgeDeduplicationResult {
            request_id: request.request_id,
            unique_events,
            duplicate_groups,
            processing_time_ms: processing_time,
            confidence_score,
        })
    }

    async fn deduplicate_events(
        &self,
        events: &[EdgeEvent],
        request: &EdgeDeduplicationRequest,
    ) -> Result<(Vec<EdgeEvent>, Vec<DuplicateGroup>), String> {
        let mut unique_events = Vec::new();
        let mut duplicate_groups: Vec<DuplicateGroup> = Vec::new();
        let mut processed_hashes = HashMap::new();

        let cache = self.dedup_cache.read().await;
        
        for event in events {
            if let Some(cached_event) = cache.get(&event.content_hash) {
                let time_diff = event.timestamp.signed_duration_since(cached_event.timestamp).num_milliseconds();
                
                if time_diff.abs() < request.dedup_window_ms {
                    if let Some(group) = duplicate_groups.iter_mut().find(|g| g.canonical_event.content_hash == event.content_hash) {
                        group.duplicates.push(event.clone());
                        group.similarity_scores.push(1.0);
                    } else {
                        duplicate_groups.push(DuplicateGroup {
                            group_id: uuid::Uuid::new_v4().to_string(),
                            canonical_event: cached_event.clone(),
                            duplicates: vec![event.clone()],
                            similarity_scores: vec![1.0],
                        });
                    }
                    continue;
                }
            }

            let mut is_duplicate = false;
            for (existing_hash, existing_event) in &processed_hashes {
                let similarity = self.calculate_semantic_similarity(event, existing_event);
                
                if similarity > request.similarity_threshold {
                    if let Some(group) = duplicate_groups.iter_mut().find(|g| g.canonical_event.content_hash == *existing_hash) {
                        group.duplicates.push(event.clone());
                        group.similarity_scores.push(similarity);
                    } else {
                        duplicate_groups.push(DuplicateGroup {
                            group_id: uuid::Uuid::new_v4().to_string(),
                            canonical_event: existing_event.clone(),
                            duplicates: vec![event.clone()],
                            similarity_scores: vec![similarity],
                        });
                    }
                    is_duplicate = true;
                    break;
                }
            }

            if !is_duplicate {
                unique_events.push(event.clone());
                processed_hashes.insert(event.content_hash.clone(), event.clone());
            }
        }

        drop(cache);
        let mut cache = self.dedup_cache.write().await;
        for event in &unique_events {
            cache.insert(event.content_hash.clone(), event.clone());
        }

        let cutoff_time = Utc::now() - chrono::Duration::milliseconds(request.dedup_window_ms * 2);
        cache.retain(|_, event| event.timestamp > cutoff_time);

        Ok((unique_events, duplicate_groups))
    }

    fn calculate_semantic_similarity(&self, event1: &EdgeEvent, event2: &EdgeEvent) -> f32 {
        if event1.event_type != event2.event_type {
            return 0.0;
        }

        let mut similarity_score = 0.5;

        let common_keys: Vec<&String> = event1.metadata.keys()
            .filter(|k| event2.metadata.contains_key(*k))
            .collect();

        if !common_keys.is_empty() {
            let matching_values = common_keys.iter()
                .filter(|&k| event1.metadata.get(k.as_str()) == event2.metadata.get(k.as_str()))
                .count();
            
            similarity_score += (matching_values as f32 / common_keys.len() as f32) * 0.4;
        }

        let time_diff = (event1.timestamp.timestamp_millis() - event2.timestamp.timestamp_millis()).abs();
        if time_diff < 60000 {
            similarity_score += 0.1;
        }

        similarity_score.min(1.0)
    }

    fn calculate_deduplication_confidence(&self, unique_events: &[EdgeEvent], duplicate_groups: &[DuplicateGroup]) -> f32 {
        let total_events = unique_events.len() + duplicate_groups.iter().map(|g| g.duplicates.len() + 1).sum::<usize>();
        
        if total_events == 0 {
            return 1.0;
        }

        let dedup_ratio = duplicate_groups.len() as f32 / total_events as f32;
        let base_confidence = 0.5 + (dedup_ratio * 0.3);

        let avg_similarity: f32 = duplicate_groups.iter()
            .flat_map(|g| &g.similarity_scores)
            .sum::<f32>() / duplicate_groups.iter().map(|g| g.similarity_scores.len()).sum::<usize>() as f32;

        let similarity_boost = avg_similarity * 0.2;

        (base_confidence + similarity_boost).min(1.0)
    }

    async fn update_performance_metrics(&self, processing_time_ms: u64, success: bool) {
        let mut metrics = self.performance_metrics.write().await;
        
        if success {
            metrics.successful_deduplications += 1;
        }

        let total_requests = metrics.total_requests as f64;
        metrics.average_processing_time_ms = 
            (metrics.average_processing_time_ms * (total_requests - 1.0) + processing_time_ms as f64) / total_requests;

        let cache_size = self.dedup_cache.read().await.len();
        metrics.cache_hit_ratio = cache_size as f64 / total_requests;

        let errors = metrics.total_requests - metrics.successful_deduplications;
        metrics.error_rate = errors as f64 / total_requests;
    }

    pub async fn get_performance_metrics(&self) -> EdgePerformanceMetrics {
        self.performance_metrics.read().await.clone()
    }

    pub async fn cleanup_expired_cache(&self, max_age_ms: i64) {
        let cutoff_time = Utc::now() - chrono::Duration::milliseconds(max_age_ms);
        let mut cache = self.dedup_cache.write().await;
        cache.retain(|_, event| event.timestamp > cutoff_time);
    }

    pub async fn execute_wasm_function(
        &self,
        module_id: &str,
        function_name: &str,
        input_data: &[u8],
    ) -> Result<Vec<u8>, String> {
        let mut modules = self.modules.write().await;
        
        let module = modules.get_mut(module_id)
            .ok_or_else(|| format!("WASM module {} not found", module_id))?;

        if input_data.len() > module.config.security_policy.memory_limit_mb as usize * 1024 * 1024 {
            return Err("Input data exceeds memory limit".to_string());
        }

        if module.instance.is_none() {
            module.instance = Some(WasmInstance {
                module_id: module_id.to_string(),
                memory_usage: 0,
                cpu_time_used: 0,
            });
        }

        let result = self.execute_wasm_function_impl(module, function_name, input_data).await?;

        module.last_used = Utc::now();
        module.execution_count += 1;

        Ok(result)
    }

    async fn execute_wasm_function_impl(
        &self,
        _module: &mut WasmModule,
        function_name: &str,
        input_data: &[u8],
    ) -> Result<Vec<u8>, String> {
        match function_name {
            "deduplicate" => {
                let output = format!("Processed {} bytes for deduplication", input_data.len());
                Ok(output.into_bytes())
            },
            "hash_content" => {
                let hash = format!("hash_{}", input_data.len());
                Ok(hash.into_bytes())
            },
            _ => Err(format!("Unknown function: {}", function_name)),
        }
    }
}

impl Default for WasmEdgeClient {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_wasm_edge_client_creation() {
        let client = WasmEdgeClient::new();
        let metrics = client.get_performance_metrics().await;
        assert_eq!(metrics.total_requests, 0);
    }

    #[tokio::test]
    async fn test_deduplication_request() {
        let client = WasmEdgeClient::new();
        
        let events = vec![
            EdgeEvent {
                event_id: "event1".to_string(),
                event_type: "price_update".to_string(),
                timestamp: Utc::now(),
                content_hash: "hash1".to_string(),
                source_id: "source1".to_string(),
                metadata: [("symbol".to_string(), "AAPL".to_string())].iter().cloned().collect(),
            },
            EdgeEvent {
                event_id: "event2".to_string(),
                event_type: "price_update".to_string(),
                timestamp: Utc::now(),
                content_hash: "hash1".to_string(),
                source_id: "source2".to_string(),
                metadata: [("symbol".to_string(), "AAPL".to_string())].iter().cloned().collect(),
            },
        ];

        let request = EdgeDeduplicationRequest {
            request_id: "test_request".to_string(),
            events,
            dedup_window_ms: 60000,
            similarity_threshold: 0.8,
        };

        let result = client.process_deduplication_request(request).await;
        assert!(result.is_ok());
        
        let result = result.unwrap();
        assert_eq!(result.unique_events.len(), 1);
        assert_eq!(result.duplicate_groups.len(), 1);
    }

    #[tokio::test]
    async fn test_wasm_module_registration() {
        let client = WasmEdgeClient::new();
        
        let config = WasmModuleConfig {
            module_id: "test_module".to_string(),
            module_path: "/path/to/module.wasm".to_string(),
            max_memory_mb: 64,
            timeout_ms: 5000,
            security_policy: SecurityPolicy {
                allow_network: false,
                allow_filesystem: false,
                max_cpu_time_ms: 1000,
                memory_limit_mb: 32,
            },
        };

        let result = client.register_wasm_module(config).await;
        assert!(result.is_ok());
    }
}
