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
