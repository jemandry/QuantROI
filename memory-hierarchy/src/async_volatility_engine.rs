use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::{RwLock, Semaphore};
use tokio::task::JoinHandle;
use futures::future::join_all;
use crate::brownian_volatility_strand::{BrownianVolatilityStrand, BrownianMotionParameters, VolatilitySimulationRecord};

pub struct AsyncVolatilityEngine {
    strands: Arc<RwLock<HashMap<String, Arc<BrownianVolatilityStrand>>>>,
    simulation_semaphore: Arc<Semaphore>,
    base_file_path: String,
}

impl AsyncVolatilityEngine {
    pub fn new(base_file_path: String, max_concurrent_simulations: usize) -> Self {
        Self {
            strands: Arc::new(RwLock::new(HashMap::new())),
            simulation_semaphore: Arc::new(Semaphore::new(max_concurrent_simulations)),
            base_file_path,
        }
    }

    pub async fn create_strand(&self, strand_id: String) -> Result<(), Box<dyn std::error::Error>> {
        let file_path = format!("{}/volatility_strand_{}.mmap", self.base_file_path, strand_id);
        let strand = Arc::new(BrownianVolatilityStrand::new(strand_id.clone(), file_path).await?);
        
        let mut strands = self.strands.write().await;
        strands.insert(strand_id, strand);
        
        Ok(())
    }

    pub async fn simulate_batch_async(
        &self,
        strand_id: &str,
        simulations: Vec<(String, BrownianMotionParameters, usize)>, 
    ) -> Result<Vec<VolatilitySimulationRecord>, Box<dyn std::error::Error>> {
        let strands = self.strands.read().await;
        let strand = strands.get(strand_id)
            .ok_or("Strand not found")?
            .clone();
        drop(strands);

        let mut handles: Vec<JoinHandle<Result<VolatilitySimulationRecord, Box<dyn std::error::Error + Send + Sync>>>> = Vec::new();

        for (sim_id, params, num_steps) in simulations {
            let strand_clone = strand.clone();
            let semaphore_clone = self.simulation_semaphore.clone();
            
            let handle = tokio::spawn(async move {
                let _permit = semaphore_clone.acquire().await.unwrap();
                
                let result = strand_clone.simulate_and_append_gbm(sim_id, params, num_steps).await;
                match result {
                    Ok(record) => Ok(record),
                    Err(e) => Err(Box::new(std::io::Error::new(std::io::ErrorKind::Other, e.to_string())) as Box<dyn std::error::Error + Send + Sync>),
                }
            });
            
            handles.push(handle);
        }

        let results = join_all(handles).await;
        let mut simulation_records = Vec::new();
        
        for result in results {
            match result {
                Ok(Ok(record)) => simulation_records.push(record),
                Ok(Err(e)) => return Err(format!("Simulation error: {}", e).into()),
                Err(e) => return Err(format!("Task join error: {}", e).into()),
            }
        }

        Ok(simulation_records)
    }

    pub async fn simulate_monte_carlo_volatility(
        &self,
        strand_id: &str,
        base_parameters: BrownianMotionParameters,
        num_simulations: usize,
        num_steps: usize,
        volatility_range: (f64, f64), 
    ) -> Result<Vec<VolatilitySimulationRecord>, Box<dyn std::error::Error>> {
        let mut simulations = Vec::new();
        
        for i in 0..num_simulations {
            let sigma_variation = volatility_range.0 + 
                (volatility_range.1 - volatility_range.0) * (i as f64 / num_simulations as f64);
            
            let mut params = base_parameters.clone();
            params.sigma = sigma_variation;
            params.seed = Some(base_parameters.seed.unwrap_or(42) + i as u64);
            
            simulations.push((
                format!("monte_carlo_{}_{}", strand_id, i),
                params,
                num_steps,
            ));
        }

        self.simulate_batch_async(strand_id, simulations).await
    }

    pub async fn get_strand_statistics(
        &self,
        strand_id: &str,
    ) -> Result<VolatilityStrandStatistics, Box<dyn std::error::Error>> {
        let strands = self.strands.read().await;
        let strand = strands.get(strand_id)
            .ok_or("Strand not found")?;

        let metadata = strand.get_metadata().await;
        let simulation_count = strand.get_simulation_count().await;

        Ok(VolatilityStrandStatistics {
            strand_id: strand_id.to_string(),
            total_simulations: simulation_count,
            file_size_bytes: metadata.current_file_size,
            creation_timestamp: metadata.creation_timestamp,
            audit_chain_verified: strand.verify_audit_chain().await?,
        })
    }

    pub async fn get_all_strand_statistics(&self) -> HashMap<String, VolatilityStrandStatistics> {
        let strands = self.strands.read().await;
        let mut statistics = HashMap::new();

        for strand_id in strands.keys() {
            if let Ok(stats) = self.get_strand_statistics(strand_id).await {
                statistics.insert(strand_id.clone(), stats);
            }
        }

        statistics
    }

    pub async fn simulate_correlated_assets(
        &self,
        strand_ids: Vec<String>,
        correlation_matrix: Vec<Vec<f64>>,
        base_parameters: Vec<BrownianMotionParameters>,
        num_steps: usize,
    ) -> Result<HashMap<String, VolatilitySimulationRecord>, Box<dyn std::error::Error>> {
        if strand_ids.len() != base_parameters.len() || 
           correlation_matrix.len() != strand_ids.len() {
            return Err("Dimension mismatch in correlation parameters".into());
        }

        let _cholesky = self.cholesky_decomposition(&correlation_matrix)?;
        
        let mut results = HashMap::new();
        let mut handles = Vec::new();

        for (i, strand_id) in strand_ids.iter().enumerate() {
            let strands = self.strands.read().await;
            let strand = strands.get(strand_id)
                .ok_or(format!("Strand {} not found", strand_id))?
                .clone();
            drop(strands);

            let mut params = base_parameters[i].clone();
            params.correlation_matrix = Some(correlation_matrix.clone());
            
            let sim_id = format!("correlated_{}_{}", strand_id, 
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_nanos());

            let semaphore_clone = self.simulation_semaphore.clone();
            
            let handle = tokio::spawn(async move {
                let _permit = semaphore_clone.acquire().await.unwrap();
                strand.simulate_and_append_gbm(sim_id, params, num_steps).await
                    .map_err(|e| e.to_string())
            });
            
            handles.push((strand_id.clone(), handle));
        }

        for (strand_id, handle) in handles {
            match handle.await {
                Ok(Ok(record)) => {
                    results.insert(strand_id, record);
                },
                Ok(Err(e)) => return Err(format!("Simulation error: {}", e).into()),
                Err(e) => return Err(format!("Task join error: {}", e).into()),
            }
        }

        Ok(results)
    }

    fn cholesky_decomposition(&self, matrix: &[Vec<f64>]) -> Result<Vec<Vec<f64>>, Box<dyn std::error::Error>> {
        let n = matrix.len();
        let mut l = vec![vec![0.0; n]; n];

        for i in 0..n {
            for j in 0..=i {
                if i == j {
                    let mut sum = 0.0;
                    for k in 0..j {
                        sum += l[j][k] * l[j][k];
                    }
                    l[j][j] = (matrix[j][j] - sum).sqrt();
                } else {
                    let mut sum = 0.0;
                    for k in 0..j {
                        sum += l[i][k] * l[j][k];
                    }
                    l[i][j] = (matrix[i][j] - sum) / l[j][j];
                }
            }
        }

        Ok(l)
    }

    pub async fn get_strands(&self) -> Arc<RwLock<HashMap<String, Arc<BrownianVolatilityStrand>>>> {
        self.strands.clone()
    }

    pub async fn cleanup_old_simulations(
        &self,
        _strand_id: &str,
        _older_than_ns: u64,
    ) -> Result<usize, Box<dyn std::error::Error>> {
        Ok(0)
    }

    pub async fn export_strand_to_audit_format(
        &self,
        strand_id: &str,
    ) -> Result<String, Box<dyn std::error::Error>> {
        let strands = self.strands.read().await;
        let strand = strands.get(strand_id)
            .ok_or("Strand not found")?;

        let metadata = strand.get_metadata().await;
        let audit_verified = strand.verify_audit_chain().await?;

        let audit_export = serde_json::json!({
            "strand_id": strand_id,
            "metadata": metadata,
            "audit_chain_verified": audit_verified,
            "export_timestamp": std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos(),
            "total_simulations": metadata.total_simulations,
            "file_size_bytes": metadata.current_file_size
        });

        Ok(audit_export.to_string())
    }
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct VolatilityStrandStatistics {
    pub strand_id: String,
    pub total_simulations: u64,
    pub file_size_bytes: u64,
    pub creation_timestamp: u64,
    pub audit_chain_verified: bool,
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[tokio::test]
    async fn test_async_volatility_engine() {
        let temp_dir = TempDir::new().unwrap();
        let base_path = temp_dir.path().to_string_lossy().to_string();
        
        let engine = AsyncVolatilityEngine::new(base_path, 4);
        
        engine.create_strand("test_strand".to_string()).await.unwrap();

        let base_params = BrownianMotionParameters {
            mu: 0.05,
            sigma: 0.2,
            dt: 1.0 / 252.0,
            initial_value: 100.0,
            correlation_matrix: None,
            seed: Some(42),
        };

        let results = engine.simulate_monte_carlo_volatility(
            "test_strand",
            base_params,
            10,
            50,
            (0.1, 0.3),
        ).await.unwrap();

        assert_eq!(results.len(), 10);

        let stats = engine.get_strand_statistics("test_strand").await.unwrap();
        assert_eq!(stats.total_simulations, 10);
        assert!(stats.audit_chain_verified);

        let export = engine.export_strand_to_audit_format("test_strand").await.unwrap();
        assert!(export.contains("test_strand"));
    }

    #[tokio::test]
    async fn test_correlated_assets_simulation() {
        let temp_dir = TempDir::new().unwrap();
        let base_path = temp_dir.path().to_string_lossy().to_string();
        
        let engine = AsyncVolatilityEngine::new(base_path, 4);
        
        engine.create_strand("asset_1".to_string()).await.unwrap();
        engine.create_strand("asset_2".to_string()).await.unwrap();

        let correlation_matrix = vec![
            vec![1.0, 0.5],
            vec![0.5, 1.0],
        ];

        let base_params = vec![
            BrownianMotionParameters {
                mu: 0.05,
                sigma: 0.2,
                dt: 1.0 / 252.0,
                initial_value: 100.0,
                correlation_matrix: None,
                seed: Some(42),
            },
            BrownianMotionParameters {
                mu: 0.03,
                sigma: 0.15,
                dt: 1.0 / 252.0,
                initial_value: 50.0,
                correlation_matrix: None,
                seed: Some(43),
            },
        ];

        let results = engine.simulate_correlated_assets(
            vec!["asset_1".to_string(), "asset_2".to_string()],
            correlation_matrix,
            base_params,
            100,
        ).await.unwrap();

        assert_eq!(results.len(), 2);
        assert!(results.contains_key("asset_1"));
        assert!(results.contains_key("asset_2"));
    }
}
