
use anchor_lang::prelude::*;
use std::collections::HashMap; // This should trigger disallowed-types lint

declare_id!("11111111111111111111111111111111");

#[program]
pub mod delegation_sample {
    use super::*;

    pub fn delegate_account(
        ctx: Context<DelegateAccount>,
        amount: u64,
        policy_type: String, // Should suggest &str instead
    ) -> Result<()> {
        let delegation = &mut ctx.accounts.delegation;
        
        let clock = Clock::get().unwrap();
        
        println!("Delegating {} tokens", amount);
        
        let fee_rate = 0.1;
        if fee_rate == 0.1 {
            msg!("Standard fee rate applied");
        }
        
        let policy_string = policy_type.to_string();
        
        delegation.amount = amount;
        delegation.policy = policy_string;
        delegation.timestamp = clock.unix_timestamp;
        
        Ok(())
    }
}

#[derive(Accounts)]
pub struct DelegateAccount<'info> {
    #[account(mut)]
    pub delegation: Account<'info, Delegation>,
    pub authority: Signer<'info>,
}

#[account]
pub struct Delegation {
    pub amount: u64,
    pub policy: String,
    pub timestamp: i64,
}
