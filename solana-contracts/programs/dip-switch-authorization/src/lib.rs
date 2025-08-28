use anchor_lang::prelude::*;
use anchor_lang::solana_program::hash::hash;

declare_id!("DipSwitchAuth11111111111111111111111111111111");

#[program]
pub mod dip_switch_authorization {
    use super::*;

    pub fn create_authorization(
        ctx: Context<CreateAuthorization>,
        agent_id: String,
        allowed_actions: Vec<String>,
        constraints: String, // JSON string of constraints
        investor_type: u8,   // 0=Conservative, 1=Moderate, 2=Aggressive
        expiration_timestamp: i64,
        p_value_threshold: f64,
        confidence_threshold: f64,
    ) -> Result<()> {
        let authorization = &mut ctx.accounts.authorization;
        let clock = Clock::get()?;

        require!(
            expiration_timestamp > clock.unix_timestamp,
            AuthorizationError::ExpirationInPast
        );

        require!(
            p_value_threshold > 0.0 && p_value_threshold <= 1.0,
            AuthorizationError::InvalidPValueThreshold
        );
        require!(
            confidence_threshold > 0.0 && confidence_threshold <= 1.0,
            AuthorizationError::InvalidConfidenceThreshold
        );

        let auth_data = format!(
            "{}:{}:{}:{}:{}:{}",
            agent_id,
            allowed_actions.join(","),
            constraints,
            investor_type,
            expiration_timestamp,
            clock.unix_timestamp
        );
        let auth_hash = hash(auth_data.as_bytes());

        authorization.agent_id = agent_id;
        authorization.allowed_actions = allowed_actions;
        authorization.constraints = constraints;
        authorization.investor_type = investor_type;
        authorization.expiration_timestamp = expiration_timestamp;
        authorization.p_value_threshold = p_value_threshold;
        authorization.confidence_threshold = confidence_threshold;
        authorization.authorization_hash = auth_hash.to_bytes();
        authorization.created_at = clock.unix_timestamp;
        authorization.last_modified = clock.unix_timestamp;
        authorization.is_active = true;
        authorization.authority = ctx.accounts.authority.key();

        emit!(AuthorizationCreated {
            agent_id: authorization.agent_id.clone(),
            authorization_hash: auth_hash.to_bytes(),
            investor_type,
            expiration_timestamp,
            created_at: clock.unix_timestamp,
        });

        Ok(())
    }

    pub fn modify_authorization(
        ctx: Context<ModifyAuthorization>,
        new_constraints: String,
        new_expiration: Option<i64>,
    ) -> Result<()> {
        let authorization = &mut ctx.accounts.authorization;
        let clock = Clock::get()?;

        require!(authorization.is_active, AuthorizationError::AuthorizationInactive);
        require!(
            authorization.expiration_timestamp > clock.unix_timestamp,
            AuthorizationError::AuthorizationExpired
        );

        authorization.constraints = new_constraints;
        authorization.last_modified = clock.unix_timestamp;

        if let Some(new_exp) = new_expiration {
            require!(
                new_exp > clock.unix_timestamp,
                AuthorizationError::ExpirationInPast
            );
            authorization.expiration_timestamp = new_exp;
        }

        let auth_data = format!(
            "{}:{}:{}:{}:{}:{}",
            authorization.agent_id,
            authorization.allowed_actions.join(","),
            authorization.constraints,
            authorization.investor_type,
            authorization.expiration_timestamp,
            clock.unix_timestamp
        );
        let new_hash = hash(auth_data.as_bytes());
        authorization.authorization_hash = new_hash.to_bytes();

        emit!(AuthorizationModified {
            agent_id: authorization.agent_id.clone(),
            new_hash: new_hash.to_bytes(),
            modified_at: clock.unix_timestamp,
        });

        Ok(())
    }

    pub fn validate_authorization(
        ctx: Context<ValidateAuthorization>,
        action: String,
        causal_claim: String,
        p_value: f64,
        confidence: f64,
    ) -> Result<bool> {
        let authorization = &ctx.accounts.authorization;
        let clock = Clock::get()?;

        if !authorization.is_active || authorization.expiration_timestamp <= clock.unix_timestamp {
            return Ok(false);
        }

        if !authorization.allowed_actions.contains(&action) {
            return Ok(false);
        }

        if p_value > authorization.p_value_threshold {
            emit!(ValidationFailed {
                agent_id: authorization.agent_id.clone(),
                reason: "p_value_threshold_exceeded".to_string(),
                p_value,
                threshold: authorization.p_value_threshold,
                timestamp: clock.unix_timestamp,
            });
            return Ok(false);
        }

        if confidence < authorization.confidence_threshold {
            emit!(ValidationFailed {
                agent_id: authorization.agent_id.clone(),
                reason: "confidence_threshold_not_met".to_string(),
                confidence,
                threshold: authorization.confidence_threshold,
                timestamp: clock.unix_timestamp,
            });
            return Ok(false);
        }

        emit!(ValidationSuccessful {
            agent_id: authorization.agent_id.clone(),
            action,
            causal_claim,
            p_value,
            confidence,
            timestamp: clock.unix_timestamp,
        });

        Ok(true)
    }

    pub fn record_hallucination(
        ctx: Context<RecordHallucination>,
        hallucination_id: String,
        hallucination_type: u8, // 0=Unvalidated, 1=Statistical, 2=Causal, 3=DataQuality
        causal_claim: String,
        validation_failed: String, // JSON string
        market_regime: String,
        vix_level: f64,
        error_cause: String,
    ) -> Result<()> {
        let hallucination = &mut ctx.accounts.hallucination;
        let clock = Clock::get()?;

        hallucination.hallucination_id = hallucination_id;
        hallucination.hallucination_type = hallucination_type;
        hallucination.causal_claim = causal_claim;
        hallucination.validation_failed = validation_failed;
        hallucination.market_regime = market_regime;
        hallucination.vix_level = vix_level;
        hallucination.error_cause = error_cause;
        hallucination.detected_at = clock.unix_timestamp;
        hallucination.authority = ctx.accounts.authority.key();

        emit!(HallucinationRecorded {
            hallucination_id: hallucination.hallucination_id.clone(),
            hallucination_type,
            market_regime: hallucination.market_regime.clone(),
            vix_level,
            detected_at: clock.unix_timestamp,
        });

        Ok(())
    }

    pub fn expire_authorization(ctx: Context<ExpireAuthorization>) -> Result<()> {
        let authorization = &mut ctx.accounts.authorization;
        let clock = Clock::get()?;

        authorization.is_active = false;
        authorization.last_modified = clock.unix_timestamp;

        emit!(AuthorizationExpired {
            agent_id: authorization.agent_id.clone(),
            expired_at: clock.unix_timestamp,
        });

        Ok(())
    }

    pub fn update_investor_financial_goals(
        ctx: Context<UpdateInvestorGoals>,
        investor_id: String,
        financial_goals: Vec<String>,
        target_amounts: Vec<u64>,
        time_horizons: Vec<i64>,
    ) -> Result<()> {
        let goals = &mut ctx.accounts.investor_goals;
        let clock = Clock::get()?;

        require!(
            financial_goals.len() == target_amounts.len() && 
            target_amounts.len() == time_horizons.len(),
            AuthorizationError::InvalidGoalParameters
        );

        require!(
            financial_goals.len() <= 10,
            AuthorizationError::TooManyGoals
        );

        goals.investor_id = investor_id.clone();
        goals.financial_goals = financial_goals.clone();
        goals.target_amounts = target_amounts.clone();
        goals.time_horizons = time_horizons.clone();
        goals.last_updated = clock.unix_timestamp;
        goals.authority = ctx.accounts.authority.key();

        let total_target: u64 = target_amounts.iter().sum();
        goals.total_target_amount = total_target;

        emit!(InvestorGoalsUpdated {
            investor_id,
            goals_count: financial_goals.len() as u8,
            total_target_amount: total_target,
            updated_at: clock.unix_timestamp,
        });

        Ok(())
    }

    pub fn validate_investor_constraints(
        ctx: Context<ValidateInvestorConstraints>,
        investor_id: String,
        proposed_allocation: Vec<u8>, // Percentage allocations
        risk_score: f64,
    ) -> Result<bool> {
        let authorization = &ctx.accounts.authorization;
        let goals = &ctx.accounts.investor_goals;
        let clock = Clock::get()?;

        require!(authorization.is_active, AuthorizationError::AuthorizationInactive);
        require!(
            authorization.expiration_timestamp > clock.unix_timestamp,
            AuthorizationError::AuthorizationExpired
        );

        require!(
            goals.investor_id == investor_id,
            AuthorizationError::InvestorMismatch
        );

        let total_allocation: u32 = proposed_allocation.iter().map(|&x| x as u32).sum();
        require!(
            total_allocation == 100,
            AuthorizationError::InvalidAllocation
        );

        // Validate risk score against investor type constraints
        let max_risk_score = match authorization.investor_type {
            0 => 0.3, // Conservative
            1 => 0.6, // Moderate  
            2 => 1.0, // Aggressive
            _ => 0.5, // Default
        };

        let validation_passed = risk_score <= max_risk_score;

        emit!(InvestorConstraintsValidated {
            investor_id,
            risk_score,
            max_allowed_risk: max_risk_score,
            validation_passed,
            validated_at: clock.unix_timestamp,
        });

        Ok(validation_passed)
    }
}

#[derive(Accounts)]
#[instruction(agent_id: String)]
pub struct CreateAuthorization<'info> {
    #[account(
        init,
        payer = authority,
        space = 8 + Authorization::INIT_SPACE,
        seeds = [b"authorization", agent_id.as_bytes()],
        bump
    )]
    pub authorization: Account<'info, Authorization>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct ModifyAuthorization<'info> {
    #[account(
        mut,
        has_one = authority,
        seeds = [b"authorization", authorization.agent_id.as_bytes()],
        bump
    )]
    pub authorization: Account<'info, Authorization>,
    pub authority: Signer<'info>,
}

#[derive(Accounts)]
pub struct ValidateAuthorization<'info> {
    #[account(
        seeds = [b"authorization", authorization.agent_id.as_bytes()],
        bump
    )]
    pub authorization: Account<'info, Authorization>,
}

#[derive(Accounts)]
#[instruction(hallucination_id: String)]
pub struct RecordHallucination<'info> {
    #[account(
        init,
        payer = authority,
        space = 8 + HallucinationRecord::INIT_SPACE,
        seeds = [b"hallucination", hallucination_id.as_bytes()],
        bump
    )]
    pub hallucination: Account<'info, HallucinationRecord>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct ExpireAuthorization<'info> {
    #[account(
        mut,
        has_one = authority,
        seeds = [b"authorization", authorization.agent_id.as_bytes()],
        bump
    )]
    pub authorization: Account<'info, Authorization>,
    pub authority: Signer<'info>,
}

#[derive(Accounts)]
#[instruction(investor_id: String)]
pub struct UpdateInvestorGoals<'info> {
    #[account(
        init_if_needed,
        payer = authority,
        space = 8 + InvestorFinancialGoals::INIT_SPACE,
        seeds = [b"investor_goals", investor_id.as_bytes()],
        bump
    )]
    pub investor_goals: Account<'info, InvestorFinancialGoals>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct ValidateInvestorConstraints<'info> {
    #[account(
        seeds = [b"authorization", authorization.agent_id.as_bytes()],
        bump
    )]
    pub authorization: Account<'info, Authorization>,
    #[account(
        seeds = [b"investor_goals", investor_goals.investor_id.as_bytes()],
        bump
    )]
    pub investor_goals: Account<'info, InvestorFinancialGoals>,
}

#[account]
#[derive(InitSpace)]
pub struct Authorization {
    #[max_len(64)]
    pub agent_id: String,
    #[max_len(10, 32)] // Max 10 actions, each up to 32 chars
    pub allowed_actions: Vec<String>,
    #[max_len(512)]
    pub constraints: String, // JSON string of constraints
    pub investor_type: u8,   // 0=Conservative, 1=Moderate, 2=Aggressive
    pub expiration_timestamp: i64,
    pub p_value_threshold: f64,
    pub confidence_threshold: f64,
    pub authorization_hash: [u8; 32],
    pub created_at: i64,
    pub last_modified: i64,
    pub is_active: bool,
    pub authority: Pubkey,
}

#[account]
#[derive(InitSpace)]
pub struct HallucinationRecord {
    #[max_len(32)]
    pub hallucination_id: String,
    pub hallucination_type: u8, // 0=Unvalidated, 1=Statistical, 2=Causal, 3=DataQuality
    #[max_len(256)]
    pub causal_claim: String,
    #[max_len(512)]
    pub validation_failed: String, // JSON string
    #[max_len(32)]
    pub market_regime: String,
    pub vix_level: f64,
    #[max_len(128)]
    pub error_cause: String,
    pub detected_at: i64,
    pub authority: Pubkey,
}

#[account]
#[derive(InitSpace)]
pub struct InvestorFinancialGoals {
    #[max_len(64)]
    pub investor_id: String,
    #[max_len(10, 64)] // Max 10 goals, each up to 64 chars
    pub financial_goals: Vec<String>,
    #[max_len(10)] // Max 10 target amounts
    pub target_amounts: Vec<u64>,
    #[max_len(10)] // Max 10 time horizons
    pub time_horizons: Vec<i64>,
    pub total_target_amount: u64,
    pub last_updated: i64,
    pub authority: Pubkey,
}

#[event]
pub struct AuthorizationCreated {
    pub agent_id: String,
    pub authorization_hash: [u8; 32],
    pub investor_type: u8,
    pub expiration_timestamp: i64,
    pub created_at: i64,
}

#[event]
pub struct AuthorizationModified {
    pub agent_id: String,
    pub new_hash: [u8; 32],
    pub modified_at: i64,
}

#[event]
pub struct ValidationSuccessful {
    pub agent_id: String,
    pub action: String,
    pub causal_claim: String,
    pub p_value: f64,
    pub confidence: f64,
    pub timestamp: i64,
}

#[event]
pub struct ValidationFailed {
    pub agent_id: String,
    pub reason: String,
    pub p_value: f64,
    pub threshold: f64,
    pub confidence: f64,
    pub timestamp: i64,
}

#[event]
pub struct HallucinationRecorded {
    pub hallucination_id: String,
    pub hallucination_type: u8,
    pub market_regime: String,
    pub vix_level: f64,
    pub detected_at: i64,
}

#[event]
pub struct AuthorizationExpired {
    pub agent_id: String,
    pub expired_at: i64,
}

#[event]
pub struct InvestorGoalsUpdated {
    pub investor_id: String,
    pub goals_count: u8,
    pub total_target_amount: u64,
    pub updated_at: i64,
}

#[event]
pub struct InvestorConstraintsValidated {
    pub investor_id: String,
    pub risk_score: f64,
    pub max_allowed_risk: f64,
    pub validation_passed: bool,
    pub validated_at: i64,
}

#[error_code]
pub enum AuthorizationError {
    #[msg("Expiration timestamp cannot be in the past")]
    ExpirationInPast,
    #[msg("P-value threshold must be between 0 and 1")]
    InvalidPValueThreshold,
    #[msg("Confidence threshold must be between 0 and 1")]
    InvalidConfidenceThreshold,
    #[msg("Authorization is not active")]
    AuthorizationInactive,
    #[msg("Authorization has expired")]
    AuthorizationExpired,
    #[msg("Financial goal parameters have mismatched lengths")]
    InvalidGoalParameters,
    #[msg("Too many financial goals specified (max 10)")]
    TooManyGoals,
    #[msg("Investor ID does not match")]
    InvestorMismatch,
    #[msg("Allocation percentages must sum to 100")]
    InvalidAllocation,
}
