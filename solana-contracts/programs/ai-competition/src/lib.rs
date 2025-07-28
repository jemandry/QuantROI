use anchor_lang::prelude::*;
use sqlx::PgPool;
use bigdecimal::BigDecimal;
use std::str::FromStr;

declare_id!("11111111111111111111111111111115");

#[program]
pub mod ai_competition {
    use super::*;

    pub fn initialize(_ctx: Context<Initialize>) -> Result<()> {
        Ok(())
    }

    pub fn execute_gated_deep_q_learning(
        ctx: Context<ExecuteGatedDeepQLearning>,
        market_state: MarketState,
    ) -> Result<QLearningResult> {
        let strategy = &mut ctx.accounts.strategy;
        
        let gru_features = extract_gru_features(&market_state, &strategy.gru_network_config)?;
        
        let q_values = calculate_q_values(&gru_features, &strategy.q_value_model)?;
        
        let selected_action = select_action_epsilon_greedy(&q_values, strategy.q_value_model.epsilon)?;
        
        let reward = execute_trade_action(&selected_action, &market_state)?;
        
        store_experience(&strategy.experience_replay, &market_state, &selected_action, reward)?;
        
        let experience_replay = strategy.experience_replay.clone();
        update_q_network(&mut strategy.q_value_model, &experience_replay)?;
        
        if should_update_target_network(&strategy.performance_metrics) {
            let q_value_model = strategy.q_value_model.clone();
            update_target_network(&mut strategy.target_network, &q_value_model)?;
        }
        
        store_trade_async(
            market_state.symbol.clone(),
            market_state.price,
            market_state.volume as i32,
            "GatedDeepQLearning".to_string(),
            q_values[selected_action.action_index as usize],
        );
        
        Ok(QLearningResult {
            action: selected_action.clone(),
            q_value: q_values[selected_action.action_index as usize],
            reward,
            epsilon: strategy.q_value_model.epsilon,
        })
    }

    pub fn execute_gated_policy_gradient(
        ctx: Context<ExecuteGatedPolicyGradient>,
        market_state: MarketState,
    ) -> Result<PolicyGradientResult> {
        let strategy = &mut ctx.accounts.strategy;
        
        let gru_features = extract_gru_features(&market_state, &strategy.gru_network_config)?;
        
        let action_probs = calculate_action_probabilities(&gru_features, &strategy.policy_network)?;
        
        let selected_action = sample_action_from_policy(&action_probs)?;
        
        let state_value = calculate_state_value(&gru_features, &strategy.value_network)?;
        
        let reward = execute_trade_action(&selected_action, &market_state)?;
        
        let advantage = calculate_gae_advantage(
            reward,
            state_value,
            &strategy.advantage_estimation
        )?;
        
        update_policy_network(
            &mut strategy.policy_network,
            &gru_features,
            &selected_action,
            advantage
        )?;
        
        update_value_network(
            &mut strategy.value_network,
            &gru_features,
            reward
        )?;
        
        Ok(PolicyGradientResult {
            action: selected_action.clone(),
            action_probability: action_probs[selected_action.action_index as usize],
            state_value,
            advantage,
            reward,
        })
    }

    pub fn adaptive_strategy_switch(
        ctx: Context<AdaptiveStrategySwitch>,
        market_conditions: MarketConditions,
        qos_requirements: QoSRequirements,
    ) -> Result<()> {
        let manager = &mut ctx.accounts.strategy_manager;
        
        let current_regime = detect_market_regime(&market_conditions, &manager.market_regime_detector)?;
        
        let current_performance = evaluate_strategy_performance(
            &manager.performance_tracker,
            manager.switching_criteria.performance_window
        )?;
        
        let optimal_strategy = determine_optimal_strategy(
            &current_regime,
            &qos_requirements,
            current_performance,
            &manager.switching_criteria
        )?;
        
        if optimal_strategy != manager.current_strategy {
            switch_strategy(manager, optimal_strategy.clone())?;
            
            emit!(StrategySwitch {
                old_strategy: manager.current_strategy.clone(),
                new_strategy: optimal_strategy,
                market_regime: current_regime.clone(),
                performance_score: current_performance,
                timestamp: Clock::get()?.unix_timestamp,
            });
        }
        
        Ok(())
    }
}

#[derive(Accounts)]
pub struct Initialize {}

#[derive(Accounts)]
pub struct ExecuteGatedDeepQLearning<'info> {
    #[account(mut)]
    pub strategy: Account<'info, GatedDeepQLearning>,
    pub signer: Signer<'info>,
}

#[derive(Accounts)]
pub struct ExecuteGatedPolicyGradient<'info> {
    #[account(mut)]
    pub strategy: Account<'info, GatedPolicyGradient>,
    pub signer: Signer<'info>,
}

#[derive(Accounts)]
pub struct AdaptiveStrategySwitch<'info> {
    #[account(mut)]
    pub strategy_manager: Account<'info, AdaptiveStrategyManager>,
    pub signer: Signer<'info>,
}

#[account]
pub struct GatedDeepQLearning {
    pub strategy_id: u64,
    pub gru_network_config: GRUNetworkConfig,
    pub q_value_model: QValueModel,
    pub experience_replay: ExperienceReplay,
    pub target_network: TargetNetwork,
    pub performance_metrics: PerformanceMetrics,
}

#[account]
pub struct GatedPolicyGradient {
    pub strategy_id: u64,
    pub gru_network_config: GRUNetworkConfig,
    pub policy_network: PolicyNetwork,
    pub value_network: ValueNetwork,
    pub advantage_estimation: AdvantageEstimation,
    pub performance_metrics: PerformanceMetrics,
}

#[account]
pub struct AdaptiveStrategyManager {
    pub manager_id: u64,
    pub current_strategy: RLStrategyType,
    pub market_regime_detector: MarketRegimeDetector,
    pub performance_tracker: PerformanceTracker,
    pub switching_criteria: SwitchingCriteria,
    pub qos_requirements: QoSRequirements,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, PartialEq)]
pub struct GRUNetworkConfig {
    pub hidden_size: u32,
    pub num_layers: u8,
    pub dropout_rate: f64,
    pub sequence_length: u32,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct QValueModel {
    pub state_dim: u32,
    pub action_dim: u32,
    pub learning_rate: f64,
    pub epsilon: f64,
    pub epsilon_decay: f64,
    pub min_epsilon: f64,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct PolicyNetwork {
    pub state_dim: u32,
    pub action_dim: u32,
    pub learning_rate: f64,
    pub entropy_coefficient: f64,
    pub clip_ratio: f64,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct ValueNetwork {
    pub state_dim: u32,
    pub learning_rate: f64,
    pub value_loss_coefficient: f64,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct AdvantageEstimation {
    pub gamma: f64,
    pub lambda: f64,
    pub normalize_advantages: bool,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq)]
pub struct ExperienceReplay {
    pub buffer_size: u32,
    pub batch_size: u32,
    pub current_size: u32,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct TargetNetwork {
    pub update_frequency: u32,
    pub last_update: i64,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct PerformanceMetrics {
    pub total_trades: u64,
    pub successful_trades: u64,
    pub total_return: f64,
    pub sharpe_ratio: f64,
    pub max_drawdown: f64,
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
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct SwitchingCriteria {
    pub performance_window: u32,
    pub min_performance_threshold: f64,
    pub volatility_switch_threshold: f64,
    pub qos_latency_threshold: u32,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq)]
pub enum RLStrategyType {
    GatedDeepQLearning,
    GatedPolicyGradient,
    TemporalFusionTransformer,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy)]
pub enum MarketRegime {
    Bull,
    Bear,
    Sideways,
    HighVolatility,
    LowVolatility,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct MarketState {
    pub symbol: String,
    pub price: f64,
    pub volume: f64,
    pub volatility: f64,
    pub timestamp: i64,
    pub features: Vec<f64>,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy)]
pub struct TradingAction {
    pub action_type: ActionType,
    pub quantity: f64,
    pub price_limit: Option<f64>,
    pub action_index: u32,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy)]
pub enum ActionType {
    Buy,
    Sell,
    Hold,
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
pub struct QLearningResult {
    pub action: TradingAction,
    pub q_value: f64,
    pub reward: f64,
    pub epsilon: f64,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct PolicyGradientResult {
    pub action: TradingAction,
    pub action_probability: f64,
    pub state_value: f64,
    pub advantage: f64,
    pub reward: f64,
}

#[event]
pub struct StrategySwitch {
    pub old_strategy: RLStrategyType,
    pub new_strategy: RLStrategyType,
    pub market_regime: MarketRegime,
    pub performance_score: f64,
    pub timestamp: i64,
}

#[error_code]
pub enum AICompetitionError {
    #[msg("Invalid competition parameters")]
    InvalidParameters,
    #[msg("Invalid market state")]
    InvalidMarketState,
    #[msg("Strategy execution failed")]
    StrategyExecutionFailed,
    #[msg("Invalid Q-learning parameters")]
    InvalidQLearningParameters,
    #[msg("Invalid policy gradient parameters")]
    InvalidPolicyGradientParameters,
    #[msg("Market regime detection failed")]
    MarketRegimeDetectionFailed,
    #[msg("Strategy switching failed")]
    StrategySwitchingFailed,
    #[msg("Database connection failed")]
    DatabaseConnectionFailed,
    #[msg("Database insert operation failed")]
    DatabaseInsertFailed,
}

fn extract_gru_features(market_state: &MarketState, _config: &GRUNetworkConfig) -> Result<Vec<f64>> {
    let mut features = Vec::new();
    
    features.push(market_state.price);
    features.push(market_state.volume);
    features.push(market_state.volatility);
    features.extend_from_slice(&market_state.features);
    
    Ok(features)
}

fn calculate_q_values(features: &[f64], model: &QValueModel) -> Result<Vec<f64>> {
    let mut q_values = vec![0.0; model.action_dim as usize];
    
    for i in 0..model.action_dim as usize {
        q_values[i] = features.iter().sum::<f64>() * (i as f64 + 1.0) * 0.1;
    }
    
    Ok(q_values)
}

fn select_action_epsilon_greedy(q_values: &[f64], epsilon: f64) -> Result<TradingAction> {
    let action_index = if rand::random::<f64>() < epsilon {
        rand::random::<usize>() % q_values.len()
    } else {
        q_values.iter()
            .enumerate()
            .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap())
            .map(|(index, _)| index)
            .unwrap_or(0)
    };
    
    Ok(TradingAction {
        action_type: match action_index {
            0 => ActionType::Buy,
            1 => ActionType::Sell,
            _ => ActionType::Hold,
        },
        quantity: 100.0,
        price_limit: None,
        action_index: action_index as u32,
    })
}

fn execute_trade_action(action: &TradingAction, market_state: &MarketState) -> Result<f64> {
    let base_reward = match action.action_type {
        ActionType::Buy => market_state.price * 0.001,
        ActionType::Sell => market_state.price * 0.002,
        ActionType::Hold => 0.0,
    };
    
    Ok(base_reward * action.quantity)
}

fn store_experience(
    _replay: &ExperienceReplay,
    _market_state: &MarketState,
    _action: &TradingAction,
    _reward: f64,
) -> Result<()> {
    Ok(())
}

fn update_q_network(model: &mut QValueModel, _replay: &ExperienceReplay) -> Result<()> {
    model.epsilon = (model.epsilon * model.epsilon_decay).max(model.min_epsilon);
    Ok(())
}

fn should_update_target_network(metrics: &PerformanceMetrics) -> bool {
    metrics.total_trades % 100 == 0
}

fn update_target_network(target: &mut TargetNetwork, _model: &QValueModel) -> Result<()> {
    target.last_update = Clock::get()?.unix_timestamp;
    Ok(())
}

fn calculate_action_probabilities(features: &[f64], network: &PolicyNetwork) -> Result<Vec<f64>> {
    let mut probs = vec![0.0; network.action_dim as usize];
    let sum: f64 = features.iter().sum();
    
    for i in 0..network.action_dim as usize {
        probs[i] = (sum * (i as f64 + 1.0)).exp();
    }
    
    let total: f64 = probs.iter().sum();
    for prob in &mut probs {
        *prob /= total;
    }
    
    Ok(probs)
}

fn sample_action_from_policy(action_probs: &[f64]) -> Result<TradingAction> {
    let random_val = rand::random::<f64>();
    let mut cumulative = 0.0;
    
    for (i, &prob) in action_probs.iter().enumerate() {
        cumulative += prob;
        if random_val <= cumulative {
            return Ok(TradingAction {
                action_type: match i {
                    0 => ActionType::Buy,
                    1 => ActionType::Sell,
                    _ => ActionType::Hold,
                },
                quantity: 100.0,
                price_limit: None,
                action_index: i as u32,
            });
        }
    }
    
    Ok(TradingAction {
        action_type: ActionType::Hold,
        quantity: 0.0,
        price_limit: None,
        action_index: 2,
    })
}

fn calculate_state_value(features: &[f64], _network: &ValueNetwork) -> Result<f64> {
    Ok(features.iter().sum::<f64>() * 0.01)
}

fn calculate_gae_advantage(reward: f64, state_value: f64, _estimation: &AdvantageEstimation) -> Result<f64> {
    Ok(reward - state_value)
}

fn update_policy_network(
    _network: &mut PolicyNetwork,
    _features: &[f64],
    _action: &TradingAction,
    _advantage: f64,
) -> Result<()> {
    Ok(())
}

fn update_value_network(
    _network: &mut ValueNetwork,
    _features: &[f64],
    _reward: f64,
) -> Result<()> {
    Ok(())
}

fn detect_market_regime(
    conditions: &MarketConditions,
    detector: &MarketRegimeDetector,
) -> Result<MarketRegime> {
    if conditions.volatility > detector.volatility_threshold {
        Ok(MarketRegime::HighVolatility)
    } else if conditions.trend_strength > detector.trend_strength_threshold {
        if conditions.current_price > 0.0 {
            Ok(MarketRegime::Bull)
        } else {
            Ok(MarketRegime::Bear)
        }
    } else {
        Ok(MarketRegime::Sideways)
    }
}

fn evaluate_strategy_performance(tracker: &PerformanceTracker, _window: u32) -> Result<f64> {
    Ok(tracker.performance_score)
}

fn determine_optimal_strategy(
    market_regime: &MarketRegime,
    qos_requirements: &QoSRequirements,
    _current_performance: f64,
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

fn switch_strategy(manager: &mut AdaptiveStrategyManager, new_strategy: RLStrategyType) -> Result<()> {
    manager.current_strategy = new_strategy;
    Ok(())
}

pub async fn store_trade_async(
    symbol: String,
    price: f64,
    volume: i32,
    strategy_type: String,
    confidence: f64,
) -> Result<()> {
    let database_url = "postgresql://postgres:postgres@localhost:5432/fintech_db";
    let pool = PgPool::connect(database_url).await
        .map_err(|_| AICompetitionError::DatabaseConnectionFailed)?;
    
    let price_decimal = BigDecimal::from_str(&price.to_string())
        .map_err(|_| AICompetitionError::DatabaseInsertFailed)?;
    let confidence_decimal = BigDecimal::from_str(&confidence.to_string())
        .map_err(|_| AICompetitionError::DatabaseInsertFailed)?;
    
    sqlx::query!(
        "INSERT INTO trades (time, symbol, price, volume, strategy_type, confidence) VALUES (NOW(), $1, $2, $3, $4, $5)",
        symbol, price_decimal, volume, strategy_type, confidence_decimal
    )
    .execute(&pool)
    .await
    .map_err(|_| AICompetitionError::DatabaseInsertFailed)?;
    
    pool.close().await;
    Ok(())
}
