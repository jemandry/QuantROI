use axum::{extract::Extension, response::Json};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::sync::Arc;

use crate::{error::ApiError, solana_client::SolanaClientService, AppState};

#[derive(Deserialize)]
pub struct MintNFTRequest {
    pub wallet_address: String,
    pub nft_type: String,
    pub metadata: NFTMetadata,
    pub quiz_score: Option<u8>,
    pub position_data: Option<PositionData>,
    pub reward_type: Option<String>,
}

#[derive(Deserialize, Serialize)]
pub struct NFTMetadata {
    pub name: String,
    pub description: String,
    pub image_url: String,
    pub attributes: Vec<NFTAttribute>,
}

#[derive(Deserialize, Serialize)]
pub struct NFTAttribute {
    pub trait_type: String,
    pub value: String,
}

#[derive(Deserialize, Serialize)]
pub struct PositionData {
    pub strategy_name: String,
    pub roi_target: f64,
    pub investment_amount: u64,
    pub delegation_timestamp: i64,
}

#[derive(Deserialize)]
pub struct ListNFTRequest {
    pub nft_id: String,
    pub price: u64,
}

#[derive(Serialize)]
pub struct NFTPortfolioItem {
    pub nft_id: String,
    pub nft_type: String,
    pub metadata: NFTMetadata,
    pub mint_timestamp: i64,
    pub is_listed: bool,
    pub listing_price: Option<u64>,
    pub estimated_value: Option<u64>,
}

pub struct NFTService {
    solana_client: Arc<SolanaClientService>,
}

impl NFTService {
    pub fn new(solana_client: Arc<SolanaClientService>) -> Self {
        Self { solana_client }
    }

    pub async fn mint_nft(&self, request: &MintNFTRequest) -> Result<String, ApiError> {
        if request.nft_type == "certification" {
            if let Some(score) = request.quiz_score {
                if score < 80 {
                    return Err(ApiError::ValidationError("Quiz score must be at least 80 for certification NFT".to_string()));
                }
            } else {
                return Err(ApiError::ValidationError("Quiz score required for certification NFT".to_string()));
            }
        }

        let nft_id = uuid::Uuid::new_v4().to_string();
        
        Ok(nft_id)
    }

    pub async fn list_nft_for_sale(&self, request: &ListNFTRequest) -> Result<String, ApiError> {
        let listing_id = uuid::Uuid::new_v4().to_string();
        
        Ok(listing_id)
    }

    pub async fn get_nft_portfolio(&self, wallet_address: &str) -> Result<Vec<NFTPortfolioItem>, ApiError> {
        Ok(vec![
            NFTPortfolioItem {
                nft_id: uuid::Uuid::new_v4().to_string(),
                nft_type: "certification".to_string(),
                metadata: NFTMetadata {
                    name: "Trading Certification".to_string(),
                    description: "Certified for advanced trading strategies".to_string(),
                    image_url: "https://example.com/cert.png".to_string(),
                    attributes: vec![
                        NFTAttribute {
                            trait_type: "Score".to_string(),
                            value: "95".to_string(),
                        },
                        NFTAttribute {
                            trait_type: "Level".to_string(),
                            value: "Expert".to_string(),
                        },
                    ],
                },
                mint_timestamp: chrono::Utc::now().timestamp(),
                is_listed: false,
                listing_price: None,
                estimated_value: Some(500000),
            }
        ])
    }
}

pub async fn mint_nft(
    Extension(state): Extension<AppState>,
    Json(payload): Json<MintNFTRequest>,
) -> Result<Json<Value>, ApiError> {
    let nft_id = state.nft_service.mint_nft(&payload).await?;

    Ok(Json(json!({
        "nft_id": nft_id,
        "status": "minted",
        "nft_type": payload.nft_type,
        "metadata": payload.metadata,
        "wallet_address": payload.wallet_address,
        "timestamp": chrono::Utc::now().timestamp()
    })))
}

pub async fn list_nft_for_sale(
    Extension(state): Extension<AppState>,
    Json(payload): Json<ListNFTRequest>,
) -> Result<Json<Value>, ApiError> {
    let listing_id = state.nft_service.list_nft_for_sale(&payload).await?;

    Ok(Json(json!({
        "listing_id": listing_id,
        "status": "listed",
        "nft_id": payload.nft_id,
        "price": payload.price,
        "timestamp": chrono::Utc::now().timestamp()
    })))
}

pub async fn get_nft_portfolio(
    Extension(state): Extension<AppState>,
) -> Result<Json<Vec<NFTPortfolioItem>>, ApiError> {
    let portfolio = state.nft_service.get_nft_portfolio("wallet_address").await?;
    Ok(Json(portfolio))
}
