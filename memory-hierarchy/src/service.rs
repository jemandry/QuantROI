use memory_hierarchy::{MemoryHierarchy, CausalDataAgent};
use std::sync::Arc;
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
    start_time: std::time::Instant,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt()
        .with_env_filter("memory_hierarchy=info")
        .init();

    info!("Starting Memory Hierarchy Service");

    let hierarchy = Arc::new(MemoryHierarchy::new());
    let causal_agent = hierarchy.create_causal_agent();

    let state = Arc::new(AppState {
        hierarchy,
        causal_agent,
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
    State(state): State<Arc<AppState>>,
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
