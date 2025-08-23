
use solana_program::{
    account_info::{next_account_info, AccountInfo},
    entrypoint,
    entrypoint::ProgramResult,
    msg,
    program_error::ProgramError,
    pubkey::Pubkey,
    rent::Rent,
    sysvar::Sysvar,
    system_instruction,
    program::invoke,
    clock::Clock,
};
use borsh::{BorshDeserialize, BorshSerialize};

#[derive(BorshSerialize, BorshDeserialize, Debug)]
pub struct AuditLog {
    pub root: String,
    pub ipfs_hash: String,
    pub timestamp: i64,
    pub ticker: String,
    pub authority: Pubkey,
}

#[derive(BorshSerialize, BorshDeserialize, Debug)]
pub struct TradeAudit {
    pub root: String,
    pub ipfs_hash: String,
    pub causal_hypothesis: String,
    pub confidence: u8,
    pub confounders: Vec<String>,
    pub timestamp: i64,
    pub ticker: String,
    pub authority: Pubkey,
    pub trade_type: String,
    pub strike_price: f64,
    pub implied_volatility: f64,
    pub open_interest: u64,
}

#[derive(BorshSerialize, BorshDeserialize, Debug)]
pub enum AuditInstruction {
    StoreAudit {
        root: String,
        ipfs_hash: String,
        ticker: String,
    },
    StoreTradeAudit {
        root: String,
        ipfs_hash: String,
        causal_hypothesis: String,
        confidence: u8,
        confounders: Vec<String>,
        ticker: String,
        trade_type: String,
        strike_price: f64,
        implied_volatility: f64,
        open_interest: u64,
    },
}

entrypoint!(process_instruction);

pub fn process_instruction(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    instruction_data: &[u8],
) -> ProgramResult {
    let instruction = AuditInstruction::try_from_slice(instruction_data)
        .map_err(|_| ProgramError::InvalidInstructionData)?;

    match instruction {
        AuditInstruction::StoreAudit { root, ipfs_hash, ticker } => {
            store_audit(program_id, accounts, root, ipfs_hash, ticker)
        }
        AuditInstruction::StoreTradeAudit { 
            root, 
            ipfs_hash, 
            causal_hypothesis, 
            confidence, 
            confounders, 
            ticker, 
            trade_type, 
            strike_price, 
            implied_volatility, 
            open_interest 
        } => {
            store_trade_audit(
                program_id, 
                accounts, 
                root, 
                ipfs_hash, 
                causal_hypothesis, 
                confidence, 
                confounders, 
                ticker, 
                trade_type, 
                strike_price, 
                implied_volatility, 
                open_interest
            )
        }
    }
}

fn store_audit(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    root: String,
    ipfs_hash: String,
    ticker: String,
) -> ProgramResult {
    let account_info_iter = &mut accounts.iter();
    let authority = next_account_info(account_info_iter)?;
    let audit_account = next_account_info(account_info_iter)?;
    let system_program = next_account_info(account_info_iter)?;

    if !authority.is_signer {
        return Err(ProgramError::MissingRequiredSignature);
    }

    if root.len() != 64 {
        msg!("Invalid root hash length: expected 64 characters");
        return Err(ProgramError::InvalidInstructionData);
    }

    if ipfs_hash.is_empty() {
        msg!("IPFS hash cannot be empty");
        return Err(ProgramError::InvalidInstructionData);
    }

    if ticker.is_empty() || ticker.len() > 10 {
        msg!("Invalid ticker: must be 1-10 characters");
        return Err(ProgramError::InvalidInstructionData);
    }

    let clock = Clock::get()?;
    let timestamp = clock.unix_timestamp;

    let audit_log = AuditLog {
        root: root.clone(),
        ipfs_hash: ipfs_hash.clone(),
        timestamp,
        ticker: ticker.clone(),
        authority: *authority.key,
    };

    let audit_log_size = audit_log.try_to_vec()?.len();
    let rent = Rent::get()?;
    let required_lamports = rent.minimum_balance(audit_log_size);

    if audit_account.lamports() == 0 {
        invoke(
            &system_instruction::create_account(
                authority.key,
                audit_account.key,
                required_lamports,
                audit_log_size as u64,
                program_id,
            ),
            &[authority.clone(), audit_account.clone(), system_program.clone()],
        )?;
    }

    audit_log.serialize(&mut &mut audit_account.data.borrow_mut()[..])?;

    msg!(
        "Audit log stored: root={}, ipfs={}, ticker={}, timestamp={}",
        root,
        ipfs_hash,
        ticker,
        timestamp
    );

    Ok(())
}

fn store_trade_audit(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    root: String,
    ipfs_hash: String,
    causal_hypothesis: String,
    confidence: u8,
    confounders: Vec<String>,
    ticker: String,
    trade_type: String,
    strike_price: f64,
    implied_volatility: f64,
    open_interest: u64,
) -> ProgramResult {
    let account_info_iter = &mut accounts.iter();
    let authority = next_account_info(account_info_iter)?;
    let trade_audit_account = next_account_info(account_info_iter)?;
    let system_program = next_account_info(account_info_iter)?;

    if !authority.is_signer {
        return Err(ProgramError::MissingRequiredSignature);
    }

    if confidence < 50 {
        msg!("Invalid claim: Confidence must be >= 50%");
        return Err(ProgramError::InvalidInstructionData);
    }

    if confounders.is_empty() {
        msg!("Invalid claim: Must provide at least one confounder for causal validation");
        return Err(ProgramError::InvalidInstructionData);
    }

    if causal_hypothesis.is_empty() || causal_hypothesis.len() > 500 {
        msg!("Invalid hypothesis: Must be 1-500 characters");
        return Err(ProgramError::InvalidInstructionData);
    }

    if root.len() != 64 {
        msg!("Invalid root hash length: expected 64 characters");
        return Err(ProgramError::InvalidInstructionData);
    }

    if ipfs_hash.is_empty() {
        msg!("IPFS hash cannot be empty");
        return Err(ProgramError::InvalidInstructionData);
    }

    if ticker.is_empty() || ticker.len() > 10 {
        msg!("Invalid ticker: must be 1-10 characters");
        return Err(ProgramError::InvalidInstructionData);
    }

    let clock = Clock::get()?;
    let timestamp = clock.unix_timestamp;

    let trade_audit = TradeAudit {
        root: root.clone(),
        ipfs_hash: ipfs_hash.clone(),
        causal_hypothesis: causal_hypothesis.clone(),
        confidence,
        confounders: confounders.clone(),
        timestamp,
        ticker: ticker.clone(),
        authority: *authority.key,
        trade_type: trade_type.clone(),
        strike_price,
        implied_volatility,
        open_interest,
    };

    let trade_audit_size = trade_audit.try_to_vec()?.len();
    let rent = Rent::get()?;
    let required_lamports = rent.minimum_balance(trade_audit_size);

    if trade_audit_account.lamports() == 0 {
        invoke(
            &system_instruction::create_account(
                authority.key,
                trade_audit_account.key,
                required_lamports,
                trade_audit_size as u64,
                program_id,
            ),
            &[authority.clone(), trade_audit_account.clone(), system_program.clone()],
        )?;
    }

    trade_audit.serialize(&mut &mut trade_audit_account.data.borrow_mut()[..])?;

    msg!(
        "Trade audit stored: hypothesis={}, confidence={}%, confounders={:?}, ticker={}, strike={}, iv={}, oi={}",
        causal_hypothesis,
        confidence,
        confounders,
        ticker,
        strike_price,
        implied_volatility,
        open_interest
    );

    Ok(())
}

#[derive(BorshSerialize, BorshDeserialize, Debug)]
pub struct GovernanceState {
    pub validators: [Pubkey; 3],
    pub required_signatures: u8,
    pub pending_audits: Vec<PendingAudit>,
}

#[derive(BorshSerialize, BorshDeserialize, Debug, Clone)]
pub struct PendingAudit {
    pub audit_id: String,
    pub root: String,
    pub ipfs_hash: String,
    pub signatures: Vec<Pubkey>,
    pub timestamp: i64,
}

#[derive(BorshSerialize, BorshDeserialize, Debug)]
pub enum GovernanceInstruction {
    InitializeGovernance {
        validators: [Pubkey; 3],
    },
    ProposeAudit {
        audit_id: String,
        root: String,
        ipfs_hash: String,
    },
    SignAudit {
        audit_id: String,
    },
    ExecuteAudit {
        audit_id: String,
    },
}

fn initialize_governance(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    validators: [Pubkey; 3],
) -> ProgramResult {
    let account_info_iter = &mut accounts.iter();
    let authority = next_account_info(account_info_iter)?;
    let governance_account = next_account_info(account_info_iter)?;
    let system_program = next_account_info(account_info_iter)?;

    if !authority.is_signer {
        return Err(ProgramError::MissingRequiredSignature);
    }

    let governance_state = GovernanceState {
        validators,
        required_signatures: 2,
        pending_audits: Vec::new(),
    };

    let governance_size = governance_state.try_to_vec()?.len();
    let rent = Rent::get()?;
    let required_lamports = rent.minimum_balance(governance_size);

    if governance_account.lamports() == 0 {
        invoke(
            &system_instruction::create_account(
                authority.key,
                governance_account.key,
                required_lamports,
                governance_size as u64,
                program_id,
            ),
            &[authority.clone(), governance_account.clone(), system_program.clone()],
        )?;
    }

    governance_state.serialize(&mut &mut governance_account.data.borrow_mut()[..])?;

    msg!("Governance initialized with validators: {:?}", validators);
    Ok(())
}

fn propose_audit(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    audit_id: String,
    root: String,
    ipfs_hash: String,
) -> ProgramResult {
    let account_info_iter = &mut accounts.iter();
    let proposer = next_account_info(account_info_iter)?;
    let governance_account = next_account_info(account_info_iter)?;

    if !proposer.is_signer {
        return Err(ProgramError::MissingRequiredSignature);
    }

    let mut governance_state = GovernanceState::try_from_slice(&governance_account.data.borrow())?;

    if !governance_state.validators.contains(proposer.key) {
        return Err(ProgramError::InvalidAccountData);
    }

    let clock = Clock::get()?;
    let pending_audit = PendingAudit {
        audit_id: audit_id.clone(),
        root,
        ipfs_hash,
        signatures: vec![*proposer.key],
        timestamp: clock.unix_timestamp,
    };

    governance_state.pending_audits.push(pending_audit);
    governance_state.serialize(&mut &mut governance_account.data.borrow_mut()[..])?;

    msg!("Audit proposed: {}", audit_id);
    Ok(())
}

fn sign_audit(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    audit_id: String,
) -> ProgramResult {
    let account_info_iter = &mut accounts.iter();
    let signer = next_account_info(account_info_iter)?;
    let governance_account = next_account_info(account_info_iter)?;

    if !signer.is_signer {
        return Err(ProgramError::MissingRequiredSignature);
    }

    let mut governance_state = GovernanceState::try_from_slice(&governance_account.data.borrow())?;

    if !governance_state.validators.contains(signer.key) {
        return Err(ProgramError::InvalidAccountData);
    }

    for audit in &mut governance_state.pending_audits {
        if audit.audit_id == audit_id {
            if !audit.signatures.contains(signer.key) {
                audit.signatures.push(*signer.key);
                msg!("Audit signed by validator: {}", signer.key);
                break;
            }
        }
    }

    governance_state.serialize(&mut &mut governance_account.data.borrow_mut()[..])?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_audit_log_serialization() {
        let audit_log = AuditLog {
            root: "a".repeat(64),
            ipfs_hash: "QmTest123".to_string(),
            timestamp: 1234567890,
            ticker: "AAPL".to_string(),
            authority: Pubkey::default(),
        };

        let serialized = audit_log.try_to_vec().unwrap();
        let deserialized = AuditLog::try_from_slice(&serialized).unwrap();

        assert_eq!(audit_log.root, deserialized.root);
        assert_eq!(audit_log.ipfs_hash, deserialized.ipfs_hash);
        assert_eq!(audit_log.timestamp, deserialized.timestamp);
        assert_eq!(audit_log.ticker, deserialized.ticker);
        assert_eq!(audit_log.authority, deserialized.authority);
    }

    #[test]
    fn test_instruction_serialization() {
        let instruction = AuditInstruction::StoreAudit {
            root: "a".repeat(64),
            ipfs_hash: "QmTest123".to_string(),
            ticker: "AAPL".to_string(),
        };

        let serialized = instruction.try_to_vec().unwrap();
        let deserialized = AuditInstruction::try_from_slice(&serialized).unwrap();

        match deserialized {
            AuditInstruction::StoreAudit { root, ipfs_hash, ticker } => {
                assert_eq!(root, "a".repeat(64));
                assert_eq!(ipfs_hash, "QmTest123");
                assert_eq!(ticker, "AAPL");
            }
            _ => panic!("Wrong instruction type"),
        }
    }

    #[test]
    fn test_trade_audit_serialization() {
        let trade_audit = TradeAudit {
            root: "a".repeat(64),
            ipfs_hash: "QmTest123".to_string(),
            causal_hypothesis: "IV spike causes price move".to_string(),
            confidence: 75,
            confounders: vec!["earnings".to_string(), "market_volatility".to_string()],
            timestamp: 1234567890,
            ticker: "AAPL".to_string(),
            authority: Pubkey::default(),
            trade_type: "call".to_string(),
            strike_price: 150.0,
            implied_volatility: 0.25,
            open_interest: 5000,
        };

        let serialized = trade_audit.try_to_vec().unwrap();
        let deserialized = TradeAudit::try_from_slice(&serialized).unwrap();

        assert_eq!(trade_audit.causal_hypothesis, deserialized.causal_hypothesis);
        assert_eq!(trade_audit.confidence, deserialized.confidence);
        assert_eq!(trade_audit.confounders, deserialized.confounders);
        assert_eq!(trade_audit.strike_price, deserialized.strike_price);
        assert_eq!(trade_audit.implied_volatility, deserialized.implied_volatility);
        assert_eq!(trade_audit.open_interest, deserialized.open_interest);
    }

    #[test]
    fn test_trade_audit_instruction_serialization() {
        let instruction = AuditInstruction::StoreTradeAudit {
            root: "a".repeat(64),
            ipfs_hash: "QmTest123".to_string(),
            causal_hypothesis: "IV spike causes price move".to_string(),
            confidence: 75,
            confounders: vec!["earnings".to_string()],
            ticker: "AAPL".to_string(),
            trade_type: "call".to_string(),
            strike_price: 150.0,
            implied_volatility: 0.25,
            open_interest: 5000,
        };

        let serialized = instruction.try_to_vec().unwrap();
        let deserialized = AuditInstruction::try_from_slice(&serialized).unwrap();

        match deserialized {
            AuditInstruction::StoreTradeAudit { 
                causal_hypothesis, 
                confidence, 
                confounders, 
                strike_price, 
                .. 
            } => {
                assert_eq!(causal_hypothesis, "IV spike causes price move");
                assert_eq!(confidence, 75);
                assert_eq!(confounders, vec!["earnings".to_string()]);
                assert_eq!(strike_price, 150.0);
            }
            _ => panic!("Wrong instruction type"),
        }
    }
}
