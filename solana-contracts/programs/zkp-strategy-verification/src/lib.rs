use anchor_lang::prelude::*;
use anchor_spl::token::{self, Token, TokenAccount, Transfer};
use sha3::{Digest, Sha3_256};
use sqlx::PgPool;
use bigdecimal::BigDecimal;
use std::str::FromStr;

declare_id!("ZKPStrategyVerif11111111111111111111111111");

#[program]
pub mod zkp_strategy_verification {
    use super::*;

    pub fn create_strategy_nft(
        ctx: Context<CreateStrategyNFT>,
        strategy_commitment: [u8; 32],
        performance_target: f64,
        access_price: u64,
        metadata: StrategyMetadata,
    ) -> Result<()> {
        let strategy_nft = &mut ctx.accounts.strategy_nft;
        let clock = Clock::get()?;
        
        require!(performance_target > 0.0, StrategyError::InvalidPerformanceTarget);
        require!(access_price > 0, StrategyError::InvalidAccessPrice);
        
        let mut hasher = Sha3_256::new();
        hasher.update(&strategy_commitment);
        hasher.update(ctx.accounts.creator.key().as_ref());
        hasher.update(&clock.unix_timestamp.to_le_bytes());
        let verification_hash = hasher.finalize();
        
        strategy_nft.creator = ctx.accounts.creator.key();
        strategy_nft.strategy_commitment = strategy_commitment;
        strategy_nft.verification_hash = verification_hash.into();
        strategy_nft.performance_target = performance_target;
        strategy_nft.access_price = access_price;
        strategy_nft.metadata = metadata;
        strategy_nft.created_at = clock.unix_timestamp;
        strategy_nft.total_copies_sold = 0;
        strategy_nft.total_revenue = 0;
        strategy_nft.is_active = true;
        strategy_nft.health_status = HealthStatus::Healthy;
        strategy_nft.last_performance_check = clock.unix_timestamp;
        
        emit!(StrategyNFTCreated {
            nft_id: strategy_nft.key(),
            creator: ctx.accounts.creator.key(),
            verification_hash: verification_hash.into(),
            performance_target,
            access_price,
            timestamp: clock.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn verify_strategy_proof(
        ctx: Context<VerifyStrategyProof>,
        proof_data: Vec<u8>,
        performance_claim: f64,
    ) -> Result<()> {
        let strategy_nft = &mut ctx.accounts.strategy_nft;
        let clock = Clock::get()?;
        
        require!(strategy_nft.is_active, StrategyError::StrategyInactive);
        
        let mut hasher = Sha3_256::new();
        hasher.update(&proof_data);
        hasher.update(&performance_claim.to_le_bytes());
        let proof_hash = hasher.finalize();
        
        let is_valid = proof_hash[0..8] == strategy_nft.verification_hash[0..8];
        
        if is_valid && performance_claim >= strategy_nft.performance_target {
            strategy_nft.health_status = HealthStatus::Healthy;
            strategy_nft.last_performance_check = clock.unix_timestamp;
            
            emit!(StrategyVerified {
                nft_id: strategy_nft.key(),
                performance_claim,
                verification_result: true,
                timestamp: clock.unix_timestamp,
            });
        } else {
            strategy_nft.health_status = HealthStatus::Degraded;
            
            emit!(StrategyVerified {
                nft_id: strategy_nft.key(),
                performance_claim,
                verification_result: false,
                timestamp: clock.unix_timestamp,
            });
        }
        
        Ok(())
    }

    pub fn purchase_strategy_access(
        ctx: Context<PurchaseStrategyAccess>,
        nft_id: Pubkey,
    ) -> Result<()> {
        let strategy_nft = &mut ctx.accounts.strategy_nft;
        let access_record = &mut ctx.accounts.access_record;
        let clock = Clock::get()?;
        
        require!(strategy_nft.is_active, StrategyError::StrategyInactive);
        require!(strategy_nft.health_status == HealthStatus::Healthy, StrategyError::UnhealthyStrategy);
        
        let transfer_ctx = CpiContext::new(
            ctx.accounts.token_program.to_account_info(),
            Transfer {
                from: ctx.accounts.buyer_token_account.to_account_info(),
                to: ctx.accounts.creator_token_account.to_account_info(),
                authority: ctx.accounts.buyer.to_account_info(),
            },
        );
        token::transfer(transfer_ctx, strategy_nft.access_price)?;
        
        access_record.buyer = ctx.accounts.buyer.key();
        access_record.strategy_nft = nft_id;
        access_record.access_granted_at = clock.unix_timestamp;
        access_record.access_expires_at = clock.unix_timestamp + 86400;
        access_record.trade_copying_enabled = true;
        
        strategy_nft.total_copies_sold += 1;
        strategy_nft.total_revenue += strategy_nft.access_price;
        
        emit!(StrategyAccessPurchased {
            buyer: ctx.accounts.buyer.key(),
            nft_id,
            access_price: strategy_nft.access_price,
            expires_at: access_record.access_expires_at,
            timestamp: clock.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn execute_trade_copy(
        ctx: Context<ExecuteTradeCopy>,
        trade_data: TradeData,
    ) -> Result<()> {
        let access_record = &ctx.accounts.access_record;
        let clock = Clock::get()?;
        
        require!(access_record.trade_copying_enabled, StrategyError::TradeCopyingDisabled);
        require!(clock.unix_timestamp < access_record.access_expires_at, StrategyError::AccessExpired);
        
        let start_time = clock.unix_timestamp;
        
        let _ = store_strategy_trade_async(
            trade_data.symbol.clone(),
            trade_data.price,
            trade_data.quantity as i32,
            "zkp_strategy_copy".to_string(),
            0.95, // High confidence for strategy copies
        );
        
        let execution_result = TradeExecutionResult {
            trade_id: trade_data.trade_id,
            symbol: trade_data.symbol.clone(),
            quantity: trade_data.quantity,
            price: trade_data.price,
            direction: trade_data.direction,
            executed_at: clock.unix_timestamp,
            execution_time_ms: (clock.unix_timestamp - start_time) as u32,
        };
        
        emit!(TradeCopyExecuted {
            buyer: access_record.buyer,
            trade_result: execution_result,
            timestamp: clock.unix_timestamp,
        });
        
        Ok(())
    }
}

#[account]
#[derive(InitSpace)]
pub struct StrategyNFT {
    pub creator: Pubkey,
    pub strategy_commitment: [u8; 32],
    pub verification_hash: [u8; 32],
    pub performance_target: f64,
    pub access_price: u64,
    pub metadata: StrategyMetadata,
    pub created_at: i64,
    pub total_copies_sold: u64,
    pub total_revenue: u64,
    pub is_active: bool,
    pub health_status: HealthStatus,
    pub last_performance_check: i64,
}

#[account]
#[derive(InitSpace)]
pub struct StrategyAccessRecord {
    pub buyer: Pubkey,
    pub strategy_nft: Pubkey,
    pub access_granted_at: i64,
    pub access_expires_at: i64,
    pub trade_copying_enabled: bool,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, InitSpace)]
pub struct StrategyMetadata {
    #[max_len(50)]
    pub name: String,
    #[max_len(200)]
    pub description: String,
    #[max_len(20)]
    pub strategy_type: String,
    pub risk_level: u8,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, InitSpace)]
pub struct TradeData {
    pub trade_id: u64,
    #[max_len(10)]
    pub symbol: String,
    pub quantity: f64,
    pub price: f64,
    pub direction: TradeDirection,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, InitSpace)]
pub struct TradeExecutionResult {
    pub trade_id: u64,
    #[max_len(10)]
    pub symbol: String,
    pub quantity: f64,
    pub price: f64,
    pub direction: TradeDirection,
    pub executed_at: i64,
    pub execution_time_ms: u32,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq, InitSpace)]
pub enum HealthStatus {
    Healthy,
    Degraded,
    Failed,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, InitSpace)]
pub enum TradeDirection {
    Buy,
    Sell,
}

async fn store_strategy_trade_async(
    symbol: String,
    price: f64,
    volume: i32,
    strategy_type: String,
    confidence: f64,
) -> Result<()> {
    let database_url = "postgresql://postgres:postgres@localhost:5432/fintech_db";
    let pool = PgPool::connect(database_url).await
        .map_err(|_| StrategyError::DatabaseConnectionFailed)?;
    
    let price_decimal = BigDecimal::from_str(&price.to_string())
        .map_err(|_| StrategyError::DatabaseInsertFailed)?;
    let confidence_decimal = BigDecimal::from_str(&confidence.to_string())
        .map_err(|_| StrategyError::DatabaseInsertFailed)?;
    
    sqlx::query!(
        "INSERT INTO trades (time, symbol, price, volume, strategy_type, confidence) VALUES (NOW(), $1, $2, $3, $4, $5)",
        symbol, price_decimal, volume, strategy_type, confidence_decimal
    )
    .execute(&pool)
    .await
    .map_err(|_| StrategyError::DatabaseInsertFailed)?;
    
    pool.close().await;
    Ok(())
}

async fn store_strategy_health_async(
    nft_id: String,
    health_status: String,
    performance_score: f64,
    last_check_timestamp: i64,
) -> Result<()> {
    let database_url = "postgresql://postgres:postgres@localhost:5432/fintech_db";
    let pool = PgPool::connect(database_url).await
        .map_err(|_| StrategyError::DatabaseConnectionFailed)?;
    
    let performance_decimal = BigDecimal::from_str(&performance_score.to_string())
        .map_err(|_| StrategyError::DatabaseInsertFailed)?;
    
    sqlx::query!(
        "INSERT INTO strategy_health (time, nft_id, health_status, performance_score, last_check) VALUES (NOW(), $1, $2, $3, to_timestamp($4))",
        nft_id, health_status, performance_decimal, last_check_timestamp
    )
    .execute(&pool)
    .await
    .map_err(|_| StrategyError::DatabaseInsertFailed)?;
    
    pool.close().await;
    Ok(())
}

async fn query_strategy_performance_async(
    nft_id: String,
    time_window_hours: i32,
) -> Result<f64> {
    let database_url = "postgresql://postgres:postgres@localhost:5432/fintech_db";
    let pool = PgPool::connect(database_url).await
        .map_err(|_| StrategyError::DatabaseConnectionFailed)?;
    
    let result = sqlx::query!(
        "SELECT AVG(performance_score) as avg_performance FROM strategy_health WHERE nft_id = $1 AND time >= NOW() - INTERVAL '%d hours'",
        nft_id, time_window_hours
    )
    .fetch_one(&pool)
    .await
    .map_err(|_| StrategyError::DatabaseQueryFailed)?;
    
    pool.close().await;
    
    let avg_performance = result.avg_performance
        .and_then(|d| d.to_string().parse::<f64>().ok())
        .unwrap_or(0.0);
    
    Ok(avg_performance)
}

#[derive(Accounts)]
pub struct CreateStrategyNFT<'info> {
    #[account(init, payer = creator, space = 8 + StrategyNFT::INIT_SPACE)]
    pub strategy_nft: Account<'info, StrategyNFT>,
    #[account(mut)]
    pub creator: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct VerifyStrategyProof<'info> {
    #[account(mut)]
    pub strategy_nft: Account<'info, StrategyNFT>,
    pub verifier: Signer<'info>,
}

#[derive(Accounts)]
pub struct PurchaseStrategyAccess<'info> {
    #[account(mut)]
    pub strategy_nft: Account<'info, StrategyNFT>,
    #[account(init, payer = buyer, space = 8 + StrategyAccessRecord::INIT_SPACE)]
    pub access_record: Account<'info, StrategyAccessRecord>,
    #[account(mut)]
    pub buyer: Signer<'info>,
    #[account(mut)]
    pub buyer_token_account: Account<'info, TokenAccount>,
    #[account(mut)]
    pub creator_token_account: Account<'info, TokenAccount>,
    pub token_program: Program<'info, Token>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct ExecuteTradeCopy<'info> {
    pub access_record: Account<'info, StrategyAccessRecord>,
    pub trader: Signer<'info>,
}

#[event]
pub struct StrategyNFTCreated {
    pub nft_id: Pubkey,
    pub creator: Pubkey,
    pub verification_hash: [u8; 32],
    pub performance_target: f64,
    pub access_price: u64,
    pub timestamp: i64,
}

#[event]
pub struct StrategyVerified {
    pub nft_id: Pubkey,
    pub performance_claim: f64,
    pub verification_result: bool,
    pub timestamp: i64,
}

#[event]
pub struct StrategyAccessPurchased {
    pub buyer: Pubkey,
    pub nft_id: Pubkey,
    pub access_price: u64,
    pub expires_at: i64,
    pub timestamp: i64,
}

#[event]
pub struct TradeCopyExecuted {
    pub buyer: Pubkey,
    pub trade_result: TradeExecutionResult,
    pub timestamp: i64,
}

#[error_code]
pub enum StrategyError {
    #[msg("Invalid performance target")]
    InvalidPerformanceTarget,
    #[msg("Invalid access price")]
    InvalidAccessPrice,
    #[msg("Strategy is inactive")]
    StrategyInactive,
    #[msg("Strategy health is not healthy")]
    UnhealthyStrategy,
    #[msg("Trade copying is disabled")]
    TradeCopyingDisabled,
    #[msg("Access has expired")]
    AccessExpired,
    #[msg("Database connection failed")]
    DatabaseConnectionFailed,
    #[msg("Database insert operation failed")]
    DatabaseInsertFailed,
    #[msg("Database query operation failed")]
    DatabaseQueryFailed,
}
