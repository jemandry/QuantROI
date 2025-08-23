use memory_hierarchy::MemoryHierarchy;
use std::time::Instant;
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "memory-hierarchy")]
#[command(about = "Memory hierarchy demonstration and benchmarking tool")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    Demo,
    Benchmark {
        #[arg(short, long, default_value_t = 1000)]
        operations: usize,
        #[arg(short, long, default_value_t = 1024)]
        size: usize,
    },
    Info,
}

#[tokio::main]
async fn main() {
    let cli = Cli::parse();

    match cli.command {
        Commands::Demo => run_demo().await,
        Commands::Benchmark { operations, size } => run_benchmark(operations, size).await,
        Commands::Info => show_info(),
    }
}

async fn run_demo() {
    println!("🚀 Memory Hierarchy Interactive Demonstration");
    println!("=============================================\n");

    let hierarchy = MemoryHierarchy::new();

    println!("📊 Memory Hierarchy Levels:");
    show_hierarchy_levels();

    println!("\n💾 Storing data across hierarchy levels...");
    
    let small_data = "Small frequently accessed data".as_bytes().to_vec();
    hierarchy.put("hot_data".to_string(), small_data).await;
    
    let medium_data = vec![0u8; 1024 * 1024]; // 1MB
    hierarchy.put("warm_data".to_string(), medium_data).await;
    
    let large_data = vec![0u8; 100 * 1024 * 1024]; // 100MB
    hierarchy.put("cold_data".to_string(), large_data).await;

    println!("✅ Data stored successfully\n");

    println!("🔍 Demonstrating access patterns...");
    
    println!("   Accessing hot data multiple times:");
    for i in 1..=5 {
        let start = Instant::now();
        let _data = hierarchy.get("hot_data").await;
        let latency = start.elapsed();
        println!("     Access {}: {:?}", i, latency);
    }
    
    println!("   Accessing cold data:");
    let start = Instant::now();
    let _data = hierarchy.get("cold_data").await;
    let latency = start.elapsed();
    println!("     Cold data access: {:?}", latency);

    println!("\n📈 Performance Report:");
    println!("{}", hierarchy.get_performance_report().await);
}

async fn run_benchmark(operations: usize, data_size: usize) {
    println!("⚡ Memory Hierarchy Benchmark");
    println!("============================\n");
    println!("Operations: {}", operations);
    println!("Data size: {} bytes\n", data_size);

    let hierarchy = MemoryHierarchy::new();
    let test_data = vec![42u8; data_size];

    println!("📝 Write Benchmark:");
    let start = Instant::now();
    for i in 0..operations {
        let key = format!("benchmark_key_{}", i);
        hierarchy.put(key, test_data.clone()).await;
    }
    let write_time = start.elapsed();
    let write_ops_per_sec = operations as f64 / write_time.as_secs_f64();
    println!("   Total time: {:?}", write_time);
    println!("   Operations/sec: {:.2}", write_ops_per_sec);

    println!("\n📖 Read Benchmark:");
    let start = Instant::now();
    for i in 0..operations {
        let key = format!("benchmark_key_{}", i);
        let _data = hierarchy.get(&key).await;
    }
    let read_time = start.elapsed();
    let read_ops_per_sec = operations as f64 / read_time.as_secs_f64();
    println!("   Total time: {:?}", read_time);
    println!("   Operations/sec: {:.2}", read_ops_per_sec);

    println!("\n📊 Final Performance Report:");
    println!("{}", hierarchy.get_performance_report().await);
}

fn show_info() {
    println!("🏗️  Memory Hierarchy Architecture Information");
    println!("============================================\n");

    show_hierarchy_levels();

    println!("\n🎯 Key Principles:");
    println!("   • Locality of Reference: Recently accessed data is likely to be accessed again");
    println!("   • Spatial Locality: Data near recently accessed data is likely to be accessed");
    println!("   • Temporal Locality: Recently accessed data is likely to be accessed again soon");
    println!("   • Cache Coherence: Multiple caches maintain consistent views of data");
    println!("   • Write-Through vs Write-Back: Different strategies for handling writes");

    println!("\n⚙️  Optimization Techniques:");
    println!("   • Prefetching: Load data before it's requested");
    println!("   • Cache Replacement Policies: LRU, LFU, FIFO, Random");
    println!("   • Data Structure Choice: Arrays vs linked lists for spatial locality");
    println!("   • Memory Alignment: Align data to cache line boundaries");
    println!("   • Loop Optimization: Restructure loops for better cache usage");

    println!("\n🚀 Real-World Applications:");
    println!("   • Database Buffer Pools: Keep frequently accessed pages in memory");
    println!("   • Web Caching: CDNs cache content closer to users");
    println!("   • CPU Design: Multi-level caches in modern processors");
    println!("   • Operating Systems: Page replacement algorithms");
    println!("   • High-Frequency Trading: Ultra-low latency data access");
}

fn show_hierarchy_levels() {
    use memory_hierarchy::MemoryLevel;
    
    let levels = [
        (MemoryLevel::Register, "CPU Registers"),
        (MemoryLevel::L1Cache, "L1 Cache"),
        (MemoryLevel::L2Cache, "L2 Cache"),
        (MemoryLevel::L3Cache, "L3 Cache"),
        (MemoryLevel::MainMemory, "Main Memory (RAM)"),
        (MemoryLevel::SSD, "SSD Storage"),
        (MemoryLevel::HDD, "HDD Storage"),
        (MemoryLevel::NetworkStorage, "Network Storage"),
        (MemoryLevel::ArchivalStorage, "Archival Storage"),
    ];

    for (level, name) in levels.iter() {
        let latency = level.latency();
        let capacity = level.capacity();
        let capacity_str = if capacity == usize::MAX {
            "Unlimited".to_string()
        } else if capacity >= 1024 * 1024 * 1024 * 1024 {
            format!("{} TB", capacity / (1024 * 1024 * 1024 * 1024))
        } else if capacity >= 1024 * 1024 * 1024 {
            format!("{} GB", capacity / (1024 * 1024 * 1024))
        } else if capacity >= 1024 * 1024 {
            format!("{} MB", capacity / (1024 * 1024))
        } else if capacity >= 1024 {
            format!("{} KB", capacity / 1024)
        } else {
            format!("{} B", capacity)
        };

        println!("   {:20} | Latency: {:>12?} | Capacity: {:>10}", 
                 name, latency, capacity_str);
    }
}
