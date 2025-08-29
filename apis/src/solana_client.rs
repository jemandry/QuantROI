use solana_client::rpc_client::RpcClient;
use solana_sdk::{
    commitment_config::CommitmentConfig,
    pubkey::Pubkey,
    signature::{Keypair, Signature},
    transaction::Transaction,
};
use std::str::FromStr;

use crate::error::ApiError;
use crate::jito_mev_protection::{JitoMevProtectionService, AtomicTradeBundle};

pub struct SolanaClientService {
    client: RpcClient,
    commitment: CommitmentConfig,
    mev_protection: JitoMevProtectionService,
}

impl SolanaClientService {
    pub async fn new() -> Result<Self, ApiError> {
        let rpc_url = std::env::var("SOLANA_RPC_URL")
            .unwrap_or_else(|_| "https://api.devnet.solana.com".to_string());
        
        let client = RpcClient::new_with_commitment(rpc_url, CommitmentConfig::confirmed());
        let mev_protection = JitoMevProtectionService::new().await?;
        
        Ok(Self {
            client,
            commitment: CommitmentConfig::confirmed(),
            mev_protection,
        })
    }

    pub async fn send_transaction(&self, transaction: &Transaction) -> Result<Signature, ApiError> {
        self.mev_protection.send_private_transaction(transaction).await
    }

    pub async fn send_atomic_bundle(&mut self, bundle: AtomicTradeBundle) -> Result<String, ApiError> {
        self.mev_protection.submit_atomic_bundle(bundle).await
    }

    pub async fn send_transaction_legacy(&self, transaction: &Transaction) -> Result<Signature, ApiError> {
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

    pub async fn optimize_geographic_routing(&mut self) -> Result<(), ApiError> {
        self.mev_protection.switch_to_optimal_endpoint().await
    }

    pub fn get_mev_protection_metrics(&self) -> serde_json::Value {
        let metrics = self.mev_protection.get_performance_metrics();
        let endpoint = self.mev_protection.get_current_endpoint();
        
        serde_json::json!({
            "total_bundles_submitted": metrics.total_bundles_submitted,
            "successful_bundles": metrics.successful_bundles,
            "failed_bundles": metrics.failed_bundles,
            "avg_execution_time_ms": metrics.avg_execution_time_ms,
            "total_tips_paid": metrics.total_tips_paid,
            "mev_protection_rate": metrics.mev_protection_rate,
            "current_endpoint": {
                "region": endpoint.region,
                "url": endpoint.url,
                "is_jito_validator": endpoint.is_jito_validator,
                "latency_ms": endpoint.latency_ms
            },
            "geographic_latencies": metrics.geographic_latencies
        })
    }
}
