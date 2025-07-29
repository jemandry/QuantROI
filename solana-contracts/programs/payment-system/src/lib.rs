use anchor_lang::prelude::*;
use anchor_spl::token::{self, Token, TokenAccount, Transfer};
use sha3::{Digest, Sha3_256};

declare_id!("11111111111111111111111111111112");

#[program]
pub mod payment_system {
    use super::*;

    pub fn setup_periodic_payments(
        ctx: Context<SetupPeriodicPayments>,
        payment_id: u64,
        recipient: Pubkey,
        amount: u64,
        frequency: PaymentFrequency,
        start_time: i64,
        end_time: Option<i64>,
    ) -> Result<()> {
        let payment_schedule = &mut ctx.accounts.payment_schedule;
        let clock = Clock::get()?;
        
        require!(amount > 0, PaymentError::InvalidAmount);
        require!(start_time > clock.unix_timestamp, PaymentError::InvalidStartTime);
        
        if let Some(end) = end_time {
            require!(end > start_time, PaymentError::InvalidEndTime);
        }
        
        let mut hasher = Sha3_256::new();
        hasher.update(&payment_id.to_le_bytes());
        hasher.update(ctx.accounts.payer.key().as_ref());
        hasher.update(recipient.as_ref());
        hasher.update(&amount.to_le_bytes());
        hasher.update(&(frequency.clone() as u8).to_le_bytes());
        hasher.update(&start_time.to_le_bytes());
        hasher.update(&clock.unix_timestamp.to_le_bytes());
        let schedule_hash = hasher.finalize();
        
        payment_schedule.payment_id = payment_id;
        payment_schedule.payer = ctx.accounts.payer.key();
        payment_schedule.recipient = recipient;
        payment_schedule.amount = amount;
        payment_schedule.frequency = frequency.clone();
        payment_schedule.start_time = start_time;
        payment_schedule.end_time = end_time;
        payment_schedule.next_payment_due = start_time;
        payment_schedule.total_payments_made = 0;
        payment_schedule.total_amount_paid = 0;
        payment_schedule.is_active = true;
        payment_schedule.created_at = clock.unix_timestamp;
        payment_schedule.schedule_hash = schedule_hash.to_vec();
        
        emit!(PeriodicPaymentSetup {
            payment_id,
            payer: ctx.accounts.payer.key(),
            recipient,
            amount,
            frequency,
            start_time,
            schedule_hash: schedule_hash.to_vec(),
            timestamp: clock.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn execute_smart_withdrawal(
        ctx: Context<ExecuteSmartWithdrawal>,
        payment_id: u64,
        withdrawal_amount: u64,
    ) -> Result<()> {
        let payment_schedule = &mut ctx.accounts.payment_schedule;
        let clock = Clock::get()?;
        
        require!(payment_schedule.is_active, PaymentError::PaymentInactive);
        require!(clock.unix_timestamp >= payment_schedule.next_payment_due, PaymentError::PaymentNotDue);
        require!(withdrawal_amount == payment_schedule.amount, PaymentError::IncorrectAmount);
        
        let transfer_ctx = CpiContext::new(
            ctx.accounts.token_program.to_account_info(),
            Transfer {
                from: ctx.accounts.payer_token_account.to_account_info(),
                to: ctx.accounts.recipient_token_account.to_account_info(),
                authority: ctx.accounts.payer.to_account_info(),
            },
        );
        token::transfer(transfer_ctx, withdrawal_amount)?;
        
        let mut hasher = Sha3_256::new();
        hasher.update(&payment_id.to_le_bytes());
        hasher.update(&withdrawal_amount.to_le_bytes());
        hasher.update(payment_schedule.payer.as_ref());
        hasher.update(payment_schedule.recipient.as_ref());
        hasher.update(&clock.unix_timestamp.to_le_bytes());
        let withdrawal_hash = hasher.finalize();
        
        payment_schedule.total_payments_made += 1;
        payment_schedule.total_amount_paid += withdrawal_amount;
        payment_schedule.last_payment_at = Some(clock.unix_timestamp);
        
        let frequency_seconds = match payment_schedule.frequency {
            PaymentFrequency::Daily => 86400,
            PaymentFrequency::Weekly => 604800,
            PaymentFrequency::Monthly => 2592000, // 30 days
            PaymentFrequency::Quarterly => 7776000, // 90 days
            PaymentFrequency::Yearly => 31536000, // 365 days
        };
        
        payment_schedule.next_payment_due += frequency_seconds;
        
        if let Some(end_time) = payment_schedule.end_time {
            if payment_schedule.next_payment_due > end_time {
                payment_schedule.is_active = false;
            }
        }
        
        emit!(SmartWithdrawalExecuted {
            payment_id,
            payer: payment_schedule.payer,
            recipient: payment_schedule.recipient,
            amount: withdrawal_amount,
            withdrawal_hash: withdrawal_hash.to_vec(),
            next_payment_due: payment_schedule.next_payment_due,
            timestamp: clock.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn process_central_billing(
        ctx: Context<ProcessCentralBilling>,
        billing_id: u64,
        usage_units: u32,
        billing_period_start: i64,
        billing_period_end: i64,
    ) -> Result<()> {
        let billing_record = &mut ctx.accounts.billing_record;
        let clock = Clock::get()?;
        
        require!(usage_units > 0, PaymentError::InvalidUsageUnits);
        require!(billing_period_start < billing_period_end, PaymentError::InvalidBillingPeriod);
        
        let sol_per_unit = 10_000_000; // 0.01 SOL in lamports
        let total_amount = usage_units as u64 * sol_per_unit;
        
        let mut hasher = Sha3_256::new();
        hasher.update(&billing_id.to_le_bytes());
        hasher.update(ctx.accounts.user.key().as_ref());
        hasher.update(&usage_units.to_le_bytes());
        hasher.update(&billing_period_start.to_le_bytes());
        hasher.update(&billing_period_end.to_le_bytes());
        hasher.update(&total_amount.to_le_bytes());
        hasher.update(&clock.unix_timestamp.to_le_bytes());
        let billing_hash = hasher.finalize();
        
        billing_record.billing_id = billing_id;
        billing_record.user = ctx.accounts.user.key();
        billing_record.usage_units = usage_units;
        billing_record.billing_period_start = billing_period_start;
        billing_record.billing_period_end = billing_period_end;
        billing_record.total_amount = total_amount;
        billing_record.is_paid = false;
        billing_record.created_at = clock.unix_timestamp;
        billing_record.billing_hash = billing_hash.to_vec();
        
        emit!(CentralBillingProcessed {
            billing_id,
            user: ctx.accounts.user.key(),
            usage_units,
            total_amount,
            billing_period_start,
            billing_period_end,
            billing_hash: billing_hash.to_vec(),
            timestamp: clock.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn manage_profit_distribution(
        ctx: Context<ManageProfitDistribution>,
        distribution_id: u64,
        total_profit: u64,
        distribution_rules: Vec<DistributionRule>,
    ) -> Result<()> {
        let profit_distribution = &mut ctx.accounts.profit_distribution;
        let clock = Clock::get()?;
        
        require!(total_profit > 0, PaymentError::InvalidProfitAmount);
        require!(!distribution_rules.is_empty(), PaymentError::NoDistributionRules);
        require!(distribution_rules.len() <= 10, PaymentError::TooManyDistributionRules);
        
        let total_percentage: u16 = distribution_rules.iter().map(|rule| rule.percentage).sum();
        require!(total_percentage == 100, PaymentError::InvalidDistributionPercentages);
        
        let mut hasher = Sha3_256::new();
        hasher.update(&distribution_id.to_le_bytes());
        hasher.update(&total_profit.to_le_bytes());
        hasher.update(&clock.unix_timestamp.to_le_bytes());
        for rule in &distribution_rules {
            hasher.update(rule.recipient.as_ref());
            hasher.update(&rule.percentage.to_le_bytes());
        }
        let distribution_hash = hasher.finalize();
        
        profit_distribution.distribution_id = distribution_id;
        profit_distribution.total_profit = total_profit;
        profit_distribution.distribution_rules = distribution_rules.clone();
        profit_distribution.is_executed = false;
        profit_distribution.created_at = clock.unix_timestamp;
        profit_distribution.distribution_hash = distribution_hash.to_vec();
        
        let mut distributions = Vec::new();
        for rule in &distribution_rules {
            let amount = (total_profit * rule.percentage as u64) / 100;
            distributions.push(IndividualDistribution {
                recipient: rule.recipient,
                amount,
                distribution_type: rule.distribution_type,
                is_paid: false,
            });
        }
        profit_distribution.individual_distributions = distributions;
        
        emit!(ProfitDistributionManaged {
            distribution_id,
            total_profit,
            recipient_count: distribution_rules.len() as u8,
            distribution_hash: distribution_hash.to_vec(),
            timestamp: clock.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn handle_limited_time_contracts(
        ctx: Context<HandleLimitedTimeContracts>,
        contract_id: u64,
        contract_duration: u32,
        auto_renewal: bool,
    ) -> Result<()> {
        let limited_contract = &mut ctx.accounts.limited_contract;
        let clock = Clock::get()?;
        
        require!(contract_duration > 0, PaymentError::InvalidContractDuration);
        
        let mut hasher = Sha3_256::new();
        hasher.update(&contract_id.to_le_bytes());
        hasher.update(ctx.accounts.contract_owner.key().as_ref());
        hasher.update(&contract_duration.to_le_bytes());
        hasher.update(&(auto_renewal as u8).to_le_bytes());
        hasher.update(&clock.unix_timestamp.to_le_bytes());
        let contract_hash = hasher.finalize();
        
        limited_contract.contract_id = contract_id;
        limited_contract.owner = ctx.accounts.contract_owner.key();
        limited_contract.contract_duration = contract_duration;
        limited_contract.created_at = clock.unix_timestamp;
        limited_contract.expires_at = clock.unix_timestamp + contract_duration as i64;
        limited_contract.auto_renewal = auto_renewal;
        limited_contract.is_active = true;
        limited_contract.renewal_count = 0;
        limited_contract.contract_hash = contract_hash.to_vec();
        
        emit!(LimitedTimeContractCreated {
            contract_id,
            owner: ctx.accounts.contract_owner.key(),
            expires_at: limited_contract.expires_at,
            auto_renewal,
            contract_hash: contract_hash.to_vec(),
            timestamp: clock.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn process_contract_expiration(
        ctx: Context<ProcessContractExpiration>,
        contract_id: u64,
    ) -> Result<()> {
        let limited_contract = &mut ctx.accounts.limited_contract;
        let clock = Clock::get()?;
        
        require!(limited_contract.is_active, PaymentError::ContractAlreadyExpired);
        
        if clock.unix_timestamp >= limited_contract.expires_at {
            if limited_contract.auto_renewal {
                limited_contract.expires_at = clock.unix_timestamp + limited_contract.contract_duration as i64;
                limited_contract.renewal_count += 1;
                
                emit!(ContractAutoRenewed {
                    contract_id,
                    new_expiry: limited_contract.expires_at,
                    renewal_count: limited_contract.renewal_count,
                    timestamp: clock.unix_timestamp,
                });
            } else {
                limited_contract.is_active = false;
                
                emit!(ContractExpired {
                    contract_id,
                    owner: limited_contract.owner,
                    expired_at: clock.unix_timestamp,
                    timestamp: clock.unix_timestamp,
                });
            }
        }
        
        Ok(())
    }
}

#[account]
pub struct PaymentSchedule {
    pub payment_id: u64,                       // 8 bytes
    pub payer: Pubkey,                         // 32 bytes
    pub recipient: Pubkey,                     // 32 bytes
    pub amount: u64,                           // 8 bytes
    pub frequency: PaymentFrequency,           // 1 byte
    pub start_time: i64,                       // 8 bytes
    pub end_time: Option<i64>,                 // 9 bytes
    pub next_payment_due: i64,                 // 8 bytes
    pub total_payments_made: u32,              // 4 bytes
    pub total_amount_paid: u64,                // 8 bytes
    pub is_active: bool,                       // 1 byte
    pub created_at: i64,                       // 8 bytes
    pub last_payment_at: Option<i64>,          // 9 bytes
    pub schedule_hash: Vec<u8>,                // 32 bytes (SHA-3)
}

#[account]
pub struct BillingRecord {
    pub billing_id: u64,                       // 8 bytes
    pub user: Pubkey,                          // 32 bytes
    pub usage_units: u32,                      // 4 bytes
    pub billing_period_start: i64,             // 8 bytes
    pub billing_period_end: i64,               // 8 bytes
    pub total_amount: u64,                     // 8 bytes (in lamports)
    pub is_paid: bool,                         // 1 byte
    pub created_at: i64,                       // 8 bytes
    pub paid_at: Option<i64>,                  // 9 bytes
    pub billing_hash: Vec<u8>,                 // 32 bytes (SHA-3)
}

#[account]
pub struct ProfitDistribution {
    pub distribution_id: u64,                  // 8 bytes
    pub total_profit: u64,                     // 8 bytes
    pub distribution_rules: Vec<DistributionRule>, // Variable size
    pub individual_distributions: Vec<IndividualDistribution>, // Variable size
    pub is_executed: bool,                     // 1 byte
    pub created_at: i64,                       // 8 bytes
    pub executed_at: Option<i64>,              // 9 bytes
    pub distribution_hash: Vec<u8>,            // 32 bytes (SHA-3)
}

#[account]
pub struct LimitedContract {
    pub contract_id: u64,                      // 8 bytes
    pub owner: Pubkey,                         // 32 bytes
    pub contract_duration: u32,                // 4 bytes (seconds)
    pub created_at: i64,                       // 8 bytes
    pub expires_at: i64,                       // 8 bytes
    pub auto_renewal: bool,                    // 1 byte
    pub is_active: bool,                       // 1 byte
    pub renewal_count: u32,                    // 4 bytes
    pub contract_hash: Vec<u8>,                // 32 bytes (SHA-3)
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq)]
pub enum PaymentFrequency {
    Daily,
    Weekly,
    Monthly,
    Quarterly,
    Yearly,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct DistributionRule {
    pub recipient: Pubkey,
    pub percentage: u16, // 0-100
    pub distribution_type: DistributionType,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct IndividualDistribution {
    pub recipient: Pubkey,
    pub amount: u64,
    pub distribution_type: DistributionType,
    pub is_paid: bool,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq)]
pub enum DistributionType {
    DataSupplier,
    Referral,
    Partner,
    Affiliate,
}

#[derive(Accounts)]
#[instruction(payment_id: u64)]
pub struct SetupPeriodicPayments<'info> {
    #[account(
        init,
        payer = payer,
        space = 8 + 8 + 32 + 32 + 8 + 1 + 8 + 9 + 8 + 4 + 8 + 1 + 8 + 9 + 64,
        seeds = [b"payment_schedule".as_ref(), payment_id.to_le_bytes().as_ref()],
        bump
    )]
    pub payment_schedule: Account<'info, PaymentSchedule>,
    #[account(mut)]
    pub payer: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(payment_id: u64)]
pub struct ExecuteSmartWithdrawal<'info> {
    #[account(
        mut,
        seeds = [b"payment_schedule".as_ref(), payment_id.to_le_bytes().as_ref()],
        bump
    )]
    pub payment_schedule: Account<'info, PaymentSchedule>,
    #[account(mut)]
    pub payer_token_account: Account<'info, TokenAccount>,
    #[account(mut)]
    pub recipient_token_account: Account<'info, TokenAccount>,
    pub payer: Signer<'info>,
    pub token_program: Program<'info, Token>,
}

#[derive(Accounts)]
#[instruction(billing_id: u64)]
pub struct ProcessCentralBilling<'info> {
    #[account(
        init,
        payer = user,
        space = 8 + 8 + 32 + 4 + 8 + 8 + 8 + 1 + 8 + 9 + 64,
        seeds = [b"billing_record".as_ref(), billing_id.to_le_bytes().as_ref()],
        bump
    )]
    pub billing_record: Account<'info, BillingRecord>,
    #[account(mut)]
    pub user: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(distribution_id: u64)]
pub struct ManageProfitDistribution<'info> {
    #[account(
        init,
        payer = authority,
        space = 8 + 8 + 8 + 4 + (10 * 48) + 4 + (10 * 49) + 1 + 8 + 9 + 64, // Max 10 distribution rules
        seeds = [b"profit_distribution".as_ref(), distribution_id.to_le_bytes().as_ref()],
        bump
    )]
    pub profit_distribution: Account<'info, ProfitDistribution>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(contract_id: u64)]
pub struct HandleLimitedTimeContracts<'info> {
    #[account(
        init,
        payer = contract_owner,
        space = 8 + 8 + 32 + 4 + 8 + 8 + 1 + 1 + 4 + 64,
        seeds = [b"limited_contract".as_ref(), contract_id.to_le_bytes().as_ref()],
        bump
    )]
    pub limited_contract: Account<'info, LimitedContract>,
    #[account(mut)]
    pub contract_owner: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(contract_id: u64)]
pub struct ProcessContractExpiration<'info> {
    #[account(
        mut,
        seeds = [b"limited_contract".as_ref(), contract_id.to_le_bytes().as_ref()],
        bump
    )]
    pub limited_contract: Account<'info, LimitedContract>,
    pub authority: Signer<'info>,
}

#[event]
pub struct PeriodicPaymentSetup {
    pub payment_id: u64,
    pub payer: Pubkey,
    pub recipient: Pubkey,
    pub amount: u64,
    pub frequency: PaymentFrequency,
    pub start_time: i64,
    pub schedule_hash: Vec<u8>,
    pub timestamp: i64,
}

#[event]
pub struct SmartWithdrawalExecuted {
    pub payment_id: u64,
    pub payer: Pubkey,
    pub recipient: Pubkey,
    pub amount: u64,
    pub withdrawal_hash: Vec<u8>,
    pub next_payment_due: i64,
    pub timestamp: i64,
}

#[event]
pub struct CentralBillingProcessed {
    pub billing_id: u64,
    pub user: Pubkey,
    pub usage_units: u32,
    pub total_amount: u64,
    pub billing_period_start: i64,
    pub billing_period_end: i64,
    pub billing_hash: Vec<u8>,
    pub timestamp: i64,
}

#[event]
pub struct ProfitDistributionManaged {
    pub distribution_id: u64,
    pub total_profit: u64,
    pub recipient_count: u8,
    pub distribution_hash: Vec<u8>,
    pub timestamp: i64,
}

#[event]
pub struct LimitedTimeContractCreated {
    pub contract_id: u64,
    pub owner: Pubkey,
    pub expires_at: i64,
    pub auto_renewal: bool,
    pub contract_hash: Vec<u8>,
    pub timestamp: i64,
}

#[event]
pub struct ContractAutoRenewed {
    pub contract_id: u64,
    pub new_expiry: i64,
    pub renewal_count: u32,
    pub timestamp: i64,
}

#[event]
pub struct ContractExpired {
    pub contract_id: u64,
    pub owner: Pubkey,
    pub expired_at: i64,
    pub timestamp: i64,
}

#[error_code]
pub enum PaymentError {
    #[msg("Invalid amount")]
    InvalidAmount,
    #[msg("Invalid start time")]
    InvalidStartTime,
    #[msg("Invalid end time")]
    InvalidEndTime,
    #[msg("Payment is not active")]
    PaymentInactive,
    #[msg("Payment not due yet")]
    PaymentNotDue,
    #[msg("Incorrect payment amount")]
    IncorrectAmount,
    #[msg("Invalid usage units")]
    InvalidUsageUnits,
    #[msg("Invalid billing period")]
    InvalidBillingPeriod,
    #[msg("Invalid profit amount")]
    InvalidProfitAmount,
    #[msg("No distribution rules provided")]
    NoDistributionRules,
    #[msg("Too many distribution rules")]
    TooManyDistributionRules,
    #[msg("Invalid distribution percentages")]
    InvalidDistributionPercentages,
    #[msg("Invalid contract duration")]
    InvalidContractDuration,
    #[msg("Contract already expired")]
    ContractAlreadyExpired,
}
