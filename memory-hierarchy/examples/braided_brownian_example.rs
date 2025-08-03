use memory_hierarchy::{MemoryHierarchy, BraidedBrownianModel, QuantizationLevel, PruningStrategy};
use std::time::Instant;

#[tokio::main]
async fn main() {
    println!("Braided Brownian Motion in Memory Hierarchy");
    println!("===========================================\n");

    let hierarchy = MemoryHierarchy::new();

    println!("1. Creating braided Brownian models for financial risk analysis...");
    
    let portfolio_risk_model = BraidedBrownianModel::new("portfolio_risk_3strand".to_string(), 3, 100);
    let correlation_model = BraidedBrownianModel::new("asset_correlation_5strand".to_string(), 5, 200);
    let volatility_model = BraidedBrownianModel::new("volatility_surface_4strand".to_string(), 4, 150);
    
    println!("   Portfolio Risk Model: {} strands, {} time steps", 
             portfolio_risk_model.num_strands, portfolio_risk_model.time_steps);
    println!("   Asset Correlation Model: {} strands, {} time steps", 
             correlation_model.num_strands, correlation_model.time_steps);
    println!("   Volatility Surface Model: {} strands, {} time steps", 
             volatility_model.num_strands, volatility_model.time_steps);
    
    hierarchy.register_braided_model(portfolio_risk_model).await;
    hierarchy.register_braided_model(correlation_model).await;
    hierarchy.register_braided_model(volatility_model).await;
    
    println!("\n2. Applying quantization and pruning optimizations...");
    
    hierarchy.quantize_braided_model("portfolio_risk_3strand", QuantizationLevel::INT8).await.unwrap();
    hierarchy.prune_braided_model("portfolio_risk_3strand", PruningStrategy::Structured, 0.4).await.unwrap();
    
    hierarchy.quantize_braided_model("asset_correlation_5strand", QuantizationLevel::FP16).await.unwrap();
    hierarchy.prune_braided_model("asset_correlation_5strand", PruningStrategy::MagnitudeBased, 0.3).await.unwrap();
    
    hierarchy.quantize_braided_model("volatility_surface_4strand", QuantizationLevel::INT8).await.unwrap();
    hierarchy.prune_braided_model("volatility_surface_4strand", PruningStrategy::Structured, 0.35).await.unwrap();
    
    println!("   ✓ Portfolio model: INT8 quantized, 40% structured pruning");
    println!("   ✓ Correlation model: FP16 quantized, 30% magnitude-based pruning");
    println!("   ✓ Volatility model: INT8 quantized, 35% structured pruning");
    
    println!("\n3. Generating braided Brownian paths for risk scenarios...");
    
    let bull_market_conditions = vec![100.0, 105.0, 102.0];
    let bear_market_conditions = vec![100.0, 95.0, 98.0];
    let volatile_market_conditions = vec![100.0, 110.0, 90.0, 105.0, 95.0];
    
    let start = Instant::now();
    let bull_paths = hierarchy.generate_braided_paths("portfolio_risk_3strand", &bull_market_conditions).await.unwrap();
    let bull_time = start.elapsed();
    
    let start = Instant::now();
    let bear_paths = hierarchy.generate_braided_paths("portfolio_risk_3strand", &bear_market_conditions).await.unwrap();
    let bear_time = start.elapsed();
    
    let start = Instant::now();
    let volatile_paths = hierarchy.generate_braided_paths("asset_correlation_5strand", &volatile_market_conditions).await.unwrap();
    let volatile_time = start.elapsed();
    
    println!("   Bull market paths: {} strands in {:?}", bull_paths.len(), bull_time);
    println!("   Bear market paths: {} strands in {:?}", bear_paths.len(), bear_time);
    println!("   Volatile market paths: {} strands in {:?}", volatile_paths.len(), volatile_time);
    
    println!("\n4. Calculating risk moments and storing in memory hierarchy...");
    
    let bull_moments = hierarchy.calculate_risk_moments("portfolio_risk_3strand", &bull_paths).await.unwrap();
    let bear_moments = hierarchy.calculate_risk_moments("portfolio_risk_3strand", &bear_paths).await.unwrap();
    let volatile_moments = hierarchy.calculate_risk_moments("asset_correlation_5strand", &volatile_paths).await.unwrap();
    
    println!("   Bull market risk moments: {:?}", &bull_moments[..6.min(bull_moments.len())]);
    println!("   Bear market risk moments: {:?}", &bear_moments[..6.min(bear_moments.len())]);
    println!("   Volatile market risk moments: {:?}", &volatile_moments[..9.min(volatile_moments.len())]);
    
    hierarchy.store_braided_analysis("bull_market_analysis".to_string(), "portfolio_risk_3strand", &bull_market_conditions).await.unwrap();
    hierarchy.store_braided_analysis("bear_market_analysis".to_string(), "portfolio_risk_3strand", &bear_market_conditions).await.unwrap();
    hierarchy.store_braided_analysis("volatile_market_analysis".to_string(), "asset_correlation_5strand", &volatile_market_conditions).await.unwrap();
    
    println!("   ✓ Analysis results stored in memory hierarchy");
    
    println!("\n5. Demonstrating high-frequency access patterns...");
    
    let start = Instant::now();
    for i in 0..50 {
        let _bull_analysis = hierarchy.get("bull_market_analysis").await;
        let _bear_analysis = hierarchy.get("bear_market_analysis").await;
        
        if i % 10 == 0 {
            let _volatile_analysis = hierarchy.get("volatile_market_analysis").await;
        }
    }
    let access_time = start.elapsed();
    
    println!("   50 rapid risk analysis accesses in {:?} (avg: {:?} per access)", 
             access_time, access_time / 50);
    
    println!("\n6. Real-time risk monitoring simulation...");
    
    for scenario in 0..10 {
        let market_shock = vec![100.0 + (scenario as f32 * 2.0), 100.0 - (scenario as f32 * 1.5), 100.0 + (scenario as f32 * 0.5)];
        
        let start = Instant::now();
        let shock_paths = hierarchy.generate_braided_paths("portfolio_risk_3strand", &market_shock).await.unwrap();
        let shock_moments = hierarchy.calculate_risk_moments("portfolio_risk_3strand", &shock_paths).await.unwrap();
        let processing_time = start.elapsed();
        
        let shock_key = format!("market_shock_{}", scenario);
        hierarchy.put(shock_key.clone(), format!("risk_moments: {:?}", shock_moments).into_bytes()).await;
        
        if scenario % 3 == 0 {
            println!("   Scenario {}: Risk processed in {:?}, moments: [{:.3}, {:.3}, {:.3}]", 
                     scenario, processing_time, 
                     shock_moments.get(0).unwrap_or(&0.0),
                     shock_moments.get(1).unwrap_or(&0.0),
                     shock_moments.get(2).unwrap_or(&0.0));
        }
    }
    
    println!("\n7. Final optimization and performance report:");
    println!("{}", hierarchy.get_performance_report().await);
    
    let ai_stats = hierarchy.get_ai_optimization_stats().await;
    println!("\nBraided Brownian Motion Statistics:");
    println!("- Total braided models: {}", ai_stats.get("total_braided_models").unwrap_or(&0.0));
    println!("- Average speedup: {:.2}x", ai_stats.get("average_speedup").unwrap_or(&1.0));
    println!("- Memory saved: {:.2} KB", ai_stats.get("total_memory_saved_bytes").unwrap_or(&0.0) / 1024.0);
    println!("- Accuracy retention: {:.1}%", ai_stats.get("average_accuracy_retention").unwrap_or(&1.0) * 100.0);
}
