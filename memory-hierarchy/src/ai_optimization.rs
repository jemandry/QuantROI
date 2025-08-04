use std::collections::HashMap;
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use tokio::sync::RwLock;
use std::hash::{Hash, Hasher};

#[derive(Debug, Clone, Copy, PartialEq)]
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
            QuantizationLevel::FP16 => 0.99,
            QuantizationLevel::INT8 => 0.95,
            QuantizationLevel::INT4 => 0.85,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum PruningStrategy {
    MagnitudeBased,
    Structured,
    Gradual,
}

impl PruningStrategy {
    pub fn memory_reduction(&self, sparsity: f32) -> f32 {
        match self {
            PruningStrategy::MagnitudeBased => 1.0 + sparsity * 2.0,
            PruningStrategy::Structured => 1.0 + sparsity * 3.0,
            PruningStrategy::Gradual => 1.0 + sparsity * 1.5,
        }
    }

    pub fn speedup_factor(&self, sparsity: f32) -> f32 {
        match self {
            PruningStrategy::MagnitudeBased => 1.0 + sparsity * 1.2,
            PruningStrategy::Structured => 1.0 + sparsity * 2.0,
            PruningStrategy::Gradual => 1.0 + sparsity * 0.8,
        }
    }
}

#[derive(Debug, Clone)]
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
    pub fn new(id: String, num_weights: usize) -> Self {
        let weights: Vec<f32> = (0..num_weights)
            .map(|i| (i as f32 * 0.001) % 1.0)
            .collect();
        
        let size_bytes = weights.len() * 4;
        
        let metadata = OptimizationMetadata {
            model_id: id.clone(),
            original_size_bytes: size_bytes,
            optimized_size_bytes: size_bytes,
            quantization_level: Some(QuantizationLevel::FP32),
            pruning_strategy: None,
            sparsity_level: None,
            accuracy_retention: 1.0,
            speedup_factor: 1.0,
            optimization_timestamp: SystemTime::now()
                .duration_since(UNIX_EPOCH)
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
        
        match level {
            QuantizationLevel::FP32 => {},
            QuantizationLevel::FP16 => {
                for weight in &mut self.weights {
                    *weight = (*weight * 65536.0).round() / 65536.0;
                }
            },
            QuantizationLevel::INT8 => {
                for weight in &mut self.weights {
                    let quantized = (*weight * 127.0).round().clamp(-128.0, 127.0) / 127.0;
                    *weight = quantized;
                }
            },
            QuantizationLevel::INT4 => {
                for weight in &mut self.weights {
                    let quantized = (*weight * 7.0).round().clamp(-8.0, 7.0) / 7.0;
                    *weight = quantized;
                }
            },
        }

        self.quantization = level;
        self.size_bytes = (self.size_bytes as f32 / reduction_factor) as usize;
        self.metadata.optimized_size_bytes = self.size_bytes;
        self.metadata.quantization_level = Some(level);
        self.metadata.accuracy_retention *= level.accuracy_retention();
        self.metadata.speedup_factor *= level.speedup_factor();

        Ok(())
    }

    pub fn prune(&mut self, strategy: PruningStrategy, sparsity: f32) -> Result<(), String> {
        if !(0.0..1.0).contains(&sparsity) {
            return Err("Sparsity must be between 0.0 and 1.0".to_string());
        }

        let num_to_prune = (self.weights.len() as f32 * sparsity) as usize;
        
        match strategy {
            PruningStrategy::MagnitudeBased => {
                let mut weight_indices: Vec<(usize, f32)> = self.weights
                    .iter()
                    .enumerate()
                    .map(|(i, &w)| (i, w.abs()))
                    .collect();
                weight_indices.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap());
                
                for &(idx, _) in weight_indices.iter().take(num_to_prune) {
                    self.weights[idx] = 0.0;
                }
            },
            PruningStrategy::Structured => {
                let group_size = 8;
                let groups_to_prune = num_to_prune / group_size;
                
                for group in 0..groups_to_prune {
                    let start_idx = group * group_size;
                    let end_idx = std::cmp::min(start_idx + group_size, self.weights.len());
                    for idx in start_idx..end_idx {
                        self.weights[idx] = 0.0;
                    }
                }
            },
            PruningStrategy::Gradual => {
                let step = self.weights.len() / num_to_prune;
                for i in (0..self.weights.len()).step_by(step).take(num_to_prune) {
                    self.weights[i] = 0.0;
                }
            },
        }

        self.sparsity = sparsity;
        self.pruning_strategy = Some(strategy);
        let reduction_factor = strategy.memory_reduction(sparsity);
        self.size_bytes = (self.size_bytes as f32 / reduction_factor) as usize;
        self.metadata.optimized_size_bytes = self.size_bytes;
        self.metadata.pruning_strategy = Some(strategy);
        self.metadata.sparsity_level = Some(sparsity);
        self.metadata.speedup_factor *= strategy.speedup_factor(sparsity);
        
        let accuracy_loss = sparsity * 0.1;
        self.metadata.accuracy_retention *= 1.0 - accuracy_loss;

        Ok(())
    }

    pub async fn inference(&self, input: &[f32]) -> Vec<f32> {
        let base_latency = Duration::from_micros(100);
        let optimized_latency = Duration::from_nanos(
            (base_latency.as_nanos() as f32 / self.metadata.speedup_factor) as u64
        );
        tokio::time::sleep(optimized_latency).await;
        
        let output_size = std::cmp::min(input.len(), 10);
        let mut output = vec![0.0; output_size];
        
        for (i, output_val) in output.iter_mut().enumerate() {
            for (j, &input_val) in input.iter().enumerate().take(std::cmp::min(input.len(), self.weights.len() / output_size)) {
                let weight_idx = i * (self.weights.len() / output_size) + j;
                if weight_idx < self.weights.len() {
                    *output_val += input_val * self.weights[weight_idx];
                }
            }
        }
        
        output
    }

    pub fn get_performance_metrics(&self) -> HashMap<String, f64> {
        let mut metrics = HashMap::new();
        
        metrics.insert("size_bytes".to_string(), self.size_bytes as f64);
        metrics.insert("sparsity".to_string(), self.sparsity as f64);
        metrics.insert("accuracy_retention".to_string(), self.metadata.accuracy_retention as f64);
        metrics.insert("speedup_factor".to_string(), self.metadata.speedup_factor as f64);
        metrics.insert("memory_reduction".to_string(), 
                      self.metadata.original_size_bytes as f64 / self.metadata.optimized_size_bytes as f64);
        
        let zero_weights = self.weights.iter().filter(|&&w| w == 0.0).count();
        metrics.insert("actual_sparsity".to_string(), zero_weights as f64 / self.weights.len() as f64);
        
        metrics
    }
}

#[derive(Debug, Clone)]
pub struct BraidedBrownianModel {
    pub id: String,
    pub num_strands: usize,
    pub time_steps: usize,
    pub weights_linear: Vec<f32>,
    pub weights_conv: Vec<f32>,
    pub brownian_params: Option<crate::brownian_volatility_strand::BrownianMotionParameters>,
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
            optimization_timestamp: SystemTime::now()
                .duration_since(UNIX_EPOCH)
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
            brownian_params: None,
            quantization: QuantizationLevel::FP32,
            sparsity: 0.0,
            pruning_strategy: None,
            metadata,
        }
    }

    pub async fn generate_braided_paths_with_meta_learning(&self, initial_conditions: &[f32]) -> Vec<Vec<f32>> {
        if let Some(ref brownian_params) = self.brownian_params {
            let volatility_regime = if brownian_params.sigma > 0.3 {
                "high_volatility"
            } else if brownian_params.sigma < 0.15 {
                "low_volatility"  
            } else {
                "normal_volatility"
            };
            
            match volatility_regime {
                "high_volatility" => self.generate_braided_paths_milstein(initial_conditions).await,
                "low_volatility" => self.generate_braided_paths(initial_conditions).await,
                _ => self.generate_braided_paths_runge_kutta(initial_conditions).await,
            }
        } else {
            self.generate_braided_paths(initial_conditions).await
        }
    }
    
    pub async fn generate_braided_paths_milstein(&self, initial_conditions: &[f32]) -> Vec<Vec<f32>> {
        self.generate_braided_paths(initial_conditions).await
    }
    
    pub async fn generate_braided_paths_runge_kutta(&self, initial_conditions: &[f32]) -> Vec<Vec<f32>> {
        self.generate_braided_paths(initial_conditions).await
    }

    pub async fn generate_braided_paths(&self, initial_conditions: &[f32]) -> Vec<Vec<f32>> {
        let mut paths: Vec<Vec<f32>> = Vec::new();
        
        for strand in 0..self.num_strands {
            let initial_value = initial_conditions[strand % initial_conditions.len()];
            paths.push(vec![initial_value]);
        }
        
        for step in 0..self.time_steps {
            let mut new_values = Vec::new();
            
            for strand in 0..self.num_strands {
                let current_value = paths[strand][step];
                
                let (next_value, random) = if let Some(ref brownian_params) = self.brownian_params {
                    let sqrt_dt = (brownian_params.dt as f32).sqrt();
                    let drift_term = brownian_params.mu as f32 - 0.5 * (brownian_params.sigma as f32).powi(2);
                    
                    let mut rng_state = ((strand as u64 + 1) * 12345) + (step as u64 * 7919);
                    rng_state = rng_state.wrapping_mul(1103515245).wrapping_add(12345);
                    
                    let u1 = (rng_state as f32 / u64::MAX as f32).max(1e-8);
                    rng_state = rng_state.wrapping_mul(1103515245).wrapping_add(12345);
                    let u2 = rng_state as f32 / u64::MAX as f32;
                    
                    let normal = (-2.0 * u1.ln()).sqrt() * (2.0 * std::f32::consts::PI * u2).cos();
                    let dw = normal * sqrt_dt;
                    
                    let drift_increment = drift_term * brownian_params.dt as f32;
                    let diffusion_increment = brownian_params.sigma as f32 * dw;
                    let milstein_correction = 0.5 * (brownian_params.sigma as f32).powi(2) * 
                                            (dw * dw - brownian_params.dt as f32);
                    
                    let brownian_value = current_value * (1.0 + drift_increment + 
                                                        diffusion_increment + milstein_correction);
                    (brownian_value, dw * brownian_params.sigma as f32)
                } else {
                    let mut rng_state = ((strand as u64 + 1) * 12345) + (step as u64 * 7919);
                    rng_state = rng_state.wrapping_mul(1103515245).wrapping_add(12345);
                    
                    let u1 = (rng_state as f32 / u64::MAX as f32).max(1e-8);
                    rng_state = rng_state.wrapping_mul(1103515245).wrapping_add(12345);
                    let u2 = rng_state as f32 / u64::MAX as f32;
                    
                    let normal = (-2.0 * u1.ln()).sqrt() * (2.0 * std::f32::consts::PI * u2).cos();
                    let random = normal * 0.1;
                    (current_value, random)
                };
                
                let mut braided_increment = random;
                
                for other_strand in 0..self.num_strands {
                    if other_strand != strand {
                        let weight_idx = (strand * self.num_strands + other_strand) % self.weights_conv.len();
                        let other_value = paths[other_strand][step];
                        
                        let relative_position = current_value - other_value;
                        let braiding_force = self.weights_conv[weight_idx] * relative_position * 0.05;
                        
                        let phase_shift = (strand as f32 * 2.0 * std::f32::consts::PI / self.num_strands as f32) + 
                                        (step as f32 * 0.1);
                        let oscillation = (phase_shift + other_strand as f32).sin() * 0.02;
                        
                        braided_increment += braiding_force + oscillation;
                    }
                }
                
                let braid_period = self.time_steps as f32 / 4.0;
                let braid_phase = (step as f32 / braid_period) * 2.0 * std::f32::consts::PI;
                let strand_offset = strand as f32 * 2.0 * std::f32::consts::PI / self.num_strands as f32;
                let periodic_braiding = (braid_phase + strand_offset).sin() * 0.03;
                
                braided_increment += periodic_braiding;
                
                let final_value = if self.brownian_params.is_some() {
                    next_value + braided_increment * 0.1  // Apply braiding as small perturbation to Brownian motion
                } else {
                    current_value + braided_increment
                };
                new_values.push(final_value);
            }
            
            for (strand, &new_value) in new_values.iter().enumerate() {
                paths[strand].push(new_value);
            }
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
                    let quantized = (*weight * 127.0).round().clamp(-128.0, 127.0) / 127.0;
                    *weight = quantized;
                }
                for weight in &mut self.weights_conv {
                    let quantized = (*weight * 127.0).round().clamp(-128.0, 127.0) / 127.0;
                    *weight = quantized;
                }
            },
            QuantizationLevel::INT4 => {
                for weight in &mut self.weights_linear {
                    let quantized = (*weight * 7.0).round().clamp(-8.0, 7.0) / 7.0;
                    *weight = quantized;
                }
                for weight in &mut self.weights_conv {
                    let quantized = (*weight * 7.0).round().clamp(-8.0, 7.0) / 7.0;
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
        if !(0.0..1.0).contains(&sparsity) {
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
                
                for &(idx, _) in linear_indices.iter().take(linear_to_prune) {
                    self.weights_linear[idx] = 0.0;
                }
                
                let mut conv_indices: Vec<(usize, f32)> = self.weights_conv
                    .iter()
                    .enumerate()
                    .map(|(i, &w)| (i, w.abs()))
                    .collect();
                conv_indices.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap());
                
                for &(idx, _) in conv_indices.iter().take(conv_to_prune) {
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

pub struct AIModelOptimizer {
    models: RwLock<HashMap<String, AIModel>>,
    braided_models: RwLock<HashMap<String, BraidedBrownianModel>>,
    optimization_history: RwLock<Vec<OptimizationMetadata>>,
}

impl Default for AIModelOptimizer {
    fn default() -> Self {
        Self::new()
    }
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
            if total_models > 0 {
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
        }
        
        stats
    }

    pub async fn generate_report(&self) -> String {
        let stats = self.get_optimization_stats().await;
        let models = self.models.read().await;
        let braided_models = self.braided_models.read().await;
        
        let mut report = String::new();
        report.push_str("AI Model Optimization Report\n");
        report.push_str("============================\n\n");
        
        report.push_str(&format!("Total Models: {}\n", stats.get("total_models").unwrap_or(&0.0)));
        report.push_str(&format!("Total Braided Models: {}\n", stats.get("total_braided_models").unwrap_or(&0.0)));
        report.push_str(&format!("Total Optimizations: {}\n", stats.get("total_optimizations").unwrap_or(&0.0)));
        
        if let Some(memory_saved) = stats.get("total_memory_saved_bytes") {
            report.push_str(&format!("Memory Saved: {:.2} KB\n", memory_saved / 1024.0));
        }
        
        if let Some(avg_speedup) = stats.get("average_speedup") {
            report.push_str(&format!("Average Speedup: {:.2}x\n", avg_speedup));
        }
        
        if let Some(avg_accuracy) = stats.get("average_accuracy_retention") {
            report.push_str(&format!("Average Accuracy Retention: {:.1}%\n", avg_accuracy * 100.0));
        }
        
        if !models.is_empty() {
            report.push_str("\nStandard Models:\n");
            for (id, model) in models.iter() {
                report.push_str(&format!("  - {}: {:.1}% sparse, {:.2}x speedup\n", 
                                       id, model.sparsity * 100.0, model.metadata.speedup_factor));
            }
        }
        
        if !braided_models.is_empty() {
            report.push_str("\nBraided Brownian Models:\n");
            for (id, model) in braided_models.iter() {
                report.push_str(&format!("  - {}: {} strands, {} steps, {:.1}% sparse\n", 
                                       id, model.num_strands, model.time_steps, model.sparsity * 100.0));
            }
        }
        
        report
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
    async fn test_braided_brownian_model() {
        let mut model = BraidedBrownianModel::new("test_braided".to_string(), 3, 50);
        let original_size = model.metadata.original_size_bytes;
        
        model.quantize(QuantizationLevel::INT8).unwrap();
        assert!(model.metadata.optimized_size_bytes < original_size);
        
        model.prune(PruningStrategy::Structured, 0.3).unwrap();
        assert_eq!(model.sparsity, 0.3);
        
        let paths = model.generate_braided_paths(&[100.0, 105.0, 95.0]).await;
        assert_eq!(paths.len(), 3);
        assert!(!paths[0].is_empty());
        
        let moments = model.calculate_risk_moments(&paths);
        assert_eq!(moments.len(), 9);
    }
}
