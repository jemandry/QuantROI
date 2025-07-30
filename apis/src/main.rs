use axum::{
    extract::Extension,
    http::StatusCode,
    response::Json,
    routing::{get, post},
    Router,
};
use serde_json::{json, Value};
use std::sync::Arc;
use tower_http::cors::CorsLayer;
use tracing::{info, warn};

mod auth;
mod trading;
mod portfolio;
mod payments;
mod nft;
mod solana_client;
mod error;

use auth::AuthService;
use trading::TradingService;
use portfolio::PortfolioService;
use payments::PaymentService;
use nft::NFTService;
use solana_client::SolanaClientService;
use error::ApiError;

#[derive(Clone)]
pub struct AppState {
    pub auth_service: Arc<AuthService>,
    pub trading_service: Arc<TradingService>,
    pub portfolio_service: Arc<PortfolioService>,
    pub payment_service: Arc<PaymentService>,
    pub nft_service: Arc<NFTService>,
    pub solana_client: Arc<SolanaClientService>,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::init();

    let solana_client = Arc::new(SolanaClientService::new().await?);
    let auth_service = Arc::new(AuthService::new());
    let trading_service = Arc::new(TradingService::new(solana_client.clone()));
    let portfolio_service = Arc::new(PortfolioService::new(solana_client.clone()));
    let payment_service = Arc::new(PaymentService::new(solana_client.clone()));
    let nft_service = Arc::new(NFTService::new(solana_client.clone()));

    let app_state = AppState {
        auth_service,
        trading_service,
        portfolio_service,
        payment_service,
        nft_service,
        solana_client,
    };

    let app = Router::new()
        .route("/health", get(health_check))
        .route("/api/auth/login", post(auth::login))
        .route("/api/auth/register", post(auth::register))
        .route("/api/auth/refresh", post(auth::refresh_token))
        .route("/api/trading/delegate", post(trading::create_delegation))
        .route("/api/trading/execute", post(trading::execute_trade))
        .route("/api/trading/status/:delegation_id", get(trading::get_delegation_status))
        .route("/api/trading/portfolio-allocation", post(trading::set_portfolio_allocation))
        .route("/api/trading/portfolio-allocation", get(trading::get_portfolio_allocation))
        .route("/api/trading/rebalance", post(trading::rebalance_portfolio))
        .route("/api/portfolio/overview", get(portfolio::get_portfolio_overview))
        .route("/api/portfolio/performance", get(portfolio::get_performance_metrics))
        .route("/api/payments/setup", post(payments::setup_payment_rules))
        .route("/api/payments/execute", post(payments::execute_payment))
        .route("/api/payments/history", get(payments::get_payment_history))
        .route("/api/nft/mint", post(nft::mint_nft))
        .route("/api/nft/list", post(nft::list_nft_for_sale))
        .route("/api/nft/portfolio", get(nft::get_nft_portfolio))
        .route("/api/profile/switches", get(portfolio::get_profile_switches))
        .route("/api/profile/switches", post(portfolio::update_profile_switches))
        .route("/api/objectives/create", post(portfolio::create_wealth_objective))
        .route("/api/objectives/progress", post(portfolio::update_objective_progress))
        .route("/api/objectives/timeline", post(portfolio::generate_ai_timeline))
        .layer(CorsLayer::permissive())
        .layer(Extension(app_state));

    let listener = tokio::net::TcpListener::bind("0.0.0.0:8080").await?;
    info!("QuantROI API server starting on port 8080");
    
    axum::serve(listener, app).await?;
    
    Ok(())
}

async fn health_check() -> Result<Json<Value>, ApiError> {
    Ok(Json(json!({
        "status": "healthy",
        "service": "quantroi-api",
        "version": "0.1.0",
        "timestamp": chrono::Utc::now().timestamp()
    })))
}
