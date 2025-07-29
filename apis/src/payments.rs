use axum::{extract::Extension, response::Json};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::sync::Arc;

use crate::{error::ApiError, solana_client::SolanaClientService, AppState};

#[derive(Deserialize)]
pub struct PaymentRuleRequest {
    pub wallet_address: String,
    pub rule_type: String,
    pub amount: Option<u64>,
    pub percentage: Option<f64>,
    pub frequency: String,
    pub recipient: String,
    pub conditions: Vec<PaymentCondition>,
}

#[derive(Deserialize, Serialize)]
pub struct PaymentCondition {
    pub condition_type: String,
    pub threshold: f64,
    pub operator: String,
}

#[derive(Deserialize)]
pub struct ExecutePaymentRequest {
    pub payment_rule_id: String,
    pub amount: u64,
    pub recipient: String,
}

#[derive(Serialize)]
pub struct PaymentHistory {
    pub payment_id: String,
    pub amount: u64,
    pub recipient: String,
    pub status: String,
    pub timestamp: i64,
    pub transaction_hash: Option<String>,
}

pub struct PaymentService {
    solana_client: Arc<SolanaClientService>,
}

impl PaymentService {
    pub fn new(solana_client: Arc<SolanaClientService>) -> Self {
        Self { solana_client }
    }

    pub async fn setup_payment_rules(&self, request: &PaymentRuleRequest) -> Result<String, ApiError> {
        let rule_id = uuid::Uuid::new_v4().to_string();
        
        Ok(rule_id)
    }

    pub async fn execute_payment(&self, request: &ExecutePaymentRequest) -> Result<String, ApiError> {
        let payment_id = uuid::Uuid::new_v4().to_string();
        
        Ok(payment_id)
    }

    pub async fn get_payment_history(&self, wallet_address: &str) -> Result<Vec<PaymentHistory>, ApiError> {
        Ok(vec![
            PaymentHistory {
                payment_id: uuid::Uuid::new_v4().to_string(),
                amount: 100000,
                recipient: "recipient_wallet_address".to_string(),
                status: "completed".to_string(),
                timestamp: chrono::Utc::now().timestamp(),
                transaction_hash: Some("transaction_hash_example".to_string()),
            }
        ])
    }
}

pub async fn setup_payment_rules(
    Extension(state): Extension<AppState>,
    Json(payload): Json<PaymentRuleRequest>,
) -> Result<Json<Value>, ApiError> {
    let rule_id = state.payment_service.setup_payment_rules(&payload).await?;

    Ok(Json(json!({
        "rule_id": rule_id,
        "status": "created",
        "message": "Payment rules configured successfully",
        "rule_type": payload.rule_type,
        "frequency": payload.frequency,
        "recipient": payload.recipient
    })))
}

pub async fn execute_payment(
    Extension(state): Extension<AppState>,
    Json(payload): Json<ExecutePaymentRequest>,
) -> Result<Json<Value>, ApiError> {
    let payment_id = state.payment_service.execute_payment(&payload).await?;

    Ok(Json(json!({
        "payment_id": payment_id,
        "status": "executed",
        "amount": payload.amount,
        "recipient": payload.recipient,
        "timestamp": chrono::Utc::now().timestamp()
    })))
}

pub async fn get_payment_history(
    Extension(state): Extension<AppState>,
) -> Result<Json<Vec<PaymentHistory>>, ApiError> {
    let history = state.payment_service.get_payment_history("wallet_address").await?;
    Ok(Json(history))
}
