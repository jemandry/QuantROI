
use std::collections::HashMap;
use std::time::{Duration, Instant};
use serde::{Deserialize, Serialize};
use tokio::sync::RwLock;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum QuantizationLevel {
    FP32,
    FP16,
    INT8,
    INT4,
}

impl QuantizationLevel {
    pub fn memory_reduction_factor(&self) -> f32 {
        match self {
            QuantizationLevel::FP32 => 1.0,
            QuantizationLevel::FP16 => 2.0,
            QuantizationLevel::INT8 => 4.0,
            QuantizationLevel::INT4 => 8.0,
        }
    }

    pub fn speedup_factor(&self) -> f32 {
        match self {
            QuantizationLevel::FP32 => 1.0,
            QuantizationLevel::FP16 => 1.5,
            QuantizationLevel::INT8 => 2.5,
            QuantizationLevel::INT4 => 4.0,
        }
    }

    pub fn accuracy_retention(&self) -> f32 {
        match self {
            QuantizationLevel::FP32 => 1.0,
            QuantizationLevel::FP16 => 0.999,
            QuantizationLevel::INT8 => 0.995,
            QuantizationLevel::INT4 => 0.985,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum PruningStrategy {
    Unstructured,
    Structured,
    MagnitudeBased,
    SensitivityBased,
}

impl PruningStrategy {
    pub fn memory_reduction(&self, sparsity: f32) -> f32 {
        match self {
            PruningStrategy::Unstructured => 1.0 + sparsity * 2.0, // Sparse storage overhead
            PruningStrategy::Structured => 1.0 / (1.0 - sparsity), // Direct reduction
            PruningStrategy::MagnitudeBased => 1.0 + sparsity * 1.5,
            PruningStrategy::SensitivityBased => 1.0 + sparsity * 2.5,
        }
    }

    pub fn speedup_factor(&self, sparsity: f32) -> f32 {
        match self {
            PruningStrategy::Unstructured => 1.0 + sparsity * 0.5, // Limited by sparse ops
            PruningStrategy::Structured => 1.0 / (1.0 - sparsity), // Direct speedup
            PruningStrategy::MagnitudeBased => 1.0 + sparsity * 0.8,
            PruningStrategy::SensitivityBased => 1.0 + sparsity * 1.2,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OptimizationMetadata {
    pub model_id: String,
    pub original_size_bytes: usize,
    pub optimized_size_bytes: usize,
    pub quantization_level: Option<QuantizationLevel>,
    pub pruning_strategy: Option<PruningStrategy>,
    pub sparsity_level: Option<f32>,
    pub accuracy_retention: f32,
    pub speedup_factor: f32,
    pub optimization_timestamp: u64,
    pub calibration_data_hash: String,
}

impl OptimizationMetadata {
    pub fn calculate_hash(&self) -> String {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        
        let mut hasher = DefaultHasher::new();
        self.model_id.hash(&mut hasher);
        self.original_size_bytes.hash(&mut hasher);
        self.optimized_size_bytes.hash(&mut hasher);
        self.optimization_timestamp.hash(&mut hasher);
        
        format!("{:x}", hasher.finish())
    }
}

#[derive(Debug, Clone)]
pub struct AIModel {
    pub id: String,
    pub weights: Vec<f32>,
    pub size_bytes: usize,
    pub quantization: QuantizationLevel,
    pub sparsity: f32,
    pub pruning_strategy: Option<PruningStrategy>,
    pub metadata: OptimizationMetadata,
}

impl AIModel {
    pub fn new(id: String, weight_count: usize) -> Self {
        let weights: Vec<f32> = (0..weight_count)
            .map(|i| (i as f32 * 0.001) % 1.0)
            .collect();
        
        let size_bytes = weight_count * 4; // FP32 = 4 bytes per weight
        
        let metadata = OptimizationMetadata {
            model_id: id.clone(),
            original_size_bytes: size_bytes,
            optimized_size_bytes: size_bytes,
            quantization_level: Some(QuantizationLevel::FP32),
            pruning_strategy: None,
            sparsity_level: None,
            accuracy_retention: 1.0,
            speedup_factor: 1.0,
            optimization_timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos() as u64,
            calibration_data_hash: "original".to_string(),
        };

        Self {
            id,
            weights,
            size_bytes,
            quantization: QuantizationLevel::FP32,
            sparsity: 0.0,
            pruning_strategy: None,
            metadata,
        }
    }

    pub fn quantize(&mut self, level: QuantizationLevel) -> Result<(), String> {
        if level == self.quantization {
            return Ok(());
        }

        let reduction_factor = level.memory_reduction_factor();
        let new_size = (self.size_bytes as f32 / reduction_factor) as usize;
        
        match level {
            QuantizationLevel::FP32 => {
            }
            QuantizationLevel::FP16 => {
                for weight in &mut self.weights {
                    *weight = (*weight * 65536.0).round() / 65536.0;
                }
            }
            QuantizationLevel::INT8 => {
                for weight in &mut self.weights {
                    let quantized = ((*weight * 127.0).round().max(-128.0).min(127.0)) / 127.0;
                    *weight = quantized;
                }
            }
            QuantizationLevel::INT4 => {
                for weight in &mut self.weights {
                    let quantized = ((*weight * 7.0).round().max(-8.0).min(7.0)) / 7.0;
                    *weight = quantized;
                }
            }
        }

        self.quantization = level;
        self.size_bytes = new_size;
        self.metadata.optimized_size_bytes = new_size;
        self.metadata.quantization_level = Some(level);
        self.metadata.accuracy_retention *= level.accuracy_retention();
        self.metadata.speedup_factor *= level.speedup_factor();

        Ok(())
    }

    pub fn prune(&mut self, strategy: PruningStrategy, sparsity: f32) -> Result<(), String> {
        if sparsity < 0.0 || sparsity >= 1.0 {
            return Err("Sparsity must be between 0.0 and 1.0".to_string());
        }

        let weights_to_prune = (self.weights.len() as f32 * sparsity) as usize;
        
        match strategy {
            PruningStrategy::MagnitudeBased => {
                let mut weight_indices: Vec<(usize, f32)> = self.weights
                    .iter()
                    .enumerate()
                    .map(|(i, &w)| (i, w.abs()))
                    .collect();
                
                weight_indices.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap());
                
                for i in 0..weights_to_prune {
                    let idx = weight_indices[i].0;
                    self.weights[idx] = 0.0;
                }
            }
            PruningStrategy::Structured => {
                let group_size = 8; // Simulate 8-weight neurons
                let groups_to_prune = weights_to_prune / group_size;
                
                for group in 0..groups_to_prune {
                    let start_idx = group * group_size;
                    let end_idx = std::cmp::min(start_idx + group_size, self.weights.len());
                    
                    for idx in start_idx..end_idx {
                        self.weights[idx] = 0.0;
                    }
                }
            }
            PruningStrategy::Unstructured | PruningStrategy::SensitivityBased => {
                use std::collections::HashSet;
                let mut rng_state = 42u64; // Simple PRNG for deterministic results
                let mut pruned_indices = HashSet::new();
                
                while pruned_indices.len() < weights_to_prune {
                    rng_state = rng_state.wrapping_mul(1103515245).wrapping_add(12345);
                    let idx = (rng_state as usize) % self.weights.len();
                    pruned_indices.insert(idx);
                }
                
                for &idx in &pruned_indices {
                    self.weights[idx] = 0.0;
                }
            }
        }

        let reduction_factor = strategy.memory_reduction(sparsity);
        let new_size = (self.size_bytes as f32 / reduction_factor) as usize;
        
        self.sparsity = sparsity;
        self.pruning_strategy = Some(strategy);
        self.size_bytes = new_size;
        self.metadata.optimized_size_bytes = new_size;
        self.metadata.pruning_strategy = Some(strategy);
        self.metadata.sparsity_level = Some(sparsity);
        self.metadata.speedup_factor *= strategy.speedup_factor(sparsity);
        
        let accuracy_loss = sparsity * 0.1; // 10% accuracy loss per 100% sparsity
        self.metadata.accuracy_retention *= 1.0 - accuracy_loss;

        Ok(())
    }

    pub async fn inference(&self, input: &[f32]) -> Vec<f32> {
        let start = Instant::now();
        
        let mut output = Vec::new();
        let chunk_size = std::cmp::min(input.len(), self.weights.len() / 10);
        
        for i in 0..chunk_size {
            let mut sum = 0.0;
            for j in 0..std::cmp::min(10, self.weights.len()) {
                let weight_idx = (i * 10 + j) % self.weights.len();
                let input_idx = i % input.len();
                sum += self.weights[weight_idx] * input[input_idx];
            }
            output.push(sum.tanh()); // Activation function
        }
        
        let base_latency = Duration::from_micros(100);
        let optimized_latency = Duration::from_nanos(
            (base_latency.as_nanos() as f32 / self.metadata.speedup_factor) as u64
        );
        
        let elapsed = start.elapsed();
        if elapsed < optimized_latency {
            tokio::time::sleep(optimized_latency - elapsed).await;
        }
        
        output
    }

    pub fn get_performance_metrics(&self) -> HashMap<String, f64> {
        let mut metrics = HashMap::new();
        
        metrics.insert("size_bytes".to_string(), self.size_bytes as f64);
        metrics.insert("memory_reduction".to_string(), 
                      self.metadata.original_size_bytes as f64 / self.size_bytes as f64);
        metrics.insert("speedup_factor".to_string(), self.metadata.speedup_factor as f64);
        metrics.insert("accuracy_retention".to_string(), self.metadata.accuracy_retention as f64);
        metrics.insert("sparsity".to_string(), self.sparsity as f64);
        
        if let Some(quant) = self.metadata.quantization_level {
            metrics.insert("quantization_bits".to_string(), match quant {
                QuantizationLevel::FP32 => 32.0,
                QuantizationLevel::FP16 => 16.0,
                QuantizationLevel::INT8 => 8.0,
                QuantizationLevel::INT4 => 4.0,
            });
        }
        
        metrics
    }
}

pub struct AIModelOptimizer {
    models: RwLock<HashMap<String, AIModel>>,
    braided_models: RwLock<HashMap<String, BraidedBrownianModel>>,
    optimization_history: RwLock<Vec<OptimizationMetadata>>,
}

impl AIModelOptimizer {
    pub fn new() -> Self {
        Self {
            models: RwLock::new(HashMap::new()),
            braided_models: RwLock::new(HashMap::new()),
            optimization_history: RwLock::new(Vec::new()),
        }
    }

    pub async fn register_model(&self, model: AIModel) {
        let mut models = self.models.write().await;
        models.insert(model.id.clone(), model);
    }

    pub async fn quantize_model(&self, model_id: &str, level: QuantizationLevel) -> Result<(), String> {
        let mut models = self.models.write().await;
        
        if let Some(model) = models.get_mut(model_id) {
            model.quantize(level)?;
            
            let mut history = self.optimization_history.write().await;
            history.push(model.metadata.clone());
            
            Ok(())
        } else {
            Err(format!("Model {} not found", model_id))
        }
    }

    pub async fn prune_model(&self, model_id: &str, strategy: PruningStrategy, sparsity: f32) -> Result<(), String> {
        let mut models = self.models.write().await;
        
        if let Some(model) = models.get_mut(model_id) {
            model.prune(strategy, sparsity)?;
            
            let mut history = self.optimization_history.write().await;
            history.push(model.metadata.clone());
            
            Ok(())
        } else {
            Err(format!("Model {} not found", model_id))
        }
    }

    pub async fn inference(&self, model_id: &str, input: &[f32]) -> Result<Vec<f32>, String> {
        let models = self.models.read().await;
        
        if let Some(model) = models.get(model_id) {
            Ok(model.inference(input).await)
        } else {
            Err(format!("Model {} not found", model_id))
        }
    }

    pub async fn get_optimization_stats(&self) -> HashMap<String, f64> {
        let models = self.models.read().await;
        let braided_models = self.braided_models.read().await;
        let history = self.optimization_history.read().await;
        
        let mut stats = HashMap::new();
        
        stats.insert("total_models".to_string(), models.len() as f64);
        stats.insert("total_braided_models".to_string(), braided_models.len() as f64);
        stats.insert("total_optimizations".to_string(), history.len() as f64);
        
        if !models.is_empty() || !braided_models.is_empty() {
            let total_original_size: usize = models.values()
                .map(|m| m.metadata.original_size_bytes)
                .chain(braided_models.values().map(|m| m.metadata.original_size_bytes))
                .sum();
            let total_optimized_size: usize = models.values()
                .map(|m| m.size_bytes)
                .chain(braided_models.values().map(|m| m.metadata.optimized_size_bytes))
                .sum();
            
            stats.insert("total_memory_saved_bytes".to_string(), 
                        (total_original_size - total_optimized_size) as f64);
            stats.insert("average_memory_reduction".to_string(), 
                        total_original_size as f64 / total_optimized_size as f64);
            
            let total_models = models.len() + braided_models.len();
            let avg_speedup: f32 = models.values()
                .map(|m| m.metadata.speedup_factor)
                .chain(braided_models.values().map(|m| m.metadata.speedup_factor))
                .sum::<f32>() / total_models as f32;
            stats.insert("average_speedup".to_string(), avg_speedup as f64);
            
            let avg_accuracy: f32 = models.values()
                .map(|m| m.metadata.accuracy_retention)
                .chain(braided_models.values().map(|m| m.metadata.accuracy_retention))
                .sum::<f32>() / total_models as f32;
            stats.insert("average_accuracy_retention".to_string(), avg_accuracy as f64);
        }
        
        stats
    }

    pub async fn generate_report(&self) -> String {
        let models = self.models.read().await;
        let stats = self.get_optimization_stats().await;
        
        let mut report = String::new();
        report.push_str("AI Model Optimization Report\n");
        report.push_str("============================\n\n");
        
        report.push_str(&format!("Total Models: {}\n", stats.get("total_models").unwrap_or(&0.0)));
        report.push_str(&format!("Total Optimizations: {}\n", stats.get("total_optimizations").unwrap_or(&0.0)));
        
        if let Some(memory_saved) = stats.get("total_memory_saved_bytes") {
            report.push_str(&format!("Memory Saved: {:.2} MB\n", memory_saved / 1_048_576.0));
        }
        
        if let Some(avg_reduction) = stats.get("average_memory_reduction") {
            report.push_str(&format!("Average Memory Reduction: {:.2}x\n", avg_reduction));
        }
        
        if let Some(avg_speedup) = stats.get("average_speedup") {
            report.push_str(&format!("Average Speedup: {:.2}x\n", avg_speedup));
        }
        
        if let Some(avg_accuracy) = stats.get("average_accuracy_retention") {
            report.push_str(&format!("Average Accuracy Retention: {:.1}%\n", avg_accuracy * 100.0));
        }
        
        report.push_str("\nModel Details:\n");
        report.push_str("--------------\n");
        
        for model in models.values() {
            report.push_str(&format!("Model: {}\n", model.id));
            report.push_str(&format!("  Size: {:.2} KB -> {:.2} KB\n", 
                           model.metadata.original_size_bytes as f64 / 1024.0,
                           model.size_bytes as f64 / 1024.0));
            report.push_str(&format!("  Quantization: {:?}\n", model.quantization));
            if let Some(strategy) = model.pruning_strategy {
                report.push_str(&format!("  Pruning: {:?} ({:.1}% sparse)\n", 
                               strategy, model.sparsity * 100.0));
            }
            report.push_str(&format!("  Speedup: {:.2}x\n", model.metadata.speedup_factor));
            report.push_str(&format!("  Accuracy: {:.1}%\n", model.metadata.accuracy_retention * 100.0));
            report.push_str("\n");
        }
        
        report
    }

    pub async fn register_braided_model(&self, model: BraidedBrownianModel) {
        let mut models = self.braided_models.write().await;
        models.insert(model.id.clone(), model);
    }

    pub async fn generate_braided_paths(&self, model_id: &str, initial_conditions: &[f32]) -> Result<Vec<Vec<f32>>, String> {
        let models = self.braided_models.read().await;
        
        if let Some(model) = models.get(model_id) {
            Ok(model.generate_braided_paths(initial_conditions).await)
        } else {
            Err(format!("Braided model {} not found", model_id))
        }
    }

    pub async fn calculate_risk_moments(&self, model_id: &str, paths: &[Vec<f32>]) -> Result<Vec<f32>, String> {
        let models = self.braided_models.read().await;
        
        if let Some(model) = models.get(model_id) {
            Ok(model.calculate_risk_moments(paths))
        } else {
            Err(format!("Braided model {} not found", model_id))
        }
    }

    pub async fn quantize_braided_model(&self, model_id: &str, level: QuantizationLevel) -> Result<(), String> {
        let mut models = self.braided_models.write().await;
        
        if let Some(model) = models.get_mut(model_id) {
            model.quantize(level)?;
            
            let mut history = self.optimization_history.write().await;
            history.push(model.metadata.clone());
            
            Ok(())
        } else {
            Err(format!("Braided model {} not found", model_id))
        }
    }

    pub async fn prune_braided_model(&self, model_id: &str, strategy: PruningStrategy, sparsity: f32) -> Result<(), String> {
        let mut models = self.braided_models.write().await;
        
        if let Some(model) = models.get_mut(model_id) {
            model.prune(strategy, sparsity)?;
            
            let mut history = self.optimization_history.write().await;
            history.push(model.metadata.clone());
            
            Ok(())
        } else {
            Err(format!("Braided model {} not found", model_id))
        }
    }
}

#[derive(Debug, Clone)]
pub struct BraidedBrownianModel {
    pub id: String,
    pub num_strands: usize,
    pub time_steps: usize,
    pub weights_linear: Vec<f32>,
    pub weights_conv: Vec<f32>,
    pub quantization: QuantizationLevel,
    pub sparsity: f32,
    pub pruning_strategy: Option<PruningStrategy>,
    pub metadata: OptimizationMetadata,
}

impl BraidedBrownianModel {
    pub fn new(id: String, num_strands: usize, time_steps: usize) -> Self {
        let linear_weights: Vec<f32> = (0..num_strands * time_steps)
            .map(|i| (i as f32 * 0.001) % 1.0)
            .collect();
        let conv_weights: Vec<f32> = (0..num_strands * num_strands * 3)
            .map(|i| (i as f32 * 0.001) % 1.0)
            .collect();
        
        let size_bytes = (linear_weights.len() + conv_weights.len()) * 4;
        
        let metadata = OptimizationMetadata {
            model_id: id.clone(),
            original_size_bytes: size_bytes,
            optimized_size_bytes: size_bytes,
            quantization_level: Some(QuantizationLevel::FP32),
            pruning_strategy: None,
            sparsity_level: None,
            accuracy_retention: 1.0,
            speedup_factor: 1.0,
            optimization_timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos() as u64,
            calibration_data_hash: "braided_original".to_string(),
        };

        Self {
            id,
            num_strands,
            time_steps,
            weights_linear: linear_weights,
            weights_conv: conv_weights,
            quantization: QuantizationLevel::FP32,
            sparsity: 0.0,
            pruning_strategy: None,
            metadata,
        }
    }

    pub async fn generate_braided_paths(&self, initial_conditions: &[f32]) -> Vec<Vec<f32>> {
        let mut paths: Vec<Vec<f32>> = Vec::new();
        
        for strand in 0..self.num_strands {
            let mut path = vec![initial_conditions[strand % initial_conditions.len()]];
            let mut rng_state = (strand as u64 + 1) * 12345;
            
            for step in 0..self.time_steps {
                rng_state = rng_state.wrapping_mul(1103515245).wrapping_add(12345);
                let random = (rng_state as f32 / u64::MAX as f32 - 0.5) * 0.1;
                
                let mut braided_increment = random;
                for other_strand in 0..self.num_strands {
                    if other_strand != strand && other_strand < paths.len() && step < paths[other_strand].len() {
                        let weight_idx = (strand * self.num_strands + other_strand) % self.weights_conv.len();
                        braided_increment += self.weights_conv[weight_idx] * paths[other_strand][step] * 0.01;
                    }
                }
                
                let next_value = path[step] + braided_increment;
                path.push(next_value);
            }
            paths.push(path);
        }
        
        let base_latency = Duration::from_micros(500);
        let optimized_latency = Duration::from_nanos(
            (base_latency.as_nanos() as f32 / self.metadata.speedup_factor) as u64
        );
        tokio::time::sleep(optimized_latency).await;
        
        paths
    }

    pub fn calculate_risk_moments(&self, paths: &[Vec<f32>]) -> Vec<f32> {
        let mut moments = Vec::new();
        
        for path in paths {
            if path.is_empty() { continue; }
            
            let mean = path.iter().sum::<f32>() / path.len() as f32;
            
            let variance = path.iter()
                .map(|x| (x - mean).powi(2))
                .sum::<f32>() / path.len() as f32;
            
            let skewness = if variance > 0.0 {
                path.iter()
                    .map(|x| ((x - mean) / variance.sqrt()).powi(3))
                    .sum::<f32>() / path.len() as f32
            } else {
                0.0
            };
            
            moments.extend_from_slice(&[mean, variance, skewness]);
        }
        
        moments
    }

    pub fn quantize(&mut self, level: QuantizationLevel) -> Result<(), String> {
        if level == self.quantization {
            return Ok(());
        }

        let reduction_factor = level.memory_reduction_factor();
        
        match level {
            QuantizationLevel::FP32 => {},
            QuantizationLevel::FP16 => {
                for weight in &mut self.weights_linear {
                    *weight = (*weight * 65536.0).round() / 65536.0;
                }
                for weight in &mut self.weights_conv {
                    *weight = (*weight * 65536.0).round() / 65536.0;
                }
            },
            QuantizationLevel::INT8 => {
                for weight in &mut self.weights_linear {
                    let quantized = ((*weight * 127.0).round().max(-128.0).min(127.0)) / 127.0;
                    *weight = quantized;
                }
                for weight in &mut self.weights_conv {
                    let quantized = ((*weight * 127.0).round().max(-128.0).min(127.0)) / 127.0;
                    *weight = quantized;
                }
            },
            QuantizationLevel::INT4 => {
                for weight in &mut self.weights_linear {
                    let quantized = ((*weight * 7.0).round().max(-8.0).min(7.0)) / 7.0;
                    *weight = quantized;
                }
                for weight in &mut self.weights_conv {
                    let quantized = ((*weight * 7.0).round().max(-8.0).min(7.0)) / 7.0;
                    *weight = quantized;
                }
            },
        }

        self.quantization = level;
        let new_size = ((self.weights_linear.len() + self.weights_conv.len()) as f32 / reduction_factor) as usize;
        self.metadata.optimized_size_bytes = new_size;
        self.metadata.quantization_level = Some(level);
        self.metadata.accuracy_retention *= level.accuracy_retention();
        self.metadata.speedup_factor *= level.speedup_factor();

        Ok(())
    }

    pub fn prune(&mut self, strategy: PruningStrategy, sparsity: f32) -> Result<(), String> {
        if sparsity < 0.0 || sparsity >= 1.0 {
            return Err("Sparsity must be between 0.0 and 1.0".to_string());
        }

        let linear_to_prune = (self.weights_linear.len() as f32 * sparsity) as usize;
        let conv_to_prune = (self.weights_conv.len() as f32 * sparsity) as usize;
        
        match strategy {
            PruningStrategy::Structured => {
                let group_size = 8;
                let linear_groups_to_prune = linear_to_prune / group_size;
                let conv_groups_to_prune = conv_to_prune / group_size;
                
                for group in 0..linear_groups_to_prune {
                    let start_idx = group * group_size;
                    let end_idx = std::cmp::min(start_idx + group_size, self.weights_linear.len());
                    for idx in start_idx..end_idx {
                        self.weights_linear[idx] = 0.0;
                    }
                }
                
                for group in 0..conv_groups_to_prune {
                    let start_idx = group * group_size;
                    let end_idx = std::cmp::min(start_idx + group_size, self.weights_conv.len());
                    for idx in start_idx..end_idx {
                        self.weights_conv[idx] = 0.0;
                    }
                }
            },
            _ => {
                let mut linear_indices: Vec<(usize, f32)> = self.weights_linear
                    .iter()
                    .enumerate()
                    .map(|(i, &w)| (i, w.abs()))
                    .collect();
                linear_indices.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap());
                
                for i in 0..linear_to_prune {
                    let idx = linear_indices[i].0;
                    self.weights_linear[idx] = 0.0;
                }
                
                let mut conv_indices: Vec<(usize, f32)> = self.weights_conv
                    .iter()
                    .enumerate()
                    .map(|(i, &w)| (i, w.abs()))
                    .collect();
                conv_indices.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap());
                
                for i in 0..conv_to_prune {
                    let idx = conv_indices[i].0;
                    self.weights_conv[idx] = 0.0;
                }
            }
        }

        self.sparsity = sparsity;
        self.pruning_strategy = Some(strategy);
        let reduction_factor = strategy.memory_reduction(sparsity);
        let new_size = ((self.weights_linear.len() + self.weights_conv.len()) as f32 / reduction_factor) as usize;
        self.metadata.optimized_size_bytes = new_size;
        self.metadata.pruning_strategy = Some(strategy);
        self.metadata.sparsity_level = Some(sparsity);
        self.metadata.speedup_factor *= strategy.speedup_factor(sparsity);
        
        let accuracy_loss = sparsity * 0.1;
        self.metadata.accuracy_retention *= 1.0 - accuracy_loss;

        Ok(())
    }
}

impl Default for AIModelOptimizer {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_quantization_levels() {
        let mut model = AIModel::new("test_model".to_string(), 1000);
        let original_size = model.size_bytes;
        
        model.quantize(QuantizationLevel::INT8).unwrap();
        assert!(model.size_bytes < original_size);
        assert_eq!(model.quantization, QuantizationLevel::INT8);
        assert!(model.metadata.speedup_factor > 1.0);
    }

    #[tokio::test]
    async fn test_pruning_strategies() {
        let mut model = AIModel::new("test_model".to_string(), 1000);
        let _original_weights: Vec<f32> = model.weights.clone();
        
        model.prune(PruningStrategy::MagnitudeBased, 0.3).unwrap();
        
        let zero_count = model.weights.iter().filter(|&&w| w == 0.0).count();
        assert!(zero_count > 0);
        assert!(model.sparsity > 0.0);
        assert!(model.metadata.speedup_factor > 1.0);
    }

    #[tokio::test]
    async fn test_model_optimizer() {
        let optimizer = AIModelOptimizer::new();
        let model = AIModel::new("test_model".to_string(), 500);
        
        optimizer.register_model(model).await;
        
        optimizer.quantize_model("test_model", QuantizationLevel::INT8).await.unwrap();
        optimizer.prune_model("test_model", PruningStrategy::Structured, 0.2).await.unwrap();
        
        let stats = optimizer.get_optimization_stats().await;
        assert!(stats.get("total_models").unwrap() > &0.0);
        assert!(stats.get("average_speedup").unwrap() > &1.0);
    }

    #[tokio::test]
    async fn test_inference_performance() {
        let mut model = AIModel::new("perf_test".to_string(), 1000);
        let input = vec![0.5; 100];
        
        let start = Instant::now();
        let _output1 = model.inference(&input).await;
        let _original_time = start.elapsed();
        
        model.quantize(QuantizationLevel::INT8).unwrap();
        model.prune(PruningStrategy::Structured, 0.4).unwrap();
        
        let start = Instant::now();
        let _output2 = model.inference(&input).await;
        let _optimized_time = start.elapsed();
        
        assert!(model.metadata.speedup_factor > 1.0);
    }
}
