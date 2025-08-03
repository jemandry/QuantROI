use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use serde::{Deserialize, Serialize};
use uuid::Uuid;
use chrono::{DateTime, Utc};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataInventory {
    pub stock_symbol: Option<String>,
    pub time_period: Option<String>,
    pub volume_data: bool,
    pub news_data: bool,
    pub options_data: bool,
    pub earnings_data: bool,
    pub insider_trading: bool,
    pub market_events: bool,
    pub seasonal_data: bool,
    pub etf_flows: bool,
    pub custom_factors: HashMap<String, bool>,
}

impl Default for DataInventory {
    fn default() -> Self {
        Self {
            stock_symbol: None,
            time_period: None,
            volume_data: false,
            news_data: false,
            options_data: false,
            earnings_data: false,
            insider_trading: false,
            market_events: false,
            seasonal_data: false,
            etf_flows: false,
            custom_factors: HashMap::new(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CausalQuestion {
    pub id: String,
    pub question: String,
    pub category: String,
    pub priority: u8,
    pub data_requirement: String,
    pub confidence_impact: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserResponse {
    pub question_id: String,
    pub response: String,
    pub timestamp: DateTime<Utc>,
    pub confidence_boost: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnalysisSession {
    pub session_id: String,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub inventory: DataInventory,
    pub asked_questions: Vec<String>,
    pub user_responses: Vec<UserResponse>,
    pub confidence_score: f32,
    pub status: SessionStatus,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SessionStatus {
    Initializing,
    GatheringData,
    AskingQuestions,
    AnalysisReady,
    Completed,
}

pub struct CausalDataAgent {
    sessions: Arc<RwLock<HashMap<String, AnalysisSession>>>,
    baseline_questions: Vec<CausalQuestion>,
    confidence_threshold: f32,
    quantum_audit_engine: Option<Box<dyn crate::quantum_audit::QuantumAuditEngine + Send + Sync>>,
}

impl CausalDataAgent {
    pub fn new() -> Self {
        let baseline_questions = vec![
            CausalQuestion {
                id: "earnings_news".to_string(),
                question: "Was there any earnings announcement or significant news during this time period?".to_string(),
                category: "fundamental".to_string(),
                priority: 9,
                data_requirement: "news_data".to_string(),
                confidence_impact: 0.15,
            },
            CausalQuestion {
                id: "volume_spike".to_string(),
                question: "Did you notice any unusual volume spikes or trading activity?".to_string(),
                category: "technical".to_string(),
                priority: 8,
                data_requirement: "volume_data".to_string(),
                confidence_impact: 0.12,
            },
            CausalQuestion {
                id: "options_activity".to_string(),
                question: "Were there any large option trades or changes in implied volatility?".to_string(),
                category: "derivatives".to_string(),
                priority: 7,
                data_requirement: "options_data".to_string(),
                confidence_impact: 0.10,
            },
            CausalQuestion {
                id: "market_events".to_string(),
                question: "Were there any market-wide events (Fed decisions, economic data) affecting this stock?".to_string(),
                category: "macro".to_string(),
                priority: 8,
                data_requirement: "market_events".to_string(),
                confidence_impact: 0.13,
            },
            CausalQuestion {
                id: "seasonal_effects".to_string(),
                question: "Has this stock shown seasonal patterns (e.g., Q4 strength, summer weakness)?".to_string(),
                category: "seasonal".to_string(),
                priority: 5,
                data_requirement: "seasonal_data".to_string(),
                confidence_impact: 0.08,
            },
            CausalQuestion {
                id: "etf_flows".to_string(),
                question: "Were there unusual inflows/outflows in ETFs or indexes containing this stock?".to_string(),
                category: "flows".to_string(),
                priority: 6,
                data_requirement: "etf_flows".to_string(),
                confidence_impact: 0.09,
            },
            CausalQuestion {
                id: "insider_trading".to_string(),
                question: "Was there any reported insider buying or selling activity?".to_string(),
                category: "insider".to_string(),
                priority: 7,
                data_requirement: "insider_trading".to_string(),
                confidence_impact: 0.11,
            },
        ];

        Self {
            sessions: Arc::new(RwLock::new(HashMap::new())),
            baseline_questions,
            confidence_threshold: 0.7,
            quantum_audit_engine: None,
        }
    }

    pub async fn create_session(&self) -> String {
        let session_id = Uuid::new_v4().to_string();
        let session = AnalysisSession {
            session_id: session_id.clone(),
            created_at: Utc::now(),
            updated_at: Utc::now(),
            inventory: DataInventory::default(),
            asked_questions: Vec::new(),
            user_responses: Vec::new(),
            confidence_score: 0.0,
            status: SessionStatus::Initializing,
        };

        let mut sessions = self.sessions.write().await;
        sessions.insert(session_id.clone(), session);
        session_id
    }

    pub async fn get_session(&self, session_id: &str) -> Option<AnalysisSession> {
        let sessions = self.sessions.read().await;
        sessions.get(session_id).cloned()
    }

    pub async fn update_inventory(&self, session_id: &str, field: &str, value: String) -> Result<(), String> {
        let mut sessions = self.sessions.write().await;
        if let Some(session) = sessions.get_mut(session_id) {
            match field {
                "stock_symbol" => session.inventory.stock_symbol = Some(value),
                "time_period" => session.inventory.time_period = Some(value),
                "volume_data" => session.inventory.volume_data = value.parse().unwrap_or(false),
                "news_data" => session.inventory.news_data = value.parse().unwrap_or(false),
                "options_data" => session.inventory.options_data = value.parse().unwrap_or(false),
                "earnings_data" => session.inventory.earnings_data = value.parse().unwrap_or(false),
                "insider_trading" => session.inventory.insider_trading = value.parse().unwrap_or(false),
                "market_events" => session.inventory.market_events = value.parse().unwrap_or(false),
                "seasonal_data" => session.inventory.seasonal_data = value.parse().unwrap_or(false),
                "etf_flows" => session.inventory.etf_flows = value.parse().unwrap_or(false),
                _ => {
                    session.inventory.custom_factors.insert(field.to_string(), value.parse().unwrap_or(false));
                }
            }
            session.updated_at = Utc::now();
            session.confidence_score = self.calculate_confidence_score(&session.inventory);
            Ok(())
        } else {
            Err("Session not found".to_string())
        }
    }

    pub async fn add_custom_factor(&self, session_id: &str, factor_name: &str, _description: &str) -> Result<(), String> {
        let mut sessions = self.sessions.write().await;
        if let Some(session) = sessions.get_mut(session_id) {
            session.inventory.custom_factors.insert(factor_name.to_string(), false);
            session.updated_at = Utc::now();
            Ok(())
        } else {
            Err("Session not found".to_string())
        }
    }

    pub async fn get_missing_data_requests(&self, session_id: &str) -> Result<Vec<String>, String> {
        let sessions = self.sessions.read().await;
        if let Some(session) = sessions.get(session_id) {
            let mut missing = Vec::new();

            if session.inventory.stock_symbol.is_none() {
                missing.push("Which asset would you like to analyze? (stock symbol, ETF, or index)".to_string());
            }

            if session.inventory.time_period.is_none() {
                missing.push("What time period should we analyze? (e.g., 'Jan 2025', 'last 30 days', 'Q4 2024')".to_string());
            }

            if !session.inventory.volume_data {
                missing.push("Volume data is missing. This could impact analysis confidence. Would you like to include volume data?".to_string());
            }

            if !session.inventory.news_data {
                missing.push("News and earnings data is not available. This significantly impacts causal analysis. Add news data?".to_string());
            }

            if !session.inventory.options_data {
                missing.push("Options chain data is missing. This could help identify institutional activity. Include options data?".to_string());
            }

            Ok(missing)
        } else {
            Err("Session not found".to_string())
        }
    }

    pub async fn get_causal_questions(&self, session_id: &str) -> Result<Vec<CausalQuestion>, String> {
        let sessions = self.sessions.read().await;
        if let Some(session) = sessions.get(session_id) {
            let mut relevant_questions = Vec::new();

            for question in &self.baseline_questions {
                if !session.asked_questions.contains(&question.id) {
                    let should_ask = match question.data_requirement.as_str() {
                        "news_data" => session.inventory.stock_symbol.is_some(),
                        "volume_data" => session.inventory.stock_symbol.is_some(),
                        "options_data" => session.inventory.stock_symbol.is_some(),
                        "market_events" => session.inventory.time_period.is_some(),
                        "seasonal_data" => session.inventory.stock_symbol.is_some() && session.inventory.time_period.is_some(),
                        "etf_flows" => session.inventory.stock_symbol.is_some(),
                        "insider_trading" => session.inventory.stock_symbol.is_some(),
                        _ => true,
                    };

                    if should_ask {
                        relevant_questions.push(question.clone());
                    }
                }
            }

            relevant_questions.sort_by(|a, b| b.priority.cmp(&a.priority));
            Ok(relevant_questions)
        } else {
            Err("Session not found".to_string())
        }
    }

    pub async fn record_user_response(&self, session_id: &str, question_id: &str, response: &str) -> Result<(), String> {
        let mut sessions = self.sessions.write().await;
        if let Some(session) = sessions.get_mut(session_id) {
            let confidence_boost = self.baseline_questions
                .iter()
                .find(|q| q.id == question_id)
                .map(|q| q.confidence_impact)
                .unwrap_or(0.05);

            let user_response = UserResponse {
                question_id: question_id.to_string(),
                response: response.to_string(),
                timestamp: Utc::now(),
                confidence_boost,
            };

            session.user_responses.push(user_response);
            session.asked_questions.push(question_id.to_string());
            session.updated_at = Utc::now();
            
            session.confidence_score = self.calculate_confidence_score(&session.inventory) + 
                session.user_responses.iter().map(|r| r.confidence_boost).sum::<f32>();

            if session.confidence_score >= self.confidence_threshold {
                session.status = SessionStatus::AnalysisReady;
            }

            Ok(())
        } else {
            Err("Session not found".to_string())
        }
    }

    pub async fn get_confidence_feedback(&self, session_id: &str) -> Result<String, String> {
        let sessions = self.sessions.read().await;
        if let Some(session) = sessions.get(session_id) {
            let confidence = session.confidence_score;
            
            let feedback = if confidence < 0.3 {
                format!("Analysis confidence is very low ({:.1}%). Critical data is missing. Please provide stock symbol and time period to continue.", confidence * 100.0)
            } else if confidence < 0.5 {
                format!("Analysis confidence is low ({:.1}%). Consider adding volume data and news information to improve accuracy.", confidence * 100.0)
            } else if confidence < self.confidence_threshold {
                format!("Analysis confidence is moderate ({:.1}%). Adding options data or market event information could improve results.", confidence * 100.0)
            } else {
                format!("Analysis confidence is high ({:.1}%). Ready to proceed with causal analysis.", confidence * 100.0)
            };

            Ok(feedback)
        } else {
            Err("Session not found".to_string())
        }
    }

    pub async fn is_ready_for_analysis(&self, session_id: &str) -> Result<bool, String> {
        let sessions = self.sessions.read().await;
        if let Some(session) = sessions.get(session_id) {
            Ok(session.confidence_score >= self.confidence_threshold && 
               session.inventory.stock_symbol.is_some() && 
               session.inventory.time_period.is_some())
        } else {
            Err("Session not found".to_string())
        }
    }

    pub async fn generate_analysis_summary(&self, session_id: &str) -> Result<String, String> {
        let sessions = self.sessions.read().await;
        if let Some(session) = sessions.get(session_id) {
            let mut summary = format!("Causal Analysis Summary for Session {}\n", session_id);
            summary.push_str(&format!("Created: {}\n", session.created_at.format("%Y-%m-%d %H:%M:%S UTC")));
            summary.push_str(&format!("Confidence Score: {:.1}%\n\n", session.confidence_score * 100.0));

            if let Some(symbol) = &session.inventory.stock_symbol {
                summary.push_str(&format!("Asset: {}\n", symbol));
            }
            if let Some(period) = &session.inventory.time_period {
                summary.push_str(&format!("Time Period: {}\n", period));
            }

            summary.push_str("\nData Availability:\n");
            summary.push_str(&format!("- Volume Data: {}\n", if session.inventory.volume_data { "✓" } else { "✗" }));
            summary.push_str(&format!("- News Data: {}\n", if session.inventory.news_data { "✓" } else { "✗" }));
            summary.push_str(&format!("- Options Data: {}\n", if session.inventory.options_data { "✓" } else { "✗" }));
            summary.push_str(&format!("- Earnings Data: {}\n", if session.inventory.earnings_data { "✓" } else { "✗" }));
            summary.push_str(&format!("- Insider Trading: {}\n", if session.inventory.insider_trading { "✓" } else { "✗" }));
            summary.push_str(&format!("- Market Events: {}\n", if session.inventory.market_events { "✓" } else { "✗" }));
            summary.push_str(&format!("- Seasonal Data: {}\n", if session.inventory.seasonal_data { "✓" } else { "✗" }));
            summary.push_str(&format!("- ETF Flows: {}\n", if session.inventory.etf_flows { "✓" } else { "✗" }));

            if !session.inventory.custom_factors.is_empty() {
                summary.push_str("\nCustom Factors:\n");
                for (factor, available) in &session.inventory.custom_factors {
                    summary.push_str(&format!("- {}: {}\n", factor, if *available { "✓" } else { "✗" }));
                }
            }

            if !session.user_responses.is_empty() {
                summary.push_str("\nUser Responses:\n");
                for response in &session.user_responses {
                    let question = self.baseline_questions.iter()
                        .find(|q| q.id == response.question_id)
                        .map(|q| q.question.as_str())
                        .unwrap_or("Unknown question");
                    summary.push_str(&format!("- {}: {}\n", question, response.response));
                }
            }

            Ok(summary)
        } else {
            Err("Session not found".to_string())
        }
    }

    fn calculate_confidence_score(&self, inventory: &DataInventory) -> f32 {
        let mut score = 0.0;
        let mut max_score = 0.0;

        if inventory.stock_symbol.is_some() {
            score += 0.2;
        }
        max_score += 0.2;

        if inventory.time_period.is_some() {
            score += 0.15;
        }
        max_score += 0.15;

        if inventory.volume_data {
            score += 0.12;
        }
        max_score += 0.12;

        if inventory.news_data {
            score += 0.15;
        }
        max_score += 0.15;

        if inventory.options_data {
            score += 0.10;
        }
        max_score += 0.10;

        if inventory.earnings_data {
            score += 0.08;
        }
        max_score += 0.08;

        if inventory.insider_trading {
            score += 0.06;
        }
        max_score += 0.06;

        if inventory.market_events {
            score += 0.08;
        }
        max_score += 0.08;

        if inventory.seasonal_data {
            score += 0.04;
        }
        max_score += 0.04;

        if inventory.etf_flows {
            score += 0.02;
        }
        max_score += 0.02;

        score / max_score
    }

    pub async fn get_next_action(&self, session_id: &str) -> Result<String, String> {
        let sessions = self.sessions.read().await;
        if let Some(session) = sessions.get(session_id) {
            if session.inventory.stock_symbol.is_none() {
                return Ok("Please specify the asset you want to analyze (stock symbol, ETF, or index).".to_string());
            }

            if session.inventory.time_period.is_none() {
                return Ok("Please specify the time period for analysis (e.g., 'Jan 2025', 'last 30 days').".to_string());
            }

            if session.confidence_score < 0.4 {
                return Ok("Confidence is low. Consider adding volume data or news information.".to_string());
            }

            if session.confidence_score < self.confidence_threshold {
                let missing_questions = self.get_causal_questions(session_id).await?;
                if !missing_questions.is_empty() {
                    return Ok(format!("Consider answering: {}", missing_questions[0].question));
                }
            }

            if session.confidence_score >= self.confidence_threshold {
                return Ok("Ready for causal analysis! All necessary data has been collected.".to_string());
            }

            Ok("Continue gathering data or answering causal questions.".to_string())
        } else {
            Err("Session not found".to_string())
        }
    }
    
    pub fn new_with_quantum_engine(quantum_engine: Option<Box<dyn crate::quantum_audit::QuantumAuditEngine + Send + Sync>>) -> Self {
        let baseline_questions = vec![
            CausalQuestion {
                id: "earnings_news".to_string(),
                question: "Was there any earnings announcement or significant news during this time period?".to_string(),
                category: "fundamental".to_string(),
                priority: 9,
                data_requirement: "news_data".to_string(),
                confidence_impact: 0.15,
            },
            CausalQuestion {
                id: "volume_spike".to_string(),
                question: "Did you notice any unusual volume spikes or trading activity?".to_string(),
                category: "technical".to_string(),
                priority: 8,
                data_requirement: "volume_data".to_string(),
                confidence_impact: 0.12,
            },
            CausalQuestion {
                id: "options_activity".to_string(),
                question: "Were there any large option trades or changes in implied volatility?".to_string(),
                category: "derivatives".to_string(),
                priority: 7,
                data_requirement: "options_data".to_string(),
                confidence_impact: 0.10,
            },
            CausalQuestion {
                id: "market_events".to_string(),
                question: "Were there any market-wide events (Fed decisions, economic data) affecting this stock?".to_string(),
                category: "macro".to_string(),
                priority: 8,
                data_requirement: "market_events".to_string(),
                confidence_impact: 0.13,
            },
            CausalQuestion {
                id: "quantum_entanglement".to_string(),
                question: "Are there quantum entanglement patterns in the market data that could indicate hidden correlations?".to_string(),
                category: "quantum".to_string(),
                priority: 6,
                data_requirement: "quantum_data".to_string(),
                confidence_impact: 0.08,
            },
            CausalQuestion {
                id: "regulatory_prediction".to_string(),
                question: "What regulatory changes might affect this asset based on quantum ML predictions?".to_string(),
                category: "regulatory".to_string(),
                priority: 7,
                data_requirement: "regulatory_data".to_string(),
                confidence_impact: 0.11,
            },
        ];

        Self {
            sessions: Arc::new(RwLock::new(HashMap::new())),
            baseline_questions,
            confidence_threshold: 0.7,
            quantum_audit_engine: quantum_engine,
        }
    }
    
    pub async fn create_quantum_audit_session(&self, mode: crate::quantum_audit::QuantumMode) -> Result<String, String> {
        if let Some(quantum_engine) = &self.quantum_audit_engine {
            quantum_engine.create_audit_session(mode).await
        } else {
            Err("Quantum audit engine not available".to_string())
        }
    }
    
    pub async fn analyze_with_quantum_audit(&self, session_id: &str, data: &[u8]) -> Result<String, String> {
        if let Some(quantum_engine) = &self.quantum_audit_engine {
            let audit_result = quantum_engine.process_quantum_audit(session_id, data).await?;
            let predictions = quantum_engine.predict_regulatory_changes(session_id).await?;
            
            Ok(format!(
                "Quantum Audit Analysis:\n\
                 - Audit ID: {}\n\
                 - Entanglement Score: {:.4}\n\
                 - Decoherence Time: {:.2}ms\n\
                 - Regulatory Predictions: {} identified\n\
                 - Quantum Hash: {:02x?}",
                audit_result.audit_id,
                audit_result.entanglement_score,
                audit_result.decoherence_time,
                predictions.len(),
                &audit_result.quantum_hash[..8]
            ))
        } else {
            Err("Quantum audit engine not available".to_string())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_agent_creation() {
        let agent = CausalDataAgent::new();
        assert_eq!(agent.baseline_questions.len(), 7);
        assert_eq!(agent.confidence_threshold, 0.7);
    }

    #[tokio::test]
    async fn test_session_management() {
        let agent = CausalDataAgent::new();
        let session_id = agent.create_session().await;
        
        let session = agent.get_session(&session_id).await;
        assert!(session.is_some());
        
        let session = session.unwrap();
        assert_eq!(session.session_id, session_id);
        assert!(matches!(session.status, SessionStatus::Initializing));
    }

    #[tokio::test]
    async fn test_inventory_updates() {
        let agent = CausalDataAgent::new();
        let session_id = agent.create_session().await;
        
        agent.update_inventory(&session_id, "stock_symbol", "AAPL".to_string()).await.unwrap();
        agent.update_inventory(&session_id, "time_period", "Jan 2025".to_string()).await.unwrap();
        agent.update_inventory(&session_id, "volume_data", "true".to_string()).await.unwrap();
        
        let session = agent.get_session(&session_id).await.unwrap();
        assert_eq!(session.inventory.stock_symbol, Some("AAPL".to_string()));
        assert_eq!(session.inventory.time_period, Some("Jan 2025".to_string()));
        assert!(session.inventory.volume_data);
        assert!(session.confidence_score > 0.0);
    }

    #[tokio::test]
    async fn test_causal_questions() {
        let agent = CausalDataAgent::new();
        let session_id = agent.create_session().await;
        
        agent.update_inventory(&session_id, "stock_symbol", "AAPL".to_string()).await.unwrap();
        
        let questions = agent.get_causal_questions(&session_id).await.unwrap();
        assert!(!questions.is_empty());
        assert!(questions.iter().any(|q| q.category == "fundamental"));
    }

    #[tokio::test]
    async fn test_confidence_progression() {
        let agent = CausalDataAgent::new();
        let session_id = agent.create_session().await;
        
        let initial_confidence = agent.get_session(&session_id).await.unwrap().confidence_score;
        
        agent.update_inventory(&session_id, "stock_symbol", "AAPL".to_string()).await.unwrap();
        let after_symbol = agent.get_session(&session_id).await.unwrap().confidence_score;
        assert!(after_symbol > initial_confidence);
        
        agent.update_inventory(&session_id, "volume_data", "true".to_string()).await.unwrap();
        let after_volume = agent.get_session(&session_id).await.unwrap().confidence_score;
        assert!(after_volume > after_symbol);
    }

    #[tokio::test]
    async fn test_user_responses() {
        let agent = CausalDataAgent::new();
        let session_id = agent.create_session().await;
        
        agent.update_inventory(&session_id, "stock_symbol", "AAPL".to_string()).await.unwrap();
        
        agent.record_user_response(&session_id, "earnings_news", "Yes, there was an earnings beat").await.unwrap();
        
        let session = agent.get_session(&session_id).await.unwrap();
        assert_eq!(session.user_responses.len(), 1);
        assert!(session.asked_questions.contains(&"earnings_news".to_string()));
        assert!(session.confidence_score > 0.2);
    }
}
