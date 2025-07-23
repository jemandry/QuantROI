use anchor_lang::prelude::*;
use sha3::{Digest, Sha3_256};

declare_id!("RiaComplianceProgram111111111111111111111");

#[program]
pub mod ria_compliance {
    use super::*;

    pub fn register_ria_contract(
        ctx: Context<RegisterRiaContract>,
        contract_id: u64,
        contract_terms_hash: [u8; 32],
        client_pubkey: Pubkey,
        ria_pubkey: Pubkey,
        contract_duration: u32,
    ) -> Result<()> {
        let contract = &mut ctx.accounts.ria_contract;
        let clock = Clock::get()?;
        
        let mut hasher = Sha3_256::new();
        hasher.update(&contract_id.to_le_bytes());
        hasher.update(&contract_terms_hash);
        hasher.update(client_pubkey.as_ref());
        hasher.update(ria_pubkey.as_ref());
        hasher.update(&contract_duration.to_le_bytes());
        hasher.update(&clock.unix_timestamp.to_le_bytes());
        let contract_hash = hasher.finalize();
        
        contract.contract_id = contract_id;
        contract.contract_terms_hash = contract_terms_hash;
        contract.client = client_pubkey;
        contract.ria = ria_pubkey;
        contract.contract_duration = contract_duration;
        contract.created_at = clock.unix_timestamp;
        contract.expires_at = clock.unix_timestamp + contract_duration as i64;
        contract.is_active = true;
        contract.client_signed = false;
        contract.ria_signed = false;
        contract.contract_hash = contract_hash.to_vec();
        contract.compliance_status = ComplianceStatus::Pending;
        
        emit!(RiaContractRegistered {
            contract_id,
            client: client_pubkey,
            ria: ria_pubkey,
            contract_hash: contract_hash.to_vec(),
            expires_at: contract.expires_at,
            timestamp: clock.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn sign_contract_digitally(
        ctx: Context<SignContractDigitally>,
        contract_id: u64,
        signature_data: Vec<u8>,
        signer_type: SignerType,
    ) -> Result<()> {
        let contract = &mut ctx.accounts.ria_contract;
        let clock = Clock::get()?);
        
        require!(contract.is_active, RiaError::ContractInactive);
        require!(clock.unix_timestamp < contract.expires_at, RiaError::ContractExpired);
        
        let mut hasher = Sha3_256::new();
        hasher.update(&contract_id.to_le_bytes());
        hasher.update(&signature_data);
        hasher.update(&(signer_type as u8).to_le_bytes());
        hasher.update(ctx.accounts.signer.key().as_ref());
        hasher.update(&clock.unix_timestamp.to_le_bytes());
        let signature_hash = hasher.finalize();
        
        match signer_type {
            SignerType::Client => {
                require!(ctx.accounts.signer.key() == contract.client, RiaError::UnauthorizedSigner);
                require!(!contract.client_signed, RiaError::AlreadySigned);
                contract.client_signed = true;
                contract.client_signature_hash = Some(signature_hash.to_vec());
                contract.client_signed_at = Some(clock.unix_timestamp);
            },
            SignerType::Ria => {
                require!(ctx.accounts.signer.key() == contract.ria, RiaError::UnauthorizedSigner);
                require!(!contract.ria_signed, RiaError::AlreadySigned);
                contract.ria_signed = true;
                contract.ria_signature_hash = Some(signature_hash.to_vec());
                contract.ria_signed_at = Some(clock.unix_timestamp);
            },
        }
        
        if contract.client_signed && contract.ria_signed {
            contract.compliance_status = ComplianceStatus::Active;
        }
        
        emit!(ContractSigned {
            contract_id,
            signer: ctx.accounts.signer.key(),
            signer_type,
            signature_hash: signature_hash.to_vec(),
            fully_executed: contract.client_signed && contract.ria_signed,
            timestamp: clock.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn verify_compliance_status(
        ctx: Context<VerifyComplianceStatus>,
        contract_id: u64,
        compliance_data: ComplianceData,
    ) -> Result<()> {
        let contract = &mut ctx.accounts.ria_contract;
        let compliance_record = &mut ctx.accounts.compliance_record;
        let clock = Clock::get()?;
        
        require!(contract.is_active, RiaError::ContractInactive);
        
        let mut hasher = Sha3_256::new();
        hasher.update(&contract_id.to_le_bytes());
        hasher.update(&compliance_data.trading_volume.to_le_bytes());
        hasher.update(&compliance_data.risk_score.to_le_bytes());
        hasher.update(&(compliance_data.violations_count as u8).to_le_bytes());
        hasher.update(&clock.unix_timestamp.to_le_bytes());
        let compliance_hash = hasher.finalize();
        
        if compliance_record.contract_id == 0 {
            compliance_record.contract_id = contract_id;
            compliance_record.total_checks = 0;
            compliance_record.violations_found = 0;
            compliance_record.last_check = 0;
        }
        
        compliance_record.total_checks += 1;
        compliance_record.violations_found += compliance_data.violations_count as u32;
        compliance_record.last_check = clock.unix_timestamp;
        compliance_record.last_trading_volume = compliance_data.trading_volume;
        compliance_record.last_risk_score = compliance_data.risk_score;
        compliance_record.compliance_hash = compliance_hash.to_vec();
        
        let violation_rate = compliance_record.violations_found as f64 / compliance_record.total_checks as f64;
        contract.compliance_status = if violation_rate > 0.1 {
            ComplianceStatus::AtRisk
        } else if violation_rate > 0.05 {
            ComplianceStatus::Warning
        } else {
            ComplianceStatus::Active
        };
        
        emit!(ComplianceStatusVerified {
            contract_id,
            compliance_status: contract.compliance_status,
            violations_count: compliance_data.violations_count,
            risk_score: compliance_data.risk_score,
            compliance_hash: compliance_hash.to_vec(),
            timestamp: clock.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn generate_compliance_report(
        ctx: Context<GenerateComplianceReport>,
        contract_id: u64,
        report_period_start: i64,
        report_period_end: i64,
    ) -> Result<()> {
        let contract = &ctx.accounts.ria_contract;
        let compliance_record = &ctx.accounts.compliance_record;
        let report = &mut ctx.accounts.compliance_report;
        let clock = Clock::get()?;
        
        require!(contract.is_active, RiaError::ContractInactive);
        require!(report_period_start < report_period_end, RiaError::InvalidReportPeriod);
        
        let mut hasher = Sha3_256::new();
        hasher.update(&contract_id.to_le_bytes());
        hasher.update(&report_period_start.to_le_bytes());
        hasher.update(&report_period_end.to_le_bytes());
        hasher.update(&compliance_record.total_checks.to_le_bytes());
        hasher.update(&compliance_record.violations_found.to_le_bytes());
        hasher.update(&clock.unix_timestamp.to_le_bytes());
        let report_hash = hasher.finalize();
        
        report.contract_id = contract_id;
        report.report_period_start = report_period_start;
        report.report_period_end = report_period_end;
        report.total_compliance_checks = compliance_record.total_checks;
        report.total_violations = compliance_record.violations_found;
        report.compliance_score = calculate_compliance_score(
            compliance_record.total_checks,
            compliance_record.violations_found,
        );
        report.generated_at = clock.unix_timestamp;
        report.report_hash = report_hash.to_vec();
        
        emit!(ComplianceReportGenerated {
            contract_id,
            report_period_start,
            report_period_end,
            compliance_score: report.compliance_score,
            total_violations: report.total_violations,
            report_hash: report_hash.to_vec(),
            timestamp: clock.unix_timestamp,
        });
        
        Ok(())
    }
}

#[account]
pub struct RiaContract {
    pub contract_id: u64,                      // 8 bytes
    pub contract_terms_hash: [u8; 32],         // 32 bytes
    pub client: Pubkey,                        // 32 bytes
    pub ria: Pubkey,                           // 32 bytes
    pub contract_duration: u32,                // 4 bytes (seconds)
    pub created_at: i64,                       // 8 bytes
    pub expires_at: i64,                       // 8 bytes
    pub is_active: bool,                       // 1 byte
    pub client_signed: bool,                   // 1 byte
    pub ria_signed: bool,                      // 1 byte
    pub client_signature_hash: Option<Vec<u8>>, // 33 bytes (1 + 32)
    pub ria_signature_hash: Option<Vec<u8>>,   // 33 bytes (1 + 32)
    pub client_signed_at: Option<i64>,         // 9 bytes (1 + 8)
    pub ria_signed_at: Option<i64>,            // 9 bytes (1 + 8)
    pub contract_hash: Vec<u8>,                // 32 bytes (SHA-3)
    pub compliance_status: ComplianceStatus,   // 1 byte
}

#[account]
pub struct ComplianceRecord {
    pub contract_id: u64,                      // 8 bytes
    pub total_checks: u32,                     // 4 bytes
    pub violations_found: u32,                 // 4 bytes
    pub last_check: i64,                       // 8 bytes
    pub last_trading_volume: u64,              // 8 bytes
    pub last_risk_score: u8,                   // 1 byte
    pub compliance_hash: Vec<u8>,              // 32 bytes (SHA-3)
}

#[account]
pub struct ComplianceReport {
    pub contract_id: u64,                      // 8 bytes
    pub report_period_start: i64,              // 8 bytes
    pub report_period_end: i64,                // 8 bytes
    pub total_compliance_checks: u32,          // 4 bytes
    pub total_violations: u32,                 // 4 bytes
    pub compliance_score: u8,                  // 1 byte (0-100)
    pub generated_at: i64,                     // 8 bytes
    pub report_hash: Vec<u8>,                  // 32 bytes (SHA-3)
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, PartialEq, Eq)]
pub enum ComplianceStatus {
    Pending,
    Active,
    Warning,
    AtRisk,
    Suspended,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, PartialEq, Eq)]
pub enum SignerType {
    Client,
    Ria,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct ComplianceData {
    pub trading_volume: u64,
    pub risk_score: u8,
    pub violations_count: u16,
}

#[derive(Accounts)]
#[instruction(contract_id: u64)]
pub struct RegisterRiaContract<'info> {
    #[account(
        init,
        payer = authority,
        space = 8 + 8 + 32 + 32 + 32 + 4 + 8 + 8 + 1 + 1 + 1 + 33 + 33 + 9 + 9 + 64 + 1,
        seeds = [b"ria_contract", &contract_id.to_le_bytes()],
        bump
    )]
    pub ria_contract: Account<'info, RiaContract>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(contract_id: u64)]
pub struct SignContractDigitally<'info> {
    #[account(
        mut,
        seeds = [b"ria_contract", &contract_id.to_le_bytes()],
        bump
    )]
    pub ria_contract: Account<'info, RiaContract>,
    pub signer: Signer<'info>,
}

#[derive(Accounts)]
#[instruction(contract_id: u64)]
pub struct VerifyComplianceStatus<'info> {
    #[account(
        mut,
        seeds = [b"ria_contract", &contract_id.to_le_bytes()],
        bump
    )]
    pub ria_contract: Account<'info, RiaContract>,
    #[account(
        init_if_needed,
        payer = authority,
        space = 8 + 8 + 4 + 4 + 8 + 8 + 1 + 64,
        seeds = [b"compliance_record", &contract_id.to_le_bytes()],
        bump
    )]
    pub compliance_record: Account<'info, ComplianceRecord>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(contract_id: u64)]
pub struct GenerateComplianceReport<'info> {
    #[account(
        seeds = [b"ria_contract", &contract_id.to_le_bytes()],
        bump
    )]
    pub ria_contract: Account<'info, RiaContract>,
    #[account(
        seeds = [b"compliance_record", &contract_id.to_le_bytes()],
        bump
    )]
    pub compliance_record: Account<'info, ComplianceRecord>,
    #[account(
        init,
        payer = authority,
        space = 8 + 8 + 8 + 8 + 4 + 4 + 1 + 8 + 64,
        seeds = [b"compliance_report", &contract_id.to_le_bytes(), &Clock::get()?.unix_timestamp.to_le_bytes()],
        bump
    )]
    pub compliance_report: Account<'info, ComplianceReport>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[event]
pub struct RiaContractRegistered {
    pub contract_id: u64,
    pub client: Pubkey,
    pub ria: Pubkey,
    pub contract_hash: Vec<u8>,
    pub expires_at: i64,
    pub timestamp: i64,
}

#[event]
pub struct ContractSigned {
    pub contract_id: u64,
    pub signer: Pubkey,
    pub signer_type: SignerType,
    pub signature_hash: Vec<u8>,
    pub fully_executed: bool,
    pub timestamp: i64,
}

#[event]
pub struct ComplianceStatusVerified {
    pub contract_id: u64,
    pub compliance_status: ComplianceStatus,
    pub violations_count: u16,
    pub risk_score: u8,
    pub compliance_hash: Vec<u8>,
    pub timestamp: i64,
}

#[event]
pub struct ComplianceReportGenerated {
    pub contract_id: u64,
    pub report_period_start: i64,
    pub report_period_end: i64,
    pub compliance_score: u8,
    pub total_violations: u32,
    pub report_hash: Vec<u8>,
    pub timestamp: i64,
}

#[error_code]
pub enum RiaError {
    #[msg("Contract is not active")]
    ContractInactive,
    #[msg("Contract has expired")]
    ContractExpired,
    #[msg("Unauthorized signer")]
    UnauthorizedSigner,
    #[msg("Already signed")]
    AlreadySigned,
    #[msg("Invalid report period")]
    InvalidReportPeriod,
}

fn calculate_compliance_score(total_checks: u32, violations: u32) -> u8 {
    if total_checks == 0 {
        return 100;
    }
    
    let violation_rate = violations as f64 / total_checks as f64;
    let score = ((1.0 - violation_rate) * 100.0).max(0.0).min(100.0) as u8;
    score
}
