use solana_client::rpc_client::RpcClient;
use solana_sdk::{
    commitment_config::CommitmentConfig,
    pubkey::Pubkey,
    signature::{Keypair, Signature},
    transaction::Transaction,
};
use std::str::FromStr;

use crate::error::ApiError;

pub struct SolanaClientService {
    client: RpcClient,
    commitment: CommitmentConfig,
}

impl SolanaClientService {
    pub async fn new() -> Result<Self, ApiError> {
        let rpc_url = std::env::var("SOLANA_RPC_URL")
            .unwrap_or_else(|_| "https://api.devnet.solana.com".to_string());
        
        let client = RpcClient::new_with_commitment(rpc_url, CommitmentConfig::confirmed());
        
        Ok(Self {
            client,
            commitment: CommitmentConfig::confirmed(),
        })
    }

    pub async fn send_transaction(&self, transaction: &Transaction) -> Result<Signature, ApiError> {
        self.client
            .send_and_confirm_transaction(transaction)
            .map_err(|e| ApiError::SolanaTransactionFailed(format!("Transaction failed: {}", e)))
    }

    pub async fn get_account_balance(&self, pubkey: &Pubkey) -> Result<u64, ApiError> {
        self.client
            .get_balance(pubkey)
            .map_err(|e| ApiError::SolanaTransactionFailed(format!("Failed to get balance: {}", e)))
    }

    pub async fn get_program_accounts(&self, program_id: &Pubkey) -> Result<Vec<(Pubkey, solana_sdk::account::Account)>, ApiError> {
        self.client
            .get_program_accounts(program_id)
            .map_err(|e| ApiError::SolanaTransactionFailed(format!("Failed to get program accounts: {}", e)))
    }

    pub fn get_payment_system_program_id(&self) -> Result<Pubkey, ApiError> {
        Pubkey::from_str("PaymentSystemProgram11111111111111111111")
            .map_err(|e| ApiError::InternalServerError(format!("Invalid program ID: {}", e)))
    }

    pub fn get_delegation_management_program_id(&self) -> Result<Pubkey, ApiError> {
        Pubkey::from_str("DeLegationManagementProgram11111111111111111")
            .map_err(|e| ApiError::InternalServerError(format!("Invalid program ID: {}", e)))
    }

    pub fn get_nft_marketplace_program_id(&self) -> Result<Pubkey, ApiError> {
        Pubkey::from_str("NFTMarketplaceProgram1111111111111111111111")
            .map_err(|e| ApiError::InternalServerError(format!("Invalid program ID: {}", e)))
    }

    pub fn get_ai_competition_program_id(&self) -> Result<Pubkey, ApiError> {
        Pubkey::from_str("AiCompetitionProgram111111111111111111111")
            .map_err(|e| ApiError::InternalServerError(format!("Invalid program ID: {}", e)))
    }

    pub fn get_knowledge_verification_program_id(&self) -> Result<Pubkey, ApiError> {
        Pubkey::from_str("KnowledgeVerificationProgram1111111111111")
            .map_err(|e| ApiError::InternalServerError(format!("Invalid program ID: {}", e)))
    }
}
