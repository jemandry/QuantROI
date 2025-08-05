use anchor_lang::prelude::*;
use sha3::{Digest, Sha3_256};
use switchboard_v2::{AggregatorAccountData, SwitchboardDecimal};

    pub fn initialize_founder_authority(
        ctx: Context<InitializeFounderAuthority>,
        company_name: String,
        delegation_guidelines: Option<DelegationGuidelines>,
    ) -> Result<()> {
        founder_authority::initialize_founder_authority(ctx, company_name, delegation_guidelines)
    }

    pub fn add_board_member(
        ctx: Context<AddBoardMember>,
        board_member: Pubkey,
    ) -> Result<()> {
        founder_authority::add_board_member(ctx, board_member)
    }

    pub fn set_cto(
        ctx: Context<SetCTO>,
        cto: Pubkey,
    ) -> Result<()> {
        founder_authority::set_cto(ctx, cto)
    }

    pub fn set_ceo(
        ctx: Context<SetCEO>,
        ceo: Pubkey,
    ) -> Result<()> {
        founder_authority::set_ceo(ctx, ceo)
    }

    pub fn update_delegation_guidelines(
        ctx: Context<UpdateDelegationGuidelines>,
        new_guidelines: DelegationGuidelines,
    ) -> Result<()> {
        founder_authority::update_delegation_guidelines(ctx, new_guidelines)
    }


pub mod master_strategy;

declare_id!("DeLegationManagementProgram11111111111111111");

pub mod founder_authority;
use founder_authority::*;

#[program]
pub mod delegation_management {
    use super::*;

    pub fn initialize_delegation(
        ctx: Context<InitializeDelegation>,
        ai_policy_pubkey: Pubkey,
        delegation_amount: u64,
        delegation_type: DelegationType,
        authority_level: AuthorityLevel,
    ) -> Result<()> {
        let delegation = &mut ctx.accounts.delegation;
        let clock = Clock::get()?;
        
        require!(
            validate_delegation_authority(&ctx.accounts.bank_authority.key(), &authority_level, &delegation_type)?,
            DelegationError::UnauthorizedAccess
        );
        
        let mut hasher = Sha3_256::new();
        hasher.update(ctx.accounts.bank_authority.key().as_ref());
        hasher.update(ai_policy_pubkey.as_ref());
        hasher.update(&delegation_amount.to_le_bytes());
        hasher.update(&clock.unix_timestamp.to_le_bytes());
        let hash = hasher.finalize();

        delegation.bank_authority = ctx.accounts.bank_authority.key();
        delegation.founder = ctx.accounts.founder.key();
        delegation.ai_policy_pubkey = ai_policy_pubkey;
        delegation.delegation_amount = delegation_amount;
        delegation.delegation_type = delegation_type.clone();
        delegation.authority_level = authority_level.clone();
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
                execute_ai_trade_internal(&market_conditions, &qos_requirements)?
            },
        };

        if optimal_strategy != strategy_manager.current_strategy {
            strategy_manager.current_strategy = optimal_strategy;

            emit!(StrategySwitch {
                delegation_id: delegation.key(),
                old_strategy: strategy_manager.current_strategy,
                new_strategy: optimal_strategy,
                market_regime: current_regime.clone(),
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

    pub fn process_weekly_reconsent(
        ctx: Context<ProcessWeeklyReconsent>,
        knowledge_test_score: u8,
        user_confirmation: bool,
    ) -> Result<()> {
        let delegation = &mut ctx.accounts.delegation;
        let clock = Clock::get()?;
        
        if delegation.knowledge_test_required {
            require!(
                knowledge_test_score >= delegation.reconsent_schedule.knowledge_test_threshold,
                DelegationError::InsufficientKnowledgeScore
            );
        }

        require!(user_confirmation, DelegationError::UserConsentRequired);
        
        delegation.last_reconsent = clock.unix_timestamp;
        delegation.reconsent_streak += 1;
        
        let frequency_seconds = match delegation.reconsent_schedule.frequency {
            ReconsentFrequency::Weekly => 604800,      // 7 days
            ReconsentFrequency::BiWeekly => 1209600,   // 14 days
            ReconsentFrequency::Monthly => 2592000,    // 30 days
            ReconsentFrequency::Quarterly => 7776000,  // 90 days
        };

        delegation.reconsent_schedule.next_required= clock.unix_timestamp + frequency_seconds;
        
        update_wealth_milestone_progress(delegation, clock.unix_timestamp)?;

        emit!(WeeklyReconsentProcessed {
            delegation_id: delegation.bank_authority,
            user: delegation.bank_authority,
            knowledge_score: knowledge_test_score,
            reconsent_streak: delegation.reconsent_streak,
            next_required: delegation.reconsent_schedule.next_required,
            timestamp: clock.unix_timestamp,
        });

        Ok(())
    }

    pub fn create_forever_contract(
        ctx: Context<CreateForeverContract>,
        delegation_amount: u64,
        weekly_confirmation_required: bool,
        knowledge_test_frequency: ReconsentFrequency,
    ) -> Result<()> {
        let delegation = &mut ctx.accounts.delegation;
        let clock = Clock::get()?;
        
        delegation.contract_type = ContractType::Forever;
        delegation.delegation_amount = delegation_amount;
        delegation.bank_authority = ctx.accounts.bank_authority.key();
        delegation.created_at = clock.unix_timestamp;
        delegation.is_active = true;

        delegation.memory_switches= DelegationMemoryState {
            auto_renewal_enabled: true,
            weekly_confirmation_required,
            risk_tolerance_memory: RiskToleranceHistory {
                entries: Vec::new(),
                last_updated: clock.unix_timestamp,
            },
            performance_memory: PerformanceHistory {
                monthly_returns: Vec::new(),
                sharpe_ratio_history: Vec::new(),
                max_drawdown_history: Vec::new(),
            },
            compliance_memory: ComplianceHistory {
                ria_compliance_status: true,
                sec_rule_10b5_checks: Vec::new(),
                recordkeeping_hours: 0.0,
                audit_trail_hashes: Vec::new(),
                last_compliance_review: clock.unix_timestamp,
            },
            user_preference_memory: UserPreferenceHistory {
                strategy_preferences: Vec::new(),
                risk_tolerance_changes: Vec::new(),
                notification_preferences: Vec::new(),
            },
        };

        delegation.reconsent_schedule = ReconsentSchedule {
            frequency: knowledge_test_frequency,
            next_required: clock.unix_timestamp + 604800, // First reconsent in 1 week
            grace_period_hours: 48,
            auto_pause_on_miss: true,
            knowledge_test_threshold: 80, // 80% minimum score
        };

        delegation.last_reconsent = clock.unix_timestamp;
        delegation.reconsent_streak = 0;
        delegation.knowledge_test_required = true;
        
        delegation.wealth_milestone_tracking = WealthMilestoneTracker {
            target_amount: 5_000_000_000_000, // $5M in lamports
            current_progress: 0,
            milestones: vec![
                WealthMilestone { amount: 100_000_000_000, achieved: false, date: None }, // $100K
                WealthMilestone { amount: 500_000_000_000, achieved: false, date: None }, // $500K
                WealthMilestone { amount: 1_000_000_000_000, achieved: false, date: None }, // $1M
                WealthMilestone { amount: 5_000_000_000_000, achieved: false, date: None }, // $5M
            ],
            auto_rewards_enabled: true,
        };
        
        emit!(ForeverContractCreated {
            delegation_id: delegation.key(),
            user: ctx.accounts.bank_authority.key(),
            amount: delegation_amount,
            weekly_confirmation: weekly_confirmation_required,
            timestamp: clock.unix_timestamp,
        });

        Ok(())
    }
}

pub fn update_wealth_milestone_progress(
    delegation: &mut DelegationAccount,
    timestamp: i64,
) -> Result<()> {
    if delegation.total_profit_loss > 0 {
        delegation.wealth_milestone_tracking.current_progress = delegation.total_profit_loss as u64;
        
        for milestone in &mut delegation.wealth_milestone_tracking.milestones {
            if !milestone.achieved && delegation.wealth_milestone_tracking.current_progress >= milestone.amount {
                milestone.achieved = true;
                milestone.date = Some(timestamp);
                
                emit!(WealthMilestoneAchieved {
                    delegation_id: delegation.bank_authority,
                    user: delegation.bank_authority,
                    milestone_amount: milestone.amount,
                    timestamp,
                });
            }
        }
    }
    
    Ok(())
}

pub fn set_portfolio_allocation(
    ctx: Context<SetPortfolioAllocation>,
    deep_q_learning_percent: u8,
    policy_gradient_percent: u8,
    temporal_fusion_percent: u8,
    cash_percent: u8,
    auto_trading_enabled: bool,
    rebalance_frequency: RebalanceFrequency,
) -> Result<()> {
    let delegation = &mut ctx.accounts.delegation;
    let strategy_manager = &mut ctx.accounts.strategy_manager;
    let clock = Clock::get()?;
    
    let total_percent = deep_q_learning_percent + policy_gradient_percent + temporal_fusion_percent + cash_percent;
    require!(total_percent == 100, DelegationError::InvalidAllocationPercentages);
    
    let snapshot = AllocationSnapshot {
        timestamp: clock.unix_timestamp,
        deep_q_learning_percent,
        policy_gradient_percent,
        temporal_fusion_percent,
        cash_percent,
        market_regime: MarketRegime::Sideways,
        performance_trigger: false,
    };
    
    strategy_manager.portfolio_allocation = PortfolioAllocation {
        deep_q_learning_percent,
        policy_gradient_percent,
        temporal_fusion_percent,
        cash_percent,
        auto_trading_enabled,
        rebalance_frequency,
        last_rebalance: clock.unix_timestamp,
        allocation_history: vec![snapshot],
    };
    
    let mut hasher = Sha3_256::new();
    hasher.update(&delegation.key().to_bytes());
    hasher.update(&[deep_q_learning_percent, policy_gradient_percent, temporal_fusion_percent, cash_percent]);
    hasher.update(&clock.unix_timestamp.to_le_bytes());
    let allocation_hash = hasher.finalize();
    
    emit!(PortfolioAllocationUpdated {
        delegation_id: delegation.key(),
        user: delegation.bank_authority,
        deep_q_learning_percent,
        policy_gradient_percent,
        temporal_fusion_percent,
        cash_percent,
        auto_trading_enabled,
        allocation_hash: allocation_hash.to_vec(),
        timestamp: clock.unix_timestamp,
    });
    
    Ok(())
}

pub fn get_portfolio_allocation(ctx: Context<GetPortfolioAllocation>) -> Result<PortfolioAllocation> {
    let strategy_manager = &ctx.accounts.strategy_manager;
    Ok(strategy_manager.portfolio_allocation.clone())
}

pub fn rebalance_portfolio(
    ctx: Context<RebalancePortfolio>,
    market_conditions: MarketConditions,
) -> Result<()> {
    let delegation = &mut ctx.accounts.delegation;
    let strategy_manager = &mut ctx.accounts.strategy_manager;
    let clock = Clock::get()?;
    
    let current_regime = detect_market_regime(&market_conditions, &strategy_manager.market_regime_detector)?;
    
    let performance_score = strategy_manager.performance_tracker.performance_score;
    let allocation = &mut strategy_manager.portfolio_allocation;
    
    let should_rebalance = match allocation.rebalance_frequency {
        RebalanceFrequency::Daily => clock.unix_timestamp - allocation.last_rebalance >= 86400,
        RebalanceFrequency::Weekly => clock.unix_timestamp - allocation.last_rebalance >= 604800,
        RebalanceFrequency::Monthly => clock.unix_timestamp - allocation.last_rebalance >= 2592000,
        RebalanceFrequency::OnPerformance => performance_score < 0.5,
        RebalanceFrequency::Manual => false,
    };
    
    if should_rebalance {
        let snapshot = AllocationSnapshot {
            timestamp: clock.unix_timestamp,
            deep_q_learning_percent: allocation.deep_q_learning_percent,
            policy_gradient_percent: allocation.policy_gradient_percent,
            temporal_fusion_percent: allocation.temporal_fusion_percent,
            cash_percent: allocation.cash_percent,
            market_regime: current_regime,
            performance_trigger: matches!(allocation.rebalance_frequency, RebalanceFrequency::OnPerformance),
        };
        
        allocation.allocation_history.push(snapshot);
        allocation.last_rebalance = clock.unix_timestamp;
        
        emit!(PortfolioRebalanced {
            delegation_id: delegation.key(),
            user: delegation.bank_authority,
            market_regime: current_regime,
            timestamp: clock.unix_timestamp,
        });
    }
    
    Ok(())
}

#[account]
pub struct DelegationAccount {
    pub bank_authority: Pubkey,           // 32 bytes
    pub founder: Pubkey,                  // 32 bytes
    pub ai_policy_pubkey: Pubkey,         // 32 bytes
    pub delegation_amount: u64,           // 8 bytes
    pub delegation_type: DelegationType,  // 1 byte
    pub authority_level: AuthorityLevel,  // 1 byte
    pub created_at: i64,                  // 8 bytes
    pub is_active: bool,                  // 1 byte
    pub performance_score: u32,           // 4 bytes
    pub total_trades: u64,                // 8 bytes
    pub total_profit_loss: i64,           // 8 bytes
    pub cryptographic_hash: Vec<u8>,      // 32 bytes (SHA-3)
    
    pub memory_switches: DelegationMemoryState,
    pub contract_type: ContractType,
    pub reconsent_schedule: ReconsentSchedule,
    pub last_reconsent: i64,
    pub reconsent_streak: u32,
    pub knowledge_test_required: bool,
    pub wealth_milestone_tracking: WealthMilestoneTracker,
    pub duty_records: Vec<DutyRecord>,
    pub contract_terms: Option<ContractTerms>,
    pub audit_configuration: Option<AuditConfiguration>,
    pub voting_configuration: Option<VotingConfiguration>,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, PartialEq, Eq)]
pub enum DelegationType {
    Partial,
    Full,
    CeoToAssistant,
    BoardToCto,
    FounderToBoard,
    ProjectManagement,
    AiAuditor,
    EmployeeVoting,
    ShareholderVoting,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, PartialEq, Eq)]
pub enum AuthorityLevel {
    Founder,
    BoardMember,
    CTO,
    CEO,
    Assistant,
    Employee,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq)]
pub enum TradeDirection {
    Buy,
    Sell,
}

#[derive(Accounts)]
pub struct SetPortfolioAllocation<'info> {
    #[account(
        mut,
        seeds = [b"delegation", delegation.bank_authority.as_ref()],
        bump,
        constraint = delegation.bank_authority == bank_authority.key() @ DelegationError::UnauthorizedAccess
    )]
    pub delegation: Account<'info, DelegationAccount>,
    #[account(
        mut,
        seeds = [b"strategy_manager", delegation.key().as_ref()],
        bump
    )]
    pub strategy_manager: Account<'info, AdaptiveStrategyManager>,
    pub bank_authority: Signer<'info>,
}

#[derive(Accounts)]
pub struct GetPortfolioAllocation<'info> {
    #[account(
        seeds = [b"strategy_manager", delegation.key().as_ref()],
        bump
    )]
    pub strategy_manager: Account<'info, AdaptiveStrategyManager>,
    #[account(
        seeds = [b"delegation", delegation.bank_authority.as_ref()],
        bump
    )]
    pub delegation: Account<'info, DelegationAccount>,
}

#[derive(Accounts)]
pub struct RebalancePortfolio<'info> {
    #[account(
        mut,
        seeds = [b"delegation", delegation.bank_authority.as_ref()],
        bump,
        constraint = delegation.bank_authority == bank_authority.key() @ DelegationError::UnauthorizedAccess
    )]
    pub delegation: Account<'info, DelegationAccount>,
    #[account(
        mut,
        seeds = [b"strategy_manager", delegation.key().as_ref()],
        bump
    )]
    pub strategy_manager: Account<'info, AdaptiveStrategyManager>,
    pub bank_authority: Signer<'info>,
}

#[derive(Accounts)]
pub struct InitializeDelegation<'info> {
    #[account(
        init,
        payer = bank_authority,
        space = 8 + 32 + 32 + 32 + 8 + 1 + 1 + 8 + 1 + 4 + 8 + 8 + 64 + 6000, // Account discriminator + data
        seeds = [b"delegation", bank_authority.key().as_ref()],
        bump
    )]
    pub delegation: Account<'info, DelegationAccount>,
    #[account(mut)]
    pub bank_authority: Signer<'info>,
    pub founder: AccountInfo<'info>,
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

#[derive(Accounts)]
pub struct ProcessWeeklyReconsent<'info> {
    #[account(
        mut,
        seeds = [b"delegation", delegation.bank_authority.as_ref()],
        bump,
        constraint = delegation.is_active @ DelegationError::DelegationInactive
    )]
    pub delegation: Account<'info, DelegationAccount>,
    pub bank_authority: Signer<'info>,
}

#[derive(Accounts)]
pub struct CreateForeverContract<'info> {
    #[account(
        init,
        payer = bank_authority,
        space = 8 + 32 + 32 + 8 + 1 + 8 + 1 + 4 + 8 + 8 + 4 + 2000, // Base + memory system space
        seeds = [b"delegation", bank_authority.key().as_ref()],
        bump
    )]
    pub delegation: Account<'info, DelegationAccount>,
    #[account(mut)]
    pub bank_authority: Signer<'info>,
    pub system_program: Program<'info, System>,
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

#[event]
pub struct WeeklyReconsentProcessed {
    pub delegation_id: Pubkey,
    pub user: Pubkey,
    pub knowledge_score: u8,
    pub reconsent_streak: u32,
    pub next_required: i64,
    pub timestamp: i64,
}

#[event]
pub struct ForeverContractCreated {
    pub delegation_id: Pubkey,
    pub user: Pubkey,
    pub amount: u64,
    pub weekly_confirmation: bool,
    pub timestamp: i64,
}

#[event]
pub struct WealthMilestoneAchieved {
    pub delegation_id: Pubkey,
    pub user: Pubkey,
    pub milestone_amount: u64,
    pub timestamp: i64,
}

#[event]
pub struct PortfolioAllocationUpdated {
    pub delegation_id: Pubkey,
    pub user: Pubkey,
    pub deep_q_learning_percent: u8,
    pub policy_gradient_percent: u8,
    pub temporal_fusion_percent: u8,
    pub cash_percent: u8,
    pub auto_trading_enabled: bool,
    pub allocation_hash: Vec<u8>,
    pub timestamp: i64,
}

#[event]
pub struct PortfolioRebalanced {
    pub delegation_id: Pubkey,
    pub user: Pubkey,
    pub market_regime: MarketRegime,
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
    pub portfolio_allocation: PortfolioAllocation,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq)]
pub enum RLStrategyType {
    GatedDeepQLearning,
    GatedPolicyGradient,
    TemporalFusionTransformer,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq)]
pub enum ContractType {
    Standard,      // 3, 6, 12, 24 month terms
    Forever,       // Perpetual with weekly confirmation
    Milestone,     // Tied to wealth milestones
    Performance,   // Performance-based duration
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq)]
pub enum ReconsentFrequency {
    Weekly,
    BiWeekly,
    Monthly,
    Quarterly,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct ReconsentSchedule {
    pub frequency: ReconsentFrequency,
    pub next_required: i64,
    pub grace_period_hours: u32,
    pub auto_pause_on_miss: bool,
    pub knowledge_test_threshold: u8,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct WealthMilestone {
    pub amount: u64,
    pub achieved: bool,
    pub date: Option<i64>,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct WealthMilestoneTracker {
    pub target_amount: u64,
    pub current_progress: u64,
    pub milestones: Vec<WealthMilestone>,
    pub auto_rewards_enabled: bool,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct RiskToleranceHistory {
    pub entries: Vec<(i64, u8)>, // (timestamp, risk_score)
    pub last_updated: i64,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct PerformanceHistory {
    pub monthly_returns: Vec<(i64, f64)>, // (timestamp, return_percentage)
    pub sharpe_ratio_history: Vec<(i64, f64)>,
    pub max_drawdown_history: Vec<(i64, f64)>,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct ComplianceHistory {
    pub ria_compliance_status: bool,
    pub sec_rule_10b5_checks: Vec<(i64, bool)>, // (timestamp, passed)
    pub recordkeeping_hours: f64,
    pub audit_trail_hashes: Vec<[u8; 32]>,
    pub last_compliance_review: i64,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct UserPreferenceHistory {
    pub strategy_preferences: Vec<(i64, RLStrategyType)>,
    pub risk_tolerance_changes: Vec<(i64, u8)>,
    pub notification_preferences: Vec<(i64, bool)>,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct DelegationMemoryState {
    pub auto_renewal_enabled: bool,
    pub weekly_confirmation_required: bool,
    pub risk_tolerance_memory: RiskToleranceHistory,
    pub performance_memory: PerformanceHistory,
    pub compliance_memory: ComplianceHistory,
    pub user_preference_memory: UserPreferenceHistory,
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
pub struct PortfolioAllocation {
    pub deep_q_learning_percent: u8,
    pub policy_gradient_percent: u8,
    pub temporal_fusion_percent: u8,
    pub cash_percent: u8,
    pub auto_trading_enabled: bool,
    pub rebalance_frequency: RebalanceFrequency,
    pub last_rebalance: i64,
    pub allocation_history: Vec<AllocationSnapshot>,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct AllocationSnapshot {
    pub timestamp: i64,
    pub deep_q_learning_percent: u8,
    pub policy_gradient_percent: u8,
    pub temporal_fusion_percent: u8,
    pub cash_percent: u8,
    pub market_regime: MarketRegime,
    pub performance_trigger: bool,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub enum RebalanceFrequency {
    Daily,
    Weekly,
    Monthly,
    OnPerformance,
    Manual,
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

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy)]
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
    #[msg("Knowledge test score below required threshold")]
    InsufficientKnowledgeScore,
    #[msg("User consent required for reconsenting")]
    UserConsentRequired,
    #[msg("Knowledge test submission is too old")]
    StaleKnowledgeTest,
    #[msg("Exceeded recordkeeping time limit")]
    ExceededRecordkeepingLimit,
    #[msg("Portfolio allocation percentages must sum to 100")]
    InvalidAllocationPercentages,
    #[msg("Duty not found")]
    DutyNotFound,
    #[msg("Invalid duty status")]
    InvalidDutyStatus,
    #[msg("Audit not configured")]
    AuditNotConfigured,
    #[msg("Voting not configured")]
    VotingNotConfigured,
    #[msg("Invalid voting weights")]
    InvalidVotingWeights,
    #[msg("Oracle verification failed")]
    OracleVerificationFailed,
    #[msg("Insufficient audit score")]
    InsufficientAuditScore,
    #[msg("Unauthorized delegation")]
    UnauthorizedDelegation,
    #[msg("Invalid authority level")]
    InvalidAuthorityLevel,
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

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct DutyRecord {
    pub duty_id: u64,
    pub description: String,
    pub assigned_to: Pubkey,
    pub assigned_by: Pubkey,
    pub created_at: i64,
    pub due_date: i64,
    pub status: DutyStatus,
    pub completion_proof: Option<Vec<u8>>,
    pub verification_required: bool,
    pub payment_amount: u64,
    pub payment_triggered: bool,
    pub cryptographic_hash: Vec<u8>,
    pub completeness_score: Option<u8>,
    pub sincerity_score: Option<u8>,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct ContractTerms {
    pub terms_hash: [u8; 32],
    pub payment_on_delivery: bool,
    pub verification_requirements: Vec<String>,
    pub milestone_payments: Vec<MilestonePayment>,
    pub auto_audit_enabled: bool,
    pub audit_frequency: AuditFrequency,
    pub oracle_verification_required: bool,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct MilestonePayment {
    pub milestone_id: u64,
    pub description: String,
    pub amount: u64,
    pub completion_criteria: String,
    pub verification_required: bool,
    pub oracle_verification: bool,
    pub completed: bool,
    pub payment_executed: bool,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct AuditConfiguration {
    pub audit_type: AuditType,
    pub frequency: AuditFrequency,
    pub variance_threshold: Option<f64>,
    pub vrf_seed: Option<u64>,
    pub last_audit: i64,
    pub next_audit_due: i64,
    pub audit_history: Vec<AuditRecord>,
    pub oracle_feed: Option<Pubkey>,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct VotingConfiguration {
    pub voting_type: VotingType,
    pub employee_weight_percent: u8,
    pub shareholder_weight_percent: u8,
    pub ai_classification_enabled: bool,
    pub major_issue_threshold: f64,
    pub public_voting: bool,
    pub zkp_privacy: bool,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq)]
pub enum DutyStatus {
    Assigned,
    InProgress,
    Completed,
    Verified,
    PaymentTriggered,
    AiAudited,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq)]
pub enum AuditType {
    Random,
    VarianceBased,
    Scheduled,
    OnDemand,
    AiDriven,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq)]
pub enum AuditFrequency {
    Random,
    VarianceBased,
    Weekly,
    Monthly,
    OnCompletion,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq)]
pub enum VotingType {
    EmployeeVoting,
    ShareholderVoting,
    CombinedVoting,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct AuditRecord {
    pub audit_id: u64,
    pub auditor: Pubkey,
    pub audit_type: AuditType,
    pub findings: Vec<String>,
    pub compliance_score: u8,
    pub completeness_assessment: Option<u8>,
    pub sincerity_assessment: Option<u8>,
    pub timestamp: i64,
    pub cryptographic_hash: Vec<u8>,
    pub vrf_proof: Option<Vec<u8>>,
}

pub fn assign_duty(
    ctx: Context<AssignDuty>,
    duty_id: u64,
    description: String,
    assigned_to: Pubkey,
    due_date: i64,
    payment_amount: u64,
    verification_required: bool,
    ai_auditor_assessment: bool,
) -> Result<()> {
    let delegation = &mut ctx.accounts.delegation;
    let clock = Clock::get()?;
    
    let mut hasher = Sha3_256::new();
    hasher.update(&duty_id.to_le_bytes());
    hasher.update(description.as_bytes());
    hasher.update(assigned_to.as_ref());
    hasher.update(ctx.accounts.assigner.key().as_ref());
    hasher.update(&due_date.to_le_bytes());
    hasher.update(&payment_amount.to_le_bytes());
    hasher.update(&clock.unix_timestamp.to_le_bytes());
    let duty_hash = hasher.finalize();

    let duty_record = DutyRecord {
        duty_id,
        description: description.clone(),
        assigned_to,
        assigned_by: ctx.accounts.assigner.key(),
        created_at: clock.unix_timestamp,
        due_date,
        status: DutyStatus::Assigned,
        completion_proof: None,
        verification_required,
        payment_amount,
        payment_triggered: false,
        cryptographic_hash: duty_hash.to_vec(),
        completeness_score: None,
        sincerity_score: None,
    };

    delegation.duty_records.push(duty_record);

    emit!(DutyAssigned {
        delegation_id: delegation.key(),
        duty_id,
        assigned_to,
        assigned_by: ctx.accounts.assigner.key(),
        description,
        payment_amount,
        due_date,
        duty_hash: duty_hash.to_vec(),
        ai_auditor_assessment,
        timestamp: clock.unix_timestamp,
    });

    Ok(())
}

pub fn complete_duty(
    ctx: Context<CompleteDuty>,
    duty_id: u64,
    completion_proof: Vec<u8>,
) -> Result<()> {
    let delegation = &mut ctx.accounts.delegation;
    let clock = Clock::get()?;
    
    let delegation_key = delegation.key();
    let assignee_key = ctx.accounts.assignee.key();
    
    let duty_record = delegation.duty_records.iter_mut()
        .find(|duty| duty.duty_id == duty_id)
        .ok_or(DelegationError::DutyNotFound)?;

    require!(duty_record.assigned_to == assignee_key, DelegationError::UnauthorizedAccess);
    require!(duty_record.status == DutyStatus::Assigned || duty_record.status == DutyStatus::InProgress, DelegationError::InvalidDutyStatus);

    let verification_required = duty_record.verification_required;
    duty_record.status = DutyStatus::Completed;
    duty_record.completion_proof = Some(completion_proof.clone());

    if !verification_required {
        duty_record.status = DutyStatus::Verified;
        duty_record.payment_triggered = true;
    }
    
    emit!(DutyCompleted {
        delegation_id: delegation_key,
        duty_id,
        assignee: assignee_key,
        completion_proof: completion_proof,
        verification_required,
        timestamp: clock.unix_timestamp,
    });

    Ok(())
}

pub fn ai_audit_duty(
    ctx: Context<AiAuditDuty>,
    duty_id: u64,
    completeness_score: u8,
    sincerity_score: u8,
    audit_findings: Vec<String>,
) -> Result<()> {
    let delegation = &mut ctx.accounts.delegation;
    let clock = Clock::get()?;
    
    let duty_record = delegation.duty_records.iter_mut()
        .find(|duty| duty.duty_id == duty_id)
        .ok_or(DelegationError::DutyNotFound)?;

    require!(duty_record.status == DutyStatus::Completed, DelegationError::InvalidDutyStatus);

    duty_record.completeness_score = Some(completeness_score);
    duty_record.sincerity_score = Some(sincerity_score);
    duty_record.status = DutyStatus::AiAudited;

    let audit_record = AuditRecord {
        audit_id: clock.unix_timestamp as u64,
        auditor: ctx.accounts.ai_auditor.key(),
        audit_type: AuditType::AiDriven,
        findings: audit_findings.clone(),
        compliance_score: (completeness_score + sincerity_score) / 2,
        completeness_assessment: Some(completeness_score),
        sincerity_assessment: Some(sincerity_score),
        timestamp: clock.unix_timestamp,
        cryptographic_hash: {
            let mut hasher = Sha3_256::new();
            hasher.update(&duty_id.to_le_bytes());
            hasher.update(&completeness_score.to_le_bytes());
            hasher.update(&sincerity_score.to_le_bytes());
            hasher.update(&clock.unix_timestamp.to_le_bytes());
            hasher.finalize().to_vec()
        },
        vrf_proof: None,
    };

    if let Some(ref mut audit_config) = delegation.audit_configuration {
        audit_config.audit_history.push(audit_record);
    }

    emit!(AiAuditCompleted {
        delegation_id: delegation.key(),
        duty_id,
        ai_auditor: ctx.accounts.ai_auditor.key(),
        completeness_score,
        sincerity_score,
        findings: audit_findings,
        timestamp: clock.unix_timestamp,
    });

    Ok(())
}

pub fn configure_vrf_audit(
    ctx: Context<ConfigureVrfAudit>,
    audit_type: AuditType,
    frequency: AuditFrequency,
    variance_threshold: Option<f64>,
    oracle_feed: Option<Pubkey>,
) -> Result<()> {
    let delegation = &mut ctx.accounts.delegation;
    let clock = Clock::get()?;

    let vrf_seed = generate_vrf_random_seed(&delegation.key(), clock.unix_timestamp)?;

    let audit_config = AuditConfiguration {
        audit_type,
        frequency,
        variance_threshold,
        vrf_seed: Some(vrf_seed),
        last_audit: 0,
        next_audit_due: clock.unix_timestamp + get_audit_interval(frequency),
        audit_history: Vec::new(),
        oracle_feed,
    };

    delegation.audit_configuration = Some(audit_config);

    emit!(VrfAuditConfigured {
        delegation_id: delegation.key(),
        audit_type,
        frequency,
        vrf_seed,
        oracle_feed,
        next_audit_due: delegation.audit_configuration.as_ref().unwrap().next_audit_due,
        timestamp: clock.unix_timestamp,
    });

    Ok(())
}

pub fn execute_random_audit(
    ctx: Context<ExecuteRandomAudit>,
    audit_findings: Vec<String>,
    compliance_score: u8,
) -> Result<()> {
    let delegation = &mut ctx.accounts.delegation;
    let clock = Clock::get()?;

    let delegation_key = delegation.key();
    let auditor_key = ctx.accounts.auditor.key();
    
    let audit_config = delegation.audit_configuration.as_mut()
        .ok_or(DelegationError::AuditNotConfigured)?;

    let vrf_proof = {
        let mut hasher = Sha3_256::new();
        hasher.update(&audit_config.vrf_seed.unwrap_or(0).to_le_bytes());
        hasher.update(&clock.unix_timestamp.to_le_bytes());
        hasher.update(auditor_key.as_ref());
        hasher.finalize().to_vec()
    };

    let audit_record = AuditRecord {
        audit_id: clock.unix_timestamp as u64,
        auditor: auditor_key,
        audit_type: audit_config.audit_type,
        findings: audit_findings.clone(),
        compliance_score,
        completeness_assessment: None,
        sincerity_assessment: None,
        timestamp: clock.unix_timestamp,
        cryptographic_hash: {
            let mut hasher = Sha3_256::new();
            hasher.update(&clock.unix_timestamp.to_le_bytes());
            hasher.update(auditor_key.as_ref());
            hasher.update(&compliance_score.to_le_bytes());
            for finding in &audit_findings {
                hasher.update(finding.as_bytes());
            }
            hasher.finalize().to_vec()
        },
        vrf_proof: Some(vrf_proof.clone()),
    };

    audit_config.audit_history.push(audit_record);
    audit_config.last_audit = clock.unix_timestamp;
    let next_audit_due = clock.unix_timestamp + get_audit_interval(audit_config.frequency);
    audit_config.next_audit_due = next_audit_due;
    
    emit!(RandomAuditExecuted {
        delegation_id: delegation_key,
        audit_id: clock.unix_timestamp as u64,
        auditor: auditor_key,
        compliance_score,
        findings_count: audit_findings.len() as u32,
        vrf_proof,
        next_audit_due,
        timestamp: clock.unix_timestamp,
    });

    Ok(())
}

pub fn configure_voting_system(
    ctx: Context<ConfigureVoting>,
    voting_type: VotingType,
    employee_weight_percent: u8,
    shareholder_weight_percent: u8,
    ai_classification_enabled: bool,
    major_issue_threshold: f64,
    public_voting: bool,
) -> Result<()> {
    let delegation = &mut ctx.accounts.delegation;
    let clock = Clock::get()?;

    require!(employee_weight_percent + shareholder_weight_percent <= 100, DelegationError::InvalidVotingWeights);

    let voting_config = VotingConfiguration {
        voting_type,
        employee_weight_percent,
        shareholder_weight_percent,
        ai_classification_enabled,
        major_issue_threshold,
        public_voting,
        zkp_privacy: !public_voting,
    };

    delegation.voting_configuration = Some(voting_config);

    emit!(VotingSystemConfigured {
        delegation_id: delegation.key(),
        voting_type,
        employee_weight_percent,
        shareholder_weight_percent,
        ai_classification_enabled,
        public_voting,
        timestamp: clock.unix_timestamp,
    });

    Ok(())
}

pub fn submit_vote(
    ctx: Context<SubmitVote>,
    issue_id: u64,
    vote: bool,
    voter_type: VotingType,
    ai_issue_classification: Option<f64>,
) -> Result<()> {
    let delegation = &mut ctx.accounts.delegation;
    let clock = Clock::get()?;

    let voting_config = delegation.voting_configuration.as_ref()
        .ok_or(DelegationError::VotingNotConfigured)?;

    let is_major_issue = if voting_config.ai_classification_enabled {
        ai_issue_classification.unwrap_or(0.0) > voting_config.major_issue_threshold
    } else {
        true
    };

    let vote_weight = match voter_type {
        VotingType::EmployeeVoting => voting_config.employee_weight_percent,
        VotingType::ShareholderVoting => voting_config.shareholder_weight_percent,
        VotingType::CombinedVoting => 100,
    };

    emit!(VoteSubmitted {
        delegation_id: delegation.key(),
        issue_id,
        voter: ctx.accounts.voter.key(),
        vote,
        voter_type,
        vote_weight,
        is_major_issue,
        ai_classification_score: ai_issue_classification,
        public_vote: voting_config.public_voting,
        timestamp: clock.unix_timestamp,
    });

    Ok(())
}

pub fn verify_delivery_with_oracle(
    ctx: Context<VerifyDeliveryWithOracle>,
    duty_id: u64,
    verification_criteria: String,
) -> Result<()> {
    let delegation = &mut ctx.accounts.delegation;
    let clock = Clock::get()?;

    let delegation_key = delegation.key();
    
    let oracle_verification_result = if let Some(oracle_feed) = &ctx.accounts.oracle_feed {
        verify_with_oracle(oracle_feed, &verification_criteria)?
    } else {
        true
    };
    
    let duty_record = delegation.duty_records.iter_mut()
        .find(|duty| duty.duty_id == duty_id)
        .ok_or(DelegationError::DutyNotFound)?;

    require!(duty_record.status == DutyStatus::Completed, DelegationError::InvalidDutyStatus);

    let payment_triggered = if oracle_verification_result {
        duty_record.status = DutyStatus::Verified;
        duty_record.payment_triggered = true;
        true
    } else {
        false
    };
    
    emit!(OracleVerificationCompleted {
        delegation_id: delegation_key,
        duty_id,
        oracle_feed: ctx.accounts.oracle_feed.as_ref().map(|acc| acc.key()),
        verification_result: oracle_verification_result,
        payment_triggered,
        timestamp: clock.unix_timestamp,
    });

    Ok(())
}

pub fn setup_contract_terms_with_oracle(
    ctx: Context<SetupContractTermsWithOracle>,
    terms_hash: [u8; 32],
    payment_on_delivery: bool,
    verification_requirements: Vec<String>,
    milestone_payments: Vec<MilestonePayment>,
    audit_frequency: AuditFrequency,
    oracle_verification_required: bool,
) -> Result<()> {
    let delegation = &mut ctx.accounts.delegation;
    let clock = Clock::get()?;

    let milestone_count = milestone_payments.len() as u32;
    
    let contract_terms = ContractTerms {
        terms_hash,
        payment_on_delivery,
        verification_requirements,
        milestone_payments,
        auto_audit_enabled: true,
        audit_frequency,
        oracle_verification_required,
    };

    delegation.contract_terms = Some(contract_terms);
    let delegation_key = delegation.key();
    
    emit!(ContractTermsWithOracleSetup {
        delegation_id: delegation_key,
        terms_hash,
        payment_on_delivery,
        oracle_verification_required,
        audit_frequency,
        milestone_count,
        timestamp: clock.unix_timestamp,
    });

    Ok(())
}

pub fn submit_zkp_vote(
    ctx: Context<SubmitZKPVote>,
    issue_id: u64,
    vote_commitment: [u8; 32],
    stake_proof: [u8; 32],
    eligibility_proof: [u8; 32],
    zkp_proof: Vec<u8>,
    voter_type: VotingType,
) -> Result<()> {
    let delegation = &mut ctx.accounts.delegation;
    let clock = Clock::get()?;

    let voting_config = delegation.voting_configuration.as_ref()
        .ok_or(DelegationError::VotingNotConfigured)?;

    let proof_hash = {
        let mut hasher = Sha3_256::new();
        hasher.update(&vote_commitment);
        hasher.update(&stake_proof);
        hasher.update(&eligibility_proof);
        hasher.update(&zkp_proof);
        hasher.finalize()
    };

    emit!(ZKPVoteSubmitted {
        delegation_id: delegation.key(),
        issue_id,
        voter: ctx.accounts.voter.key(),
        vote_commitment,
        stake_proof,
        eligibility_proof,
        voter_type,
        proof_hash: proof_hash.to_vec(),
        public_vote: voting_config.public_voting,
        timestamp: clock.unix_timestamp,
    });

    Ok(())
}

fn verify_with_oracle(
    oracle_account: &AccountInfo,
    verification_criteria: &str,
) -> Result<bool> {
    if oracle_account.data_is_empty() {
        return Ok(true);
    }
    
    match AggregatorAccountData::new(oracle_account) {
        Ok(feed) => {
            let val: f64 = feed.get_result()?.try_into()?;
            
            let threshold: f64 = verification_criteria
                .parse()
                .unwrap_or(0.5);
            
            Ok(val >= threshold)
        }
        Err(_) => Ok(true)
    }
}

fn validate_delegation_authority(
    authority: &Pubkey,
    authority_level: &AuthorityLevel,
    delegation_type: &DelegationType,
) -> Result<bool> {
    match (authority_level, delegation_type) {
        (AuthorityLevel::Founder, _) => Ok(true),
        (AuthorityLevel::BoardMember, DelegationType::BoardToCTO) => Ok(true),
        (AuthorityLevel::BoardMember, DelegationType::AITrading) => Ok(true),
        (AuthorityLevel::BoardMember, DelegationType::RiskManagement) => Ok(true),
        (AuthorityLevel::CEO, DelegationType::CEOToAssistant) => Ok(true),
        (AuthorityLevel::CEO, DelegationType::PortfolioRebalancing) => Ok(true),
        (AuthorityLevel::CTO, DelegationType::ComplianceMonitoring) => Ok(true),
        (AuthorityLevel::CTO, DelegationType::AITrading) => Ok(true),
        _ => Ok(false),
    }
}

fn generate_vrf_random_seed(
    delegation_id: &Pubkey,
    timestamp: i64,
) -> Result<u64> {
    let mut hasher = Sha3_256::new();
    hasher.update(delegation_id.as_ref());
    hasher.update(&timestamp.to_le_bytes());
    let hash = hasher.finalize();
    
    let seed_bytes: [u8; 8] = hash[0..8].try_into().unwrap();
    Ok(u64::from_le_bytes(seed_bytes))
}

fn get_audit_interval(frequency: AuditFrequency) -> i64 {
    match frequency {
        AuditFrequency::Random => {
            let base_interval = 86400;
            let random_factor = Clock::get().unwrap().unix_timestamp % 604800;
            base_interval + random_factor
        },
        AuditFrequency::VarianceBased => 259200,
        AuditFrequency::Weekly => 604800,
        AuditFrequency::Monthly => 2592000,
        AuditFrequency::OnCompletion => 0,
    }
}

fn calculate_audit_variance(
    delegation: &DelegationAccount,
    threshold: f64,
) -> Result<bool> {
    if let Some(audit_config) = &delegation.audit_configuration {
        if audit_config.audit_history.len() < 2 {
            return Ok(false);
        }

        let recent_scores: Vec<f64> = audit_config.audit_history
            .iter()
            .rev()
            .take(5)
            .map(|audit| audit.compliance_score as f64)
            .collect();

        let mean = recent_scores.iter().sum::<f64>() / recent_scores.len() as f64;
        let variance = recent_scores.iter()
            .map(|score| (score - mean).powi(2))
            .sum::<f64>() / recent_scores.len() as f64;

        Ok(variance > threshold)
    } else {
        Ok(false)
    }
}

fn execute_ai_trade_internal(
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

#[derive(Accounts)]
#[instruction(duty_id: u64)]
pub struct AssignDuty<'info> {
    #[account(
        mut,
        seeds = [b"delegation", delegation.bank_authority.as_ref()],
        bump,
        constraint = delegation.is_active @ DelegationError::DelegationInactive
    )]
    pub delegation: Account<'info, DelegationAccount>,
    pub assigner: Signer<'info>,
}

#[derive(Accounts)]
#[instruction(duty_id: u64)]
pub struct CompleteDuty<'info> {
    #[account(
        mut,
        seeds = [b"delegation", delegation.bank_authority.as_ref()],
        bump,
        constraint = delegation.is_active @ DelegationError::DelegationInactive
    )]
    pub delegation: Account<'info, DelegationAccount>,
    pub assignee: Signer<'info>,
}

#[derive(Accounts)]
#[instruction(duty_id: u64)]
pub struct AiAuditDuty<'info> {
    #[account(
        mut,
        seeds = [b"delegation", delegation.bank_authority.as_ref()],
        bump,
        constraint = delegation.is_active @ DelegationError::DelegationInactive
    )]
    pub delegation: Account<'info, DelegationAccount>,
    pub ai_auditor: Signer<'info>,
}

#[derive(Accounts)]
pub struct ConfigureVrfAudit<'info> {
    #[account(
        mut,
        seeds = [b"delegation", delegation.bank_authority.as_ref()],
        bump,
        constraint = delegation.bank_authority == authority.key() @ DelegationError::UnauthorizedAccess
    )]
    pub delegation: Account<'info, DelegationAccount>,
    pub authority: Signer<'info>,
}

#[derive(Accounts)]
pub struct ExecuteRandomAudit<'info> {
    #[account(
        mut,
        seeds = [b"delegation", delegation.bank_authority.as_ref()],
        bump,
        constraint = delegation.is_active @ DelegationError::DelegationInactive
    )]
    pub delegation: Account<'info, DelegationAccount>,
    pub auditor: Signer<'info>,
}

#[derive(Accounts)]
pub struct ConfigureVoting<'info> {
    #[account(
        mut,
        seeds = [b"delegation", delegation.bank_authority.as_ref()],
        bump,
        constraint = delegation.bank_authority == authority.key() @ DelegationError::UnauthorizedAccess
    )]
    pub delegation: Account<'info, DelegationAccount>,
    pub authority: Signer<'info>,
}

#[derive(Accounts)]
#[instruction(issue_id: u64)]
pub struct SubmitVote<'info> {
    #[account(
        mut,
        seeds = [b"delegation", delegation.bank_authority.as_ref()],
        bump,
        constraint = delegation.is_active @ DelegationError::DelegationInactive
    )]
    pub delegation: Account<'info, DelegationAccount>,
    pub voter: Signer<'info>,
}

#[derive(Accounts)]
#[instruction(issue_id: u64)]
pub struct SubmitZKPVote<'info> {
    #[account(
        mut,
        seeds = [b"delegation", delegation.bank_authority.as_ref()],
        bump,
        constraint = delegation.is_active @ DelegationError::DelegationInactive
    )]
    pub delegation: Account<'info, DelegationAccount>,
    pub voter: Signer<'info>,
}

#[derive(Accounts)]
#[instruction(duty_id: u64)]
pub struct VerifyDeliveryWithOracle<'info> {
    #[account(
        mut,
        seeds = [b"delegation", delegation.bank_authority.as_ref()],
        bump,
        constraint = delegation.is_active @ DelegationError::DelegationInactive
    )]
    pub delegation: Account<'info, DelegationAccount>,
    pub verifier: Signer<'info>,
    pub oracle_feed: Option<AccountInfo<'info>>,
}

#[derive(Accounts)]
pub struct SetupContractTermsWithOracle<'info> {
    #[account(
        mut,
        seeds = [b"delegation", delegation.bank_authority.as_ref()],
        bump,
        constraint = delegation.bank_authority == authority.key() @ DelegationError::UnauthorizedAccess
    )]
    pub delegation: Account<'info, DelegationAccount>,
    pub authority: Signer<'info>,
    pub oracle_feed: Option<AccountInfo<'info>>,
}

#[event]
pub struct DutyAssigned {
    pub delegation_id: Pubkey,
    pub duty_id: u64,
    pub assigned_to: Pubkey,
    pub assigned_by: Pubkey,
    pub description: String,
    pub payment_amount: u64,
    pub due_date: i64,
    pub duty_hash: Vec<u8>,
    pub ai_auditor_assessment: bool,
    pub timestamp: i64,
}

#[event]
pub struct DutyCompleted {
    pub delegation_id: Pubkey,
    pub duty_id: u64,
    pub assignee: Pubkey,
    pub completion_proof: Vec<u8>,
    pub verification_required: bool,
    pub timestamp: i64,
}

#[event]
pub struct AiAuditCompleted {
    pub delegation_id: Pubkey,
    pub duty_id: u64,
    pub ai_auditor: Pubkey,
    pub completeness_score: u8,
    pub sincerity_score: u8,
    pub findings: Vec<String>,
    pub timestamp: i64,
}

#[event]
pub struct VrfAuditConfigured {
    pub delegation_id: Pubkey,
    pub audit_type: AuditType,
    pub frequency: AuditFrequency,
    pub vrf_seed: u64,
    pub oracle_feed: Option<Pubkey>,
    pub next_audit_due: i64,
    pub timestamp: i64,
}

#[event]
pub struct RandomAuditExecuted {
    pub delegation_id: Pubkey,
    pub audit_id: u64,
    pub auditor: Pubkey,
    pub compliance_score: u8,
    pub findings_count: u32,
    pub vrf_proof: Vec<u8>,
    pub next_audit_due: i64,
    pub timestamp: i64,
}

#[event]
pub struct VotingSystemConfigured {
    pub delegation_id: Pubkey,
    pub voting_type: VotingType,
    pub employee_weight_percent: u8,
    pub shareholder_weight_percent: u8,
    pub ai_classification_enabled: bool,
    pub public_voting: bool,
    pub timestamp: i64,
}

#[event]
pub struct VoteSubmitted {
    pub delegation_id: Pubkey,
    pub issue_id: u64,
    pub voter: Pubkey,
    pub vote: bool,
    pub voter_type: VotingType,
    pub vote_weight: u8,
    pub is_major_issue: bool,
    pub ai_classification_score: Option<f64>,
    pub public_vote: bool,
    pub timestamp: i64,
}

#[event]
pub struct ZKPVoteSubmitted {
    pub delegation_id: Pubkey,
    pub issue_id: u64,
}

fn validate_delegation_authority(
    _authority: &Pubkey,
    authority_level: &AuthorityLevel,
    delegation_type: &DelegationType,
) -> Result<bool> {
    match (authority_level, delegation_type) {
        (AuthorityLevel::Founder, _) => Ok(true),
        (AuthorityLevel::BoardMember, DelegationType::BoardToCto) => Ok(true),
        (AuthorityLevel::BoardMember, DelegationType::ProjectManagement) => Ok(true),
        (AuthorityLevel::CEO, DelegationType::CeoToAssistant) => Ok(true),
        (AuthorityLevel::CEO, DelegationType::ProjectManagement) => Ok(true),
        (AuthorityLevel::CTO, DelegationType::ProjectManagement) => Ok(true),
        (AuthorityLevel::CTO, DelegationType::AiAuditor) => Ok(true),
        _ => Ok(false),
    }
}

    pub voter: Pubkey,
    pub vote_commitment: [u8; 32],
    pub stake_proof: [u8; 32],
    pub eligibility_proof: [u8; 32],
    pub voter_type: VotingType,
    pub proof_hash: Vec<u8>,
    pub public_vote: bool,
    pub timestamp: i64,
}

#[event]
pub struct OracleVerificationCompleted {
    pub delegation_id: Pubkey,
    pub duty_id: u64,
    pub oracle_feed: Option<Pubkey>,
    pub verification_result: bool,
    pub payment_triggered: bool,
    pub timestamp: i64,
}

#[event]
pub struct ContractTermsWithOracleSetup {
    pub delegation_id: Pubkey,
    pub terms_hash: [u8; 32],
    pub payment_on_delivery: bool,
    pub oracle_verification_required: bool,
    pub audit_frequency: AuditFrequency,
    pub milestone_count: u32,
    pub timestamp: i64,
}
