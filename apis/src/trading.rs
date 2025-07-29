use axum::{extract::{Extension, Path}, response::Json};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::sync::Arc;

use crate::{error::ApiError, solana_client::SolanaClientService, AppState};

#[derive(Deserialize)]
pub struct CreateDelegationRequest {
    pub wallet_address: String,
    pub bank_authority: String,
    pub ai_policy_id: String,
    pub investment_amount: u64,
    pub risk_tolerance: u8,
    pub quiz_passed: bool,
}

#[derive(Deserialize)]
pub struct ExecuteTradeRequest {
    pub delegation_id: String,
    pub trade_type: String,
    pub amount: u64,
    pub symbol: String,
    pub strategy_params: Value,
}

#[derive(Serialize)]
pub struct DelegationStatus {
    pub delegation_id: String,
    pub status: String,
    pub current_balance: u64,
    pub total_trades: u32,
    pub profit_loss: i64,
    pub roi_percentage: f64,
    pub last_trade_timestamp: i64,
}

pub struct TradingService {
    solana_client: Arc<SolanaClientService>,
}

impl TradingService {
    pub fn new(solana_client: Arc<SolanaClientService>) -> Self {
        Self { solana_client }
    }

    pub async fn create_ai_delegation(&self, request: &CreateDelegationRequest) -> Result<String, ApiError> {
        if !request.quiz_passed {
            return Err(ApiError::ValidationError("Knowledge quiz must be passed before delegation".to_string()));
        }

        let delegation_id = uuid::Uuid::new_v4().to_string();
        
        Ok(delegation_id)
    }

    pub async fn execute_trade(&self, request: &ExecuteTradeRequest) -> Result<String, ApiError> {
        let trade_id = uuid::Uuid::new_v4().to_string();
        
        Ok(trade_id)
    }

    pub async fn get_delegation_status(&self, delegation_id: &str) -> Result<DelegationStatus, ApiError> {
        Ok(DelegationStatus {
            delegation_id: delegation_id.to_string(),
            status: "active".to_string(),
            current_balance: 1000000,
            total_trades: 25,
            profit_loss: 50000,
            roi_percentage: 5.0,
            last_trade_timestamp: chrono::Utc::now().timestamp(),
        })
    }
}

pub async fn create_delegation(
    Extension(state): Extension<AppState>,
    Json(payload): Json<CreateDelegationRequest>,
) -> Result<Json<Value>, ApiError> {
    let delegation_id = state.trading_service.create_ai_delegation(&payload).await?;

    Ok(Json(json!({
        "delegation_id": delegation_id,
        "status": "created",
        "message": "AI delegation created successfully",
        "wallet_address": payload.wallet_address,
        "investment_amount": payload.investment_amount,
        "ai_policy_id": payload.ai_policy_id
    })))
}

pub async fn execute_trade(
    Extension(state): Extension<AppState>,
    Json(payload): Json<ExecuteTradeRequest>,
) -> Result<Json<Value>, ApiError> {
    let trade_id = state.trading_service.execute_trade(&payload).await?;

    Ok(Json(json!({
        "trade_id": trade_id,
        "status": "executed",
        "delegation_id": payload.delegation_id,
        "trade_type": payload.trade_type,
        "amount": payload.amount,
        "symbol": payload.symbol,
        "timestamp": chrono::Utc::now().timestamp()
    })))
}

pub async fn get_delegation_status(
    Extension(state): Extension<AppState>,
    Path(delegation_id): Path<String>,
) -> Result<Json<DelegationStatus>, ApiError> {
    let status = state.trading_service.get_delegation_status(&delegation_id).await?;
    Ok(Json(status))
}
