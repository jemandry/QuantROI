use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};
use rand::Rng;

#[derive(Debug, Clone)]
pub struct InspectorVerificationSystem {
    active_inspectors: Arc<RwLock<HashMap<String, Inspector>>>,
    verification_requests: Arc<RwLock<HashMap<String, VerificationRequest>>>,
    rotation_schedules: Arc<RwLock<HashMap<String, RotationSchedule>>>,
    solana_integration: Arc<crate::solana_event_logger::SolanaEventLogger>,
    #[allow(dead_code)]
    wealth_engine: Arc<crate::wealth_engine::TradingWealthEngine>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Inspector {
    pub inspector_id: String,
    pub public_key: String,
    pub specializations: Vec<InspectorSpecialization>,
    pub verification_count: u64,
    pub success_rate: f64,
    pub last_active: DateTime<Utc>,
    pub status: InspectorStatus,
    pub workload_capacity: u32,
    pub current_workload: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum InspectorSpecialization {
    TradingCompliance,
    RiskManagement,
    MoneyDisbursement,
    ContractAuditing,
    ZKPVerification,
    GovernanceReview,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum InspectorStatus {
    Active,
    Inactive,
    OnRotation,
    Overloaded,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerificationRequest {
    pub request_id: String,
    pub request_type: VerificationType,
    pub requester_id: String,
    pub data_hash: String,
    pub amount: Option<u64>,
    pub inspector_id: Option<String>,
    pub status: VerificationStatus,
    pub priority: VerificationPriority,
    pub created_at: DateTime<Utc>,
    pub deadline: DateTime<Utc>,
    pub assigned_at: Option<DateTime<Utc>>,
    pub completed_at: Option<DateTime<Utc>>,
    pub verification_result: Option<VerificationResult>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum VerificationType {
    MoneyDisbursement,
    TradingDecision,
    RiskAssessment,
    ComplianceCheck,
    ContractExecution,
    GovernanceProposal,
    ZKPValidation,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum VerificationStatus {
    Pending,
    Assigned,
    InProgress,
    Completed,
    Rejected,
    Expired,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum VerificationPriority {
    Low,
    Medium,
    High,
    Critical,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerificationResult {
    pub approved: bool,
    pub inspector_notes: String,
    pub risk_score: f64,
    pub compliance_flags: Vec<String>,
    pub recommendations: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RotationSchedule {
    pub schedule_id: String,
    pub inspector_pool: Vec<String>,
    pub rotation_frequency: RotationFrequency,
    pub last_rotation: DateTime<Utc>,
    pub next_rotation: DateTime<Utc>,
    pub current_inspector: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RotationFrequency {
    Daily,
    Weekly,
    Monthly,
    OnDemand,
}

impl InspectorVerificationSystem {
    pub async fn new(
        solana_integration: Arc<crate::solana_event_logger::SolanaEventLogger>,
        wealth_engine: Arc<crate::wealth_engine::TradingWealthEngine>,
    ) -> Self {
        Self {
            active_inspectors: Arc::new(RwLock::new(HashMap::new())),
            verification_requests: Arc::new(RwLock::new(HashMap::new())),
            rotation_schedules: Arc::new(RwLock::new(HashMap::new())),
            solana_integration,
            wealth_engine,
        }
    }

    pub async fn register_inspector(
        &self,
        inspector: Inspector,
    ) -> Result<String, Box<dyn std::error::Error + Send + Sync>> {
        let inspector_id = inspector.inspector_id.clone();
        
        {
            let mut inspectors = self.active_inspectors.write().await;
            inspectors.insert(inspector_id.clone(), inspector.clone());
        }

        let _event_id = self.solana_integration
            .log_inspector_verification(&inspector_id, &inspector_id, &serde_json::to_string(&inspector)?)
            .await?;

        Ok(inspector_id)
    }

    pub async fn submit_verification_request(
        &self,
        request: VerificationRequest,
    ) -> Result<String, Box<dyn std::error::Error + Send + Sync>> {
        let request_id = request.request_id.clone();
        
        let assigned_inspector = self.assign_inspector(&request).await?;
        
        let mut updated_request = request;
        updated_request.inspector_id = Some(assigned_inspector.clone());
        updated_request.status = VerificationStatus::Assigned;
        updated_request.assigned_at = Some(Utc::now());

        {
            let mut requests = self.verification_requests.write().await;
            requests.insert(request_id.clone(), updated_request.clone());
        }

        {
            let mut inspectors = self.active_inspectors.write().await;
            if let Some(inspector) = inspectors.get_mut(&assigned_inspector) {
                inspector.current_workload += 1;
                if inspector.current_workload >= inspector.workload_capacity {
                    inspector.status = InspectorStatus::Overloaded;
                }
            }
        }

        let _event_id = self.solana_integration
            .log_inspector_verification(&request_id, &assigned_inspector, &serde_json::to_string(&updated_request)?)
            .await?;

        Ok(request_id)
    }

    pub async fn complete_verification(
        &self,
        request_id: &str,
        result: VerificationResult,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let inspector_id = {
            let mut requests = self.verification_requests.write().await;
            if let Some(request) = requests.get_mut(request_id) {
                request.status = VerificationStatus::Completed;
                request.completed_at = Some(Utc::now());
                request.verification_result = Some(result.clone());
                request.inspector_id.clone()
            } else {
                return Err("Verification request not found".into());
            }
        };

        if let Some(ref inspector_id) = inspector_id {
            let mut inspectors = self.active_inspectors.write().await;
            if let Some(inspector) = inspectors.get_mut(inspector_id) {
                inspector.current_workload = inspector.current_workload.saturating_sub(1);
                inspector.verification_count += 1;
                inspector.last_active = Utc::now();
                
                if inspector.current_workload < inspector.workload_capacity {
                    inspector.status = InspectorStatus::Active;
                }

                let success_rate = if result.approved { 1.0 } else { 0.0 };
                inspector.success_rate = (inspector.success_rate * (inspector.verification_count - 1) as f64 + success_rate) / inspector.verification_count as f64;
            }
        }

        let _event_id = self.solana_integration
            .log_inspector_verification(request_id, &inspector_id.unwrap_or_default(), &serde_json::to_string(&result)?)
            .await?;

        Ok(())
    }

    pub async fn setup_rotation_schedule(
        &self,
        schedule: RotationSchedule,
    ) -> Result<String, Box<dyn std::error::Error + Send + Sync>> {
        let schedule_id = schedule.schedule_id.clone();
        
        {
            let mut schedules = self.rotation_schedules.write().await;
            schedules.insert(schedule_id.clone(), schedule.clone());
        }

        let _event_id = self.solana_integration
            .log_inspector_verification(&schedule_id, "system", &serde_json::to_string(&schedule)?)
            .await?;

        Ok(schedule_id)
    }

    pub async fn execute_rotation(
        &self,
        schedule_id: &str,
    ) -> Result<String, Box<dyn std::error::Error + Send + Sync>> {
        let new_inspector = {
            let mut schedules = self.rotation_schedules.write().await;
            if let Some(schedule) = schedules.get_mut(schedule_id) {
                if schedule.inspector_pool.is_empty() {
                    return Err("No inspectors available for rotation".into());
                }

                let mut rng = rand::thread_rng();
                let new_inspector_idx = rng.gen_range(0..schedule.inspector_pool.len());
                let new_inspector = schedule.inspector_pool[new_inspector_idx].clone();
                
                schedule.current_inspector = Some(new_inspector.clone());
                schedule.last_rotation = Utc::now();
                schedule.next_rotation = self.calculate_next_rotation(&schedule.rotation_frequency);
                
                new_inspector
            } else {
                return Err("Rotation schedule not found".into());
            }
        };

        {
            let mut inspectors = self.active_inspectors.write().await;
            for inspector in inspectors.values_mut() {
                inspector.status = if inspector.inspector_id == new_inspector {
                    InspectorStatus::OnRotation
                } else {
                    InspectorStatus::Active
                };
            }
        }

        let _event_id = self.solana_integration
            .log_inspector_verification(schedule_id, &new_inspector, &format!("Rotation executed, new inspector: {}", new_inspector))
            .await?;

        Ok(new_inspector)
    }

    async fn assign_inspector(
        &self,
        request: &VerificationRequest,
    ) -> Result<String, Box<dyn std::error::Error + Send + Sync>> {
        let inspectors = self.active_inspectors.read().await;
        
        let mut suitable_inspectors: Vec<&Inspector> = inspectors
            .values()
            .filter(|inspector| {
                inspector.status == InspectorStatus::Active &&
                inspector.current_workload < inspector.workload_capacity &&
                self.has_required_specialization(inspector, &request.request_type)
            })
            .collect();

        if suitable_inspectors.is_empty() {
            return Err("No suitable inspectors available".into());
        }

        suitable_inspectors.sort_by(|a, b| {
            let score_a = self.calculate_inspector_score(a, request);
            let score_b = self.calculate_inspector_score(b, request);
            score_b.partial_cmp(&score_a).unwrap_or(std::cmp::Ordering::Equal)
        });

        Ok(suitable_inspectors[0].inspector_id.clone())
    }

    fn has_required_specialization(&self, inspector: &Inspector, verification_type: &VerificationType) -> bool {
        match verification_type {
            VerificationType::MoneyDisbursement => inspector.specializations.contains(&InspectorSpecialization::MoneyDisbursement),
            VerificationType::TradingDecision => inspector.specializations.contains(&InspectorSpecialization::TradingCompliance),
            VerificationType::RiskAssessment => inspector.specializations.contains(&InspectorSpecialization::RiskManagement),
            VerificationType::ComplianceCheck => inspector.specializations.contains(&InspectorSpecialization::TradingCompliance),
            VerificationType::ContractExecution => inspector.specializations.contains(&InspectorSpecialization::ContractAuditing),
            VerificationType::GovernanceProposal => inspector.specializations.contains(&InspectorSpecialization::GovernanceReview),
            VerificationType::ZKPValidation => inspector.specializations.contains(&InspectorSpecialization::ZKPVerification),
        }
    }

    fn calculate_inspector_score(&self, inspector: &Inspector, request: &VerificationRequest) -> f64 {
        let workload_factor = 1.0 - (inspector.current_workload as f64 / inspector.workload_capacity as f64);
        let success_rate_factor = inspector.success_rate;
        let priority_factor = match request.priority {
            VerificationPriority::Critical => 1.0,
            VerificationPriority::High => 0.8,
            VerificationPriority::Medium => 0.6,
            VerificationPriority::Low => 0.4,
        };

        workload_factor * 0.4 + success_rate_factor * 0.4 + priority_factor * 0.2
    }

    fn calculate_next_rotation(&self, frequency: &RotationFrequency) -> DateTime<Utc> {
        let now = Utc::now();
        match frequency {
            RotationFrequency::Daily => now + chrono::Duration::days(1),
            RotationFrequency::Weekly => now + chrono::Duration::weeks(1),
            RotationFrequency::Monthly => now + chrono::Duration::days(30),
            RotationFrequency::OnDemand => now + chrono::Duration::days(365),
        }
    }

    pub async fn get_verification_request(&self, request_id: &str) -> Option<VerificationRequest> {
        let requests = self.verification_requests.read().await;
        requests.get(request_id).cloned()
    }

    pub async fn get_inspector(&self, inspector_id: &str) -> Option<Inspector> {
        let inspectors = self.active_inspectors.read().await;
        inspectors.get(inspector_id).cloned()
    }

    pub async fn get_pending_requests(&self) -> Vec<VerificationRequest> {
        let requests = self.verification_requests.read().await;
        requests.values()
            .filter(|r| matches!(r.status, VerificationStatus::Pending | VerificationStatus::Assigned))
            .cloned()
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::braided_cord_data_engine::BraidedCordDataEngine;

    #[tokio::test]
    async fn test_inspector_verification_system_creation() {
        let braided_engine = Arc::new(BraidedCordDataEngine::new().await);
        let solana_logger = Arc::new(crate::solana_event_logger::SolanaEventLogger::new(braided_engine.clone()).await);
        let wealth_engine = Arc::new(crate::wealth_engine::TradingWealthEngine::new());
        
        let inspector_system = InspectorVerificationSystem::new(solana_logger, wealth_engine).await;
        
        assert!(inspector_system.active_inspectors.read().await.is_empty());
        assert!(inspector_system.verification_requests.read().await.is_empty());
    }

    #[tokio::test]
    async fn test_inspector_registration() {
        let braided_engine = Arc::new(BraidedCordDataEngine::new().await);
        let solana_logger = Arc::new(crate::solana_event_logger::SolanaEventLogger::new(braided_engine.clone()).await);
        let wealth_engine = Arc::new(crate::wealth_engine::TradingWealthEngine::new());
        
        let inspector_system = InspectorVerificationSystem::new(solana_logger, wealth_engine).await;

        let inspector = Inspector {
            inspector_id: "inspector_001".to_string(),
            public_key: "inspector_pubkey_123".to_string(),
            specializations: vec![InspectorSpecialization::MoneyDisbursement, InspectorSpecialization::TradingCompliance],
            verification_count: 0,
            success_rate: 0.0,
            last_active: Utc::now(),
            status: InspectorStatus::Active,
            workload_capacity: 10,
            current_workload: 0,
        };

        let result = inspector_system.register_inspector(inspector).await;
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), "inspector_001");

        let stored_inspector = inspector_system.get_inspector("inspector_001").await;
        assert!(stored_inspector.is_some());
        assert_eq!(stored_inspector.unwrap().workload_capacity, 10);
    }
}
