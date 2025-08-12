use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DipSwitchBank {
    pub bank_id: String,
    pub bank_name: String,
    pub switch_count: u8,
    pub current_state: Vec<bool>,
    pub bank_type: BankType,
    pub hardware_address: String,
    pub last_modified: DateTime<Utc>,
    pub description: String,
    pub version: u32,
    pub constraints: Vec<SwitchConstraint>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfigurationProfile {
    pub profile_id: String,
    pub profile_name: String,
    pub description: String,
    pub switch_configurations: HashMap<String, Vec<bool>>,
    pub trading_mode: TradingMode,
    pub risk_parameters: RiskParameters,
    pub created_at: DateTime<Utc>,
    pub created_by: String,
    pub version: u32,
    pub profile_questions: Vec<ProfileQuestion>,
    pub constraint_overrides: HashMap<String, Vec<SwitchConstraint>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActiveConfiguration {
    pub configuration_id: String,
    pub profile_id: String,
    pub activated_at: DateTime<Utc>,
    pub activated_by: String,
    pub status: ConfigurationStatus,
    pub verification_hash: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum BankType {
    TradingParameters,
    RiskManagement,
    SystemConfiguration,
    NetworkRouting,
    SecuritySettings,
    PerformanceOptimization,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TradingMode {
    Conservative,
    Moderate,
    Aggressive,
    HighFrequency,
    MarketMaking,
    Arbitrage,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskParameters {
    pub max_position_size: f64,
    pub stop_loss_threshold: f64,
    pub daily_loss_limit: f64,
    pub volatility_threshold: f64,
    pub correlation_limit: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SwitchConstraint {
    pub constraint_id: String,
    pub constraint_type: ConstraintType,
    pub constraint_value: ConstraintValue,
    pub error_message: String,
    pub is_client_configurable: bool,
    pub created_at: DateTime<Utc>,
    pub created_by: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ConstraintType {
    MinConfidenceScore,
    MaxPositionSize,
    RequiredSwitchState,
    MutualExclusion,
    TimeWindow,
    UserPermission,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ConstraintValue {
    Numeric(f64),
    Boolean(bool),
    String(String),
    SwitchIndices(Vec<u8>),
    TimeRange { start: DateTime<Utc>, end: DateTime<Utc> },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProfileQuestion {
    pub question_id: String,
    pub question_text: String,
    pub question_type: QuestionType,
    pub required: bool,
    pub validation_rules: Vec<ValidationRule>,
    pub default_answer: Option<String>,
    pub created_at: DateTime<Utc>,
    pub created_by: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum QuestionType {
    MultipleChoice { options: Vec<String> },
    Numeric { min: Option<f64>, max: Option<f64> },
    Text { max_length: Option<usize> },
    Boolean,
    Scale { min: u8, max: u8 },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationRule {
    pub rule_type: ValidationRuleType,
    pub rule_value: String,
    pub error_message: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ValidationRuleType {
    Range,
    Pattern,
    Required,
    Custom,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VersionHistory {
    pub version_id: String,
    pub entity_id: String,
    pub entity_type: EntityType,
    pub version_number: u32,
    pub changes: Vec<VersionChange>,
    pub created_at: DateTime<Utc>,
    pub created_by: String,
    pub change_reason: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum EntityType {
    SwitchBank,
    ConfigurationProfile,
    Constraint,
    ProfileQuestion,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VersionChange {
    pub field_name: String,
    pub old_value: Option<String>,
    pub new_value: String,
    pub change_type: ChangeType,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ChangeType {
    Added,
    Modified,
    Removed,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ConfigurationStatus {
    Active,
    Inactive,
    Testing,
    Failed,
    Pending,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SwitchChangeEvent {
    pub event_id: String,
    pub bank_id: String,
    pub switch_index: u8,
    pub old_state: bool,
    pub new_state: bool,
    pub changed_by: String,
    pub timestamp: DateTime<Utc>,
    pub reason: String,
}

#[derive(Debug, Clone)]
pub struct DipSwitchSystem {
    switch_banks: Arc<RwLock<HashMap<String, DipSwitchBank>>>,
    configuration_profiles: Arc<RwLock<HashMap<String, ConfigurationProfile>>>,
    active_configurations: Arc<RwLock<HashMap<String, ActiveConfiguration>>>,
    change_history: Arc<RwLock<Vec<SwitchChangeEvent>>>,
    version_history: Arc<RwLock<Vec<VersionHistory>>>,
    solana_integration: Arc<crate::solana_event_logger::SolanaEventLogger>,
}

impl DipSwitchSystem {
    pub async fn new(
        solana_integration: Arc<crate::solana_event_logger::SolanaEventLogger>,
    ) -> Self {
        Self {
            switch_banks: Arc::new(RwLock::new(HashMap::new())),
            configuration_profiles: Arc::new(RwLock::new(HashMap::new())),
            active_configurations: Arc::new(RwLock::new(HashMap::new())),
            change_history: Arc::new(RwLock::new(Vec::new())),
            version_history: Arc::new(RwLock::new(Vec::new())),
            solana_integration,
        }
    }

    pub async fn register_switch_bank(
        &self,
        bank: DipSwitchBank,
    ) -> Result<String, Box<dyn std::error::Error + Send + Sync>> {
        let bank_id = bank.bank_id.clone();
        
        {
            let mut banks = self.switch_banks.write().await;
            banks.insert(bank_id.clone(), bank.clone());
        }

        let _event_id = self.solana_integration
            .log_sip_event(&bank_id, "dip_bank_registered", &serde_json::to_string(&bank)?)
            .await?;

        Ok(bank_id)
    }

    pub async fn set_switch_state(
        &self,
        bank_id: &str,
        switch_index: u8,
        state: bool,
        changed_by: &str,
        reason: &str,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        self.validate_constraints(bank_id, switch_index, state, changed_by).await?;
        
        self.increment_bank_version(bank_id, changed_by, reason).await?;
        
        let old_state = {
            let mut banks = self.switch_banks.write().await;
            if let Some(bank) = banks.get_mut(bank_id) {
                if (switch_index as usize) < bank.current_state.len() {
                    let old_state = bank.current_state[switch_index as usize];
                    bank.current_state[switch_index as usize] = state;
                    bank.last_modified = Utc::now();
                    old_state
                } else {
                    return Err("Switch index out of range".into());
                }
            } else {
                return Err("Switch bank not found".into());
            }
        };

        let change_event = SwitchChangeEvent {
            event_id: format!("change_{}", uuid::Uuid::new_v4()),
            bank_id: bank_id.to_string(),
            switch_index,
            old_state,
            new_state: state,
            changed_by: changed_by.to_string(),
            timestamp: Utc::now(),
            reason: reason.to_string(),
        };

        {
            let mut history = self.change_history.write().await;
            history.push(change_event.clone());
        }

        let _event_id = self.solana_integration
            .log_sip_event(bank_id, "switch_state_changed", &serde_json::to_string(&change_event)?)
            .await?;

        Ok(())
    }

    pub async fn apply_configuration_profile(
        &self,
        profile_id: &str,
        activated_by: &str,
    ) -> Result<String, Box<dyn std::error::Error + Send + Sync>> {
        let configuration_id = format!("config_{}", uuid::Uuid::new_v4());
        
        let profile = {
            let profiles = self.configuration_profiles.read().await;
            profiles.get(profile_id).cloned()
        };
        
        if let Some(profile) = profile {
            for (bank_id, switch_states) in &profile.switch_configurations {
                let mut banks = self.switch_banks.write().await;
                if let Some(bank) = banks.get_mut(bank_id) {
                    bank.current_state = switch_states.clone();
                    bank.last_modified = Utc::now();
                }
            }
            
            let verification_hash = self.generate_configuration_hash(&profile).await;
            
            let active_config = ActiveConfiguration {
                configuration_id: configuration_id.clone(),
                profile_id: profile_id.to_string(),
                activated_at: Utc::now(),
                activated_by: activated_by.to_string(),
                status: ConfigurationStatus::Active,
                verification_hash,
            };
            
            {
                let mut configs = self.active_configurations.write().await;
                configs.insert(configuration_id.clone(), active_config.clone());
            }
            
            let _event_id = self.solana_integration
                .log_sip_event(&configuration_id, "configuration_applied", &serde_json::to_string(&active_config)?)
                .await?;
        }
        
        Ok(configuration_id)
    }

    pub async fn create_configuration_profile(
        &self,
        profile: ConfigurationProfile,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let profile_id = profile.profile_id.clone();
        
        {
            let mut profiles = self.configuration_profiles.write().await;
            profiles.insert(profile_id.clone(), profile.clone());
        }
        
        let _event_id = self.solana_integration
            .log_sip_event(&profile_id, "profile_created", &serde_json::to_string(&profile)?)
            .await?;
        
        Ok(())
    }

    pub async fn get_current_configuration(&self, bank_id: &str) -> Option<Vec<bool>> {
        let banks = self.switch_banks.read().await;
        banks.get(bank_id).map(|bank| bank.current_state.clone())
    }

    pub async fn get_switch_banks(&self) -> HashMap<String, DipSwitchBank> {
        let banks = self.switch_banks.read().await;
        banks.clone()
    }

    pub async fn get_configuration_profiles(&self) -> HashMap<String, ConfigurationProfile> {
        let profiles = self.configuration_profiles.read().await;
        profiles.clone()
    }

    pub async fn get_change_history(&self, bank_id: Option<&str>) -> Vec<SwitchChangeEvent> {
        let history = self.change_history.read().await;
        if let Some(bank_id) = bank_id {
            history.iter()
                .filter(|event| event.bank_id == bank_id)
                .cloned()
                .collect()
        } else {
            history.clone()
        }
    }

    async fn generate_configuration_hash(&self, profile: &ConfigurationProfile) -> String {
        use sha3::{Digest, Sha3_256};
        
        let config_data = format!("{:?}", profile.switch_configurations);
        let mut hasher = Sha3_256::new();
        hasher.update(config_data.as_bytes());
        hex::encode(hasher.finalize())
    }

    pub async fn validate_configuration(
        &self,
        profile_id: &str,
    ) -> Result<bool, Box<dyn std::error::Error + Send + Sync>> {
        let profiles = self.configuration_profiles.read().await;
        let banks = self.switch_banks.read().await;
        
        if let Some(profile) = profiles.get(profile_id) {
            for (bank_id, switch_states) in &profile.switch_configurations {
                if let Some(bank) = banks.get(bank_id) {
                    if switch_states.len() != bank.switch_count as usize {
                        return Ok(false);
                    }
                } else {
                    return Ok(false);
                }
            }
            Ok(true)
        } else {
            Ok(false)
        }
    }

    pub async fn get_bank_status(&self, bank_id: &str) -> Option<DipSwitchBank> {
        let banks = self.switch_banks.read().await;
        banks.get(bank_id).cloned()
    }

    pub async fn reset_bank_to_defaults(
        &self,
        bank_id: &str,
        reset_by: &str,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        {
            let mut banks = self.switch_banks.write().await;
            if let Some(bank) = banks.get_mut(bank_id) {
                let default_state = vec![false; bank.switch_count as usize];
                bank.current_state = default_state;
                bank.last_modified = Utc::now();
            } else {
                return Err("Switch bank not found".into());
            }
        }

        let reset_event = SwitchChangeEvent {
            event_id: format!("reset_{}", uuid::Uuid::new_v4()),
            bank_id: bank_id.to_string(),
            switch_index: 255, // Special value indicating full bank reset
            old_state: true, // Placeholder
            new_state: false, // Placeholder
            changed_by: reset_by.to_string(),
            timestamp: Utc::now(),
            reason: "Bank reset to defaults".to_string(),
        };

        {
            let mut history = self.change_history.write().await;
            history.push(reset_event.clone());
        }

        let _event_id = self.solana_integration
            .log_sip_event(bank_id, "bank_reset", &serde_json::to_string(&reset_event)?)
            .await?;

        Ok(())
    }

    pub async fn validate_constraints(
        &self,
        bank_id: &str,
        switch_index: u8,
        new_state: bool,
        user_id: &str,
    ) -> Result<bool, Box<dyn std::error::Error + Send + Sync>> {
        let banks = self.switch_banks.read().await;
        if let Some(bank) = banks.get(bank_id) {
            for constraint in &bank.constraints {
                match constraint.constraint_type {
                    ConstraintType::RequiredSwitchState => {
                        if let ConstraintValue::Boolean(required_state) = constraint.constraint_value {
                            if new_state != required_state {
                                return Err(constraint.error_message.clone().into());
                            }
                        }
                    },
                    ConstraintType::UserPermission => {
                        if let ConstraintValue::String(required_user) = &constraint.constraint_value {
                            if user_id != required_user {
                                return Err(constraint.error_message.clone().into());
                            }
                        }
                    },
                    ConstraintType::MutualExclusion => {
                        if let ConstraintValue::SwitchIndices(excluded_switches) = &constraint.constraint_value {
                            if new_state && excluded_switches.contains(&switch_index) {
                                return Err(constraint.error_message.clone().into());
                            }
                        }
                    },
                    ConstraintType::TimeWindow => {
                        if let ConstraintValue::TimeRange { start, end } = &constraint.constraint_value {
                            let now = Utc::now();
                            if now < *start || now > *end {
                                return Err(constraint.error_message.clone().into());
                            }
                        }
                    },
                    _ => {} // Handle other constraint types as needed
                }
            }
        }
        Ok(true)
    }

    pub async fn add_constraint(
        &self,
        bank_id: &str,
        constraint: SwitchConstraint,
        user_id: &str,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        self.increment_bank_version(bank_id, user_id, "Added constraint").await?;
        
        {
            let mut banks = self.switch_banks.write().await;
            if let Some(bank) = banks.get_mut(bank_id) {
                bank.constraints.push(constraint.clone());
            }
        }

        self.solana_integration
            .log_sip_event(bank_id, "constraint_added", &serde_json::to_string(&constraint)?)
            .await?;

        Ok(())
    }

    pub async fn update_profile_questions(
        &self,
        profile_id: &str,
        questions: Vec<ProfileQuestion>,
        user_id: &str,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        self.increment_profile_version(profile_id, user_id, "Updated profile questions").await?;
        
        {
            let mut profiles = self.configuration_profiles.write().await;
            if let Some(profile) = profiles.get_mut(profile_id) {
                profile.profile_questions = questions.clone();
            }
        }

        self.solana_integration
            .log_sip_event(profile_id, "profile_questions_updated", &serde_json::to_string(&questions)?)
            .await?;

        Ok(())
    }

    async fn increment_bank_version(
        &self,
        bank_id: &str,
        user_id: &str,
        reason: &str,
    ) -> Result<u32, Box<dyn std::error::Error + Send + Sync>> {
        let new_version = {
            let mut banks = self.switch_banks.write().await;
            if let Some(bank) = banks.get_mut(bank_id) {
                bank.version += 1;
                bank.last_modified = Utc::now();
                bank.version
            } else {
                return Err("Bank not found".into());
            }
        };

        let version_history = VersionHistory {
            version_id: format!("version_{}", uuid::Uuid::new_v4()),
            entity_id: bank_id.to_string(),
            entity_type: EntityType::SwitchBank,
            version_number: new_version,
            changes: vec![], // Would be populated with actual changes in production
            created_at: Utc::now(),
            created_by: user_id.to_string(),
            change_reason: reason.to_string(),
        };

        {
            let mut history = self.version_history.write().await;
            history.push(version_history);
        }

        Ok(new_version)
    }

    async fn increment_profile_version(
        &self,
        profile_id: &str,
        user_id: &str,
        reason: &str,
    ) -> Result<u32, Box<dyn std::error::Error + Send + Sync>> {
        let new_version = {
            let mut profiles = self.configuration_profiles.write().await;
            if let Some(profile) = profiles.get_mut(profile_id) {
                profile.version += 1;
                profile.version
            } else {
                return Err("Profile not found".into());
            }
        };

        let version_history = VersionHistory {
            version_id: format!("version_{}", uuid::Uuid::new_v4()),
            entity_id: profile_id.to_string(),
            entity_type: EntityType::ConfigurationProfile,
            version_number: new_version,
            changes: vec![], // Would be populated with actual changes in production
            created_at: Utc::now(),
            created_by: user_id.to_string(),
            change_reason: reason.to_string(),
        };

        {
            let mut history = self.version_history.write().await;
            history.push(version_history);
        }

        Ok(new_version)
    }

    pub async fn get_version_history(&self, entity_id: &str) -> Vec<VersionHistory> {
        let history = self.version_history.read().await;
        history.iter()
            .filter(|h| h.entity_id == entity_id)
            .cloned()
            .collect()
    }

    pub async fn get_bank_constraints(&self, bank_id: &str) -> Vec<SwitchConstraint> {
        let banks = self.switch_banks.read().await;
        if let Some(bank) = banks.get(bank_id) {
            bank.constraints.clone()
        } else {
            vec![]
        }
    }

    pub async fn get_profile_questions(&self, profile_id: &str) -> Vec<ProfileQuestion> {
        let profiles = self.configuration_profiles.read().await;
        if let Some(profile) = profiles.get(profile_id) {
            profile.profile_questions.clone()
        } else {
            vec![]
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::braided_cord_data_engine::BraidedCordDataEngine;

    #[tokio::test]
    async fn test_dip_switch_system_creation() {
        let braided_engine = Arc::new(BraidedCordDataEngine::new().await);
        let solana_logger = Arc::new(crate::solana_event_logger::SolanaEventLogger::new(braided_engine).await);
        let dip_system = DipSwitchSystem::new(solana_logger).await;
        
        assert!(dip_system.switch_banks.read().await.is_empty());
        assert!(dip_system.configuration_profiles.read().await.is_empty());
    }

    #[tokio::test]
    async fn test_switch_bank_registration() {
        let braided_engine = Arc::new(BraidedCordDataEngine::new().await);
        let solana_logger = Arc::new(crate::solana_event_logger::SolanaEventLogger::new(braided_engine).await);
        let dip_system = DipSwitchSystem::new(solana_logger).await;

        let bank = DipSwitchBank {
            bank_id: "trading_params_1".to_string(),
            bank_name: "Trading Parameters Bank 1".to_string(),
            switch_count: 8,
            current_state: vec![false; 8],
            bank_type: BankType::TradingParameters,
            hardware_address: "0x1000".to_string(),
            last_modified: Utc::now(),
            description: "Main trading parameter configuration".to_string(),
            version: 1,
            constraints: vec![],
        };

        let result = dip_system.register_switch_bank(bank.clone()).await;
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), "trading_params_1");

        let banks = dip_system.switch_banks.read().await;
        assert!(banks.contains_key("trading_params_1"));
    }

    #[tokio::test]
    async fn test_switch_state_change() {
        let braided_engine = Arc::new(BraidedCordDataEngine::new().await);
        let solana_logger = Arc::new(crate::solana_event_logger::SolanaEventLogger::new(braided_engine).await);
        let dip_system = DipSwitchSystem::new(solana_logger).await;

        let bank = DipSwitchBank {
            bank_id: "test_bank".to_string(),
            bank_name: "Test Bank".to_string(),
            switch_count: 4,
            current_state: vec![false; 4],
            bank_type: BankType::TradingParameters,
            hardware_address: "0x2000".to_string(),
            last_modified: Utc::now(),
            description: "Test bank for switch operations".to_string(),
            version: 1,
            constraints: vec![],
        };

        dip_system.register_switch_bank(bank).await.unwrap();

        let result = dip_system.set_switch_state(
            "test_bank",
            2,
            true,
            "test_user",
            "Enable high frequency trading"
        ).await;

        assert!(result.is_ok());

        let current_config = dip_system.get_current_configuration("test_bank").await;
        assert!(current_config.is_some());
        let config = current_config.unwrap();
        assert!(config[2]);
        assert!(!config[0]);
    }

    #[tokio::test]
    async fn test_configuration_profile() {
        let braided_engine = Arc::new(BraidedCordDataEngine::new().await);
        let solana_logger = Arc::new(crate::solana_event_logger::SolanaEventLogger::new(braided_engine).await);
        let dip_system = DipSwitchSystem::new(solana_logger).await;

        let mut switch_configs = HashMap::new();
        switch_configs.insert("bank1".to_string(), vec![true, false, true, false]);

        let profile = ConfigurationProfile {
            profile_id: "aggressive_trading".to_string(),
            profile_name: "Aggressive Trading Mode".to_string(),
            description: "High-risk, high-reward trading configuration".to_string(),
            switch_configurations: switch_configs,
            trading_mode: TradingMode::Aggressive,
            risk_parameters: RiskParameters {
                max_position_size: 1000000.0,
                stop_loss_threshold: 0.05,
                daily_loss_limit: 50000.0,
                volatility_threshold: 0.3,
                correlation_limit: 0.8,
            },
            created_at: Utc::now(),
            created_by: "risk_manager".to_string(),
            version: 1,
            profile_questions: vec![],
            constraint_overrides: HashMap::new(),
        };

        let result = dip_system.create_configuration_profile(profile).await;
        assert!(result.is_ok());

        let profiles = dip_system.get_configuration_profiles().await;
        assert!(profiles.contains_key("aggressive_trading"));
    }

    #[tokio::test]
    async fn test_constraint_validation() {
        let braided_engine = Arc::new(BraidedCordDataEngine::new().await);
        let solana_logger = Arc::new(crate::solana_event_logger::SolanaEventLogger::new(braided_engine).await);
        let dip_system = DipSwitchSystem::new(solana_logger).await;

        let bank = DipSwitchBank {
            bank_id: "test_bank".to_string(),
            bank_name: "Test Bank".to_string(),
            switch_count: 4,
            current_state: vec![false; 4],
            bank_type: BankType::TradingParameters,
            hardware_address: "0x2000".to_string(),
            last_modified: Utc::now(),
            description: "Test bank for constraint validation".to_string(),
            version: 1,
            constraints: vec![
                SwitchConstraint {
                    constraint_id: "required_state".to_string(),
                    constraint_type: ConstraintType::RequiredSwitchState,
                    constraint_value: ConstraintValue::Boolean(true),
                    error_message: "Switch must be enabled".to_string(),
                    is_client_configurable: true,
                    created_at: Utc::now(),
                    created_by: "admin".to_string(),
                }
            ],
        };

        dip_system.register_switch_bank(bank).await.unwrap();

        let result = dip_system.validate_constraints("test_bank", 0, false, "user").await;
        assert!(result.is_err());

        let result = dip_system.validate_constraints("test_bank", 0, true, "user").await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_versioning() {
        let braided_engine = Arc::new(BraidedCordDataEngine::new().await);
        let solana_logger = Arc::new(crate::solana_event_logger::SolanaEventLogger::new(braided_engine).await);
        let dip_system = DipSwitchSystem::new(solana_logger).await;

        let bank = DipSwitchBank {
            bank_id: "version_test".to_string(),
            bank_name: "Version Test Bank".to_string(),
            switch_count: 2,
            current_state: vec![false; 2],
            bank_type: BankType::TradingParameters,
            hardware_address: "0x3000".to_string(),
            last_modified: Utc::now(),
            description: "Bank for version testing".to_string(),
            version: 1,
            constraints: vec![],
        };

        dip_system.register_switch_bank(bank).await.unwrap();

        let initial_version = {
            let banks = dip_system.switch_banks.read().await;
            banks.get("version_test").unwrap().version
        };

        let constraint = SwitchConstraint {
            constraint_id: "test_constraint".to_string(),
            constraint_type: ConstraintType::MinConfidenceScore,
            constraint_value: ConstraintValue::Numeric(80.0),
            error_message: "Test constraint".to_string(),
            is_client_configurable: true,
            created_at: Utc::now(),
            created_by: "admin".to_string(),
        };

        dip_system.add_constraint("version_test", constraint, "admin").await.unwrap();

        let new_version = {
            let banks = dip_system.switch_banks.read().await;
            banks.get("version_test").unwrap().version
        };

        assert_eq!(new_version, initial_version + 1);

        let history = dip_system.get_version_history("version_test").await;
        assert!(!history.is_empty());
    }

    #[tokio::test]
    async fn test_profile_questions() {
        let braided_engine = Arc::new(BraidedCordDataEngine::new().await);
        let solana_logger = Arc::new(crate::solana_event_logger::SolanaEventLogger::new(braided_engine).await);
        let dip_system = DipSwitchSystem::new(solana_logger).await;

        let mut switch_configs = HashMap::new();
        switch_configs.insert("bank1".to_string(), vec![true, false]);

        let profile = ConfigurationProfile {
            profile_id: "test_profile".to_string(),
            profile_name: "Test Profile".to_string(),
            description: "Profile for testing questions".to_string(),
            switch_configurations: switch_configs,
            trading_mode: TradingMode::Conservative,
            risk_parameters: RiskParameters {
                max_position_size: 10000.0,
                stop_loss_threshold: 0.02,
                daily_loss_limit: 1000.0,
                volatility_threshold: 0.1,
                correlation_limit: 0.5,
            },
            created_at: Utc::now(),
            created_by: "test_user".to_string(),
            version: 1,
            profile_questions: vec![],
            constraint_overrides: HashMap::new(),
        };

        dip_system.create_configuration_profile(profile).await.unwrap();

        let questions = vec![
            ProfileQuestion {
                question_id: "risk_tolerance".to_string(),
                question_text: "What is your risk tolerance level?".to_string(),
                question_type: QuestionType::Scale { min: 1, max: 10 },
                required: true,
                validation_rules: vec![
                    ValidationRule {
                        rule_type: ValidationRuleType::Range,
                        rule_value: "1-10".to_string(),
                        error_message: "Risk tolerance must be between 1 and 10".to_string(),
                    }
                ],
                default_answer: Some("5".to_string()),
                created_at: Utc::now(),
                created_by: "system_admin".to_string(),
            }
        ];

        let initial_version = {
            let profiles = dip_system.configuration_profiles.read().await;
            profiles.get("test_profile").unwrap().version
        };

        dip_system.update_profile_questions("test_profile", questions.clone(), "system_admin").await.unwrap();

        let new_version = {
            let profiles = dip_system.configuration_profiles.read().await;
            profiles.get("test_profile").unwrap().version
        };

        assert_eq!(new_version, initial_version + 1);

        let retrieved_questions = dip_system.get_profile_questions("test_profile").await;
        assert_eq!(retrieved_questions.len(), 1);
        assert_eq!(retrieved_questions[0].question_id, "risk_tolerance");
    }
}
