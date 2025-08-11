use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};
use sha3::{Digest, Sha3_256};

#[derive(Debug, Clone)]
pub struct MoneyDisbursementSystem {
    pending_disbursements: Arc<RwLock<HashMap<String, DisbursementRequest>>>,
    completed_disbursements: Arc<RwLock<HashMap<String, CompletedDisbursement>>>,
    inspector_system: Arc<crate::inspector_verification_system::InspectorVerificationSystem>,
    #[allow(dead_code)]
    wealth_engine: Arc<crate::wealth_engine::TradingWealthEngine>,
    solana_integration: Arc<crate::solana_event_logger::SolanaEventLogger>,
    verification_thresholds: DisbursementThresholds,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DisbursementRequest {
    pub disbursement_id: String,
    pub requester_id: String,
    pub recipient_id: String,
    pub amount: u64,
    pub disbursement_type: DisbursementType,
    pub verification_required: bool,
    pub inspector_verification_id: Option<String>,
    pub cryptographic_hash: String,
    pub status: DisbursementStatus,
    pub priority: DisbursementPriority,
    pub created_at: DateTime<Utc>,
    pub approved_at: Option<DateTime<Utc>>,
    pub executed_at: Option<DateTime<Utc>>,
    pub metadata: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompletedDisbursement {
    pub disbursement_id: String,
    pub original_request: DisbursementRequest,
    pub execution_hash: String,
    pub transaction_signature: Option<String>,
    pub inspector_approval: Option<String>,
    pub execution_timestamp: DateTime<Utc>,
    pub final_amount: u64,
    pub fees_deducted: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DisbursementType {
    TradingProfit,
    DelegationReward,
    ComplianceBonus,
    InspectorFee,
    SystemMaintenance,
    GovernanceReward,
    StakingReward,
    ReferralBonus,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum DisbursementStatus {
    Pending,
    AwaitingVerification,
    Verified,
    Approved,
    Executing,
    Completed,
    Rejected,
    Failed,
    Cancelled,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DisbursementPriority {
    Low,
    Medium,
    High,
    Critical,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DisbursementThresholds {
    pub auto_approve_limit: u64,
    pub inspector_required_limit: u64,
    pub multi_inspector_limit: u64,
    pub board_approval_limit: u64,
}

impl Default for DisbursementThresholds {
    fn default() -> Self {
        Self {
            auto_approve_limit: 10_000,
            inspector_required_limit: 100_000,
            multi_inspector_limit: 1_000_000,
            board_approval_limit: 10_000_000,
        }
    }
}

impl MoneyDisbursementSystem {
    pub async fn new(
        inspector_system: Arc<crate::inspector_verification_system::InspectorVerificationSystem>,
        wealth_engine: Arc<crate::wealth_engine::TradingWealthEngine>,
        solana_integration: Arc<crate::solana_event_logger::SolanaEventLogger>,
    ) -> Self {
        Self {
            pending_disbursements: Arc::new(RwLock::new(HashMap::new())),
            completed_disbursements: Arc::new(RwLock::new(HashMap::new())),
            inspector_system,
            wealth_engine,
            solana_integration,
            verification_thresholds: DisbursementThresholds::default(),
        }
    }

    pub async fn request_disbursement(
        &self,
        mut request: DisbursementRequest,
    ) -> Result<String, Box<dyn std::error::Error + Send + Sync>> {
        let disbursement_id = request.disbursement_id.clone();
        
        let hash_data = format!("{}{}{}{}", 
            request.requester_id, request.recipient_id, request.amount, request.created_at);
        let cryptographic_hash = Sha3_256::digest(hash_data.as_bytes());
        request.cryptographic_hash = hex::encode(cryptographic_hash);

        request.verification_required = self.requires_verification(&request);
        
        if request.verification_required {
            let verification_request = crate::inspector_verification_system::VerificationRequest {
                request_id: format!("verify_{}", disbursement_id),
                request_type: crate::inspector_verification_system::VerificationType::MoneyDisbursement,
                requester_id: request.requester_id.clone(),
                data_hash: request.cryptographic_hash.clone(),
                amount: Some(request.amount),
                inspector_id: None,
                status: crate::inspector_verification_system::VerificationStatus::Pending,
                priority: self.map_disbursement_priority(&request.priority),
                created_at: Utc::now(),
                deadline: Utc::now() + chrono::Duration::hours(24),
                assigned_at: None,
                completed_at: None,
                verification_result: None,
            };
            
            let verification_id = self.inspector_system.submit_verification_request(verification_request).await?;
            request.inspector_verification_id = Some(verification_id);
            request.status = DisbursementStatus::AwaitingVerification;
        } else {
            request.status = DisbursementStatus::Approved;
        }
        
        {
            let mut disbursements = self.pending_disbursements.write().await;
            disbursements.insert(disbursement_id.clone(), request.clone());
        }
        
        self.solana_integration
            .log_money_disbursement(&disbursement_id, request.amount, 
                                  &request.recipient_id, &request.cryptographic_hash)
            .await?;
        
        if !request.verification_required {
            self.execute_disbursement(&disbursement_id).await?;
        }
        
        Ok(disbursement_id)
    }

    pub async fn approve_disbursement(
        &self,
        disbursement_id: &str,
        inspector_approval: String,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let should_execute = {
            let mut disbursements = self.pending_disbursements.write().await;
            if let Some(request) = disbursements.get_mut(disbursement_id) {
                if request.status == DisbursementStatus::AwaitingVerification {
                    request.status = DisbursementStatus::Approved;
                    request.approved_at = Some(Utc::now());
                    request.metadata.insert("inspector_approval".to_string(), inspector_approval);
                    true
                } else {
                    false
                }
            } else {
                false
            }
        };

        if should_execute {
            self.execute_disbursement(disbursement_id).await?;
        }

        Ok(())
    }

    pub async fn execute_disbursement(
        &self,
        disbursement_id: &str,
    ) -> Result<String, Box<dyn std::error::Error + Send + Sync>> {
        let request = {
            let mut disbursements = self.pending_disbursements.write().await;
            if let Some(request) = disbursements.get_mut(disbursement_id) {
                if request.status == DisbursementStatus::Approved {
                    request.status = DisbursementStatus::Executing;
                    request.clone()
                } else {
                    return Err("Disbursement not approved for execution".into());
                }
            } else {
                return Err("Disbursement request not found".into());
            }
        };

        let execution_hash_data = format!("{}{}{}", 
            request.disbursement_id, request.amount, Utc::now());
        let execution_hash = Sha3_256::digest(execution_hash_data.as_bytes());
        let execution_hash_str = hex::encode(execution_hash);

        let fees = self.calculate_fees(&request);
        let final_amount = request.amount.saturating_sub(fees);

        let transaction_signature = self.execute_payment(&request, final_amount).await?;

        let completed_disbursement = CompletedDisbursement {
            disbursement_id: disbursement_id.to_string(),
            original_request: request.clone(),
            execution_hash: execution_hash_str.clone(),
            transaction_signature: Some(transaction_signature.clone()),
            inspector_approval: request.metadata.get("inspector_approval").cloned(),
            execution_timestamp: Utc::now(),
            final_amount,
            fees_deducted: fees,
        };

        {
            let mut completed = self.completed_disbursements.write().await;
            completed.insert(disbursement_id.to_string(), completed_disbursement.clone());
        }

        {
            let mut disbursements = self.pending_disbursements.write().await;
            if let Some(request) = disbursements.get_mut(disbursement_id) {
                request.status = DisbursementStatus::Completed;
                request.executed_at = Some(Utc::now());
            }
        }

        self.solana_integration
            .log_money_disbursement(disbursement_id, final_amount, 
                                  &request.recipient_id, &execution_hash_str)
            .await?;

        Ok(transaction_signature)
    }

    fn requires_verification(&self, request: &DisbursementRequest) -> bool {
        match request.disbursement_type {
            DisbursementType::SystemMaintenance | DisbursementType::InspectorFee => {
                request.amount > self.verification_thresholds.inspector_required_limit
            }
            _ => request.amount > self.verification_thresholds.auto_approve_limit
        }
    }

    fn map_disbursement_priority(&self, priority: &DisbursementPriority) -> crate::inspector_verification_system::VerificationPriority {
        match priority {
            DisbursementPriority::Low => crate::inspector_verification_system::VerificationPriority::Low,
            DisbursementPriority::Medium => crate::inspector_verification_system::VerificationPriority::Medium,
            DisbursementPriority::High => crate::inspector_verification_system::VerificationPriority::High,
            DisbursementPriority::Critical => crate::inspector_verification_system::VerificationPriority::Critical,
        }
    }

    fn calculate_fees(&self, request: &DisbursementRequest) -> u64 {
        let base_fee = match request.disbursement_type {
            DisbursementType::TradingProfit => request.amount / 1000,
            DisbursementType::DelegationReward => request.amount / 2000,
            DisbursementType::ComplianceBonus => 0,
            DisbursementType::InspectorFee => 0,
            DisbursementType::SystemMaintenance => request.amount / 500,
            DisbursementType::GovernanceReward => request.amount / 2000,
            DisbursementType::StakingReward => request.amount / 1000,
            DisbursementType::ReferralBonus => request.amount / 1000,
        };

        let priority_multiplier = match request.priority {
            DisbursementPriority::Critical => 2.0,
            DisbursementPriority::High => 1.5,
            DisbursementPriority::Medium => 1.0,
            DisbursementPriority::Low => 0.8,
        };

        (base_fee as f64 * priority_multiplier) as u64
    }

    async fn execute_payment(
        &self,
        _request: &DisbursementRequest,
        _amount: u64,
    ) -> Result<String, Box<dyn std::error::Error + Send + Sync>> {
        let transaction_signature = format!("tx_sig_{}", uuid::Uuid::new_v4());
        Ok(transaction_signature)
    }

    pub async fn get_disbursement_status(&self, disbursement_id: &str) -> Option<DisbursementStatus> {
        let pending = self.pending_disbursements.read().await;
        if let Some(request) = pending.get(disbursement_id) {
            return Some(request.status.clone());
        }

        let completed = self.completed_disbursements.read().await;
        if completed.contains_key(disbursement_id) {
            return Some(DisbursementStatus::Completed);
        }

        None
    }

    pub async fn get_disbursement_request(&self, disbursement_id: &str) -> Option<DisbursementRequest> {
        let pending = self.pending_disbursements.read().await;
        pending.get(disbursement_id).cloned()
    }

    pub async fn get_completed_disbursement(&self, disbursement_id: &str) -> Option<CompletedDisbursement> {
        let completed = self.completed_disbursements.read().await;
        completed.get(disbursement_id).cloned()
    }

    pub async fn get_pending_disbursements(&self) -> Vec<DisbursementRequest> {
        let pending = self.pending_disbursements.read().await;
        pending.values().cloned().collect()
    }

    pub async fn update_thresholds(&mut self, thresholds: DisbursementThresholds) {
        self.verification_thresholds = thresholds;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::braided_cord_data_engine::BraidedCordDataEngine;

    #[tokio::test]
    async fn test_money_disbursement_system_creation() {
        let braided_engine = Arc::new(BraidedCordDataEngine::new().await);
        let solana_logger = Arc::new(crate::solana_event_logger::SolanaEventLogger::new(braided_engine.clone()).await);
        let wealth_engine = Arc::new(crate::wealth_engine::TradingWealthEngine::new());
        let inspector_system = Arc::new(crate::inspector_verification_system::InspectorVerificationSystem::new(solana_logger.clone(), wealth_engine.clone()).await);
        
        let disbursement_system = MoneyDisbursementSystem::new(inspector_system, wealth_engine, solana_logger).await;
        
        assert!(disbursement_system.pending_disbursements.read().await.is_empty());
        assert!(disbursement_system.completed_disbursements.read().await.is_empty());
    }

    #[tokio::test]
    async fn test_disbursement_request() {
        let braided_engine = Arc::new(BraidedCordDataEngine::new().await);
        let solana_logger = Arc::new(crate::solana_event_logger::SolanaEventLogger::new(braided_engine.clone()).await);
        let wealth_engine = Arc::new(crate::wealth_engine::TradingWealthEngine::new());
        let inspector_system = Arc::new(crate::inspector_verification_system::InspectorVerificationSystem::new(solana_logger.clone(), wealth_engine.clone()).await);
        
        let disbursement_system = MoneyDisbursementSystem::new(inspector_system, wealth_engine, solana_logger).await;

        let request = DisbursementRequest {
            disbursement_id: "disbursement_001".to_string(),
            requester_id: "requester_123".to_string(),
            recipient_id: "recipient_456".to_string(),
            amount: 5000,
            disbursement_type: DisbursementType::TradingProfit,
            verification_required: false,
            inspector_verification_id: None,
            cryptographic_hash: String::new(),
            status: DisbursementStatus::Pending,
            priority: DisbursementPriority::Medium,
            created_at: Utc::now(),
            approved_at: None,
            executed_at: None,
            metadata: HashMap::new(),
        };

        let result = disbursement_system.request_disbursement(request).await;
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), "disbursement_001");

        let status = disbursement_system.get_disbursement_status("disbursement_001").await;
        assert!(status.is_some());
    }
}
