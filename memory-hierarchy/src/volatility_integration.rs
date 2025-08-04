use std::sync::Arc;
use tokio::sync::RwLock;
use crate::{MemoryHierarchy, ai_optimization::BraidedBrownianModel};
use crate::brownian_volatility_strand::{BrownianMotionParameters, VolatilitySimulationRecord};
use crate::async_volatility_engine::AsyncVolatilityEngine;

pub struct VolatilityIntegratedMemoryHierarchy {
    memory_hierarchy: Arc<MemoryHierarchy>,
    volatility_engine: Arc<AsyncVolatilityEngine>,
    strand_mappings: Arc<RwLock<std::collections::HashMap<String, String>>>, 
}

impl VolatilityIntegratedMemoryHierarchy {
    pub async fn new(base_file_path: String, max_concurrent_simulations: usize) -> Self {
        let memory_hierarchy = Arc::new(MemoryHierarchy::new());
        let volatility_engine = Arc::new(AsyncVolatilityEngine::new(base_file_path, max_concurrent_simulations));
        
        Self {
            memory_hierarchy,
            volatility_engine,
            strand_mappings: Arc::new(RwLock::new(std::collections::HashMap::new())),
        }
    }

    pub async fn register_volatility_model(
        &self,
        model_id: String,
        parameters: BrownianMotionParameters,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let num_strands = 3; 
        let time_steps = (1.0 / parameters.dt) as usize; 
        
        let braided_model = BraidedBrownianModel::new(
            model_id.clone(),
            num_strands,
            time_steps,
        );
        
        self.memory_hierarchy.register_braided_model(braided_model).await;
        
        let strand_id = format!("volatility_{}", model_id);
        self.volatility_engine.create_strand(strand_id.clone()).await?;
        
        {
            let mut mappings = self.strand_mappings.write().await;
            mappings.insert(model_id, strand_id);
        }
        
        Ok(())
    }

    pub async fn simulate_volatility_with_memory_caching(
        &self,
        model_id: &str,
        simulation_id: String,
        parameters: BrownianMotionParameters,
        num_steps: usize,
        cache_results: bool,
    ) -> Result<VolatilitySimulationRecord, Box<dyn std::error::Error>> {
        let strand_id = {
            let mappings = self.strand_mappings.read().await;
            mappings.get(model_id)
                .ok_or(format!("Model {} not registered", model_id))?
                .clone()
        };

        if cache_results {
            let cache_key = format!("volatility_sim:{}:{}", model_id, simulation_id);
            if let Some(cached_data) = self.memory_hierarchy.get(&cache_key).await {
                if let Ok(cached_record) = serde_json::from_slice::<VolatilitySimulationRecord>(&cached_data) {
                    return Ok(cached_record);
                }
            }
        }

        let strands_arc = self.volatility_engine.get_strands().await;
        let strands = strands_arc.read().await;
        let strand = strands.get(&strand_id)
            .ok_or("Strand not found")?;
        
        let record = strand.simulate_and_append_gbm(simulation_id, parameters, num_steps).await?;

        if cache_results {
            let cache_key = format!("volatility_sim:{}:{}", model_id, record.simulation_id);
            let serialized = serde_json::to_vec(&record)?;
            self.memory_hierarchy.put(cache_key, serialized).await;
        }

        let initial_conditions: Vec<f32> = vec![record.parameters.initial_value as f32];
        let analysis_key = format!("braided_analysis:{}:{}", model_id, record.simulation_id);
        self.memory_hierarchy.store_braided_analysis(analysis_key, model_id, &initial_conditions).await?;

        Ok(record)
    }

    pub async fn run_monte_carlo_with_tiered_storage(
        &self,
        model_id: &str,
        base_parameters: BrownianMotionParameters,
        num_simulations: usize,
        num_steps: usize,
        volatility_range: (f64, f64),
    ) -> Result<Vec<VolatilitySimulationRecord>, Box<dyn std::error::Error>> {
        let strand_id = {
            let mappings = self.strand_mappings.read().await;
            mappings.get(model_id)
                .ok_or(format!("Model {} not registered", model_id))?
                .clone()
        };

        let results = self.volatility_engine.simulate_monte_carlo_volatility(
            &strand_id,
            base_parameters,
            num_simulations,
            num_steps,
            volatility_range,
        ).await?;

        for (i, record) in results.iter().enumerate() {
            let tier_key = if i < 10 {
                format!("hot:volatility_summary:{}:{}", model_id, record.simulation_id)
            } else if i < 100 {
                format!("warm:volatility_summary:{}:{}", model_id, record.simulation_id)
            } else {
                format!("cold:volatility_summary:{}:{}", model_id, record.simulation_id)
            };

            let summary = serde_json::json!({
                "simulation_id": record.simulation_id,
                "final_value": record.path_data.last(),
                "risk_moments": record.risk_moments,
                "parameters": record.parameters
            });

            self.memory_hierarchy.put(tier_key, summary.to_string().into_bytes()).await;
        }

        Ok(results)
    }

    pub async fn get_volatility_performance_report(&self) -> Result<String, Box<dyn std::error::Error>> {
        let memory_report = self.memory_hierarchy.get_performance_report().await;
        let volatility_stats = self.volatility_engine.get_all_strand_statistics().await;

        let combined_report = serde_json::json!({
            "memory_hierarchy": memory_report,
            "volatility_strands": volatility_stats,
            "integration_timestamp": std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos(),
            "total_registered_models": self.strand_mappings.read().await.len()
        });

        Ok(combined_report.to_string())
    }

    pub async fn export_audit_trail(
        &self,
        model_id: &str,
    ) -> Result<String, Box<dyn std::error::Error>> {
        let strand_id = {
            let mappings = self.strand_mappings.read().await;
            mappings.get(model_id)
                .ok_or(format!("Model {} not registered", model_id))?
                .clone()
        };

        let volatility_audit = self.volatility_engine.export_strand_to_audit_format(&strand_id).await?;
        let memory_stats = self.memory_hierarchy.get_ai_optimization_stats().await;

        let combined_audit = serde_json::json!({
            "model_id": model_id,
            "volatility_audit": serde_json::from_str::<serde_json::Value>(&volatility_audit)?,
            "memory_hierarchy_stats": memory_stats,
            "audit_timestamp": std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos(),
            "audit_version": "1.0"
        });

        Ok(combined_audit.to_string())
    }

    pub async fn get(&self, key: &str) -> Option<Vec<u8>> {
        self.memory_hierarchy.get(key).await
    }

    pub async fn put(&self, key: String, data: Vec<u8>) {
        self.memory_hierarchy.put(key, data).await;
    }

    pub async fn get_stats(&self) -> crate::AccessStats {
        self.memory_hierarchy.get_stats().await
    }

    pub async fn get_performance_report(&self) -> String {
        self.get_volatility_performance_report().await.unwrap_or_else(|e| {
            format!("Error generating performance report: {}", e)
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[tokio::test]
    async fn test_volatility_integrated_memory_hierarchy() {
        let temp_dir = TempDir::new().unwrap();
        let base_path = temp_dir.path().to_string_lossy().to_string();
        
        let integrated_system = VolatilityIntegratedMemoryHierarchy::new(base_path, 4).await;

        let parameters = BrownianMotionParameters {
            mu: 0.05,
            sigma: 0.2,
            dt: 1.0 / 252.0,
            initial_value: 100.0,
            correlation_matrix: None,
            seed: Some(42),
        };

        integrated_system.register_volatility_model(
            "test_model".to_string(),
            parameters.clone(),
        ).await.unwrap();

        let record = integrated_system.simulate_volatility_with_memory_caching(
            "test_model",
            "test_sim_1".to_string(),
            parameters.clone(),
            100,
            true,
        ).await.unwrap();

        assert_eq!(record.simulation_id, "test_sim_1");
        assert_eq!(record.path_data.len(), 101);

        let cached_record = integrated_system.simulate_volatility_with_memory_caching(
            "test_model",
            "test_sim_1".to_string(),
            parameters.clone(),
            100,
            true,
        ).await.unwrap();

        assert_eq!(cached_record.simulation_id, record.simulation_id);
        assert_eq!(cached_record.audit_hash, record.audit_hash);

        let monte_carlo_results = integrated_system.run_monte_carlo_with_tiered_storage(
            "test_model",
            parameters,
            50,
            100,
            (0.1, 0.3),
        ).await.unwrap();

        assert_eq!(monte_carlo_results.len(), 50);

        let report = integrated_system.get_volatility_performance_report().await.unwrap();
        assert!(report.contains("memory_hierarchy"));
        assert!(report.contains("volatility_strands"));

        let audit = integrated_system.export_audit_trail("test_model").await.unwrap();
        assert!(audit.contains("test_model"));
        assert!(audit.contains("audit_timestamp"));
    }

    #[tokio::test]
    async fn test_tiered_storage_access_patterns() {
        let temp_dir = TempDir::new().unwrap();
        let base_path = temp_dir.path().to_string_lossy().to_string();
        
        let integrated_system = VolatilityIntegratedMemoryHierarchy::new(base_path, 4).await;

        let parameters = BrownianMotionParameters {
            mu: 0.05,
            sigma: 0.2,
            dt: 1.0 / 252.0,
            initial_value: 100.0,
            correlation_matrix: None,
            seed: Some(42),
        };

        integrated_system.register_volatility_model(
            "tiered_test".to_string(),
            parameters.clone(),
        ).await.unwrap();

        let results = integrated_system.run_monte_carlo_with_tiered_storage(
            "tiered_test",
            parameters,
            150,
            50,
            (0.1, 0.4),
        ).await.unwrap();

        assert_eq!(results.len(), 150);

        let hot_key = format!("hot:volatility_summary:tiered_test:{}", results[0].simulation_id);
        let hot_data = integrated_system.get(&hot_key).await;
        assert!(hot_data.is_some());

        let warm_key = format!("warm:volatility_summary:tiered_test:{}", results[50].simulation_id);
        let warm_data = integrated_system.get(&warm_key).await;
        assert!(warm_data.is_some());

        let cold_key = format!("cold:volatility_summary:tiered_test:{}", results[120].simulation_id);
        let cold_data = integrated_system.get(&cold_key).await;
        assert!(cold_data.is_some());
    }
}
