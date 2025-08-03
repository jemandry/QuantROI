use memory_hierarchy::{MemoryHierarchy, CausalDataAgent};
use std::time::Duration;
use tokio::time::sleep;

#[tokio::main]
async fn main() {
    println!("Intelligent Causal Data Agent Example");
    println!("====================================\n");

    let hierarchy = MemoryHierarchy::new();
    let agent = hierarchy.create_causal_agent();

    println!("1. Creating analysis session...");
    let session_id = agent.create_session().await;
    println!("   Session ID: {}\n", session_id);

    println!("2. Initial confidence assessment...");
    let confidence = agent.get_confidence_feedback(&session_id).await.unwrap();
    println!("   {}\n", confidence);

    println!("3. Agent requesting missing data...");
    let missing_requests = agent.get_missing_data_requests(&session_id).await.unwrap();
    for (i, request) in missing_requests.iter().enumerate() {
        println!("   {}. {}", i + 1, request);
    }
    println!();

    println!("4. User provides basic information...");
    agent.update_inventory(&session_id, "stock_symbol", "AAPL".to_string()).await.unwrap();
    agent.update_inventory(&session_id, "time_period", "January 2025".to_string()).await.unwrap();
    println!("   ✓ Stock: AAPL");
    println!("   ✓ Period: January 2025\n");

    println!("5. Updated confidence after basic info...");
    let confidence = agent.get_confidence_feedback(&session_id).await.unwrap();
    println!("   {}\n", confidence);

    println!("6. Agent asks causal questions...");
    let questions = agent.get_causal_questions(&session_id).await.unwrap();
    for (i, question) in questions.iter().take(3).enumerate() {
        println!("   {}. [{}] {}", i + 1, question.category.to_uppercase(), question.question);
    }
    println!();

    println!("7. User responds to causal questions...");
    agent.record_user_response(&session_id, "earnings_news", "Yes, Apple reported strong Q4 earnings on Jan 15th with revenue beat").await.unwrap();
    println!("   ✓ Earnings question answered");

    agent.record_user_response(&session_id, "volume_spike", "Yes, volume was 3x normal on Jan 15th and 16th").await.unwrap();
    println!("   ✓ Volume question answered");

    agent.record_user_response(&session_id, "options_activity", "Large call buying observed, IV increased 20%").await.unwrap();
    println!("   ✓ Options question answered\n");

    println!("8. Adding additional data sources...");
    agent.update_inventory(&session_id, "volume_data", "true".to_string()).await.unwrap();
    agent.update_inventory(&session_id, "news_data", "true".to_string()).await.unwrap();
    agent.update_inventory(&session_id, "options_data", "true".to_string()).await.unwrap();
    println!("   ✓ Volume data added");
    println!("   ✓ News data added");
    println!("   ✓ Options data added\n");

    println!("9. User adds custom causal factor...");
    agent.add_custom_factor(&session_id, "ai_announcement", "Apple AI partnership announcement").await.unwrap();
    agent.update_inventory(&session_id, "ai_announcement", "true".to_string()).await.unwrap();
    println!("   ✓ Custom factor: AI announcement impact\n");

    println!("10. Final confidence assessment...");
    let confidence = agent.get_confidence_feedback(&session_id).await.unwrap();
    println!("   {}\n", confidence);

    println!("11. Checking analysis readiness...");
    let ready = agent.is_ready_for_analysis(&session_id).await.unwrap();
    println!("   Analysis Ready: {}\n", if ready { "✅ YES" } else { "❌ NO" });

    if ready {
        println!("12. Generating analysis summary...");
        let summary = agent.generate_analysis_summary(&session_id).await.unwrap();
        println!("{}\n", summary);

        println!("13. Simulating causal analysis integration...");
        println!("   → Integrating with CausalGraphDiscovery...");
        sleep(Duration::from_millis(500)).await;
        
        println!("   → Running Granger causality tests...");
        sleep(Duration::from_millis(300)).await;
        
        println!("   → Analyzing temporal relationships...");
        sleep(Duration::from_millis(400)).await;
        
        println!("   → Building causal graph with {} factors", 8);
        sleep(Duration::from_millis(200)).await;
        
        println!("   ✅ Causal analysis complete!\n");

        println!("14. Storing results in memory hierarchy...");
        let analysis_key = format!("causal_analysis_{}", session_id);
        let analysis_data = format!("{{\"session_id\": \"{}\", \"symbol\": \"AAPL\", \"confidence\": 0.85, \"factors\": [\"earnings\", \"volume\", \"options\", \"ai_announcement\"]}}", session_id);
        hierarchy.put(analysis_key.clone(), analysis_data.into_bytes()).await;
        println!("   ✓ Analysis stored with key: {}\n", analysis_key);

        println!("15. Demonstrating intelligent follow-up...");
        let next_action = agent.get_next_action(&session_id).await.unwrap();
        println!("   Next recommended action: {}\n", next_action);
    }

    println!("16. Performance metrics...");
    let session = agent.get_session(&session_id).await.unwrap();
    println!("   Questions asked: {}", session.asked_questions.len());
    println!("   User responses: {}", session.user_responses.len());
    println!("   Custom factors: {}", session.inventory.custom_factors.len());
    println!("   Final confidence: {:.1}%", session.confidence_score * 100.0);
    println!("   Session duration: {:?}", session.updated_at - session.created_at);

    println!("\n🎯 Intelligent Causal Data Agent demonstration complete!");
    println!("   The agent successfully guided data collection and causal question asking");
    println!("   to achieve high confidence for financial analysis.");
}
