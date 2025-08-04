use memory_hierarchy::{BraidedBrownianModel, QuantizationLevel, PruningStrategy};
use std::collections::HashMap;

#[tokio::test]
async fn test_braided_cord_mapping_correlations() {
    println!("Testing braided cord mapping correlations...");
    
    let model = BraidedBrownianModel::new("correlation_test".to_string(), 3, 100);
    let initial_conditions = vec![100.0, 105.0, 95.0];
    
    let paths = model.generate_braided_paths(&initial_conditions).await;
    
    assert_eq!(paths.len(), 3, "Should have 3 braided strands");
    assert_eq!(paths[0].len(), 101, "Each path should have 101 points (initial + 100 steps)");
    
    println!("✓ Basic path structure validated");
    
    let mut correlations = Vec::new();
    for i in 0..3 {
        for j in (i+1)..3 {
            let correlation = calculate_correlation(&paths[i], &paths[j]);
            correlations.push((i, j, correlation));
            println!("Correlation between strand {} and {}: {:.6}", i, j, correlation);
        }
    }
    
    let has_correlation = correlations.iter().any(|(_, _, corr)| corr.abs() > 0.01);
    assert!(has_correlation, "Braided strands should show correlation due to braiding weights");
    
    println!("✓ Braided correlations detected");
}

#[tokio::test]
async fn test_braided_cord_deterministic_behavior() {
    println!("Testing deterministic behavior of braided cord mapping...");
    
    let model = BraidedBrownianModel::new("deterministic_test".to_string(), 3, 50);
    let initial_conditions = vec![100.0, 105.0, 95.0];
    
    let paths1 = model.generate_braided_paths(&initial_conditions).await;
    let paths2 = model.generate_braided_paths(&initial_conditions).await;
    
    for strand in 0..3 {
        for step in 0..paths1[strand].len() {
            assert!((paths1[strand][step] - paths2[strand][step]).abs() < 1e-6,
                   "Paths should be deterministic for audit compliance");
        }
    }
    
    println!("✓ Deterministic behavior confirmed");
}

#[tokio::test]
async fn test_braided_cord_topological_invariants() {
    println!("Testing topological invariants of braided cord mapping...");
    
    let model = BraidedBrownianModel::new("topology_test".to_string(), 3, 100);
    let initial_conditions = vec![100.0, 105.0, 95.0];
    
    let paths = model.generate_braided_paths(&initial_conditions).await;
    
    let mut crossings = 0;
    let mut winding_numbers = Vec::new();
    
    for strand in 0..3 {
        let mut winding = 0.0;
        for step in 1..paths[strand].len() {
            let diff = paths[strand][step] - paths[strand][step-1];
            winding += diff;
        }
        winding_numbers.push(winding);
    }
    
    for step in 1..paths[0].len() {
        for strand1 in 0..3 {
            for strand2 in (strand1+1)..3 {
                if step < paths[strand1].len() && step < paths[strand2].len() {
                    let prev_diff = paths[strand1][step-1] - paths[strand2][step-1];
                    let curr_diff = paths[strand1][step] - paths[strand2][step];
                    
                    if (prev_diff > 0.0) != (curr_diff > 0.0) && prev_diff.abs() > 1e-6 && curr_diff.abs() > 1e-6 {
                        crossings += 1;
                    }
                }
            }
        }
    }
    
    println!("Total strand crossings: {}", crossings);
    println!("Winding numbers: {:?}", winding_numbers);
    
    assert!(crossings > 0, "Braided strands should have crossings");
    
    println!("✓ Topological invariants calculated");
}

#[tokio::test]
async fn test_braided_cord_optimization_preservation() {
    println!("Testing braided cord mapping preservation after optimization...");
    
    let mut model = BraidedBrownianModel::new("optimization_test".to_string(), 3, 50);
    let initial_conditions = vec![100.0, 105.0, 95.0];
    
    let original_paths = model.generate_braided_paths(&initial_conditions).await;
    let original_moments = model.calculate_risk_moments(&original_paths);
    
    model.quantize(QuantizationLevel::INT8).unwrap();
    model.prune(PruningStrategy::Structured, 0.3).unwrap();
    
    let optimized_paths = model.generate_braided_paths(&initial_conditions).await;
    let optimized_moments = model.calculate_risk_moments(&optimized_paths);
    
    for i in 0..original_moments.len() {
        let diff = (original_moments[i] - optimized_moments[i]).abs();
        let relative_diff = diff / original_moments[i].abs().max(1e-6);
        println!("Moment {}: original={:.6}, optimized={:.6}, relative_diff={:.6}", 
                i, original_moments[i], optimized_moments[i], relative_diff);
        
        assert!(relative_diff < 0.6, "Optimization should preserve braided characteristics within reasonable bounds");
    }
    
    println!("✓ Braided cord mapping preserved after optimization");
}

#[tokio::test]
async fn test_braided_cord_convolutional_weights() {
    println!("Testing convolutional weights in braided cord mapping...");
    
    let model = BraidedBrownianModel::new("conv_test".to_string(), 3, 50);
    
    assert!(!model.weights_conv.is_empty(), "Convolutional weights should exist");
    
    let non_zero_weights = model.weights_conv.iter().filter(|&&w| w != 0.0).count();
    let total_weights = model.weights_conv.len();
    let non_zero_ratio = non_zero_weights as f32 / total_weights as f32;
    
    println!("Convolutional weights: {} total, {} non-zero ({:.1}%)", 
             total_weights, non_zero_weights, non_zero_ratio * 100.0);
    
    assert!(non_zero_ratio > 0.5, "Most convolutional weights should be non-zero initially");
    
    let num_strands = model.num_strands;
    for strand in 0..num_strands {
        for other_strand in 0..num_strands {
            if strand != other_strand {
                let weight_idx = (strand * num_strands + other_strand) % model.weights_conv.len();
                println!("Strand {} -> Strand {}: weight_idx={}, weight={:.6}", 
                        strand, other_strand, weight_idx, model.weights_conv[weight_idx]);
            }
        }
    }
    
    println!("✓ Convolutional weight mapping validated");
}

fn calculate_correlation(path1: &[f32], path2: &[f32]) -> f32 {
    let n = path1.len().min(path2.len());
    if n < 2 { return 0.0; }
    
    let mean1 = path1[..n].iter().sum::<f32>() / n as f32;
    let mean2 = path2[..n].iter().sum::<f32>() / n as f32;
    
    let mut numerator = 0.0;
    let mut sum_sq1 = 0.0;
    let mut sum_sq2 = 0.0;
    
    for i in 0..n {
        let diff1 = path1[i] - mean1;
        let diff2 = path2[i] - mean2;
        numerator += diff1 * diff2;
        sum_sq1 += diff1 * diff1;
        sum_sq2 += diff2 * diff2;
    }
    
    let denominator = (sum_sq1 * sum_sq2).sqrt();
    if denominator > 1e-10 {
        numerator / denominator
    } else {
        0.0
    }
}
