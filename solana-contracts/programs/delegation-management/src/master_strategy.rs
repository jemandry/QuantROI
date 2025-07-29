use anchor_lang::prelude::*;
use crate::{RLStrategyType, MarketConditions, QoSRequirements, AdaptiveTradeResult};

#[account]
pub struct MasterStrategyLearner {
    pub learner_id: u64,
    pub delegation_id: Pubkey,
    pub strategy_performance_matrix: StrategyPerformanceMatrix,
    pub learning_parameters: LearningParameters,
    pub causal_feature_extractor: CausalFeatureExtractor,
    pub total_trades_processed: u64,
    pub last_updated: i64,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct StrategyPerformanceMatrix {
    pub dql_performance: StrategyMetrics,
    pub pg_performance: StrategyMetrics,
    pub tft_performance: StrategyMetrics,
    pub strategy_weights: [f64; 3], // [DQL, PG, TFT]
    pub performance_window: u32,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct StrategyMetrics {
    pub total_trades: u32,
    pub winning_trades: u32,
    pub total_return: f64,
    pub sharpe_ratio: f64,
    pub max_drawdown: f64,
    pub avg_execution_time: f64,
    pub confidence_accuracy: f64,
    pub recent_performance: Vec<f64>, // Rolling window of recent returns
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct LearningParameters {
    pub learning_rate: f64,
    pub exploration_rate: f64,
    pub performance_decay_factor: f64,
    pub min_trades_for_learning: u32,
    pub weight_update_frequency: u32,
    pub causal_learning_enabled: bool,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct CausalFeatureExtractor {
    pub market_regime_features: Vec<f64>,
    pub volatility_patterns: Vec<f64>,
    pub volume_profile_features: Vec<f64>,
    pub sentiment_correlation_matrix: [[f64; 3]; 3], // Strategy x Market condition correlations
    pub temporal_dependencies: Vec<TemporalDependency>,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct TemporalDependency {
    pub lag_periods: u32,
    pub correlation_strength: f64,
    pub strategy_impact: RLStrategyType,
}

impl MasterStrategyLearner {
    pub fn initialize(
        delegation_id: Pubkey,
        learning_rate: f64,
        exploration_rate: f64,
    ) -> Self {
        Self {
            learner_id: Clock::get().unwrap().unix_timestamp as u64,
            delegation_id,
            strategy_performance_matrix: StrategyPerformanceMatrix::default(),
            learning_parameters: LearningParameters {
                learning_rate,
                exploration_rate,
                performance_decay_factor: 0.95,
                min_trades_for_learning: 10,
                weight_update_frequency: 50,
                causal_learning_enabled: true,
            },
            causal_feature_extractor: CausalFeatureExtractor::default(),
            total_trades_processed: 0,
            last_updated: Clock::get().unwrap().unix_timestamp,
        }
    }
    
    pub fn update_strategy_performance(
        &mut self,
        strategy: RLStrategyType,
        trade_result: &AdaptiveTradeResult,
        market_conditions: &MarketConditions,
    ) -> Result<()> {
        self.total_trades_processed += 1;
        
        let trade_return = trade_result.expected_return * trade_result.confidence as f64;
        let execution_time = 1.0; // Simplified for now
        
        match strategy {
            RLStrategyType::GatedDeepQLearning => {
                let metrics = &mut self.strategy_performance_matrix.dql_performance;
                Self::update_strategy_metrics_static(metrics, trade_return, execution_time, trade_result.confidence)?;
            },
            RLStrategyType::GatedPolicyGradient => {
                let metrics = &mut self.strategy_performance_matrix.pg_performance;
                Self::update_strategy_metrics_static(metrics, trade_return, execution_time, trade_result.confidence)?;
            },
            RLStrategyType::TemporalFusionTransformer => {
                let metrics = &mut self.strategy_performance_matrix.tft_performance;
                Self::update_strategy_metrics_static(metrics, trade_return, execution_time, trade_result.confidence)?;
            },
        }
        
        if self.learning_parameters.causal_learning_enabled {
            self.extract_and_update_causal_features(strategy, trade_result, market_conditions)?;
        }
        
        if self.total_trades_processed % self.learning_parameters.weight_update_frequency as u64 == 0 {
            self.update_strategy_weights()?;
        }
        
        self.last_updated = Clock::get()?.unix_timestamp;
        Ok(())
    }
    
    fn update_strategy_metrics_static(
        metrics: &mut StrategyMetrics,
        trade_return: f64,
        execution_time: f64,
        confidence: f64,
    ) -> Result<()> {
        metrics.total_trades += 1;
        
        if trade_return > 0.0 {
            metrics.winning_trades += 1;
        }
        
        metrics.total_return += trade_return;
        
        metrics.recent_performance.push(trade_return);
        if metrics.recent_performance.len() > 100 {
            metrics.recent_performance.remove(0);
        }
        
        if metrics.recent_performance.len() > 1 {
            let mean_return = metrics.recent_performance.iter().sum::<f64>() / metrics.recent_performance.len() as f64;
            let variance = metrics.recent_performance.iter()
                .map(|r| (r - mean_return).powi(2))
                .sum::<f64>() / (metrics.recent_performance.len() - 1) as f64;
            let std_dev = variance.sqrt();
            metrics.sharpe_ratio = if std_dev > 0.0 { mean_return / std_dev } else { 0.0 };
        }
        
        metrics.avg_execution_time = 0.9 * metrics.avg_execution_time + 0.1 * execution_time;
        
        let confidence_error = (confidence - if trade_return > 0.0 { 1.0 } else { 0.0 }).abs();
        metrics.confidence_accuracy = 0.9 * metrics.confidence_accuracy + 0.1 * (1.0 - confidence_error);
        
        Ok(())
    }
    
    fn extract_and_update_causal_features(
        &mut self,
        strategy: RLStrategyType,
        trade_result: &AdaptiveTradeResult,
        market_conditions: &MarketConditions,
    ) -> Result<()> {
        let extractor = &mut self.causal_feature_extractor;
        
        extractor.market_regime_features.push(market_conditions.current_price);
        extractor.volatility_patterns.push(market_conditions.volatility);
        extractor.volume_profile_features.push(market_conditions.volume);
        
        let max_features = 100;
        if extractor.market_regime_features.len() > max_features {
            extractor.market_regime_features.remove(0);
            extractor.volatility_patterns.remove(0);
            extractor.volume_profile_features.remove(0);
        }
        
        let strategy_idx = match strategy {
            RLStrategyType::GatedDeepQLearning => 0,
            RLStrategyType::GatedPolicyGradient => 1,
            RLStrategyType::TemporalFusionTransformer => 2,
        };
        
        let market_condition_idx = if market_conditions.volatility > 0.02 { 0 } 
                                  else if market_conditions.trend_strength.abs() > 0.05 { 1 } 
                                  else { 2 };
        
        let trade_success = if trade_result.expected_return > 0.0 { 1.0 } else { -1.0 };
        let learning_rate = self.learning_parameters.learning_rate;
        
        extractor.sentiment_correlation_matrix[strategy_idx][market_condition_idx] = 
            (1.0 - learning_rate) * extractor.sentiment_correlation_matrix[strategy_idx][market_condition_idx] +
            learning_rate * trade_success * market_conditions.market_sentiment;
        
        Ok(())
    }
    
    fn update_strategy_weights(&mut self) -> Result<()> {
        let dql_score = self.calculate_strategy_score(&self.strategy_performance_matrix.dql_performance);
        let pg_score = self.calculate_strategy_score(&self.strategy_performance_matrix.pg_performance);
        let tft_score = self.calculate_strategy_score(&self.strategy_performance_matrix.tft_performance);
        
        let total_score = dql_score + pg_score + tft_score;
        
        if total_score > 0.0 {
            let exploration = self.learning_parameters.exploration_rate;
            
            self.strategy_performance_matrix.strategy_weights[0] = 
                (1.0 - exploration) * (dql_score / total_score) + exploration / 3.0;
            self.strategy_performance_matrix.strategy_weights[1] = 
                (1.0 - exploration) * (pg_score / total_score) + exploration / 3.0;
            self.strategy_performance_matrix.strategy_weights[2] = 
                (1.0 - exploration) * (tft_score / total_score) + exploration / 3.0;
        } else {
            self.strategy_performance_matrix.strategy_weights = [1.0/3.0, 1.0/3.0, 1.0/3.0];
        }
        
        Ok(())
    }
    
    fn calculate_strategy_score(&self, metrics: &StrategyMetrics) -> f64 {
        if metrics.total_trades < self.learning_parameters.min_trades_for_learning {
            return 1.0; // Default score for strategies with insufficient data
        }
        
        let return_score = metrics.total_return / metrics.total_trades as f64;
        let sharpe_score = metrics.sharpe_ratio.max(0.0);
        let win_rate_score = metrics.winning_trades as f64 / metrics.total_trades as f64;
        let efficiency_score = 1.0 / (1.0 + metrics.avg_execution_time / 1000.0); // Favor faster execution
        let confidence_score = metrics.confidence_accuracy;
        
        0.3 * return_score + 0.25 * sharpe_score + 0.2 * win_rate_score + 
        0.15 * efficiency_score + 0.1 * confidence_score
    }
    
    pub fn select_optimal_strategy(
        &self,
        market_conditions: &MarketConditions,
        qos_requirements: &QoSRequirements,
    ) -> RLStrategyType {
        let base_weights = self.get_base_strategy_weights(market_conditions, qos_requirements);
        
        let learned_weights = &self.strategy_performance_matrix.strategy_weights;
        
        let combined_weights = [
            0.6 * base_weights[0] + 0.4 * learned_weights[0],
            0.6 * base_weights[1] + 0.4 * learned_weights[1],
            0.6 * base_weights[2] + 0.4 * learned_weights[2],
        ];
        
        let max_idx = combined_weights.iter()
            .enumerate()
            .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap())
            .map(|(idx, _)| idx)
            .unwrap_or(0);
        
        match max_idx {
            0 => RLStrategyType::GatedDeepQLearning,
            1 => RLStrategyType::GatedPolicyGradient,
            _ => RLStrategyType::TemporalFusionTransformer,
        }
    }
    
    fn get_base_strategy_weights(
        &self,
        market_conditions: &MarketConditions,
        qos_requirements: &QoSRequirements,
    ) -> [f64; 3] {
        let mut weights = [0.0, 0.0, 0.0];
        
        if qos_requirements.latency_requirement < 5 {
            weights[0] += 0.5;
        }
        
        if market_conditions.volatility > 0.02 {
            weights[0] += 0.3;
        }
        
        if market_conditions.trend_strength.abs() > 0.05 {
            weights[1] += 0.4;
        }
        
        if market_conditions.market_sentiment.abs() > 0.3 {
            weights[2] += 0.3;
        }
        
        let total: f64 = weights.iter().sum();
        if total > 0.0 {
            for weight in &mut weights {
                *weight /= total;
            }
        } else {
            weights = [1.0/3.0, 1.0/3.0, 1.0/3.0];
        }
        
        weights
    }
    
    fn calculate_trade_return(
        &self,
        trade_result: &AdaptiveTradeResult,
        _market_conditions: &MarketConditions,
    ) -> f64 {
        trade_result.expected_return * trade_result.confidence
    }
    
    pub fn get_learning_insights(&self) -> MasterStrategyInsights {
        MasterStrategyInsights {
            total_trades: self.total_trades_processed,
            strategy_weights: self.strategy_performance_matrix.strategy_weights,
            dql_sharpe: self.strategy_performance_matrix.dql_performance.sharpe_ratio,
            pg_sharpe: self.strategy_performance_matrix.pg_performance.sharpe_ratio,
            tft_sharpe: self.strategy_performance_matrix.tft_performance.sharpe_ratio,
            learning_rate: self.learning_parameters.learning_rate,
            exploration_rate: self.learning_parameters.exploration_rate,
            last_updated: self.last_updated,
        }
    }
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct MasterStrategyInsights {
    pub total_trades: u64,
    pub strategy_weights: [f64; 3],
    pub dql_sharpe: f64,
    pub pg_sharpe: f64,
    pub tft_sharpe: f64,
    pub learning_rate: f64,
    pub exploration_rate: f64,
    pub last_updated: i64,
}

impl Default for StrategyPerformanceMatrix {
    fn default() -> Self {
        Self {
            dql_performance: StrategyMetrics::default(),
            pg_performance: StrategyMetrics::default(),
            tft_performance: StrategyMetrics::default(),
            strategy_weights: [1.0/3.0, 1.0/3.0, 1.0/3.0],
            performance_window: 100,
        }
    }
}

impl Default for StrategyMetrics {
    fn default() -> Self {
        Self {
            total_trades: 0,
            winning_trades: 0,
            total_return: 0.0,
            sharpe_ratio: 0.0,
            max_drawdown: 0.0,
            avg_execution_time: 1.0,
            confidence_accuracy: 0.5,
            recent_performance: Vec::new(),
        }
    }
}

impl Default for CausalFeatureExtractor {
    fn default() -> Self {
        Self {
            market_regime_features: Vec::new(),
            volatility_patterns: Vec::new(),
            volume_profile_features: Vec::new(),
            sentiment_correlation_matrix: [[0.0; 3]; 3],
            temporal_dependencies: Vec::new(),
        }
    }
}
