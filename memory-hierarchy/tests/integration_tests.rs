use memory_hierarchy::{MemoryHierarchy, MemoryLevel, Cache, ReplacementPolicy, BraidedBrownianModel, QuantizationLevel, PruningStrategy};
use std::time::Duration;
use tokio::time::timeout;

#[tokio::test]
async fn test_memory_hierarchy_basic_operations() {
    let hierarchy = MemoryHierarchy::new();
    
    let test_data = b"Hello, Memory Hierarchy!".to_vec();
    let key = "test_key".to_string();
    
    assert!(hierarchy.put(key.clone(), test_data.clone()).await);
    
    let retrieved_data = hierarchy.get(&key).await;
    assert_eq!(retrieved_data, Some(test_data));
}

#[tokio::test]
async fn test_cache_replacement_policies() {
    let policies = [
        ReplacementPolicy::LRU,
        ReplacementPolicy::LFU,
        ReplacementPolicy::FIFO,
        ReplacementPolicy::Random,
    ];
    
    for policy in policies.iter() {
        let mut cache = Cache::new(MemoryLevel::L1Cache, policy.clone());
        
        for i in 0..100 {
            let key = format!("key_{}", i);
            let data = vec![i as u8; 100];
            cache.put(key, data).await;
        }
        
        assert!(cache.utilization() > 0.0);
        assert!(cache.utilization() <= 1.0);
    }
}

#[tokio::test]
async fn test_latency_characteristics() {
    let hierarchy = MemoryHierarchy::new();
    
    let small_data = vec![1u8; 100];
    let large_data = vec![2u8; 10 * 1024 * 1024]; // 10MB
    
    hierarchy.put("small".to_string(), small_data.clone()).await;
    hierarchy.put("large".to_string(), large_data.clone()).await;
    
    let start = std::time::Instant::now();
    let _data = hierarchy.get("small").await;
    let first_access = start.elapsed();
    
    let start = std::time::Instant::now();
    let _data = hierarchy.get("small").await;
    let second_access = start.elapsed();
    
    assert!(second_access <= first_access + Duration::from_millis(10));
}

#[tokio::test]
async fn test_capacity_limits() {
    let mut cache = Cache::new(MemoryLevel::L1Cache, ReplacementPolicy::LRU);
    let capacity = MemoryLevel::L1Cache.capacity();
    
    let oversized_data = vec![0u8; capacity + 1000];
    let _result = cache.put("oversized".to_string(), oversized_data).await;
    
    assert!(cache.utilization() <= 1.0);
}

#[tokio::test]
async fn test_data_promotion() {
    let hierarchy = MemoryHierarchy::new();
    
    let data = vec![42u8; 1000];
    hierarchy.put("promote_test".to_string(), data.clone()).await;
    
    for _ in 0..5 {
        let retrieved = hierarchy.get("promote_test").await;
        assert_eq!(retrieved, Some(data.clone()));
    }
    
    let start = std::time::Instant::now();
    let _data = hierarchy.get("promote_test").await;
    let access_time = start.elapsed();
    
    assert!(access_time < Duration::from_millis(10));
}

#[tokio::test]
async fn test_braided_brownian_integration() {
    let hierarchy = MemoryHierarchy::new();
    
    let braided_model = BraidedBrownianModel::new("test_braided_model".to_string(), 3, 50);
    hierarchy.register_braided_model(braided_model).await;
    
    hierarchy.quantize_braided_model("test_braided_model", QuantizationLevel::INT8).await.unwrap();
    hierarchy.prune_braided_model("test_braided_model", PruningStrategy::Structured, 0.3).await.unwrap();
    
    let initial_conditions = vec![100.0, 105.0, 95.0];
    let paths = hierarchy.generate_braided_paths("test_braided_model", &initial_conditions).await.unwrap();
    assert_eq!(paths.len(), 3);
    assert!(!paths[0].is_empty());
    
    let moments = hierarchy.calculate_risk_moments("test_braided_model", &paths).await.unwrap();
    assert!(!moments.is_empty());
    assert_eq!(moments.len(), 9);
    
    hierarchy.store_braided_analysis("test_braided_analysis".to_string(), "test_braided_model", &initial_conditions).await.unwrap();
    let stored_analysis = hierarchy.get("test_braided_analysis").await;
    assert!(stored_analysis.is_some());
    
    let stats = hierarchy.get_ai_optimization_stats().await;
    assert!(stats.get("total_braided_models").unwrap() > &0.0);
    assert!(stats.get("average_speedup").unwrap() > &1.0);
}

#[tokio::test]
async fn test_braided_model_optimization() {
    let mut model = BraidedBrownianModel::new("optimization_test".to_string(), 2, 100);
    let original_size = model.metadata.original_size_bytes;
    
    model.quantize(QuantizationLevel::INT8).unwrap();
    assert_eq!(model.quantization, QuantizationLevel::INT8);
    assert!(model.metadata.optimized_size_bytes < original_size);
    assert!(model.metadata.speedup_factor > 1.0);
    
    model.prune(PruningStrategy::Structured, 0.4).unwrap();
    assert_eq!(model.sparsity, 0.4);
    assert!(model.metadata.speedup_factor > 2.0);
    
    let paths = model.generate_braided_paths(&[100.0, 110.0]).await;
    assert_eq!(paths.len(), 2);
    assert!(!paths[0].is_empty());
    
    let moments = model.calculate_risk_moments(&paths);
    assert_eq!(moments.len(), 6);
}

#[tokio::test]
async fn test_concurrent_access() {
    let hierarchy = std::sync::Arc::new(MemoryHierarchy::new());
    
    let data = vec![123u8; 500];
    hierarchy.put("concurrent_test".to_string(), data.clone()).await;
    
    let mut handles = Vec::new();
    for i in 0..10 {
        let hierarchy_clone = hierarchy.clone();
        let data_clone = data.clone();
        
        let handle = tokio::spawn(async move {
            for _ in 0..10 {
                let retrieved = hierarchy_clone.get("concurrent_test").await;
                assert_eq!(retrieved, Some(data_clone.clone()));
                
                let key = format!("concurrent_write_{}", i);
                hierarchy_clone.put(key, data_clone.clone()).await;
            }
        });
        
        handles.push(handle);
    }
    
    for handle in handles {
        handle.await.unwrap();
    }
}

#[tokio::test]
async fn test_performance_metrics() {
    let hierarchy = MemoryHierarchy::new();
    
    for i in 0..50 {
        let key = format!("metrics_test_{}", i);
        let data = vec![i as u8; 100];
        hierarchy.put(key.clone(), data).await;
        
        if i % 3 == 0 {
            for _ in 0..3 {
                hierarchy.get(&key).await;
            }
        }
    }
    
    let stats = hierarchy.get_stats().await;
    
    assert!(stats.total_accesses > 0);
    assert!(stats.cache_hits + stats.cache_misses == stats.total_accesses);
    assert!(stats.total_latency > Duration::from_nanos(0));
    
    let report = hierarchy.get_performance_report().await;
    assert!(report.contains("Memory Hierarchy Performance Report"));
    assert!(report.contains("Total Accesses:"));
    assert!(report.contains("Cache Hit Rate:"));
}

#[tokio::test]
async fn test_memory_level_properties() {
    let levels = [
        MemoryLevel::Register,
        MemoryLevel::L1Cache,
        MemoryLevel::L2Cache,
        MemoryLevel::L3Cache,
        MemoryLevel::MainMemory,
        MemoryLevel::SSD,
        MemoryLevel::HDD,
        MemoryLevel::NetworkStorage,
        MemoryLevel::ArchivalStorage,
    ];
    
    for (i, level) in levels.iter().enumerate() {
        let latency = level.latency();
        let capacity = level.capacity();
        
        if i > 0 && i < levels.len() - 2 { // Skip unlimited capacity levels
            let prev_latency = levels[i-1].latency();
            assert!(latency >= prev_latency, 
                   "Latency should increase with memory level: {:?} vs {:?}", 
                   prev_latency, latency);
        }
        
        if capacity != usize::MAX && i > 0 {
            let prev_capacity = levels[i-1].capacity();
            if prev_capacity != usize::MAX {
                assert!(capacity >= prev_capacity,
                       "Capacity should generally increase with memory level");
            }
        }
    }
}

#[tokio::test]
async fn test_timeout_handling() {
    let hierarchy = MemoryHierarchy::new();
    
    let data = vec![0u8; 1000];
    
    let put_result = timeout(Duration::from_secs(5), 
                            hierarchy.put("timeout_test".to_string(), data)).await;
    assert!(put_result.is_ok(), "Put operation should complete within timeout");
    
    let get_result = timeout(Duration::from_secs(5), 
                            hierarchy.get("timeout_test")).await;
    assert!(get_result.is_ok(), "Get operation should complete within timeout");
}
