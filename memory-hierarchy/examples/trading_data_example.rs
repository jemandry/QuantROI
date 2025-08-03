use memory_hierarchy::MemoryHierarchy;
use std::time::Instant;
use tokio::time::{sleep, Duration};

#[tokio::main]
async fn main() {
    println!("Memory Hierarchy Demo: High-Frequency Trading Data Management");
    println!("==============================================================\n");

    let hierarchy = MemoryHierarchy::new();

    println!("1. Storing different types of trading data...");
    
    let market_data = generate_market_data();
    hierarchy.put("market_prices".to_string(), market_data).await;
    
    let trade_history = generate_trade_history();
    hierarchy.put("trade_history_1h".to_string(), trade_history).await;
    
    let historical_data = generate_historical_data();
    hierarchy.put("historical_analysis_1y".to_string(), historical_data).await;
    
    let compliance_data = generate_compliance_data();
    hierarchy.put("compliance_records_2023".to_string(), compliance_data).await;

    println!("✓ Data stored across memory hierarchy\n");

    println!("2. Simulating realistic trading access patterns...");
    
    for i in 0..100 {
        let start = Instant::now();
        let _data = hierarchy.get("market_prices").await;
        let latency = start.elapsed();
        
        if i % 20 == 0 {
            println!("   Market data access #{}: {:?}", i + 1, latency);
        }
        
        sleep(Duration::from_micros(1000)).await;
    }
    
    for i in 0..10 {
        let start = Instant::now();
        let _data = hierarchy.get("trade_history_1h").await;
        let latency = start.elapsed();
        println!("   Trade history access #{}: {:?}", i + 1, latency);
        sleep(Duration::from_millis(100)).await;
    }
    
    let start = Instant::now();
    let _data = hierarchy.get("historical_analysis_1y").await;
    let latency = start.elapsed();
    println!("   Historical data access: {:?}", latency);
    
    let start = Instant::now();
    let _data = hierarchy.get("compliance_records_2023").await;
    let latency = start.elapsed();
    println!("   Compliance data access: {:?}\n", latency);

    println!("3. Performance Analysis:");
    println!("{}", hierarchy.get_performance_report().await);

    println!("\n4. Demonstrating Data Locality Benefits:");
    demonstrate_locality_benefits(&hierarchy).await;
}

async fn demonstrate_locality_benefits(hierarchy: &MemoryHierarchy) {
    println!("   Testing spatial locality (accessing related data)...");
    
    for i in 0..10 {
        let key = format!("symbol_AAPL_tick_{}", i);
        let data = generate_tick_data(i);
        hierarchy.put(key, data).await;
    }
    
    let start = Instant::now();
    for i in 0..10 {
        let key = format!("symbol_AAPL_tick_{}", i);
        let _data = hierarchy.get(&key).await;
    }
    let sequential_time = start.elapsed();
    
    let start = Instant::now();
    let indices = [7, 2, 9, 1, 5, 8, 3, 0, 6, 4];
    for &i in &indices {
        let key = format!("symbol_AAPL_tick_{}", i);
        let _data = hierarchy.get(&key).await;
    }
    let random_time = start.elapsed();
    
    println!("   Sequential access time: {:?}", sequential_time);
    println!("   Random access time: {:?}", random_time);
    println!("   Locality benefit: {:.2}x faster", 
             random_time.as_nanos() as f64 / sequential_time.as_nanos() as f64);
}

fn generate_market_data() -> Vec<u8> {
    let data = r#"{
        "symbol": "AAPL",
        "price": 150.25,
        "volume": 1000000,
        "timestamp": "2025-08-03T07:48:00Z",
        "bid": 150.24,
        "ask": 150.26,
        "last_trade": 150.25
    }"#;
    data.as_bytes().to_vec()
}

fn generate_trade_history() -> Vec<u8> {
    let mut history = String::new();
    history.push('[');
    for i in 0..100 {
        if i > 0 { history.push(','); }
        history.push_str(&format!(
            r#"{{"trade_id": {}, "price": {:.2}, "volume": {}, "timestamp": "2025-08-03T{:02}:00:00Z"}}"#,
            i, 150.0 + (i as f64 * 0.01), 1000 + i * 10, 7 + (i / 60)
        ));
    }
    history.push(']');
    history.as_bytes().to_vec()
}

fn generate_historical_data() -> Vec<u8> {
    let mut data = String::new();
    data.push_str(r#"{"analysis_type": "yearly_performance", "data": ["#);
    for i in 0..365 {
        if i > 0 { data.push(','); }
        data.push_str(&format!(
            r#"{{"date": "2024-{:02}-{:02}", "close": {:.2}, "volume": {}}}"#,
            1 + (i / 31), 1 + (i % 31), 140.0 + (i as f64 * 0.1), 500000 + i * 1000
        ));
    }
    data.push_str("]}");
    data.as_bytes().to_vec()
}

fn generate_compliance_data() -> Vec<u8> {
    let mut data = String::new();
    data.push_str(r#"{"compliance_report": "2023_annual", "transactions": ["#);
    for i in 0..10000 {
        if i > 0 { data.push(','); }
        data.push_str(&format!(
            r#"{{"id": {}, "type": "trade", "amount": {:.2}, "compliance_check": "passed"}}"#,
            i, 1000.0 + (i as f64 * 10.0)
        ));
    }
    data.push_str("]}");
    data.as_bytes().to_vec()
}

fn generate_tick_data(tick_id: usize) -> Vec<u8> {
    let data = format!(
        r#"{{"tick_id": {}, "price": {:.2}, "timestamp": "2025-08-03T07:48:{:02}Z"}}"#,
        tick_id, 150.0 + (tick_id as f64 * 0.001), tick_id % 60
    );
    data.as_bytes().to_vec()
}
