use anchor_lang::prelude::*;
use anchor_spl::token::{self, Token, TokenAccount, Transfer};
use std::collections::HashMap;

declare_id!("EnhancedVotingSystem11111111111111111111111111");

#[program]
pub mod enhanced_voting_system {
    use super::*;

    pub fn initialize_voting_system(
        ctx: Context<InitializeVotingSystem>,
        admin_authority: Pubkey,
        min_stake_threshold: u64,
        voting_duration: i64,
    ) -> Result<()> {
        let voting_system = &mut ctx.accounts.voting_system;
        voting_system.admin_authority = admin_authority;
        voting_system.min_stake_threshold = min_stake_threshold;
        voting_system.voting_duration = voting_duration;
        voting_system.total_votes = 0;
        voting_system.created_at = Clock::get()?.unix_timestamp;
        voting_system.is_active = true;
        
        emit!(VotingSystemInitialized {
            admin: admin_authority,
            min_stake: min_stake_threshold,
            duration: voting_duration,
            timestamp: Clock::get()?.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn submit_vote_with_zkp(
        ctx: Context<SubmitVote>,
        vote_content_hash: [u8; 32],
        zkp_proof: ZKPProof,
        source_reliability_score: u64, // 0-1000 (0.000-1.000)
        stake_amount: u64,
        ipfs_hash: String,
    ) -> Result<()> {
        let voting_system = &mut ctx.accounts.voting_system;
        let vote_record = &mut ctx.accounts.vote_record;
        let voter = &ctx.accounts.voter;
        
        require!(voting_system.is_active, VotingError::VotingInactive);
        
        let current_time = Clock::get()?.unix_timestamp;
        require!(
            current_time <= voting_system.created_at + voting_system.voting_duration,
            VotingError::VotingPeriodExpired
        );
        
        require!(
            stake_amount >= voting_system.min_stake_threshold,
            VotingError::InsufficientStake
        );
        
        require!(
            Self::verify_zkp_proof(&zkp_proof, stake_amount, voter.key()),
            VotingError::InvalidZKPProof
        );
        
        require!(
            !Self::is_nullifier_used(&voting_system, &zkp_proof.nullifier),
            VotingError::DuplicateVote
        );
        
        let base_weight = Self::calculate_stake_weight(stake_amount, voting_system.min_stake_threshold);
        let reliability_multiplier = source_reliability_score as f64 / 1000.0;
        let final_vote_weight = (base_weight * reliability_multiplier * 1000.0) as u64;
        
        vote_record.voter = voter.key();
        vote_record.vote_content_hash = vote_content_hash;
        vote_record.zkp_proof_hash = Self::hash_zkp_proof(&zkp_proof);
        vote_record.source_reliability_score = source_reliability_score;
        vote_record.stake_amount = stake_amount;
        vote_record.vote_weight = final_vote_weight;
        vote_record.ipfs_hash = ipfs_hash.clone();
        vote_record.timestamp = current_time;
        vote_record.is_verified = true;
        vote_record.nullifier = zkp_proof.nullifier;
        
        voting_system.total_votes += 1;
        voting_system.total_stake += stake_amount;
        voting_system.total_weight += final_vote_weight;
        
        Self::add_used_nullifier(&mut voting_system, &zkp_proof.nullifier)?;
        
        emit!(VoteSubmitted {
            voter: voter.key(),
            vote_id: vote_record.key(),
            content_hash: vote_content_hash,
            stake_amount,
            vote_weight: final_vote_weight,
            reliability_score: source_reliability_score,
            ipfs_hash,
            zkp_verified: true,
            timestamp: current_time,
        });
        
        Self::check_for_anomalies(&vote_record, current_time)?;
        
        Ok(())
    }

    pub fn update_source_reliability(
        ctx: Context<UpdateSourceReliability>,
        voter_pubkey: Pubkey,
        new_reliability_score: u64,
        accuracy_history: Vec<u64>, // Last 10 accuracy scores (0-1000)
        granger_p_value: u64, // P-value * 10000 for precision
    ) -> Result<()> {
        let reliability_record = &mut ctx.accounts.reliability_record;
        let authority = &ctx.accounts.authority;
        
        require!(
            authority.key() == ctx.accounts.voting_system.admin_authority ||
            Self::is_authorized_updater(&authority.key()),
            VotingError::UnauthorizedReliabilityUpdate
        );
        
        require!(
            new_reliability_score <= 1000,
            VotingError::InvalidReliabilityScore
        );
        
        let accuracy_avg = if accuracy_history.is_empty() {
            500 // Default neutral score
        } else {
            accuracy_history.iter().sum::<u64>() / accuracy_history.len() as u64
        };
        
        let granger_bonus = if granger_p_value < 500 { // p < 0.05
            100 // 10% bonus for statistically significant predictions
        } else if granger_p_value < 1000 { // p < 0.10
            50  // 5% bonus for marginally significant
        } else {
            0   // No bonus
        };
        
        let combined_score = std::cmp::min(
            1000,
            (new_reliability_score * 60 + accuracy_avg * 30 + granger_bonus * 10) / 100
        );
        
        reliability_record.voter = voter_pubkey;
        reliability_record.current_score = combined_score;
        reliability_record.accuracy_history = accuracy_history;
        reliability_record.granger_p_value = granger_p_value;
        reliability_record.last_updated = Clock::get()?.unix_timestamp;
        reliability_record.update_count += 1;
        
        emit!(ReliabilityUpdated {
            voter: voter_pubkey,
            old_score: reliability_record.current_score,
            new_score: combined_score,
            accuracy_avg,
            granger_p_value,
            timestamp: Clock::get()?.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn batch_process_votes(
        ctx: Context<BatchProcessVotes>,
        vote_batch_id: String,
        merkle_root: [u8; 32],
        ipfs_batch_hash: String,
        vote_count: u32,
    ) -> Result<()> {
        let batch_record = &mut ctx.accounts.batch_record;
        let voting_system = &ctx.accounts.voting_system;
        
        require!(
            vote_count <= 1000, // Maximum batch size
            VotingError::BatchTooLarge
        );
        
        batch_record.batch_id = vote_batch_id.clone();
        batch_record.merkle_root = merkle_root;
        batch_record.ipfs_hash = ipfs_batch_hash.clone();
        batch_record.vote_count = vote_count;
        batch_record.processed_at = Clock::get()?.unix_timestamp;
        batch_record.is_verified = true;
        
        emit!(VoteBatchProcessed {
            batch_id: vote_batch_id,
            merkle_root,
            ipfs_hash: ipfs_batch_hash,
            vote_count,
            timestamp: Clock::get()?.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn generate_heatmap_data(
        ctx: Context<GenerateHeatmapData>,
        time_window_hours: u32,
    ) -> Result<HeatmapData> {
        let voting_system = &ctx.accounts.voting_system;
        let current_time = Clock::get()?.unix_timestamp;
        let cutoff_time = current_time - (time_window_hours as i64 * 3600);
        
        let heatmap_data = HeatmapData {
            total_votes: voting_system.total_votes,
            verified_votes: voting_system.total_votes, // Simplified
            pending_votes: 0,
            failed_votes: 0,
            avg_stake: voting_system.total_stake / std::cmp::max(1, voting_system.total_votes as u64),
            avg_reliability: 750, // Would calculate from actual data
            time_window_start: cutoff_time,
            time_window_end: current_time,
            generated_at: current_time,
        };
        
        emit!(HeatmapGenerated {
            time_window_hours,
            total_votes: heatmap_data.total_votes,
            avg_stake: heatmap_data.avg_stake,
            timestamp: current_time,
        });
        
        Ok(heatmap_data)
    }

    pub fn emergency_pause(
        ctx: Context<EmergencyPause>,
        reason: String,
    ) -> Result<()> {
        let voting_system = &mut ctx.accounts.voting_system;
        let authority = &ctx.accounts.authority;
        
        require!(
            authority.key() == voting_system.admin_authority,
            VotingError::UnauthorizedAccess
        );
        
        voting_system.is_active = false;
        voting_system.pause_reason = Some(reason.clone());
        voting_system.paused_at = Some(Clock::get()?.unix_timestamp);
        
        emit!(VotingPaused {
            admin: authority.key(),
            reason,
            timestamp: Clock::get()?.unix_timestamp,
        });
        
        Ok(())
    }

    fn verify_zkp_proof(proof: &ZKPProof, stake_amount: u64, voter: &Pubkey) -> bool {
        proof.stake_commitment != [0u8; 32] && 
        proof.nullifier != [0u8; 32] &&
        stake_amount > 0
    }

    fn calculate_stake_weight(stake_amount: u64, min_threshold: u64) -> f64 {
        let ratio = stake_amount as f64 / min_threshold as f64;
        (ratio.ln() + 1.0).min(3.0) // Cap at 3x weight
    }

    fn hash_zkp_proof(proof: &ZKPProof) -> [u8; 32] {
        use solana_program::keccak;
        let mut data = Vec::new();
        data.extend_from_slice(&proof.stake_commitment);
        data.extend_from_slice(&proof.nullifier);
        data.extend_from_slice(&proof.merkle_root);
        
        let hash = keccak::hash(&data);
        hash.to_bytes()
    }

    fn is_nullifier_used(voting_system: &VotingSystem, nullifier: &[u8; 32]) -> bool {
        voting_system.used_nullifiers.contains(nullifier)
    }

    fn add_used_nullifier(voting_system: &mut VotingSystem, nullifier: &[u8; 32]) -> Result<()> {
        require!(
            voting_system.used_nullifiers.len() < 10000, // Prevent unbounded growth
            VotingError::TooManyNullifiers
        );
        
        voting_system.used_nullifiers.push(*nullifier);
        Ok(())
    }

    fn is_authorized_updater(pubkey: &Pubkey) -> bool {
        true // Simplified for demo
    }

    fn check_for_anomalies(vote_record: &VoteRecord, current_time: i64) -> Result<()> {
        let processing_time = current_time - vote_record.timestamp;
        
        if processing_time > 300 { // 5 minutes
            emit!(AnomalyDetected {
                vote_id: vote_record.key(),
                anomaly_type: "delayed_vote".to_string(),
                severity: "medium".to_string(),
                description: format!("Vote processing took {} seconds", processing_time),
                timestamp: current_time,
            });
        }
        
        Ok(())
    }
}

#[account]
pub struct VotingSystem {
    pub admin_authority: Pubkey,
    pub min_stake_threshold: u64,
    pub voting_duration: i64,
    pub total_votes: u32,
    pub total_stake: u64,
    pub total_weight: u64,
    pub created_at: i64,
    pub is_active: bool,
    pub used_nullifiers: Vec<[u8; 32]>,
    pub pause_reason: Option<String>,
    pub paused_at: Option<i64>,
}

#[account]
pub struct VoteRecord {
    pub voter: Pubkey,
    pub vote_content_hash: [u8; 32],
    pub zkp_proof_hash: [u8; 32],
    pub source_reliability_score: u64,
    pub stake_amount: u64,
    pub vote_weight: u64,
    pub ipfs_hash: String,
    pub timestamp: i64,
    pub is_verified: bool,
    pub nullifier: [u8; 32],
}

#[account]
pub struct SourceReliabilityRecord {
    pub voter: Pubkey,
    pub current_score: u64,
    pub accuracy_history: Vec<u64>,
    pub granger_p_value: u64,
    pub last_updated: i64,
    pub update_count: u32,
}

#[account]
pub struct VoteBatchRecord {
    pub batch_id: String,
    pub merkle_root: [u8; 32],
    pub ipfs_hash: String,
    pub vote_count: u32,
    pub processed_at: i64,
    pub is_verified: bool,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct ZKPProof {
    pub stake_commitment: [u8; 32],
    pub nullifier: [u8; 32],
    pub merkle_root: [u8; 32],
    pub proof_a: [u8; 64],
    pub proof_b: [u8; 128],
    pub proof_c: [u8; 64],
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct HeatmapData {
    pub total_votes: u32,
    pub verified_votes: u32,
    pub pending_votes: u32,
    pub failed_votes: u32,
    pub avg_stake: u64,
    pub avg_reliability: u64,
    pub time_window_start: i64,
    pub time_window_end: i64,
    pub generated_at: i64,
}

#[derive(Accounts)]
pub struct InitializeVotingSystem<'info> {
    #[account(
        init,
        payer = admin,
        space = 8 + 32 + 8 + 8 + 4 + 8 + 8 + 8 + 1 + 4 + 32 * 1000 + 100, // Estimated space
    )]
    pub voting_system: Account<'info, VotingSystem>,
    #[account(mut)]
    pub admin: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct SubmitVote<'info> {
    #[account(mut)]
    pub voting_system: Account<'info, VotingSystem>,
    #[account(
        init,
        payer = voter,
        space = 8 + 32 + 32 + 32 + 8 + 8 + 8 + 100 + 8 + 1 + 32, // Estimated space
    )]
    pub vote_record: Account<'info, VoteRecord>,
    #[account(mut)]
    pub voter: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct UpdateSourceReliability<'info> {
    pub voting_system: Account<'info, VotingSystem>,
    #[account(
        init_if_needed,
        payer = authority,
        space = 8 + 32 + 8 + 4 + 10 * 8 + 8 + 8 + 4, // Estimated space
    )]
    pub reliability_record: Account<'info, SourceReliabilityRecord>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct BatchProcessVotes<'info> {
    pub voting_system: Account<'info, VotingSystem>,
    #[account(
        init,
        payer = processor,
        space = 8 + 100 + 32 + 100 + 4 + 8 + 1, // Estimated space
    )]
    pub batch_record: Account<'info, VoteBatchRecord>,
    #[account(mut)]
    pub processor: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct GenerateHeatmapData<'info> {
    pub voting_system: Account<'info, VotingSystem>,
    pub requester: Signer<'info>,
}

#[derive(Accounts)]
pub struct EmergencyPause<'info> {
    #[account(mut)]
    pub voting_system: Account<'info, VotingSystem>,
    pub authority: Signer<'info>,
}

#[event]
pub struct VotingSystemInitialized {
    pub admin: Pubkey,
    pub min_stake: u64,
    pub duration: i64,
    pub timestamp: i64,
}

#[event]
pub struct VoteSubmitted {
    pub voter: Pubkey,
    pub vote_id: Pubkey,
    pub content_hash: [u8; 32],
    pub stake_amount: u64,
    pub vote_weight: u64,
    pub reliability_score: u64,
    pub ipfs_hash: String,
    pub zkp_verified: bool,
    pub timestamp: i64,
}

#[event]
pub struct ReliabilityUpdated {
    pub voter: Pubkey,
    pub old_score: u64,
    pub new_score: u64,
    pub accuracy_avg: u64,
    pub granger_p_value: u64,
    pub timestamp: i64,
}

#[event]
pub struct VoteBatchProcessed {
    pub batch_id: String,
    pub merkle_root: [u8; 32],
    pub ipfs_hash: String,
    pub vote_count: u32,
    pub timestamp: i64,
}

#[event]
pub struct HeatmapGenerated {
    pub time_window_hours: u32,
    pub total_votes: u32,
    pub avg_stake: u64,
    pub timestamp: i64,
}

#[event]
pub struct VotingPaused {
    pub admin: Pubkey,
    pub reason: String,
    pub timestamp: i64,
}

#[event]
pub struct AnomalyDetected {
    pub vote_id: Pubkey,
    pub anomaly_type: String,
    pub severity: String,
    pub description: String,
    pub timestamp: i64,
}

#[error_code]
pub enum VotingError {
    #[msg("Voting system is not active")]
    VotingInactive,
    #[msg("Voting period has expired")]
    VotingPeriodExpired,
    #[msg("Insufficient stake amount")]
    InsufficientStake,
    #[msg("Invalid ZKP proof")]
    InvalidZKPProof,
    #[msg("Duplicate vote detected")]
    DuplicateVote,
    #[msg("Unauthorized access")]
    UnauthorizedAccess,
    #[msg("Unauthorized reliability update")]
    UnauthorizedReliabilityUpdate,
    #[msg("Invalid reliability score")]
    InvalidReliabilityScore,
    #[msg("Batch size too large")]
    BatchTooLarge,
    #[msg("Too many nullifiers stored")]
    TooManyNullifiers,
}
