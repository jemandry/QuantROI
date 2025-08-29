use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};
use memory_hierarchy::{MemoryHierarchy, MemoryLevel, Cache, ReplacementPolicy};
use tokio::runtime::Runtime;

fn bench_memory_hierarchy_operations(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();
    
    let mut group = c.benchmark_group("memory_hierarchy");
    
    for size in [64, 1024, 4096, 65536].iter() {
        group.bench_with_input(BenchmarkId::new("put", size), size, |b, &size| {
            let hierarchy = MemoryHierarchy::new();
            let data = vec![42u8; size];
            
            b.iter(|| {
                rt.block_on(async {
                    let key = format!("bench_key_{}", rand::random::<u32>());
                    hierarchy.put(black_box(key), black_box(data.clone())).await
                })
            });
        });
        
        group.bench_with_input(BenchmarkId::new("get", size), size, |b, &size| {
            let hierarchy = MemoryHierarchy::new();
            let data = vec![42u8; size];
            
            rt.block_on(async {
                for i in 0..100 {
                    let key = format!("bench_key_{}", i);
                    hierarchy.put(key, data.clone()).await;
                }
            });
            
            b.iter(|| {
                rt.block_on(async {
                    let key = format!("bench_key_{}", rand::random::<u32>() % 100);
                    hierarchy.get(black_box(&key)).await
                })
            });
        });
    }
    
    group.finish();
}

fn bench_cache_replacement_policies(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();
    
    let mut group = c.benchmark_group("cache_policies");
    
    let policies = [
        ("LRU", ReplacementPolicy::LRU),
        ("LFU", ReplacementPolicy::LFU),
        ("FIFO", ReplacementPolicy::FIFO),
        ("Random", ReplacementPolicy::Random),
    ];
    
    for (name, policy) in policies.iter() {
        group.bench_function(*name, |b| {
            b.iter(|| {
                rt.block_on(async {
                let mut cache = Cache::new(MemoryLevel::L1Cache, policy.clone());
                let data = vec![42u8; 64];
                
                for i in 0..100 {
                    let key = format!("key_{}", i % 20); // 20 unique keys, repeated access
                    
                    if i % 2 == 0 {
                        cache.put(black_box(key), black_box(data.clone())).await;
                    } else {
                        cache.get(black_box(&key)).await;
                    }
                }
                })
            });
        });
    }
    
    group.finish();
}

fn bench_locality_patterns(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();
    
    let mut group = c.benchmark_group("locality_patterns");
    
    group.bench_function("sequential_access", |b| {
        let hierarchy = MemoryHierarchy::new();
        
        rt.block_on(async {
            for i in 0..1000 {
                let key = format!("seq_{}", i);
                let data = vec![i as u8; 64];
                hierarchy.put(key, data).await;
            }
        });
        
        b.iter(|| {
            rt.block_on(async {
                for i in 0..100 {
                    let key = format!("seq_{}", i);
                    hierarchy.get(black_box(&key)).await;
                }
            })
        });
    });
    
    group.bench_function("random_access", |b| {
        let hierarchy = MemoryHierarchy::new();
        
        rt.block_on(async {
            for i in 0..1000 {
                let key = format!("rand_{}", i);
                let data = vec![i as u8; 64];
                hierarchy.put(key, data).await;
            }
        });
        
        b.iter(|| {
            rt.block_on(async {
                for _ in 0..100 {
                    let i = rand::random::<usize>() % 1000;
                    let key = format!("rand_{}", i);
                    hierarchy.get(black_box(&key)).await;
                }
            })
        });
    });
    
    group.finish();
}

fn bench_concurrent_access(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();
    
    let mut group = c.benchmark_group("concurrent_access");
    
    for num_tasks in [1, 2, 4, 8].iter() {
        group.bench_with_input(BenchmarkId::new("concurrent", num_tasks), num_tasks, |b, &num_tasks| {
            b.iter(|| {
                rt.block_on(async {
                let hierarchy = std::sync::Arc::new(MemoryHierarchy::new());
                
                for i in 0..100 {
                    let key = format!("concurrent_{}", i);
                    let data = vec![i as u8; 64];
                    hierarchy.put(key, data).await;
                }
                
                let mut handles = Vec::new();
                for task_id in 0..num_tasks {
                    let hierarchy_clone = hierarchy.clone();
                    let handle = tokio::spawn(async move {
                        for i in 0..25 { // 25 operations per task = 100 total for 4 tasks
                            let key = format!("concurrent_{}", (task_id * 25 + i) % 100);
                            hierarchy_clone.get(black_box(&key)).await;
                        }
                    });
                    handles.push(handle);
                }
                
                for handle in handles {
                    handle.await.unwrap();
                }
                })
            });
        });
    }
    
    group.finish();
}

criterion_group!(
    benches,
    bench_memory_hierarchy_operations,
    bench_cache_replacement_policies,
    bench_locality_patterns,
    bench_concurrent_access
);
criterion_main!(benches);
