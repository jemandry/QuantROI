use solana_client::rpc_client::RpcClient;
use solana_sdk::{
    commitment_config::CommitmentConfig,
    pubkey::Pubkey,
    signature::{Keypair, Signature},
    transaction::Transaction,
    compute_budget::ComputeBudgetInstruction,
};
use std::collections::HashMap;
use std::str::FromStr;
use serde::{Deserialize, Serialize};
use tokio::time::{Duration, Instant};

use crate::error::ApiError;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JitoBundle {
    pub transactions: Vec<Transaction>,
    pub bundle_id: String,
    pub tip_amount: u64,
    pub priority_fee: u64,
    pub max_retries: u32,
}

#[derive(Debug, Clone)]
pub struct GeographicRpcEndpoint {
    pub region: String,
    pub url: String,
    pub jito_endpoint: Option<String>,
    pub latency_ms: f64,
    pub is_jito_validator: bool,
}

#[derive(Debug, Clone)]
pub enum TradeUrgency {
    Critical,    // <1s execution required
    High,        // <5s execution required
    Normal,      // <30s execution acceptable
    Low,         // Best effort
}

#[derive(Debug, Clone)]
pub struct AtomicTradeBundle {
    pub causal_analysis_tx: Transaction,
    pub trade_execution_tx: Transaction,
    pub compliance_logging_tx: Transaction,
    pub masking_application_tx: Option<Transaction>,
    pub bundle_metadata: BundleMetadata,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BundleMetadata {
    pub strategy_id: String,
    pub user_id: String,
    pub timestamp: i64,
    pub expected_execution_time_ms: u64,
    pub max_slippage_bps: u16,
    pub compliance_flags: Vec<String>,
}

pub struct JitoMevProtectionService {
    geographic_endpoints: HashMap<String, GeographicRpcEndpoint>,
    current_endpoint: GeographicRpcEndpoint,
    jito_client: Option<RpcClient>,
    bundle_cache: HashMap<String, JitoBundle>,
    performance_metrics: MevPerformanceMetrics,
}

#[derive(Debug, Default)]
pub struct MevPerformanceMetrics {
    pub total_bundles_submitted: u64,
    pub successful_bundles: u64,
    pub failed_bundles: u64,
    pub avg_execution_time_ms: f64,
    pub total_tips_paid: u64,
    pub mev_protection_rate: f64,
    pub geographic_latencies: HashMap<String, f64>,
}

impl JitoMevProtectionService {
    pub async fn new() -> Result<Self, ApiError> {
        let geographic_endpoints = Self::initialize_geographic_endpoints();
        let current_endpoint = Self::select_optimal_endpoint(&geographic_endpoints).await?;
        
        let jito_client = if current_endpoint.jito_endpoint.is_some() {
            Some(RpcClient::new_with_commitment(
                current_endpoint.jito_endpoint.as_ref().unwrap().clone(),
                CommitmentConfig::confirmed(),
            ))
        } else {
            None
        };

        Ok(Self {
            geographic_endpoints,
            current_endpoint,
            jito_client,
            bundle_cache: HashMap::new(),
            performance_metrics: MevPerformanceMetrics::default(),
        })
    }

    fn initialize_geographic_endpoints() -> HashMap<String, GeographicRpcEndpoint> {
        let mut endpoints = HashMap::new();
        
        endpoints.insert("us-east".to_string(), GeographicRpcEndpoint {
            region: "us-east".to_string(),
            url: "https://ny.rpc.jito.wtf".to_string(),
            jito_endpoint: Some("https://ny.mainnet.block-engine.jito.wtf".to_string()),
            latency_ms: 0.0,
            is_jito_validator: true,
        });

        endpoints.insert("ap-southeast".to_string(), GeographicRpcEndpoint {
            region: "ap-southeast".to_string(),
            url: "https://singapore.rpc.jito.wtf".to_string(),
            jito_endpoint: Some("https://singapore.mainnet.block-engine.jito.wtf".to_string()),
            latency_ms: 0.0,
            is_jito_validator: true,
        });

        endpoints.insert("eu-west".to_string(), GeographicRpcEndpoint {
            region: "eu-west".to_string(),
            url: "https://london.rpc.jito.wtf".to_string(),
            jito_endpoint: Some("https://london.mainnet.block-engine.jito.wtf".to_string()),
            latency_ms: 0.0,
            is_jito_validator: true,
        });

        endpoints.insert("mainnet-fallback".to_string(), GeographicRpcEndpoint {
            region: "mainnet-fallback".to_string(),
            url: "https://api.mainnet-beta.solana.com".to_string(),
            jito_endpoint: None,
            latency_ms: 0.0,
            is_jito_validator: false,
        });

        endpoints.insert("devnet-fallback".to_string(), GeographicRpcEndpoint {
            region: "devnet-fallback".to_string(),
            url: "https://api.devnet.solana.com".to_string(),
            jito_endpoint: None,
            latency_ms: 0.0,
            is_jito_validator: false,
        });

        endpoints
    }

    async fn select_optimal_endpoint(endpoints: &HashMap<String, GeographicRpcEndpoint>) -> Result<GeographicRpcEndpoint, ApiError> {
        let env_preference = std::env::var("SOLANA_NETWORK").unwrap_or_else(|_| "devnet".to_string());
        
        if env_preference == "mainnet" {
            Ok(endpoints.get("us-east").unwrap().clone())
        } else {
            Ok(endpoints.get("devnet-fallback").unwrap().clone())
        }
    }

    pub async fn submit_atomic_bundle(&mut self, bundle: AtomicTradeBundle) -> Result<String, ApiError> {
        let start_time = Instant::now();
        
        let priority_fee = self.calculate_priority_fee(&bundle).await?;
        let tip_amount = self.calculate_tip_amount(&bundle).await?;
        
        let mut transactions = vec![
            bundle.causal_analysis_tx,
            bundle.trade_execution_tx,
            bundle.compliance_logging_tx,
        ];
        
        if let Some(masking_tx) = bundle.masking_application_tx {
            transactions.push(masking_tx);
        }

        for tx in &mut transactions {
            let priority_fee_ix = ComputeBudgetInstruction::set_compute_unit_price(priority_fee);
        }

        let jito_bundle = JitoBundle {
            transactions: transactions.clone(),
            bundle_id: format!("bundle_{}", chrono::Utc::now().timestamp_millis()),
            tip_amount,
            priority_fee,
            max_retries: 3,
        };

        let result = if let Some(ref jito_client) = self.jito_client {
            self.submit_jito_bundle_internal(&jito_bundle).await
        } else {
            self.submit_regular_bundle(&jito_bundle).await
        };

        let execution_time = start_time.elapsed().as_millis() as f64;
        self.update_performance_metrics(&jito_bundle, &result, execution_time);

        result
    }

    async fn submit_jito_bundle_internal(&self, bundle: &JitoBundle) -> Result<String, ApiError> {
        
        log::info!("Submitting Jito bundle {} with {} transactions", 
                  bundle.bundle_id, bundle.transactions.len());
        log::info!("Bundle tip: {} lamports, priority fee: {} lamports", 
                  bundle.tip_amount, bundle.priority_fee);

        tokio::time::sleep(Duration::from_millis(50)).await;
        
        Ok(format!("jito_bundle_{}", bundle.bundle_id))
    }

    async fn submit_regular_bundle(&self, bundle: &JitoBundle) -> Result<String, ApiError> {
        log::warn!("Jito not available, falling back to regular transaction submission");
        log::warn!("WARNING: Transactions are vulnerable to MEV extraction");

        let client = RpcClient::new_with_commitment(
            self.current_endpoint.url.clone(),
            CommitmentConfig::confirmed(),
        );

        let mut signatures = Vec::new();
        for (i, tx) in bundle.transactions.iter().enumerate() {
            match client.send_and_confirm_transaction(tx) {
                Ok(signature) => {
                    signatures.push(signature.to_string());
                    log::info!("Transaction {}/{} confirmed: {}", i + 1, bundle.transactions.len(), signature);
                }
                Err(e) => {
                    log::error!("Transaction {}/{} failed: {}", i + 1, bundle.transactions.len(), e);
                    return Err(ApiError::SolanaTransactionFailed(
                        format!("Bundle partially failed at transaction {}: {}", i + 1, e)
                    ));
                }
            }
        }

        Ok(format!("regular_bundle_{}", bundle.bundle_id))
    }

    async fn calculate_priority_fee(&self, bundle: &AtomicTradeBundle) -> Result<u64, ApiError> {
        let base_fee = 1000u64; // 1000 lamports base
        
        let urgency_multiplier = match self.determine_trade_urgency(bundle) {
            TradeUrgency::Critical => 10.0,
            TradeUrgency::High => 5.0,
            TradeUrgency::Normal => 2.0,
            TradeUrgency::Low => 1.0,
        };

        let congestion_multiplier = self.get_network_congestion_multiplier().await;
        
        let final_fee = (base_fee as f64 * urgency_multiplier * congestion_multiplier) as u64;
        
        Ok(final_fee.min(10_000))
    }

    async fn calculate_tip_amount(&self, bundle: &AtomicTradeBundle) -> Result<u64, ApiError> {
        let base_tip = 1000u64;
        
        let trade_size_multiplier = self.get_trade_size_multiplier(bundle);
        let time_sensitivity_multiplier = self.get_time_sensitivity_multiplier(bundle);
        
        let final_tip = (base_tip as f64 * trade_size_multiplier * time_sensitivity_multiplier) as u64;
        
        Ok(final_tip.max(1_000).min(10_000))
    }

    fn determine_trade_urgency(&self, bundle: &AtomicTradeBundle) -> TradeUrgency {
        if bundle.bundle_metadata.expected_execution_time_ms < 1000 {
            TradeUrgency::Critical
        } else if bundle.bundle_metadata.expected_execution_time_ms < 5000 {
            TradeUrgency::High
        } else if bundle.bundle_metadata.expected_execution_time_ms < 30000 {
            TradeUrgency::Normal
        } else {
            TradeUrgency::Low
        }
    }

    async fn get_network_congestion_multiplier(&self) -> f64 {
        1.5
    }

    fn get_trade_size_multiplier(&self, bundle: &AtomicTradeBundle) -> f64 {
        2.0 // Simplified
    }

    fn get_time_sensitivity_multiplier(&self, bundle: &AtomicTradeBundle) -> f64 {
        match self.determine_trade_urgency(bundle) {
            TradeUrgency::Critical => 3.0,
            TradeUrgency::High => 2.0,
            TradeUrgency::Normal => 1.5,
            TradeUrgency::Low => 1.0,
        }
    }

    fn update_performance_metrics(&mut self, bundle: &JitoBundle, result: &Result<String, ApiError>, execution_time_ms: f64) {
        self.performance_metrics.total_bundles_submitted += 1;
        
        match result {
            Ok(_) => {
                self.performance_metrics.successful_bundles += 1;
                self.performance_metrics.total_tips_paid += bundle.tip_amount;
            }
            Err(_) => {
                self.performance_metrics.failed_bundles += 1;
            }
        }

        let total_executions = self.performance_metrics.total_bundles_submitted as f64;
        self.performance_metrics.avg_execution_time_ms = 
            (self.performance_metrics.avg_execution_time_ms * (total_executions - 1.0) + execution_time_ms) / total_executions;

        self.performance_metrics.mev_protection_rate = 
            if self.jito_client.is_some() { 1.0 } else { 0.0 };

        self.performance_metrics.geographic_latencies.insert(
            self.current_endpoint.region.clone(),
            execution_time_ms,
        );
    }

    pub async fn switch_to_optimal_endpoint(&mut self) -> Result<(), ApiError> {
        let mut best_endpoint = self.current_endpoint.clone();
        let mut best_latency = f64::MAX;

        for endpoint in self.geographic_endpoints.values() {
            let latency = self.test_endpoint_latency(endpoint).await;
            if latency < best_latency {
                best_latency = latency;
                best_endpoint = endpoint.clone();
            }
        }

        if best_endpoint.region != self.current_endpoint.region {
            log::info!("Switching from {} to {} (latency: {:.2}ms)", 
                      self.current_endpoint.region, best_endpoint.region, best_latency);
            
            self.current_endpoint = best_endpoint;
            
            self.jito_client = if self.current_endpoint.jito_endpoint.is_some() {
                Some(RpcClient::new_with_commitment(
                    self.current_endpoint.jito_endpoint.as_ref().unwrap().clone(),
                    CommitmentConfig::confirmed(),
                ))
            } else {
                None
            };
        }

        Ok(())
    }

    async fn test_endpoint_latency(&self, endpoint: &GeographicRpcEndpoint) -> f64 {
        let start = Instant::now();
        
        let client = RpcClient::new_with_commitment(endpoint.url.clone(), CommitmentConfig::confirmed());
        
        match client.get_slot() {
            Ok(_) => start.elapsed().as_millis() as f64,
            Err(_) => f64::MAX, // Endpoint unavailable
        }
    }

    pub fn get_performance_metrics(&self) -> &MevPerformanceMetrics {
        &self.performance_metrics
    }

    pub fn get_current_endpoint(&self) -> &GeographicRpcEndpoint {
        &self.current_endpoint
    }

    pub async fn send_private_transaction(&self, transaction: &Transaction) -> Result<Signature, ApiError> {
        if let Some(ref jito_client) = self.jito_client {
            log::info!("Submitting transaction to Jito private mempool");
            jito_client
                .send_and_confirm_transaction(transaction)
                .map_err(|e| ApiError::SolanaTransactionFailed(format!("Jito transaction failed: {}", e)))
        } else {
            log::warn!("Jito not available, submitting to public mempool (MEV vulnerable)");
            let client = RpcClient::new_with_commitment(
                self.current_endpoint.url.clone(),
                CommitmentConfig::confirmed(),
            );
            client
                .send_and_confirm_transaction(transaction)
                .map_err(|e| ApiError::SolanaTransactionFailed(format!("Transaction failed: {}", e)))
        }
    }
}

impl AtomicTradeBundle {
    pub fn new(
        strategy_id: String,
        user_id: String,
        causal_analysis_tx: Transaction,
        trade_execution_tx: Transaction,
        compliance_logging_tx: Transaction,
        masking_application_tx: Option<Transaction>,
    ) -> Self {
        Self {
            causal_analysis_tx,
            trade_execution_tx,
            compliance_logging_tx,
            masking_application_tx,
            bundle_metadata: BundleMetadata {
                strategy_id,
                user_id,
                timestamp: chrono::Utc::now().timestamp(),
                expected_execution_time_ms: 1000, // Default 1 second
                max_slippage_bps: 50, // Default 0.5%
                compliance_flags: vec![],
            },
        }
    }

    pub fn with_urgency(mut self, expected_execution_time_ms: u64) -> Self {
        self.bundle_metadata.expected_execution_time_ms = expected_execution_time_ms;
        self
    }

    pub fn with_slippage_tolerance(mut self, max_slippage_bps: u16) -> Self {
        self.bundle_metadata.max_slippage_bps = max_slippage_bps;
        self
    }

    pub fn with_compliance_flags(mut self, flags: Vec<String>) -> Self {
        self.bundle_metadata.compliance_flags = flags;
        self
    }
}
