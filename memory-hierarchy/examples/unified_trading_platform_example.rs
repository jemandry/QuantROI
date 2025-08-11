use memory_hierarchy::*;
use memory_hierarchy::voting_system::{ProposalStatus, ProposalType};
use memory_hierarchy::dip_switch_system::BankType;
use memory_hierarchy::money_disbursement_system::{DisbursementStatus, DisbursementPriority, DisbursementType};
use memory_hierarchy::inspector_verification_system::{Inspector, InspectorSpecialization, InspectorStatus};
use std::sync::Arc;
use std::collections::HashMap;
use chrono::Utc;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    println!("🚀 Unified Trading Platform Integration Demo");
    
    let braided_engine = Arc::new(BraidedCordDataEngine::new().await);
    println!("✅ Braided cord data engine initialized");
    
    let solana_logger = Arc::new(SolanaEventLogger::new(braided_engine.clone()).await);
    println!("✅ Solana event logging initialized");
    
    let wealth_engine = Arc::new(TradingWealthEngine::new());
    println!("✅ Trading wealth engine initialized");
    
    let voting_system = Arc::new(VotingSystem::new(solana_logger.clone()).await);
    println!("✅ Voting system initialized");
    
    let dip_system = Arc::new(DipSwitchSystem::new(solana_logger.clone()).await);
    println!("✅ DIP switch system initialized");
    
    let mina_zkp = Arc::new(MinaZkpIntegration::new(
        "https://berkeley.minaprotocol.com:3085".to_string(),
        "test_private_key".to_string(),
        "test_public_key".to_string(),
        solana_logger.clone(),
    ).await);
    println!("✅ Mina ZKP integration initialized");
    
    let inspector_system = Arc::new(InspectorVerificationSystem::new(
        solana_logger.clone(),
        wealth_engine.clone(),
    ).await);
    println!("✅ Inspector verification system initialized");
    
    let disbursement_system = Arc::new(MoneyDisbursementSystem::new(
        inspector_system.clone(),
        wealth_engine.clone(),
        solana_logger.clone(),
    ).await);
    println!("✅ Money disbursement system initialized");
    
    println!("\n📊 Demo 1: Trading Strategy Proposal with ZKP");
    
    let proposal = Proposal {
        proposal_id: "strategy_001".to_string(),
        title: "AI-Driven Risk Management Strategy".to_string(),
        description: "Implement new AI-driven risk management with ZKP verification".to_string(),
        proposer_address: "proposer_wallet_123".to_string(),
        created_at: Utc::now(),
        voting_deadline: Utc::now() + chrono::Duration::days(7),
        proposal_type: ProposalType::TradingStrategy,
        status: ProposalStatus::Active,
        required_quorum: 100.0,
        required_majority: 0.6,
    };
    
    let proposal_id = voting_system.create_proposal(proposal).await?;
    println!("✅ Created proposal: {}", proposal_id);
    
    let strategy_circuit = ZkCircuit {
        circuit_id: "strategy_verification".to_string(),
        circuit_name: "Strategy Verification Circuit".to_string(),
        circuit_type: ProofType::TradingCompliance,
        constraints: vec!["risk_limit < 0.1".to_string()],
        public_inputs: vec!["strategy_id".to_string()],
        private_inputs: vec!["risk_parameters".to_string()],
        verification_key: "strategy_vk_123".to_string(),
        proving_key: "strategy_pk_123".to_string(),
    };
    
    mina_zkp.register_circuit(strategy_circuit).await?;
    
    let strategy_proof = mina_zkp.generate_proof(
        "strategy_verification",
        vec!["strategy_001".to_string()],
        vec!["risk_limit=0.05".to_string()],
        "Strategy meets risk requirements".to_string(),
    ).await?;
    
    println!("✅ Generated ZKP for strategy: {}", strategy_proof.proof_id);
    
    println!("\n🔧 Demo 2: DIP Switch Configuration for Trading Parameters");
    
    let trading_params_bank = DipSwitchBank {
        bank_id: "trading_params_main".to_string(),
        bank_name: "Main Trading Parameters".to_string(),
        switch_count: 8,
        current_state: vec![false; 8],
        bank_type: BankType::TradingParameters,
        hardware_address: "0x1000".to_string(),
        last_modified: Utc::now(),
        description: "Primary trading parameter configuration bank".to_string(),
    };
    
    let risk_management_bank = DipSwitchBank {
        bank_id: "risk_mgmt_001".to_string(),
        bank_name: "Risk Management Controls".to_string(),
        switch_count: 6,
        current_state: vec![false; 6],
        bank_type: BankType::RiskManagement,
        hardware_address: "0x2000".to_string(),
        last_modified: Utc::now(),
        description: "Risk management and compliance controls".to_string(),
    };
    
    dip_system.register_switch_bank(trading_params_bank).await?;
    dip_system.register_switch_bank(risk_management_bank).await?;
    
    dip_system.set_switch_state(
        "trading_params_main",
        0,
        true,
        "system_admin",
        "Enable high-frequency trading mode"
    ).await?;
    
    dip_system.set_switch_state(
        "risk_mgmt_001",
        2,
        true,
        "risk_manager",
        "Activate volatility monitoring"
    ).await?;
    
    println!("✅ Configured DIP switches for trading parameters");
    
    println!("\n🔍 Demo 3: Inspector Verification for Money Disbursement");
    
    let inspector = Inspector {
        inspector_id: "inspector_001".to_string(),
        public_key: "inspector_pubkey_123".to_string(),
        specializations: vec![InspectorSpecialization::MoneyDisbursement],
        verification_count: 0,
        success_rate: 1.0,
        last_active: Utc::now(),
        status: InspectorStatus::Active,
        workload_capacity: 10,
        current_workload: 0,
    };
    
    inspector_system.register_inspector(inspector).await?;
    println!("✅ Registered inspector for disbursement verification");
    
    let disbursement_request = DisbursementRequest {
        disbursement_id: "disbursement_001".to_string(),
        requester_id: "trader_wallet_456".to_string(),
        recipient_id: "recipient_wallet_789".to_string(),
        amount: 50000,
        disbursement_type: DisbursementType::TradingProfit,
        verification_required: true,
        inspector_verification_id: None,
        cryptographic_hash: String::new(),
        status: DisbursementStatus::Pending,
        priority: DisbursementPriority::Medium,
        created_at: Utc::now(),
        approved_at: None,
        executed_at: None,
        metadata: HashMap::new(),
    };
    
    let disbursement_id = disbursement_system.request_disbursement(disbursement_request).await?;
    println!("✅ Requested disbursement with inspector verification: {}", disbursement_id);
    
    println!("\n🗳️  Demo 4: Voting on Trading Strategy Proposal");
    
    voting_system.set_voter_weight("voter_001", 25.0).await?;
    voting_system.set_voter_weight("voter_002", 35.0).await?;
    voting_system.set_voter_weight("voter_003", 40.0).await?;
    
    let votes = vec![
        Vote {
            vote_id: "vote_001".to_string(),
            voter_address: "voter_001".to_string(),
            proposal_id: "strategy_001".to_string(),
            vote_choice: VoteChoice::Yes,
            timestamp: Utc::now(),
            weight: 0.0,
            signature: "sig_001".to_string(),
        },
        Vote {
            vote_id: "vote_002".to_string(),
            voter_address: "voter_002".to_string(),
            proposal_id: "strategy_001".to_string(),
            vote_choice: VoteChoice::Yes,
            timestamp: Utc::now(),
            weight: 0.0,
            signature: "sig_002".to_string(),
        },
        Vote {
            vote_id: "vote_003".to_string(),
            voter_address: "voter_003".to_string(),
            proposal_id: "strategy_001".to_string(),
            vote_choice: VoteChoice::No,
            timestamp: Utc::now(),
            weight: 0.0,
            signature: "sig_003".to_string(),
        },
    ];
    
    for vote in votes {
        voting_system.cast_vote(vote).await?;
    }
    
    let voting_result = voting_system.tally_votes("strategy_001").await?;
    println!("✅ Voting completed - Result: {:?}", voting_result.final_status);
    println!("   Yes: {:.1}%, No: {:.1}%, Quorum: {}", 
             voting_result.yes_weight / voting_result.total_weight * 100.0,
             voting_result.no_weight / voting_result.total_weight * 100.0,
             voting_result.quorum_reached);
    
    println!("\n📋 Demo 5: Complete Audit Trail Integration");
    
    let audit_events = solana_logger.get_cached_events().await;
    println!("✅ Total audit events logged: {}", audit_events.len());
    
    for (event_id, event) in audit_events.iter().take(5) {
        println!("   Event {}: {:?} at {}", event_id, event.event_type, event.timestamp_ns);
    }
    
    println!("\n🎉 Unified Trading Platform Integration Demo Complete!");
    println!("   ✅ Voting system with ZKP verification");
    println!("   ✅ DIP switch hardware configuration");
    println!("   ✅ Inspector verification for disbursements");
    println!("   ✅ Comprehensive audit trail");
    println!("   ✅ Dual-chain Solana + Mina integration");
    
    Ok(())
}
