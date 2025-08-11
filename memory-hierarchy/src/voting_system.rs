use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Vote {
    pub vote_id: String,
    pub voter_address: String,
    pub proposal_id: String,
    pub vote_choice: VoteChoice,
    pub timestamp: DateTime<Utc>,
    pub weight: f64,
    pub signature: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum VoteChoice {
    Yes,
    No,
    Abstain,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Proposal {
    pub proposal_id: String,
    pub title: String,
    pub description: String,
    pub proposer_address: String,
    pub created_at: DateTime<Utc>,
    pub voting_deadline: DateTime<Utc>,
    pub proposal_type: ProposalType,
    pub status: ProposalStatus,
    pub required_quorum: f64,
    pub required_majority: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ProposalType {
    TradingStrategy,
    RiskParameter,
    FeeStructure,
    GovernanceRule,
    TreasuryAllocation,
    DelegationPolicy,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ProposalStatus {
    Active,
    Passed,
    Rejected,
    Expired,
    Executed,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VotingResult {
    pub proposal_id: String,
    pub total_votes: u64,
    pub yes_votes: u64,
    pub no_votes: u64,
    pub abstain_votes: u64,
    pub total_weight: f64,
    pub yes_weight: f64,
    pub no_weight: f64,
    pub abstain_weight: f64,
    pub quorum_reached: bool,
    pub majority_reached: bool,
    pub final_status: ProposalStatus,
}

#[allow(dead_code)]
pub struct VotingSystem {
    proposals: Arc<RwLock<HashMap<String, Proposal>>>,
    votes: Arc<RwLock<HashMap<String, Vec<Vote>>>>,
    voter_weights: Arc<RwLock<HashMap<String, f64>>>,
    solana_integration: Arc<crate::solana_event_logger::SolanaEventLogger>,
    audit_engine: Option<Arc<dyn crate::quantum_audit::QuantumAuditEngine + Send + Sync>>,
}

impl VotingSystem {
    pub async fn new(
        solana_integration: Arc<crate::solana_event_logger::SolanaEventLogger>,
    ) -> Self {
        Self {
            proposals: Arc::new(RwLock::new(HashMap::new())),
            votes: Arc::new(RwLock::new(HashMap::new())),
            voter_weights: Arc::new(RwLock::new(HashMap::new())),
            solana_integration,
            audit_engine: None,
        }
    }

    pub async fn create_proposal(
        &self,
        proposal: Proposal,
    ) -> Result<String, Box<dyn std::error::Error + Send + Sync>> {
        let proposal_id = proposal.proposal_id.clone();
        
        {
            let mut proposals = self.proposals.write().await;
            proposals.insert(proposal_id.clone(), proposal.clone());
        }

        {
            let mut votes = self.votes.write().await;
            votes.insert(proposal_id.clone(), Vec::new());
        }

        let _event_id = self.solana_integration
            .log_governance_event(&proposal_id, "proposal_created", &serde_json::to_string(&proposal)?)
            .await?;

        Ok(proposal_id)
    }

    pub async fn cast_vote(
        &self,
        vote: Vote,
    ) -> Result<String, Box<dyn std::error::Error + Send + Sync>> {
        let proposal_id = vote.proposal_id.clone();
        let vote_id = vote.vote_id.clone();

        {
            let proposals = self.proposals.read().await;
            let proposal = proposals.get(&proposal_id)
                .ok_or("Proposal not found")?;
            
            if proposal.status != ProposalStatus::Active {
                return Err("Proposal is not active".into());
            }

            if Utc::now() > proposal.voting_deadline {
                return Err("Voting deadline has passed".into());
            }
        }

        {
            let votes = self.votes.read().await;
            if let Some(existing_votes) = votes.get(&proposal_id) {
                if existing_votes.iter().any(|v| v.voter_address == vote.voter_address) {
                    return Err("Voter has already voted on this proposal".into());
                }
            }
        }

        let voter_weight = {
            let weights = self.voter_weights.read().await;
            weights.get(&vote.voter_address).copied().unwrap_or(1.0)
        };

        let mut weighted_vote = vote;
        weighted_vote.weight = voter_weight;

        {
            let mut votes = self.votes.write().await;
            votes.entry(proposal_id.clone())
                .or_insert_with(Vec::new)
                .push(weighted_vote.clone());
        }

        let _event_id = self.solana_integration
            .log_governance_event(&proposal_id, "vote_cast", &serde_json::to_string(&weighted_vote)?)
            .await?;

        Ok(vote_id)
    }

    pub async fn tally_votes(
        &self,
        proposal_id: &str,
    ) -> Result<VotingResult, Box<dyn std::error::Error + Send + Sync>> {
        let proposal = {
            let proposals = self.proposals.read().await;
            proposals.get(proposal_id)
                .ok_or("Proposal not found")?
                .clone()
        };

        let votes = {
            let votes = self.votes.read().await;
            votes.get(proposal_id)
                .cloned()
                .unwrap_or_default()
        };

        let mut yes_votes = 0u64;
        let mut no_votes = 0u64;
        let mut abstain_votes = 0u64;
        let mut yes_weight = 0.0f64;
        let mut no_weight = 0.0f64;
        let mut abstain_weight = 0.0f64;
        let mut total_weight = 0.0f64;

        for vote in &votes {
            total_weight += vote.weight;
            match vote.vote_choice {
                VoteChoice::Yes => {
                    yes_votes += 1;
                    yes_weight += vote.weight;
                }
                VoteChoice::No => {
                    no_votes += 1;
                    no_weight += vote.weight;
                }
                VoteChoice::Abstain => {
                    abstain_votes += 1;
                    abstain_weight += vote.weight;
                }
            }
        }

        let quorum_reached = total_weight >= proposal.required_quorum;
        let majority_reached = yes_weight > (yes_weight + no_weight) * proposal.required_majority;

        let final_status = if !quorum_reached {
            ProposalStatus::Rejected
        } else if majority_reached {
            ProposalStatus::Passed
        } else {
            ProposalStatus::Rejected
        };

        let result = VotingResult {
            proposal_id: proposal_id.to_string(),
            total_votes: votes.len() as u64,
            yes_votes,
            no_votes,
            abstain_votes,
            total_weight,
            yes_weight,
            no_weight,
            abstain_weight,
            quorum_reached,
            majority_reached,
            final_status: final_status.clone(),
        };

        {
            let mut proposals = self.proposals.write().await;
            if let Some(proposal) = proposals.get_mut(proposal_id) {
                proposal.status = final_status;
            }
        }

        let _event_id = self.solana_integration
            .log_governance_event(proposal_id, "voting_completed", &serde_json::to_string(&result)?)
            .await?;

        Ok(result)
    }

    pub async fn set_voter_weight(
        &self,
        voter_address: &str,
        weight: f64,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let mut weights = self.voter_weights.write().await;
        weights.insert(voter_address.to_string(), weight);
        Ok(())
    }

    pub async fn get_proposal(
        &self,
        proposal_id: &str,
    ) -> Result<Option<Proposal>, Box<dyn std::error::Error + Send + Sync>> {
        let proposals = self.proposals.read().await;
        Ok(proposals.get(proposal_id).cloned())
    }

    pub async fn get_active_proposals(&self) -> Result<Vec<Proposal>, Box<dyn std::error::Error + Send + Sync>> {
        let proposals = self.proposals.read().await;
        Ok(proposals.values()
            .filter(|p| p.status == ProposalStatus::Active && Utc::now() <= p.voting_deadline)
            .cloned()
            .collect())
    }

    pub async fn get_votes_for_proposal(
        &self,
        proposal_id: &str,
    ) -> Result<Vec<Vote>, Box<dyn std::error::Error + Send + Sync>> {
        let votes = self.votes.read().await;
        Ok(votes.get(proposal_id).cloned().unwrap_or_default())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::braided_cord_data_engine::BraidedCordDataEngine;

    #[tokio::test]
    async fn test_voting_system_creation() {
        let braided_engine = Arc::new(BraidedCordDataEngine::new().await);
        let solana_logger = Arc::new(crate::solana_event_logger::SolanaEventLogger::new(braided_engine).await);
        let voting_system = VotingSystem::new(solana_logger).await;
        
        assert!(voting_system.proposals.read().await.is_empty());
        assert!(voting_system.votes.read().await.is_empty());
    }

    #[tokio::test]
    async fn test_proposal_creation() {
        let braided_engine = Arc::new(BraidedCordDataEngine::new().await);
        let solana_logger = Arc::new(crate::solana_event_logger::SolanaEventLogger::new(braided_engine).await);
        let voting_system = VotingSystem::new(solana_logger).await;

        let proposal = Proposal {
            proposal_id: "prop_001".to_string(),
            title: "Increase Trading Fee".to_string(),
            description: "Proposal to increase trading fee from 0.1% to 0.15%".to_string(),
            proposer_address: "proposer123".to_string(),
            created_at: Utc::now(),
            voting_deadline: Utc::now() + chrono::Duration::days(7),
            proposal_type: ProposalType::FeeStructure,
            status: ProposalStatus::Active,
            required_quorum: 100.0,
            required_majority: 0.6,
        };

        let result = voting_system.create_proposal(proposal.clone()).await;
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), "prop_001");

        let stored_proposal = voting_system.get_proposal("prop_001").await.unwrap();
        assert!(stored_proposal.is_some());
        assert_eq!(stored_proposal.unwrap().title, "Increase Trading Fee");
    }

    #[tokio::test]
    async fn test_vote_casting() {
        let braided_engine = Arc::new(BraidedCordDataEngine::new().await);
        let solana_logger = Arc::new(crate::solana_event_logger::SolanaEventLogger::new(braided_engine).await);
        let voting_system = VotingSystem::new(solana_logger).await;

        let proposal = Proposal {
            proposal_id: "prop_002".to_string(),
            title: "Test Proposal".to_string(),
            description: "Test proposal for voting".to_string(),
            proposer_address: "proposer123".to_string(),
            created_at: Utc::now(),
            voting_deadline: Utc::now() + chrono::Duration::days(7),
            proposal_type: ProposalType::TradingStrategy,
            status: ProposalStatus::Active,
            required_quorum: 10.0,
            required_majority: 0.5,
        };

        voting_system.create_proposal(proposal).await.unwrap();

        voting_system.set_voter_weight("voter1", 5.0).await.unwrap();

        let vote = Vote {
            vote_id: "vote_001".to_string(),
            voter_address: "voter1".to_string(),
            proposal_id: "prop_002".to_string(),
            vote_choice: VoteChoice::Yes,
            timestamp: Utc::now(),
            weight: 0.0, // Will be set by the system
            signature: "signature123".to_string(),
        };

        let result = voting_system.cast_vote(vote).await;
        assert!(result.is_ok());

        let votes = voting_system.get_votes_for_proposal("prop_002").await.unwrap();
        assert_eq!(votes.len(), 1);
        assert_eq!(votes[0].weight, 5.0);
        assert!(matches!(votes[0].vote_choice, VoteChoice::Yes));
    }

    #[tokio::test]
    async fn test_vote_tallying() {
        let braided_engine = Arc::new(BraidedCordDataEngine::new().await);
        let solana_logger = Arc::new(crate::solana_event_logger::SolanaEventLogger::new(braided_engine).await);
        let voting_system = VotingSystem::new(solana_logger).await;

        let proposal = Proposal {
            proposal_id: "prop_003".to_string(),
            title: "Test Tallying".to_string(),
            description: "Test proposal for vote tallying".to_string(),
            proposer_address: "proposer123".to_string(),
            created_at: Utc::now(),
            voting_deadline: Utc::now() + chrono::Duration::days(7),
            proposal_type: ProposalType::RiskParameter,
            status: ProposalStatus::Active,
            required_quorum: 10.0,
            required_majority: 0.6,
        };

        voting_system.create_proposal(proposal).await.unwrap();

        voting_system.set_voter_weight("voter1", 6.0).await.unwrap();
        voting_system.set_voter_weight("voter2", 4.0).await.unwrap();
        voting_system.set_voter_weight("voter3", 2.0).await.unwrap();

        let votes = vec![
            Vote {
                vote_id: "vote_001".to_string(),
                voter_address: "voter1".to_string(),
                proposal_id: "prop_003".to_string(),
                vote_choice: VoteChoice::Yes,
                timestamp: Utc::now(),
                weight: 0.0,
                signature: "sig1".to_string(),
            },
            Vote {
                vote_id: "vote_002".to_string(),
                voter_address: "voter2".to_string(),
                proposal_id: "prop_003".to_string(),
                vote_choice: VoteChoice::Yes,
                timestamp: Utc::now(),
                weight: 0.0,
                signature: "sig2".to_string(),
            },
            Vote {
                vote_id: "vote_003".to_string(),
                voter_address: "voter3".to_string(),
                proposal_id: "prop_003".to_string(),
                vote_choice: VoteChoice::No,
                timestamp: Utc::now(),
                weight: 0.0,
                signature: "sig3".to_string(),
            },
        ];

        for vote in votes {
            voting_system.cast_vote(vote).await.unwrap();
        }

        let result = voting_system.tally_votes("prop_003").await.unwrap();
        
        assert_eq!(result.total_votes, 3);
        assert_eq!(result.yes_votes, 2);
        assert_eq!(result.no_votes, 1);
        assert_eq!(result.yes_weight, 10.0); // 6.0 + 4.0
        assert_eq!(result.no_weight, 2.0);
        assert_eq!(result.total_weight, 12.0);
        assert!(result.quorum_reached);
        assert!(result.majority_reached); // 10.0 > (10.0 + 2.0) * 0.6 = 7.2
        assert!(matches!(result.final_status, ProposalStatus::Passed));
    }
}
