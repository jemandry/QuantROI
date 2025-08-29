use axum::{
    extract::{Extension, Query},
    http::StatusCode,
    response::Json,
};
use serde::{Deserialize, Serialize};
use std::{collections::HashMap, time::Instant};
use crate::{solana_client::SolanaClientService, AppState};

#[derive(Serialize, Deserialize)]
pub struct StrategyHealthResponse {
    pub nft_id: String,
    pub name: String,
    pub health_status: String,
    pub last_check: i64,
    pub performance_target: f64,
    pub current_performance: f64,
    pub trade_copying_enabled: bool,
    pub access_expires: i64,
}

#[derive(Serialize, Deserialize)]
pub struct TradeCopyRequest {
    pub strategy_nft_id: String,
    pub trade_data: TradeData,
}

#[derive(Serialize, Deserialize)]
pub struct TradeData {
    pub trade_id: u64,
    pub symbol: String,
    pub quantity: f64,
    pub price: f64,
    pub direction: String,
}

pub async fn get_strategy_health(
    Query(params): Query<HashMap<String, String>>,
    Extension(app_state): Extension<AppState>,
) -> Result<Json<Vec<StrategyHealthResponse>>, StatusCode> {
    let wallet = params.get("wallet").ok_or(StatusCode::BAD_REQUEST)?;

    let strategies = fetch_user_strategies(&app_state.solana_client, wallet).await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    
    Ok(Json(strategies))
}

pub async fn execute_trade_copy(
    Json(req): Json<TradeCopyRequest>,
    Extension(app_state): Extension<AppState>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    let start_time = Instant::now();
    
    let result = execute_strategy_trade_copy(&app_state.solana_client, &req).await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    
    let execution_time = start_time.elapsed().as_millis();
    
    if execution_time > 10 {
        tracing::warn!("Trade copy execution time {}ms exceeds 10ms target", execution_time);
    }
    
    Ok(Json(serde_json::json!({
        "success": true,
        "execution_time_ms": execution_time,
        "trade_result": result
    })))
}

async fn fetch_user_strategies(
    solana_client: &SolanaClientService,
    wallet: &str,
) -> Result<Vec<StrategyHealthResponse>, Box<dyn std::error::Error>> {
    let mock_strategies = vec![
        StrategyHealthResponse {
            nft_id: "ZKPStrategy123456789".to_string(),
            name: "AI Momentum Strategy".to_string(),
            health_status: "Healthy".to_string(),
            last_check: chrono::Utc::now().timestamp(),
            performance_target: 0.15,
            current_performance: 0.18,
            trade_copying_enabled: true,
            access_expires: chrono::Utc::now().timestamp() + 86400,
        }
    ];
    
    Ok(mock_strategies)
}

async fn execute_strategy_trade_copy(
    solana_client: &SolanaClientService,
    req: &TradeCopyRequest,
) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
    Ok(serde_json::json!({
        "status": "executed",
        "trade_id": req.trade_data.trade_id,
        "symbol": req.trade_data.symbol,
        "quantity": req.trade_data.quantity,
        "price": req.trade_data.price,
        "direction": req.trade_data.direction
    }))
}
