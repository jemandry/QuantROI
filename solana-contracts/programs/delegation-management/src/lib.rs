use anchor_lang::prelude::*;
use anchor_spl::token::{self, Token, TokenAccount, Transfer};
use sha3::{Digest, Sha3_256};

declare_id!("DeLegationManagementProgram11111111111111111");

#[program]
pub mod delegation_management {
    use super::*;

    pub fn initialize_delegation(
        ctx: Context<InitializeDelegation>,
        ai_policy_pubkey: Pubkey,
        delegation_amount: u64,
        delegation_type: DelegationType,
    ) -> Result<()> {
        let delegation = &mut ctx.accounts.delegation;
        let clock = Clock::get()?;
        
        let mut hasher = Sha3_256::new();
        hasher.update(ctx.accounts.bank_authority.key().as_ref());
        hasher.update(ai_policy_pubkey.as_ref());
        hasher.update(&delegation_amount.to_le_bytes());
        hasher.update(&clock.unix_timestamp.to_le_bytes());
        let hash = hasher.finalize();
        
        delegation.bank_authority = ctx.accounts.bank_authority.key();
        delegation.ai_policy_pubkey = ai_policy_pubkey;
        delegation.delegation_amount = delegation_amount;
        delegation.delegation_type = delegation_type;
        delegation.created_at = clock.unix_timestamp;
        delegation.is_active = true;
        delegation.performance_score = 0;
        delegation.total_trades = 0;
        delegation.total_profit_loss = 0;
        delegation.cryptographic_hash = hash.to_vec();
        
        emit!(DelegationInitialized {
            delegation_id: delegation.key(),
            bank_authority: ctx.accounts.bank_authority.key(),
            ai_policy: ai_policy_pubkey,
            amount: delegation_amount,
            timestamp: clock.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn execute_ai_trade(
        ctx: Context<ExecuteAiTrade>,
        trade_amount: u64,
        trade_direction: TradeDirection,
        ai_confidence_score: u8,
    ) -> Result<()> {
        let delegation = &mut ctx.accounts.delegation;
        let clock = Clock::get()?;
        
        require!(delegation.is_active, DelegationError::DelegationInactive);
        require!(ai_confidence_score >= 70, DelegationError::LowConfidenceScore);
        require!(trade_amount <= delegation.delegation_amount, DelegationError::InsufficientFunds);
        
        let trade_result = match trade_direction {
            TradeDirection::Buy => {
                let profit = (trade_amount as f64 * 0.001) as i64; // 0.1% microgain
                delegation.total_profit_loss += profit;
                profit
            },
            TradeDirection::Sell => {
                let profit = (trade_amount as f64 * 0.002) as i64; // 0.2% microgain
                delegation.total_profit_loss += profit;
                profit
            },
        };
        
        delegation.total_trades += 1;
        delegation.performance_score = calculate_performance_score(
            delegation.total_profit_loss,
            delegation.total_trades,
        );
        
        let mut hasher = Sha3_256::new();
        hasher.update(&delegation.key().to_bytes());
        hasher.update(&trade_amount.to_le_bytes());
        hasher.update(&(trade_direction as u8).to_le_bytes());
        hasher.update(&clock.unix_timestamp.to_le_bytes());
        let trade_hash = hasher.finalize();
        
        emit!(TradeExecuted {
            delegation_id: delegation.key(),
            trade_amount,
            trade_direction,
            profit_loss: trade_result,
            confidence_score: ai_confidence_score,
            trade_hash: trade_hash.to_vec(),
            timestamp: clock.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn execute_adaptive_rl_trade(
        ctx: Context<ExecuteAdaptiveRLTrade>,
        market_conditions: MarketConditions,
        qos_requirements: QoSRequirements,
        strategy_preference: Option<RLStrategyType>,
    ) -> Result<AdaptiveTradeResult> {
        let delegation = &mut ctx.accounts.delegation;
        let strategy_manager = &mut ctx.accounts.strategy_manager;
        let clock = Clock::get()?;
        
        require!(delegation.is_active, DelegationError::DelegationInactive);
        
        let current_regime = detect_market_regime(&market_conditions, &strategy_manager.market_regime_detector)?;
        
        let optimal_strategy = if let Some(preferred) = strategy_preference {
            preferred
        } else {
            determine_optimal_rl_strategy(
                &current_regime,
                &qos_requirements,
                &strategy_manager.switching_criteria
            )?
        };
        
        let trade_result = match optimal_strategy {
            RLStrategyType::GatedDeepQLearning => {
                execute_gated_dql_trade(&market_conditions, &qos_requirements)?
            },
            RLStrategyType::GatedPolicyGradient => {
                execute_gated_pg_trade(&market_conditions, &qos_requirements)?
            },
            RLStrategyType::TemporalFusionTransformer => {
                execute_tft_trade(&market_conditions, &qos_requirements)?
            },
        };
        
        if optimal_strategy != strategy_manager.current_strategy {
            strategy_manager.current_strategy = optimal_strategy;
            
            emit!(StrategySwitch {
                delegation_id: delegation.key(),
                old_strategy: strategy_manager.current_strategy,
                new_strategy: optimal_strategy,
                market_regime: current_regime,
                timestamp: clock.unix_timestamp,
            });
        }
        
        delegation.total_trades += 1;
        delegation.performance_score = calculate_performance_score(
            delegation.total_profit_loss,
            delegation.total_trades,
        );
        
        emit!(AdaptiveTradeExecuted {
            delegation_id: delegation.key(),
            strategy_used: optimal_strategy,
            market_regime: current_regime,
            trade_result: trade_result.clone(),
            timestamp: clock.unix_timestamp,
        });
        
        Ok(trade_result)
    }

    pub fn update_delegation_status(
        ctx: Context<UpdateDelegationStatus>,
        new_status: bool,
    ) -> Result<()> {
        let delegation = &mut ctx.accounts.delegation;
        let clock = Clock::get()?;
        
        delegation.is_active = new_status;
        
        emit!(DelegationStatusUpdated {
            delegation_id: delegation.key(),
            new_status,
            timestamp: clock.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn revoke_delegation(ctx: Context<RevokeDelegation>) -> Result<()> {
        let delegation = &mut ctx.accounts.delegation;
        let clock = Clock::get()?;
        
        delegation.is_active = false;
        
        emit!(DelegationRevoked {
            delegation_id: delegation.key(),
            bank_authority: delegation.bank_authority,
            timestamp: clock.unix_timestamp,
        });
        
        Ok(())
    }
}

#[account]
pub struct DelegationAccount {
    pub bank_authority: Pubkey,           // 32 bytes
    pub ai_policy_pubkey: Pubkey,         // 32 bytes
    pub delegation_amount: u64,           // 8 bytes
    pub delegation_type: DelegationType,  // 1 byte
    pub created_at: i64,                  // 8 bytes
    pub is_active: bool,                  // 1 byte
    pub performance_score: u32,           // 4 bytes
    pub total_trades: u64,                // 8 bytes
    pub total_profit_loss: i64,           // 8 bytes
    pub cryptographic_hash: Vec<u8>,      // 32 bytes (SHA-3)
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, PartialEq, Eq)]
pub enum DelegationType {
    Partial,
    Full,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, PartialEq, Eq)]
pub enum TradeDirection {
    Buy,
    Sell,
}

#[derive(Accounts)]
pub struct InitializeDelegation<'info> {
    #[account(
        init,
        payer = bank_authority,
        space = 8 + 32 + 32 + 8 + 1 + 8 + 1 + 4 + 8 + 8 + 64, // Account discriminator + data
        seeds = [b"delegation", bank_authority.key().as_ref()],
        bump
    )]
    pub delegation: Account<'info, DelegationAccount>,
    #[account(mut)]
    pub bank_authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct ExecuteAiTrade<'info> {
    #[account(
        mut,
        seeds = [b"delegation", delegation.bank_authority.as_ref()],
        bump,
        constraint = delegation.is_active @ DelegationError::DelegationInactive
    )]
    pub delegation: Account<'info, DelegationAccount>,
    pub ai_authority: Signer<'info>,
}

#[derive(Accounts)]
pub struct ExecuteAdaptiveRLTrade<'info> {
    #[account(
        mut,
        seeds = [b"delegation", delegation.bank_authority.as_ref()],
        bump,
        constraint = delegation.is_active @ DelegationError::DelegationInactive
    )]
    pub delegation: Account<'info, DelegationAccount>,
    #[account(
        mut,
        seeds = [b"strategy_manager", delegation.key().as_ref()],
        bump
    )]
    pub strategy_manager: Account<'info, AdaptiveStrategyManager>,
    pub ai_authority: Signer<'info>,
}

#[derive(Accounts)]
pub struct UpdateDelegationStatus<'info> {
    #[account(
        mut,
        seeds = [b"delegation", delegation.bank_authority.as_ref()],
        bump,
        constraint = delegation.bank_authority == bank_authority.key() @ DelegationError::UnauthorizedAccess
    )]
    pub delegation: Account<'info, DelegationAccount>,
    pub bank_authority: Signer<'info>,
}

#[derive(Accounts)]
pub struct RevokeDelegation<'info> {
    #[account(
        mut,
        seeds = [b"delegation", delegation.bank_authority.as_ref()],
        bump,
        constraint = delegation.bank_authority == bank_authority.key() @ DelegationError::UnauthorizedAccess
    )]
    pub delegation: Account<'info, DelegationAccount>,
    pub bank_authority: Signer<'info>,
}

#[event]
pub struct DelegationInitialized {
    pub delegation_id: Pubkey,
    pub bank_authority: Pubkey,
    pub ai_policy: Pubkey,
    pub amount: u64,
    pub timestamp: i64,
}

#[event]
pub struct TradeExecuted {
    pub delegation_id: Pubkey,
    pub trade_amount: u64,
    pub trade_direction: TradeDirection,
    pub profit_loss: i64,
    pub confidence_score: u8,
    pub trade_hash: Vec<u8>,
    pub timestamp: i64,
}

#[event]
pub struct DelegationStatusUpdated {
    pub delegation_id: Pubkey,
    pub new_status: bool,
    pub timestamp: i64,
}

#[event]
pub struct DelegationRevoked {
    pub delegation_id: Pubkey,
    pub bank_authority: Pubkey,
    pub timestamp: i64,
}

#[account]
pub struct AdaptiveStrategyManager {
    pub manager_id: u64,
    pub delegation_id: Pubkey,
    pub current_strategy: RLStrategyType,
    pub market_regime_detector: MarketRegimeDetector,
    pub performance_tracker: PerformanceTracker,
    pub switching_criteria: SwitchingCriteria,
    pub strategy_performance_history: Vec<StrategyPerformance>,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, PartialEq)]
pub enum RLStrategyType {
    GatedDeepQLearning,
    GatedPolicyGradient,
    TemporalFusionTransformer,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct MarketRegimeDetector {
    pub volatility_threshold: f64,
    pub trend_strength_threshold: f64,
    pub volume_threshold: f64,
    pub regime_history: Vec<MarketRegime>,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct PerformanceTracker {
    pub window_size: u32,
    pub recent_returns: Vec<f64>,
    pub performance_score: f64,
    pub strategy_switches: u32,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct SwitchingCriteria {
    pub performance_window: u32,
    pub min_performance_threshold: f64,
    pub volatility_switch_threshold: f64,
    pub qos_latency_threshold: u32,
    pub trend_strength_threshold: f64,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct StrategyPerformance {
    pub strategy: RLStrategyType,
    pub performance_score: f64,
    pub trades_executed: u32,
    pub timestamp: i64,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub enum MarketRegime {
    Bull,
    Bear,
    Sideways,
    HighVolatility,
    LowVolatility,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct MarketConditions {
    pub current_price: f64,
    pub volatility: f64,
    pub volume: f64,
    pub trend_strength: f64,
    pub market_sentiment: f64,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct QoSRequirements {
    pub latency_requirement: u32,
    pub throughput_requirement: u32,
    pub accuracy_requirement: f64,
    pub priority_level: u8,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct AdaptiveTradeResult {
    pub action: ActionType,
    pub quantity: f64,
    pub confidence: f64,
    pub expected_return: f64,
    pub strategy_used: RLStrategyType,
    pub execution_time_ms: u32,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub enum ActionType {
    Buy,
    Sell,
    Hold,
}

#[event]
pub struct StrategySwitch {
    pub delegation_id: Pubkey,
    pub old_strategy: RLStrategyType,
    pub new_strategy: RLStrategyType,
    pub market_regime: MarketRegime,
    pub timestamp: i64,
}

#[event]
pub struct AdaptiveTradeExecuted {
    pub delegation_id: Pubkey,
    pub strategy_used: RLStrategyType,
    pub market_regime: MarketRegime,
    pub trade_result: AdaptiveTradeResult,
    pub timestamp: i64,
}

#[error_code]
pub enum DelegationError {
    #[msg("Delegation is not active")]
    DelegationInactive,
    #[msg("AI confidence score too low")]
    LowConfidenceScore,
    #[msg("Insufficient funds for trade")]
    InsufficientFunds,
    #[msg("Unauthorized access")]
    UnauthorizedAccess,
}

fn calculate_performance_score(total_profit_loss: i64, total_trades: u64) -> u32 {
    if total_trades == 0 {
        return 0;
    }
    
    let avg_profit = total_profit_loss as f64 / total_trades as f64;
    let score = (avg_profit * 1000.0).max(0.0).min(100000.0) as u32;
    score
}

fn detect_market_regime(
    conditions: &MarketConditions,
    detector: &MarketRegimeDetector,
) -> Result<MarketRegime> {
    if conditions.volatility > detector.volatility_threshold {
        Ok(MarketRegime::HighVolatility)
    } else if conditions.trend_strength.abs() > detector.trend_strength_threshold {
        if conditions.trend_strength > 0.0 {
            Ok(MarketRegime::Bull)
        } else {
            Ok(MarketRegime::Bear)
        }
    } else {
        Ok(MarketRegime::Sideways)
    }
}

fn determine_optimal_rl_strategy(
    market_regime: &MarketRegime,
    qos_requirements: &QoSRequirements,
    criteria: &SwitchingCriteria,
) -> Result<RLStrategyType> {
    match (market_regime, qos_requirements.latency_requirement) {
        (_, latency) if latency < criteria.qos_latency_threshold => {
            Ok(RLStrategyType::GatedDeepQLearning)
        },
        (MarketRegime::Bull | MarketRegime::Bear, _) => {
            Ok(RLStrategyType::GatedPolicyGradient)
        },
        (MarketRegime::HighVolatility, _) => {
            Ok(RLStrategyType::GatedDeepQLearning)
        },
        _ => Ok(RLStrategyType::TemporalFusionTransformer),
    }
}

fn execute_gated_dql_trade(
    conditions: &MarketConditions,
    _qos_requirements: &QoSRequirements,
) -> Result<AdaptiveTradeResult> {
    let start_time = Clock::get()?.unix_timestamp;
    
    let action = if conditions.current_price > conditions.volatility {
        ActionType::Buy
    } else if conditions.current_price < -conditions.volatility {
        ActionType::Sell
    } else {
        ActionType::Hold
    };
    
    let quantity = match action {
        ActionType::Hold => 0.0,
        _ => 100.0,
    };
    
    let execution_time = (Clock::get()?.unix_timestamp - start_time) as u32;
    
    Ok(AdaptiveTradeResult {
        action,
        quantity,
        confidence: 0.85,
        expected_return: 0.002,
        strategy_used: RLStrategyType::GatedDeepQLearning,
        execution_time_ms: execution_time,
    })
}

fn execute_gated_pg_trade(
    conditions: &MarketConditions,
    _qos_requirements: &QoSRequirements,
) -> Result<AdaptiveTradeResult> {
    let start_time = Clock::get()?.unix_timestamp;
    
    let trend_signal = conditions.trend_strength * conditions.market_sentiment;
    
    let action = if trend_signal > 0.1 {
        ActionType::Buy
    } else if trend_signal < -0.1 {
        ActionType::Sell
    } else {
        ActionType::Hold
    };
    
    let quantity = match action {
        ActionType::Hold => 0.0,
        _ => 150.0,
    };
    
    let execution_time = (Clock::get()?.unix_timestamp - start_time) as u32;
    
    Ok(AdaptiveTradeResult {
        action,
        quantity,
        confidence: 0.78,
        expected_return: 0.003,
        strategy_used: RLStrategyType::GatedPolicyGradient,
        execution_time_ms: execution_time,
    })
}

fn execute_tft_trade(
    _conditions: &MarketConditions,
    _qos_requirements: &QoSRequirements,
) -> Result<AdaptiveTradeResult> {
    let start_time = Clock::get()?.unix_timestamp;
    
    let execution_time = (Clock::get()?.unix_timestamp - start_time) as u32;
    
    Ok(AdaptiveTradeResult {
        action: ActionType::Hold,
        quantity: 0.0,
        confidence: 0.60,
        expected_return: 0.001,
        strategy_used: RLStrategyType::TemporalFusionTransformer,
        execution_time_ms: execution_time,
    })
}
