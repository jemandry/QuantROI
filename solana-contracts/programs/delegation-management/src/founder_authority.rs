
use anchor_lang::prelude::*;
use crate::{AuthorityLevel, DelegationType, DelegationError, RoleType};

#[account]
pub struct FounderAuthority {
    pub founder: Pubkey,
    pub company_name: String,
    pub established_at: i64,
    pub board_members: Vec<Pubkey>,
    pub cto: Option<Pubkey>,
    pub ceo: Option<Pubkey>,
    pub delegation_guidelines: DelegationGuidelines,
    pub is_active: bool,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct DelegationGuidelines {
    pub max_board_delegations: u8,
    pub max_cto_delegations: u8,
    pub max_ceo_delegations: u8,
    pub require_founder_approval: bool,
    pub auto_approve_threshold: f64,
    pub risk_limits: RiskLimits,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct RiskLimits {
    pub max_portfolio_risk: f64,
    pub max_single_trade_size: f64,
    pub max_daily_trades: u32,
    pub require_multi_sig: bool,
}

impl Default for DelegationGuidelines {
    fn default() -> Self {
        Self {
            max_board_delegations: 5,
            max_cto_delegations: 10,
            max_ceo_delegations: 15,
            require_founder_approval: true,
            auto_approve_threshold: 0.95,
            risk_limits: RiskLimits {
                max_portfolio_risk: 0.15,
                max_single_trade_size: 0.05,
                max_daily_trades: 100,
                require_multi_sig: true,
            },
        }
    }
}

pub fn initialize_founder_authority(
    ctx: Context<InitializeFounderAuthority>,
    company_name: String,
    delegation_guidelines: Option<DelegationGuidelines>,
) -> Result<()> {
    let founder_authority = &mut ctx.accounts.founder_authority;
    let clock = Clock::get()?;

    founder_authority.founder = ctx.accounts.founder.key();
    founder_authority.company_name = company_name;
    founder_authority.established_at = clock.unix_timestamp;
    founder_authority.board_members = Vec::new();
    founder_authority.cto = None;
    founder_authority.ceo = None;
    founder_authority.delegation_guidelines = delegation_guidelines.unwrap_or_default();
    founder_authority.is_active = true;

    emit!(FounderAuthorityInitialized {
        founder: founder_authority.founder,
        company_name: founder_authority.company_name.clone(),
        established_at: founder_authority.established_at,
    });

    Ok(())
}

pub fn add_board_member(
    ctx: Context<AddBoardMember>,
    board_member: Pubkey,
) -> Result<()> {
    let founder_authority = &mut ctx.accounts.founder_authority;
    
    require!(
        ctx.accounts.founder.key() == founder_authority.founder,
        DelegationError::UnauthorizedAccess
    );

    require!(
        founder_authority.board_members.len() < founder_authority.delegation_guidelines.max_board_delegations as usize,
        DelegationError::InvalidDelegationType
    );

    founder_authority.board_members.push(board_member);

    emit!(BoardMemberAdded {
        founder: founder_authority.founder,
        board_member,
        total_board_members: founder_authority.board_members.len() as u8,
    });

    Ok(())
}

pub fn set_cto(
    ctx: Context<SetCTO>,
    cto: Pubkey,
) -> Result<()> {
    let founder_authority = &mut ctx.accounts.founder_authority;
    
    require!(
        ctx.accounts.founder.key() == founder_authority.founder,
        DelegationError::UnauthorizedAccess
    );

    founder_authority.cto = Some(cto);

    emit!(CTOSet {
        founder: founder_authority.founder,
        cto,
    });

    Ok(())
}

pub fn set_ceo(
    ctx: Context<SetCEO>,
    ceo: Pubkey,
) -> Result<()> {
    let founder_authority = &mut ctx.accounts.founder_authority;
    
    require!(
        ctx.accounts.founder.key() == founder_authority.founder,
        DelegationError::UnauthorizedAccess
    );

    founder_authority.ceo = Some(ceo);

    emit!(CEOSet {
        founder: founder_authority.founder,
        ceo,
    });

    Ok(())
}

pub fn update_delegation_guidelines(
    ctx: Context<UpdateDelegationGuidelines>,
    new_guidelines: DelegationGuidelines,
) -> Result<()> {
    let founder_authority = &mut ctx.accounts.founder_authority;
    
    require!(
        ctx.accounts.founder.key() == founder_authority.founder,
        DelegationError::UnauthorizedAccess
    );

    founder_authority.delegation_guidelines = new_guidelines;

    emit!(DelegationGuidelinesUpdated {
        founder: founder_authority.founder,
        max_board_delegations: founder_authority.delegation_guidelines.max_board_delegations,
        max_cto_delegations: founder_authority.delegation_guidelines.max_cto_delegations,
        max_ceo_delegations: founder_authority.delegation_guidelines.max_ceo_delegations,
    });

    Ok(())
}

pub fn validate_hierarchical_authority(
    founder_authority: &FounderAuthority,
    authority: &Pubkey,
    authority_level: &AuthorityLevel,
    delegation_type: &DelegationType,
) -> Result<bool> {
    if !founder_authority.is_active {
        return Ok(false);
    }

    match authority_level {
        AuthorityLevel::Founder => {
            Ok(*authority == founder_authority.founder)
        }
        AuthorityLevel::BoardMember => {
            let is_board_member = founder_authority.board_members.contains(authority);
            let valid_delegation = matches!(
                delegation_type,
                DelegationType::BoardToCTO | DelegationType::AITrading | DelegationType::RiskManagement
            );
            Ok(is_board_member && valid_delegation)
        }
        AuthorityLevel::CTO => {
            let is_cto = founder_authority.cto == Some(*authority);
            let valid_delegation = matches!(
                delegation_type,
                DelegationType::ComplianceMonitoring | DelegationType::AITrading
            );
            Ok(is_cto && valid_delegation)
        }
        AuthorityLevel::CEO => {
            let is_ceo = founder_authority.ceo == Some(*authority);
            let valid_delegation = matches!(
                delegation_type,
                DelegationType::CEOToAssistant | DelegationType::PortfolioRebalancing
            );
            Ok(is_ceo && valid_delegation)
        }
        _ => Ok(false),
    }
}

pub fn validate_role_authority(
    founder_authority: &FounderAuthority,
    authority: &Pubkey,
    role: &RoleType,
) -> Result<bool> {
    if !founder_authority.is_active {
        return Ok(false);
    }

    match role {
        RoleType::Board => {
            Ok(*authority == founder_authority.founder)
        }
        RoleType::CTO => {
            Ok(founder_authority.board_members.contains(authority))
        }
    }
}

#[derive(Accounts)]
pub struct InitializeFounderAuthority<'info> {
    #[account(init, payer = founder, space = 8 + 1000)]
    pub founder_authority: Account<'info, FounderAuthority>,
    #[account(mut)]
    pub founder: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct AddBoardMember<'info> {
    #[account(mut)]
    pub founder_authority: Account<'info, FounderAuthority>,
    pub founder: Signer<'info>,
}

#[derive(Accounts)]
pub struct SetCTO<'info> {
    #[account(mut)]
    pub founder_authority: Account<'info, FounderAuthority>,
    pub founder: Signer<'info>,
}

#[derive(Accounts)]
pub struct SetCEO<'info> {
    #[account(mut)]
    pub founder_authority: Account<'info, FounderAuthority>,
    pub founder: Signer<'info>,
}

#[derive(Accounts)]
pub struct UpdateDelegationGuidelines<'info> {
    #[account(mut)]
    pub founder_authority: Account<'info, FounderAuthority>,
    pub founder: Signer<'info>,
}

#[event]
pub struct FounderAuthorityInitialized {
    pub founder: Pubkey,
    pub company_name: String,
    pub established_at: i64,
}

#[event]
pub struct BoardMemberAdded {
    pub founder: Pubkey,
    pub board_member: Pubkey,
    pub total_board_members: u8,
}

#[event]
pub struct CTOSet {
    pub founder: Pubkey,
    pub cto: Pubkey,
}

#[event]
pub struct CEOSet {
    pub founder: Pubkey,
    pub ceo: Pubkey,
}

#[event]
pub struct DelegationGuidelinesUpdated {
    pub founder: Pubkey,
    pub max_board_delegations: u8,
    pub max_cto_delegations: u8,
    pub max_ceo_delegations: u8,
}
