use memory_hierarchy::{MemoryHierarchy, MemoryLevel, ReplacementPolicy, Cache};
use std::time::Instant;

#[tokio::main]
async fn main() {
    println!("Memory Hierarchy Optimization Strategies");
    println!("=======================================\n");

    println!("1. Cache Replacement Policy Performance:");
    compare_replacement_policies().await;

    println!("\n2. Data Structure Optimization for Speed:");
    demonstrate_data_structure_optimization().await;

    println!("\n3. Prefetching and Predictive Loading:");
    demonstrate_prefetching_strategies().await;

    println!("\n4. AI/ML Workload Optimization:");
    demonstrate_ai_workload_optimization().await;
}

async fn compare_replacement_policies() {
    let policies = [
        ("LRU", ReplacementPolicy::LRU),
        ("LFU", ReplacementPolicy::LFU),
        ("FIFO", ReplacementPolicy::FIFO),
        ("Random", ReplacementPolicy::Random),
    ];

    for (name, policy) in policies.iter() {
        let mut cache = Cache::new(MemoryLevel::L1Cache, policy.clone());
        let start = Instant::now();

        for i in 0..1000 {
            let key = format!("key_{}", i % 50); // 50 unique keys, repeated access
            let data = vec![i as u8; 64]; // 64-byte blocks
            
            if i % 2 == 0 {
                cache.put(key, data).await;
            } else {
                cache.get(&format!("key_{}", i % 50)).await;
            }
        }

        let elapsed = start.elapsed();
        println!("   {}: Hit Rate: {:.2}%, Utilization: {:.2}%, Time: {:?}",
                 name, cache.hit_rate() * 100.0, cache.utilization() * 100.0, elapsed);
    }
}

async fn demonstrate_data_structure_optimization() {
    println!("   Comparing array vs linked list performance in memory hierarchy:");

    let hierarchy = MemoryHierarchy::new();

    let array_data = (0..1000u32).map(|i| i.to_le_bytes()).flatten().collect::<Vec<u8>>();
    hierarchy.put("contiguous_array".to_string(), array_data).await;

    for i in 0..1000 {
        let node_data = format!("{{\"value\": {}, \"next\": {}}}", i, (i + 1) % 1000);
        hierarchy.put(format!("node_{}", i), node_data.into_bytes()).await;
    }

    let start = Instant::now();
    let _array = hierarchy.get("contiguous_array").await;
    let array_time = start.elapsed();

    let start = Instant::now();
    for i in 0..100 { // Sample 100 nodes
        let _node = hierarchy.get(&format!("node_{}", i)).await;
    }
    let list_time = start.elapsed();

    println!("   Array access time: {:?}", array_time);
    println!("   Linked list access time: {:?}", list_time);
    println!("   Array is {:.2}x faster due to spatial locality",
             list_time.as_nanos() as f64 / array_time.as_nanos() as f64);
}

async fn demonstrate_prefetching_strategies() {
    let hierarchy = MemoryHierarchy::new();

    for i in 0..100 {
        let data = format!("data_block_{}", i);
        hierarchy.put(format!("block_{}", i), data.into_bytes()).await;
    }

    println!("   Without prefetching:");
    let start = Instant::now();
    for i in 0..20 {
        let _data = hierarchy.get(&format!("block_{}", i)).await;
    }
    let no_prefetch_time = start.elapsed();
    println!("     Access time: {:?}", no_prefetch_time);

    println!("   With prefetching simulation:");
    let start = Instant::now();
    
    for chunk_start in (0..20).step_by(5) {
        let mut prefetch_tasks = Vec::new();
        for i in chunk_start..std::cmp::min(chunk_start + 5, 20) {
            let hierarchy_ref = &hierarchy;
            let key = format!("block_{}", i);
            prefetch_tasks.push(async move {
                hierarchy_ref.get(&key).await
            });
        }
        
        for task in prefetch_tasks {
            let _data = task.await;
        }
    }
    
    let prefetch_time = start.elapsed();
    println!("     Access time with prefetching: {:?}", prefetch_time);
    println!("     Improvement: {:.2}x faster",
             no_prefetch_time.as_nanos() as f64 / prefetch_time.as_nanos() as f64);
}

async fn demonstrate_ai_workload_optimization() {
    let hierarchy = MemoryHierarchy::new();

    println!("   Optimizing for AI/ML workloads (matrix operations):");

    let weights = generate_matrix_data(1000, 1000, "weights");
    hierarchy.put("model_weights".to_string(), weights).await;

    for batch in 0..10 {
        let batch_data = generate_matrix_data(32, 1000, &format!("batch_{}", batch));
        hierarchy.put(format!("training_batch_{}", batch), batch_data).await;
    }

    for layer in 0..5 {
        let gradient_data = generate_matrix_data(100, 100, &format!("grad_{}", layer));
        hierarchy.put(format!("gradients_layer_{}", layer), gradient_data).await;
    }

    let start = Instant::now();
    
    for epoch in 0..3 {
        println!("     Epoch {}: Processing batches...", epoch + 1);
        
        let _weights = hierarchy.get("model_weights").await;
        
        for batch in 0..10 {
            let _batch_data = hierarchy.get(&format!("training_batch_{}", batch)).await;
            
            for layer in 0..5 {
                let _gradients = hierarchy.get(&format!("gradients_layer_{}", layer)).await;
                let updated_grad = generate_matrix_data(100, 100, &format!("updated_grad_{}", layer));
                hierarchy.put(format!("gradients_layer_{}", layer), updated_grad).await;
            }
        }
    }
    
    let training_time = start.elapsed();
    println!("     Total training simulation time: {:?}", training_time);
    
    println!("\n   AI Workload Performance Report:");
    println!("{}", hierarchy.get_performance_report().await);
}

fn generate_matrix_data(rows: usize, cols: usize, prefix: &str) -> Vec<u8> {
    let mut data = format!("{{\"type\": \"matrix\", \"name\": \"{}\", \"shape\": [{}, {}], \"data\": [", 
                          prefix, rows, cols);
    
    for i in 0..(rows * cols) {
        if i > 0 { data.push(','); }
        data.push_str(&format!("{:.6}", (i as f32) * 0.001));
        
        if i > 1000 {
            data.push_str("...");
            break;
        }
    }
    
    data.push_str("]}");
    data.into_bytes()
}
