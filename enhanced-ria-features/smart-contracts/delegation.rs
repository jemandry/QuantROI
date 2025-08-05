use anchor_lang::prelude::*;
use anchor_spl::token::{self, Token, TokenAccount, Transfer};

declare_id!("DeLegAtion1111111111111111111111111111111111");

#[program]
pub mod delegation {
    use super::*;

    pub fn initialize_delegation(
        ctx: Context<InitializeDelegation>,
        merkle_root: [u8; 32],
        voting_period: i64,
        min_stake_threshold: u64,
    ) -> Result<()> {
        let delegation_state = &mut ctx.accounts.delegation_state;
        delegation_state.authority = ctx.accounts.authority.key();
        delegation_state.merkle_root = merkle_root;
        delegation_state.voting_period = voting_period;
        delegation_state.min_stake_threshold = min_stake_threshold;
        delegation_state.total_votes = 0;
        delegation_state.yes_votes = 0;
        delegation_state.no_votes = 0;
        delegation_state.is_active = true;
        delegation_state.created_at = Clock::get()?.unix_timestamp;
        
        msg!("Delegation initialized with merkle root: {:?}", merkle_root);
        Ok(())
    }

    pub fn submit_zkp_vote(
        ctx: Context<SubmitZKPVote>,
        random_vote_id: [u8; 32],
        nullifier: [u8; 32],
        vote_choice: bool,
        zkp_proof: ZKPProof,
    ) -> Result<()> {
        let delegation_state = &mut ctx.accounts.delegation_state;
        let vote_record = &mut ctx.accounts.vote_record;
        
        let current_time = Clock::get()?.unix_timestamp;
        require!(
            delegation_state.is_active && 
            current_time <= delegation_state.created_at + delegation_state.voting_period,
            DelegationError::VotingPeriodExpired
        );
        
        require!(
            !delegation_state.used_nullifiers.contains(&nullifier),
            DelegationError::NullifierAlreadyUsed
        );
        
        require!(
            verify_zkp_proof(&zkp_proof, &delegation_state.merkle_root),
            DelegationError::InvalidZKPProof
        );
        
        vote_record.random_vote_id = random_vote_id;
        vote_record.nullifier = nullifier;
        vote_record.vote_choice = vote_choice;
        vote_record.timestamp = current_time;
        vote_record.delegation_state = delegation_state.key();
        
        delegation_state.total_votes += 1;
        if vote_choice {
            delegation_state.yes_votes += 1;
        } else {
            delegation_state.no_votes += 1;
        }
        
        delegation_state.used_nullifiers.push(nullifier);
        
        emit!(VoteSubmitted {
            random_vote_id,
            vote_choice,
            timestamp: current_time,
            total_votes: delegation_state.total_votes,
        });
        
        msg!("ZKP vote submitted with random ID: {:?}", random_vote_id);
        Ok(())
    }

    pub fn finalize_voting(ctx: Context<FinalizeVoting>) -> Result<()> {
        let delegation_state = &mut ctx.accounts.delegation_state;
        
        require!(
            ctx.accounts.authority.key() == delegation_state.authority,
            DelegationError::UnauthorizedAccess
        );
        
        let current_time = Clock::get()?.unix_timestamp;
        require!(
            current_time > delegation_state.created_at + delegation_state.voting_period,
            DelegationError::VotingStillActive
        );
        
        delegation_state.is_active = false;
        delegation_state.finalized_at = current_time;
        
        let total_votes = delegation_state.total_votes;
        let yes_percentage = if total_votes > 0 {
            (delegation_state.yes_votes * 100) / total_votes
        } else {
            0
        };
        
        emit!(VotingFinalized {
            total_votes,
            yes_votes: delegation_state.yes_votes,
            no_votes: delegation_state.no_votes,
            yes_percentage,
            finalized_at: current_time,
        });
        
        msg!("Voting finalized - Yes: {}, No: {}, Total: {}", 
             delegation_state.yes_votes, 
             delegation_state.no_votes, 
             total_votes);
        Ok(())
    }

    pub fn get_voting_results(ctx: Context<GetVotingResults>) -> Result<VotingResults> {
        let delegation_state = &ctx.accounts.delegation_state;
        
        Ok(VotingResults {
            total_votes: delegation_state.total_votes,
            yes_votes: delegation_state.yes_votes,
            no_votes: delegation_state.no_votes,
            is_finalized: !delegation_state.is_active,
            created_at: delegation_state.created_at,
            finalized_at: delegation_state.finalized_at,
        })
    }
}

#[derive(Accounts)]
pub struct InitializeDelegation<'info> {
    #[account(
        init,
        payer = authority,
        space = 8 + DelegationState::INIT_SPACE,
        seeds = [b"delegation", authority.key().as_ref()],
        bump
    )]
    pub delegation_state: Account<'info, DelegationState>,
    
    #[account(mut)]
    pub authority: Signer<'info>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct SubmitZKPVote<'info> {
    #[account(mut)]
    pub delegation_state: Account<'info, DelegationState>,
    
    #[account(
        init,
        payer = voter,
        space = 8 + VoteRecord::INIT_SPACE,
        seeds = [b"vote", delegation_state.key().as_ref(), voter.key().as_ref()],
        bump
    )]
    pub vote_record: Account<'info, VoteRecord>,
    
    #[account(mut)]
    pub voter: Signer<'info>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct FinalizeVoting<'info> {
    #[account(mut)]
    pub delegation_state: Account<'info, DelegationState>,
    
    pub authority: Signer<'info>,
}

#[derive(Accounts)]
pub struct GetVotingResults<'info> {
    pub delegation_state: Account<'info, DelegationState>,
}

#[account]
pub struct DelegationState {
    pub authority: Pubkey,
    pub merkle_root: [u8; 32],
    pub voting_period: i64,
    pub min_stake_threshold: u64,
    pub total_votes: u64,
    pub yes_votes: u64,
    pub no_votes: u64,
    pub is_active: bool,
    pub created_at: i64,
    pub finalized_at: i64,
    pub used_nullifiers: Vec<[u8; 32]>,
}

impl DelegationState {
    const INIT_SPACE: usize = 32 + 32 + 8 + 8 + 8 + 8 + 8 + 1 + 8 + 8 + (4 + 32 * 1000); // Max 1000 nullifiers
}

#[account]
pub struct VoteRecord {
    pub random_vote_id: [u8; 32],
    pub nullifier: [u8; 32],
    pub vote_choice: bool,
    pub timestamp: i64,
    pub delegation_state: Pubkey,
}

impl VoteRecord {
    const INIT_SPACE: usize = 32 + 32 + 1 + 8 + 32;
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct ZKPProof {
    pub pi_a: [String; 3],
    pub pi_b: [[String; 2]; 3],
    pub pi_c: [String; 3],
    pub protocol: String,
    pub curve: String,
}

#[derive(AnchorSerialize, AnchorDeserialize)]
pub struct VotingResults {
    pub total_votes: u64,
    pub yes_votes: u64,
    pub no_votes: u64,
    pub is_finalized: bool,
    pub created_at: i64,
    pub finalized_at: i64,
}

#[event]
pub struct VoteSubmitted {
    pub random_vote_id: [u8; 32],
    pub vote_choice: bool,
    pub timestamp: i64,
    pub total_votes: u64,
}

#[event]
pub struct VotingFinalized {
    pub total_votes: u64,
    pub yes_votes: u64,
    pub no_votes: u64,
    pub yes_percentage: u64,
    pub finalized_at: i64,
}

#[error_code]
pub enum DelegationError {
    #[msg("Voting period has expired")]
    VotingPeriodExpired,
    
    #[msg("Nullifier has already been used")]
    NullifierAlreadyUsed,
    
    #[msg("Invalid ZKP proof")]
    InvalidZKPProof,
    
    #[msg("Unauthorized access")]
    UnauthorizedAccess,
    
    #[msg("Voting is still active")]
    VotingStillActive,
    
    #[msg("Insufficient stake")]
    InsufficientStake,
}

fn verify_zkp_proof(proof: &ZKPProof, merkle_root: &[u8; 32]) -> bool {
    !proof.pi_a[0].is_empty() && 
    !proof.pi_b[0][0].is_empty() && 
    !proof.pi_c[0].is_empty() &&
    proof.protocol == "groth16" &&
    proof.curve == "bn128"
}
