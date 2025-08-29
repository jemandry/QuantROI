use anchor_lang::prelude::*;
use crate::{DelegationError};

#[derive(AnchorSerialize, AnchorDeserialize, Clone, PartialEq, Eq)]
pub enum RoleType {
    Board = 0,
    CTO = 1,
}

#[account]
pub struct Config {
    pub founder: Pubkey,
    pub is_initialized: bool,
}

#[account]
pub struct BoardDelegations {
    pub delegates: Vec<Pubkey>,  // Multiple board members
}

#[account]
pub struct Delegation {
    pub delegate: Pubkey,
    pub role: RoleType,
    pub delegated_by: Pubkey,
    pub expiry: Option<u64>,  // Unix timestamp for auto-expiry
}

pub fn initialize(ctx: Context<Initialize>) -> Result<()> {
    let config = &mut ctx.accounts.config;
    require!(!config.is_initialized, DelegationError::AlreadyInitialized);
    config.founder = ctx.accounts.signer.key();
    config.is_initialized = true;
    emit!(Initialized { founder: config.founder });
    Ok(())
}

pub fn delegate_board(ctx: Context<DelegateBoard>, target: Pubkey, expiry: Option<u64>) -> Result<()> {
    let config = &ctx.accounts.config;
    require_keys_eq!(ctx.accounts.signer.key(), config.founder, DelegationError::UnauthorizedAccess);

    let board_delegations = &mut ctx.accounts.board_delegations;
    if !board_delegations.delegates.contains(&target) {
        board_delegations.delegates.push(target);
    }
    let delegation = &mut ctx.accounts.delegation;
    delegation.delegate = target;
    delegation.role = RoleType::Board;
    delegation.delegated_by = ctx.accounts.signer.key();
    delegation.expiry = expiry;
    emit!(Delegated { delegate: target, role: RoleType::Board, expiry });
    Ok(())
}

pub fn delegate_cto(ctx: Context<DelegateCTO>, target: Pubkey, expiry: Option<u64>) -> Result<()> {
    let caller_delegation = &ctx.accounts.caller_delegation;
    require_keys_eq!(ctx.accounts.signer.key(), caller_delegation.delegate, DelegationError::UnauthorizedAccess);
    require_eq!(caller_delegation.role, RoleType::Board, DelegationError::UnauthorizedAccess);

    if let Some(exp) = caller_delegation.expiry {
        let clock = Clock::get()?;
        require!(clock.unix_timestamp < exp as i64, DelegationError::Expired);
    }

    let delegation = &mut ctx.accounts.delegation;
    delegation.delegate = target;
    delegation.role = RoleType::CTO;
    delegation.delegated_by = ctx.accounts.signer.key();
    delegation.expiry = expiry;
    emit!(Delegated { delegate: target, role: RoleType::CTO, expiry });
    Ok(())
}

pub fn revoke_board(ctx: Context<RevokeBoard>, target: Pubkey) -> Result<()> {
    let config = &ctx.accounts.config;
    require_keys_eq!(ctx.accounts.signer.key(), config.founder, DelegationError::UnauthorizedAccess);

    let board_delegations = &mut ctx.accounts.board_delegations;
    if let Some(pos) = board_delegations.delegates.iter().position(|&d| d == target) {
        board_delegations.delegates.swap_remove(pos);
    }
    emit!(Revoked { delegate: target, role: RoleType::Board });
    Ok(())
}

pub fn revoke_cto(ctx: Context<RevokeCTO>, target: Pubkey) -> Result<()> {
    let caller_delegation = &ctx.accounts.caller_delegation;
    require_keys_eq!(ctx.accounts.signer.key(), caller_delegation.delegate, DelegationError::UnauthorizedAccess);
    require_eq!(caller_delegation.role, RoleType::Board, DelegationError::UnauthorizedAccess);

    emit!(Revoked { delegate: target, role: RoleType::CTO });
    Ok(())
}

pub fn is_delegation_expired(delegation: &Delegation) -> Result<bool> {
    if let Some(expiry) = delegation.expiry {
        let clock = Clock::get()?;
        Ok(clock.unix_timestamp >= expiry as i64)
    } else {
        Ok(false)
    }
}

pub fn validate_enhanced_authority(
    config: &Config,
    board_delegations: &BoardDelegations,
    authority: &Pubkey,
    role: &RoleType,
) -> Result<bool> {
    if !config.is_initialized {
        return Ok(false);
    }

    match role {
        RoleType::Board => {
            Ok(*authority == config.founder)
        }
        RoleType::CTO => {
            Ok(board_delegations.delegates.contains(authority))
        }
    }
}

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(mut)]
    pub signer: Signer<'info>,
    #[account(
        init,
        payer = signer,
        space = 8 + 32 + 1,  // discriminator + founder + is_initialized
        seeds = [b"config"],
        bump
    )]
    pub config: Account<'info, Config>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(target: Pubkey)]
pub struct DelegateBoard<'info> {
    #[account(mut)]
    pub signer: Signer<'info>,
    #[account(seeds = [b"config"], bump)]
    pub config: Account<'info, Config>,
    #[account(
        init_if_needed,
        payer = signer,
        space = 8 + 32 * 10 + 32,  // discriminator + vec of delegates (up to 10) + founder
        seeds = [b"board_delegations"],
        bump
    )]
    pub board_delegations: Account<'info, BoardDelegations>,
    #[account(
        init_if_needed,
        payer = signer,
        space = 8 + 32 + 1 + 32 + 8,  // discriminator + delegate + role + delegated_by + expiry (Option<u64>)
        seeds = [b"delegation", target.as_ref()],
        bump
    )]
    pub delegation: Account<'info, Delegation>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(target: Pubkey)]
pub struct DelegateCTO<'info> {
    #[account(mut)]
    pub signer: Signer<'info>,
    #[account(seeds = [b"config"], bump)]
    pub config: Account<'info, Config>,
    #[account(seeds = [b"delegation", signer.key().as_ref()], bump)]
    pub caller_delegation: Account<'info, Delegation>,
    #[account(
        init_if_needed,
        payer = signer,
        space = 8 + 32 + 1 + 32 + 8,
        seeds = [b"delegation", target.as_ref()],
        bump
    )]
    pub delegation: Account<'info, Delegation>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(target: Pubkey)]
pub struct RevokeBoard<'info> {
    #[account(mut)]
    pub signer: Signer<'info>,
    #[account(seeds = [b"config"], bump)]
    pub config: Account<'info, Config>,
    #[account(mut, seeds = [b"board_delegations"], bump)]
    pub board_delegations: Account<'info, BoardDelegations>,
}

#[derive(Accounts)]
#[instruction(target: Pubkey)]
pub struct RevokeCTO<'info> {
    #[account(mut)]
    pub signer: Signer<'info>,
    #[account(seeds = [b"config"], bump)]
    pub config: Account<'info, Config>,
    #[account(seeds = [b"delegation", signer.key().as_ref()], bump)]
    pub caller_delegation: Account<'info, Delegation>,
}

#[event]
pub struct Initialized {
    pub founder: Pubkey,
}

#[event]
pub struct Delegated {
    pub delegate: Pubkey,
    pub role: RoleType,
    pub expiry: Option<u64>,
}

#[event]
pub struct Revoked {
    pub delegate: Pubkey,
    pub role: RoleType,
}
