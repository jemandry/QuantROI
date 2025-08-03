
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
pub enum AuditInstruction {
    StoreAudit {
        root: String,
        ipfs_hash: String,
        ticker: String,
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
        }
    }
}
