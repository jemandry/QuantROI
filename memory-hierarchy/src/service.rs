use memory_hierarchy::{MemoryHierarchy, CausalDataAgent, TradingWealthEngine, QuantumMode, QuantumAuditEngine, QuantumSimulationEngine, BraidedCordDataEngine, SolanaEventLogger, SolanaEventData, MertonJumpParams};
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::info;
use serde::{Deserialize, Serialize};
use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::Json,
    routing::{get, post, delete},
    Router,
};
use tower_http::cors::CorsLayer;
use tower_http::trace::TraceLayer;
use std::collections::HashMap;

#[derive(Debug, Serialize, Deserialize)]
struct PutRequest {
    key: String,
    data: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct GetResponse {
    key: String,
    data: Option<String>,
    found: bool,
}

#[derive(Debug, Serialize, Deserialize)]
struct PerformanceResponse {
    report: String,
    stats: HashMap<String, f64>,
}

#[derive(Debug, Serialize, Deserialize)]
struct HealthResponse {
    status: String,
    version: String,
    uptime_seconds: u64,
}

struct AppState {
    hierarchy: Arc<MemoryHierarchy>,
    causal_agent: CausalDataAgent,
    quantum_audit_engine: Option<Arc<dyn QuantumAuditEngine + Send + Sync>>,
    wealth_engine: Arc<RwLock<TradingWealthEngine>>,
    solana_event_logger: Arc<SolanaEventLogger>,
    start_time: std::time::Instant,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt()
        .with_env_filter("memory_hierarchy=info")
        .init();

    info!("Starting Memory Hierarchy Service");

    let hierarchy = Arc::new(MemoryHierarchy::new());
    let causal_agent = hierarchy.create_quantum_causal_agent(QuantumMode::Simulation);
    let quantum_engine: Arc<dyn QuantumAuditEngine + Send + Sync> = Arc::new(QuantumSimulationEngine::new());
    let wealth_engine = Arc::new(RwLock::new(TradingWealthEngine::new()));
    
    let braided_engine = Arc::new(BraidedCordDataEngine::new().await);
    let solana_event_logger = Arc::new(SolanaEventLogger::new(braided_engine).await);

    let state = Arc::new(AppState {
        hierarchy,
        causal_agent,
        quantum_audit_engine: Some(quantum_engine),
        wealth_engine,
        solana_event_logger,
        start_time: std::time::Instant::now(),
    });

    let app = Router::new()
        .route("/health", get(health_check))
        .route("/data", post(put_data))
        .route("/data/:key", get(get_data))
        .route("/data/:key", delete(delete_data))
        .route("/performance", get(get_performance))
        .route("/stats", get(get_stats))
        .route("/metrics", get(metrics))
        .route("/causal/session", post(create_causal_session))
        .route("/causal/session/:session_id", get(get_causal_session))
        .route("/causal/session/:session_id/inventory", post(update_causal_inventory))
        .route("/causal/session/:session_id/questions", get(get_causal_questions))
        .route("/causal/session/:session_id/response", post(record_causal_response))
        .route("/causal/session/:session_id/confidence", get(get_causal_confidence))
        .route("/causal/session/:session_id/summary", get(get_causal_summary))
        .route("/quantum/audit/session", post(create_quantum_audit_session))
        .route("/quantum/audit/session/:session_id/analyze", post(analyze_quantum_audit))
        .route("/quantum/audit/session/:session_id/predictions", get(get_regulatory_predictions))
        .route("/wealth/project", post(create_wealth_project))
        .route("/wealth/project/:project_id", get(get_wealth_project))
        .route("/wealth/project/:project_id/delegate", post(delegate_project_task))
        .route("/wealth/milestones", get(get_wealth_milestones))
        .route("/solana/event/anchor_build", post(log_anchor_build_event))
        .route("/solana/event/contract_execution", post(log_contract_execution_event))
        .route("/solana/event/volatility_analysis", post(analyze_contract_volatility))
        .route("/solana/events", get(get_solana_events))
        .route("/solana/events/:event_id", get(get_solana_event_details))
        .layer(CorsLayer::permissive())
        .layer(TraceLayer::new_for_http())
        .with_state(state);

    let listener = tokio::net::TcpListener::bind("0.0.0.0:8080").await?;
    info!("Memory Hierarchy Service listening on port 8080");
    
    axum::serve(listener, app).await?;

    Ok(())
}

async fn health_check(State(state): State<Arc<AppState>>) -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "healthy".to_string(),
        version: env!("CARGO_PKG_VERSION").to_string(),
        uptime_seconds: state.start_time.elapsed().as_secs(),
    })
}

async fn put_data(
    State(state): State<Arc<AppState>>,
    Json(request): Json<PutRequest>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    state.hierarchy.put(request.key.clone(), request.data.into_bytes()).await;
    
    Ok(Json(serde_json::json!({
        "status": "success",
        "key": request.key,
        "message": "Data stored successfully"
    })))
}

async fn get_data(
    Path(key): Path<String>,
    State(state): State<Arc<AppState>>,
) -> Json<GetResponse> {
    match state.hierarchy.get(&key).await {
        Some(data) => Json(GetResponse {
            key: key.clone(),
            data: Some(String::from_utf8_lossy(&data).to_string()),
            found: true,
        }),
        None => Json(GetResponse {
            key: key.clone(),
            data: None,
            found: false,
        }),
    }
}

async fn delete_data(
    Path(key): Path<String>,
    State(_state): State<Arc<AppState>>,
) -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "acknowledged",
        "key": key,
        "message": "Delete request processed (handled by cache eviction policies)"
    }))
}

async fn get_performance(State(state): State<Arc<AppState>>) -> Json<PerformanceResponse> {
    let report = state.hierarchy.get_performance_report().await;
    let ai_stats = state.hierarchy.get_ai_optimization_stats().await;
    
    Json(PerformanceResponse {
        report,
        stats: ai_stats,
    })
}

async fn get_stats(State(state): State<Arc<AppState>>) -> Json<HashMap<String, f64>> {
    Json(state.hierarchy.get_ai_optimization_stats().await)
}

async fn metrics(State(_state): State<Arc<AppState>>) -> String {
    let ai_stats = _state.hierarchy.get_ai_optimization_stats().await;
    
    format!(
        "# HELP memory_hierarchy_total_models Total number of AI models\n\
         # TYPE memory_hierarchy_total_models gauge\n\
         memory_hierarchy_total_models {}\n\
         # HELP memory_hierarchy_total_braided_models Total number of braided Brownian models\n\
         # TYPE memory_hierarchy_total_braided_models gauge\n\
         memory_hierarchy_total_braided_models {}\n\
         # HELP memory_hierarchy_average_speedup Average speedup factor from optimizations\n\
         # TYPE memory_hierarchy_average_speedup gauge\n\
         memory_hierarchy_average_speedup {}\n\
         # HELP memory_hierarchy_memory_saved_bytes Total memory saved in bytes\n\
         # TYPE memory_hierarchy_memory_saved_bytes gauge\n\
         memory_hierarchy_memory_saved_bytes {}\n\
         # HELP memory_hierarchy_uptime_seconds Uptime of the memory hierarchy service\n\
         # TYPE memory_hierarchy_uptime_seconds counter\n\
         memory_hierarchy_uptime_seconds {}\n",
        ai_stats.get("total_models").unwrap_or(&0.0),
        ai_stats.get("total_braided_models").unwrap_or(&0.0),
        ai_stats.get("average_speedup").unwrap_or(&1.0),
        ai_stats.get("total_memory_saved_bytes").unwrap_or(&0.0),
        _state.start_time.elapsed().as_secs()
    )
}

async fn create_causal_session(State(state): State<Arc<AppState>>) -> Json<serde_json::Value> {
    let session_id = state.causal_agent.create_session().await;
    Json(serde_json::json!({
        "session_id": session_id,
        "status": "created"
    }))
}

async fn get_causal_session(
    State(state): State<Arc<AppState>>,
    Path(session_id): Path<String>,
) -> Json<serde_json::Value> {
    match state.causal_agent.get_session(&session_id).await {
        Some(session) => Json(serde_json::json!(session)),
        None => Json(serde_json::json!({
            "error": "Session not found"
        }))
    }
}

#[derive(serde::Deserialize)]
struct InventoryUpdate {
    field: String,
    value: String,
}

async fn update_causal_inventory(
    State(state): State<Arc<AppState>>,
    Path(session_id): Path<String>,
    Json(update): Json<InventoryUpdate>,
) -> Json<serde_json::Value> {
    match state.causal_agent.update_inventory(&session_id, &update.field, update.value).await {
        Ok(_) => Json(serde_json::json!({
            "status": "updated"
        })),
        Err(e) => Json(serde_json::json!({
            "error": e
        }))
    }
}

async fn get_causal_questions(
    State(state): State<Arc<AppState>>,
    Path(session_id): Path<String>,
) -> Json<serde_json::Value> {
    match state.causal_agent.get_causal_questions(&session_id).await {
        Ok(questions) => Json(serde_json::json!(questions)),
        Err(e) => Json(serde_json::json!({
            "error": e
        }))
    }
}

#[derive(serde::Deserialize)]
struct CausalResponse {
    question_id: String,
    response: String,
}

async fn record_causal_response(
    State(state): State<Arc<AppState>>,
    Path(session_id): Path<String>,
    Json(response): Json<CausalResponse>,
) -> Json<serde_json::Value> {
    match state.causal_agent.record_user_response(&session_id, &response.question_id, &response.response).await {
        Ok(_) => Json(serde_json::json!({
            "status": "recorded"
        })),
        Err(e) => Json(serde_json::json!({
            "error": e
        }))
    }
}

async fn get_causal_confidence(
    State(state): State<Arc<AppState>>,
    Path(session_id): Path<String>,
) -> Json<serde_json::Value> {
    match state.causal_agent.get_confidence_feedback(&session_id).await {
        Ok(feedback) => Json(serde_json::json!({
            "feedback": feedback
        })),
        Err(e) => Json(serde_json::json!({
            "error": e
        }))
    }
}

async fn get_causal_summary(
    State(state): State<Arc<AppState>>,
    Path(session_id): Path<String>,
) -> Json<serde_json::Value> {
    match state.causal_agent.generate_analysis_summary(&session_id).await {
        Ok(summary) => Json(serde_json::json!({
            "summary": summary
        })),
        Err(e) => Json(serde_json::json!({
            "error": e
        }))
    }
}

#[derive(serde::Deserialize)]
struct QuantumModeRequest {
    mode: String,
}

async fn create_quantum_audit_session(
    State(state): State<Arc<AppState>>,
    Json(request): Json<QuantumModeRequest>,
) -> Json<serde_json::Value> {
    let mode = match request.mode.as_str() {
        "simulation" => QuantumMode::Simulation,
        "production" => QuantumMode::ProductionHardware,
        "classical" => QuantumMode::NonQuantum,
        _ => QuantumMode::Simulation,
    };
    
    match state.causal_agent.create_quantum_audit_session(mode).await {
        Ok(session_id) => Json(serde_json::json!({
            "session_id": session_id,
            "status": "created"
        })),
        Err(e) => Json(serde_json::json!({
            "error": e
        }))
    }
}

#[derive(serde::Deserialize)]
struct QuantumAnalysisRequest {
    data: String,
}

async fn analyze_quantum_audit(
    State(state): State<Arc<AppState>>,
    Path(session_id): Path<String>,
    Json(request): Json<QuantumAnalysisRequest>,
) -> Json<serde_json::Value> {
    let data = request.data.as_bytes();
    match state.causal_agent.analyze_with_quantum_audit(&session_id, data).await {
        Ok(analysis) => Json(serde_json::json!({
            "analysis": analysis
        })),
        Err(e) => Json(serde_json::json!({
            "error": e
        }))
    }
}

async fn get_regulatory_predictions(
    State(state): State<Arc<AppState>>,
    Path(session_id): Path<String>,
) -> Json<serde_json::Value> {
    if let Some(quantum_engine) = &state.quantum_audit_engine {
        match quantum_engine.predict_regulatory_changes(&session_id).await {
            Ok(predictions) => Json(serde_json::json!({
                "predictions": predictions
            })),
            Err(e) => Json(serde_json::json!({
                "error": e
            }))
        }
    } else {
        Json(serde_json::json!({
            "error": "Quantum audit engine not available"
        }))
    }
}

#[derive(serde::Deserialize)]
struct CreateProjectRequest {
    name: String,
    causal_factors: Vec<String>,
    wealth_target: u64,
}

async fn create_wealth_project(
    State(state): State<Arc<AppState>>,
    Json(request): Json<CreateProjectRequest>,
) -> Json<serde_json::Value> {
    let mut wealth_engine = state.wealth_engine.write().await;
    let project_id = wealth_engine.create_causal_project(
        request.name,
        request.causal_factors,
        request.wealth_target
    ).await;
    
    Json(serde_json::json!({
        "project_id": project_id,
        "status": "created"
    }))
}

async fn get_wealth_project(
    State(state): State<Arc<AppState>>,
    Path(project_id): Path<String>,
) -> Json<serde_json::Value> {
    let wealth_engine = state.wealth_engine.read().await;
    match wealth_engine.get_project(&project_id) {
        Some(project) => Json(serde_json::json!(project)),
        None => Json(serde_json::json!({
            "error": "Project not found"
        }))
    }
}

#[derive(serde::Deserialize)]
struct DelegateTaskRequest {
    task_type: String,
    delegated_to: String,
    reward_amount: u64,
}

async fn delegate_project_task(
    State(state): State<Arc<AppState>>,
    Path(project_id): Path<String>,
    Json(request): Json<DelegateTaskRequest>,
) -> Json<serde_json::Value> {
    let task_type = match request.task_type.as_str() {
        "data_collection" => memory_hierarchy::TaskType::DataCollection,
        "causal_analysis" => memory_hierarchy::TaskType::CausalAnalysis,
        "risk_assessment" => memory_hierarchy::TaskType::RiskAssessment,
        "compliance_check" => memory_hierarchy::TaskType::ComplianceCheck,
        "trading_execution" => memory_hierarchy::TaskType::TradingExecution,
        _ => memory_hierarchy::TaskType::DataCollection,
    };
    
    let mut wealth_engine = state.wealth_engine.write().await;
    match wealth_engine.delegate_task(&project_id, task_type, request.delegated_to, request.reward_amount).await {
        Ok(task_id) => Json(serde_json::json!({
            "task_id": task_id,
            "status": "delegated"
        })),
        Err(e) => Json(serde_json::json!({
            "error": e
        }))
    }
}

async fn get_wealth_milestones(State(state): State<Arc<AppState>>) -> Json<serde_json::Value> {
    let wealth_engine = state.wealth_engine.read().await;
    let milestones = wealth_engine.get_wealth_milestones();
    Json(serde_json::json!({
        "milestones": milestones
    }))
}

#[derive(Deserialize)]
struct AnchorBuildRequest {
    project_path: String,
    success: bool,
}

#[derive(Deserialize)]
struct ContractExecutionRequest {
    transaction_signature: String,
    program_id: String,
    merton_params: MertonJumpParams,
}

#[derive(Deserialize)]
struct VolatilityAnalysisRequest {
    event_id: String,
}

async fn log_anchor_build_event(
    State(state): State<Arc<AppState>>,
    Json(request): Json<AnchorBuildRequest>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    match state.solana_event_logger.log_anchor_build_event(&request.project_path, request.success).await {
        Ok(event_id) => Ok(Json(serde_json::json!({
            "event_id": event_id,
            "status": "logged",
            "project_path": request.project_path,
            "success": request.success
        }))),
        Err(_) => Err(StatusCode::INTERNAL_SERVER_ERROR),
    }
}

async fn log_contract_execution_event(
    State(state): State<Arc<AppState>>,
    Json(request): Json<ContractExecutionRequest>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    let program_id = request.program_id.clone();
    
    match state.solana_event_logger.log_contract_execution_with_volatility(
        &request.transaction_signature,
        &program_id,
        request.merton_params,
    ).await {
        Ok(event_id) => Ok(Json(serde_json::json!({
            "event_id": event_id,
            "status": "logged",
            "transaction_signature": request.transaction_signature,
            "volatility_modeling": "applied"
        }))),
        Err(_) => Err(StatusCode::INTERNAL_SERVER_ERROR),
    }
}

async fn analyze_contract_volatility(
    State(state): State<Arc<AppState>>,
    Json(request): Json<VolatilityAnalysisRequest>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    match state.solana_event_logger.get_event_by_id(&request.event_id).await {
        Some(event_data) => {
            if let Some(volatility_impact) = event_data.volatility_impact {
                Ok(Json(serde_json::json!({
                    "event_id": request.event_id,
                    "volatility_path": volatility_impact.volatility_path,
                    "confidence_score": volatility_impact.confidence_score,
                    "merton_params": volatility_impact.merton_jump_params
                })))
            } else {
                Ok(Json(serde_json::json!({
                    "event_id": request.event_id,
                    "volatility_impact": "none"
                })))
            }
        },
        None => Err(StatusCode::NOT_FOUND),
    }
}

async fn get_solana_events(
    State(state): State<Arc<AppState>>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    let events = state.solana_event_logger.get_cached_events().await;
    let event_summaries: Vec<serde_json::Value> = events.iter().map(|(id, event)| {
        serde_json::json!({
            "event_id": id,
            "event_type": event.event_type,
            "timestamp_ns": event.timestamp_ns,
            "program_id": event.program_id,
            "has_volatility_impact": event.volatility_impact.is_some()
        })
    }).collect();
    
    Ok(Json(serde_json::json!({
        "total_events": events.len(),
        "events": event_summaries
    })))
}

async fn get_solana_event_details(
    State(state): State<Arc<AppState>>,
    Path(event_id): Path<String>,
) -> Result<Json<SolanaEventData>, StatusCode> {
    match state.solana_event_logger.get_event_by_id(&event_id).await {
        Some(event_data) => Ok(Json(event_data)),
        None => Err(StatusCode::NOT_FOUND),
    }
}
