use memory_hierarchy::{
    EnhancedConfidenceEngine, CrossSourceResolver, WasmEdgeClient, 
    ComplianceReportGenerator, BraidedCordDataEngine, CausalDataAgent,
    EventSource, EventSourceData, SourceType, EdgeDeduplicationRequest, 
    EdgeEvent, ReportType
};
use chrono::Utc;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🚀 Enhanced Architecture Analysis Demo");
    println!("=====================================");

    println!("\n📊 Phase 1: Confidence Scoring and Conflict Resolution");
    
    let confidence_engine = EnhancedConfidenceEngine::new();
    let conflict_resolver = CrossSourceResolver::new();

    let source1 = EventSource {
        source_id: "bloomberg".to_string(),
        source_type: SourceType::MarketData,
        reliability_score: 0.95,
        historical_accuracy: 0.95,
        latency_ms: 50,
        last_updated: Utc::now(),
    };

    let source2 = EventSource {
        source_id: "reuters".to_string(),
        source_type: SourceType::MarketData,
        reliability_score: 0.90,
        historical_accuracy: 0.90,
        latency_ms: 100,
        last_updated: Utc::now(),
    };

    confidence_engine.register_source(source1.clone()).await;
    confidence_engine.register_source(source2.clone()).await;

    let source_data = vec![
        EventSourceData {
            source: source1.clone(),
            raw_value: serde_json::json!({"price": 150.25, "volume": 1000000}),
            normalized_value: 150.25,
            source_confidence: 0.95,
            timeliness_score: 0.98,
        },
        EventSourceData {
            source: source2.clone(),
            raw_value: serde_json::json!({"price": 150.30, "volume": 1000500}),
            normalized_value: 150.30,
            source_confidence: 0.90,
            timeliness_score: 0.95,
        },
    ];

    let multi_source_event = confidence_engine
        .process_multi_source_event(
            "event_001".to_string(),
            "price_update".to_string(),
            source_data.clone(),
        )
        .await?;

    println!("✅ Multi-source event processed: {}", multi_source_event.event_id);
    println!("   Confidence Score: {:.2}", multi_source_event.confidence_score);

    let conflict_analysis = conflict_resolver.analyze_conflict(&source_data, "price_update").await;
    println!("🔍 Conflict Analysis: {:?}", conflict_analysis.conflict_severity);

    println!("\n🧠 Phase 2: AI-Assisted Causal Graph Building");
    
    let causal_agent = CausalDataAgent::new();
    let session_id = causal_agent.create_session().await;
    println!("📝 Created causal analysis session: {}", session_id);

    causal_agent.process_multi_source_event(
        "causal_event_001".to_string(),
        "earnings_announcement".to_string(),
        source_data,
    ).await?;

    let insights = causal_agent.get_causal_insights(&session_id).await?;
    println!("🎯 Causal Insights Generated:");
    println!("   Overall Confidence: {:.2}", insights.overall_confidence);
    println!("   Primary Causal Chains: {}", insights.primary_causal_chains.len());
    println!("   Temporal Patterns: {}", insights.temporal_patterns.len());

    println!("\n⚡ Phase 3: WASM Edge Client and Distributed Processing");
    
    let edge_client = WasmEdgeClient::new();

    let edge_events = vec![
        EdgeEvent {
            event_id: "edge_001".to_string(),
            event_type: "trade_execution".to_string(),
            timestamp: Utc::now(),
            content_hash: "hash_001".to_string(),
            source_id: "exchange_a".to_string(),
            metadata: [("symbol".to_string(), "AAPL".to_string())].iter().cloned().collect(),
        },
        EdgeEvent {
            event_id: "edge_002".to_string(),
            event_type: "trade_execution".to_string(),
            timestamp: Utc::now(),
            content_hash: "hash_001".to_string(),
            source_id: "exchange_b".to_string(),
            metadata: [("symbol".to_string(), "AAPL".to_string())].iter().cloned().collect(),
        },
    ];

    let dedup_request = EdgeDeduplicationRequest {
        request_id: "dedup_001".to_string(),
        events: edge_events,
        dedup_window_ms: 60000,
        similarity_threshold: 0.8,
    };

    let dedup_result = edge_client.process_deduplication_request(dedup_request).await?;
    println!("🔄 Edge Deduplication Results:");
    println!("   Unique Events: {}", dedup_result.unique_events.len());
    println!("   Duplicate Groups: {}", dedup_result.duplicate_groups.len());
    println!("   Processing Time: {}ms", dedup_result.processing_time_ms);
    println!("   Confidence Score: {:.2}", dedup_result.confidence_score);

    let metrics = edge_client.get_performance_metrics().await;
    println!("📈 Edge Performance Metrics:");
    println!("   Total Requests: {}", metrics.total_requests);
    println!("   Success Rate: {:.2}%", (1.0 - metrics.error_rate) * 100.0);

    println!("\n📋 Phase 4: Compliance Report Generation");
    
    let compliance_generator = ComplianceReportGenerator::new();

    let report = compliance_generator.generate_report(
        ReportType::Sec10K,
        Utc::now() - chrono::Duration::days(90),
        Utc::now(),
    ).await?;

    println!("📊 Compliance Report Generated:");
    println!("   Report ID: {}", report.report_id);
    println!("   Report Type: {:?}", report.report_type);
    println!("   Sections: {}", report.sections.len());
    println!("   Compliance Status: {:?}", report.compliance_status);
    println!("   Total Audit Events: {}", report.summary.total_audit_events);
    println!("   Data Quality Score: {:.2}", report.summary.data_quality_score);

    let html_report = compliance_generator.export_report_as_html(&report).await?;
    println!("📄 HTML Report Generated ({} characters)", html_report.len());

    println!("\n🔗 Integration with Existing Braided Cord System");
    
    let braided_engine = BraidedCordDataEngine::new().await;
    println!("✅ Braided Cord Data Engine initialized");

    let metrics = braided_engine.get_metrics().await;
    println!("📊 Braided Engine Metrics:");
    println!("   Hot Tier Hits: {}", metrics.hot_tier_hits);
    println!("   Warm Tier Hits: {}", metrics.warm_tier_hits);
    println!("   Cold Tier Hits: {}", metrics.cold_tier_hits);

    println!("\n🎉 Enhanced Architecture Analysis Demo Complete!");
    println!("All 4 phases successfully demonstrated with existing system integration.");

    Ok(())
}
