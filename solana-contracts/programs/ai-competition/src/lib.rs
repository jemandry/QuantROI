use anchor_lang::prelude::*;
use anchor_spl::token::{self, Token, TokenAccount, Transfer};
use sha3::{Digest, Sha3_256};

declare_id!("AiCompetitionProgram111111111111111111111");

#[program]
pub mod ai_competition {
    use super::*;

    pub fn initialize(ctx: Context<Initialize>) -> Result<()> {
        let competition = &mut ctx.accounts.competition;
        competition.authority = ctx.accounts.authority.key();
        competition.total_objectives = 0;
        competition.active_objectives = 0;
        competition.completed_objectives = 0;
        
        emit!(CompetitionInitialized {
            authority: competition.authority,
            timestamp: Clock::get()?.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn create_wealth_objective(
        ctx: Context<CreateObjective>,
        objective: WealthObjective,
    ) -> Result<()> {
        let competition = &mut ctx.accounts.competition;
        let objective_account = &mut ctx.accounts.objective_account;
        
        objective_account.owner = ctx.accounts.user.key();
        objective_account.objective = objective.clone();
        objective_account.status = ObjectiveStatus::Active;
        objective_account.creation_timestamp = Clock::get()?.unix_timestamp;
        objective_account.progress_percentage = 0;
        objective_account.milestones_completed = 0;
        objective_account.extension_requests = 0;
        objective_account.votes_for_supplement = 0;
        objective_account.votes_against_supplement = 0;
        
        let objective_hash = create_objective_hash(&objective)?;
        objective_account.objective_hash = objective_hash;
        
        competition.total_objectives += 1;
        competition.active_objectives += 1;
        
        emit!(WealthObjectiveCreated {
            owner: ctx.accounts.user.key(),
            objective_hash,
            target_roi: objective.target_roi,
            timeline_months: objective.timeline_months,
            timestamp: Clock::get()?.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn update_objective_progress(
        ctx: Context<UpdateProgress>,
        progress: ObjectiveProgress,
    ) -> Result<()> {
        let objective_account = &mut ctx.accounts.objective_account;
        
        require!(objective_account.owner == ctx.accounts.user.key(), ErrorCode::UnauthorizedObjectiveOwner);
        require!(objective_account.status == ObjectiveStatus::Active, ErrorCode::ObjectiveNotActive);
        
        objective_account.progress_percentage = progress.percentage;
        objective_account.current_roi = Some(progress.current_roi);
        objective_account.last_update_timestamp = Clock::get()?.unix_timestamp;
        
        if progress.milestone_completed {
            objective_account.milestones_completed += 1;
        }
        
        if progress.percentage >= 100 {
            objective_account.status = ObjectiveStatus::Completed;
            objective_account.completion_timestamp = Some(Clock::get()?.unix_timestamp);
            
            let competition = &mut ctx.accounts.competition;
            competition.active_objectives -= 1;
            competition.completed_objectives += 1;
        }
        
        emit!(ObjectiveProgressUpdated {
            objective_account: ctx.accounts.objective_account.key(),
            owner: ctx.accounts.user.key(),
            progress_percentage: progress.percentage,
            current_roi: progress.current_roi,
            milestone_completed: progress.milestone_completed,
            timestamp: Clock::get()?.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn generate_ai_timeline(
        ctx: Context<GenerateTimeline>,
        goal_params: GoalParameters,
    ) -> Result<()> {
        let objective_account = &mut ctx.accounts.objective_account;
        
        require!(objective_account.owner == ctx.accounts.user.key(), ErrorCode::UnauthorizedObjectiveOwner);
        
        let ai_timeline = AITimeline {
            milestones: generate_milestones(&goal_params)?,
            risk_assessments: generate_risk_assessments(&goal_params)?,
            recommended_strategies: generate_strategies(&goal_params)?,
            inspector_rotation_schedule: generate_rotation_schedule()?,
        };
        
        objective_account.ai_timeline = Some(ai_timeline.clone());
        objective_account.timeline_generated_timestamp = Some(Clock::get()?.unix_timestamp);
        
        emit!(AITimelineGenerated {
            objective_account: ctx.accounts.objective_account.key(),
            owner: ctx.accounts.user.key(),
            milestone_count: ai_timeline.milestones.len() as u8,
            timestamp: Clock::get()?.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn request_objective_extension(
        ctx: Context<RequestExtension>,
        reason: String,
        additional_months: u8,
    ) -> Result<()> {
        let objective_account = &mut ctx.accounts.objective_account;
        
        require!(objective_account.owner == ctx.accounts.user.key(), ErrorCode::UnauthorizedObjectiveOwner);
        require!(objective_account.status == ObjectiveStatus::Active, ErrorCode::ObjectiveNotActive);
        require!(additional_months <= 12, ErrorCode::ExcessiveExtensionRequest);
        
        objective_account.extension_requests += 1;
        objective_account.last_extension_reason = Some(reason.clone());
        objective_account.requested_additional_months = Some(additional_months);
        objective_account.extension_request_timestamp = Some(Clock::get()?.unix_timestamp);
        
        emit!(ObjectiveExtensionRequested {
            objective_account: ctx.accounts.objective_account.key(),
            owner: ctx.accounts.user.key(),
            reason,
            additional_months,
            timestamp: Clock::get()?.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn vote_on_objective_supplement(
        ctx: Context<VoteObjective>,
        vote: ObjectiveVote,
        expense_amount: Option<u64>,
    ) -> Result<()> {
        let objective_account = &mut ctx.accounts.objective_account;
        
        require!(objective_account.status == ObjectiveStatus::Active, ErrorCode::ObjectiveNotActive);
        
        if let Some(amount) = expense_amount {
            require!(amount <= 1000_000_000, ErrorCode::ExcessiveSupplementAmount);
        }
        
        match vote {
            ObjectiveVote::For => objective_account.votes_for_supplement += 1,
            ObjectiveVote::Against => objective_account.votes_against_supplement += 1,
        }
        
        emit!(ObjectiveSupplementVoted {
            objective_account: ctx.accounts.objective_account.key(),
            voter: ctx.accounts.voter.key(),
            vote,
            expense_amount,
            timestamp: Clock::get()?.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn distribute_objective_rewards(ctx: Context<DistributeRewards>) -> Result<()> {
        let objective_account = &ctx.accounts.objective_account;
        
        require!(objective_account.status == ObjectiveStatus::Completed, ErrorCode::ObjectiveNotCompleted);
        require!(objective_account.owner == ctx.accounts.user.key(), ErrorCode::UnauthorizedObjectiveOwner);
        
        let reward_amount = calculate_reward_amount(objective_account)?;
        
        let transfer_instruction = Transfer {
            from: ctx.accounts.reward_pool.to_account_info(),
            to: ctx.accounts.user_token_account.to_account_info(),
            authority: ctx.accounts.authority.to_account_info(),
        };
        
        token::transfer(
            CpiContext::new(
                ctx.accounts.token_program.to_account_info(),
                transfer_instruction,
            ),
            reward_amount,
        )?;
        
        emit!(ObjectiveRewardDistributed {
            objective_account: ctx.accounts.objective_account.key(),
            owner: ctx.accounts.user.key(),
            reward_amount,
            timestamp: Clock::get()?.unix_timestamp,
        });
        
        Ok(())
    }
}

fn create_objective_hash(objective: &WealthObjective) -> Result<[u8; 32]> {
    let mut hasher = Sha3_256::new();
    hasher.update(objective.goal_description.as_bytes());
    hasher.update(&objective.target_roi.to_le_bytes());
    hasher.update(&objective.timeline_months.to_le_bytes());
    hasher.update(&objective.risk_tolerance.to_le_bytes());
    Ok(hasher.finalize().into())
}

fn generate_milestones(goal_params: &GoalParameters) -> Result<Vec<Milestone>> {
    let milestone_count = (goal_params.timeline_months / 3).max(1);
    let mut milestones = Vec::new();
    
    for i in 0..milestone_count {
        milestones.push(Milestone {
            description: format!("Milestone {} - {}% progress target", i + 1, (i + 1) * 100 / milestone_count),
            target_percentage: (i + 1) * 100 / milestone_count,
            deadline_months: (i + 1) * 3,
            reward_amount: goal_params.total_investment / (milestone_count as u64),
        });
    }
    
    Ok(milestones)
}

fn generate_risk_assessments(_goal_params: &GoalParameters) -> Result<Vec<RiskAssessment>> {
    Ok(vec![
        RiskAssessment {
            risk_type: "Market Volatility".to_string(),
            probability: 0.3,
            impact_score: 7,
            mitigation_strategy: "Diversified portfolio allocation".to_string(),
        },
        RiskAssessment {
            risk_type: "Regulatory Changes".to_string(),
            probability: 0.2,
            impact_score: 8,
            mitigation_strategy: "Compliance monitoring and adaptation".to_string(),
        },
    ])
}

fn generate_strategies(_goal_params: &GoalParameters) -> Result<Vec<String>> {
    Ok(vec![
        "AI-driven portfolio optimization".to_string(),
        "Automated rebalancing based on market conditions".to_string(),
        "Risk-adjusted position sizing".to_string(),
    ])
}

fn generate_rotation_schedule() -> Result<Vec<InspectorRotation>> {
    Ok(vec![
        InspectorRotation {
            inspector_id: "inspector_1".to_string(),
            rotation_week: 1,
            specialization: "Risk Assessment".to_string(),
        },
        InspectorRotation {
            inspector_id: "inspector_2".to_string(),
            rotation_week: 2,
            specialization: "Compliance Review".to_string(),
        },
    ])
}

fn calculate_reward_amount(objective_account: &ObjectiveAccount) -> Result<u64> {
    let base_reward = 1_000_000;
    let roi_multiplier = if let Some(current_roi) = objective_account.current_roi {
        if current_roi >= objective_account.objective.target_roi {
            2.0
        } else {
            1.0 + (current_roi / objective_account.objective.target_roi)
        }
    } else {
        1.0
    };
    
    Ok((base_reward as f64 * roi_multiplier) as u64)
}

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(
        init,
        payer = authority,
        space = 8 + Competition::INIT_SPACE
    )]
    pub competition: Account<'info, Competition>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct CreateObjective<'info> {
    #[account(mut)]
    pub competition: Account<'info, Competition>,
    #[account(
        init,
        payer = user,
        space = 8 + ObjectiveAccount::INIT_SPACE
    )]
    pub objective_account: Account<'info, ObjectiveAccount>,
    #[account(mut)]
    pub user: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct UpdateProgress<'info> {
    #[account(mut)]
    pub competition: Account<'info, Competition>,
    #[account(mut)]
    pub objective_account: Account<'info, ObjectiveAccount>,
    pub user: Signer<'info>,
}

#[derive(Accounts)]
pub struct GenerateTimeline<'info> {
    #[account(mut)]
    pub objective_account: Account<'info, ObjectiveAccount>,
    pub user: Signer<'info>,
}

#[derive(Accounts)]
pub struct RequestExtension<'info> {
    #[account(mut)]
    pub objective_account: Account<'info, ObjectiveAccount>,
    pub user: Signer<'info>,
}

#[derive(Accounts)]
pub struct VoteObjective<'info> {
    #[account(mut)]
    pub objective_account: Account<'info, ObjectiveAccount>,
    pub voter: Signer<'info>,
}

#[derive(Accounts)]
pub struct DistributeRewards<'info> {
    pub objective_account: Account<'info, ObjectiveAccount>,
    #[account(mut)]
    pub user: Signer<'info>,
    #[account(mut)]
    pub authority: Signer<'info>,
    #[account(mut)]
    pub reward_pool: Account<'info, TokenAccount>,
    #[account(mut)]
    pub user_token_account: Account<'info, TokenAccount>,
    pub token_program: Program<'info, Token>,
}

#[account]
#[derive(InitSpace)]
pub struct Competition {
    pub authority: Pubkey,
    pub total_objectives: u64,
    pub active_objectives: u64,
    pub completed_objectives: u64,
}

#[account]
#[derive(InitSpace)]
pub struct ObjectiveAccount {
    pub owner: Pubkey,
    #[max_len(300)]
    pub objective: WealthObjective,
    pub objective_hash: [u8; 32],
    pub status: ObjectiveStatus,
    pub creation_timestamp: i64,
    pub completion_timestamp: Option<i64>,
    pub progress_percentage: u8,
    pub current_roi: Option<f64>,
    pub last_update_timestamp: i64,
    pub milestones_completed: u8,
    #[max_len(500)]
    pub ai_timeline: Option<AITimeline>,
    pub timeline_generated_timestamp: Option<i64>,
    pub extension_requests: u8,
    #[max_len(200)]
    pub last_extension_reason: Option<String>,
    pub requested_additional_months: Option<u8>,
    pub extension_request_timestamp: Option<i64>,
    pub votes_for_supplement: u32,
    pub votes_against_supplement: u32,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, InitSpace)]
pub struct WealthObjective {
    #[max_len(100)]
    pub goal_description: String,
    pub target_roi: f64,
    pub timeline_months: u8,
    pub risk_tolerance: u8,
    pub total_investment: u64,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, InitSpace)]
pub struct ObjectiveProgress {
    pub percentage: u8,
    pub current_roi: f64,
    pub milestone_completed: bool,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, InitSpace)]
pub struct GoalParameters {
    pub timeline_months: u8,
    pub risk_tolerance: u8,
    pub total_investment: u64,
    #[max_len(50)]
    pub investment_style: String,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, InitSpace)]
pub struct AITimeline {
    #[max_len(10)]
    pub milestones: Vec<Milestone>,
    #[max_len(5)]
    pub risk_assessments: Vec<RiskAssessment>,
    #[max_len(5)]
    pub recommended_strategies: Vec<String>,
    #[max_len(10)]
    pub inspector_rotation_schedule: Vec<InspectorRotation>,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, InitSpace)]
pub struct Milestone {
    #[max_len(100)]
    pub description: String,
    pub target_percentage: u8,
    pub deadline_months: u8,
    pub reward_amount: u64,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, InitSpace)]
pub struct RiskAssessment {
    #[max_len(50)]
    pub risk_type: String,
    pub probability: f64,
    pub impact_score: u8,
    #[max_len(100)]
    pub mitigation_strategy: String,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, InitSpace)]
pub struct InspectorRotation {
    #[max_len(50)]
    pub inspector_id: String,
    pub rotation_week: u8,
    #[max_len(50)]
    pub specialization: String,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq)]
pub enum ObjectiveStatus {
    Active,
    Completed,
    Failed,
    Extended,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq)]
pub enum ObjectiveVote {
    For,
    Against,
}

#[event]
pub struct CompetitionInitialized {
    pub authority: Pubkey,
    pub timestamp: i64,
}

#[event]
pub struct WealthObjectiveCreated {
    pub owner: Pubkey,
    pub objective_hash: [u8; 32],
    pub target_roi: f64,
    pub timeline_months: u8,
    pub timestamp: i64,
}

#[event]
pub struct ObjectiveProgressUpdated {
    pub objective_account: Pubkey,
    pub owner: Pubkey,
    pub progress_percentage: u8,
    pub current_roi: f64,
    pub milestone_completed: bool,
    pub timestamp: i64,
}

#[event]
pub struct AITimelineGenerated {
    pub objective_account: Pubkey,
    pub owner: Pubkey,
    pub milestone_count: u8,
    pub timestamp: i64,
}

#[event]
pub struct ObjectiveExtensionRequested {
    pub objective_account: Pubkey,
    pub owner: Pubkey,
    #[max_len(200)]
    pub reason: String,
    pub additional_months: u8,
    pub timestamp: i64,
}

#[event]
pub struct ObjectiveSupplementVoted {
    pub objective_account: Pubkey,
    pub voter: Pubkey,
    pub vote: ObjectiveVote,
    pub expense_amount: Option<u64>,
    pub timestamp: i64,
}

#[event]
pub struct ObjectiveRewardDistributed {
    pub objective_account: Pubkey,
    pub owner: Pubkey,
    pub reward_amount: u64,
    pub timestamp: i64,
}

#[error_code]
pub enum ErrorCode {
    #[msg("Unauthorized objective owner")]
    UnauthorizedObjectiveOwner,
    #[msg("Objective is not active")]
    ObjectiveNotActive,
    #[msg("Objective is not completed")]
    ObjectiveNotCompleted,
    #[msg("Extension request exceeds maximum allowed months")]
    ExcessiveExtensionRequest,
    #[msg("Supplement amount exceeds maximum allowed")]
    ExcessiveSupplementAmount,
}
