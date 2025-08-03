use std::collections::HashMap;
use std::fs::OpenOptions;
use std::io::{Write, Seek, SeekFrom};
use std::sync::Arc;
use tokio::sync::RwLock;
use tokio::fs::File;
use tokio::io::{AsyncWriteExt, AsyncSeekExt};
use memmap2::{MmapMut, MmapOptions};
use serde::{Serialize, Deserialize};
use sha2::{Sha256, Digest};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BrownianMotionParameters {
    pub mu: f64,        
    pub sigma: f64,     
    pub dt: f64,        
    pub initial_value: f64,
    pub correlation_matrix: Option<Vec<Vec<f64>>>,
    pub seed: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VolatilitySimulationRecord {
    pub timestamp_ns: u64,
    pub simulation_id: String,
    pub parameters: BrownianMotionParameters,
    pub path_data: Vec<f64>,
    pub risk_moments: Vec<f64>,
    pub audit_hash: String,
    pub parent_hash: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VolatilityStrandMetadata {
    pub strand_id: String,
    pub creation_timestamp: u64,
    pub total_simulations: u64,
    pub memory_mapped_file_path: String,
    pub current_file_size: u64,
    pub audit_chain_root: String,
}

pub struct BrownianVolatilityStrand {
    metadata: Arc<RwLock<VolatilityStrandMetadata>>,
    memory_mapped_file: Arc<RwLock<Option<MmapMut>>>,
    simulation_index: Arc<RwLock<HashMap<String, u64>>>, 
    audit_chain: Arc<RwLock<Vec<String>>>, 
}

impl BrownianVolatilityStrand {
    pub async fn new(strand_id: String, file_path: String) -> Result<Self, Box<dyn std::error::Error>> {
        let metadata = VolatilityStrandMetadata {
            strand_id: strand_id.clone(),
            creation_timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)?
                .as_nanos() as u64,
            total_simulations: 0,
            memory_mapped_file_path: file_path.clone(),
            current_file_size: 0,
            audit_chain_root: "genesis".to_string(),
        };

        let file = OpenOptions::new()
            .create(true)
            .read(true)
            .write(true)
            .open(&file_path)?;
        
        file.set_len(1024 * 1024)?;
        
        let mmap = unsafe { MmapOptions::new().map_mut(&file)? };

        Ok(Self {
            metadata: Arc::new(RwLock::new(metadata)),
            memory_mapped_file: Arc::new(RwLock::new(Some(mmap))),
            simulation_index: Arc::new(RwLock::new(HashMap::new())),
            audit_chain: Arc::new(RwLock::new(vec!["genesis".to_string()])),
        })
    }

    pub async fn simulate_and_append_gbm(
        &self,
        simulation_id: String,
        parameters: BrownianMotionParameters,
        num_steps: usize,
    ) -> Result<VolatilitySimulationRecord, Box<dyn std::error::Error>> {
        let path = self.generate_gbm_path(&parameters, num_steps).await?;
        
        let risk_moments = self.calculate_risk_moments(&path).await;
        
        let parent_hash = {
            let audit_chain = self.audit_chain.read().await;
            audit_chain.last().cloned()
        };

        let record = VolatilitySimulationRecord {
            timestamp_ns: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)?
                .as_nanos() as u64,
            simulation_id: simulation_id.clone(),
            parameters,
            path_data: path,
            risk_moments,
            audit_hash: String::new(), 
            parent_hash,
        };

        let mut record_with_hash = record.clone();
        record_with_hash.audit_hash = self.calculate_audit_hash(&record).await?;

        self.append_to_mmap(&simulation_id, &record_with_hash).await?;

        {
            let mut audit_chain = self.audit_chain.write().await;
            audit_chain.push(record_with_hash.audit_hash.clone());
        }

        {
            let mut metadata = self.metadata.write().await;
            metadata.total_simulations += 1;
        }

        Ok(record_with_hash)
    }

    async fn generate_gbm_path(
        &self,
        parameters: &BrownianMotionParameters,
        num_steps: usize,
    ) -> Result<Vec<f64>, Box<dyn std::error::Error>> {
        use rand::prelude::*;
        use rand_chacha::ChaCha8Rng;

        let mut rng = if let Some(seed) = parameters.seed {
            ChaCha8Rng::seed_from_u64(seed)
        } else {
            ChaCha8Rng::from_entropy()
        };

        let mut path = Vec::with_capacity(num_steps + 1);
        path.push(parameters.initial_value);

        let sqrt_dt = parameters.dt.sqrt();
        let drift_term = parameters.mu - 0.5 * parameters.sigma * parameters.sigma;

        for _ in 0..num_steps {
            let dw = rng.sample::<f64, _>(rand_distr::StandardNormal) * sqrt_dt;
            let current_value = path.last().unwrap();
            
            let next_value = current_value * (
                1.0 + drift_term * parameters.dt + parameters.sigma * dw
            );
            
            path.push(next_value);
        }

        Ok(path)
    }

    async fn calculate_risk_moments(&self, path: &[f64]) -> Vec<f64> {
        if path.len() < 2 {
            return vec![0.0, 0.0, 0.0, 0.0]; 
        }

        let returns: Vec<f64> = path.windows(2)
            .map(|w| (w[1] - w[0]) / w[0])
            .collect();

        let n = returns.len() as f64;
        let mean = returns.iter().sum::<f64>() / n;
        
        let variance = returns.iter()
            .map(|r| (r - mean).powi(2))
            .sum::<f64>() / n;
        
        let std_dev = variance.sqrt();
        
        let skewness = if std_dev > 0.0 {
            returns.iter()
                .map(|r| ((r - mean) / std_dev).powi(3))
                .sum::<f64>() / n
        } else {
            0.0
        };
        
        let kurtosis = if std_dev > 0.0 {
            returns.iter()
                .map(|r| ((r - mean) / std_dev).powi(4))
                .sum::<f64>() / n - 3.0 
        } else {
            0.0
        };

        vec![mean, variance, skewness, kurtosis]
    }

    async fn calculate_audit_hash(
        &self,
        record: &VolatilitySimulationRecord,
    ) -> Result<String, Box<dyn std::error::Error>> {
        let mut hasher = Sha256::new();
        
        hasher.update(record.timestamp_ns.to_be_bytes());
        hasher.update(record.simulation_id.as_bytes());
        hasher.update(serde_json::to_string(&record.parameters)?.as_bytes());
        hasher.update(serde_json::to_string(&record.path_data)?.as_bytes());
        hasher.update(serde_json::to_string(&record.risk_moments)?.as_bytes());
        
        if let Some(parent_hash) = &record.parent_hash {
            hasher.update(parent_hash.as_bytes());
        }

        Ok(format!("{:x}", hasher.finalize()))
    }

    async fn append_to_mmap(
        &self,
        simulation_id: &str,
        record: &VolatilitySimulationRecord,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let serialized = serde_json::to_vec(record)?;
        let record_size = serialized.len() as u64;

        {
            let mut mmap_guard = self.memory_mapped_file.write().await;
            let mut metadata_guard = self.metadata.write().await;
            let mut index_guard = self.simulation_index.write().await;

            if let Some(ref mut mmap) = *mmap_guard {
                let current_offset = metadata_guard.current_file_size;
                
                if current_offset + record_size + 8 > mmap.len() as u64 {
                    let new_size = (mmap.len() * 2).max((current_offset + record_size + 8) as usize);
                    
                    mmap.flush()?;
                    drop(mmap_guard);

                    let file = OpenOptions::new()
                        .write(true)
                        .open(&metadata_guard.memory_mapped_file_path)?;
                    file.set_len(new_size as u64)?;

                    let new_mmap = unsafe { MmapOptions::new().map_mut(&file)? };
                    *self.memory_mapped_file.write().await = Some(new_mmap);
                    
                    mmap_guard = self.memory_mapped_file.write().await;
                }

                if let Some(ref mut mmap) = *mmap_guard {
                    let size_bytes = record_size.to_le_bytes();
                    mmap[current_offset as usize..(current_offset + 8) as usize]
                        .copy_from_slice(&size_bytes);
                    
                    let data_start = (current_offset + 8) as usize;
                    let data_end = data_start + serialized.len();
                    mmap[data_start..data_end].copy_from_slice(&serialized);
                    
                    index_guard.insert(simulation_id.to_string(), current_offset);
                    metadata_guard.current_file_size = current_offset + 8 + record_size;
                    
                    mmap.flush()?;
                }
            }
        }

        Ok(())
    }

    pub async fn get_simulation(
        &self,
        simulation_id: &str,
    ) -> Result<Option<VolatilitySimulationRecord>, Box<dyn std::error::Error>> {
        let index_guard = self.simulation_index.read().await;
        let mmap_guard = self.memory_mapped_file.read().await;

        if let (Some(offset), Some(ref mmap)) = (index_guard.get(simulation_id), &*mmap_guard) {
            let size_bytes = &mmap[*offset as usize..(*offset + 8) as usize];
            let record_size = u64::from_le_bytes(size_bytes.try_into()?);
            
            let data_start = (*offset + 8) as usize;
            let data_end = data_start + record_size as usize;
            let record_data = &mmap[data_start..data_end];
            
            let record: VolatilitySimulationRecord = serde_json::from_slice(record_data)?;
            Ok(Some(record))
        } else {
            Ok(None)
        }
    }

    pub async fn verify_audit_chain(&self) -> Result<bool, Box<dyn std::error::Error>> {
        let audit_chain = self.audit_chain.read().await;
        let index_guard = self.simulation_index.read().await;

        for (i, hash) in audit_chain.iter().skip(1).enumerate() {
            let mut found = false;
            for (sim_id, _offset) in index_guard.iter() {
                if let Ok(Some(record)) = self.get_simulation(sim_id).await {
                    if record.audit_hash == *hash {
                        if i > 0 {
                            let expected_parent = &audit_chain[i];
                            if record.parent_hash.as_ref() != Some(expected_parent) {
                                return Ok(false);
                            }
                        }
                        found = true;
                        break;
                    }
                }
            }
            if !found {
                return Ok(false);
            }
        }

        Ok(true)
    }

    pub async fn get_metadata(&self) -> VolatilityStrandMetadata {
        self.metadata.read().await.clone()
    }

    pub async fn get_simulation_count(&self) -> u64 {
        self.metadata.read().await.total_simulations
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::NamedTempFile;

    #[tokio::test]
    async fn test_brownian_volatility_strand() {
        let temp_file = NamedTempFile::new().unwrap();
        let file_path = temp_file.path().to_string_lossy().to_string();
        
        let strand = BrownianVolatilityStrand::new(
            "test_strand".to_string(),
            file_path,
        ).await.unwrap();

        let parameters = BrownianMotionParameters {
            mu: 0.05,
            sigma: 0.2,
            dt: 1.0 / 252.0, 
            initial_value: 100.0,
            correlation_matrix: None,
            seed: Some(42),
        };

        let record = strand.simulate_and_append_gbm(
            "test_sim_1".to_string(),
            parameters,
            100,
        ).await.unwrap();

        assert_eq!(record.simulation_id, "test_sim_1");
        assert_eq!(record.path_data.len(), 101); 
        assert_eq!(record.risk_moments.len(), 4); 

        let retrieved = strand.get_simulation("test_sim_1").await.unwrap().unwrap();
        assert_eq!(retrieved.simulation_id, record.simulation_id);
        assert_eq!(retrieved.audit_hash, record.audit_hash);

        assert!(strand.verify_audit_chain().await.unwrap());

        let metadata = strand.get_metadata().await;
        assert_eq!(metadata.total_simulations, 1);
    }

    #[tokio::test]
    async fn test_multiple_simulations_audit_chain() {
        let temp_file = NamedTempFile::new().unwrap();
        let file_path = temp_file.path().to_string_lossy().to_string();
        
        let strand = BrownianVolatilityStrand::new(
            "test_strand".to_string(),
            file_path,
        ).await.unwrap();

        let parameters = BrownianMotionParameters {
            mu: 0.05,
            sigma: 0.2,
            dt: 1.0 / 252.0,
            initial_value: 100.0,
            correlation_matrix: None,
            seed: Some(42),
        };

        for i in 0..5 {
            strand.simulate_and_append_gbm(
                format!("test_sim_{}", i),
                parameters.clone(),
                50,
            ).await.unwrap();
        }

        for i in 0..5 {
            let sim = strand.get_simulation(&format!("test_sim_{}", i)).await.unwrap();
            assert!(sim.is_some());
        }

        assert!(strand.verify_audit_chain().await.unwrap());

        let metadata = strand.get_metadata().await;
        assert_eq!(metadata.total_simulations, 5);
    }
}
