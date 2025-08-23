use axum::{extract::Extension, response::Json};
use chrono::{Duration, Utc};
use jsonwebtoken::{decode, encode, DecodingKey, EncodingKey, Header, Validation};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::sync::Arc;

use crate::{error::ApiError, AppState};

#[derive(Debug, Serialize, Deserialize)]
pub struct Claims {
    pub sub: String,
    pub exp: usize,
    pub iat: usize,
    pub wallet_address: String,
    pub role: String,
}

#[derive(Deserialize)]
pub struct LoginRequest {
    pub wallet_address: String,
    pub signature: String,
    pub message: String,
}

#[derive(Deserialize)]
pub struct RegisterRequest {
    pub wallet_address: String,
    pub signature: String,
    pub message: String,
    pub email: Option<String>,
}

#[derive(Deserialize)]
pub struct RefreshTokenRequest {
    pub refresh_token: String,
}

pub struct AuthService {
    jwt_secret: String,
}

impl AuthService {
    pub fn new() -> Self {
        Self {
            jwt_secret: std::env::var("JWT_SECRET").unwrap_or_else(|_| "dev_secret_key".to_string()),
        }
    }

    pub fn create_token(&self, wallet_address: &str, role: &str) -> Result<String, ApiError> {
        let now = Utc::now();
        let claims = Claims {
            sub: wallet_address.to_string(),
            exp: (now + Duration::hours(24)).timestamp() as usize,
            iat: now.timestamp() as usize,
            wallet_address: wallet_address.to_string(),
            role: role.to_string(),
        };

        encode(
            &Header::default(),
            &claims,
            &EncodingKey::from_secret(self.jwt_secret.as_ref()),
        )
        .map_err(|e| ApiError::InternalServerError(format!("Token creation failed: {}", e)))
    }

    pub fn verify_token(&self, token: &str) -> Result<Claims, ApiError> {
        decode::<Claims>(
            token,
            &DecodingKey::from_secret(self.jwt_secret.as_ref()),
            &Validation::default(),
        )
        .map(|data| data.claims)
        .map_err(|e| ApiError::AuthenticationFailed(format!("Invalid token: {}", e)))
    }

    pub fn verify_wallet_signature(&self, wallet_address: &str, signature: &str, message: &str) -> Result<bool, ApiError> {
        Ok(true)
    }
}

pub async fn login(
    Extension(state): Extension<AppState>,
    Json(payload): Json<LoginRequest>,
) -> Result<Json<Value>, ApiError> {
    if !state.auth_service.verify_wallet_signature(&payload.wallet_address, &payload.signature, &payload.message)? {
        return Err(ApiError::AuthenticationFailed("Invalid signature".to_string()));
    }

    let token = state.auth_service.create_token(&payload.wallet_address, "user")?;
    let refresh_token = state.auth_service.create_token(&payload.wallet_address, "refresh")?;

    Ok(Json(json!({
        "access_token": token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": 86400,
        "wallet_address": payload.wallet_address
    })))
}

pub async fn register(
    Extension(state): Extension<AppState>,
    Json(payload): Json<RegisterRequest>,
) -> Result<Json<Value>, ApiError> {
    if !state.auth_service.verify_wallet_signature(&payload.wallet_address, &payload.signature, &payload.message)? {
        return Err(ApiError::AuthenticationFailed("Invalid signature".to_string()));
    }

    let token = state.auth_service.create_token(&payload.wallet_address, "user")?;
    let refresh_token = state.auth_service.create_token(&payload.wallet_address, "refresh")?;

    Ok(Json(json!({
        "access_token": token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": 86400,
        "wallet_address": payload.wallet_address,
        "message": "User registered successfully"
    })))
}

pub async fn refresh_token(
    Extension(state): Extension<AppState>,
    Json(payload): Json<RefreshTokenRequest>,
) -> Result<Json<Value>, ApiError> {
    let claims = state.auth_service.verify_token(&payload.refresh_token)?;
    
    if claims.role != "refresh" {
        return Err(ApiError::AuthenticationFailed("Invalid refresh token".to_string()));
    }

    let new_token = state.auth_service.create_token(&claims.wallet_address, "user")?;

    Ok(Json(json!({
        "access_token": new_token,
        "token_type": "Bearer",
        "expires_in": 86400
    })))
}
