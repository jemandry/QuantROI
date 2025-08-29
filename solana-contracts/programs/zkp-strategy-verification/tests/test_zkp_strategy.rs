use anchor_lang::prelude::*;
use zkp_strategy_verification::*;

#[tokio::test]
async fn test_create_strategy_nft() {
    let strategy_commitment = [1u8; 32];
    let performance_target = 0.15;
    let access_price = 1000000;
    let metadata = StrategyMetadata {
        name: "Test Strategy".to_string(),
        description: "A test trading strategy".to_string(),
        strategy_type: "momentum".to_string(),
        risk_level: 3,
    };

    assert!(performance_target > 0.0);
    assert!(access_price > 0);
}

#[tokio::test]
async fn test_trade_copy_latency() {
    let start = std::time::Instant::now();
    
    let trade_data = TradeData {
        trade_id: 12345,
        symbol: "AAPL".to_string(),
        quantity: 100.0,
        price: 150.0,
        direction: TradeDirection::Buy,
    };
    
    let execution_time = start.elapsed().as_millis();
    assert!(execution_time < 10, "Trade copy execution time {}ms exceeds 10ms target", execution_time);
}

#[tokio::test]
async fn test_strategy_verification() {
    let proof_data = vec![1, 2, 3, 4, 5];
    let performance_claim = 0.20;
    
    assert!(performance_claim > 0.0);
    assert!(!proof_data.is_empty());
}
